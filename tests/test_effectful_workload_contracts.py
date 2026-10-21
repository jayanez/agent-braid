# SPDX-License-Identifier: AGPL-3.0-only
"""Structural schema admission stays distinct from semantic model validation."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

from research.workload_lab.model import InvalidWorkload, validate
from tests.test_effectful_workload_model import operation, request

SCHEMA = Path(__file__).resolve().parents[1] / 'specs/024-effectful-workload-lab/contracts/request.schema.json'


class WorkloadContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema = json.loads(SCHEMA.read_text())
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(schema)

    def test_seven_kind_positive_and_per_kind_unknown_fields(self):
        ops = [operation(), operation(kind='config-read'),
               operation(kind='literal-write', value=0),
               operation(kind='derived-write', expression={'int': 0}),
               operation(kind='guarded-write', expression={'int': 0}, guard={'op': 'eq', 'left': {'int': 0}, 'right': {'int': 0}}),
               operation(kind='add-constant', amount=-1),
               operation(kind='external-action', event='send', idempotencyKey='key', outcomes=['error', 'send-then-error'])]
        for op in ops:
            with self.subTest(kind=op['kind']):
                r = request([op]); self.validator.validate(r); validate(r)
                r['operations'][0]['url'] = 'https://example.invalid'
                self.assertFalse(self.validator.is_valid(r))
                with self.assertRaises(InvalidWorkload): validate(r)
                r = request([op]); del r['operations'][0]['resource']
                self.assertFalse(self.validator.is_valid(r))

    def test_structural_refusals_and_semantic_only_checks(self):
        base = request()
        mutations = [({'model': 'integer-batch-v1'}), ({'operations': []}),
                     ({'observation': {'mode': 'exact', 'resources': []}}),
                     ({'caps': {'paths': True, 'steps': 1, 'events': 1}})]
        for changes in mutations:
            r = {**deepcopy(base), **changes}
            self.assertFalse(self.validator.is_valid(r))
            with self.assertRaises(InvalidWorkload): validate(r)
        for field, value in [('id', '\ud800'), ('resource', ''), ('requiredVersion', -1),
                             ('dependencies', ['a', 'a']), ('outcomes', ['success', 'error', 'send-then-error'])]:
            r = request(); r['operations'][0][field] = value
            self.assertFalse(self.validator.is_valid(r))
        # The structural schema deliberately cannot establish these cross-field facts.
        cases = [request([operation(dependencies=['a'])]), request([operation(resource='missing')]),
                 request([operation(), operation()]), request()]
        cases[-1]['initial']['aliases'] = {'left': 'right', 'right': 'left'}
        for r in cases:
            self.assertTrue(self.validator.is_valid(r))
            with self.assertRaises(InvalidWorkload): validate(r)

    def test_effect_declarations_and_observation_aliases(self):
        op = operation(effects={'complete': True, 'reads': ['alias'], 'writes': [], 'emits': []})
        r = request([op]); r['observation'] = {'mode': 'selected-values', 'resources': ['chain', 'y']}
        self.validator.validate(r); validate(r)
        for value in [1, 'true', None]:
            r = request([deepcopy(op)]); r['operations'][0]['effects']['complete'] = value
            self.assertFalse(self.validator.is_valid(r))
            with self.assertRaises(InvalidWorkload): validate(r)
        r = request(); r['observation'] = {'mode': 'selected-values', 'resources': ['x', 'chain']}
        self.validator.validate(r)
        with self.assertRaises(InvalidWorkload): validate(r)
