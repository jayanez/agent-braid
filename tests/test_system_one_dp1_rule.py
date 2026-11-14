# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 DP-1 structural rule: truth table, shadow answers, active advice and owner promotion."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
import os
import subprocess
import unittest
from unittest.mock import patch

from agent_braid import system_one_dp1_rule as rule
from agent_braid import system_one_promotion as promotion
from agent_braid import system_one_shadow as shadow
from agent_braid import tooling_mcp
from agent_braid.cli import main
from agent_braid.plugin_mcp import PluginRouter
from agent_braid.plugin_registry import apply, plan_setup
from tests import test_system_one_shadow as base

ZERO = {name: 0 for name in shadow.RESOURCE_CLASSES}


def classes(**counts):
    return dict(ZERO, **counts)


def pair(**changes):
    """A pair that satisfies every clause; each test flips exactly one."""
    value = {'system2': 'unknown', 'reasonCodes': ['partial-coverage'],
             'effectKinds': {'left': ['write'], 'right': ['write']},
             'resourceClasses': {'left': classes(src=1), 'right': classes(src=1)},
             'sameParentDirCount': 0, 'topDirOverlap': False}
    value.update(changes)
    return value


LEFT, RIGHT = ['repo://r/alpha/one.py'], ['repo://r/beta/two.py']


class RuleTruthTable(unittest.TestCase):
    def advise(self, **changes):
        left = changes.pop('left', LEFT)
        right = changes.pop('right', RIGHT)
        return rule.advise_pair(pair(**changes), left, right)

    def test_all_clauses_hold_is_likely_independent(self):
        self.assertEqual(self.advise(), 'likely-independent')
        self.assertEqual(self.advise(reasonCodes=['partial-coverage', 'read-version']), 'likely-independent')
        self.assertEqual(self.advise(effectKinds={'left': ['read'], 'right': ['read', 'write']}), 'likely-independent')

    def test_negative_control_per_clause(self):
        cases = {
            'system2-unknown': dict(system2='independent-candidate'),
            'system2-conflicting': dict(system2='conflicting'),
            'reason-external-effect': dict(reasonCodes=['external-effect']),
            'reason-mixed': dict(reasonCodes=['partial-coverage', 'external-effect']),
            'reason-dependency': dict(reasonCodes=['partial-coverage', 'dependency-order']),
            'effect-call-left': dict(effectKinds={'left': ['call'], 'right': ['write']}),
            'effect-delete-right': dict(effectKinds={'left': ['write'], 'right': ['delete']}),
            'effect-unknown': dict(effectKinds={'left': ['unknown'], 'right': ['write']}),
            'effect-deploy': dict(effectKinds={'left': ['write'], 'right': ['deploy']}),
            'effect-missing': dict(effectKinds=None),
            'same-parent': dict(sameParentDirCount=1),
            'top-dir-overlap': dict(topDirOverlap=True),
            'lockfile-left': dict(resourceClasses={'left': classes(src=1, lockfile=1), 'right': classes(src=1)}),
            'config-right': dict(resourceClasses={'left': classes(src=1), 'right': classes(config=1)}),
            'generated-left': dict(resourceClasses={'left': classes(generated=1), 'right': classes(src=1)}),
        }
        for name, changes in cases.items():
            with self.subTest(name):
                self.assertEqual(self.advise(**changes), 'undetermined')

    def test_shared_canonical_resource_is_not_independent(self):
        self.assertEqual(self.advise(left=['repo://r/x.py'], right=['repo://r/x.py']), 'undetermined')
        self.assertEqual(self.advise(left=['git://r/x.py'],
                                     right=['git-unsupported://r/x.py?operation=b']), 'undetermined')
        self.assertEqual(self.advise(left=['repo://r/x.py?operation=a'],
                                     right=['repo://r/x.py?operation=b']), 'undetermined')

    def test_malformed_pairs_are_undetermined_and_never_conflicting(self):
        for value in ({}, {'system2': 'unknown'}, pair(effectKinds={'left': None, 'right': ['read']}),
                      pair(resourceClasses=None), pair(topDirOverlap=None), pair(sameParentDirCount=None)):
            self.assertEqual(rule.advise_pair(value, LEFT, RIGHT), 'undetermined')
        self.assertNotEqual(self.advise(system2='conflicting'), 'likely-conflicting')

    def test_canonical_resource_strips_query_and_folds_the_unsupported_scheme(self):
        self.assertEqual(rule.canonical_resource('git-unsupported://r/a/b.py?operation=op-1'), 'git://r/a/b.py')
        self.assertEqual(rule.canonical_resource('git://r/a/b.py'), 'git://r/a/b.py')
        self.assertEqual(rule.canonical_resource('repo://r/a.py?x=1#frag'), 'repo://r/a.py')
        self.assertEqual(rule.shared_canonical(['git://r/a.py'], ['git-unsupported://r/a.py?operation=z']),
                         {'git://r/a.py'})
        self.assertEqual(rule.shared_canonical(['git://r/a.py'], ['git://r/b.py']), set())

    def test_manifest_identity_is_compiled_into_the_shadow_module(self):
        self.assertEqual((rule.BACKEND_ID, rule.manifest_digest()),
                         (shadow.EXPECTED_BACKEND_ID, shadow.EXPECTED_MANIFEST_DIGEST))
        self.assertEqual(rule.BACKEND_KIND, 'rule')


def aim_request(*, left='repo://r/alpha/one.py', right='repo://r/beta/two.py', partial=True):
    value = deepcopy(base.SAMPLE)
    for operation, resource in zip(value['operations'], (left, right)):
        for effect in operation['effects']['declared']:
            effect['resource'] = resource
    if partial:
        value['operations'][1]['effects']['coverage']['status'] = 'partial'
    return value


class ShadowAnswerTests(base.Base):
    def test_shadow_episode_records_the_rule_answer_per_pair(self):
        service = self.service()
        self.invoke(service, aim_request())
        self.invoke(service, aim_request(left='repo://r/alpha/one.py', right='repo://r/alpha/two.py'))
        self.invoke(service, base.SAMPLE)
        independent, same_dir, complete = self.episodes()
        for episode in (independent, same_dir, complete):
            shadow.validate_episode(episode)
            self.assertEqual((episode['systemOne']['status'], episode['systemOne']['reason']), ('answered', None))
            self.assertIs(episode['executionAuthorization'], False)
        self.assertEqual(independent['pairs'][0]['system2'], 'unknown')
        self.assertEqual(independent['systemOne']['answers'][0]['choice'], 'likely-independent')
        self.assertEqual(same_dir['systemOne']['answers'][0]['choice'], 'undetermined')
        self.assertEqual(complete['systemOne']['answers'][0]['choice'], 'undetermined')

    def test_git_modify_versus_delete_of_one_path_is_not_independent(self):
        report = {'analyzer': {'name': 'agent-braid', 'version': '0.1.0-alpha', 'ruleSet': 'exact-resource-footprints-v1'},
                  'operations': [{'instanceId': 'a', 'resources': ['git://r/src/x.py']},
                                 {'instanceId': 'b', 'resources': ['git-unsupported://r/src/x.py?operation=b']}],
                  'summary': {'operationCount': 2, 'pairCount': 1,
                              'classifications': {'independent-candidate': 0, 'ordered': 0,
                                                  'conflicting': 0, 'unknown': 1}},
                  'interactions': [{'left': 'a', 'right': 'b', 'classification': 'unknown', 'sharedResources': [],
                                    'reasons': ['At least one effect footprint is partial or unknown.'],
                                    'constraints': ['serialize-unless-stronger-evidence'],
                                    'evidence': {'coverage': ['complete', 'partial']}}]}
        episode = shadow.build_episode(report, 'analyze-work', 'git')
        shadow.validate_episode(episode)
        self.assertEqual(episode['systemOne']['answers'][0]['choice'], 'undetermined')
        advice = shadow.advise_report(report, 'git')
        self.assertEqual([p['choice'] for p in advice['pairs']], ['undetermined'])

    def test_unmapped_reasons_stay_skipped_without_answers(self):
        report = base.EpisodeTests.report_with(self, ['A sentence outside the table'])
        episode = shadow.build_episode(report, 'analyze-work', 'aim')
        self.assertEqual((episode['systemOne']['status'], episode['systemOne']['answers']), ('skipped', None))

    def test_mismatched_installed_rule_is_refused_without_answers(self):
        with patch.object(shadow, 'EXPECTED_MANIFEST_DIGEST', '0' * 64):
            self.invoke(self.service(), aim_request())
        episode, = self.episodes()
        self.assertEqual((episode['systemOne']['status'], episode['systemOne']['answers']), ('refused', None))


class ParityAndAdviceTests(base.Base):
    def envelope(self, mode, request):
        with patch.object(tooling_mcp, 'uuid', base.counter_uuid()):
            service = self.service(mode)
            value = self.invoke(service, request)
            self.assertTrue(shadow.flush())
            return value

    def test_off_and_shadow_envelopes_are_byte_identical_and_carry_no_advice(self):
        for request in (aim_request(), base.SAMPLE):
            off = json.dumps(self.envelope('off', request), sort_keys=True)
            on = json.dumps(self.envelope('shadow', request), sort_keys=True)
            self.assertEqual(off, on)
            self.assertNotIn('systemOneAdvice', on)

    def test_active_advise_adds_advice_and_changes_nothing_else(self):
        request = aim_request()
        plain = self.envelope('shadow', request)
        advised = self.envelope('advise', request)
        value = advised['result']
        advice = value.pop('systemOneAdvice')
        self.assertEqual(advice['pairs'], [{'left': request['operations'][0]['instanceId'],
                                            'right': request['operations'][1]['instanceId'],
                                            'choice': 'likely-independent', 'ruleId': rule.RULE_ID,
                                            'label': 'not verified'}])
        self.assertEqual((advice['pairsAdvised'], advice['pairsTotal'], advice['label']), (1, 1, 'not verified'))
        self.assertIs(advice['executionAuthorization'], False)
        self.assertEqual(value['report'], plain['result']['report'])  # classification untouched
        self.assertEqual(value['report']['interactions'][0]['classification'], 'unknown')
        self.assertIs(advised['provenance']['executionAuthorization'], False)
        self.assertNotIn('systemOneAdvice', json.dumps(plain))
        self.assertEqual(len(self.episodes()), 2)  # advise also records shadow episodes

    def test_advice_for_a_complete_pair_is_undetermined(self):
        advised = self.envelope('advise', base.SAMPLE)
        self.assertEqual([p['choice'] for p in advised['result']['systemOneAdvice']['pairs']], ['undetermined'])

    def test_advice_failure_never_fails_the_analysis(self):
        with patch.object(shadow, 'advise_report', side_effect=RuntimeError('boom')):
            envelope = self.invoke(self.service('advise'), aim_request())
        self.assertEqual(envelope['status'], 'ok')
        self.assertNotIn('systemOneAdvice', envelope['result'])


class PromotionFlowTests(base.Base):
    def setUp(self):
        super().setUp()
        self.home = self.base / 'agent-braid-home'
        self.home.mkdir(mode=0o700)
        env = patch.dict(os.environ, {'AGENT_BRAID_HOME': str(self.home)})
        env.start()
        self.addCleanup(env.stop)

    def run_cli(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main(['system-one', 'promote', *args])
        return status, out.getvalue(), err.getvalue()

    def seed(self):
        self.invoke(self.service(), aim_request())

    def test_go_and_rollback_round_trip_with_preview_and_confirmation(self):
        self.seed()
        status, out, _ = self.run_cli('--decision-point', 'DP-1', '--go')
        preview = json.loads(out)
        self.assertEqual(status, 0)
        self.assertEqual(promotion.load(self.home), ())  # a preview records nothing
        self.assertEqual(preview['manifestDigest'], shadow.EXPECTED_MANIFEST_DIGEST)
        self.assertIs(preview['executionAuthorization'], False)
        status, _, err = self.run_cli('--decision-point', 'DP-1', '--go', '--confirm', '0' * 64)
        self.assertEqual(status, 2)
        self.assertEqual(promotion.load(self.home), ())
        status, out, _ = self.run_cli('--decision-point', 'DP-1', '--go', '--confirm', preview['previewDigest'])
        self.assertEqual(status, 0)
        record, = promotion.load(self.home)
        self.assertEqual((record['decision'], record['manifestDigest'], record['evidenceDigest']),
                         ('go', shadow.EXPECTED_MANIFEST_DIGEST, preview['evidenceDigest']))
        resolved, _ = promotion.inspect(self.home, 'advise', shadow.EXPECTED_MANIFEST_DIGEST)
        self.assertEqual((resolved['activeMode'], resolved['reason']), ('advise', 'owner-go'))
        # A go pinned to another manifest does not promote.
        resolved, _ = promotion.inspect(self.home, 'advise', '1' * 64)
        self.assertEqual(resolved['activeMode'], 'shadow')

        status, out, _ = self.run_cli('--decision-point', 'DP-1', '--rollback')
        rollback_preview = json.loads(out)
        self.assertEqual(status, 0)
        self.assertEqual(len(promotion.load(self.home)), 1)
        status, _, _ = self.run_cli('--decision-point', 'DP-1', '--rollback', '--confirm',
                                    rollback_preview['previewDigest'])
        self.assertEqual(status, 0)
        resolved, _ = promotion.inspect(self.home, 'advise', shadow.EXPECTED_MANIFEST_DIGEST)
        self.assertEqual((resolved['activeMode'], resolved['reason']), ('off', 'rolled-back'))

    def test_router_serves_advice_only_after_a_confirmed_go(self):
        self.seed()
        repo = self.base / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        preview = plan_setup(self.home, [repo], system_one='advise')
        apply(self.home, preview, preview['previewDigest'])
        self.assertEqual({s.config.system_one for s in PluginRouter(self.home).services.values()}, {'shadow'})
        _, out, _ = self.run_cli('--decision-point', 'DP-1', '--go')
        self.run_cli('--decision-point', 'DP-1', '--go', '--confirm', json.loads(out)['previewDigest'])
        self.assertEqual({s.config.system_one for s in PluginRouter(self.home).services.values()}, {'advise'})

    def test_go_without_shadow_evidence_is_refused(self):
        status, out, err = self.run_cli('--decision-point', 'DP-1', '--go')
        self.assertEqual((status, out), (2, ''))
        self.assertIn('no shadow episodes', err)

    def test_changed_evidence_invalidates_the_preview(self):
        self.seed()
        _, out, _ = self.run_cli('--decision-point', 'DP-1', '--go')
        self.seed()
        status, _, _ = self.run_cli('--decision-point', 'DP-1', '--go', '--confirm', json.loads(out)['previewDigest'])
        self.assertEqual(status, 2)
        self.assertEqual(promotion.load(self.home), ())

    def test_learned_backends_keep_the_gate_and_the_rule_backend_is_exempt(self):
        kwargs = dict(evidence_digest='2' * 64, manifest_digest='3' * 64, decided_on='2026-11-14')
        with self.assertRaises(promotion.PromotionError) as caught:
            promotion.owner_go(self.home, 'DP-1', backend_kind='learned', **kwargs)
        self.assertEqual(caught.exception.code, 'promotion-gated')
        self.assertEqual(promotion.load(self.home), ())
        promotion.owner_go(self.home, 'DP-1', backend_kind=rule.BACKEND_KIND, **kwargs)
        self.assertEqual(len(promotion.load(self.home)), 1)


if __name__ == '__main__':
    unittest.main()
