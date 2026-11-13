# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 T009 wiring: APO/GEPA arms through `lightning run` with candidate evaluation by SPEC-071 sub-runs."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest

from agent_braid import lightning_algorithm as algorithm
from agent_braid import lightning_arm as arm
from agent_braid import lightning_cli as cli
from agent_braid import lightning_config as config
from agent_braid import lightning_gepa as gepa
from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store
from agent_braid.harness_host_claude import ENV_DENY
from unittest import mock

CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.endswith('_API_KEY') and k not in ENV_DENY}
ROOT = runner.checkout_root()


def profile(name, **algo):
    return config.build({'rollout': {'repetitions': 1, 'hosts': ['claude-code']},
                         'algorithm': {'name': name, **algo}})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def seed_run(self, run_id='seed'):
        status = runner.run(self.home, profile('baseline'), run_id=run_id, fake_hosts=True, environ=CLEAN_ENV)
        self.assertEqual(status['completed'], 10)
        return run_id


class EstimateTests(unittest.TestCase):
    def test_preregistered_arms_are_bounded_by_their_budgets(self):
        for name in ('apo', 'gepa'):
            with self.subTest(name=name):
                cfg = config.build({'algorithm': {'name': name}})
                plan = arm.estimate(cfg, ROOT)
                self.assertEqual(plan['developmentCases'], 10)
                self.assertLessEqual(plan['atMost']['rollouts'], cfg['budget']['maxRollouts'])
                self.assertLessEqual(plan['atMost']['optimizerCalls'], cfg['budget']['maxOptimizerCalls'])
                self.assertFalse(plan['executionAuthorization'])

    def test_apo_estimate_counts_the_three_round_cap(self):
        cfg = config.build({'rollout': {'hosts': ['claude-code'], 'repetitions': 1},
                            'algorithm': {'name': 'apo', 'beamWidth': 2, 'branchFactor': 2, 'rounds': 9,
                                          'minibatch': 5}})
        plan = arm.estimate(cfg, ROOT)
        self.assertEqual(plan['rounds'], 3)
        self.assertEqual(plan['upperBound'], {'optimizerCalls': 3 + 6 + 6, 'rollouts': (2 + 4 + 4) * 5 + 10})

    def test_baseline_is_not_an_arm(self):
        with self.assertRaises(runner.RunnerError):
            arm.estimate(profile('baseline'), ROOT)


class ArmTests(Base):
    def test_gepa_arm_runs_end_to_end_on_fake_hosts_and_replays(self):
        seed = self.seed_run()
        cfg = profile('gepa', rounds=2, minibatch=3)
        summary = arm.run_arm(self.home, cfg, seed_run=seed, run_id='gepa-arm', fake_hosts=True, environ=CLEAN_ENV)
        self.assertEqual((summary['refusal'], summary['label'], summary['seedRun']), (None, 'pipeline-only', seed))
        self.assertGreater(summary['optimizerCalls'], 0)
        self.assertGreater(summary['rollouts'], 0)
        run = store.RunStore(self.home, 'gepa-arm')
        evals = [e for e in run.read_journal() if e['kind'] == 'eval']
        self.assertTrue(evals)
        subs = [r['runId'] for r in store.list_runs(self.home) if r['runId'].startswith('gepa-arm-e')]
        self.assertEqual(len(subs), len(evals))
        def refuse(*_):
            raise AssertionError('replay must not evaluate or call')
        channel = runner.OptimizerChannel('claude-code', transport=refuse, fake=True)
        replayed = algorithm.replay(self.home, 'gepa-arm', gepa.GEPA(evaluator=refuse, optimizer=channel,
                                                                    seed_vectors=arm.seed_vectors(self.home, seed, ROOT)),
                                    cfg)
        self.assertTrue(replayed['selectionsMatch'] and replayed['resultsMatch'])

    def test_model_pin_reaches_every_candidate_sub_run_and_the_optimizer_host(self):
        seed = self.seed_run()
        cfg = profile('gepa', rounds=1, minibatch=2)
        sub_models, host_models = [], []
        real_run, real_host = runner.run, runner.SandboxedHost

        def spy_run(*args, **kwargs):
            sub_models.append(kwargs.get('models'))
            return real_run(*args, **kwargs)

        def spy_host(*args, **kwargs):
            host_models.append(kwargs.get('model'))
            return real_host(*args, **kwargs)

        with mock.patch.object(runner, 'run', spy_run), mock.patch.object(runner, 'SandboxedHost', spy_host):
            summary = arm.run_arm(self.home, cfg, seed_run=seed, run_id='pinned', fake_hosts=True, environ=CLEAN_ENV)
        self.assertEqual(summary['models'], {'claude-code': arm.DEFAULT_MODEL})
        self.assertTrue(sub_models)
        self.assertTrue(all(m == {'claude-code': 'claude-sonnet-5-5'} for m in sub_models))
        self.assertEqual(host_models, ['claude-sonnet-5-5'])

    def test_explicit_model_overrides_the_default(self):
        seed = self.seed_run()
        with mock.patch.object(runner, 'SandboxedHost', wraps=runner.SandboxedHost) as host:
            summary = arm.run_arm(self.home, profile('gepa', rounds=1, minibatch=2), seed_run=seed, run_id='other',
                                  fake_hosts=True, environ=CLEAN_ENV, models={'claude-code': 'claude-opus-5-5'})
        self.assertEqual(summary['models'], {'claude-code': 'claude-opus-5-5'})
        self.assertEqual(host.call_args.kwargs['model'], 'claude-opus-5-5')

    def test_seed_run_must_cover_every_development_case(self):
        cfg = profile('baseline')
        runner.run(self.home, cfg, run_id='short', fake_hosts=True, environ=CLEAN_ENV, case_ids=['DEV-01'])
        with self.assertRaises(runner.RunnerError) as caught:
            arm.seed_vectors(self.home, 'short', ROOT)
        self.assertEqual(caught.exception.code, 'seed-incomplete')

    def test_candidate_plugin_packages_the_candidate_skill(self):
        market = Path(self.tmp.name) / 'built'
        skill = market / 'plugins/agent-braid/skills/analyze/SKILL.md'
        skill.parent.mkdir(parents=True)
        skill.write_text('old')
        text = '---\nname: agent-braid-analyze\ndescription: x\n---\nUse `agent-braid-plan` next.\n'
        plugin = arm.candidate_plugin(market / 'plugins/agent-braid', text, Path(self.tmp.name) / 'copy')
        packaged = (plugin / 'skills/analyze/SKILL.md').read_text()
        self.assertIn('name: analyze', packaged)
        self.assertIn('`plan`', packaged)
        self.assertEqual(skill.read_text(), 'old')


class CliTests(Base):
    def cli(self, *argv):
        parser = argparse.ArgumentParser()
        cli.add_parser(parser.add_subparsers(dest='command'))
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.run(parser.parse_args(['lightning', *argv, '--home', str(self.home)]))
        return code, out.getvalue(), err.getvalue()

    def init(self, algorithm_name):
        code, out, _ = self.cli('init', '--non-interactive', '--algorithm', algorithm_name)
        digest = json.loads(out)['previewDigest']
        self.assertEqual(self.cli('init', '--non-interactive', '--algorithm', algorithm_name, '--apply',
                                  '--preview-digest', digest)[0], 0)

    def test_dry_run_of_an_arm_prints_the_estimate(self):
        self.init('gepa')
        code, out, _ = self.cli('run', '--dry-run')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['algorithm'], 'gepa')

    def test_init_flags_apply_the_preregistered_profile(self):
        flags = ('init', '--non-interactive', '--algorithm', 'apo', '--hosts', 'claude-code', '--beam-width', '2',
                 '--branch-factor', '2', '--rounds', '2', '--minibatch', '5')
        code, out, _ = self.cli(*flags)
        self.assertEqual(code, 0)
        preview = json.loads(out)
        self.assertIn('--beam-width', preview['applyWith'])
        self.assertEqual(self.cli(*flags, '--apply', '--preview-digest', preview['previewDigest'])[0], 0)
        algo = config.load(self.home)['algorithm']
        self.assertEqual((algo['beamWidth'], algo['branchFactor'], algo['rounds'], algo['minibatch']), (2, 2, 2, 5))
        plan = json.loads(self.cli('run', '--dry-run')[1])
        self.assertEqual(plan['upperBound'], {'rollouts': 60, 'optimizerCalls': 9})

    def test_init_flags_are_range_checked(self):
        code, _, err = self.cli('init', '--non-interactive', '--beam-width', '9')
        self.assertEqual(code, 2)
        self.assertIn('config-range', err)

    def test_run_passes_the_model_flag_to_the_arm(self):
        self.init('gepa')
        with mock.patch('agent_braid.lightning_arm.run_arm', return_value={}) as run_arm:
            self.cli('run', '--fake-hosts', '--seed-run', 'seed', '--model', 'claude-opus-5-5')
        self.assertEqual(run_arm.call_args.kwargs['models'], {'claude-code': 'claude-opus-5-5'})
        with mock.patch('agent_braid.lightning_arm.run_arm', return_value={}) as run_arm:
            self.cli('run', '--fake-hosts', '--seed-run', 'seed')
        self.assertIsNone(run_arm.call_args.kwargs['models'])  # run_arm pins DEFAULT_MODEL

    def test_arm_needs_a_seed_run_and_the_development_set(self):
        self.init('apo')
        code, _, err = self.cli('run', '--fake-hosts')
        self.assertEqual(code, 2)
        self.assertIn('--seed-run', err)
        code, _, err = self.cli('run', '--dry-run', '--prompt-set', 'held-out')
        self.assertEqual(code, 2)
        self.assertIn('holdout-contamination', err)


class LabScriptTests(unittest.TestCase):
    def main(self, *argv, env=None):
        from scripts import spec072_development_arms as lab
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env or {}, clear=env is not None), \
                mock.patch.object(lab.runner, 'run', side_effect=AssertionError('must not run')), \
                mock.patch.object(lab.arm, 'run_arm', side_effect=AssertionError('must not run')), \
                mock.patch.object(lab, 'keychain_token', return_value=None), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = lab.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_default_prints_the_cost_summary_and_launches_nothing(self):
        code, out, _ = self.main()
        self.assertEqual(code, 0)
        summary = json.loads(out)['costSummary']
        self.assertEqual(summary['runs'], {'baseline': {'rollouts': 30, 'optimizerCalls': 0},
                                           'apo': {'rollouts': 60, 'optimizerCalls': 9},
                                           'gepa': {'rollouts': 105, 'optimizerCalls': 3}})
        self.assertEqual(summary['atMost'], {'rollouts': 195, 'optimizerCalls': 12})

    def test_execute_refuses_without_the_subscription_token(self):
        code, out, err = self.main('--execute', env={'PATH': os.environ.get('PATH', '')})
        self.assertEqual(code, 2)
        self.assertIn('CLAUDE_CODE_OAUTH_TOKEN is not set', err)
        self.assertIn('costSummary', out)  # the summary is printed first

    def test_execute_refuses_a_paid_route(self):
        code, _, err = self.main('--execute', env={'PATH': os.environ.get('PATH', ''), 'ANTHROPIC_API_KEY': 'x',
                                                   'CLAUDE_CODE_OAUTH_TOKEN': 'y'})
        self.assertEqual(code, 2)
        self.assertIn('refused', err)


if __name__ == '__main__':
    unittest.main()
