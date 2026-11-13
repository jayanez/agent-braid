# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-003 / SC-003 (T004): typed placeholders and a clean post-redaction scan."""
import json
import unittest
from unittest.mock import patch

from agent_braid import lightning_hosts
from agent_braid import lightning_redact as r

SALT = bytes(range(16))
HOME = '/Users/owner'
# Synthetic shapes only; none is a real credential.
SAMPLES = {
    'secret': ('the value s3cr3t-literal-value here', '[REDACTED:secret]'),
    'token': ('key sk-ant-' + 'A' * 24 + ' and ghp_' + 'b' * 30 + ' and AKIA' + 'C' * 16, '[REDACTED:token]'),
    'bearer': ('Authorization: Bearer ' + 'x' * 32, '[REDACTED:bearer]'),
    'private-key': ('-----BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----', '[REDACTED:private-key]'),
    'email': ('mail Owner@Example.org now', '[REDACTED:email:'),
    'home': (HOME + '/repo/file.py', '~/repo/file.py'),
}


def redactor(salt=SALT):
    return r.Redactor(salt, secrets=['s3cr3t-literal-value'], home=HOME)


class RedactTests(unittest.TestCase):
    def test_every_class_is_detected_then_replaced_by_its_placeholder(self):
        red = redactor()
        for cls, (text, placeholder) in SAMPLES.items():
            with self.subTest(cls=cls):
                self.assertIn(cls, red.scan(text))  # negative control: a disabled pattern fails here
                out = red.clean_text(text)
                self.assertIn(placeholder, out)
                self.assertEqual(red.scan(out), [])

    def test_email_tags_are_stable_within_a_run_and_unlinkable_across_runs(self):
        first, again, other = redactor(), redactor(), redactor(bytes(16))
        tag = first.redact('owner@example.org')
        self.assertRegex(tag, r'^\[REDACTED:email:[0-9a-f]{8}\]$')
        self.assertEqual(tag, again.redact('OWNER@example.org'))
        self.assertNotEqual(tag, other.redact('owner@example.org'))
        self.assertNotEqual(len(r.new_salt()), 0)
        self.assertNotEqual(r.new_salt(), r.new_salt())
        with self.assertRaises(r.RedactionError):
            r.Redactor(b'short')

    def test_json_values_including_keys_are_redacted(self):
        record = {'messages': [{'role': 'user', 'text': SAMPLES['bearer'][0]}],
                  'owner@example.org': {'path': HOME + '/x', 'n': 3, 'ok': True, 'none': None}}
        out = redactor().clean(record)
        dumped = json.dumps(out)
        self.assertEqual(redactor().scan(dumped), [])
        self.assertEqual(out['messages'][0]['role'], 'user')
        self.assertIn('~/x', dumped)
        self.assertNotIn('example.org', dumped)

    def test_an_unclean_result_is_refused(self):
        red = redactor()
        with patch.object(r, 'TOKENS', []), patch.object(red, 'scan', return_value=['token']):
            with self.assertRaises(r.RedactionError) as caught:
                red.clean_text(SAMPLES['token'][0])
        self.assertEqual(caught.exception.code, 'redaction-incomplete')
        self.assertNotIn('sk-ant', str(caught.exception))

    def test_home_prefix_is_not_confused_with_a_longer_name(self):
        self.assertEqual(redactor().redact(HOME + 'x/y'), HOME + 'x/y')

    def test_the_spec069_driver_uses_the_shared_patterns(self):
        self.assertIs(lightning_hosts.SECRET_PATTERNS, r.SECRET_PATTERNS)
        secrets = lightning_hosts.Secrets()
        self.assertEqual(secrets.redact('Bearer ' + 'x' * 20), '[REDACTED]')


if __name__ == '__main__':
    unittest.main()
