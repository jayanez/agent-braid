# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T008 (REQ-008 / SC-008): the terms gate reads an owner terms decision record (E5, OD-1).

OD-1 is deferred: no real record exists. Every record here is SYNTHETIC, written to a temporary plugin home, names
the fictional provider below and is never committed; it says nothing about any real provider's terms.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_export as export
from tests.spec075_fixtures import T0, consent, new_run, rollout

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / 'schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json').read_text())
NOW = T0 + 60  # 2027-01-15
SYNTHETIC = {'schema': 'braid-lightning-terms-decision/v0.1', 'provider': 'SYNTHETIC test provider (not real)',
             'host': 'claude-code', 'models': ['synthetic-model-1'],
             'terms': {'version': 'synthetic-terms-0'}, 'reviewedOn': '2027-01-01', 'validUntil': '2027-06-30',
             'outcome': 'permits-training'}
RECORD = 'terms/synthetic-test.json'


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'home'
        consent(self.home)
        run = new_run(self.home)
        rollout(run, 'ro-f0', 'raw-f0', [('fixture ok', 'yes')], task='task-f', d4=True)
        rollout(run, 'ro-f1', 'raw-f1', [('fixture bad', 'no')], task='task-f', d4=False)
        host = new_run(self.home, 'run-host')
        rollout(host, 'ro-h0', 'raw-h0', [('host ok', 'host yes')], task='task-h', d4=True, label='host-run',
                model='synthetic-model-1')
        rollout(host, 'ro-h1', 'raw-h1', [('host bad', 'host no')], task='task-h', d4=False, label='host-run',
                model='synthetic-model-1')

    def tearDown(self):
        self.tmp.cleanup()

    def record(self, value=None, *, name=RECORD, raw=None, mode=0o600):
        path = self.home / 'lightning' / name
        path.parent.mkdir(mode=0o700, exist_ok=True)
        data = raw if raw is not None else json.dumps(SYNTHETIC if value is None else value).encode()
        path.write_bytes(data)
        path.chmod(mode)
        return data

    def export(self, name='out', runs=('run-1', 'run-host'), **kwargs):
        options = {'kind': 'rollout', 'level': 'trajectory', 'now': NOW, 'terms_decision': RECORD, **kwargs}
        return export.export_dataset(self.home, list(runs), out=self.base / name, **options)

    def refused(self, name='refused', **kwargs):
        with self.assertRaises(export.ExportError) as caught:
            self.export(name, **kwargs)
        self.assertEqual(caught.exception.code, 'terms-gate-missing')
        self.assertIsNone(caught.exception.__cause__)
        self.assertFalse((self.base / name).exists())
        for secret in (str(self.home), 'synthetic-test', 'SYNTHETIC test provider'):
            self.assertNotIn(secret, str(caught.exception))
        return caught.exception


class GateTests(Base):
    def test_no_record_refuses_every_host_unit_before_writing(self):
        self.refused(terms_decision=None)
        self.refused()  # named, but the file does not exist
        manifest = self.export('fixture-only', runs=('run-1',), terms_decision=None)
        self.assertIsNone(manifest['termsDecision'])

    def test_a_permitting_synthetic_record_lets_matching_units_through(self):
        raw = self.record()
        manifest = self.export()
        self.assertEqual(manifest['termsDecision'], {'path': RECORD, 'sha256': hashlib.sha256(raw).hexdigest()})
        self.assertEqual(sorted(e['source'] for e in manifest['records']), ['fixture'] * 2 + ['host-model'] * 2)
        try:
            import jsonschema
            self.assertEqual(list(jsonschema.Draft202012Validator(SCHEMA).iter_errors(manifest)), [])
        except ImportError:  # pragma: no cover
            pass
        self.assertIn(b'host yes', (self.base / 'out' / 'records.jsonl').read_bytes())

    def test_a_fixture_only_export_cites_no_record(self):
        self.record()
        self.assertIsNone(self.export('f', runs=('run-1',))['termsDecision'])

    def test_the_record_binds_host_and_model(self):
        cases = {
            'other host': {**SYNTHETIC, 'host': 'opencode'},
            'other model': {**SYNTHETIC, 'models': ['synthetic-model-2']},
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                self.record(value)
                self.refused(name)
        self.record()
        other = new_run(self.home, 'run-other')
        rollout(other, 'ro-o0', 'raw-o0', [('o', 'o')], task='task-o', d4=True, label='host-run',
                model='synthetic-model-2')  # one unit the record does not cover
        self.refused('mixed', runs=('run-1', 'run-host', 'run-other'))
        bare = new_run(self.home, 'run-bare')
        rollout(bare, 'ro-b0', 'raw-b0', [('b', 'b')], task='task-b', d4=True, label='host-run')  # no model
        self.refused('bare', runs=('run-1', 'run-bare'))
        opencode = new_run(self.home, 'run-oc')
        rollout(opencode, 'ro-c0', 'raw-c0', [('c', 'c')], task='task-c', d4=True, label='host-run',
                host='opencode', model='synthetic-model-1')  # same model id, other host
        self.refused('oc', runs=('run-1', 'run-oc'))

    def test_outcomes_other_than_permits_training_refuse(self):
        for outcome in ('forbids-training', 'undecided', 'permits', 'PERMITS-TRAINING', None, True):
            with self.subTest(outcome=outcome):
                self.record({**SYNTHETIC, 'outcome': outcome})
                self.refused()

    def test_dates_bound_the_record(self):
        cases = {
            'not yet reviewed': {**SYNTHETIC, 'reviewedOn': '2027-01-16'},
            'stale': {**SYNTHETIC, 'validUntil': '2027-01-14'},
            'inverted': {**SYNTHETIC, 'reviewedOn': '2027-02-01', 'validUntil': '2027-01-01'},
            'bad date': {**SYNTHETIC, 'reviewedOn': '2027-02-30'},
            'timestamp': {**SYNTHETIC, 'validUntil': '2027-06-30T00:00:00Z'},
            'missing review date': {k: v for k, v in SYNTHETIC.items() if k != 'reviewedOn'},
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                self.record(value)
                self.refused()
        self.record({**SYNTHETIC, 'reviewedOn': '2027-01-15', 'validUntil': '2027-01-15'})  # both bounds inclusive
        self.export('edge')

    def test_malformed_records_refuse(self):
        cases = {
            'no terms': {k: v for k, v in SYNTHETIC.items() if k != 'terms'},
            'empty terms': {**SYNTHETIC, 'terms': {}},
            'both terms': {**SYNTHETIC, 'terms': {'version': 'v', 'url': 'https://example.invalid/t'}},
            'plain url': {**SYNTHETIC, 'terms': {'url': 'http://example.invalid/t'}},
            'no provider': {k: v for k, v in SYNTHETIC.items() if k != 'provider'},
            'provider control char': {**SYNTHETIC, 'provider': 'x\ny'},
            'no models': {**SYNTHETIC, 'models': []},
            'models not a list': {**SYNTHETIC, 'models': 'synthetic-model-1'},
            'duplicate models': {**SYNTHETIC, 'models': ['synthetic-model-1'] * 2},
            'unknown host': {**SYNTHETIC, 'host': 'other-host'},
            'unknown key': {**SYNTHETIC, 'extra': 1},
            'schema': {**SYNTHETIC, 'schema': 'braid-lightning-terms-decision/v0.2'},
            'not an object': [SYNTHETIC],
        }
        for name, value in cases.items():
            with self.subTest(name=name):
                self.record(value)
                self.refused()
        valid = json.dumps(SYNTHETIC)
        duplicated = valid[:-1] + ', "outcome": "permits-training"}'  # a full valid record, one key twice
        compact = json.dumps(SYNTHETIC)
        padded = compact + ' ' * (16 * 1024 + 1 - len(compact))  # valid JSON, exact keys, one byte over the limit
        self.assertEqual(len(padded), 16 * 1024 + 1)
        self.assertEqual(json.loads(padded), SYNTHETIC)
        self.assertGreater(len(padded), 16 * 1024)
        for name, raw in (('not json', b'{'), ('duplicate key', duplicated.encode()), ('too large', padded.encode())):
            with self.subTest(name=name):
                self.record(raw=raw)
                self.refused()
        url = {**SYNTHETIC, 'terms': {'url': 'https://example.invalid/synthetic-terms'}}
        self.record(url)
        self.export('url')

    def test_the_loader_alone_refuses_every_non_permitting_outcome(self):
        for outcome in ('forbids-training', 'undecided', 'permits', None):
            with self.subTest(outcome=outcome), self.assertRaises(export.ExportError) as caught:
                self.record({**SYNTHETIC, 'outcome': outcome})
                export.load_terms_decision(self.home, RECORD, today='2027-01-15')
            self.assertEqual(caught.exception.code, 'terms-gate-missing')
        self.record()
        loaded = export.load_terms_decision(self.home, RECORD, today='2027-01-15')
        self.assertEqual((loaded['outcome'], loaded['host'], loaded['models'], loaded['path']),
                         ('permits-training', 'claude-code', frozenset({'synthetic-model-1'}), RECORD))

    def test_unsafe_record_paths_refuse(self):
        self.record()
        for name in ('terms/x.txt', 'terms/sub/x.json', 'other/synthetic-test.json'):  # real files, wrong place
            (self.home / 'lightning' / name).parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            self.record(name=name)
        for relative in ('/tmp/x.json', '../terms/synthetic-test.json', 'terms/../x.json', 'terms/x.txt',
                         'terms/sub/x.json', 'other/synthetic-test.json', 'terms/ x.json', ''):
            with self.subTest(relative=relative):
                self.refused(terms_decision=relative)
        self.record(mode=0o644)
        self.refused()  # not private
        self.record(name='terms/real.json')
        target = self.home / 'lightning' / 'terms' / 'link.json'
        target.symlink_to(self.home / 'lightning' / 'terms' / 'real.json')
        self.refused(terms_decision='terms/link.json')

    def test_directories_must_be_private(self):
        self.record()
        self.export('private-ok')
        for folder in (self.home / 'lightning' / 'terms', self.home / 'lightning'):
            for mode in (0o777, 0o750, 0o705):
                with self.subTest(folder=folder.name, mode=oct(mode)):
                    folder.chmod(mode)
                    self.refused()
                    folder.chmod(0o700)
        self.export('private-again')

    def test_a_symlink_swapped_in_after_the_path_checks_is_not_followed(self):
        self.record(name='terms/real.json')
        path = self.home / 'lightning' / RECORD
        self.record()
        real_safe = export.registry._safe

        def swap(target, **kwargs):
            checked = real_safe(target, **kwargs)
            if target == path:  # after the path check, before the open
                path.unlink()
                path.symlink_to(self.home / 'lightning' / 'terms' / 'real.json')
            return checked

        with patch.object(export.registry, '_safe', swap):
            self.refused()

    def test_an_oversize_record_is_read_bounded(self):
        padded = json.dumps(SYNTHETIC, indent=1).replace('\n', '\n' + ' ' * 4000).encode()
        self.record(raw=padded)
        reads = []
        real_fdopen = export.os.fdopen

        def watched(fd, *args, **kwargs):
            stream = real_fdopen(fd, *args, **kwargs)
            real_read = stream.read
            stream.read = lambda size=-1: reads.append(size) or real_read(size)
            return stream

        with patch.object(export.os, 'fdopen', watched):
            self.refused()
        self.assertEqual(reads, [16 * 1024 + 1])

    def test_refusals_carry_no_context(self):
        self.record(raw=b'{')
        error = self.refused()
        self.assertIsNone(error.__context__)

    def test_the_writers_apply_the_same_gate(self):
        self.record()
        items, _ = export.select(export.read_runs(self.home, ['run-1', 'run-host']))
        terms = export.load_terms_decision(self.home, RECORD, today='2027-01-15')
        for writer in (lambda t: export.rollout_records(items, level='transition', terms=t),
                       lambda t: export.supervised(items, level='transition', outcome_field=True, terms=t)):
            writer(terms)
            with self.assertRaises(export.ExportError) as caught:
                writer(None)
            self.assertEqual(caught.exception.code, 'terms-gate-missing')
            forged = dict(terms, outcome='forbids-training')
            with self.assertRaises(export.ExportError):
                writer(forged)


class ManifestTests(Base):
    def test_check_manifest_requires_the_record_for_host_units(self):
        self.record()
        manifest = self.export()
        records = (self.base / 'out' / 'records.jsonl').read_bytes()
        sources = {(e['runId'], e['rolloutId'], e['attemptId']): e['source'] for e in manifest['records']}
        terms = export.load_terms_decision(self.home, RECORD, today='2027-01-15')
        export.check_manifest(manifest, records, sources, terms)
        for change in ({'termsDecision': None},
                       {'termsDecision': {'path': 'terms/other.json', 'sha256': '0' * 64}},
                       {'termsDecision': {'path': RECORD, 'sha256': '0' * 64}}):
            broken = copy.deepcopy(manifest)
            broken.update(change)
            broken['digest'] = export.manifest_digest(broken)
            with self.subTest(change=change), self.assertRaises(export.ExportError) as caught:
                export.check_manifest(broken, records, sources, terms)
            self.assertEqual(caught.exception.code, 'invalid-manifest')
        with self.assertRaises(export.ExportError):  # a cited record that the gate never read
            export.check_manifest(manifest, records, sources)

    def test_the_export_verifies_the_cited_hash(self):
        self.record()
        real = export.build_manifest
        for cited in ({'path': 'terms/other.json', 'sha256': '0' * 64}, {'path': RECORD, 'sha256': '0' * 64}):
            def forged(entries, records, **kwargs):
                return real(entries, records, **{**kwargs, 'terms_decision': cited})

            with self.subTest(cited=cited), patch.object(export, 'build_manifest', forged), \
                    self.assertRaises(export.ExportError) as caught:
                self.export('forged')
            self.assertEqual(caught.exception.code, 'invalid-manifest')
            self.assertFalse((self.base / 'forged').exists())

    def test_no_real_record_is_shipped(self):
        found = [p for p in ROOT.rglob('*.json')
                 if not any(part.startswith('.') for part in p.relative_to(ROOT).parts)
                 and b'braid-lightning-terms-decision/v0.1' in p.read_bytes()]
        self.assertEqual(found, [])


if __name__ == '__main__':
    unittest.main()
