# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-046 registry quarantine: a missing or unsafe row never invalidates the whole registry."""
import json
from pathlib import Path
import shutil
import unittest

from tests import test_plugin_registry as registry_tests
from agent_braid.plugin_registry import (RegistryError, configuration_digest, inspect_registry, load,
                                         not_grown, plan_setup, apply)


class RegistryQuarantineTests(unittest.TestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install
    second_repo = registry_tests.PluginRegistryTests.second_repo

    def with_worktree(self, name='ephemeral worktree'):
        worktree = self.base / name
        worktree.mkdir(exist_ok=True)
        preview = plan_setup(self.home, [self.repo], worktree_roots=[worktree])
        apply(self.home, preview, preview['previewDigest'])
        return worktree

    def rewrite(self, transform):
        path = self.home / 'registry.json'
        path.write_text(json.dumps(transform(json.loads(path.read_text()))))

    def test_missing_worktree_root_is_stale_and_excluded_without_invalidating_the_registry(self):
        worktree = self.with_worktree()
        live = inspect_registry(self.home)
        self.assertEqual(live['value']['workspaces'][0]['worktreeRoots'], [str(worktree)])
        self.assertEqual((live['stale'], live['quarantined']), ([], []))
        shutil.rmtree(worktree)
        found = inspect_registry(self.home)
        identifier = found['value']['workspaces'][0]['workspaceId']
        self.assertEqual(found['value']['workspaces'][0]['worktreeRoots'], [])
        self.assertEqual(found['stale'], [{'workspaceId': identifier, 'rootIndex': 0, 'reason': 'missing'}])
        self.assertEqual(found['quarantined'], [])
        self.assertEqual(load(self.home), found['value'])
        self.assertNotIn(str(worktree), json.dumps(found['stale']))

    def test_stale_roots_are_outside_the_digest_and_reappearing_changes_it_both_ways(self):
        self.install()
        without_root = configuration_digest(load(self.home))
        worktree = self.with_worktree()
        with_root = configuration_digest(load(self.home))
        self.assertNotEqual(with_root, without_root)
        shutil.rmtree(worktree)
        self.assertEqual(configuration_digest(load(self.home)), without_root)
        worktree.mkdir()
        self.assertEqual(configuration_digest(load(self.home)), with_root)

    def test_not_grown_accepts_only_roots_that_are_declared_and_missing(self):
        worktree = self.with_worktree()
        full = inspect_registry(self.home)
        shutil.rmtree(worktree)
        shrunk = inspect_registry(self.home)
        self.assertTrue(not_grown(full['value'], shrunk))
        self.assertTrue(not_grown(full['value'], full))
        self.assertFalse(not_grown(shrunk['value'], full))
        self.assertFalse(not_grown(full['value'], None))
        self.assertFalse(not_grown(None, full))
        self.assertFalse(not_grown(full['value'], dict(shrunk, value=dict(shrunk['value'], telemetry='local'))))
        self.assertFalse(not_grown(full['value'], dict(shrunk, value=dict(shrunk['value'], workspaces=[]))))
        # a root dropped from the declared list is a revocation, not a deletion
        self.rewrite(lambda v: dict(v, workspaces=[dict(v['workspaces'][0], worktreeRoots=[])]))
        self.assertFalse(not_grown(full['value'], inspect_registry(self.home)))

    def test_unsafe_worktree_root_quarantines_only_its_workspace(self):
        other = self.second_repo()
        self.install([self.repo, other])
        ids = {r['sourceRoot']: r['workspaceId'] for r in load(self.home)['workspaces']}
        inside = self.home / 'inside'
        live = self.base / 'live'
        live.mkdir()

        def poison(value):
            for row in value['workspaces']:
                if row['sourceRoot'] == str(self.repo):
                    row['worktreeRoots'] = [str(live), str(inside)]
            return value
        self.rewrite(poison)
        found = inspect_registry(self.home)
        self.assertEqual([r['workspaceId'] for r in found['value']['workspaces']], [ids[str(other)]])
        self.assertEqual(len(found['quarantined']), 1)
        entry = found['quarantined'][0]
        self.assertEqual(entry['workspaceId'], ids[str(self.repo)])
        self.assertIn('worktree root 1', entry['reason'].lower())
        self.assertIn('overlap', entry['reason'].lower())
        self.assertNotIn(str(inside), json.dumps(found['quarantined']))
        with self.assertRaisesRegex(RegistryError, 'orktree root 1'):
            load(self.home)

    def test_missing_root_that_overlaps_plugin_state_is_unsafe_not_stale(self):
        self.install()
        self.rewrite(lambda v: dict(v, workspaces=[dict(v['workspaces'][0], worktreeRoots=[str(self.home / 'gone')])]))
        found = inspect_registry(self.home)
        self.assertEqual(found['value']['workspaces'], [])
        self.assertEqual(found['stale'], [])
        self.assertIn('overlap', found['quarantined'][0]['reason'].lower())

    def test_malformed_rows_are_quarantined_and_never_served(self):
        other = self.second_repo()
        (self.base / 'file').write_text('x')
        mutations = {
            'identity': lambda row: dict(row, workspaceId='0' * 32),
            'unknown key': lambda row: dict(row, extra=1),
            'non-string root': lambda row: dict(row, worktreeRoots=[7]),
            'relative root': lambda row: dict(row, worktreeRoots=['relative/dir']),
            'file root': lambda row: dict(row, worktreeRoots=[str(self.base / 'file')]),
            'runtime without grant': lambda row: dict(row, runtimeEnabled=True),
            'not an object': lambda row: 'nope',
        }
        for number, (name, mutate) in enumerate(mutations.items()):
            with self.subTest(name):
                self.home = self.base / f'state-{number}'
                self.install([self.repo, other])
                good = load(self.home)['workspaces']
                self.rewrite(lambda v: dict(v, workspaces=[mutate(v['workspaces'][0]), v['workspaces'][1]]))
                found = inspect_registry(self.home)
                self.assertEqual([r['workspaceId'] for r in found['value']['workspaces']], [good[1]['workspaceId']])
                self.assertEqual(len(found['quarantined']), 1)
                self.assertNotEqual(found['quarantined'][0]['workspaceId'], good[1]['workspaceId'])
                self.assertNotIn(str(self.base), found['quarantined'][0]['reason'])

    def test_structural_problems_stay_fatal_for_the_whole_registry(self):
        other = self.second_repo()
        self.install([self.repo, other])
        original = (self.home / 'registry.json').read_text()
        value = json.loads(original)
        duplicated = dict(value, workspaces=[value['workspaces'][0], dict(value['workspaces'][0])])
        for raw in (json.dumps(duplicated), json.dumps(dict(value, schema='other')),
                    json.dumps(dict(value, telemetry='cloud')), '[]',
                    original.replace('"workspaces"', '"workspaces": [], "workspaces"', 1)):
            with self.subTest(raw[:40]):
                (self.home / 'registry.json').write_text(raw)
                with self.assertRaises(RegistryError):
                    inspect_registry(self.home)
        (self.home / 'registry.json').write_text(original)
        (self.home / 'registry.json').chmod(0o644)
        with self.assertRaisesRegex(RegistryError, 'private'):
            inspect_registry(self.home)

    def test_duplicate_id_with_an_unsafe_twin_is_fatal_not_quarantined(self):
        self.install()
        def twin(value):
            row = value['workspaces'][0]
            return dict(value, workspaces=[row, dict(row, worktreeRoots=[str(self.home / 'x')])])
        self.rewrite(twin)
        with self.assertRaisesRegex(RegistryError, 'Duplicate'):
            inspect_registry(self.home)

    def test_setup_rejects_worktree_roots_that_do_not_exist(self):
        with self.assertRaisesRegex(RegistryError, 'Worktree root 0 does not exist'):
            plan_setup(self.home, [self.repo], worktree_roots=[self.base / 'missing'])
        self.assertFalse(self.home.exists())

    def test_setup_previews_and_applies_with_a_stale_root_and_keeps_it_unless_pruned(self):
        worktree = self.with_worktree()
        shutil.rmtree(worktree)
        other = self.second_repo()
        preview = plan_setup(self.home, [other])
        kept = [r for r in preview['registry']['workspaces'] if r['sourceRoot'] == str(self.repo)]
        self.assertEqual(kept[0]['worktreeRoots'], [str(worktree)])
        self.assertTrue(any('stale' in effect.lower() for effect in preview['effects']))
        apply(self.home, preview, preview['previewDigest'])
        self.assertEqual(len(load(self.home)['workspaces']), 2)
        self.assertEqual(len(inspect_registry(self.home)['stale']), 1)

    def test_prune_stale_removes_only_stale_roots_with_exact_digest_apply(self):
        live = self.base / 'live worktree'
        live.mkdir()
        gone = self.base / 'gone worktree'
        gone.mkdir()
        preview = plan_setup(self.home, [self.repo], worktree_roots=[live, gone])
        apply(self.home, preview, preview['previewDigest'])
        shutil.rmtree(gone)
        before = (self.home / 'registry.json').read_bytes()
        pruned = plan_setup(self.home, [], prune_stale=True)
        self.assertEqual((self.home / 'registry.json').read_bytes(), before)
        self.assertEqual(pruned['registry']['workspaces'][0]['worktreeRoots'], [str(live)])
        self.assertTrue(any('prune' in effect.lower() for effect in pruned['effects']))
        with self.assertRaises(RegistryError):
            apply(self.home, pruned, '0' * 64)
        apply(self.home, pruned, pruned['previewDigest'])
        self.assertEqual(inspect_registry(self.home)['stale'], [])
        raw = json.loads((self.home / 'registry.json').read_text())
        self.assertEqual(raw['workspaces'][0]['worktreeRoots'], [str(live)])

    def test_setup_refuses_to_rewrite_unsafe_rows_without_prune_and_drops_them_with_it(self):
        other = self.second_repo()
        self.install([self.repo, other])
        poisoned = load(self.home)['workspaces'][0]['workspaceId']  # rows are sorted by random-path ids
        self.rewrite(lambda v: dict(v, workspaces=[dict(v['workspaces'][0], worktreeRoots=[str(self.home / 'x')]),
                                                   v['workspaces'][1]]))
        with self.assertRaisesRegex(RegistryError, 'prune-stale'):
            plan_setup(self.home, [], telemetry='local')
        preview = plan_setup(self.home, [], telemetry='local', prune_stale=True)
        self.assertEqual(len(preview['registry']['workspaces']), 1)
        dropped = [e for e in preview['effects'] if 'unsafe' in e.lower()]
        self.assertEqual(len(dropped), 1)
        self.assertIn(poisoned, dropped[0])
        self.assertIn('backup', dropped[0])
        self.assertIn('grantStore', dropped[0])
        apply(self.home, preview, preview['previewDigest'])
        self.assertEqual(inspect_registry(self.home)['quarantined'], [])


if __name__ == '__main__':
    unittest.main()
