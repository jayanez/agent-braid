# SPDX-License-Identifier: AGPL-3.0-only
"""Offline inspection of an operator-selected, independently pinned Linux bundle.

No discovery, download, extraction, import, build, ldd, subprocess or activation.
Byte identity and ELF metadata do not attest signatures, library resolution,
reproducible builds, vulnerability status, bootability or native capacity.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import struct

from .forecast_data import integer, pin, require
from research.lab.model import loads

REQUIRED = {'kernel','manager','systemctl','dmsetup','git','python','operator',
            'operatorLauncher','censusObject'}
MAX_FILES = 20000
MAX_BYTES = 480*1024**2


def elf_header(raw, *, bpf=False):
    require(len(raw)>=64 and raw[:7]==b'\x7fELF\x02\x01\x01','artifact-elf64-le')
    typ,machine,version=struct.unpack_from('<HHI',raw,16)
    require(machine==(247 if bpf else 183) and typ in ((1,) if bpf else (2,3))
            and version==1,'artifact-elf-architecture')
    return {'class':64,'endian':'little','machine':machine,'type':typ}


def inspect_bundle(root, manifest_bytes, *, expected_manifest_sha256):
    """Inspect explicit files only; the manifest pin is external operator authority.

    The caller must separately authenticate source releases/package metadata and
    review every binding. We never accept a self-reported signatureVerified flag.
    This function is not invoked automatically by profile compilation or import.
    """
    pin(expected_manifest_sha256)
    require(len(manifest_bytes)<=4*1024**2 and hashlib.sha256(manifest_bytes).hexdigest()
            ==expected_manifest_sha256,'artifact-manifest-pin')
    manifest=loads(manifest_bytes.decode())
    require(set(manifest)=={'version','architecture','files','bindings','provenanceSha256'}
            and manifest['version']=='fc1-linux-artifacts-v1' and manifest['architecture']=='aarch64',
            'artifact-manifest-fields')
    pin(manifest['provenanceSha256'])
    rows=manifest['files']; bindings=manifest['bindings']
    require(type(rows) is list and 0<len(rows)<=MAX_FILES and type(bindings) is dict
            and set(bindings)==REQUIRED,'artifact-roster')
    root=Path(root)
    require(root.is_absolute() and root.resolve()==root and root.is_dir(),'artifact-root')
    inventory={}; total=0
    for row in rows:
        require(type(row) is dict and set(row)=={'path','sha256','bytes','kind'},'artifact-file-fields')
        name=row['path']; pure=PurePosixPath(name)
        require(type(name) is str and name and not pure.is_absolute() and '..' not in pure.parts
                and str(pure)==name and len(name)<=1024 and len(pure.parts)<=16 and name not in inventory,'artifact-path')
        pin(row['sha256']);integer(row['bytes'],1,128*1024**2)
        require(row['kind'] in ('elf','bpf-elf','data'),'artifact-kind')
        total+=row['bytes']; require(total<=MAX_BYTES,'artifact-total-byte-cap')
        directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            for part in pure.parts[:-1]:
                child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
                os.close(directory);directory=child
            fd=os.open(pure.name,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=directory)
        finally: os.close(directory)
        try:
            before=os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and before.st_size==row['bytes'],'artifact-size-type')
            value=hashlib.sha256(); head=b''; read=0
            elf_bytes=bytearray() if row['kind']=='elf' else None
            while True:
                block=os.read(fd,min(1024**2,row['bytes']-read+1))
                if not block: break
                read+=len(block);require(read<=row['bytes'],'artifact-growing-file')
                if len(head)<64: head=(head+block)[:64]
                value.update(block)
                if elf_bytes is not None: elf_bytes.extend(block)
            after=os.fstat(fd)
            require((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)
                    ==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
                    and read==row['bytes'],'artifact-changed-during-read')
            require(value.hexdigest()==row['sha256'],'artifact-hash')
        finally: os.close(fd)
        inventory[name]={**row}
        if row['kind']!='data': inventory[name]['elf']=elf_header(head,bpf=row['kind']=='bpf-elf')
        if elf_bytes is not None: inventory[name]['dependencies']=elf_dependencies(elf_bytes)
    require(all(type(name) is str and name in inventory for name in bindings.values()),'artifact-binding')
    for role in ('manager','systemctl','dmsetup','git','python','operator'):
        require(inventory[bindings[role]]['kind']=='elf','artifact-executable-kind')
    require(inventory[bindings['censusObject']]['kind']=='bpf-elf','artifact-census-kind')
    return {'version':'fc1-linux-artifact-inspection-v1','manifestSha256':expected_manifest_sha256,
            'provenanceSha256':manifest['provenanceSha256'],'files':len(rows),'fileBytes':total,
            'bindings':{role:inventory[name] for role,name in bindings.items()},
            'sourceAuthenticityAccepted':False,'dependencyClosureAccepted':False,
            'imageBuilt':False,'nativeQualified':False,'executionAuthorization':False}


def elf_dependencies(raw):
    """Read ELF program/dynamic headers only; never ask the loader to resolve them."""
    elf_header(raw)
    offset=struct.unpack_from('<Q',raw,32)[0]
    size,count=struct.unpack_from('<HH',raw,54)
    require(count<=128 and (count==0 or size==56) and offset+size*count<=len(raw),
            'artifact-program-headers')
    segments=[];interpreter=None;dynamic=None
    for i in range(count):
        typ,flags,start,virtual,physical,filesize,memory,alignment=struct.unpack_from('<IIQQQQQQ',raw,offset+i*size)
        require(start+filesize<=len(raw),'artifact-segment-range')
        segments.append((typ,start,virtual,filesize))
        if typ==3:
            require(interpreter is None and 0<filesize<=4096 and raw[start+filesize-1]==0,
                    'artifact-interpreter')
            interpreter=bytes(raw[start:start+filesize-1]).decode('ascii')
        if typ==2:
            require(dynamic is None and filesize<=65536 and filesize%16==0,'artifact-dynamic-range')
            dynamic=(start,filesize)
    needed=[];paths=[];soname=None;required_versions={};provided_versions=[]
    if dynamic:
        tags=[];start,length=dynamic
        for pos in range(start,start+length,16):
            tag,value=struct.unpack_from('<qQ',raw,pos)
            if tag==0:break
            tags.append((tag,value))
        else: require(False,'artifact-dynamic-terminator')
        tables=[v for k,v in tags if k==5];sizes=[v for k,v in tags if k==10]
        require(len(tables)==len(sizes)==1 and 0<sizes[0]<=1024**2,'artifact-string-table')
        locations=[start+tables[0]-virtual for typ,start,virtual,length in segments
                   if typ==1 and virtual<=tables[0] and tables[0]+sizes[0]<=virtual+length]
        require(len(locations)==1,'artifact-string-table-mapping')
        table=locations[0];limit=table+sizes[0]
        def text_at(value):
            require(value<sizes[0],'artifact-dynamic-string-offset')
            end=raw.find(b'\0',table+value,limit)
            require(table+value<=end<=table+value+4096,'artifact-dynamic-string')
            return bytes(raw[table+value:end]).decode('ascii')
        def at_virtual(address,width):
            matches=[start+address-virtual for typ,start,virtual,length in segments
                     if typ==1 and virtual<=address and address+width<=virtual+length]
            require(len(matches)==1,'artifact-version-mapping')
            return matches[0]
        def version_chain(pointer_tag,count_tag,definition=False):
            pointers=[v for k,v in tags if k==pointer_tag];counts=[v for k,v in tags if k==count_tag]
            if not pointers and not counts:return
            require(len(pointers)==len(counts)==1 and 0<counts[0]<=128,'artifact-version-count')
            current=pointers[0];seen=set()
            for index in range(counts[0]):
                require(current not in seen,'artifact-version-cycle');seen.add(current)
                if definition:
                    pos=at_virtual(current,20)
                    version,flags,number,count,hashed,aux,next_offset=struct.unpack_from('<HHHHIII',raw,pos)
                    library=None;header_size=20;aux_size=8
                else:
                    pos=at_virtual(current,16)
                    version,count,name,aux,next_offset=struct.unpack_from('<HHIII',raw,pos)
                    library=text_at(name);header_size=16;aux_size=16
                require(version==1 and 0<count<=256 and aux>=header_size,'artifact-version-header')
                cursor=current+aux;aux_seen=set();names=[]
                for j in range(count):
                    require(cursor not in aux_seen,'artifact-version-aux-cycle');aux_seen.add(cursor)
                    pos=at_virtual(cursor,aux_size)
                    if definition:name,step=struct.unpack_from('<II',raw,pos)
                    else:hashed,flags,other,name,step=struct.unpack_from('<IHHII',raw,pos)
                    names.append(text_at(name))
                    require(step==0 if j==count-1 else step>=aux_size,'artifact-version-aux-link')
                    cursor+=step
                if definition:provided_versions.append(names[0])
                else:required_versions.setdefault(library,[]).extend(names)
                require(next_offset==0 if index==counts[0]-1 else next_offset>=header_size,
                        'artifact-version-link')
                current+=next_offset
        version_chain(0x6ffffffe,0x6fffffff)
        version_chain(0x6ffffffc,0x6ffffffd,True)
        for tag,value in tags:
            if tag not in (1,14,15,29):continue
            text=text_at(value)
            if tag==1:needed.append(text)
            elif tag==14:
                require(soname is None,'artifact-duplicate-soname');soname=text
            else:paths.append(text)
    return {'interpreter':interpreter,'needed':needed,'searchPaths':paths,'soname':soname,
            'requiredVersions':required_versions,'providedVersions':provided_versions,
            'loaderResolutionVerified':False}
