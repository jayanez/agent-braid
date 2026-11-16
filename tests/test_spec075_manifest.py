# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T006 (REQ-005, REQ-006 / SC-005, SC-006): manifest builder, atomic write and determinism."""
import copy
import hashlib
import json
import os
from pathlib import Path
import random
import re
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_export as export
from agent_braid import lightning_redact as redact
from agent_braid import trace_adapter
from tests.spec075_fixtures import T0, consent, new_run, rollout

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json').read_text())
NOW = T0 + 3600


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'home'
        consent(self.home)
        first = new_run(self.home, 'run-1')
        rollout(first, 'ro-1', 'raw-one', [('ask héllo', 'answer', [{'name': 'Edit'}]), ('more', 'done')],
                status='succeeded')
        rollout(first, 'ro-2', 'raw-two', [('try', 'wrong')], task='task-b', d4=False, status='failed')
        rollout(first, 'ro-3', 'raw-empty', [None], task='task-c')  # excluded: content-missing
        second = new_run(self.home, 'run-2', created=T0 + 86400)
        rollout(second, 'ro-9', 'raw-nine', [('z', 'z')], task='task-0', status='succeeded')

    def tearDown(self):
        self.tmp.cleanup()

    def export(self, name='out', runs=('run-1', 'run-2'), **kwargs):
        options = {'kind': 'rollout', 'level': 'trajectory', 'now': NOW, **kwargs}
        if options['kind'] == 'rollout':
            options.setdefault('balance', 'none')  # T006 checks the unbalanced manifest; T007 tests balance
        out = self.base / name
        manifest = export.export_dataset(self.home, list(runs), out=out, **options)
        return out, manifest

    def validate(self, manifest):
        try:
            import jsonschema
        except ImportError:  # pragma: no cover - development dependency
            return
        self.assertEqual([e.message for e in jsonschema.Draft202012Validator(SCHEMA).iter_errors(manifest)], [])


class ManifestTests(Base):
    def test_export_writes_exactly_records_and_manifest(self):
        for kind, extra in (('rollout', {}), ('supervised', {'outcome_field': True}), ('supervised', {})):
            for level in export.LEVELS:
                name = f'{kind}-{level}-{bool(extra)}'
                with self.subTest(name=name):
                    out, manifest = self.export(name, kind=kind, level=level, **extra)
                    self.assertEqual(sorted(p.name for p in out.iterdir()), ['manifest.json', 'records.jsonl'])
                    self.assertEqual(json.loads((out / 'manifest.json').read_bytes()), manifest)
                    self.assertEqual((out / 'manifest.json').read_bytes(),
                                     trace_adapter.canonical_bytes(manifest) + b'\n')
                    self.validate(manifest)

    def test_record_hashes_match_the_lines(self):  # SC-003's manifest half, and SC-005
        for kind in export.KINDS:
            out, manifest = self.export(kind, kind=kind, level='transition',
                                        **({'outcome_field': True} if kind == 'supervised' else {}))
            records = (out / 'records.jsonl').read_bytes()
            lines = records.splitlines(keepends=True)
            self.assertEqual(manifest['recordsSha256'], hashlib.sha256(records).hexdigest())
            self.assertEqual([e['sha256'] for e in manifest['records']], [hashlib.sha256(l).hexdigest() for l in lines])
            self.assertEqual([e['recordId'] for e in manifest['records']], [json.loads(l)['recordId'] for l in lines])

    def test_manifest_fields(self):
        _, manifest = self.export()
        self.assertEqual(manifest['redactionVersion'], export.redaction_version())
        self.assertRegex(manifest['redactionVersion'], r'^spec074-redact/[0-9a-f]{16}$')
        self.assertEqual((manifest['termsDecision'], manifest['canaryScan'], manifest['balance'],
                          manifest['balanceReport'], manifest['generatedAt']),
                         (None, 'clean', 'none', [], '2027-01-15T09:00:00Z'))
        self.assertEqual(manifest['exclusions'], {**export.empty_exclusions(), 'content-missing': 1})
        self.assertEqual(manifest['retention'], {'run-1': {'retentionDays': 30, 'expiresAt': '2027-02-14'},
                                                 'run-2': {'retentionDays': 30, 'expiresAt': '2027-02-15'}})
        self.assertEqual(manifest['digest'], export.manifest_digest(manifest))
        self.assertEqual([e['taskId'] for e in manifest['records']], ['task-0', 'task-a', 'task-b'])
        body = {k: v for k, v in manifest.items() if k not in ('generatedAt', 'digest')}
        self.assertEqual(manifest['digest'], hashlib.sha256(trace_adapter.canonical_bytes(body)).hexdigest())

    def test_redaction_version_follows_the_redactor(self):
        base = export.redaction_version()
        self.assertEqual(base, export.redaction_version())
        with patch.object(redact, 'TOKENS', [*redact.TOKENS, re.compile(r'\bnew-[a-z]{8}')]):
            changed = export.redaction_version()
        with patch.object(redact, 'SALT_BYTES', 32):
            salted = export.redaction_version()
        self.assertEqual(len({base, changed, salted}), 3)
        self.assertEqual(base, export.redaction_version())


class DeterminismTests(Base):
    def test_two_exports_are_byte_identical_except_generated_at(self):
        out_a, first = self.export('a')
        cwd = os.getcwd()
        other = self.base / 'elsewhere'
        other.mkdir()
        real_select = export.select

        def shuffled_select(items):
            items = list(items)
            random.Random(11).shuffle(items)
            return real_select(items)

        try:
            os.chdir(other)
            with patch.object(export, 'select', shuffled_select):
                out_b, second = self.export('b', runs=('run-2', 'run-1'), now=NOW + 12345)
        finally:
            os.chdir(cwd)
        self.assertEqual((out_a / 'records.jsonl').read_bytes(), (out_b / 'records.jsonl').read_bytes())
        self.assertNotEqual(first['generatedAt'], second['generatedAt'])
        self.assertEqual({**first, 'generatedAt': None}, {**second, 'generatedAt': None})
        self.assertEqual(first['digest'], second['digest'])  # generatedAt is outside the digest

    def test_no_clock_or_host_path_in_dataset_bytes(self):
        out, manifest = self.export()
        data = (out / 'records.jsonl').read_bytes() + (out / 'manifest.json').read_bytes()
        for value in (str(self.base), str(self.home), 'raw-one', 'raw-two', 'raw-nine', str(int(T0))):
            self.assertNotIn(value.encode(), data)
        self.assertNotIn(b'createdAt', (out / 'records.jsonl').read_bytes())


class CheckTests(Base):
    def setUp(self):
        super().setUp()
        out, self.manifest = self.export()
        self.records = (out / 'records.jsonl').read_bytes()
        self.sources = {(e['runId'], e['rolloutId'], e['attemptId']): e['source'] for e in self.manifest['records']}

    def refused(self, mutate, records=None, sources=None):
        manifest = copy.deepcopy(self.manifest)
        mutate(manifest)
        manifest['digest'] = export.manifest_digest(manifest)
        with self.assertRaises(export.ExportError) as caught:
            export.check_manifest(manifest, self.records if records is None else records,
                                  self.sources if sources is None else sources)
        self.assertEqual(caught.exception.code, 'invalid-manifest')

    def test_valid_manifest_passes(self):
        export.check_manifest(self.manifest, self.records, self.sources)

    def test_builder_checks(self):
        row = {'taskId': 'task-a', 'successes': 1, 'failures': 0, 'unknown': 0, 'keptPerOutcome': 0, 'dropped': 0,
               'singleOutcome': True}
        cases = {
            'records hash': lambda m: m.update(recordsSha256='0' * 64),
            'record hash': lambda m: m['records'][0].update(sha256='0' * 64),
            'record id': lambda m: m['records'][0].update(recordId='r-' + '0' * 16),
            'turn range order': lambda m: m['records'][0].update(turnRange=[2, 0]),
            'unsorted limits': lambda m: m['records'][0].update(limits=['truncated', 'text-level-merge']),
            'retention misses a run': lambda m: m['retention'].pop('run-2'),
            'retention cites another run': lambda m: m['retention'].update({'run-x': m['retention']['run-1']}),
            'duplicate balance task': lambda m: m.update(balanceReport=[row, row]),
            'single outcome keeps records': lambda m: m.update(balanceReport=[{**row, 'keptPerOutcome': 1}]),
            'supervised balance exclusions': lambda m: (m.update(kind='supervised'),
                                                        m['exclusions'].update(balance=1)),
            'supervised balanced': lambda m: m.update(kind='supervised', balance='equal'),
            'host labelled fixture': lambda m: None,
            'host without terms decision': lambda m: m['records'][0].update(source='host-model'),
            'not scanned': lambda m: m.update(canaryScan='skipped'),
        }
        first = self.manifest['records'][0]
        for name, mutate in cases.items():
            sources = dict(self.sources)
            if name in ('host labelled fixture', 'host without terms decision'):
                sources[(first['runId'], first['rolloutId'], first['attemptId'])] = 'host-model'
            with self.subTest(name=name):
                self.refused(mutate, sources=sources)
        self.refused(lambda m: None, records=self.records + b'{}\n')
        manifest = copy.deepcopy(self.manifest)
        manifest['seed'] = 9  # digest not recomputed
        with self.assertRaises(export.ExportError):
            export.check_manifest(manifest, self.records, self.sources)


    def test_the_export_runs_the_checks(self):
        real = export._retention

        def drops_a_run(expiry, days, run_ids):
            value = real(expiry, days, run_ids)
            value.pop(sorted(value)[-1])
            return value

        with patch.object(export, '_retention', drops_a_run), self.assertRaises(export.ExportError) as caught:
            self.export('unchecked')
        self.assertEqual(caught.exception.code, 'invalid-manifest')
        self.assertFalse((self.base / 'unchecked').exists())
        real_writer = export.rollout_records

        def wrong_hash(items, *, level, terms=None):
            lines, entries = real_writer(items, level=level, terms=terms)
            return lines, [dict(entries[0], sha256='0' * 64)] + entries[1:]

        with patch.object(export, 'rollout_records', wrong_hash), self.assertRaises(export.ExportError) as caught:
            self.export('unchecked')
        self.assertEqual(caught.exception.code, 'invalid-manifest')
        self.assertFalse((self.base / 'unchecked').exists())


class WriteTests(Base):
    def test_existing_output_is_refused_and_untouched(self):
        out = self.base / 'taken'
        out.mkdir()
        (out / 'keep.txt').write_text('x')
        with self.assertRaises(export.ExportError) as caught:
            self.export('taken')
        self.assertEqual(caught.exception.code, 'output-not-empty')
        self.assertEqual([p.name for p in out.iterdir()], ['keep.txt'])
        empty = self.base / 'empty'
        empty.mkdir()
        self.export('empty')
        self.assertEqual(sorted(p.name for p in empty.iterdir()), ['manifest.json', 'records.jsonl'])

    def test_a_failure_while_writing_leaves_nothing(self):
        real = os.fdopen
        calls = []

        out = self.base / 'broken'

        def failing(fd, *args, **kwargs):
            calls.append(out.exists())  # nothing is written into the output itself
            if len(calls) == 2:  # the manifest, after records.jsonl was written
                os.close(fd)
                raise OSError('disk full')
            return real(fd, *args, **kwargs)

        with patch.object(export.os, 'fdopen', failing), self.assertRaises(export.ExportError) as caught:
            self.export('broken')
        self.assertEqual(caught.exception.code, 'path-refused')
        self.assertIsNone(caught.exception.__cause__)
        self.assertEqual(calls, [False, False])
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['home'])

    def test_an_interrupt_while_writing_leaves_nothing(self):
        real = os.fdopen
        calls = []

        def interrupted(fd, *args, **kwargs):
            calls.append(fd)
            if len(calls) == 2:
                os.close(fd)
                raise KeyboardInterrupt
            return real(fd, *args, **kwargs)

        with patch.object(export.os, 'fdopen', interrupted), self.assertRaises(KeyboardInterrupt):
            self.export('interrupted')
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['home'])

    def test_the_output_appears_only_by_rename(self):
        out = self.base / 'renamed'
        real = os.rename
        seen = []

        def watched(source, target):
            seen.append((Path(source).parent == out.parent, Path(source).name.startswith('.export-'),
                         Path(target) == out, out.exists(), sorted(p.name for p in Path(source).iterdir())))
            return real(source, target)

        with patch.object(export.os, 'rename', watched):
            self.export('renamed')
        self.assertEqual(seen, [(True, True, True, False, ['manifest.json', 'records.jsonl'])])

    def test_files_are_private(self):
        out, _ = self.export('private')
        self.assertEqual(out.stat().st_mode & 0o777, 0o700)
        for name in ('records.jsonl', 'manifest.json'):
            self.assertEqual((out / name).stat().st_mode & 0o777, 0o600)

    def test_symlinked_output_is_refused(self):
        target = self.base / 'target'
        target.mkdir()
        (self.base / 'link').symlink_to(target)
        (self.base / 'dirlink').symlink_to(self.base, target_is_directory=True)
        for name in ('link', 'dirlink/inner'):
            with self.subTest(name=name), self.assertRaises(export.ExportError) as caught:
                self.export(name)
            self.assertEqual(caught.exception.code, 'path-refused')
        self.assertEqual(list(target.iterdir()), [])

    def test_refusals_write_nothing(self):
        cases = {
            'canary-detected': lambda: self.planted('n3'),
            'terms-gate-missing': lambda: self.host('n5'),
            'invalid-argument': lambda: self.export('n2', kind='rollout', balance='ratio'),
            'no-records': lambda: (consent(self.home, 'none'), self.export('n1')),  # last: consent stays none
        }
        for code, run in cases.items():
            with self.subTest(code=code), self.assertRaises(export.ExportError) as caught:
                run()
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['home'])
        for kwargs in ({'kind': 'other'}, {'seed': -1}, {'seed': True}, {'kind': 'supervised', 'balance': 'equal'},
                       {'kind': 'rollout', 'outcome_field': True}, {'level': 'step'}):
            with self.subTest(kwargs=kwargs), self.assertRaises(export.ExportError) as caught:
                self.export('n4', **kwargs)
            self.assertEqual(caught.exception.code, 'invalid-argument')

    def host(self, name):
        run = new_run(self.home, 'run-host')
        rollout(run, 'ro-h', 'raw-host', [('host prompt', 'host answer')], label=None, status='succeeded')
        return self.export(name, runs=('run-1', 'run-host'))

    def planted(self, name):
        real = export.rollout_records

        def leaky(items, *, level, terms=None):
            lines, entries = real(items, level=level, terms=terms)
            planted = [line.replace(b'answer', b'sk-' + b'A1b2C3d4' * 3) for line in lines]
            assert planted != lines
            return planted, [dict(e, sha256=hashlib.sha256(line).hexdigest()) for e, line in zip(entries, planted)]

        with patch.object(export, 'rollout_records', leaky):
            return self.export(name)


if __name__ == '__main__':
    unittest.main()
