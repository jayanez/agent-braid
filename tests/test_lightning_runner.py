# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-071: Braid Lightning runner, reward, hooks and boundaries (fake hosts only; no model is contacted)."""
import ast
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_config as config
from agent_braid import lightning_hooks as hooks
from agent_braid import lightning_reward as reward
from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store
from agent_braid.harness_host_claude import ENV_DENY
from agent_braid.lightning_hosts import parse_claude

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import spec069_scoring as scoring  # noqa: E402

CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.endswith('_API_KEY') and k not in ENV_DENY}
CASES = json.loads((ROOT / runner.PROMPT_FILES['development']).read_text())['cases']


def profile(**rollout):
    return config.build({'rollout': {'repetitions': 1, 'hosts': ['claude-code'], **rollout}})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def run_fake(self, cfg=None, **kwargs):
        kwargs.setdefault('environ', CLEAN_ENV)
        return runner.run(self.home, cfg or profile(), fake_hosts=True, **kwargs)


class RouteTests(unittest.TestCase):
    def test_paid_or_redirected_route_is_refused_by_name_only(self):
        for name in ('FOO_API_KEY', 'ANTHROPIC_API_KEY', 'ANTHROPIC_BASE_URL', 'CLAUDE_CODE_USE_BEDROCK'):
            with self.subTest(name=name), self.assertRaises(runner.RunnerError) as caught:
                runner.env_gate({'HOME': '/x', name: 'sk-secret-value'})
            self.assertEqual(caught.exception.code, 'paid-route-refused')
            self.assertNotIn('sk-secret-value', str(caught.exception))
        runner.env_gate({'HOME': '/x', 'CLAUDE_CODE_OAUTH_TOKEN': 't'})

    def test_parent_gate_checks_provider_keys_only(self):
        runner.parent_gate({'CONTEXT7_API_KEY': 'x', 'SGAI_API_KEY': 'y'})
        for name in ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'ANTHROPIC_BASE_URL'):
            with self.subTest(name=name), self.assertRaises(runner.RunnerError):
                runner.parent_gate({name: 'v'})

    def test_key_source_verdicts(self):
        self.assertIsNone(runner.key_source_verdict('claude-code', 'oauth'))
        self.assertIsNone(runner.key_source_verdict('claude-code', 'none'))  # SPEC-069 fixture assumption
        for host, source in (('claude-code', None), ('claude-code', 'ANTHROPIC_API_KEY'), ('claude-code', 'apiKey'),
                             ('opencode', None), ('opencode', 'none')):
            with self.subTest(host=host, source=source):
                self.assertEqual(runner.key_source_verdict(host, source), 'route-unverified')

    def test_claude_parser_reads_the_key_source(self):
        stdout = json.dumps({'type': 'system', 'subtype': 'init', 'model': 'm', 'apiKeySource': 'oauth'}) + '\n'
        self.assertEqual(parse_claude(stdout).key_source, 'oauth')
        self.assertIsNone(parse_claude(json.dumps({'type': 'system', 'subtype': 'init'})).key_source)

    def test_quota_messages_map_to_budget_stop_names(self):
        from agent_braid.harness_hosts import _BUDGET_STOPS
        self.assertEqual(runner.quota_stop('', 'Weekly limit reached'), 'weekly-stop')
        self.assertEqual(runner.quota_stop('5-hour limit reached', ''), 'five-hour-headroom')
        self.assertIsNone(runner.quota_stop('all good', ''))
        self.assertTrue({'weekly-stop', 'five-hour-headroom'} <= _BUDGET_STOPS)


class PlanTests(unittest.TestCase):
    def test_dry_run_plans_within_budget_and_launches_nothing(self):
        cfg = config.build({'budget': {'maxRollouts': 7}})
        with patch('subprocess.Popen', side_effect=AssertionError('launched')):
            planned = runner.plan(cfg, 'development', ROOT)
        self.assertEqual((planned['planned'], planned['withinBudget']), (len(CASES) * 3 * 2, 7))
        self.assertFalse(planned['executionAuthorization'])


class RewardTests(unittest.TestCase):
    def test_reward_matches_score_case_and_is_deterministic(self):
        case = CASES[0]
        good = [{'kind': case['expect']['kind'], 'request': scoring.reference_request(case), 'accepted': True,
                 'refusalSummary': None,
                 'report': {'interactions': [{'left': p['left'], 'right': p['right'], 'classification': p['classification'],
                                              'constraints': list(p['constraints'])} for p in case['expect']['pairs']]}}]
        sha = reward.check_scoring(ROOT)
        one = reward.compute('r', case, good, canary_hits=0, components=['schema', 'd4', 'canary'], scoring=scoring,
                             scoring_sha256=sha)
        two = reward.compute('r', case, good, canary_hits=0, components=['canary', 'd4', 'schema'], scoring=scoring,
                             scoring_sha256=sha)
        self.assertEqual(reward.canonical(one), reward.canonical(two))
        self.assertEqual(one['d4FirstAttempt'], scoring.score_case(case, good)['validFirstAttempt'])
        self.assertEqual(one['claim'], 'empirical-measurement')
        canary = reward.compute('r', case, good, canary_hits=1, components=['d4'], scoring=scoring, scoring_sha256=sha)
        self.assertFalse(canary['d4FirstAttempt'] or canary['d4WithinRetry'])
        none = reward.compute('r', case, [], canary_hits=0, components=['d4'], scoring=scoring, scoring_sha256=sha)
        self.assertFalse(none['schemaValid'] or none['d4WithinRetry'])

    def test_replay_from_parsed_attempts_is_byte_identical_and_detects_edits(self):
        case = CASES[1]
        attempts = [{'kind': case['expect']['kind'], 'request': scoring.reference_request(case), 'accepted': False,
                     'refusalSummary': 'refused', 'report': None}]
        parsed = reward.parsed_attempts(attempts)
        sha = reward.check_scoring(ROOT)
        args = dict(canary_hits=0, components=['d4'], scoring=scoring, scoring_sha256=sha)
        first = reward.reward_sha256(reward.compute('r', case, reward.scoring_attempts(parsed), **args))
        self.assertEqual(reward.reward_sha256(reward.replay('r', case, parsed, **args)), first)
        edited = [dict(parsed[0], accepted=True)]
        self.assertNotEqual(reward.reward_sha256(reward.replay('r', case, edited, **args)), first)

    def test_changed_scoring_or_prompt_set_is_refused(self):
        with patch.object(reward, 'frozen_hashes', return_value={}):
            with self.assertRaises(reward.RewardError) as caught:
                reward.check_scoring(ROOT)
            self.assertEqual(caught.exception.code, 'scoring-hash-mismatch')
            with self.assertRaises(reward.RewardError) as caught:
                reward.check_prompt_set(ROOT, runner.PROMPT_FILES['held-out'])
            self.assertEqual(caught.exception.code, 'holdout-hash-mismatch')


class HookTests(unittest.TestCase):
    def test_hooks_get_read_only_copies_and_failures_are_contained(self):
        seen = []

        class Recorder(hooks.RolloutHooks):
            def on_rollout_start(self, rollout):
                seen.append(rollout['rolloutId'])
                rollout['rolloutId'] = 'changed'

        record = {'rolloutId': 'r1'}
        with self.assertRaises(hooks.HookFailed) as caught:
            hooks.call(Recorder(), 'on_rollout_start', record)
        self.assertEqual((seen, record['rolloutId'], caught.exception.code), (['r1'], 'r1', 'hook-failed'))
        hooks.call(None, 'on_rollout_start', record)
        with self.assertRaises(ValueError):
            hooks.call(hooks.RolloutHooks(), 'on_enqueue', record)


class PipelineTests(Base):
    """REQ-013: the full fake-host pipeline and its negative variants."""

    def test_fake_pipeline_records_rewards_and_replays(self):
        status = self.run_fake(config.build({'rollout': {'repetitions': 1}}))
        self.assertEqual(status['label'], 'pipeline-only')
        self.assertTrue(status['teardown']['clean'])
        self.assertEqual(status['hosts']['claude-code']['rollouts'], len(CASES))
        self.assertEqual(status['hosts']['opencode']['status'], 'declared-limit')  # OD-2: unverified route
        run = store.RunStore(self.home, status['runId'])
        results = [r.value for r in run.read('result')]
        self.assertTrue(all(r['keySource'] == 'none' and r['label'] == 'pipeline-only' for r in results[:len(CASES)]))
        self.assertTrue(all(r['executionAuthorization'] is False for r in results))
        text = (run.root / 'results.jsonl').read_text()
        for case in CASES:
            self.assertNotIn(case['prompt'], text)  # content-free
        report = runner.report(self.home, status['runId'])
        self.assertTrue(report['replayMatches'])
        self.assertEqual(report['hosts']['claude-code']['firstAttempt'], len(CASES))

    def test_missing_key_source_stops_as_route_unverified(self):
        status = self.run_fake(fake_key_source=None)
        self.assertEqual(status['refusal'], 'route-unverified')
        self.assertEqual(runner.run_status(self.home, status['runId'])['refusals'], ['route-unverified'])

    def test_canary_hit_zeroes_d4(self):
        status = self.run_fake(fake_variant='canary')
        report = runner.report(self.home, status['runId'])
        self.assertEqual(report['hosts']['claude-code']['firstAttempt'], len(CASES) - 1)

    def test_leaked_secret_is_caught(self):
        status = self.run_fake(fake_variant='leak-secret')
        self.assertEqual(status['refusal'], 'credential-leak')
        run = store.RunStore(self.home, status['runId'])
        planted = 'sk-ant-PLANTED-'
        self.assertFalse(any(planted in p.read_text() for p in run.root.glob('*.jsonl')))

    def test_unit_cap_stops_and_resume_is_explicit(self):
        status = self.run_fake(config.build({'rollout': {'repetitions': 1, 'hosts': ['claude-code']},
                                             'budget': {'maxRollouts': 3}}))
        self.assertEqual(status['completed'], 3)
        current = runner.run_status(self.home, status['runId'])
        self.assertEqual(current['completed'], 3)
        resumed = self.run_fake(config.build({'rollout': {'repetitions': 1, 'hosts': ['claude-code']},
                                              'budget': {'maxRollouts': 5}}), run_id=status['runId'], resume=True)
        self.assertEqual(resumed['completed'], 5)
        with self.assertRaises(runner.RunnerError):
            self.run_fake(resume=True)

    def test_failing_hook_fails_only_its_rollout(self):
        class Boom(hooks.RolloutHooks):
            def on_rollout_start(self, rollout):
                if rollout['taskId'] == CASES[0]['id']:
                    raise RuntimeError('boom')

        status = self.run_fake(hooks=Boom())
        results = [r.value for r in store.RunStore(self.home, status['runId']).read('result')]
        self.assertEqual([r['refusal'] for r in results].count('hook-failed'), 1)
        self.assertEqual(status['completed'], len(CASES) - 1)

    def test_subscription_credential_is_passed_but_never_written(self):
        token = 'synthetic-oauth-token-' + 'x' * 24
        status = self.run_fake(environ=dict(CLEAN_ENV, CLAUDE_CODE_OAUTH_TOKEN=token))
        run = store.RunStore(self.home, status['runId'])
        results = [r.value for r in run.read('result')]
        self.assertTrue(results and all(r['credentialPresent'] for r in results))
        self.assertFalse(any(token in p.read_text() for p in run.root.iterdir() if p.is_file()))
        self.assertNotIn(token, json.dumps(status))

    def test_straggler_process_is_detected_and_killed(self):
        status = self.run_fake(fake_variant='straggler')
        self.assertEqual(status['refusal'], 'straggler-process')
        self.assertFalse(status['teardown']['clean'])

    def test_timeout_fails_the_rollout(self):
        real = runner.run_process

        def slow(*args, **kwargs):
            done = real(*args, **kwargs)
            if str(args[0][0]).endswith('claude') and '-p' in args[0]:
                done.timed_out = True
            return done

        with patch.object(runner, 'run_process', slow):
            status = self.run_fake()
        results = [r.value for r in store.RunStore(self.home, status['runId']).read('result')]
        self.assertTrue(results and all(r['refusal'] == 'rollout-timeout' for r in results))
        self.assertEqual(status['completed'], 0)

    def test_paid_key_in_environment_refuses_before_launch(self):
        with patch('subprocess.Popen', side_effect=AssertionError('launched')), \
                self.assertRaises(runner.RunnerError) as caught:
            self.run_fake(environ=dict(CLEAN_ENV, ANTHROPIC_API_KEY='sk-ant-xxxxxxxxxxxx'))
        self.assertEqual(caught.exception.code, 'paid-route-refused')


class CliTests(Base):
    def cli(self, *args):
        from agent_braid.cli import main
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), patch('sys.stderr', err), patch.dict(os.environ, CLEAN_ENV, clear=True):
            code = main(['lightning', *args, '--home', str(self.home)])
        return code, out.getvalue(), err.getvalue()

    def init(self):
        flags = ['--non-interactive', '--hosts', 'claude-code', '--repetitions', '1']
        preview = json.loads(self.cli('init', *flags)[1])
        self.assertEqual(self.cli('init', *flags, '--apply', '--preview-digest', preview['previewDigest'])[0], 0)

    def test_dry_run_fake_run_status_report_and_consent(self):
        self.init()
        code, out, _ = self.cli('run', '--dry-run')
        self.assertEqual((code, json.loads(out)['planned']), (0, len(CASES)))
        code, _, err = self.cli('run')
        self.assertEqual(code, 2)
        self.assertIn('consent-required', err)
        code, out, _ = self.cli('run', '--fake-hosts')
        self.assertEqual(code, 0)
        run_id = json.loads(out)['runId']
        self.assertEqual(json.loads(self.cli('status', '--run-id', run_id)[1])['completed'], len(CASES))
        self.assertTrue(json.loads(self.cli('report', '--run-id', run_id)[1])['replayMatches'])


class BoundaryTests(unittest.TestCase):
    MODULES = ('lightning_runner', 'lightning_reward', 'lightning_hooks', 'lightning_hosts')

    def test_no_execution_listener_or_dependency(self):
        for name in self.MODULES:
            text = (ROOT / 'agent_braid' / f'{name}.py').read_text()
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = [a.name.split('.')[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    roots = [node.module.split('.')[0]]
                else:
                    continue
                for root in roots:
                    self.assertTrue(root in sys.stdlib_module_names or root == 'scripts', (name, root))
                    self.assertNotIn(root, {'socket', 'http', 'urllib', 'asyncio'}, (name, root))
            called = {node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, 'id', '')
                      for node in ast.walk(tree) if isinstance(node, ast.Call)}
            forbidden = {'execute_run', 'recover_run', 'grant_policy_run', 'execute_policy_run', 'recover_policy_run'}
            self.assertFalse(called & forbidden, (name, called & forbidden))
        for name in ('tooling_mcp.py', 'plugin_mcp.py'):
            self.assertNotIn('lightning', (ROOT / 'agent_braid' / name).read_text())


if __name__ == '__main__':
    unittest.main()
