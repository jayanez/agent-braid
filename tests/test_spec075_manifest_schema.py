# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T002 (REQ-005 / SC-005): the dataset manifest schema accepts a valid manifest and refuses broken ones."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json'
HEX = 'a' * 64


def record(**overrides) -> dict:
    value = {'recordId': 'r-0123456789abcdef', 'sha256': HEX, 'runId': 'run-1', 'taskId': 'case-1',
             'groupId': 'group-1', 'rolloutId': 'claude-code.case-1.r1', 'attemptId': 'attempt-0123456789abcdef',
             'turnRange': [0, 2], 'consentLevel': 'redacted', 'source': 'fixture', 'outcome': 'success',
             'limits': ['text-level-merge']}
    value.update(overrides)
    return value


def manifest(**overrides) -> dict:
    value = {
        'manifestVersion': 'braid-lightning-dataset-manifest/v0.1', 'kind': 'rollout', 'level': 'trajectory',
        'generatedAt': '2026-11-15T10:00:00Z', 'seed': 0, 'balance': 'equal',
        'orderingKey': ['taskId', 'groupId', 'rolloutId', 'attemptId', 'turnIndex'],
        'redactionVersion': 'spec074-redact/' + HEX, 'termsDecision': None, 'canaryScan': 'clean',
        'exclusions': {'no-consent': 0, 'consent-none': 1, 'unredacted': 0, 'content-missing': 0, 'balance': 3,
                       'overlong': 0, 'retention-expired': 0},
        'balanceReport': [{'taskId': 'case-1', 'successes': 5, 'failures': 2, 'unknown': 0, 'keptPerOutcome': 2,
                           'dropped': 3, 'singleOutcome': False}],
        'retention': {'run-1': {'retentionDays': 30, 'expiresAt': '2026-12-15'}},
        'records': [record()], 'recordsSha256': HEX, 'digest': HEX,
    }
    value.update(overrides)
    return value


class ManifestSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import jsonschema
        except ImportError:  # pragma: no cover - development dependency
            raise unittest.SkipTest('jsonschema is a development dependency')
        schema = json.loads(SCHEMA_PATH.read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        cls.validator = jsonschema.Draft202012Validator(schema)

    def assertValid(self, value):
        errors = [e.message for e in self.validator.iter_errors(value)]
        self.assertEqual(errors, [])

    def assertInvalid(self, value):
        self.assertFalse(self.validator.is_valid(value))

    def test_identity(self):
        schema = json.loads(SCHEMA_PATH.read_text())
        self.assertEqual(schema['$schema'], 'https://json-schema.org/draft/2020-12/schema')
        self.assertTrue(schema['$id'].endswith('/schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json'))
        self.assertFalse(schema['additionalProperties'])

    def test_valid_manifests_pass(self):
        self.assertValid(manifest())
        self.assertValid(manifest(kind='supervised', balance='none', balanceReport=[],
                                  records=[record(limits=[], outcome='unknown', turnRange=[1, 1])]))
        self.assertValid(manifest(level='transition'))
        host = manifest(records=[record(source='host-model')], termsDecision={'path': 'terms/decision.json',
                                                                             'sha256': HEX})
        self.assertValid(host)

    def test_missing_record_hash_or_redaction_version_fails(self):
        broken = manifest()
        del broken['records'][0]['sha256']
        self.assertInvalid(broken)
        broken = manifest()
        del broken['redactionVersion']
        self.assertInvalid(broken)
        self.assertInvalid(manifest(redactionVersion=''))

    def test_every_top_level_field_is_required(self):
        for key in manifest():
            broken = manifest()
            del broken[key]
            with self.subTest(key=key):
                self.assertInvalid(broken)

    def test_every_record_field_is_required(self):
        for key in record():
            broken = manifest()
            del broken['records'][0][key]
            with self.subTest(key=key):
                self.assertInvalid(broken)

    def test_nested_objects_require_every_field_and_refuse_unknown_keys(self):
        nested = {
            'exclusions': lambda m: m['exclusions'],
            'balanceReport item': lambda m: m['balanceReport'][0],
            'retention entry': lambda m: m['retention']['run-1'],
            'termsDecision': lambda m: m['termsDecision'],
        }
        for name, part in nested.items():
            base = manifest(termsDecision={'path': 'terms/decision.json', 'sha256': HEX})
            for key in list(part(base)):
                broken = copy.deepcopy(base)
                del part(broken)[key]
                with self.subTest(part=name, missing=key):
                    self.assertInvalid(broken)
            broken = copy.deepcopy(base)
            part(broken)['extra'] = 0
            with self.subTest(part=name, unknown='extra'):
                self.assertInvalid(broken)

    def test_counters_are_not_negative(self):
        for reason in manifest()['exclusions']:
            with self.subTest(exclusion=reason):
                self.assertInvalid(manifest(exclusions={**manifest()['exclusions'], reason: -1}))
        for key in ('successes', 'failures', 'unknown', 'keptPerOutcome', 'dropped'):
            broken = manifest()
            broken['balanceReport'][0][key] = -1
            with self.subTest(balanceReport=key):
                self.assertInvalid(broken)
        self.assertInvalid(manifest(records=[record(turnRange=[-1, 2])]))

    def test_retention_days_and_expiry_date(self):
        for days in (0, 91, 1.5):
            with self.subTest(days=days):
                self.assertInvalid(manifest(retention={'run-1': {'retentionDays': days, 'expiresAt': '2026-12-15'}}))
        for days in (1, 90):
            self.assertValid(manifest(retention={'run-1': {'retentionDays': days, 'expiresAt': '2026-12-15'}}))
        for expiry in ('2026-99-99', '2026-13-01', '2026-12-32', '2026-12-15T10:00:00Z', '26-12-15', '2026-1-5'):
            with self.subTest(expiry=expiry):
                self.assertInvalid(manifest(retention={'run-1': {'retentionDays': 30, 'expiresAt': expiry}}))
        for stamp in ('2026-99-99T99:99:99Z', '2026-11-15T24:00:00Z', '2026-11-15T10:00:00+01:00'):
            with self.subTest(generatedAt=stamp):
                self.assertInvalid(manifest(generatedAt=stamp))

    def test_terms_decision_path_is_relative_and_safe(self):
        for path in ('terms/decision.json', 'decision.json', 'terms/2026-11-14_provider.v1.json'):
            with self.subTest(path=path):
                self.assertValid(manifest(termsDecision={'path': path, 'sha256': HEX}))
        for path in ('/Users/someone/terms.json', '../terms.json', 'terms/../x.json', 'terms/./x.json',
                     'Provider permits training\nyes', 'terms decision.json', 'terms\tx.json', '', 'terms/',
                     '~/terms.json', 'C:\\terms.json', 'x' * 257):
            with self.subTest(path=path):
                self.assertInvalid(manifest(termsDecision={'path': path, 'sha256': HEX}))
        self.assertInvalid(manifest(termsDecision={'path': 'terms/decision.json', 'sha256': 'A' * 64}))

    def test_attempt_id_is_a_spec074_pseudonym(self):
        for kind in ('attempt', 'turn', 'strand', 'episode'):
            with self.subTest(kind=kind):
                self.assertValid(manifest(records=[record(attemptId=f'{kind}-0123456789abcdef')]))
        for value in ('attempt-0123456789abcde', 'attempt-0123456789abcdef0', 'attempt-0123456789ABCDEF',
                      'session-0123456789abcdef', 'loom-0123456789abcdef', '0', 'attempt-'):
            with self.subTest(value=value):
                self.assertInvalid(manifest(records=[record(attemptId=value)]))

    def test_identifier_patterns(self):
        for key in ('runId', 'taskId', 'groupId', 'rolloutId'):
            for value in ('', '-x', 'a b', 'a/b', 'x' * 65):
                with self.subTest(key=key, value=value):
                    self.assertInvalid(manifest(records=[record(**{key: value})]))
        self.assertInvalid(manifest(balanceReport=[{**manifest()['balanceReport'][0], 'taskId': 'a b'}]))

    def test_closed_vocabularies_and_shapes(self):
        cases = {
            'unknown key': manifest(extra=1),
            'unknown record key': manifest(records=[record(prompt='text')]),
            'version': manifest(manifestVersion='braid-lightning-dataset-manifest/v0.2'),
            'kind': manifest(kind='preference'),
            'balance ratio (OD-2: no ratio parameter)': manifest(balance='ratio'),
            'level': manifest(level='step'),
            'ordering key': manifest(orderingKey=['taskId']),
            'canary scan': manifest(canaryScan='hit'),
            'seed': manifest(seed=-1),
            'generatedAt': manifest(generatedAt='2026-11-15 10:00'),
            'digest': manifest(digest='A' * 64),
            'records hash': manifest(recordsSha256='abc'),
            'no records': manifest(records=[]),
            'exclusion reason': manifest(exclusions={**manifest()['exclusions'], 'other': 1}),
            'exclusion count': manifest(exclusions={**manifest()['exclusions'], 'balance': -1}),
            'retention days': manifest(retention={'run-1': {'retentionDays': 91, 'expiresAt': '2026-12-15'}}),
            'retention run id': manifest(retention={'../x': {'retentionDays': 30, 'expiresAt': '2026-12-15'}}),
            'consent': manifest(records=[record(consentLevel='none')]),
            'source': manifest(records=[record(source='rollout')]),
            'outcome': manifest(records=[record(outcome='partial')]),
            'limit': manifest(records=[record(limits=['lossy'])]),
            'duplicate limit': manifest(records=[record(limits=['truncated', 'truncated'])]),
            'record id': manifest(records=[record(recordId='record-1')]),
            'raw attempt id': manifest(records=[record(attemptId='0')]),
            'turn range': manifest(records=[record(turnRange=[0])]),
            'record hash': manifest(records=[record(sha256='0' * 63)]),
            'terms decision shape': manifest(termsDecision={'path': 'terms/x.json'}),
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                self.assertInvalid(value)

    def test_balance_none_has_an_empty_report(self):
        self.assertInvalid(manifest(balance='none'))
        self.assertValid(manifest(balance='none', balanceReport=[]))

    def test_supervised_is_never_balanced(self):
        self.assertInvalid(manifest(kind='supervised', balance='equal'))
        self.assertInvalid(manifest(kind='supervised', balance='none'))  # a balance report on a supervised export

    def test_host_model_records_require_a_terms_decision(self):
        self.assertInvalid(manifest(records=[record(), record(source='host-model')]))
        self.assertValid(manifest(records=[record(source='local-model')]))


if __name__ == '__main__':
    unittest.main()
