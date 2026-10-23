# SPDX-License-Identifier: AGPL-3.0-only
from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_braid.plugin_registry import MigrationRequired, RegistryError, load, plan_setup, apply, discover


class PluginRegistryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'state'
        self.repo = self.base / 'project one'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)

    def install(self, roots=None):
        preview = plan_setup(self.home, roots or [self.repo])
        return apply(self.home, preview, preview['previewDigest'])

    def test_preview_does_not_write_and_apply_preserves_stable_workspace(self):
        preview = plan_setup(self.home, [self.repo])
        self.assertFalse(self.home.exists())
        self.assertEqual(preview['registry']['workspaces'][0]['runtimeEnabled'], False)
        self.install()
        first = load(self.home)
        self.install()
        self.assertEqual(first, load(self.home))
        self.assertEqual((self.home.stat().st_mode & 0o777), 0o700)

    def test_changed_registry_and_wrong_digest_refuse_without_partial_addition(self):
        self.install()
        preview = plan_setup(self.home, [self.repo])
        with self.assertRaises(RegistryError):
            apply(self.home, preview, '0' * 64)
        path = self.home / 'registry.json'
        path.write_bytes(path.read_bytes() + b'\n')
        with self.assertRaises(RegistryError):
            apply(self.home, preview, preview['previewDigest'])

    def test_symlink_home_or_source_and_overlapping_roots_refuse(self):
        link = self.base / 'alias'
        link.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises(RegistryError):
            plan_setup(self.home, [link])
        with self.assertRaises(RegistryError):
            plan_setup(self.repo / 'state', [self.repo])
        target = self.base / 'real-state'
        target.mkdir()
        self.home.symlink_to(target, target_is_directory=True)
        with self.assertRaises(RegistryError):
            load(self.home)

    def test_discovery_is_bounded_deduplicated_and_does_not_follow_symlinks(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.repo, target_is_directory=True)
        found = discover(self.home, [self.base], current=self.repo)
        self.assertEqual([x['sourceRoot'] for x in found['candidates']], [str(self.repo)])
        limited = discover(self.home, [self.base], max_entries=1)
        self.assertTrue(limited['truncated'])
        self.assertFalse(self.home.exists())

    def test_removal_keeps_source_and_results(self):
        self.install()
        workspace = load(self.home)['workspaces'][0]
        result = Path(workspace['resultRoot']) / 'retained.txt'
        result.write_text('evidence')
        preview = plan_setup(self.home, [], remove=[workspace['workspaceId']])
        apply(self.home, preview, preview['previewDigest'])
        self.assertEqual(load(self.home)['workspaces'], [])
        self.assertEqual(result.read_text(), 'evidence')
        self.assertTrue(self.repo.exists())

    def test_many_files_and_cancellation_consume_a_bounded_entry_budget(self):
        import threading
        for i in range(40):
            (self.base / f'unrelated-{i}').write_text('x')
        found = discover(self.home, [self.base], max_entries=5)
        self.assertTrue(found['truncated'])
        self.assertLessEqual(found['inspectedEntries'], 5)
        cancelled = threading.Event()
        cancelled.set()
        stopped = discover(self.home, [self.base], cancelled=cancelled)
        self.assertTrue(stopped['cancelled'])
        self.assertEqual(stopped['inspectedEntries'], 0)

    def test_malformed_oversize_and_nonprivate_state_refuse(self):
        self.install()
        path = self.home / 'registry.json'
        for raw in (b'[]', b'{"schema": 1, "schema": 2}', b'x' * (256 * 1024 + 1)):
            path.write_bytes(raw)
            with self.assertRaises(RegistryError):
                load(self.home)
        path.chmod(0o644)
        with self.assertRaisesRegex(RegistryError, 'private'):
            load(self.home)

    def test_concurrent_setup_refuses_without_replacing_registry(self):
        import fcntl
        self.install()
        preview = plan_setup(self.home, [self.repo])
        before = (self.home / 'registry.json').read_bytes()
        with (self.home / 'registry.lock').open('rb') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RegistryError, 'Another setup'):
                apply(self.home, preview, preview['previewDigest'])
        self.assertEqual((self.home / 'registry.json').read_bytes(), before)

    def test_discovery_recognizes_worktrees_empty_and_unavailable_roots(self):
        empty = self.base / 'empty'; empty.mkdir()
        self.assertEqual(discover(self.home, [empty])['candidates'], [])
        missing = discover(self.home, [self.base / 'missing'])
        self.assertEqual(len(missing['unavailable']), 1)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        worktree = self.base / 'worktree'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '--detach', str(worktree)], check=True)
        found = discover(self.home, [self.base], current=worktree)
        self.assertEqual({x['sourceRoot'] for x in found['candidates']}, {str(self.repo), str(worktree)})

    def test_fifo_registry_and_receipt_are_refused_before_open(self):
        import os
        from agent_braid.plugin_legacy import selection
        self.install()
        path = self.home / 'registry.json'
        path.unlink()
        os.mkfifo(path, 0o600)
        with self.assertRaisesRegex(RegistryError, 'file type'):
            load(self.home)
        with self.assertRaisesRegex(RegistryError, 'file type'):
            selection('codex', path)

    def legacy_registry(self):
        """Rewrite an applied registry as the alpha.2 schema without consent."""
        import json
        self.install()
        path = self.home / 'registry.json'
        value = json.loads(path.read_bytes())
        del value['telemetry']
        value['schema'] = 'agent-braid-plugin-registry/v0.1'
        path.write_text(json.dumps(value))
        return value['workspaces']

    def test_new_registry_uses_v02_with_default_off_telemetry(self):
        preview = plan_setup(self.home, [self.repo])
        self.assertEqual(preview['registry']['schema'], 'agent-braid-plugin-registry/v0.2')
        self.assertEqual(preview['registry']['telemetry'], 'off')
        self.assertIsNone(preview['migratedFrom'])
        self.assertEqual(load(self.home)['telemetry'], 'off')

    def test_telemetry_consent_requires_preview_digest_and_can_be_withdrawn(self):
        self.install()
        preview = plan_setup(self.home, [], telemetry='local')
        self.assertEqual(load(self.home)['telemetry'], 'off')
        self.assertTrue(preview['reconnectRequired'])
        self.assertTrue(any('telemetry' in effect for effect in preview['effects']))
        with self.assertRaises(RegistryError):
            apply(self.home, preview, '0' * 64)
        apply(self.home, preview, preview['previewDigest'])
        self.assertEqual(load(self.home)['telemetry'], 'local')
        self.assertEqual(len(load(self.home)['workspaces']), 1)
        preview = plan_setup(self.home, [], telemetry='off')
        apply(self.home, preview, preview['previewDigest'])
        self.assertEqual(load(self.home)['telemetry'], 'off')
        with self.assertRaises(RegistryError):
            plan_setup(self.home, [], telemetry='remote')

    def test_v01_registry_requires_visible_migration_preview(self):
        workspaces = self.legacy_registry()
        with self.assertRaisesRegex(MigrationRequired, 'plugin setup'):
            load(self.home)
        preview = plan_setup(self.home, [])
        self.assertEqual(preview['migratedFrom'], 'agent-braid-plugin-registry/v0.1')
        self.assertTrue(preview['reconnectRequired'])
        self.assertTrue(any('v0.1' in effect for effect in preview['effects']))
        apply(self.home, preview, preview['previewDigest'])
        migrated = load(self.home)
        self.assertEqual(migrated['workspaces'], workspaces)
        self.assertEqual(migrated['telemetry'], 'off')

    def test_unknown_or_missing_telemetry_consent_refuses(self):
        import json
        self.install()
        path = self.home / 'registry.json'
        value = json.loads(path.read_bytes())
        for consent in ('remote', True, None):
            value['telemetry'] = consent
            path.write_text(json.dumps(value))
            with self.assertRaises(RegistryError):
                load(self.home)
        del value['telemetry']
        path.write_text(json.dumps(value))
        with self.assertRaises(RegistryError):
            load(self.home)

    def test_cli_setup_previews_and_applies_telemetry_consent_alone(self):
        import contextlib
        import io
        import json
        from agent_braid.cli import main
        def run(*extra):
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = main(['plugin', 'setup', '--home', str(self.home), *extra])
            return code, out.getvalue(), err.getvalue()
        code, _, err = run()
        self.assertEqual(code, 2)
        self.assertIn('--telemetry', err)
        code, out, _ = run('--telemetry', 'local')
        self.assertEqual(code, 0)
        preview = json.loads(out)
        self.assertFalse(self.home.exists())
        code, _, _ = run('--telemetry', 'local', '--apply', '--preview-digest', preview['previewDigest'])
        self.assertEqual(code, 0)
        self.assertEqual(load(self.home)['telemetry'], 'local')
