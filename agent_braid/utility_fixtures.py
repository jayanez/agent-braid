# SPDX-License-Identifier: AGPL-3.0-only
"""Reconstruct the pinned synthetic corpus without runtime admission or execution."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess

PREPARED_MANIFEST_SHA256 = 'ec8f36b21dd745df8443acd6035ff75a4b01bd61fd004470ce0315a655908734'
_BLOCK_HASHES = {
    'independent-2-1024': '9511c2722566b878dfa1b3505c0703a7a0a988af4681b1966666f6cbcb10f67a',
    'independent-2-65536': 'ab5148a45574c5f7394e7291a9eda3af7f8f45c85133df53ae3c903f2703a71e',
    'independent-2-1048576': 'f1676b6d3b23bf35730fc236f0aa500fa22d28346d065111b1ae9960bfcd2001',
    'independent-4-1024': '39218987488d825eb13252684f6206b82ada78b8fda2a98f6d531a656912d26d',
    'independent-4-65536': 'c423387611906bca78bdcde8bc7146e57288210693eda0403cef1f395110350d',
    'independent-4-1048576': '697029286b580ac8473ddfddc1d4f168091f614c33328144814324784728a765',
    'dependency-chain-4-1024': '745fe61797bf0e32c1ccb66e7ee886ecd2d7aa6e6574aa8ce6d1ee4f6b9ecc76',
    'dependency-chain-4-65536': 'e198831cb35f1d7deeb29fea78c4cb6d285eaf381e71da413c467ac46ff04658',
    'dependency-chain-4-1048576': '36fb9ad009280f9cea464de451dbce12dd2c23d6cd4d7e13172dce687af3aa1d',
}


class InvalidUtilityFixture(ValueError):
    """Prepared input or reconstructed objects differ from the reviewed corpus."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvalidUtilityFixture(message)


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False).encode()
    except (ValueError, TypeError, RecursionError) as exc:
        raise InvalidUtilityFixture('invalid fixture JSON') from exc


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _validate_block(block: object) -> dict:
    _require(type(block) is dict, 'fixture block must be an object')
    name = block.get('blockId')
    _require(type(name) is str and name in _BLOCK_HASHES, 'unknown fixture block')
    _require(_sha(_canonical(block)) == _BLOCK_HASHES[name], 'fixture identity hash mismatch')
    for field in ('operationCount', 'payloadBytesPerOperation', 'aggregatePatchBytes'):
        _require(type(block[field]) is int, 'fixture numeric values require integers')
    return deepcopy(block)


def validate_prepared_manifest(raw: bytes) -> dict:
    """Require exact archived V2 bytes; historical labels remain historical."""
    _require(type(raw) is bytes and len(raw) <= 65536, 'invalid prepared manifest bytes')
    _require(_sha(raw) == PREPARED_MANIFEST_SHA256, 'prepared manifest hash mismatch')
    try:
        value = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise InvalidUtilityFixture('invalid prepared manifest JSON') from exc
    _require(type(value) is dict and type(value.get('blocks')) is list, 'invalid inventory')
    blocks = [_validate_block(block) for block in value['blocks']]
    _require([b['blockId'] for b in blocks] == list(_BLOCK_HASHES), 'fixed inventory order mismatch')
    _require(sum(bool(b['directNumericExclusions']) for b in blocks) == 5,
             'fixed exclusion inventory mismatch')
    return value


def _destination(value: str | Path) -> Path:
    raw = Path(value).expanduser().absolute()
    _require(not os.path.lexists(raw), 'fixture destination already exists')
    _require(raw.name not in {'', '.', '..'}, 'unsafe fixture destination')
    try:
        parent = raw.parent.resolve(strict=True)
    except OSError as exc:
        raise InvalidUtilityFixture('fixture parent must exist') from exc
    _require(parent.is_dir(), 'fixture parent must be a directory')
    for ancestor in (parent, *parent.parents):
        _require(not os.path.lexists(ancestor / '.git') and not (
            (ancestor / 'HEAD').is_file() and (ancestor / 'objects').is_dir()
            and (ancestor / 'refs').is_dir()), 'fixture destination is inside source Git storage')
    return parent / raw.name


def _environment(root: Path) -> dict[str, str]:
    return {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'HOME': str(root),
            'LC_ALL': 'C', 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
            'GIT_CONFIG_COUNT': '0', 'GIT_DEFAULT_HASH': 'sha1',
            'GIT_NO_REPLACE_OBJECTS': '1', 'GIT_TERMINAL_PROMPT': '0',
            'GIT_AUTHOR_NAME': 'Agent Braid synthetic fixture preparation',
            'GIT_AUTHOR_EMAIL': 'fixtures@example.invalid',
            'GIT_COMMITTER_NAME': 'Agent Braid synthetic fixture preparation',
            'GIT_COMMITTER_EMAIL': 'fixtures@example.invalid',
            'GIT_AUTHOR_DATE': '2000-01-01T00:00:00+00:00',
            'GIT_COMMITTER_DATE': '2000-01-01T00:00:00+00:00'}


def _git(repo: Path, env: dict, *args: str, data: bytes | None = None) -> bytes:
    _require(data is None or len(data) <= 2 * 1024 * 1024, 'fixture Git input exceeds cap')
    try:
        result = subprocess.run(['git', '-C', str(repo), '-c', 'core.hooksPath=/dev/null',
                                 *args], env=env, input=data, capture_output=True,
                                timeout=30, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise InvalidUtilityFixture('fixture Git preparation failed') from exc
    # Fixed reviewed shapes bound normal command output; this is a captured-output
    # check, not a claim of pre-allocation protection for arbitrary executables.
    _require(len(result.stdout) + len(result.stderr) <= 2 * 1024 * 1024,
             'fixture Git captured output exceeds cap')
    return result.stdout


def build_fixture(block: dict, destination: str | Path) -> dict:
    """Build one reviewed block in a fresh private directory; preserve failures.

    Request files are preparation artifacts. Their existence grants no authority
    and excluded blocks remain excluded. No runtime or replay entrypoint is called.
    """
    selected = _validate_block(block)
    root = _destination(destination)
    try:
        root.mkdir(mode=0o700, exist_ok=False)
    except OSError as exc:
        raise InvalidUtilityFixture('fixture destination cannot be created') from exc
    env = _environment(root)
    repo = root / 'source'

    def oid(*args: str, data: bytes | None = None) -> str:
        return _git(repo, env, *args, data=data).decode().strip()

    def tree(blobs: dict[str, str]) -> str:
        data = b''.join(f'100644 blob {blob}\t{name}\n'.encode()
                        for name, blob in sorted(blobs.items()))
        return oid('mktree', data=data)

    _git(root, env, 'init', '--template=', '--quiet', str(repo))
    ids = selected['plannedOrder']
    blob = oid('hash-object', '-w', '--stdin', data=b'base\n')
    base_blobs = {i + '.txt': blob for i in ids}
    base_tree = tree(base_blobs)
    base = oid('commit-tree', base_tree, data=b'owned synthetic base\n')
    _require((base_tree, base) == (selected['baseTree'], selected['baseCommit']),
             'reconstructed base identity mismatch')
    _git(repo, env, 'update-ref', 'refs/heads/base', base)
    final_blobs = dict(base_blobs)
    operations, identities = [], []
    for index, identifier in enumerate(ids):
        size = selected['payloadBytesPerOperation']
        payload = (identifier.encode() * 63 + b'\n') * (size // 64)
        content = b'base\n' + payload
        blob = oid('hash-object', '-w', '--stdin', data=content)
        source_tree = tree({**base_blobs, identifier + '.txt': blob})
        commit = oid('commit-tree', source_tree, '-p', base,
                     data=f'owned fixed patch {identifier}\n'.encode())
        _git(repo, env, 'update-ref', f'refs/heads/operation-{identifier}', commit)
        patch = _git(repo, env, 'diff', '--binary', '--no-ext-diff', '--no-textconv',
                     '--no-renames', base, commit, '--')
        deps = [ids[index - 1]] if selected['family'] == 'dependency-chain' and index else []
        identity = {'instanceId': identifier, 'parentCommit': base, 'sourceCommit': commit,
                    'sourceTree': source_tree, 'path': identifier + '.txt',
                    'gitChangeStatus': 'M', 'payloadBytes': len(payload),
                    'contentBytes': len(content), 'contentSha256': 'sha256:' + _sha(content),
                    'blobId': blob, 'patchFile': identifier + '.patch',
                    'patchBytes': len(patch), 'patchSha256': 'sha256:' + _sha(patch),
                    'dependencies': deps}
        _require(identity == selected['operationIdentities'][index],
                 'reconstructed operation identity mismatch')
        (root / identity['patchFile']).write_bytes(patch)
        identities.append(identity)
        operations.append({'instanceId': identifier, 'attemptId': identifier + '-attempt',
                           'source': {'kind': 'commit', 'revision': commit},
                           'dependencies': deps, 'uncertainPaths': [],
                           'declaredWrites': [identifier + '.txt']})
        final_blobs[identifier + '.txt'] = blob
    expected = tree(final_blobs)
    _require(expected == selected['expectedFinalTree'], 'reconstructed final tree mismatch')
    _require(sum(i['patchBytes'] for i in identities) == selected['aggregatePatchBytes'],
             'reconstructed aggregate patch mismatch')
    # The read-only Git adapter requires an ordinary worktree whose HEAD has the
    # common base as ancestor. Materialize only owned base files during fixture
    # preparation; all approved immutable object identities remain unchanged.
    _git(repo, env, 'checkout', '--quiet', '--detach', base)
    runtime = {'gitRuntimeRequestVersion': '0.1.0-alpha', 'repository': str(repo),
               'baseRevision': base, 'expectedFinalTree': expected, 'order': ids,
               'operations': operations}
    replay = {'gitAnalysisRequestVersion': '0.1.0-alpha', 'repository': str(repo),
              'baseRevision': base,
              'operations': [{k: v for k, v in op.items() if k != 'declaredWrites'}
                             for op in operations]}
    result = {'blockId': selected['blockId'], 'repository': str(repo),
              'runtimeRequest': runtime, 'replayRequest': replay,
              'expectedFinalTree': expected, 'identities': identities,
              'directNumericExclusions': selected['directNumericExclusions']}
    for label, value in [('runtimeRequest', runtime), ('replayRequest', replay)]:
        path = root / (label + '.json')
        raw = _canonical(value)
        path.write_bytes(raw)
        result[label + 'Path'] = str(path)
        result[label + 'Sha256'] = _sha(raw)
    (root / 'prepared-block.json').write_bytes(_canonical(selected))
    return result
