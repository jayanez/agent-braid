# SPDX-License-Identifier: AGPL-3.0-only
"""Closed census of an explicit offline staging tree; never inspect the live host.

No extraction, discovery, subprocess, ELF loading, mounting or runtime control.
The external manifest pin selects bytes; publisher/build/boot authority is separate.
Aliases must be flattened inside the retained byte cap, never followed off-tree.
"""
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat

from .forecast_data import digest, integer, parse_record, pin, require
from .forecast_linux_artifacts import elf_dependencies, elf_header, MAX_BYTES
from .forecast_build import inspect_dependency_config, inspect_kernel_helper_config

ROLES = ('manager','executor','operatorPython','operatorLauncher','workerPython','git',
         'dmsetup','managerBridge','execCensus','kernelConfig','cryptsetupConfig','libdevmapperConfig')
ELF_ROLES = ('manager','executor','operatorPython','workerPython','git','dmsetup','managerBridge')


def _name(value):
    require(type(value) is str and 0 < len(value) <= 1024, 'host-census-path')
    pure = PurePosixPath(value)
    require(not pure.is_absolute() and str(pure) == value and
            all(p not in ('','.','..') for p in pure.parts) and len(pure.parts) <= 16,
            'host-census-path')
    require(not any(p in ('udev','udevadm','systemd-udevd') or p.startswith('systemd-udevd.')
                    for p in pure.parts), 'host-census-udev-path')
    return value


def _stamp(info):
    return (info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_gid,
            info.st_size,info.st_mtime_ns,info.st_ctime_ns,info.st_nlink)


def inspect_staged_host(root, manifest_bytes, *, expected_manifest_sha256):
    """Walk every entry using retained no-follow directory FDs, with finite caps.

    Only call on an operator-selected build staging tree. The manifest is outside
    that tree, preventing a self-referential file. No entry is inferred from a
    producer's claim that a signature, closed census or bootstrap was accepted.
    A stable read window does not establish immutable future bytes or live state.
    """
    pin(expected_manifest_sha256)
    require(type(manifest_bytes) is bytes and hashlib.sha256(manifest_bytes).hexdigest()
            == expected_manifest_sha256, 'host-census-manifest-pin')
    m = parse_record(manifest_bytes)
    require(set(m) == {'version','sourceDigest','provenanceSha256','ownerUid','files',
                       'directories','bindings','forbiddenElfSha256'} and
            m['version'] == 'fc1-staged-host-v1', 'host-census-fields')
    pin(m['sourceDigest']); pin(m['provenanceSha256']); integer(m['ownerUid'],0,65535)
    require(type(m['files']) is list and 0 < len(m['files']) <= 4096 and
            type(m['directories']) is list and len(m['directories']) <= 4096 and
            type(m['bindings']) is dict and set(m['bindings']) == set(ROLES), 'host-census-roster')
    require(type(m['forbiddenElfSha256']) is list and 0 < len(m['forbiddenElfSha256']) <= 64,
            'host-census-forbidden-pins')
    forbidden = {pin(v) for v in m['forbiddenElfSha256']}
    rows = {}; total = 0
    for row in m['files']:
        require(type(row) is dict and set(row) == {'path','sha256','bytes','mode'}, 'host-census-file-fields')
        name = _name(row['path']); pin(row['sha256']); integer(row['bytes'],0,128*1024**2)
        integer(row['mode'],0,0o777)
        require(name not in rows and not row['mode'] & 0o022, 'host-census-file-mode-or-duplicate')
        total += row['bytes']; require(total <= MAX_BYTES, 'host-census-byte-cap'); rows[name] = row
    directories = [_name(p) for p in m['directories']]
    require(len(set(directories)) == len(directories) and not set(directories)&set(rows),
            'host-census-directory-roster')
    require(all(type(p) is str and p in rows for p in m['bindings'].values()), 'host-census-binding')
    root = Path(root)
    require(root.is_absolute() and root == root.resolve() and root != Path('/'), 'host-census-staging-root')
    fd = os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    seen_files = {}; seen_dirs = set(); payloads = {}; visited = 0; read_bytes = 0
    try:
        root_info = os.fstat(fd)
        def walk(directory, prefix, depth):
            nonlocal visited, read_bytes
            before = os.fstat(directory)
            require(depth <= 16 and before.st_dev == root_info.st_dev and
                    before.st_uid == m['ownerUid'] and not before.st_mode & 0o022,
                    'host-census-directory-boundary')
            # Incremental scandir avoids constructing an unbounded unexpected-name list.
            with os.scandir(directory) as entries:
                for entry in entries:
                    visited += 1; require(visited <= 8192, 'host-census-entry-cap')
                    name = _name(prefix+entry.name)
                    info = os.stat(entry.name,dir_fd=directory,follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode):
                        require(name in directories, 'host-census-unlisted-directory')
                        child = os.open(entry.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,
                                        dir_fd=directory)
                        try:
                            require(_stamp(os.fstat(child)) == _stamp(info), 'host-census-directory-race')
                            seen_dirs.add(name); walk(child,name+'/',depth+1)
                        finally: os.close(child)
                    else:
                        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                                'host-census-alias-or-special-file')
                        require(name in rows and info.st_dev == root_info.st_dev and
                                info.st_uid == m['ownerUid'], 'host-census-unlisted-or-foreign-file')
                        expected = rows[name]
                        require(info.st_size == expected['bytes'] and
                                stat.S_IMODE(info.st_mode) == expected['mode'], 'host-census-file-metadata')
                        handle = os.open(entry.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK|os.O_NOCTTY,dir_fd=directory)
                        try:
                            require(_stamp(os.fstat(handle)) == _stamp(info), 'host-census-open-race')
                            raw = bytearray()
                            while len(raw) <= info.st_size:
                                part = os.read(handle,min(65536,info.st_size-len(raw)+1))
                                read_bytes += len(part); require(read_bytes <= MAX_BYTES, 'host-census-read-cap')
                                if not part: break
                                raw.extend(part)
                            require(len(raw) == info.st_size and _stamp(os.fstat(handle)) == _stamp(info),
                                    'host-census-file-drift')
                        finally: os.close(handle)
                        sha = hashlib.sha256(raw).hexdigest()
                        require(sha == expected['sha256'] and sha not in forbidden, 'host-census-file-pin-or-forbidden-copy')
                        observed = {'sha256':sha,'bytes':len(raw),'mode':expected['mode']}
                        if raw[:4] == b'\x7fELF':
                            bpf = name == m['bindings']['execCensus']
                            observed['elf'] = elf_header(raw,bpf=bpf)
                            if not bpf: observed['dependencies'] = elf_dependencies(raw)
                        seen_files[name] = observed
                        if name in {m['bindings'][r] for r in ('kernelConfig','cryptsetupConfig','libdevmapperConfig')}:
                            require(len(raw) <= 256*1024, 'host-census-config-cap'); payloads[name] = bytes(raw)
            require(_stamp(os.fstat(directory)) == _stamp(before), 'host-census-directory-drift')
        walk(fd,'',0)
    finally: os.close(fd)
    require(set(seen_files) == set(rows) and seen_dirs == set(directories), 'host-census-incomplete')
    bindings = {role:seen_files[name] for role,name in m['bindings'].items()}
    require(all('elf' in bindings[r] and bindings[r]['mode'] & 0o111 for r in ELF_ROLES)
            and bindings['execCensus'].get('elf',{}).get('machine') == 247, 'host-census-role-kind')
    configs = {'kernel':inspect_kernel_helper_config(payloads[m['bindings']['kernelConfig']]),
               **{r:inspect_dependency_config(r,payloads[m['bindings'][r+'Config']])
                  for r in ('cryptsetup','libdevmapper')}}
    return {'version':'fc1-staged-host-census-v1','manifestSha256':expected_manifest_sha256,
            'sourceDigest':m['sourceDigest'],'provenanceSha256':m['provenanceSha256'],
            'files':len(rows),'directories':len(directories),'fileBytes':total,
            'readBytes':read_bytes,'inventoryDigest':digest(seen_files),'bindings':bindings,
            'configs':configs,'closedStagingInventory':True,'linksOrSpecialFilesAccepted':False,
            'sourceObjectCorrespondenceVerified':False,'immutableFutureBytesVerified':False,
            'runningHostVerified':False,'hostActivationClosed':False,
            'nativeQualification':False,'executionAuthorization':False}
