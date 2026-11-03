# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-068 T004: the native build emits the OpenCode package without touching host-read files (D12)."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock

from agent_braid.plugin_package import inventory, verify_package
from scripts import build_native_plugin
from scripts.build_native_plugin import OPENCODE_SOURCE, VERSION, assemble, check_package_names, opencode_package_json

OPENCODE_FILES = {'package.json', 'opencode/index.js'}
HOST_READ_EXACT = ('plugin.json', '.claude-plugin/plugin.json', 'mcp.json', '.mcp.json', 'launch')
MARKETPLACES = ('.agents/plugins/marketplace.json', '.claude-plugin/marketplace.json')
_REAL_RUN = subprocess.run


def _fake_run(command, **options):
    """Stand in for the wheel build and pip installs; Git calls stay real. No network is used."""
    command = [str(x) for x in command]
    if command[0] == 'git':
        return _REAL_RUN(command, **options)
    if '--wheel' in command:
        outdir = Path(command[command.index('--outdir') + 1])
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / 'agent_braid-0-py3-none-any.whl').write_bytes(b'fixture wheel')


def _fake_extract(archive, destination, expected):
    runtime = Path(destination) / 'python'
    (runtime / 'lib/python3.12/site-packages').mkdir(parents=True)
    (runtime / 'bin').mkdir()
    (runtime / 'bin/python3.12').write_bytes(b'#!fixture\n')
    return runtime


def host_read_differences(left, right):
    """Names of files Codex or Claude Code read that differ between two built marketplaces."""
    left, right = Path(left), Path(right)
    plugin = 'plugins/agent-braid/'
    names = [plugin + x for x in HOST_READ_EXACT] + list(MARKETPLACES)
    names += [plugin + x for x in inventory(left / plugin) if x.startswith(('skills/', 'runtime/'))]
    names += [plugin + x for x in inventory(right / plugin) if x.startswith(('skills/', 'runtime/'))]
    return sorted(x for x in set(names)
                  if not (left / x).is_file() or not (right / x).is_file() or (left / x).read_bytes() != (right / x).read_bytes())


class OpenCodeBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        cls.base = Path(cls.scratch.name)
        cls.with_target = cls._build(cls.base / 'with')
        cls.without_target = cls._build(cls.base / 'without', include_opencode=False)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    @classmethod
    def _build(cls, output, **options):
        with mock.patch.object(build_native_plugin.subprocess, 'run', _fake_run), \
                mock.patch.object(build_native_plugin, '_download'), \
                mock.patch.object(build_native_plugin, 'extract_runtime', _fake_extract), \
                mock.patch.object(build_native_plugin, 'prepare_bytecode', return_value={'mode': 'fixture'}):
            return Path(assemble(output, cls.base / 'cache', platforms=['macos-arm64'], allow_dirty=True,
                                 **options)['marketplace'])

    @property
    def plugin(self):
        return self.with_target / 'plugins/agent-braid'

    def copy_marketplace(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        copy = Path(directory.name) / 'market'
        shutil.copytree(self.with_target, copy, symlinks=True)
        return copy

    def test_package_json_is_exactly_the_contract_and_declares_no_dependencies(self):
        value = json.loads((self.plugin / 'package.json').read_text())
        self.assertEqual(value, {'name': 'agent-braid', 'version': VERSION, 'type': 'module', 'private': True,
                                 'license': 'AGPL-3.0-only', 'exports': {'.': './opencode/index.js'}})
        self.assertFalse([key for key in value if 'ependenc' in key])

    def test_entry_is_the_one_tracked_source(self):
        self.assertEqual((self.plugin / 'opencode/index.js').read_bytes(), OPENCODE_SOURCE.read_bytes())

    def test_inventory_provenance_and_verification_cover_the_new_files(self):
        self.assertEqual(verify_package(self.plugin)['status'], 'verified')
        files = json.loads((self.plugin / 'package-inventory.json').read_text())['files']
        provenance = json.loads((self.plugin / 'provenance.json').read_text())
        self.assertEqual(provenance['hosts'], ['codex', 'claude', 'opencode'])

    def test_d12_host_read_files_are_byte_identical_without_the_target(self):
        self.assertEqual(host_read_differences(self.with_target, self.without_target), [])
        # Manifests, MCP configs, launcher, skills and runtime are really compared, not an empty set.
        self.assertTrue(any(x.startswith('skills/') for x in inventory(self.plugin)))
        self.assertTrue(any(x.startswith('runtime/') for x in inventory(self.plugin)))

    def test_d12_inventory_and_provenance_differ_only_by_added_entries(self):
        before, after = inventory(self.without_target / 'plugins/agent-braid'), inventory(self.plugin)
        self.assertEqual(set(after) - set(before), OPENCODE_FILES)
        self.assertEqual(set(before) - set(after), set())
        for name in set(before) - {'provenance.json'}:
            self.assertEqual(before[name], after[name], name)
        old = json.loads((self.without_target / 'plugins/agent-braid/provenance.json').read_text())
        new = json.loads((self.plugin / 'provenance.json').read_text())
        self.assertNotIn('hosts', old)
        # The gzip timestamp makes the source archive digest differ between any two builds.
        for value in (old, new):
            value['correspondingSource'].pop('sha256')
        self.assertEqual({key: value for key, value in new.items() if key != 'hosts'}, old)

    def test_build_without_the_target_emits_no_opencode_file(self):
        plugin = self.without_target / 'plugins/agent-braid'
        self.assertFalse(any((plugin / x).exists() for x in OPENCODE_FILES))
        self.assertEqual(verify_package(plugin)['status'], 'verified')

    def test_negative_wrong_package_name(self):
        market = self.copy_marketplace()
        path = market / 'plugins/agent-braid/package.json'
        path.write_text(json.dumps({**json.loads(path.read_text()), 'name': 'agent-braid-plugin'}))
        with self.assertRaisesRegex(ValueError, 'package.json name'):
            check_package_names(market, opencode=True)

    def test_negative_declared_dependency(self):
        market = self.copy_marketplace()
        path = market / 'plugins/agent-braid/package.json'
        for key in ('dependencies', 'devDependencies', 'optionalDependencies', 'peerDependencies'):
            with self.subTest(key):
                path.write_text(json.dumps({**opencode_package_json(), key: {'left-pad': '1.3.0'}}))
                with self.assertRaisesRegex(ValueError, 'declares dependencies'):
                    check_package_names(market, opencode=True)

    def test_negative_manifest_off_contract(self):
        market = self.copy_marketplace()
        path = market / 'plugins/agent-braid/package.json'
        for change in ({'exports': {'.': './index.js'}}, {'type': 'commonjs'}, {'private': False}, {'main': 'x.js'}):
            with self.subTest(change):
                path.write_text(json.dumps({**opencode_package_json(), **change}))
                with self.assertRaisesRegex(ValueError, 'differs from the contract'):
                    check_package_names(market, opencode=True)

    def test_negative_missing_package_or_entry(self):
        market = self.copy_marketplace()
        (market / 'plugins/agent-braid/opencode/index.js').unlink()
        with self.assertRaisesRegex(ValueError, 'index.js is missing'):
            check_package_names(market, opencode=True)
        (market / 'plugins/agent-braid/package.json').unlink()
        with self.assertRaisesRegex(ValueError, 'package.json is missing'):
            check_package_names(market, opencode=True)
        check_package_names(market)  # a target-less package needs neither file

    def test_negative_symlink_in_the_plugin_directory(self):
        market = self.copy_marketplace()
        (market / 'plugins/agent-braid/opencode/alias.js').symlink_to('index.js')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            check_package_names(market, opencode=True)

    def test_negative_drift_in_a_host_read_file(self):
        market = self.copy_marketplace()
        for name in ('mcp.json', '.mcp.json', 'launch', 'skills/plan/SKILL.md'):
            with self.subTest(name):
                path = market / 'plugins/agent-braid' / name
                original = path.read_bytes()
                self.addCleanup(path.write_bytes, original)
                path.write_bytes(original + b'\n')
                self.assertEqual(host_read_differences(market, self.without_target), ['plugins/agent-braid/' + name])
                with self.assertRaisesRegex(ValueError, 'inventory changed'):
                    verify_package(market / 'plugins/agent-braid')
                path.write_bytes(original)
        self.assertEqual(host_read_differences(market, self.without_target), [])

    def test_negative_untracked_symlinked_or_missing_entry_source_never_ships(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            source = root / 'index.js'
            source.write_text('export default {}\n')
            (root / 'real.js').write_text('export default {}\n')
            with mock.patch.object(build_native_plugin, 'OPENCODE_SOURCE', source):
                with self.subTest('untracked'), self.assertRaisesRegex(ValueError, 'tracked regular file'):
                    build_native_plugin.copy_tracked_opencode_entry(root / 'out/index.js')
                subprocess.run(['git', '-C', str(root), 'add', '--', 'index.js', 'real.js'], check=True)
                source.unlink()
                source.symlink_to('real.js')  # tracked-looking and resolvable: only the symlink check can refuse it
                with self.subTest('symlink'), self.assertRaisesRegex(ValueError, 'tracked regular file'):
                    build_native_plugin.copy_tracked_opencode_entry(root / 'out/index.js')
                source.unlink()
                with self.subTest('missing'), self.assertRaisesRegex(ValueError, 'tracked regular file'):
                    build_native_plugin.copy_tracked_opencode_entry(root / 'out/index.js')


if __name__ == '__main__':
    unittest.main()
