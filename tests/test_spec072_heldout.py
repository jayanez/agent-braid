# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 T010 (procedure_008, pipeline check): the held-out command with fakes, no host and no quota."""
import contextlib
import copy
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store_mod
from agent_braid.lightning_hosts import Secrets
from agent_braid.lightning_resources import sha256_text, split_skill
from scripts import spec072_heldout as heldout

ROOT = runner.checkout_root()
TARGET = heldout.heldout_config()['target']['path']
RAW = (ROOT / TARGET).read_text(encoding='utf-8')
FRONT, BODY = split_skill(RAW)
APO_BODY = BODY + '\nAPO candidate: state every dependency between units explicitly before you call the tool.\n'
GEPA_BODY = BODY + '\nGEPA candidate: name each conflicting resource once and keep the request minimal always.\n'
CASES = [f'C-{i:02d}' for i in range(1, 11)]


def development(apo_sha=None, gepa_sha=None):
    def arm(name, sha, run_id):
        return {'runId': run_id, 'bestSha256': sha, 'seedSha256': sha256_text(BODY), 'stop': None,
                'refusal': None, 'rollouts': 45, 'optimizerCalls': 3,
                'source': {'arm': 'final', 'seedSkillSha256': sha256_text(RAW)}}
    return {'seedRun': 'run-seed', 'pinnedModel': 'claude-sonnet-5-5', 'runs': {
        'apo': arm('apo', apo_sha or sha256_text(APO_BODY), 'apo-run'),
        'gepa': arm('gepa', gepa_sha or sha256_text(GEPA_BODY), 'gepa-run')}}


def vectors(first_by_case, retry=True, canary=0):
    """Three repetitions per case; ``first_by_case[c]`` repetitions succeed at the first attempt."""
    out = []
    for case in CASES:
        for rep in range(1, 4):
            out.append({'host': 'claude-code', 'caseId': case, 'repetition': rep,
                        'validFirstAttempt': rep <= first_by_case.get(case, 3), 'validWithinRetry': retry,
                        'schemaValid': True, 'canaryHits': canary if rep == 1 and case == 'C-01' else 0})
    return out


def arm_result(verdict, canary=0):
    return {'canaryHits': canary, 'summary': {'hosts': {'claude-code': {'verdict': verdict}}}}


class HomeCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        for run_id, body in (('apo-run', APO_BODY), ('gepa-run', GEPA_BODY)):
            store = store_mod.RunStore(self.home, run_id)
            store.create(config_digest='c' * 64)
            store.write_candidate_text(sha256_text(body), body)

    def tearDown(self):
        self.tmp.cleanup()


class ArmResolutionTests(HomeCase):
    def test_arms_resolve_from_the_development_evidence_with_verified_shas(self):
        arms = heldout.resolve_arms(self.home, ROOT, development(), TARGET)
        self.assertEqual(list(arms), ['A0', 'A1', 'A2'])
        self.assertEqual(arms['A0']['candidateSha256'], sha256_text(BODY))
        self.assertEqual(arms['A0']['skillText'], RAW)
        self.assertEqual(arms['A1']['candidateSha256'], sha256_text(APO_BODY))
        self.assertEqual(arms['A2']['skillText'], FRONT + GEPA_BODY)
        self.assertEqual(arms['A2']['skillSha256'], sha256_text(FRONT + GEPA_BODY))
        self.assertEqual(arms['A2']['developmentRun'], 'gepa-run')
        self.assertNotIn('E1', arms)
        self.assertNotIn('skillText', heldout.public(arms['A1']))

    def test_a_missing_candidate_text_is_refused(self):
        with self.assertRaises(heldout.HeldoutError) as caught:
            heldout.resolve_arms(self.home, ROOT, development(gepa_sha='f' * 64), TARGET)
        self.assertEqual(caught.exception.code, 'candidate-text-missing')

    def test_a_tampered_candidate_text_is_refused(self):
        path = store_mod.RunStore(self.home, 'apo-run').root / 'candidates' / f'{sha256_text(APO_BODY)}.md'
        path.write_text(APO_BODY + 'tampered')
        with self.assertRaises(heldout.HeldoutError) as caught:
            heldout.resolve_arms(self.home, ROOT, development(), TARGET)
        self.assertEqual(caught.exception.code, 'candidate-hash-mismatch')

    def test_a_drifted_a0_guidance_or_unfinished_arm_is_refused(self):
        drifted = development()
        drifted['runs']['apo']['seedSha256'] = 'e' * 64
        with self.assertRaises(heldout.HeldoutError) as caught:
            heldout.resolve_arms(self.home, ROOT, drifted, TARGET)
        self.assertEqual(caught.exception.code, 'a0-source-drift')
        stopped = development()
        stopped['runs']['gepa']['stop'] = 'weekly-stop'
        with self.assertRaises(heldout.HeldoutError) as caught:
            heldout.resolve_arms(self.home, ROOT, stopped, TARGET)
        self.assertEqual(caught.exception.code, 'development-arm-missing')


class FreezeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        for relative in (runner.PROTOCOL, runner.PROTOCOL_FREEZE, heldout.DEVELOPMENT):
            (self.root / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / relative, self.root / relative)

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.object(heldout, 'resolve_arms', side_effect=AssertionError('arms resolved')), \
                mock.patch.object(runner, 'run', side_effect=AssertionError('launched')):
            code = heldout.main(['--home', str(self.root / 'home'), *argv], root=self.root)
        return code, json.loads(out.getvalue()), err.getvalue()

    def test_an_edited_protocol_is_refused_before_anything_else(self):
        path = self.root / runner.PROTOCOL
        path.write_text(path.read_text() + '\nA late change.\n')
        for argv in ((), ('--execute',)):
            code, printed, err = self.run_main(*argv)
            self.assertEqual(code, 2)
            self.assertEqual(printed, {'protocolFreeze': {'status': 'refused', 'code': 'protocol-hash-mismatch'}})
            self.assertIn('protocol-hash-mismatch', err)
        self.assertFalse((self.root / 'home').exists())
        self.assertFalse((self.root / heldout.OUT).exists())

    def test_a_model_other_than_the_pinned_one_is_refused(self):
        with mock.patch.object(heldout, 'check_development', return_value={'pinnedModel': 'claude-sonnet-5-5'}):
            for argv in (('--model', 'claude-other'), ('--model', 'claude-other', '--execute')):
                code, printed, err = self.run_main(*argv)
                self.assertEqual((code, printed['refusal']), (2, 'model-not-pinned'))
        self.assertFalse((self.root / heldout.OUT).exists())

    def test_changed_development_evidence_is_refused(self):
        path = self.root / heldout.DEVELOPMENT
        path.write_text(path.read_text().replace('"apo"', '"apo" ', 1))
        with self.assertRaises(heldout.HeldoutError) as caught:
            heldout.check_development(self.root)
        self.assertEqual(caught.exception.code, 'development-evidence-changed')


class RuleAndStatisticsTests(unittest.TestCase):
    def test_h1_truth_table(self):
        table = [  # (A0 verdict, A2 verdict, A0 canary, A2 canary) -> outcome
            ('meets', 'meets', 0, 0, 'not-assessable'),
            ('meets', 'misses', 0, 0, 'not-assessable'),
            ('misses', 'meets', 0, 0, 'supported'),
            ('misses', 'misses', 0, 0, 'not-supported'),
            ('misses', 'inconclusive', 0, 0, 'not-supported'),
            ('inconclusive', 'meets', 0, 0, 'not-supported'),
            ('unobserved', 'meets', 0, 0, 'not-supported'),
            ('misses', 'meets', 0, 1, 'not-supported'),  # canary hit invalidates A2
            ('meets', 'meets', 1, 0, 'not-supported'),  # invalidated A0 is not a meeting baseline
        ]
        for a0, a2, c0, c2, expected in table:
            result = heldout.h1_rule(arm_result(a0, c0), arm_result(a2, c2))
            self.assertEqual(result, {'outcome': expected, 'hosts': {'claude-code': expected}}, (a0, a2, c0, c2))

    def test_sign_test_values(self):
        self.assertEqual(heldout.sign_test(0, 0), 1.0)
        self.assertEqual(heldout.sign_test(1, 0), 1.0)
        self.assertAlmostEqual(heldout.sign_test(5, 0), 0.0625)
        self.assertAlmostEqual(heldout.sign_test(0, 5), 0.0625)
        self.assertAlmostEqual(heldout.sign_test(8, 2), 0.109375)
        self.assertAlmostEqual(heldout.sign_test(10, 0), 0.001953125)
        self.assertEqual(heldout.sign_test(3, 3), 1.0)
        self.assertAlmostEqual(heldout.sign_test(6, 1), 0.125)

    def test_paired_counts(self):
        base = vectors({'C-01': 1, 'C-02': 3, 'C-03': 2})
        other = vectors({'C-01': 3, 'C-02': 0, 'C-03': 2})
        self.assertEqual(heldout.paired(base, other), {'prompts': 10, 'improved': 1, 'unchanged': 8, 'worsened': 1,
                                                       'signTestPTwoSided': 1.0})

    def test_analysis_reports_every_preregistered_measure(self):
        result = heldout.analysis({'A0': vectors({c: 0 for c in CASES[:4]}),
                                   'A1': vectors({c: 0 for c in CASES}, retry=False),
                                   'A2': vectors({})}, 10, 3)
        a0 = result['arms']['A0']
        self.assertEqual(a0['summary']['hosts']['claude-code']['verdict'], 'misses')
        self.assertEqual(result['arms']['A2']['summary']['hosts']['claude-code']['verdict'], 'meets')
        self.assertEqual(a0['schemaValidity'], {'valid': 30, 'trials': 30, 'rate': 1.0})
        self.assertEqual(len(a0['intervals']['claude-code']['firstAttempt']), 2)
        self.assertEqual(result['paired']['A2-vs-A0']['claude-code']['improved'], 4)
        self.assertEqual(result['paired']['A1-vs-A0']['claude-code']['worsened'], 6)
        self.assertEqual(result['h1'], {'outcome': 'supported', 'hosts': {'claude-code': 'supported'}})
        hit = heldout.analysis({'A0': vectors({c: 0 for c in CASES[:4]}), 'A1': vectors({}),
                                'A2': vectors({}, canary=1)}, 10, 3)
        self.assertEqual(hit['arms']['A2']['canaryHits'], 1)
        self.assertEqual(hit['h1']['outcome'], 'not-supported')

    def test_pair_is_a0_and_a2_and_agrees_with_the_rule(self):
        arms = {label: {'candidateSha256': sha256_text(label)} for label in heldout.ARMS}
        result = heldout.analysis({'A0': vectors({c: 0 for c in CASES[:4]}), 'A1': vectors({}),
                                   'A2': vectors({})}, 10, 3)
        costs = {'A': {'heldOutRollouts': 30}, 'C': {'heldOutRollouts': 30}}
        registration, report = heldout.pair(result, arms, ROOT, 'b' * 64, costs)
        data = registration.to_dict()
        self.assertEqual(data['arms']['A']['candidateSha256'], sha256_text('A0'))
        self.assertEqual(data['arms']['C']['candidateSha256'], sha256_text('A2'))
        self.assertEqual(report.to_dict()['h1'], result['h1'])
        self.assertEqual(report.to_dict()['registrationSha256'], registration.sha256)


class DryRunAndEvidenceTests(HomeCase):
    def test_dry_run_prints_plan_cost_arms_and_freeze_and_launches_nothing(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), \
                mock.patch.object(heldout, 'check_development', return_value=development()), \
                mock.patch.object(runner, 'run', side_effect=AssertionError('launched')), \
                mock.patch.object(runner, 'parent_gate', side_effect=AssertionError('gated')):
            code = heldout.main(['--home', str(self.home)])
        self.assertEqual(code, 0)
        printed = json.loads(out.getvalue())
        self.assertFalse(printed['execute'])
        plan = printed['plan']
        self.assertEqual((plan['cases'], plan['repetitions'], plan['rolloutsPerArm'], plan['totalRollouts']),
                         (10, 3, 30, 90))
        self.assertEqual(plan['roughMinutes'], 35)
        self.assertEqual(plan['host'], 'claude-code')
        self.assertEqual(plan['requiredHosts'], ['claude-code'])
        self.assertEqual(plan['protocolFreeze']['status'], 'frozen')
        self.assertEqual(sorted(plan['arms']), ['A0', 'A1', 'A2'])
        self.assertEqual(plan['arms']['A2']['candidateSha256'], sha256_text(GEPA_BODY))
        self.assertEqual(plan['arms']['A0']['state'], {'status': 'pending', 'completed': 0})
        self.assertFalse(plan['executionAuthorization'])
        self.assertNotIn(GEPA_BODY.strip().splitlines()[-1], out.getvalue())
        self.assertIn('nothing launched', err.getvalue())

    def test_each_arm_runs_once_and_a_recorded_arm_resumes(self):
        arms = heldout.resolve_arms(self.home, ROOT, development(), TARGET)
        calls = []

        def fake_run(home, cfg, *, run_id, resume, prompt_set, plugin_dir, environ, arm, models, skill_text):
            calls.append((run_id, resume, prompt_set, skill_text == arms[run_id.split('-')[1].upper()]['skillText']))
            store = store_mod.RunStore(home, run_id)
            if not store.root.exists():
                store.create(config_digest='c' * 64)
            done.add(run_id)  # the run finishes all its rollouts
            return {'runId': run_id, 'stop': None, 'refusal': None}

        def fake_state(home, run_id, planned):
            if not run_id or not store_mod.RunStore(home, run_id).root.exists():
                return {'status': 'pending', 'completed': 0}
            return {'status': 'complete' if run_id in done else 'resume', 'completed': 30 if run_id in done else 7}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            store_mod.RunStore(self.home, 'heldout-a0-done').create(config_digest='c' * 64)
            store_mod.RunStore(self.home, 'heldout-a1-stopped').create(config_digest='c' * 64)
            done = {'heldout-a0-done'}
            record = {'arms': {'A0': {'runId': 'heldout-a0-done'}, 'A1': {'runId': 'heldout-a1-stopped'}, 'A2': {}},
                      'invocations': [{'runs': {}}]}
            with mock.patch.object(heldout, 'arm_state', side_effect=fake_state), \
                    mock.patch.object(heldout, 'new_run_id', return_value='heldout-a2-new'):
                code = heldout.execute_arms(self.home, root, arms, record, cfg={}, models={'claude-code': 'm'},
                                            environ={}, secrets=Secrets(), planned=30, run=fake_run,
                                            build=lambda label, text, work: work)
            self.assertEqual(code, 0)
            self.assertEqual(calls, [('heldout-a1-stopped', True, 'held-out', True),
                                     ('heldout-a2-new', False, 'held-out', True)])
            written = json.loads((root / heldout.OUT).read_text())
            self.assertEqual(written['arms']['A2']['runId'], 'heldout-a2-new')
            self.assertNotIn('A0', written['invocations'][-1]['runs'])

    def test_a_quota_stop_ends_the_phase(self):
        arms = heldout.resolve_arms(self.home, ROOT, development(), TARGET)
        calls = []

        def fake_run(home, cfg, **kw):
            calls.append(kw['run_id'])
            return {'runId': kw['run_id'], 'stop': 'weekly-stop', 'refusal': None}

        with tempfile.TemporaryDirectory() as tmp:
            record = {'arms': {label: {} for label in heldout.ARMS}, 'invocations': [{'runs': {}}]}
            code = heldout.execute_arms(self.home, Path(tmp), arms, record, cfg={}, models={}, environ={},
                                        secrets=Secrets(), planned=30, run=fake_run,
                                        build=lambda label, text, work: work)
        self.assertEqual(code, 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(record['arms']['A0']['status']['stop'], 'weekly-stop')

    def test_the_evidence_written_is_content_free(self):
        arms = heldout.resolve_arms(self.home, ROOT, development(), TARGET)
        result = heldout.analysis({'A0': vectors({c: 0 for c in CASES[:4]}), 'A1': vectors({}),
                                   'A2': vectors({})}, 10, 3)
        record = {'arms': {k: heldout.public(v) for k, v in arms.items()}, 'analysis': result,
                  'invocations': []}
        with tempfile.TemporaryDirectory() as tmp:
            path = heldout.write_evidence(Path(tmp), record, arms, Secrets(['sk-ant-test-secret-value-1234567890']))
            text = path.read_text()
        for arm in arms.values():
            self.assertNotIn(arm['skillText'], text)
            self.assertNotIn(GEPA_BODY.strip().splitlines()[-1], text)
        for key in heldout.FORBIDDEN_KEYS:
            self.assertNotIn(key, text)
        for bad in ({**copy.deepcopy(record), 'leak': GEPA_BODY.strip().splitlines()[-1]},
                    {**copy.deepcopy(record), 'parsedAttempts': []}):
            with tempfile.TemporaryDirectory() as tmp, self.assertRaises(heldout.HeldoutError) as caught:
                heldout.write_evidence(Path(tmp), bad, arms, Secrets())
            self.assertEqual(caught.exception.code, 'evidence-not-content-free')
        with tempfile.TemporaryDirectory() as tmp, self.assertRaises(Exception):
            heldout.write_evidence(Path(tmp), {**record, 'token': 'sk-ant-test-secret-value-1234567890'}, arms,
                                   Secrets(['sk-ant-test-secret-value-1234567890']))


class ReviewRegressionTests(HomeCase):
    """Resume, replay, safety-refusal and content checks added in the PR #1352 review."""

    def test_a_canary_count_above_one_replays_to_the_stored_reward(self):
        from scripts import spec069_scoring as scoring
        from agent_braid import lightning_reward as reward_mod
        case = json.loads((ROOT / runner.PROMPT_FILES['held-out']).read_text())['cases'][0]
        scoring_sha = reward_mod.check_scoring(ROOT)
        stored = reward_mod.compute('claude-code.x.r1', case, [], canary_hits=3, components=['schema', 'd4', 'canary'],
                                    scoring=scoring, scoring_sha256=scoring_sha)
        result = {'rolloutId': 'claude-code.x.r1', 'parsedAttempts': [],
                  'rewardSha256': reward_mod.reward_sha256(stored)}
        reward = heldout.replay_reward(result, case, True, scoring, scoring_sha)
        self.assertEqual((reward['canaryHits'], reward['d4FirstAttempt']), (3, False))
        with self.assertRaises(heldout.HeldoutError) as caught:  # no canary event: the hash cannot be reproduced
            heldout.replay_reward(result, case, False, scoring, scoring_sha)
        self.assertEqual(caught.exception.code, 'replay-mismatch')

    def test_the_first_unstopped_result_is_scored_and_a_retry_never_replaces_it(self):
        def rec(rollout, stop=None, refusal=None):
            return mock.Mock(value={'rolloutId': rollout, 'stop': stop, 'refusal': refusal})
        store = mock.Mock()
        store.read.return_value = [rec('r1', refusal='rollout-timeout'), rec('r2', stop='weekly-stop'),
                                   rec('r1'), rec('r2'), rec('r2')]
        first = heldout.scored_results(store)
        self.assertEqual(first['r1']['refusal'], 'rollout-timeout')  # the resumed retry of r1 does not count
        self.assertIs(first['r2'], store.read.return_value[3].value)

    def execute(self, record, run):
        arms = heldout.resolve_arms(self.home, ROOT, development(), TARGET)
        with tempfile.TemporaryDirectory() as tmp:
            return heldout.execute_arms(self.home, Path(tmp), arms, record, cfg={}, models={}, environ={},
                                        secrets=Secrets(), planned=30, run=run,
                                        build=lambda label, text, work: work)

    def test_a_safety_refusal_is_never_resumed_or_analysed(self):
        store_mod.RunStore(self.home, 'heldout-a0-leak').create(config_digest='c' * 64)
        record = {'arms': {'A0': {'runId': 'heldout-a0-leak', 'status': {'refusal': 'credential-leak'}},
                           'A1': {}, 'A2': {}}, 'invocations': [{'runs': {}}]}
        self.assertEqual(self.execute(record, run=mock.Mock(side_effect=AssertionError('launched'))), 1)
        self.assertEqual(record['arms']['A0']['state']['status'], 'refused')

    def test_a_recorded_run_with_rollouts_but_no_store_is_refused(self):
        record = {'arms': {'A0': {'runId': 'heldout-a0-gone', 'state': {'status': 'resume', 'completed': 7}},
                           'A1': {}, 'A2': {}}, 'invocations': [{'runs': {}}]}
        with self.assertRaises(heldout.HeldoutError) as caught:
            self.execute(record, run=mock.Mock(side_effect=AssertionError('launched')))
        self.assertEqual(caught.exception.code, 'run-store-missing')

    def test_a_json_escaped_skill_line_is_still_found(self):
        line = 'Return "conditions" only when\ta unit waits on another unit.'
        arms = {'A0': {'arm': 'A0', 'skillText': f'---\nname: x\n---\n{line}\n'}}
        heldout.assert_content_free(json.dumps({'ok': 1}), arms, Secrets())
        with self.assertRaises(heldout.HeldoutError) as caught:
            heldout.assert_content_free(json.dumps({'detail': line}), arms, Secrets())
        self.assertEqual(caught.exception.code, 'evidence-not-content-free')


class FakeHostPipelineTests(HomeCase):
    """The three arms through the real runner on fake hosts (pipeline-only; no model, no quota)."""

    def test_fake_held_out_runs_analysis_and_pair(self):
        from functools import partial
        from scripts import spec069_native_runs as driver
        arms = heldout.resolve_arms(self.home, ROOT, development(), TARGET)
        record = {'arms': {label: {} for label in heldout.ARMS}, 'invocations': [{'runs': {}}]}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code = heldout.execute_arms(self.home, root, arms, record, cfg=heldout.heldout_config(), models={},
                                        environ={}, secrets=Secrets(), planned=30,
                                        run=partial(runner.run, fake_hosts=True),
                                        build=lambda label, text, work: driver.fake_plugin(work))
            self.assertEqual(code, 0)
            self.assertEqual({a['state']['status'] for a in record['arms'].values()}, {'complete'})
            vectors = {label: heldout.run_vectors(self.home, ROOT, record['arms'][label]['runId'],
                                                  arms[label]['skillSha256']) for label in heldout.ARMS}
            self.assertEqual([len(v) for v in vectors.values()], [30, 30, 30])
            result = heldout.analysis(vectors, 10, 3)
            # fake hosts answer every case correctly: A0 meets D4, so H1 is not assessable by the rule
            self.assertEqual(result['h1'], {'outcome': 'not-assessable', 'hosts': {'claude-code': 'not-assessable'}})
            self.assertEqual(result['paired']['A2-vs-A0']['claude-code']['unchanged'], 10)
            registration, report = heldout.pair(result, arms, ROOT, 'b' * 64, {'A': {'n': 30}, 'C': {'n': 30}})
            self.assertEqual(report.to_dict()['h1']['outcome'], 'not-assessable')
            written = (root / heldout.OUT).read_text()
            for arm in arms.values():
                self.assertNotIn(arm['skillText'].strip().splitlines()[-1], written)
            with self.assertRaises(heldout.HeldoutError) as caught:  # a run of another candidate is refused
                heldout.run_vectors(self.home, ROOT, record['arms']['A1']['runId'], arms['A2']['skillSha256'])
            self.assertEqual(caught.exception.code, 'arm-candidate-mismatch')
            again = []
            heldout.execute_arms(self.home, root, arms, record, cfg=heldout.heldout_config(), models={},
                                 environ={}, secrets=Secrets(), planned=30, run=lambda *a, **k: again.append(k),
                                 build=lambda label, text, work: work)
            self.assertEqual(again, [])  # complete arms are never run again


if __name__ == '__main__':
    unittest.main()


class BuildCleanlinessTests(unittest.TestCase):
    """The plugin build tolerates only this command's own evidence files as working-tree changes."""

    def test_only_heldout_outputs_are_tolerated(self):
        from unittest import mock
        with mock.patch.object(heldout, 'dirty_paths', return_value=set()):
            self.assertFalse(heldout.build_allow_dirty(heldout.ROOT))
        with mock.patch.object(heldout, 'dirty_paths', return_value={heldout.OUT}):
            self.assertTrue(heldout.build_allow_dirty(heldout.ROOT))
        with mock.patch.object(heldout, 'dirty_paths', return_value={heldout.OUT, 'agent_braid/lightning_arm.py'}):
            with self.assertRaises(heldout.HeldoutError) as caught:
                heldout.build_allow_dirty(heldout.ROOT)
            self.assertEqual(caught.exception.code, 'dirty-checkout')
