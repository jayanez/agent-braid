# SPDX-License-Identifier: AGPL-3.0-only
"""Image-independent immutable admission recipe and metadata-only tree arithmetic.

No Git invocation, blob read, object write, checkout or execution in this module.
Static expected-tree derivation does not establish runtime equivalence/admission.
"""
from copy import deepcopy
import hashlib
import json
import re
from .forecast_data import pin, require
from .forecast_git_launch import INPUT_COMMITS

BASE = '48f4226db1e1b0565b1f8faf0eca81c150a65d30'
REPOSITORY = '/opt/agent-braid/inputs/repository'
RECIPE_PATH = '/opt/agent-braid/fc1/recipe.json'
IMAGE_GIT_CONFIG = (b'[core]\n\trepositoryformatversion = 0\n\tfilemode = true\n'
                    b'\tbare = false\n\tlogallrefupdates = false\n\thooksPath = /dev/null\n')


def tree_oid(entries):
    require(type(entries) is dict and len(entries) <= 10000, 'recipe-tree-bound')
    root = {}
    for path,(mode,oid) in entries.items():
        require(type(path) is str and not path.startswith('/') and
                all(p not in ('','.','..') for p in path.split('/')), 'recipe-tree-path')
        require(mode in ('100644','100755') and re.fullmatch('[0-9a-f]{40}',oid), 'recipe-tree-entry')
        parts=path.split('/'); node=root
        for part in parts[:-1]:
            require(not isinstance(node.get(part),tuple), 'recipe-parent-path-collision')
            node=node.setdefault(part,{})
        require(parts[-1] not in node, 'recipe-parent-path-collision')
        node[parts[-1]]=(mode,oid)
    def encode(node):
        raw=b''
        for name,value in sorted(node.items(),key=lambda pair:pair[0].encode()+
                                 (b'/' if isinstance(pair[1],dict) else b'')):
            mode,oid=('40000',encode(value)) if isinstance(value,dict) else value
            raw += mode.encode()+b' '+name.encode()+b'\0'+bytes.fromhex(oid)
        return hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    return encode(root)


def overlay(base, first, second):
    for tree in (base,first,second):
        tree_oid(tree)
    changes=[]; result=dict(base)
    for source in (first,second):
        require(set(base) <= set(source), 'recipe-delete-refused')
        changed=sorted(path for path,value in source.items() if base.get(path) != value)
        require(changed and len(changed) <= 16, 'recipe-change-count')
        for path in changed:
            require(path not in base or base[path][0] == source[path][0], 'recipe-mode-change')
            result[path]=source[path]
        changes.append(changed)
    require(not set(changes[0]) & set(changes[1]) and sum(map(len,changes)) <= 16,
            'recipe-overlapping-inputs')
    tree_oid(result)
    return result,changes


def request_from_metadata(base, sources, *, headers):
    """Caller supplies only bounded, previously read exact commit/tree metadata."""
    require(type(headers) is list and len(headers) == 3, 'recipe-commit-headers')
    require(headers[0]['commit'] == BASE and headers[0]['tree'] == tree_oid(base), 'recipe-base-tree')
    for commit,header,tree in zip(INPUT_COMMITS,headers[1:],sources,strict=True):
        require(header == {'commit':commit,'parents':[BASE],'tree':tree_oid(tree)},
                'recipe-source-parent-tree')
    merged,changes=overlay(base,*sources)
    ids=('fc1-accounting','plugins-docs')
    return {'gitRuntimeRequestVersion':'0.1.0-alpha','repository':REPOSITORY,
        'baseRevision':BASE,'expectedFinalTree':tree_oid(merged),'order':list(ids),
        'operations':[{'instanceId':name,'attemptId':'admission-'+name,
                       'source':{'kind':'commit','revision':commit},'dependencies':[],
                       'uncertainPaths':[],'declaredWrites':paths}
                      for name,commit,paths in zip(ids,INPUT_COMMITS,changes,strict=True)]}


def recipe_bytes(request, *, source_digest, git_sha256):
    """Create canonical bytes only with all real operator pins available.

    The image hash/profile identity deliberately cannot occur in the recipe.
    """
    from .forecast_admission_worker import bootstrap_free_request
    require(bootstrap_free_request(request) and request['repository'] == REPOSITORY
            and request['baseRevision'] == BASE and
            tuple(op['source']['revision'] for op in request['operations']) == INPUT_COMMITS,
            'recipe-fixed-request')
    value={'version':'agent-braid-admission-worker-v2','sourceDigest':pin(source_digest),
           'gitSha256':pin(git_sha256),'request':deepcopy(request)}
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def verify_loose_inputs(git_directory, read, *, expected_inventory=None):
    """Native readback of the image's CLOSED loose-object input repository.

    Reads only the three fixed commits and their tree/blob closure. No Git child,
    code execution, pack fallback, alternates, network or producer receipts. All
    decompression/hash work belongs to the prospective phase wall/CPU ledger.
    """
    import zlib
    from pathlib import Path
    directory=Path(git_directory); cache={}; total=0; compressed=0
    def obj(oid):
        nonlocal total,compressed
        require(re.fullmatch('[0-9a-f]{40}',oid), 'recipe-object-id')
        if oid in cache:
            return cache[oid]
        require(len(cache)<20000, 'recipe-object-count')
        raw=read(directory/'objects'/oid[:2]/oid[2:],64*1024*1024)
        compressed+=len(raw)
        require(compressed<=128*1024*1024,'recipe-compressed-byte-bound')
        decoder=zlib.decompressobj()
        data=decoder.decompress(raw,64*1024*1024+1)
        require(decoder.eof and not decoder.unused_data and not decoder.unconsumed_tail
                and len(data)<=64*1024*1024, 'recipe-object-compression-bound')
        total+=len(data)
        require(total<=128*1024*1024 and hashlib.sha1(data).hexdigest()==oid, 'recipe-object-integrity')
        header,sep,body=data.partition(b'\0')
        kind,size=header.split(b' ',1)
        require(sep and str(len(body)).encode()==size and kind in (b'commit',b'tree',b'blob'),
                'recipe-object-header')
        cache[oid]=(kind,body)
        return cache[oid]
    def flatten(oid,prefix='',depth=0):
        require(depth<64,'recipe-tree-depth')
        kind,body=obj(oid);require(kind==b'tree','recipe-tree-type')
        result={}; offset=0; names=set()
        while offset<len(body):
            end=body.index(b'\0',offset)
            mode,name=body[offset:end].split(b' ',1)
            require(name not in names and name and b'/' not in name,'recipe-tree-name')
            names.add(name);child=body[end+1:end+21]
            require(len(child)==20,'recipe-tree-oid')
            offset=end+21;name=name.decode('utf-8');path=prefix+name
            if mode==b'40000':
                result.update(flatten(child.hex(),path+'/',depth+1))
            else:
                require(mode in (b'100644',b'100755') and obj(child.hex())[0]==b'blob',
                        'recipe-nonregular-input')
                result[path]=(mode.decode(),child.hex())
        require(tree_oid({p.removeprefix(prefix):v for p,v in result.items()})==oid,'recipe-tree-order')
        return result
    headers=[];trees=[]
    for commit in (BASE,*INPUT_COMMITS):
        kind,data=obj(commit);require(kind==b'commit','recipe-commit-type')
        header=data.split(b'\n\n',1)[0].splitlines()
        tree=[line[5:].decode() for line in header if line.startswith(b'tree ')]
        parents=[line[7:].decode() for line in header if line.startswith(b'parent ')]
        require(len(tree)==1,'recipe-commit-tree')
        headers.append({'commit':commit,'parents':parents,'tree':tree[0]})
        trees.append(flatten(tree[0]))
    if expected_inventory is not None:
        require(set(cache)==expected_inventory,'recipe-extra-or-missing-objects')
    return request_from_metadata(trees[0],trees[1:],headers=headers)
