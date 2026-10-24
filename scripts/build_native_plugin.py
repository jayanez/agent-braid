#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Assemble an offline native plugin. Only this build step downloads dependencies."""
from __future__ import annotations
import argparse
import compileall
import hashlib
from importlib import metadata
import json
import os
import py_compile
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from agent_braid.plugin_package import file_hash, inventory, verify_package
from agent_braid.tooling_assets import load_skill_bundle

VERSION = '0.1.0-alpha.4'
DISTRIBUTION_ATTRIBUTES = '* -text -filter -ident\n'
WORKFLOWS_SOURCE = ROOT / 'integrations/agent-braid/plugin/workflows'
ENGINEERING_MARKER = 'ENGINEERING-ONLY.json'
ENGINEERING_MARKER_VALUE = {
    'schema': 'agent-braid-plugin-engineering-only/v1', 'component': 'workflows', 'releasable': False,
    'reason': 'The workflow component is excluded from default builds until the ADR 0024 amendment is adopted; '
              'this package shares the unchanged version string and is never a releasable identity'}


def copy_tracked_workflows(source, destination):
    """Copy only Git-tracked regular files; ignored, untracked and symlinked content never ships."""
    source = Path(source)
    listing = subprocess.check_output(['git', 'ls-files', '--cached', '-z', '--', '.'], cwd=source)
    names = sorted({os.fsdecode(raw) for raw in listing.split(b'\0') if raw})
    if not names:
        raise ValueError('The workflow source directory has no tracked files')
    root = source.resolve(strict=True)
    for name in names:
        path = source / name
        if path.is_symlink() or not path.is_file() or not path.resolve(strict=True).is_relative_to(root):
            raise ValueError(f'Workflow source {name} is not a tracked regular file')
    for name in names:
        target = Path(destination) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
        shutil.copymode(source / name, target)


PLUGIN_NAME = 'agent-braid'
SKILL_SUBSTITUTIONS = {f'agent-braid-{x}': x for x in ('analyze', 'plan', 'evidence', 'execute', 'recover')}
PACKAGED_SKILL_NAMES = frozenset(SKILL_SUBSTITUTIONS.values()) | {'setup'}
NAME_PATTERN = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')
PREFIXED_TOKEN = re.compile(r'(?<![A-Za-z0-9-])agent-braid-(?:analyze|plan|evidence|execute|recover)(?![A-Za-z0-9-])')
FRONTMATTER_NAME = re.compile(r'^name: (\S+)$', re.M)


def package_skill(content):
    """Apply only the declared SPEC-054 substitutions to one canonical skill body.

    Rewrites the frontmatter ``name`` and backtick-quoted sibling references."""
    head, separator, rest = content.partition('\n---\n')
    match = FRONTMATTER_NAME.search(head)
    if not content.startswith('---\n') or not separator or not match or match.group(1) not in SKILL_SUBSTITUTIONS:
        raise ValueError('Canonical skill frontmatter name is not in the substitution table')
    head = FRONTMATTER_NAME.sub(lambda m: 'name: ' + SKILL_SUBSTITUTIONS[m.group(1)], head, count=1)
    rest = re.sub(r'`(agent-braid-[a-z]+)`', lambda m: '`' + SKILL_SUBSTITUTIONS.get(m.group(1), m.group(1)) + '`', rest)
    return head + separator + rest


def check_package_names(staging):
    """Fail unless every SPEC-054 packaged name matches the naming policy.

    ``staging`` is the marketplace root holding ``plugins/agent-braid``."""
    staging = Path(staging)
    plugin = staging / 'plugins' / PLUGIN_NAME

    def load(path):
        return json.loads(path.read_text())

    def require(condition, message):
        if not condition:
            raise ValueError('Naming policy violation: ' + message)

    require(load(plugin / 'plugin.json').get('name') == PLUGIN_NAME, 'plugin.json name')
    require(load(plugin / '.claude-plugin/plugin.json').get('name') == PLUGIN_NAME, '.claude-plugin/plugin.json name')
    for path in (staging / '.agents/plugins/marketplace.json', staging / '.claude-plugin/marketplace.json'):
        market = load(path)
        require(market.get('name') == PLUGIN_NAME, f'{path.name} marketplace name')
        require([x.get('name') for x in market.get('plugins', [])] == [PLUGIN_NAME], f'{path.name} entry name')
    for filename in ('mcp.json', '.mcp.json'):
        require(list(load(plugin / filename).get('mcpServers', {})) == [PLUGIN_NAME], f'{filename} server key')
    skills = plugin / 'skills'
    directories = sorted(x.name for x in skills.iterdir() if x.is_dir())
    require(set(directories) == PACKAGED_SKILL_NAMES, f'skill directories {directories}')
    for directory in directories:
        text = (skills / directory / 'SKILL.md').read_text()
        match = FRONTMATTER_NAME.search(text.partition('\n---\n')[0])
        require(match and match.group(1) == directory, f'skill {directory} frontmatter name differs from directory')
        require(NAME_PATTERN.match(directory) and len(directory) <= 64, f'skill name {directory} is not portable')
        for path in (skills / directory).rglob('*'):
            if path.is_file() and PREFIXED_TOKEN.search(path.read_text(errors='ignore')):
                require(False, f'prefixed skill token remains in {path.relative_to(plugin)}')


def extract_runtime(archive, destination, expected):
    if file_hash(archive) != expected:
        raise ValueError('Runtime archive SHA-256 mismatch')
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        if len(members) > 15000 or sum(x.size for x in members) > 512 * 1024 * 1024:
            raise ValueError('Runtime archive exceeds extraction bounds')
        if any(not x.name.startswith('python/') or x.isdev() or x.isfifo() for x in members):
            raise ValueError('Runtime archive has unexpected entries')
        # CLI/MCP never use bundled terminal capability databases. Some upstream
        # entries are cyclic symlinks; omit this unused subtree, never bypass data_filter.
        members = [item for item in members if not item.name.startswith('python/share/terminfo/')
                   and item.name.rstrip('/') != 'python/share/terminfo']
        stream.extractall(destination, members=members, filter='data')
    return destination / 'python'



def materialize_runtime_links(runtime):
    """Native managers may omit symlinks; ship contained regular alias files."""
    runtime = Path(runtime).resolve(strict=True)
    aliases = []
    for path in runtime.rglob('*'):
        if not path.is_symlink():
            continue
        target = path.resolve(strict=True)
        if not target.is_relative_to(runtime) or not target.is_file():
            raise ValueError('Runtime alias must target a contained regular file')
        aliases.append((path, target))
    result = []
    for path, target in aliases:
        result.append({'path': path.relative_to(runtime).as_posix(),
                       'target': target.relative_to(runtime).as_posix()})
        path.unlink()
        shutil.copy2(target, path)
    return result


def prepare_bytecode(runtime, platform):
    """Keep core Python subprocesses read-only after relocation/Git timestamp changes."""
    if sys.version_info[:2] != (3, 12):
        raise ValueError('Native CPython 3.12 builds require a Python 3.12 build interpreter')
    library = runtime / 'lib/python3.12'
    for path in library.rglob('__pycache__'):
        shutil.rmtree(path)
    if not compileall.compile_dir(str(library), quiet=2, force=True, optimize=0,
            ddir=f'/agent-braid/runtime/{platform}/lib/python3.12',
            invalidation_mode=py_compile.PycInvalidationMode.CHECKED_HASH):
        raise ValueError('Could not precompile every bundled Python source')
    return {'mode': 'checked-hash', 'compiler': sys.version, 'optimization': 0,
            'reason': 'Core subprocesses use sys.executable without -B; hash caches survive Git/relocation mtimes'}


def _json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + '\n')


def _download(path, entry):
    if not path.exists():
        temporary = path.with_suffix('.partial')
        try:
            with urllib.request.urlopen(entry['url'], timeout=60) as source, temporary.open('xb') as target:
                size = 0
                while chunk := source.read(1024 * 1024):
                    size += len(chunk)
                    if size > 64 * 1024 * 1024:
                        raise ValueError('Runtime download exceeds archive limit')
                    target.write(chunk)
            if file_hash(temporary) != entry['sha256']:
                raise ValueError('Runtime archive SHA-256 mismatch')
            temporary.rename(path)
        finally:
            temporary.unlink(missing_ok=True)
    if file_hash(path) != entry['sha256']:
        raise ValueError('Cached runtime SHA-256 mismatch')


def verify_engineering_marker(plugin):
    """The workflow directory and the engineering-only marker exist together or not at all."""
    plugin = Path(plugin)
    marker = plugin / ENGINEERING_MARKER
    present = (plugin / 'workflows').exists()
    if present != marker.is_file() or (present and json.loads(marker.read_text()) != ENGINEERING_MARKER_VALUE):
        raise ValueError('Workflow component and engineering-only marker disagree')


def assemble(output, cache, *, platforms=None, allow_dirty=False, include_workflows=False):
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise ValueError('Build into a new directory outside the source checkout')
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
    if dirty and not allow_dirty:
        raise ValueError('Commit the exact candidate before building, or explicitly mark an --allow-dirty engineering artifact')
    if include_workflows and not WORKFLOWS_SOURCE.is_dir():
        raise ValueError('The workflow source directory is missing')
    candidate = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    lock = json.loads((ROOT / 'integrations/agent-braid/plugin/runtime-lock.json').read_text())
    selected = platforms or list(lock['platforms'])
    if set(selected) - set(lock['platforms']):
        raise ValueError('Unknown runtime platform')
    cache = Path(cache).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.plugin-build-', dir=output.parent) as name:
        staging = Path(name)
        # Git marketplaces must retain wheel RECORD/CPython CRLF bytes exactly.
        (staging / '.gitattributes').write_text(DISTRIBUTION_ATTRIBUTES)
        plugin = staging / 'plugins/agent-braid'
        plugin.mkdir(parents=True)
        wheels = staging / 'wheels'
        subprocess.run([sys.executable, '-m', 'build', '--wheel', '--outdir', str(wheels), str(ROOT)], check=True)
        wheel = next(wheels.glob('*.whl'))
        runtime_provenance = {}
        package_licenses = {}
        for platform in selected:
            entry = lock['platforms'][platform]
            archive = cache / f'{platform}.tar.gz'
            _download(archive, entry)
            extraction = staging / f'extract-{platform}'
            extraction.mkdir()
            runtime = extract_runtime(archive, extraction, entry['sha256'])
            target = plugin / 'runtime' / platform
            target.parent.mkdir(exist_ok=True)
            shutil.move(str(runtime), target)
            site = target / 'lib/python3.12/site-packages'
            # Runtime archives include pip for general use; product startup never installs packages.
            for path in site.glob('pip*'):
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            command = [sys.executable, '-m', 'pip', '--isolated', 'install', '--no-compile', '--only-binary=:all:',
                       '--implementation', 'cp', '--python-version', '3.12', '--abi', 'cp312', '--abi', 'abi3',
                       '--target', str(site), '--require-hashes', '-r', str(ROOT / 'requirements-native-plugin.txt')]
            for wheel_platform in entry['wheelPlatforms']:
                command += ['--platform', wheel_platform]
            subprocess.run(command, check=True)
            subprocess.run([sys.executable, '-m', 'pip', '--isolated', 'install', '--no-deps', '--no-compile',
                            '--target', str(site), str(wheel)], check=True)
            aliases = materialize_runtime_links(target)
            bytecode = prepare_bytecode(target, platform)
            runtime_provenance[platform] = {**entry, 'pythonVersion': lock['pythonVersion'], 'build': lock['build'], 'bytecode': bytecode, 'materializedAliases': aliases}
            package_licenses[platform] = sorted([{'name': d.metadata['Name'], 'version': d.version,
                'license': d.metadata.get('License-Expression') or d.metadata.get('License', 'unknown'),
                'licenseFiles': [str(p) for p in (d.files or []) if 'license' in str(p).lower() or 'copying' in str(p).lower()]}
                for d in metadata.distributions(path=[str(site)])], key=lambda x: x['name'].lower())
        bundle = load_skill_bundle(source_checkout=True)
        skill_provenance = []
        for skill in bundle.skills:
            packaged = package_skill(skill.content)
            destination = plugin / 'skills' / SKILL_SUBSTITUTIONS[skill.name] / 'SKILL.md'
            destination.parent.mkdir(parents=True)
            destination.write_text(packaged)
            skill_provenance.append({'canonicalName': skill.name, 'packagedName': SKILL_SUBSTITUTIONS[skill.name],
                'canonicalSha256': skill.sha256, 'packagedSha256': hashlib.sha256(packaged.encode()).hexdigest()})
        shutil.copytree(ROOT / 'integrations/agent-braid/plugin/setup', plugin / 'skills/setup')
        if include_workflows:
            # Pre-adoption guard: Claude-only component, opt-in, never a releasable identity.
            copy_tracked_workflows(WORKFLOWS_SOURCE, plugin / 'workflows')
            _json(plugin / ENGINEERING_MARKER, ENGINEERING_MARKER_VALUE)
        launch = plugin / 'launch'
        launch.write_text('''#!/bin/sh
set -eu
plugin_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
case "$(uname -s):$(uname -m)" in
  Darwin:arm64) plugin_platform=macos-arm64 ;;
  Linux:x86_64) plugin_platform=linux-x86_64 ;;
  *) echo 'Agent Braid: unsupported platform; use a supported local host' >&2; exit 2 ;;
esac
plugin_python="$plugin_root/runtime/$plugin_platform/bin/python3.12"
[ -x "$plugin_python" ] || { echo 'Agent Braid: runtime missing; reinstall the native plugin' >&2; exit 2; }
export AGENT_BRAID_PLUGIN_ROOT="$plugin_root"
exec "$plugin_python" -I -B -m agent_braid "$@"
''')
        launch.chmod(0o755)
        common = {'name': 'agent-braid', 'version': VERSION, 'description': 'Inspect agent interactions with evidence and explicit workspace boundaries.',
                  'author': {'name': 'Juan Antonio Yáñez García'}, 'license': 'AGPL-3.0-only',
                  'homepage': 'https://github.com/jayanez/agent-braid', 'repository': 'https://github.com/jayanez/agent-braid'}
        _json(plugin / 'plugin.json', {'$schema': 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json', **common,
            'extensions': {'com.openai': {'onboardingSkill': './skills/setup/SKILL.md', 'requires_local_executor': True,
                'interface': {'displayName': 'Agent Braid', 'shortDescription': 'Inspect agent interactions',
                    'longDescription': common['description'], 'developerName': common['author']['name'],
                    'category': 'Developer Tools', 'websiteURL': common['homepage'],
                    'supportURL': common['homepage'] + '/issues',
                    'privacyPolicyURL': common['homepage'] + '/blob/develop/docs/tooling/PLUGIN_PRIVACY.md',
                    'termsOfServiceURL': common['homepage'] + '/blob/develop/LICENSE',
                    'composerIcon': './assets/icon.svg', 'logo': './assets/icon.svg'}}}})
        _json(plugin / '.claude-plugin/plugin.json', common)
        args = ['plugin', 'serve', '--plugin-root']
        _json(plugin / 'mcp.json', {'$schema': 'https://agent-plugins.org/schemas/1.0.0/mcp.schema.json',
            'mcpServers': {'agent-braid': {'type': 'stdio', 'command': './launch',
                'args': ['plugin', 'serve']}}})
        _json(plugin / '.mcp.json', {'mcpServers': {'agent-braid': {'command': '${CLAUDE_PLUGIN_ROOT}/launch',
            'args': args + ['${CLAUDE_PLUGIN_ROOT}']}}})
        _json(staging / '.agents/plugins/marketplace.json', {'name': 'agent-braid', 'interface': {'displayName': 'Agent Braid'},
            'plugins': [{'name': 'agent-braid', 'source': {'source': 'local', 'path': './plugins/agent-braid'},
                'policy': {'installation': 'AVAILABLE', 'authentication': 'ON_USE'}, 'category': 'Developer Tools'}]})
        _json(staging / '.claude-plugin/marketplace.json', {'name': 'agent-braid', 'owner': common['author'],
            'plugins': [{'name': 'agent-braid', 'source': './plugins/agent-braid', 'description': common['description'], 'version': VERSION}]})
        shutil.copytree(ROOT / 'LICENSES', plugin / 'LICENSES')
        for filename in ('LICENSE', 'NOTICE', 'TRADEMARKS.md'):
            shutil.copyfile(ROOT / filename, plugin / filename)
        shutil.copyfile(ROOT / 'docs/tooling/PLUGIN_PACKAGE_README.md', plugin / 'README.md')
        (plugin / 'assets').mkdir()
        shutil.copyfile(ROOT / 'integrations/agent-braid/plugin/icon.svg', plugin / 'assets/icon.svg')
        _json(plugin / 'provenance.json', {'schema': 'agent-braid-plugin-provenance/v1', 'version': VERSION,
            'sourceCommit': candidate, 'sourceDirty': dirty, 'wheelSha256': file_hash(wheel),
            'dependencyLockSha256': file_hash(ROOT / 'requirements-native-plugin.txt'), 'runtimes': runtime_provenance,
            'dependencies': package_licenses, 'canonicalSkills': bundle.inventory(),
            'skillNaming': {'policy': 'SPEC-054', 'substitutions': SKILL_SUBSTITUTIONS, 'skills': skill_provenance},
            'limits': ['Engineering package; no native conformance, publisher authentication or official approval implied']})
        if include_workflows:
            provenance_path = plugin / 'provenance.json'
            provenance = json.loads(provenance_path.read_text())
            provenance['engineeringOnly'] = {'component': 'workflows', 'marker': ENGINEERING_MARKER}
            _json(provenance_path, provenance)
        # Corresponding tracked sources only; never package unrelated untracked local files.
        # Decision: the default (non-opt-in) source archive keeps the tracked workflow sources. The AGPL
        # corresponding-source obligation covers the repository at this commit, and the files are inert
        # source text there; only the plugin tree (plugin/workflows) is gated by --include-workflows.
        sources = staging / 'sources'
        sources.mkdir()
        paths = subprocess.check_output(['git', 'ls-files', '--cached', '-z'], cwd=ROOT).split(b'\0')
        with tarfile.open(sources / f'agent-braid-{VERSION}-source.tar.gz', 'w:gz') as archive:
            for raw in sorted(set(paths)):
                if raw:
                    relative = os.fsdecode(raw)
                    path = ROOT / relative
                    if path.is_file() and not path.is_symlink():
                        archive.add(path, arcname=relative, recursive=False)
        check_package_names(staging)
        provenance_path = plugin / 'provenance.json'
        provenance = json.loads(provenance_path.read_text())
        source_archive = sources / f'agent-braid-{VERSION}-source.tar.gz'
        provenance['correspondingSource'] = {'path': 'sources/' + source_archive.name,
                                              'sha256': file_hash(source_archive)}
        _json(provenance_path, provenance)
        _json(plugin / 'package-inventory.json', {'schema': 'agent-braid-plugin-package/v1', 'version': VERSION,
                                                'files': inventory(plugin)})
        verify_package(plugin)
        verify_engineering_marker(plugin)
        shutil.rmtree(wheels)
        for path in staging.glob('extract-*'):
            shutil.rmtree(path)
        staging.rename(output)
    return {'status': 'built', 'marketplace': str(output), 'plugin': str(output / 'plugins/agent-braid'),
            'version': VERSION, 'platforms': selected, 'sourceDirty': dirty}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--platform', choices=('macos-arm64', 'linux-x86_64'), action='append')
    parser.add_argument('--allow-dirty', action='store_true', help='explicit engineering artifact; never a releasable source identity')
    parser.add_argument('--include-workflows', action='store_true',
                        help='explicit opt-in: add the Claude-only workflow directory; the artifact is engineering-only')
    args = parser.parse_args()
    print(json.dumps(assemble(args.output, args.cache, platforms=args.platform, allow_dirty=args.allow_dirty,
                              include_workflows=args.include_workflows), indent=2))


if __name__ == '__main__':
    main()
