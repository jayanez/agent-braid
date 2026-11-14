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
        'retention': {'run-1': {'retentionDays': 30, 'expiresAt': '2026-12-15T10:00:00Z'}},
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
        host = manifest(records=[record(source='host-model')], termsDecision={'path': 'terms/anthropic.json',
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

    def test_closed_vocabularies_and_shapes(self):
        cases = {
            'unknown key': manifest(extra=1),
            'unknown record key': manifest(records=[record(prompt='text')]),
            'version': manifest(manifestVersion='braid-lightning-dataset-manifest/v0.2'),
            'kind': manifest(kind='preference'),
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
            'retention days': manifest(retention={'run-1': {'retentionDays': 91, 'expiresAt': '2026-12-15T10:00:00Z'}}),
            'retention run id': manifest(retention={'../x': {'retentionDays': 30, 'expiresAt': '2026-12-15T10:00:00Z'}}),
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

    def test_supervised_is_never_balanced(self):
        self.assertInvalid(manifest(kind='supervised', balance='equal'))
        self.assertInvalid(manifest(kind='supervised', balance='none'))  # a balance report on a supervised export

    def test_host_model_records_require_a_terms_decision(self):
        self.assertInvalid(manifest(records=[record(), record(source='host-model')]))
        self.assertValid(manifest(records=[record(source='local-model')]))


if __name__ == '__main__':
    unittest.main()
