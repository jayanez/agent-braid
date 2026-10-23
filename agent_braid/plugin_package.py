# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only verification of complete native plugin package inventories."""
from __future__ import annotations
import hashlib
import json
import stat
from pathlib import Path, PurePosixPath


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(part)
    return digest.hexdigest()


# Native hosts (e.g. Claude Code) record live processes as `.in_use/<pid>` files in
# the installed plugin root. They are host-owned and outside the package bytes.
HOST_MARKER_DIRECTORY = '.in_use'
HOST_MARKER_MAX_BYTES = 4096


def _is_host_marker(path, parts):
    if parts[0] != HOST_MARKER_DIRECTORY:
        return False
    if len(parts) == 1 and path.is_dir() and not path.is_symlink():
        return True
    if (len(parts) == 2 and parts[1].isdigit() and path.is_file() and not path.is_symlink()
            and path.stat().st_size <= HOST_MARKER_MAX_BYTES):
        return True
    raise ValueError('Unsupported entry in host marker directory')


def inventory(root):
    root = Path(root).resolve(strict=True)
    result = {}
    for index, path in enumerate(root.rglob('*')):
        if index >= 20000:
            raise ValueError('Package traversal exceeds its entry limit')
        relative = path.relative_to(root)
        name = relative.as_posix()
        if _is_host_marker(path, relative.parts):
            continue
        if name == 'package-inventory.json' or (path.is_dir() and not path.is_symlink()):
            continue
        if path.is_symlink():
            path.resolve(strict=True).relative_to(root)
            result[name] = {'link': path.readlink().as_posix()}
        elif path.is_file():
            result[name] = {'sha256': file_hash(path), 'sizeBytes': path.stat().st_size,
                            'executable': bool(path.stat().st_mode & 0o111)}
        else:
            raise ValueError('Unsupported file in plugin package')
    return result


def verify_package(root):
    root = Path(root).resolve(strict=True)
    path = root / 'package-inventory.json'
    if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Invalid package inventory')
    with path.open('rb') as stream:
        payload = stream.read(8 * 1024 * 1024 + 1)
    if len(payload) > 8 * 1024 * 1024:
        raise ValueError('Invalid package inventory size')
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError('Unknown package inventory')
    if not isinstance(value.get('version'), str) or not value['version'] or len(value['version']) > 128:
        raise ValueError('Invalid package inventory version')
    if value.get('schema') != 'agent-braid-plugin-package/v1' or not isinstance(value.get('files'), dict):
        raise ValueError('Unknown package inventory')
    if len(value['files']) > 20000:
        raise ValueError('Package inventory exceeds its file limit')
    for name in value['files']:
        parts = PurePosixPath(name)
        if parts.is_absolute() or '..' in parts.parts or str(parts) != name:
            raise ValueError('Unsafe package inventory path')
    if inventory(root) != value['files']:
        raise ValueError('Plugin package inventory changed; reinstall using the native manager')
    return {'status': 'verified', 'files': len(value['files']), 'version': value['version'],
            'limits': ['Byte inventory is not publisher authentication, native host acceptance or provider approval']}
