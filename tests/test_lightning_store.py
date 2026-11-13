# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-070 REQ-006: private append-only Braid Lightning run store."""
import os
from pathlib import Path
import stat
import tempfile
import unittest

from agent_braid import lightning_schema as s
from agent_braid import lightning_store as st


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        self.store = st.RunStore(self.home, 'run-1')
        self.store.create(config_digest='c' * 64, now=1000.0)

    def tearDown(self):
        self.tmp.cleanup()

    def rollout(self):
        return s.new_rollout('r-1', 'task-1', 'group-1', 'a' * 64, 'b' * 64, 'opencode', at=1000.0)

    def test_append_and_read_round_trip_with_private_modes(self):
        self.store.append('rollout', self.rollout())
        self.assertEqual([r.rollout_id for r in self.store.read('rollout')], ['r-1'])
        for path in (self.store.root, self.store.root / 'rollouts.jsonl', self.store.root / 'run.json'):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode) & 0o077, 0, path)

    def test_unknown_kinds_mismatches_and_content_are_refused(self):
        for kind, record, code in (('trace', {}, 'store-consent'), ('note', {}, 'store-kind'),
                                   ('event', self.rollout(), 'store-kind'),
                                   ('rollout', dict(self.rollout().to_dict(), prompt='x'), 'record-unknown-key')):
            with self.subTest(kind=kind), self.assertRaises(st.StoreError) as caught:
                self.store.append(kind, record)
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.store.read('rollout'), [])

    def test_existing_run_and_bad_identifiers_are_refused(self):
        with self.assertRaises(st.StoreError):
            st.RunStore(self.home, 'run-1').create(config_digest='c' * 64)
        with self.assertRaises(st.StoreError):
            st.RunStore(self.home, '../escape')

    def test_symlinked_run_store_is_refused(self):
        target = Path(self.tmp.name).resolve() / 'elsewhere'
        target.mkdir()
        os.symlink(target, st.runs_root(self.home) / 'linked')
        with self.assertRaises(ValueError):
            st.list_runs(self.home)

    def test_tampered_line_is_detected_on_read(self):
        self.store.append('rollout', self.rollout())
        path = self.store.root / 'rollouts.jsonl'
        path.write_bytes(path.read_bytes().replace(b'"opencode"', b'"codex"'))
        with self.assertRaises(st.StoreError):
            self.store.read('rollout')

    def test_sweep_and_purge(self):
        st.RunStore(self.home, 'run-2').create(config_digest='c' * 64, now=1000.0 + 40 * 86400)
        result = st.sweep(self.home, 30, now=1000.0 + 45 * 86400)
        self.assertEqual(result['removed'], ['run-1'])
        self.assertEqual([r['runId'] for r in st.list_runs(self.home)], ['run-2'])
        st.purge(self.home, 'run-2')
        self.assertEqual(st.list_runs(self.home), [])
        with self.assertRaises(st.StoreError):
            st.sweep(self.home, 0)


    def test_journal_start_records_host_models_and_refuses_malformed_ones(self):
        start = {'kind': 'start', 'algorithm': 'gepa', 'rngSeed': 0,
                 'source': {'arm': 'final', 'commit': 'a' * 40, 'workingTree': True, 'seedSkillSha256': 'b' * 64}}
        self.store.append_journal({**start, 'models': {'claude-code': 'claude-sonnet-5-5'}})
        self.assertEqual(self.store.read_journal()[0]['models'], {'claude-code': 'claude-sonnet-5-5'})
        for bad in ('claude-sonnet-5-5', {'claude-code': 5}, {'': 'm'}, {'claude-code': ''}):
            with self.subTest(bad=bad), self.assertRaises(st.StoreError):
                self.store.append_journal({**start, 'models': bad})

if __name__ == '__main__':
    unittest.main()
