# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-073: Lightning promotion through the HAR profile registry (procedures 001-008)."""
from pathlib import Path
import tempfile
import unittest

from agent_braid import lightning_promote as lp
from agent_braid import lightning_store as st
from agent_braid.harness_evaluation import EvaluationRecord, Registration
from agent_braid.lightning_evaluation import spec049_pair
from agent_braid.lightning_resources import sha256_text

ROOT = Path(__file__).resolve().parents[1]
SCOPE = 'lightning.skill.analyze'
BASE_TEXT = '# analyze\n\nbaseline guidance\n'
TEXT = '# analyze\n\nimproved guidance\nnew line\n'
IDENTITY = {'sourceSha256': 'd' * 64, 'host': 'claude-code', 'model': 'claude-sonnet-5-5',
            'toolSetSha256': 'e' * 64, 'policySha256': 'f' * 64}


def summary(verdict):
    return {'hosts': {'claude-code': {'verdict': verdict, 'trials': 30, 'prompts': 10,
                                      'firstAttemptPrompts': 8, 'withinRetryPrompts': 10}}}


def pair(candidate, base_verdict='misses', primary_verdict='meets', base=None):
    base = base or sha256_text(BASE_TEXT)
    return spec049_pair(
        baseline={'arm': 'A0', 'candidateSha256': base, 'canaryHits': 0, 'summary': summary(base_verdict)},
        primary={'arm': 'A2', 'candidateSha256': candidate, 'canaryHits': 0,
                 'summary': summary(primary_verdict)},
        heldout_sha256='b' * 64, protocol_sha256='c' * 64,
        costs={'A': {'rollouts': 30}, 'C': {'rollouts': 30}})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        self.run = st.RunStore(self.home, 'run-1')
        self.run.create(config_digest='c' * 64, now=1000.0)
        self.sha = sha256_text(TEXT)
        self.run.write_candidate_text(self.sha, TEXT)
        self.registration, self.evaluation = pair(self.sha)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, sha=None, scope=SCOPE, **overrides):
        kwargs = {'registration': self.registration, 'evaluation': self.evaluation, 'identity': IDENTITY,
                  **overrides}
        return lp.build_record(self.run, sha or self.sha, scope, **kwargs)

    def refused(self, reason, call):
        with self.assertRaises(lp.PromoteError) as caught:
            call()
        self.assertEqual(caught.exception.reason, reason)


class ScopeMapTests(unittest.TestCase):
    def test_closed_map_has_only_analyze_and_its_path_exists(self):
        self.assertEqual(set(lp.SCOPES), {SCOPE})
        entry = lp.SCOPES[SCOPE]
        self.assertEqual(entry.limit, 32 * 1024)
        self.assertTrue((ROOT / entry.target).is_file())

    def test_unknown_scope_is_refused(self):
        for scope in ('lightning.skill.plan', '', None, 'lightning.skill.analyze '):
            with self.assertRaises(lp.PromoteError) as caught:
                lp.scope_entry(scope)
            self.assertEqual(caught.exception.reason, 'unknown-scope')


class BuildRecordTests(Base):
    """procedure_001 / SC-001."""

    def test_valid_native_record_with_supported_h1(self):
        record = self.build()
        self.assertEqual((record.scope, record.candidateSha256, record.text), (SCOPE, self.sha, TEXT))
        self.assertEqual(record.target, lp.SCOPES[SCOPE].target)
        self.assertEqual(record.heldOutSupport, 'supported')
        self.assertEqual(record.profile['cohort'], 'native')
        self.assertEqual(record.profile['effects'], ['skill-text'])
        self.assertEqual(record.evidence, sorted([self.registration.sha256, self.evaluation.sha256]))
        self.assertFalse(record.executionAuthorization)

    def test_h1_not_supported_is_reported_not_raised(self):
        registration, evaluation = pair(self.sha, base_verdict='meets')
        record = self.build(registration=registration, evaluation=evaluation)
        self.assertEqual(record.heldOutSupport, 'no-held-out-support')
        registration, evaluation = pair(self.sha, primary_verdict='misses')
        self.assertEqual(self.build(registration=registration, evaluation=evaluation).heldOutSupport,
                         'no-held-out-support')

    def test_unknown_scope_refused(self):
        self.refused('unknown-scope', lambda: self.build(scope='lightning.skill.plan'))

    def test_candidate_not_stored(self):
        other = sha256_text('other text\n')
        registration, evaluation = pair(other)
        self.refused('candidate-not-stored',
                     lambda: self.build(sha=other, registration=registration, evaluation=evaluation))

    def test_tampered_stored_text_is_a_digest_mismatch(self):
        path = self.run.root / 'candidates' / f'{self.sha}.md'
        path.write_text(TEXT + 'injected\n')
        self.refused('digest-mismatch', self.build)

    def test_oversize_text_refused(self):
        big = '# analyze\n' + 'x' * (32 * 1024)
        sha = sha256_text(big)
        self.run.write_candidate_text(sha, big)
        registration, evaluation = pair(sha)
        self.refused('text-too-large', lambda: self.build(sha=sha, registration=registration,
                                                          evaluation=evaluation))

    def test_pair_not_naming_the_candidate_refused(self):
        registration, evaluation = pair(sha256_text('other text\n'))
        self.refused('candidate-mismatch', lambda: self.build(registration=registration,
                                                              evaluation=evaluation))

    def test_mismatched_pair_refused(self):
        registration, _ = pair(self.sha, base='9' * 64)
        self.refused('registration-mismatch', lambda: self.build(registration=registration))

    def test_arm_c_equal_to_base_refused(self):
        registration, evaluation = pair(self.sha, base=self.sha)
        self.refused('no-candidate', lambda: self.build(registration=registration, evaluation=evaluation))

    def test_bad_identity_refused(self):
        self.refused('invalid-profile', lambda: self.build(identity={**IDENTITY, 'host': ''}))

    def test_committed_spec072_pair_loads_and_its_winner_is_not_supported(self):
        evidence = ROOT / 'specs/072-lightning-prompt-optimization/evidence'
        registration = lp.load_record(Registration, (evidence / 'heldout-registration.json').read_bytes())
        evaluation = lp.load_record(EvaluationRecord,
                                    (evidence / 'heldout-evaluation-record.json').read_bytes())
        self.assertEqual(evaluation.to_dict()['registrationSha256'], registration.sha256)
        # BL.2 promoted nothing: the committed winner has no held-out support.
        self.assertNotEqual(evaluation.to_dict()['h1']['outcome'], 'supported')

    def test_non_canonical_record_bytes_refused(self):
        raw = self.registration.canonical_bytes
        self.refused('invalid-evaluation', lambda: lp.load_record(Registration, raw + b' '))
        self.refused('invalid-evaluation', lambda: lp.load_record(Registration, b'{'))


if __name__ == '__main__':
    unittest.main()
