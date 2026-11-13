# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-004 / SC-004 (T005): every canary in every form is caught; none reaches an output."""
import base64
import json
import unittest
from unittest.mock import patch
from urllib.parse import unquote

from agent_braid import lightning_redact as r
from scripts import spec074_canary_corpus as gen

CORPUS = json.loads(gen.CORPUS.read_text())


def leaks(output, value: str) -> bool:
    """The value, or its distinctive core, in the output or any decoded view of it."""
    text = json.dumps(output, ensure_ascii=False)
    joined = ''.join(r._leaves(output))
    views = [text, joined, unquote(text), r._unescape(text)]
    views += [r._b64(m.group(0)) for m in r.B64_RUN.finditer(text)]
    needles = {value, value.split()[-1] if ' ' in value else value}
    return any(n in v for n in needles for v in views)


def outcome(redactor, item):
    try:
        return 'redacted', redactor.clean(item['record'])
    except r.RedactionError as exc:
        return exc.code, None


class CanaryCorpusTests(unittest.TestCase):
    def redactor(self):
        return r.Redactor(bytes(16), secrets=CORPUS['literalSecrets'], home=CORPUS['home'])

    def test_committed_corpus_matches_the_generator(self):
        self.assertEqual(gen.CORPUS.read_bytes(), gen.render())
        forms = {(i['class'], i['form']) for i in CORPUS['canaries']}
        classes = {c for c, _ in gen.CANARIES}
        self.assertEqual(forms, {(c, f) for c in classes for f in gen.FORMS})
        self.assertEqual(classes, {'secret', 'token', 'bearer', 'private-key', 'email', 'home'})

    def test_every_canary_is_caught_in_every_form(self):
        red = self.redactor()
        for item in CORPUS['canaries']:
            with self.subTest(id=item['id']):
                self.assertTrue(red.scan(json.dumps(item['record'])) or red.scan(''.join(r._leaves(item['record']))))
                code, output = outcome(red, item)
                self.assertIn(code, ('redacted', 'redaction-incomplete'))
                if output is not None:
                    self.assertFalse(leaks(output, item['value']))
                    self.assertEqual(red.scan(json.dumps(output)), [])

    def test_a_hidden_split_is_refused(self):
        """A split whose first field holds no recognizable prefix cannot be redacted per field: refused."""
        red = self.redactor()
        refused = {i['id'] for i in CORPUS['canaries'] if i['form'] == 'split' and outcome(red, i)[0] != 'redacted'}
        self.assertTrue({'secret-00-split', 'token-03-split', 'token-05-split', 'email-11-split'} <= refused, refused)

    def test_dropping_base64_handling_is_reported(self):
        """Negative control: without the base64 view a base64 canary leaks, so the corpus test would fail."""
        red = self.redactor()
        with patch.object(r, '_b64', lambda run: ''):
            leaked = [i['id'] for i in CORPUS['canaries'] if i['form'] == 'base64'
                      and (lambda res: res[1] is not None and any(
                          i['value'] in base64.b64decode(m.group(0) + '==').decode('utf-8', 'ignore')
                          for m in r.B64_RUN.finditer(json.dumps(res[1]))))(outcome(red, i))]
        self.assertTrue(leaked)


if __name__ == '__main__':
    unittest.main()
