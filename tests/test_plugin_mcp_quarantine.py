# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-046 quarantine through the plugin router, doctor and setup CLI (incident: deleted agent worktrees)."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import unittest

from tests import test_plugin_mcp as mcp_tests
from tests import test_plugin_registry as registry_tests
from agent_braid.plugin_mcp import PluginRouter
from agent_braid.plugin_registry import load, plan_setup, apply

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples/analysis/file-edits.json').read_text())


class RouterQuarantineTests(unittest.TestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install
    second_repo = registry_tests.PluginRegistryTests.second_repo
    rewrite = mcp_tests.PluginRouterTests.rewrite

    def register(self, roots, repo=None):
        preview = plan_setup(self.home, [repo or self.repo], worktree_roots=roots)
        apply(self.home, preview, preview['previewDigest'])
        return load(self.home)['workspaces']

    def analyze(self, router, identifier):
        return router.invoke('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': SAMPLE}, threading.Event())

    def test_router_starts_with_a_deleted_worktree_and_reports_it_stale(self):
        worktree = self.base / 'agent-worktree'
        worktree.mkdir()
        identifier = self.register([worktree])[0]['workspaceId']
        shutil.rmtree(worktree)
        router = PluginRouter(self.home)
        status = router.status()
        self.assertEqual(status['status'], 'configured')
        self.assertEqual(status['staleWorktreeRoots'], [{'workspaceId': identifier, 'rootIndex': 0, 'reason': 'missing'}])
        self.assertEqual(status['unsafeWorkspaces'], [])
        self.assertFalse(status['reconnectRequired'])
        self.assertNotIn(str(worktree), json.dumps(status['staleWorktreeRoots']))
        self.assertEqual(router.services[identifier].config.worktree_roots, (self.repo,))
        self.assertEqual(self.analyze(router, identifier)['status'], 'ok')

    def test_deleting_a_registered_worktree_mid_session_keeps_status_and_calls_working(self):
        worktree = self.base / 'agent-worktree'
        worktree.mkdir()
        identifier = self.register([worktree])[0]['workspaceId']
        router = PluginRouter(self.home)
        shutil.rmtree(worktree)
        status = router.status()
        self.assertEqual(len(status['staleWorktreeRoots']), 1)
        self.assertTrue(status['reconnectRequired'])  # effective configuration differs from the snapshot
        self.assertEqual(self.analyze(router, identifier)['status'], 'ok')  # authority only shrank

    def test_reappearing_stale_root_requires_reconnect(self):
        worktree = self.base / 'agent-worktree'
        worktree.mkdir()
        identifier = self.register([worktree])[0]['workspaceId']
        shutil.rmtree(worktree)
        router = PluginRouter(self.home)
        self.assertEqual(self.analyze(router, identifier)['status'], 'ok')
        worktree.mkdir()  # authority grew relative to the snapshot taken without it
        self.assertTrue(router.status()['reconnectRequired'])
        refused = self.analyze(router, identifier)
        self.assertEqual(refused['status'], 'refused')
        self.assertEqual(refused['result'], {'code': 'reconnect-required'})

    def test_unsafe_workspace_is_isolated_and_the_others_keep_serving(self):
        other = self.second_repo()
        self.install([self.repo, other])
        ids = {r['sourceRoot']: r['workspaceId'] for r in load(self.home)['workspaces']}

        def poison(value):
            for row in value['workspaces']:
                if row['sourceRoot'] == str(self.repo):
                    row['worktreeRoots'] = [str(self.home)]
            return value
        self.rewrite(poison)
        router = PluginRouter(self.home)
        self.assertEqual(list(router.services), [ids[str(other)]])
        status = router.status()
        self.assertEqual([x['workspaceId'] for x in status['workspaces']], [ids[str(other)]])
        self.assertEqual(status['unsafeWorkspaces'][0]['workspaceId'], ids[str(self.repo)])
        self.assertIn('overlap', status['unsafeWorkspaces'][0]['reason'].lower())
        self.assertEqual(self.analyze(router, ids[str(other)])['status'], 'ok')
        self.assertEqual(self.analyze(router, ids[str(self.repo)])['status'], 'refused')

    def test_fixing_an_unsafe_workspace_requires_reconnect(self):
        self.install()
        original = (self.home / 'registry.json').read_text()
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        self.rewrite(lambda v: dict(v, workspaces=[dict(v['workspaces'][0], worktreeRoots=[str(self.home)])]))
        router = PluginRouter(self.home)
        self.assertEqual(router.services, {})
        (self.home / 'registry.json').write_text(original)
        self.assertTrue(router.status()['reconnectRequired'])
        self.assertEqual(self.analyze(router, identifier)['status'], 'refused')

    def test_workspace_whose_source_disappeared_does_not_stop_the_router(self):
        other = self.second_repo()
        self.install([self.repo, other])
        ids = {r['sourceRoot']: r['workspaceId'] for r in load(self.home)['workspaces']}
        shutil.rmtree(self.repo)
        router = PluginRouter(self.home)
        self.assertEqual(list(router.services), [ids[str(other)]])
        self.assertEqual(router.status()['unavailableWorkspaces'], [{'workspaceId': ids[str(self.repo)],
                                                                    'reason': 'configuration rejected'}])


class QuarantineCliTests(unittest.TestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install

    def cli(self, *argv):
        env = dict(os.environ, PYTHONPATH=str(ROOT))
        return subprocess.run([sys.executable, '-m', 'agent_braid', 'plugin', *argv, '--home', str(self.home)],
                              capture_output=True, text=True, env=env, cwd=ROOT, timeout=60)

    def test_doctor_diagnoses_and_prune_stale_repairs_a_registry_with_a_deleted_worktree(self):
        worktree = self.base / 'agent-worktree'
        worktree.mkdir()
        preview = plan_setup(self.home, [self.repo], worktree_roots=[worktree])
        apply(self.home, preview, preview['previewDigest'])
        shutil.rmtree(worktree)
        doctor = self.cli('doctor')
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertEqual(len(report['staleWorktreeRoots']), 1)
        self.assertEqual(report['staleWorktreeRoots'][0]['reason'], 'missing')
        listing = self.cli('workspaces')
        self.assertEqual(listing.returncode, 0, listing.stderr)
        self.assertEqual(len(json.loads(listing.stdout)['staleWorktreeRoots']), 1)
        before = (self.home / 'registry.json').read_bytes()
        previewed = self.cli('setup', '--prune-stale')
        self.assertEqual(previewed.returncode, 0, previewed.stderr)
        self.assertEqual((self.home / 'registry.json').read_bytes(), before)
        digest = json.loads(previewed.stdout)['previewDigest']
        applied = self.cli('setup', '--prune-stale', '--apply', '--preview-digest', digest)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        self.assertEqual(json.loads(self.cli('doctor').stdout)['staleWorktreeRoots'], [])
        self.assertEqual(load(self.home)['workspaces'][0]['worktreeRoots'], [])

    def test_setup_cli_refuses_a_missing_worktree_root(self):
        refused = self.cli('setup', '--source-root', str(self.repo), '--worktree-root', str(self.base / 'nope'))
        self.assertEqual(refused.returncode, 2)
        self.assertIn('does not exist', refused.stderr)
        self.assertNotIn(str(self.base), refused.stderr)


if __name__ == '__main__':
    unittest.main()
