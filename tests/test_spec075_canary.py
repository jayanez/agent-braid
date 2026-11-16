# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T010 (REQ-010 / SC-010): the canary scan over the final dataset and manifest bytes (OD-3)."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_export as export
from agent_braid import lightning_redact as redact
from tests.spec075_fixtures import T0, consent, new_run, rollout

ROOT = Path(__file__).resolve().parents[1]
CORPUS = json.loads((ROOT / 'tests/fixtures/spec074-canaries/corpus.json').read_text())
FIELDS = ('prompt', 'response', 'toolCalls')
OTHER_HOMES = ('/Users/canaryuser/projects/plan.txt', '/home/canaryuser/.ssh/config', CORPUS['home'] + '/x')


def turn(text, field):
    return {'prompt': ('p ' + text, 'r', []), 'response': ('p', 'r ' + text, []),
            'toolCalls': ('p', 'r', [{'name': 'Edit', 'arg': text}])}[field]


def replace_first(lines, entries, line):
    """Swap the first line and keep its manifest entry's hash right, so only the canary scan can catch it."""
    return [line] + lines[1:], [dict(entries[0], sha256=hashlib.sha256(line).hexdigest())] + entries[1:]


def views(data: bytes) -> list[str]:
    text = data.decode()
    out = [text, redact.unquote(text), redact._unescape(text)]
    out += [redact._b64(m.group(0)) for m in redact.B64_RUN.finditer(text)]
    for line in text.splitlines():
        out.append(''.join(redact._leaves(json.loads(line))))
    return out


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'home'
        consent(self.home)
        self.run = new_run(self.home)
        rollout(self.run, 'ro-c0', 'raw-c0', [('clean ask', 'clean answer')], task='task-c', d4=True)

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, name='out', **kwargs):
        options = {'kind': 'rollout', 'level': 'transition', 'balance': 'none', 'now': T0 + 60, **kwargs}
        return export.export_dataset(self.home, ['run-1'], out=self.base / name, **options)

    def refused(self, name='out', **kwargs):
        with self.assertRaises(export.ExportError) as caught:
            self.export(name, **kwargs)
        self.assertEqual(caught.exception.code, 'canary-detected')
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['home'])  # nothing written, no temporary
        return caught.exception


class CleanTests(Base):
    def test_a_clean_fixture_exports_with_canary_scan_clean(self):
        manifest = self.export()
        self.assertEqual(manifest['canaryScan'], 'clean')


class IngestTests(Base):
    """End to end: each corpus canary goes through store ingest, the SPEC-074 adapter and the export."""

    def ingest(self, value_text, field, n):
        rollout(self.run, f'ro-{n}', f'raw-{n}', [turn(value_text, field)], task=f'task-{n}', d4=True)

    def test_every_corpus_class_is_redacted_or_refused_in_every_field(self):
        redacted, refused = 0, 0
        for item in CORPUS['canaries']:
            if item['class'] in ('secret', 'home'):
                continue  # Q2 A residual (literal not passed at ingest) and Q1 A (other user's home): below
            for field in FIELDS:
                with self.subTest(id=item['id'], field=field):
                    self.tmp.cleanup()
                    self.setUp()
                    try:
                        self.ingest(json.dumps(item['record']), field, 1)
                    except Exception:  # pragma: no cover - the store keeps a refused stub instead of raising here
                        pass
                    try:
                        self.export()
                    except export.ExportError as exc:
                        self.assertEqual(exc.code, 'canary-detected')
                        refused += 1
                        continue
                    data = b''.join((self.base / 'out' / n).read_bytes() for n in ('records.jsonl', 'manifest.json'))
                    for view in views(data):
                        self.assertNotIn(item['value'], view)
                    redacted += 1
        self.assertEqual(redacted + refused, (len(CORPUS['canaries']) - 10) * 3)

    def test_another_users_home_path_aborts_the_export(self):  # OD-3 Q1 A
        for n, path in enumerate(OTHER_HOMES):
            for field in FIELDS:
                with self.subTest(path=path, field=field):
                    self.tmp.cleanup()
                    self.setUp()
                    self.ingest(f'see {path} now', field, n)
                    self.refused()

    def test_home_path_forms_are_caught(self):
        for form in ('plain', 'json-escaped', 'url-encoded', 'base64'):
            item = next(c for c in CORPUS['canaries'] if c['class'] == 'home' and c['form'] == form)
            with self.subTest(form=form):
                self.tmp.cleanup()
                self.setUp()
                self.ingest(item['record']['text'], 'prompt', 1)  # one level of encoding, as in the corpus
                self.refused()

    def test_literal_secrets_are_caught_only_when_passed_at_ingest(self):  # OD-3 Q2 A: documented residual
        literal = CORPUS['literalSecrets'][0]
        rollout(self.run, 'ro-l', 'raw-l', [None], task='task-l', d4=True)  # content stored below, with the literal
        self.run.append('trace', {'attemptId': 'raw-l', 'sequence': 1, 'prompt': f'key {literal}', 'response': 'r'},
                        now=T0 + 1, secrets=(literal,))
        self.export('known')
        self.assertNotIn(literal.encode(), (self.base / 'known' / 'records.jsonl').read_bytes())
        rollout(self.run, 'ro-u', 'raw-u', [(f'key {literal}', 'r')], task='task-u', d4=True)  # not passed at ingest
        manifest = self.export('unknown')
        self.assertIn(literal.encode(), (self.base / 'unknown' / 'records.jsonl').read_bytes())  # the residual
        self.assertEqual(manifest['canaryScan'], 'clean')

    def test_unknown_shape_secrets_pass(self):  # OD-3 Q2 A: documented residual
        rollout(self.run, 'ro-f', 'raw-f', [('CANARY-FREE-TEXT-7f3a', 'x')], task='task-f', d4=True)
        self.export()
        self.assertIn(b'CANARY-FREE-TEXT-7f3a', (self.base / 'out' / 'records.jsonl').read_bytes())


class FinalBytesTests(Base):
    """The scan reads the final bytes: canaries planted after the writers and the manifest builder are caught."""

    def planted_after_writer(self, value, name='out'):
        real = export.rollout_records

        def leaky(items, *, level, terms=None):
            lines, entries = real(items, level=level, terms=terms)
            record = json.loads(lines[0])
            record['turns'][0]['response'] = 'answer ' + value
            return replace_first(lines, entries, export.line_bytes(record))

        with patch.object(export, 'rollout_records', leaky):
            return self.refused(name)

    def test_each_corpus_value_and_form_planted_after_the_writer(self):
        for item in CORPUS['canaries']:
            if item['class'] == 'secret' or item['form'] == 'split':
                continue  # a literal is unknown to the export (Q2 A); a split needs two fields (below)
            with self.subTest(id=item['id']):
                self.planted_after_writer(item['record']['text'])  # the value in its corpus form

    def test_a_value_split_across_two_fields_is_caught(self):
        real = export.rollout_records
        token = 'sk-proj-CANARYq9W8e7R6t5Y4u3I2'

        def split(items, *, level, terms=None):
            lines, entries = real(items, level=level, terms=terms)
            record = json.loads(lines[0])
            record['turns'][0]['prompt'], record['turns'][0]['response'] = token[:10], token[10:]
            return replace_first(lines, entries, export.line_bytes(record))

        with patch.object(export, 'rollout_records', split):
            self.refused()

    def test_the_manifest_is_scanned_too(self):
        real = export.build_manifest
        for value in ('task-/Users/canaryuser/x', 'task-/home/canaryuser/x', 'sk-proj-CANARYq9W8e7R6t5Y4u3I2'):
            def leaky(entries, records, **kwargs):
                manifest = real(entries, records, **kwargs)
                manifest['records'][0]['taskId'] = value
                return manifest

            with self.subTest(value=value), patch.object(export, 'build_manifest', leaky):
                self.refused()

    def test_the_current_home_is_caught(self):
        self.planted_after_writer(str(Path.home()) + '/notes.txt')

    def test_a_current_home_outside_users_and_home_is_caught(self):  # the scan reads Path.home() at export time
        with patch.dict(os.environ, {'HOME': '/opt/canary-home'}):
            self.planted_after_writer('/opt/canary-home/notes.txt')

    def test_the_own_home_placeholder_and_plain_paths_pass(self):
        text = 'read ~/notes, /usr/local/bin, /Users, /Users/, /home, /home/, /homework/x, /srv/home/x, ~/home/x'
        rollout(self.run, 'ro-p', 'raw-p', [(text, 'ok')], task='task-p', d4=True)
        self.export()

    def test_home_path_boundaries(self):  # a name after /Users/ or /home/ is enough; it need not be a real home
        for path in ('/home/runner/work', '/Users/Shared/x', '/home/x', '/Users/a', 'at=/home/ci', '"/Users/b/c"',
                     'x-/home/y'):
            with self.subTest(path=path):
                self.tmp.cleanup()
                self.setUp()
                rollout(self.run, 'ro-b', 'raw-b', [(f'see {path}', 'ok')], task='task-b', d4=True)
                self.refused()

    def test_a_raw_attempt_id_typed_in_content_passes(self):  # OD-3 Q2 A: content, not the id field
        rollout(self.run, 'ro-r', 'raw-attempt.name-7', [('mentions raw-attempt.name-7', 'ok')], task='task-r', d4=True)
        manifest = self.export()
        self.assertNotIn('raw-attempt.name-7', json.dumps(manifest))
        self.assertIn(b'mentions raw-attempt.name-7', (self.base / 'out' / 'records.jsonl').read_bytes())

    def test_planted_canary_in_a_tool_call(self):
        real = export.rollout_records

        def leaky(items, *, level, terms=None):
            lines, entries = real(items, level=level, terms=terms)
            record = json.loads(lines[0])
            record['turns'][0]['toolCalls'] = [{'name': 'Edit', 'arg': 'canary.owner@example.org'}]
            return replace_first(lines, entries, export.line_bytes(record))

        with patch.object(export, 'rollout_records', leaky):
            self.refused()


if __name__ == '__main__':
    unittest.main()
