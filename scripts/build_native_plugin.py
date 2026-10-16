#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Assemble an offline native plugin. Only this build step downloads dependencies."""
from __future__ import annotations
import argparse
import hashlib
from importlib import metadata
import json
import os
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

VERSION = '0.1.0-alpha.1'


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


def assemble(output, cache, *, platforms=None, allow_dirty=False):
    output = Path(output).resolve()
    if output.exists() or output.is_relative_to(ROOT):
        raise ValueError('Build into a new directory outside the source checkout')
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
    if dirty and not allow_dirty:
        raise ValueError('Commit the exact candidate before building, or explicitly mark an --allow-dirty engineering artifact')
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
            runtime_provenance[platform] = {**entry, 'pythonVersion': lock['pythonVersion'], 'build': lock['build']}
            package_licenses[platform] = sorted([{'name': d.metadata['Name'], 'version': d.version,
                'license': d.metadata.get('License-Expression') or d.metadata.get('License', 'unknown'),
                'licenseFiles': [str(p) for p in (d.files or []) if 'license' in str(p).lower() or 'copying' in str(p).lower()]}
                for d in metadata.distributions(path=[str(site)])], key=lambda x: x['name'].lower())
        bundle = load_skill_bundle(source_checkout=True)
        for skill in bundle.skills:
            destination = plugin / 'skills' / skill.name / 'SKILL.md'
            destination.parent.mkdir(parents=True)
            destination.write_text(skill.content)
        shutil.copytree(ROOT / 'integrations/agent-braid/plugin/setup', plugin / 'skills/setup')
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
            'limits': ['Engineering package; no native conformance, publisher authentication or official approval implied']})
        # Corresponding tracked sources only; never package unrelated untracked local files.
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
        provenance_path = plugin / 'provenance.json'
        provenance = json.loads(provenance_path.read_text())
        source_archive = sources / f'agent-braid-{VERSION}-source.tar.gz'
        provenance['correspondingSource'] = {'path': 'sources/' + source_archive.name,
                                              'sha256': file_hash(source_archive)}
        _json(provenance_path, provenance)
        _json(plugin / 'package-inventory.json', {'schema': 'agent-braid-plugin-package/v1', 'version': VERSION,
                                                'files': inventory(plugin)})
        verify_package(plugin)
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
    args = parser.parse_args()
    print(json.dumps(assemble(args.output, args.cache, platforms=args.platform, allow_dirty=args.allow_dirty), indent=2))


if __name__ == '__main__':
    main()
