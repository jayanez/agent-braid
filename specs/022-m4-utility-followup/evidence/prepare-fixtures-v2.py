#!/usr/bin/env python3
"""Prepare immutable owned fixture objects; never invoke Agent Braid runtime."""
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path('/tmp/agent-braid-m4-utility-fixtures-v2-20261007')
SOURCE = Path('/tmp/agent-braid-m4-utility-review-20261007')
ROOT.mkdir(exist_ok=False)
ENV = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(ROOT),
       'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
       'GIT_CONFIG_COUNT': '0', 'GIT_DEFAULT_HASH': 'sha1',
       'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0',
       'GIT_AUTHOR_NAME': 'Agent Braid synthetic fixture preparation',
       'GIT_AUTHOR_EMAIL': 'fixtures@example.invalid',
       'GIT_COMMITTER_NAME': 'Agent Braid synthetic fixture preparation',
       'GIT_COMMITTER_EMAIL': 'fixtures@example.invalid',
       'GIT_AUTHOR_DATE': '2000-01-01T00:00:00+00:00',
       'GIT_COMMITTER_DATE': '2000-01-01T00:00:00+00:00'}

def git(repo, *args, data=None):
    return subprocess.run(['git', '-C', str(repo), '-c', 'core.hooksPath=/dev/null',
                           *args], env=ENV, input=data, capture_output=True,
                          check=True).stdout

def oid(repo, *args, data=None):
    return git(repo, *args, data=data).decode().strip()

def sha(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')

def tree(repo, blobs):
    listing = b''.join(f'100644 blob {blob}\t{name}\n'.encode()
                       for name, blob in sorted(blobs.items()))
    return oid(repo, 'mktree', data=listing)

blocks = []
for family, count in [('independent', 2), ('independent', 4), ('dependency-chain', 4)]:
    for size in [1024, 65536, 1048576]:
        name = f'{family}-{count}-{size}'
        directory = ROOT / name
        directory.mkdir()
        repo = directory / 'source.git'
        git(directory, 'init', '--bare', '--template=', '--quiet', str(repo))
        ids = list('abcd'[:count])
        base_blob = oid(repo, 'hash-object', '-w', '--stdin', data=b'base\n')
        base_blobs = {i + '.txt': base_blob for i in ids}
        base_tree = tree(repo, base_blobs)
        base_commit = oid(repo, 'commit-tree', base_tree, data=b'owned synthetic base\n')
        git(repo, 'update-ref', 'refs/heads/base', base_commit)
        final_blobs = dict(base_blobs)
        operations = []
        identities = []
        for index, identifier in enumerate(ids):
            payload = (identifier.encode() * 63 + b'\n') * (size // 64)
            assert len(payload) == size
            content = b'base\n' + payload
            blob = oid(repo, 'hash-object', '-w', '--stdin', data=content)
            source_blobs = {**base_blobs, identifier + '.txt': blob}
            source_tree = tree(repo, source_blobs)
            commit = oid(repo, 'commit-tree', source_tree, '-p', base_commit,
                         data=f'owned fixed patch {identifier}\n'.encode())
            git(repo, 'update-ref', f'refs/heads/operation-{identifier}', commit)
            patch = git(repo, 'diff', '--binary', '--no-ext-diff', '--no-textconv',
                        '--no-renames', base_commit, commit, '--')
            (directory / f'{identifier}.patch').write_bytes(patch)
            dependencies = [ids[index - 1]] if family == 'dependency-chain' and index else []
            operations.append({'instanceId': identifier, 'attemptId': identifier + '-attempt',
                               'source': {'kind': 'commit', 'revision': commit},
                               'dependencies': dependencies, 'uncertainPaths': [],
                               'declaredWrites': [identifier + '.txt']})
            identities.append({'instanceId': identifier, 'parentCommit': base_commit,
                               'sourceCommit': commit, 'sourceTree': source_tree,
                               'path': identifier + '.txt', 'gitChangeStatus': 'M',
                               'payloadBytes': len(payload), 'contentBytes': len(content),
                               'contentSha256': sha(content), 'blobId': blob,
                               'patchFile': f'{identifier}.patch', 'patchBytes': len(patch),
                               'patchSha256': sha(patch), 'dependencies': dependencies})
            final_blobs[identifier + '.txt'] = blob
        final_tree = tree(repo, final_blobs)
        request = {'gitRuntimeRequestVersion': '0.1.0-alpha', 'repository': str(repo),
                   'baseRevision': base_commit, 'expectedFinalTree': final_tree,
                   'order': ids, 'operations': operations}
        save(directory / 'runtime-request-candidate.json', request)
        replay = {'gitAnalysisRequestVersion': '0.1.0-alpha', 'repository': str(repo),
                  'baseRevision': base_commit,
                  'operations': [{k: v for k, v in op.items() if k != 'declaredWrites'}
                                 for op in operations]}
        save(directory / 'replay-request-candidate.json', replay)
        aggregate = sum(i['patchBytes'] for i in identities)
        exclusions = []
        if aggregate > 262144:
            exclusions.append({'validator': 'git_runtime._prepare', 'reason': 'runtime patch limit exceeded',
                               'actualBytes': aggregate, 'capBytes': 262144})
        if aggregate > 1048576:
            exclusions.append({'validator': 'git_replay._patches', 'reason': 'aggregate patch bytes exceed 1 MiB',
                               'actualBytes': aggregate, 'capBytes': 1048576})
        orders = [list(p) for p in itertools.permutations(ids)
                  if all(p.index(dep) < p.index(op['instanceId'])
                         for op in operations for dep in op['dependencies'])]
        blocks.append({'blockId': name, 'family': family, 'operationCount': count,
                       'payloadBytesPerOperation': size, 'baseCommit': base_commit,
                       'baseTree': base_tree, 'expectedFinalTree': final_tree,
                       'expectedTreeMethod': 'Direct construction from owned declared final file blobs; no patch execution or runtime verification.',
                       'operationIdentities': identities, 'plannedOrder': ids,
                       'dependencyRespectingOrders': orders, 'aggregatePatchBytes': aggregate,
                       'directNumericExclusions': exclusions,
                       'admissionStatus': 'not-tested', 'measurementExecuted': False,
                       'runtimeExecuted': False, 'grantIssued': False,
                       'invariants': ['All source commits have the common immutable base as parent.',
                                      'Each source differs from base in exactly one distinct ordinary text file.',
                                      'Declared dependency chain is an ordering control, not cumulative commit ancestry.',
                                      'Every planned block is retained, including directly excluded sizes.']})

source_paths = ['agent_braid/git_adapter.py', 'agent_braid/git_replay.py',
                'agent_braid/git_runtime.py', 'agent_braid/runtime_scheduler.py',
                'tests/test_git_runtime.py', 'specs/022-m4-utility-followup/measurement-protocol.md',
                'specs/022-m4-utility-followup/workload-manifest-candidate.json']
packet = {'version': 'm4-owned-fixture-preparation-draft-v2',
          'status': 'draft-preflight-blocked-human-review-pending',
          'boundary': 'External private object preparation only; no validated evidence, runtime admission, grant, measurement, or T002 instrumentation.',
          'sourceCheckoutCommit': oid(SOURCE, 'rev-parse', 'HEAD'),
          'sourceHashes': {p: sha((SOURCE / p).read_bytes()) for p in source_paths},
          'preparationScriptSha256': sha(Path(__file__).read_bytes()),
          'environment': {'python': sys.version, 'executable': sys.executable,
                          'git': git(ROOT, '--version').decode().strip(),
                          'os': platform.platform(), 'machine': platform.machine(),
                          'gitIdentityDate': '2000-01-01T00:00:00+00:00',
                          'gitConfig': 'No system/global config or templates; hooks disabled.',
                          'dependenciesInstalled': False},
          'pinnedContractCaps': {'runtime': {'operations': 4, 'changedPaths': 16, 'patchBytes': 262144,
                                  'wallSeconds': 60, 'gitCommands': 256, 'outputBytes': 8388608,
                                  'commandOutputBytes': 2097152, 'scratchBytes': 67108864,
                                  'childAddressSpaceBytes': None, 'recordBytes': 1048576, 'workers': 4},
                                 'replay': {'operations': 4, 'changedPaths': 64, 'patchBytes': 1048576,
                                   'wallSeconds': 120, 'gitCommands': 512, 'outputBytes': 16777216,
                                   'commandOutputBytes': 8388608, 'scratchBytes': 67108864},
                                 'adapterCommandOutputBytes': 8000000},
          'capsReconciliation': 'Declared numerics manually compared by Luna against bound source constants; not runtime-read.',
          'unobserved': ['Runtime admission, output/scratch/time/command budget consumption and actual final-tree verification are not executed.'],
          'blocks': blocks}
save(ROOT / 'fixture-manifest-draft.json', packet)
print(json.dumps({'blocksGenerated': len(blocks),
                  'directNumericExclusions': [b['blockId'] for b in blocks if b['directNumericExclusions']],
                  'manifest': str(ROOT / 'fixture-manifest-draft.json'), 'runtimeExecuted': False}))
