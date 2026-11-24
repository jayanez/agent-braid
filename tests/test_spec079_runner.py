# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T008 preparation (REQ-008, REQ-009): the SPEC-071 runner knows ``v4-test`` and refuses a v4 run unless
the v4 freeze holds at develop 331a384e.

Fake hosts only; no model is contacted, no plugin is built and no quota is spent.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_braid import lightning_config as config
from agent_braid import lightning_heldout_v4 as v4
from agent_braid import lightning_runner as runner
from agent_braid import lightning_schema as schema
from scripts import spec079_freeze as freeze
from tests import test_spec078_heldout_v2 as base

ROOT = Path(__file__).resolve().parents[1]


def committed() -> dict:
    return json.loads((ROOT / v4.PROMPT_FILES['v4-test']).read_text())


class V4Root(unittest.TestCase):
    """A copy of every file the v4 freeze and its boundary read, so a negative control never edits the checkout."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        for path in (*freeze.BOUND, *freeze.RECORDS, *freeze.frozen_paths(ROOT), v4.FREEZE):
            (self.root / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / path, self.root / path)
        self.home = self.root / 'home'

    def edit(self, path: str) -> None:
        with (self.root / path).open('ab') as handle:
            handle.write(b'\n')

    def run_fake(self, root=None, repetitions=3, max_rollouts=2, **kwargs):
        cfg = config.build({'rollout': {'repetitions': repetitions, 'hosts': ['claude-code']},
                            'budget': {'maxRollouts': max_rollouts}})
        target = root or ROOT
        with patch.object(runner, 'checkout_root', lambda: target):
            return runner.run(self.home, cfg, fake_hosts=True, prompt_set='v4-test', environ=base.CLEAN_ENV, **kwargs)


class RegistrationTests(unittest.TestCase):
    def test_v4_is_a_known_protected_test_split(self):
        self.assertEqual(runner.PROMPT_FILES['v4-test'], 'specs/079-kind-choice-tool-fix/prompts/v4-test.json')
        self.assertIs(runner.HELDOUT['v4-test'], v4)
        self.assertEqual(runner.TEST_SETS['v4-test'], '.V4T-')
        self.assertIn('v4-test', schema.PROMPT_SETS)
        self.assertIn(v4.PROMPT_FILES['v4-test'], runner.OPTIMIZER_DENIED)
        self.assertIn(runner.HOLDOUT_CANARY, runner.canary_note('v4-test'))
        self.assertTrue(all(c['id'].startswith('V4T-') for c in committed()['cases']))

    def test_the_cli_accepts_the_v4_split(self):
        import argparse
        from agent_braid import lightning_cli
        parser = argparse.ArgumentParser()
        lightning_cli.add_parser(parser.add_subparsers(dest='command'))
        args = parser.parse_args(['lightning', 'run', '--prompt-set', 'v4-test', '--dry-run'])
        self.assertEqual(args.prompt_set, 'v4-test')

    def test_the_committed_freeze_holds_at_the_pinned_commit(self):
        self.assertEqual(v4.FREEZE_COMMIT, '331a384eeed0c52d39186ce64fc8344f4a23a759')
        self.assertEqual(v4.check_freeze(ROOT, 'v4-test'), freeze.sha256(ROOT, v4.PROMPT_FILES['v4-test']))
        self.assertEqual(freeze.main(['--check']), 0)

    def test_the_dry_run_plan_covers_the_whole_split(self):
        cfg = config.build({'rollout': {'repetitions': 3, 'hosts': ['claude-code']}, 'budget': {'maxRollouts': 300}})
        work = runner.plan(cfg, 'v4-test', ROOT)
        self.assertEqual((work['cases'], work['planned'], work['withinBudget']), (100, 300, 300))
        self.assertFalse(work['executionAuthorization'])


class FreezeGateTests(V4Root):
    def test_the_copy_holds_before_any_edit(self):
        self.assertEqual(v4.check_freeze(self.root, 'v4-test'), freeze.sha256(ROOT, v4.PROMPT_FILES['v4-test']))

    def test_without_a_freeze_a_v4_run_is_refused_before_anything(self):
        (self.root / v4.FREEZE).unlink()
        with self.assertRaises(runner.RunnerError) as caught:
            self.run_fake(self.root)
        self.assertEqual(caught.exception.code, 'protocol-not-frozen')
        self.assertFalse(self.home.exists())

    def test_negative_control_an_edited_bound_file_refuses_the_run(self):
        """Every file the v4 freeze binds: editing one byte refuses the run before the store or a host is touched."""
        expected = {v4.SKILL: 'skill-hash-mismatch', v4.PROMPT_FILES['v4-test']: 'holdout-hash-mismatch'}
        for path in freeze.BOUND:
            with self.subTest(path):
                original = (self.root / path).read_bytes()
                self.edit(path)
                with self.assertRaises(runner.RunnerError) as caught:
                    self.run_fake(self.root)
                self.assertEqual(caught.exception.code, expected.get(path, 'protocol-hash-mismatch'))
                self.assertIn(path, str(caught.exception))
                self.assertFalse(self.home.exists())
                (self.root / path).write_bytes(original)

    def test_an_edited_closed_record_or_frozen_path_refuses_the_run(self):
        for path in (freeze.SPEC078_FREEZE_V3, 'specs/069-aim-request-authoring/prompts/held-out.json'):
            with self.subTest(path):
                original = (self.root / path).read_bytes()
                self.edit(path)
                with self.assertRaises(runner.RunnerError) as caught:
                    self.run_fake(self.root)
                self.assertEqual(caught.exception.code, 'protocol-hash-mismatch')
                (self.root / path).write_bytes(original)

    def test_a_freeze_at_another_commit_is_refused(self):
        record = json.loads((self.root / v4.FREEZE).read_text())
        for value in ({**record, 'commit': '0' * 40, 'pluginCommit': '0' * 40},
                      {**record, 'pluginCommit': '0' * 40}, {**record, 'files': {}}):
            (self.root / v4.FREEZE).write_text(json.dumps(value))
            with self.assertRaises(runner.RunnerError) as caught:
                self.run_fake(self.root)
            self.assertEqual(caught.exception.code, 'protocol-not-frozen')

    def test_the_plan_refuses_a_broken_freeze_too(self):
        self.edit(v4.PROMPT_FILES['v4-test'])
        cfg = config.build({'rollout': {'repetitions': 3, 'hosts': ['claude-code']}, 'budget': {'maxRollouts': 300}})
        with self.assertRaises(runner.RunnerError) as caught:
            runner.plan(cfg, 'v4-test', self.root)
        self.assertEqual(caught.exception.code, 'holdout-hash-mismatch')


class RunnerTests(V4Root):
    def test_wrong_repetitions_arm_subset_or_candidate_is_refused(self):
        for kwargs, code in (({'repetitions': 1}, 'config-enum'), ({'arm': 'baseline'}, 'config-enum'),
                             ({'case_ids': ['V4T-001']}, 'config-enum'),
                             ({'plugin_dir': self.root}, 'skill-hash-mismatch'),
                             ({'skill_text': 'another skill'}, 'skill-hash-mismatch')):
            with self.subTest(kwargs):
                with self.assertRaises(runner.RunnerError) as caught:
                    self.run_fake(**kwargs)
                self.assertEqual(caught.exception.code, code)

    def test_the_split_is_scored_once_and_may_resume(self):
        status = self.run_fake()
        self.assertEqual(status['hosts']['claude-code']['rollouts'], 2)
        self.assertEqual(status['label'], 'pipeline-only')
        with self.assertRaises(runner.RunnerError) as caught:
            self.run_fake()
        self.assertEqual(caught.exception.code, 'test-already-scored')
        self.assertEqual(self.run_fake(max_rollouts=3, run_id=status['runId'], resume=True)['runId'], status['runId'])

    def test_a_real_run_builds_the_plugin_from_the_pinned_commit(self):
        """OD-D: the measured plugin is the freeze commit, not whatever the checkout holds."""
        seen = []

        class Stop(Exception):
            pass

        def pinned(commit, work, cache):
            seen.append(commit)
            raise Stop

        cfg = config.build({'rollout': {'repetitions': 3, 'hosts': ['claude-code']}, 'budget': {'maxRollouts': 1}})
        with patch.object(runner, 'build_pinned_plugin', pinned), patch.object(runner, 'parent_gate', lambda env: None), \
                patch('scripts.spec069_native_runs.build_candidate', side_effect=AssertionError('checkout build')):
            with self.assertRaises(Stop):
                runner.run(self.home, cfg, prompt_set='v4-test', environ=base.CLEAN_ENV)
        self.assertEqual(seen, [v4.FREEZE_COMMIT])

    def test_the_pinned_build_uses_a_worktree_at_the_commit_and_always_removes_it(self):
        import subprocess
        calls = []

        def fake_run(argv, **kwargs):
            calls.append(argv)
            if argv[0] != sys.executable:
                return subprocess.CompletedProcess(argv, 0, '', '')
            out = json.dumps({'plugin': '/built/plugins/agent-braid', 'record': {'sourceCommit': v4.FREEZE_COMMIT}})
            return subprocess.CompletedProcess(argv, 0, 'build log\n' + out + '\n', '')

        work, cache = self.root / 'work', self.root / 'cache'
        with patch.object(runner.subprocess, 'run', fake_run):
            plugin = runner.build_pinned_plugin(v4.FREEZE_COMMIT, work, cache)
        self.assertEqual(plugin, Path('/built/plugins/agent-braid'))
        source = str(work / 'pinned-source')
        self.assertEqual(calls[0][-5:], ['worktree', 'add', '--detach', source, v4.FREEZE_COMMIT])
        self.assertEqual(calls[1][:4], [sys.executable, '-I', '-c', runner._PINNED_BUILD])
        self.assertEqual(calls[1][4:], [source, str(work / 'pinned'), str(cache)])
        self.assertEqual(calls[-1][-4:], ['worktree', 'remove', '--force', source])

        def failing(argv, **kwargs):
            calls.append(argv)
            if argv[0] == sys.executable:
                raise subprocess.CalledProcessError(1, argv)
            return subprocess.CompletedProcess(argv, 0, '', '')

        calls.clear()
        with patch.object(runner.subprocess, 'run', failing), self.assertRaises(subprocess.CalledProcessError):
            runner.build_pinned_plugin(v4.FREEZE_COMMIT, work, cache)
        self.assertEqual(calls[-1][-4:], ['worktree', 'remove', '--force', source])

    def test_a_pinned_build_from_another_commit_is_refused(self):
        import subprocess

        def other(argv, **kwargs):
            out = json.dumps({'plugin': '/x', 'record': {'sourceCommit': 'f' * 40}})
            return subprocess.CompletedProcess(argv, 0, out if argv[0] == sys.executable else '', '')

        with patch.object(runner.subprocess, 'run', other), self.assertRaises(runner.RunnerError) as caught:
            runner.build_pinned_plugin(v4.FREEZE_COMMIT, self.root / 'work', self.root / 'cache')
        self.assertEqual(caught.exception.code, 'protocol-hash-mismatch')

    def test_the_contamination_scan_includes_the_v4_split(self):
        with patch.object(runner, 'load_fingerprints', lambda root: {'idSha256': [], 'windowSha256': []}):
            prints = runner.scan_fingerprints(ROOT)
        self.assertTrue(set(v4.fingerprints(ROOT)['windowSha256']) <= set(prints['windowSha256']))
        case = committed()['cases'][0]
        self.assertFalse(runner.contamination_passed(case['prompt'], prints))
        self.assertFalse(runner.contamination_passed(f"see {case['id']}", prints))


if __name__ == '__main__':
    unittest.main()
