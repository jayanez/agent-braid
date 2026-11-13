# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-011 / SC-011 (procedure_011): the SPEC-049 pair over synthetic held-out results."""
import ast
from pathlib import Path
import unittest

from agent_braid import harness_promotion
from agent_braid.harness_evaluation import (REGISTRATION_FORMAT, REPORT_FORMAT, EvaluationRecord,
                                            Registration)
from agent_braid.lightning_evaluation import LightningEvaluationError, h1_outcome, spec049_pair
from agent_braid.system_one import freeze

ROOT = Path(__file__).resolve().parents[1]
A0, A1, A2 = ('0' * 63 + '1', '0' * 63 + '2', '0' * 63 + 'a')
HELDOUT, PROTOCOL = 'b' * 64, 'c' * 64


def summary(verdict, host='claude-code', first=8):
    return {'overall': 'meets' if verdict == 'meets' else 'negative-result', 'requiredHosts': [host],
            'hosts': {host: {'verdict': verdict, 'trials': 30, 'prompts': 10,
                             'firstAttemptPrompts': first, 'withinRetryPrompts': 10,
                             'firstAttemptPromptsMissed': ['h-01'], 'withinRetryPromptsMissed': []}}}


def arm(label, sha, verdict, canary=0):
    return {'arm': label, 'candidateSha256': sha, 'canaryHits': canary, 'summary': summary(verdict)}


def pair(base_verdict='misses', primary_verdict='meets', **overrides):
    kwargs = {'baseline': arm('A0', A0, base_verdict), 'primary': arm('A2', A2, primary_verdict),
              'heldout_sha256': HELDOUT, 'protocol_sha256': PROTOCOL,
              'costs': {'A': {'rollouts': 30}, 'C': {'rollouts': 30}}}
    kwargs.update(overrides)
    return spec049_pair(**kwargs)


class PairTests(unittest.TestCase):
    def test_formats_and_arms(self):
        registration, report = pair()
        self.assertIs(type(registration), Registration)
        self.assertIs(type(report), EvaluationRecord)
        reg, rep = registration.to_dict(), report.to_dict()
        self.assertEqual(reg['format'], REGISTRATION_FORMAT)
        self.assertEqual(rep['format'], REPORT_FORMAT)
        self.assertEqual({k: (v['arm'], v['candidateSha256']) for k, v in reg['arms'].items()},
                         {'A': ('A0', A0), 'C': ('A2', A2)})
        self.assertEqual(rep['registrationSha256'], registration.sha256)
        self.assertFalse(reg['executionAuthorization'] or rep['executionAuthorization'])
        self.assertEqual(rep['h1'], {'outcome': 'supported', 'hosts': {'claude-code': 'supported'}})

    def test_records_load_through_harness_promotion(self):
        registration, report = pair()
        self.assertEqual(harness_promotion._verified(registration, Registration, REGISTRATION_FORMAT)['arms']['C']['candidateSha256'], A2)
        harness_promotion._verified(report, EvaluationRecord, REPORT_FORMAT)
        # SPEC-073's call shape: a pending human decision over the pair is accepted.
        identity = {'sourceSha256': 'd' * 64, 'host': 'claude-code', 'model': 'claude-sonnet-5-5',
                    'toolSetSha256': 'e' * 64, 'policySha256': 'f' * 64}
        profile = {'candidateSha256': A2, 'scope': 'analyze-skill', 'cohort': 'native',
                   'effects': ['skill-text'], 'identity': identity}
        decision = harness_promotion.decide(
            registration, report, profile=profile, actor={'kind': 'human', 'id': 'owner'},
            decision='pending', safety={'unsafeAdmissions': None, 'authorityViolations': None,
                                        'effectViolations': None}, at=1)
        self.assertEqual(decision.to_dict()['regression'], {'claude-code': 'descriptive-only'})

    def test_arm_c_set_to_a1_is_refused(self):
        for overrides, reason in (({'primary': arm('A1', A1, 'meets')}, 'arm-c-not-a2'),
                                  ({'baseline': arm('A2', A2, 'misses')}, 'arm-a-not-a0')):
            with self.assertRaises(LightningEvaluationError) as caught:
                pair(**overrides)
            self.assertEqual(caught.exception.reason, reason)

    def test_altered_report_breaks_registration_binding(self):
        registration, report = pair()
        other, _ = pair(heldout_sha256='9' * 64)
        self.assertNotEqual(other.sha256, registration.sha256)
        data = report.to_dict()
        data['h1']['outcome'] = 'not-supported'
        tampered = EvaluationRecord(freeze(data), report.canonical_bytes)
        with self.assertRaises(harness_promotion.PromotionError):
            harness_promotion._verified(tampered, EvaluationRecord, REPORT_FORMAT)
        with self.assertRaises(harness_promotion.PromotionError) as caught:
            harness_promotion.decide(other, report, profile={}, actor={}, decision='pending',
                                     safety={}, at=1)
        self.assertEqual(caught.exception.reason, 'registration-mismatch')

    def test_refuses_missing_host_and_bad_bindings(self):
        for overrides in ({'heldout_sha256': 'x'}, {'protocol_sha256': ''},
                          {'costs': {'A': {}}}, {'required_hosts': ('claude-code', 'opencode')},
                          {'primary': {**arm('A2', A2, 'meets'), 'extra': 1}}):
            with self.assertRaises(LightningEvaluationError):
                pair(**overrides)

    def test_candidates_by_hash_only(self):
        registration, report = pair()
        for record in (registration, report):
            self.assertNotIn(b'description', record.canonical_bytes)
            self.assertNotIn(b'text', record.canonical_bytes)


class H1RuleTests(unittest.TestCase):
    def outcome(self, base, primary, canary=(0, 0)):
        _, report = pair(baseline=arm('A0', A0, base, canary[0]),
                         primary=arm('A2', A2, primary, canary[1]))
        return report.to_dict()['h1']['outcome']

    def test_decision_rule(self):
        self.assertEqual(self.outcome('misses', 'meets'), 'supported')
        self.assertEqual(self.outcome('meets', 'meets'), 'not-assessable')
        self.assertEqual(self.outcome('meets', 'misses'), 'not-assessable')
        self.assertEqual(self.outcome('misses', 'misses'), 'not-supported')
        self.assertEqual(self.outcome('misses', 'inconclusive'), 'not-supported')
        self.assertEqual(self.outcome('inconclusive', 'meets'), 'not-supported')

    def test_canary_hit_invalidates_the_arm(self):
        self.assertEqual(self.outcome('misses', 'meets', canary=(0, 1)), 'not-supported')
        self.assertEqual(self.outcome('meets', 'meets', canary=(1, 0)), 'not-supported')

    def test_every_required_host_must_support(self):
        valid = {'valid': True, 'hosts': {'claude-code': {'verdict': 'misses'}, 'opencode': {'verdict': 'misses'}}}
        meets = {'valid': True, 'hosts': {'claude-code': {'verdict': 'meets'}, 'opencode': {'verdict': 'misses'}}}
        self.assertEqual(h1_outcome(valid, meets, ('claude-code', 'opencode')),
                         {'outcome': 'not-supported',
                          'hosts': {'claude-code': 'supported', 'opencode': 'not-supported'}})

    def test_writer_never_calls_decide(self):
        tree = ast.parse((ROOT / 'agent_braid' / 'lightning_evaluation.py').read_text())
        names = {n.attr if isinstance(n, ast.Attribute) else n.id
                 for n in ast.walk(tree) if isinstance(n, (ast.Name, ast.Attribute))}
        self.assertFalse(names & {'decide', 'begin', 'harness_promotion'})


if __name__ == '__main__':
    unittest.main()
