# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-070 REQ-004: Braid Lightning configuration and its published schema."""
import copy
import json
from pathlib import Path
import unittest

from agent_braid import lightning_config as c

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / 'schemas/0.3.0-experimental/lightning-config.schema.json'


def mutated(path, value):
    doc = c.defaults()
    section, key = path.split('.')
    doc[section][key] = value
    return doc


INVALID = [
    (mutated('budget.eurCap', 1), 'config-constant'),
    (mutated('optimizer.route', 'api-key'), 'config-constant'),
    (mutated('promotion.mode', 'automatic'), 'config-constant'),
    (mutated('promotion.executionAuthorization', True), 'config-constant'),
    (mutated('rollout.hosts', []), 'config-range'),
    (mutated('rollout.hosts', ['codex']), 'config-enum'),
    (mutated('rollout.hosts', ['opencode', 'opencode']), 'config-duplicate'),
    (mutated('rollout.repetitions', 6), 'config-range'),
    (mutated('rollout.parallel', True), 'config-type'),
    (mutated('algorithm.name', 'grpo'), 'config-enum'),
    (mutated('target.path', '../etc/passwd'), 'config-path'),
    (mutated('target.path', '/abs/path'), 'config-path'),
    (mutated('target.path', 'a//b'), 'config-path'),
    (mutated('data.freezeSha256', 'ABC'), 'config-type'),
    (mutated('traces.retentionDays', 91), 'config-range'),
    (mutated('export.enabled', 'yes'), 'config-type'),
]


class ConfigTests(unittest.TestCase):
    def test_defaults_validate_and_respect_fixed_constants(self):
        value = c.validate(c.defaults())
        self.assertEqual((value['budget']['eurCap'], value['optimizer']['route'], value['promotion']['mode'],
                          value['promotion']['executionAuthorization']), (0, 'subscription', 'human', False))
        self.assertEqual(value['rollout']['parallel'], 1)
        self.assertEqual(value['traces']['contentConsent'], 'none')

    def test_invalid_documents_are_refused_with_codes(self):
        for doc, code in INVALID:
            with self.subTest(code=code, doc=json.dumps(doc)[:80]), self.assertRaises(c.ConfigError) as caught:
                c.validate(doc)
            self.assertEqual(caught.exception.code, code)

    def test_unknown_missing_keys_and_schema(self):
        doc = c.defaults()
        doc['rollout']['k8s'] = {}
        with self.assertRaises(c.ConfigError) as caught:
            c.validate(doc)
        self.assertEqual(caught.exception.code, 'config-unknown-key')
        doc = c.defaults()
        del doc['budget']
        with self.assertRaises(c.ConfigError) as caught:
            c.validate(doc)
        self.assertEqual(caught.exception.code, 'config-missing-key')
        with self.assertRaises(c.ConfigError):
            c.validate(dict(c.defaults(), schema='braid-lightning-config/v0.2'))

    def test_train_and_holdout_must_differ(self):
        doc = mutated('data.holdout', c.defaults()['data']['train'])
        with self.assertRaises(c.ConfigError):
            c.validate(doc)

    def test_digest_ignores_subset_order_and_detects_changes(self):
        base = c.digest(c.defaults())
        self.assertEqual(c.digest(mutated('rollout.hosts', ['opencode', 'claude-code'])), base)
        self.assertNotEqual(c.digest(mutated('rollout.repetitions', 2)), base)

    def test_parse_refuses_duplicates_nonfinite_and_oversize(self):
        raw = c.to_bytes(c.defaults())
        self.assertEqual(c.parse(raw), c.validate(c.defaults()))
        with self.assertRaises(c.ConfigError):
            c.parse(raw.replace(b'"schema"', b'"schema": "x", "schema"', 1))
        with self.assertRaises(c.ConfigError):
            c.parse(b'{"x": NaN}')
        with self.assertRaises(c.ConfigError):
            c.parse(b' ' * (c.MAX_BYTES + 1))

    def test_published_schema_agrees_with_the_validator(self):
        try:
            import jsonschema
        except ImportError:  # dev dependency; CI installs it
            self.skipTest('jsonschema is a development dependency')
        schema = json.loads(SCHEMA_PATH.read_text())
        jsonschema.Draft202012Validator.check_schema(schema)
        validator = jsonschema.Draft202012Validator(schema)
        self.assertEqual(list(validator.iter_errors(c.defaults())), [])
        for doc, code in INVALID:
            with self.subTest(code=code):
                self.assertTrue(list(validator.iter_errors(doc)), f'schema accepted a document the validator refuses ({code})')
        extra = copy.deepcopy(c.defaults())
        extra['algorithm']['extra'] = 1
        self.assertTrue(list(validator.iter_errors(extra)))
        for path in ('a/./b', 'a/../b', '.', 'ok/path.md'):
            with self.subTest(path=path):
                accepted = not list(validator.iter_errors(mutated('target.path', path)))
                try:
                    c.validate(mutated('target.path', path))
                    runtime = True
                except c.ConfigError:
                    runtime = False
                self.assertEqual(accepted, runtime)


if __name__ == '__main__':
    unittest.main()
