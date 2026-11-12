# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-002 / SC-002: versioned prompt candidates and their store."""
from pathlib import Path
import stat
import tempfile
import unittest

from agent_braid import lightning_resources as r
from agent_braid import lightning_schema as s
from agent_braid import lightning_store as st

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / r.ORIGIN_PATH).read_text(encoding='utf-8')
NOW = '2026-11-11T10:00:00Z'


def child(parent: str, text: str, **changes) -> dict:
    value = {
        'schema': r.CANDIDATE_SCHEMA, 'sha256': r.sha256_text(text), 'parentSha256': parent,
        'originPath': r.ORIGIN_PATH, 'frontMatterSha256': 'f' * 64, 'algorithm': 'gepa', 'round': 1,
        'optimizerCalls': ['call-1'], 'optimizerTemplateSha256': 'e' * 64,
        'contaminationCheck': [{'inputSha256': 'a' * 64, 'passed': True}],
        'devScore': {'minibatch': {'d4FirstAttempt': 0.6, 'schemaValid': 1.0, 'rollouts': 10}, 'full': None},
        'paretoMember': True, 'createdAt': NOW, 'promotion': 'none', 'executionAuthorization': False}
    value.update(changes)
    return value


class CandidateRecordTests(unittest.TestCase):
    def test_seed_is_the_analyze_skill_body_and_round_trips_canonically(self):
        record, body = r.seed(SKILL, created_at=NOW)
        front, expected = r.split_skill(SKILL)
        self.assertEqual(body, expected)
        self.assertEqual(front + body, SKILL)
        self.assertEqual(record.sha256, r.sha256_text(body))
        self.assertEqual(record.value['frontMatterSha256'], r.sha256_text(front))
        raw = s.canonical_bytes(record.to_dict())
        self.assertEqual(s.canonical_bytes(r.Candidate.parse(s.loads(raw)).to_dict()), raw)

    def test_child_record_parses(self):
        seed, _ = r.seed(SKILL, created_at=NOW)
        self.assertEqual(r.Candidate.parse(child(seed.sha256, 'better guidance\n')).value['round'], 1)

    def test_malformed_records_are_refused_with_codes(self):
        seed, _ = r.seed(SKILL, created_at=NOW)
        base = child(seed.sha256, 'x\n')
        cases = {
            'record-unknown-key': dict(base, prompt='leak'),
            'record-missing-key': {k: v for k, v in base.items() if k != 'round'},
            'candidate-origin': dict(base, originPath='README.md'),
            'record-shape': dict(base, promotion='active'),
            'holdout-contamination': dict(base, contaminationCheck=[{'inputSha256': 'a' * 64, 'passed': False}]),
            'candidate-lineage': dict(base, parentSha256=None),
        }
        for code, value in cases.items():
            with self.subTest(code=code), self.assertRaises(s.LightningSchemaError) as caught:
                r.Candidate.parse(value)
            self.assertEqual(caught.exception.code, code)
        for changes in ({'parentSha256': base['sha256']}, {'optimizerTemplateSha256': None},
                        {'algorithm': 'baseline'}, {'round': 0}):
            with self.subTest(changes=changes), self.assertRaises(s.LightningSchemaError):
                r.Candidate.parse(dict(base, **changes))
        with self.assertRaises(s.LightningSchemaError):
            r.Candidate.parse(dict(base, algorithm='apo'))  # paretoMember is GEPA only
        with self.assertRaises(s.LightningSchemaError):
            r.Candidate.parse(dict(base, executionAuthorization=True))

    def test_text_must_match_its_hash(self):
        with self.assertRaises(s.LightningSchemaError) as caught:
            r.check_text('other text', r.sha256_text('text'))
        self.assertEqual(caught.exception.code, 'candidate-hash-mismatch')
        with self.assertRaises(s.LightningSchemaError):
            r.split_skill('# no front matter\n')

    def test_latest_keeps_identity_and_lineage(self):
        seed, _ = r.seed(SKILL, created_at=NOW)
        first = r.Candidate.parse(child(seed.sha256, 'x\n'))
        rescored = r.Candidate.parse(dict(child(seed.sha256, 'x\n'), paretoMember=False,
                                          createdAt='2026-11-11T11:00:00Z'))
        self.assertFalse(r.latest([seed, first, rescored])[first.sha256].value['paretoMember'])
        changed = r.Candidate.parse(child(seed.sha256, 'x\n', round=2))
        with self.assertRaises(s.LightningSchemaError) as caught:
            r.latest([seed, first, changed])
        self.assertEqual(caught.exception.code, 'candidate-immutable')
        with self.assertRaises(s.LightningSchemaError) as caught:
            r.latest([first])
        self.assertEqual(caught.exception.code, 'candidate-lineage')


class CandidateStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        self.store = st.RunStore(self.home, 'run-1')
        self.store.create(config_digest='c' * 64, now=1000.0)
        self.seed, self.body = r.seed(SKILL, created_at=NOW)

    def tearDown(self):
        self.tmp.cleanup()

    def test_append_read_and_text_round_trip_privately(self):
        self.store.write_candidate_text(self.seed.sha256, self.body)
        self.store.write_candidate_text(self.seed.sha256, self.body)  # idempotent for identical bytes
        self.store.append('candidate', self.seed)
        self.assertEqual([c.sha256 for c in self.store.read('candidate')], [self.seed.sha256])
        self.assertEqual(self.store.candidate_text(self.seed.sha256), self.body)
        for path in (self.store.root / 'candidates', self.store.root / 'candidates.jsonl',
                     self.store.root / 'candidates' / f'{self.seed.sha256}.md'):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode) & 0o077, 0, path)

    def test_record_without_text_or_with_wrong_text_is_refused(self):
        with self.assertRaises(st.StoreError) as caught:
            self.store.append('candidate', self.seed)
        self.assertEqual(caught.exception.code, 'candidate-text-missing')
        with self.assertRaises(st.StoreError) as caught:
            self.store.write_candidate_text(self.seed.sha256, self.body + 'tampered')
        self.assertEqual(caught.exception.code, 'candidate-hash-mismatch')
        self.store.write_candidate_text(self.seed.sha256, self.body)
        path = self.store.root / 'candidates' / f'{self.seed.sha256}.md'
        path.write_text(self.body + 'tampered', encoding='utf-8')
        with self.assertRaises(st.StoreError) as caught:
            self.store.candidate_text(self.seed.sha256)
        self.assertEqual(caught.exception.code, 'candidate-hash-mismatch')
        with self.assertRaises(st.StoreError):
            self.store.candidate_text('../' + 'a' * 61)

    def test_unknown_key_and_kind_mismatch_are_refused(self):
        self.store.write_candidate_text(self.seed.sha256, self.body)
        with self.assertRaises(st.StoreError) as caught:
            self.store.append('candidate', dict(self.seed.to_dict(), text='inline'))
        self.assertEqual(caught.exception.code, 'record-unknown-key')
        with self.assertRaises(st.StoreError):
            self.store.append('rollout', self.seed)
        self.assertEqual(self.store.read('candidate'), [])


if __name__ == '__main__':
    unittest.main()
