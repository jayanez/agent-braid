# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only OpenCode collision diagnosis for ``plugin doctor --host opencode`` (SPEC-068 T005).

Scans the documented OpenCode skill discovery locations and configuration files. It never
writes, never contacts the network, grants nothing and does not reload the host. Precedence
(lowest to highest) is the order observed in SPEC-068 T002 row 02: home ``.claude``, home
``.agents``, OpenCode config ``skills``, project ``.claude``, ``.agents``, ``.opencode`` and
explicit ``skills`` config entries; within one kind a nearer directory is listed later.
Ordering of ancestors below the project directory was not observed and is an assumption.
"""
from __future__ import annotations

from collections import Counter
import os
from pathlib import Path

from . import jsonc

SKILL_IDS = ('analyze', 'plan', 'evidence', 'execute', 'recover', 'setup')
SERVER_NAME = 'agent-braid'
LEGACY_PREFIX = 'agent-braid-'
_CONFIG_NAMES = ('opencode.json', 'opencode.jsonc')
_MAX_CONFIG_BYTES = 1 << 20


def _chain(project: Path) -> list[Path]:
    """Directories from the Git root (or, without one, the filesystem root) down to ``project``."""
    chain = [project]
    for candidate in project.parents:
        if (chain[-1] / '.git').exists():
            break
        chain.append(candidate)
    return list(reversed(chain))


def _global_directory() -> Path:
    """OpenCode global directory; T002 row 09: a relative XDG_CONFIG_HOME is used as given."""
    value = os.environ.get('XDG_CONFIG_HOME', '')
    return (Path(value) if value else Path.home() / '.config') / 'opencode'


def _skill_directories(chain: list[Path] | None) -> list[tuple[str, Path]]:
    home = Path.home()
    found = [('home-claude', home / '.claude' / 'skills'), ('home-agents', home / '.agents' / 'skills'),
             ('opencode-config', _global_directory() / 'skills')]
    for source, relative in (('project-claude', '.claude/skills'), ('project-agents', '.agents/skills'),
                             ('project-opencode', '.opencode/skills')):
        found += [(source, directory / relative) for directory in chain or ()]
    return found


def _config_files(chain: list[Path] | None) -> list[Path]:
    directories = [_global_directory()]
    for directory in chain or ():
        directories += [directory, directory / '.opencode']
    return [directory / name for directory in directories for name in _CONFIG_NAMES]


def _read_config(path: Path) -> tuple[dict, dict | None]:
    """Return ``(report, parsed)``; parsed is None when absent or unusable."""
    try:
        if not path.is_file():
            return {'path': str(path), 'status': 'absent'}, None
        if path.stat().st_size > _MAX_CONFIG_BYTES:
            return {'path': str(path), 'status': 'unreadable', 'error': 'file too large'}, None
        parsed = jsonc.parse(path.read_bytes().decode('utf-8'))
    except OSError as exc:
        return {'path': str(path), 'status': 'unreadable', 'error': str(exc)}, None
    except (UnicodeError, jsonc.JsoncError) as exc:
        return {'path': str(path), 'status': 'invalid', 'error': str(exc)}, None
    if not isinstance(parsed, dict):
        return {'path': str(path), 'status': 'invalid', 'error': 'the configuration root must be an object'}, None
    return {'path': str(path), 'status': 'ok'}, parsed


def _explicit_skill_paths(config: Path, parsed: dict) -> list[Path]:
    value = parsed.get('skills')
    entries = value.get('paths') if isinstance(value, dict) else value
    if not isinstance(entries, list):
        return []
    paths = []
    for entry in entries:
        if isinstance(entry, str) and entry:
            try:
                path = Path(entry).expanduser()
            except RuntimeError:
                continue
            paths.append(path if path.is_absolute() else config.parent / path)
    return paths


def _list_skills(directory: Path) -> list[tuple[str, Path]]:
    try:
        return sorted((child.name, child / 'SKILL.md') for child in directory.iterdir()
                      if (child / 'SKILL.md').is_file())
    except (OSError, ValueError):
        return []


def _server_differences(entry: object, plugin_root: Path | None) -> list[str]:
    """Names of the semantic fields in which ``entry`` differs from the plugin's own value."""
    if not isinstance(entry, dict):
        return ['type']
    command = entry.get('command')
    root = command[4] if isinstance(command, list) and len(command) == 5 and isinstance(command[4], str) else None
    # Without a known plugin root only the self-consistency of the command is checked.
    expected_root = str(plugin_root) if plugin_root else root
    expected = ([f'{expected_root}/launch', 'plugin', 'serve', '--plugin-root', expected_root]
                if expected_root else None)
    checks = (('type', entry.get('type') == 'local'), ('command', expected is not None and command == expected),
              ('codemode', entry.get('codemode') is False), ('protocol', entry.get('protocol') == 'legacy'))
    return [name for name, ok in checks if not ok]


def diagnose(project: Path | None = None, plugin_root: Path | None = None) -> dict:
    """Return the OpenCode findings; every failure to read is reported, none is raised."""
    project = Path(project).expanduser().absolute() if project is not None else None
    plugin_root = plugin_root.expanduser().absolute() if plugin_root else None
    chain = _chain(project) if project is not None else None
    definitions: dict[str, list[dict]] = {name: [] for name in SKILL_IDS}
    legacy: list[dict] = []
    seen: set = set()

    def scan(source: str, directory: Path) -> None:
        try:
            key = directory.resolve()
        except (OSError, RuntimeError, ValueError):
            return
        if key in seen:
            return
        seen.add(key)
        for skill_id, path in _list_skills(directory):
            item = {'source': source, 'path': str(path)}
            if skill_id in definitions:
                definitions[skill_id].append(item)
            elif skill_id.startswith(LEGACY_PREFIX) and skill_id[len(LEGACY_PREFIX):] in SKILL_IDS:
                legacy.append(dict(item, skillId=skill_id))

    for source, directory in _skill_directories(chain):
        scan(source, directory)

    reports, warnings, server = [], [], None
    for path in _config_files(chain):
        report, parsed = _read_config(path)
        if report['status'] != 'absent':
            reports.append(report)
        if parsed is not None:
            for directory in _explicit_skill_paths(path, parsed):
                scan('config-skills', directory)
            mcp = parsed.get('mcp')
            if isinstance(mcp, dict) and SERVER_NAME in mcp:
                server = (path, mcp[SERVER_NAME])
    counts = Counter(Path(r['path']).parent for r in reports)
    for directory in sorted(d for d, n in counts.items() if n == len(_CONFIG_NAMES)):
        warnings.append({'code': 'ambiguous-configuration', 'directory': str(directory),
                         'message': 'opencode.json and opencode.jsonc both exist; T002 row 09 observed both read, the later one winning per key'})

    findings = []
    for skill_id in SKILL_IDS:
        found = definitions[skill_id]
        if found:
            findings.append({'code': 'collision', 'skillId': skill_id, 'winner': found[-1], 'definitions': found})
    if legacy:
        findings.append({'code': 'duplicate-guidance', 'definitions': legacy})
    if server is not None:
        differing = _server_differences(server[1], plugin_root)
        if differing:
            findings.append({'code': 'server-collision', 'serverName': SERVER_NAME, 'configFile': str(server[0]),
                             'differingFields': differing})
    return {'host': 'opencode', 'readOnly': True, 'project': str(project) if project else None,
            'precedence': 'later definitions in each list win; the winner is the last one',
            'findings': findings, 'configFiles': reports, 'warnings': warnings}
