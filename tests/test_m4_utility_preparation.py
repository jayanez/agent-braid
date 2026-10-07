# SPDX-License-Identifier: AGPL-3.0-only
"""Preparation tests use fake builders/treatments; no grants or runtime calls."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_braid.utility_fixtures import validate_prepared_manifest
from agent_braid.utility_trials import build_trial_plan, derive_admission_records, encode_trial_plan
from scripts import prepare_m4_utility_trials as prepare


def fake_accounting():
    cpu = {'parentCpuSeconds': 0.0, 'completedChildUserCpuSeconds': 0.0,
           'completedChildSystemCpuSeconds': 0.0}
    phases = []
    for index, name in enumerate(['input', 'replay', 'preparation', 'grant', 'execution',
                                  'independent_verification', 'report_serialization', 'cleanup']):
        phases.append({'name': name, 'outcome': 'success', 'startWallNs': index * 10,
                       'endWallNs': (index + 1) * 10, 'wallNs': 10, **cpu,
                       'gitCommands': 0, 'acceptedBudgetOutputBytes': 0,
                       'observedCapturedOutputBytes': None, 'sampledScratchPeakBytes': None,
                       'counterReasons': {'observedCapturedOutputBytes': 'synthetic unavailable',
                                          'sampledScratchPeakBytes': 'synthetic unavailable'}})
    return {'complete': True, 'outcome': 'success', 'errors': [], 'phases': phases,
            'outer': {'startWallNs': 0, 'endWallNs': 100, 'wallNs': 100, **cpu, 'counterReasons': {}},
            'residualWallNs': 20, 'gitBudgetCount': 0, 'gitCommands': 0,
            'acceptedBudgetOutputBytes': 0, 'observedCapturedOutputBytes': None,
            'sampledScratchPeakBytes': None, 'processLifetimeRssBytes': None,
            'optionalReasons': {f: 'synthetic unavailable' for f in
                               ['observedCapturedOutputBytes', 'sampledScratchPeakBytes', 'processLifetimeRssBytes']},
            'workerIntervals': {'unionWallNs': None, 'peakOccupancy': None, 'reason': 'synthetic unavailable'}}


class UtilityPreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.raw = prepare.DEFAULT_MANIFEST.read_bytes()
        self.prepared = validate_prepared_manifest(self.raw)
        self.inputs = {'synthetic-test-only-source': 'a' * 64,
                       'specs/022-m4-utility-followup/technical-review-packet.md': prepare.PROTOCOL_SHA256}
        self.state = {'candidateCommit': '2' * 40, 'inputs': self.inputs}
        self.diagnostics = self.root / 'diagnostics'
        self.diagnostics.mkdir()
        self.records = {}
        for block in self.prepared['blocks']:
            if block['directNumericExclusions']:
                continue
            ops = [{'instanceId': i['instanceId'], 'attemptId': i['instanceId'] + '-attempt',
                    'source': {'kind': 'commit', 'revision': i['sourceCommit']},
                    'dependencies': i['dependencies'], 'uncertainPaths': [], 'declaredWrites': [i['path']]}
                   for i in block['operationIdentities']]
            request = {'gitRuntimeRequestVersion': '0.1.0-alpha', 'repository': '/fake-owned-source',
                       'baseRevision': block['baseCommit'], 'expectedFinalTree': block['expectedFinalTree'],
                       'order': block['plannedOrder'], 'operations': ops}
            samples = [{'status': 'completed', 'accounting': fake_accounting(),
                        'operational': {'blockId': block['blockId'], 'mode': mode,
                                        'resultTree': block['expectedFinalTree'], 'runtimeManifest': {'request': request},
                                        'independentVerification': {'status': 'verified-completed',
                                          'resultTree': block['expectedFinalTree'], 'completedOperations': block['plannedOrder']}}}
                       for mode in ['serial', 'parallel']]
            record = {'recordVersion': 'spec022-diagnostic-preparation-v1', 'purpose': 'diagnostic-only',
                      'status': 'prepared-or-diagnosed', 'manifestSha256': hashlib.sha256(self.raw).hexdigest(),
                      'registeredMeasurementExecuted': False, 'candidateInputsChangedDuringRun': False,
                      'candidateCommit': '1' * 40, 'inputs': self.inputs,
                      'diagnosticPairs': [{'blockId': block['blockId'], 'samples': samples}]}
            raw = json.dumps(record).encode()
            self.records[block['blockId']] = raw
            (self.diagnostics / (block['blockId'] + '.json')).write_bytes(raw)
        admissions = derive_admission_records(self.raw, self.records)
        self.plan = build_trial_plan(self.raw, admissions, candidate_commit=self.state['candidateCommit'],
                                    destination_root=str(self.root / 'future'))

    def fake_builder(self, block, destination):
        destination.mkdir()
        source = destination / 'source'
        source.mkdir()
        (source / 'owned.txt').write_bytes(b'fake owned source, not Git')
        return {'blockId': block['blockId'], 'repository': str(source),
                'expectedFinalTree': block['expectedFinalTree']}

    def descriptor(self, block_index=0, pair_index=0, treatment_index=0):
        block = self.plan['blocks'][block_index]
        pair = block['pairs'][pair_index]
        return {**deepcopy(pair['treatments'][treatment_index]), 'blockId': block['blockId'],
                'pairIndex': pair['pairIndex'], 'category': pair['category'],
                'preparedBlock': deepcopy(block['preparedBlock'])}

    def callback_scope(self):
        return patch.multiple(prepare, _candidate_state=lambda: deepcopy(self.state),
                              build_fixture=self.fake_builder)

    def test_cli_prepare_writes_exact_manifest_and_pending_provenance_without_fixtures(self):
        output = self.root / 'plan.json'
        with patch.object(prepare, '_candidate_state', return_value=self.state), patch.object(prepare, 'build_fixture') as builder, patch.object(prepare, 'run_treatment') as treatment, redirect_stdout(io.StringIO()):
            result = prepare.prepare_plan(prepare.DEFAULT_MANIFEST, self.diagnostics, self.root / 'future', output)
        self.assertEqual(result, 0)
        builder.assert_not_called()
        treatment.assert_not_called()
        self.assertFalse((self.root / 'future').exists())
        self.assertEqual(output.read_bytes(), encode_trial_plan(self.plan))
        receipt = json.loads(Path(str(output) + '.provenance.json').read_bytes())
        self.assertEqual(receipt['manifestSha256'], hashlib.sha256(output.read_bytes()).hexdigest())
        self.assertFalse(receipt['registeredExecution'])
        self.assertEqual(receipt['reviewDecision'], 'pending-separate-stable-harness-manifest-review')

    def test_cli_execute_and_registered_are_refused_through_actual_entrypoint(self):
        for flag in ['--execute', '--registered']:
            process = subprocess.run([sys.executable, str(prepare.ROOT / 'scripts/prepare_m4_utility_trials.py'), flag],
                                     capture_output=True, timeout=30)
            self.assertEqual(process.returncode, 2)
            self.assertEqual(json.loads(process.stderr)['status'], 'refused')

    def test_candidate_must_be_clean_and_protocol_bytes_exact(self):
        with patch.object(prepare, '_git', return_value='dirty'):
            with self.assertRaisesRegex(ValueError, 'clean candidate'):
                prepare._candidate_state()
        with patch.object(prepare, '_git', side_effect=['', '2' * 40]), patch.object(prepare, '_inputs', return_value={**self.inputs, 'specs/022-m4-utility-followup/technical-review-packet.md': '0' * 64}):
            with self.assertRaisesRegex(ValueError, 'protocol bytes differ'):
                prepare._candidate_state()

    def test_stale_diagnostic_inputs_and_existing_outputs_are_rejected(self):
        with patch.object(prepare, '_candidate_state', return_value={**self.state, 'inputs': {**self.inputs, 'synthetic-test-only-source': '0' * 64}}):
            with self.assertRaisesRegex(ValueError, 'diagnostic code inputs'):
                prepare.prepare_plan(prepare.DEFAULT_MANIFEST, self.diagnostics, self.root / 'future', self.root / 'plan.json')
        existing = self.root / 'plan.json'
        existing.write_bytes(b'preserve')
        with patch.object(prepare, '_candidate_state', return_value=self.state):
            with self.assertRaises(ValueError):
                prepare.prepare_plan(prepare.DEFAULT_MANIFEST, self.diagnostics, self.root / 'future', existing)
        self.assertEqual(existing.read_bytes(), b'preserve')

    def test_all_fixture_copies_precede_callback_and_runtime_paths_are_bound(self):
        calls = []
        def treatment(fixture, mode, **kwargs):
            calls.append(kwargs)
            self.assertEqual(fixture['preparedSourceFingerprint'], prepare.source_fingerprint(Path(fixture['repository'])))
            self.assertEqual(kwargs['run_leaf'], 'run')
            self.assertEqual(kwargs['grant_leaf'], 'grants')
            return {'status': 'completed', 'syntheticTestOnly': True}
        with self.callback_scope(), patch.object(prepare, 'run_treatment', side_effect=treatment):
            callback, record = prepare.prepare_runtime_callback(self.plan)
            self.assertEqual(calls, [])
            self.assertEqual(record['fixtureCopies'], 176)
            self.assertEqual(len(record['sourceFingerprints']), 176)
            self.assertTrue(record['wallNs'] >= 0 and record['parentCpuNs'] >= 0)
            descriptor = self.descriptor()
            result = callback(descriptor)
            self.assertEqual(result['status'], 'completed')
            self.assertEqual(calls[0]['treatment_root'], Path(descriptor['runPath']).parent)
            self.assertFalse(calls[0]['treatment_root'].exists())
            self.assertEqual(callback(descriptor)['status'], 'invalidated')
            self.assertEqual(len(calls), 1)

    def test_source_mutation_descriptor_tamper_and_candidate_drift_never_dispatch(self):
        with self.callback_scope(), patch.object(prepare, 'run_treatment') as treatment:
            callback, _ = prepare.prepare_runtime_callback(self.plan)
            tampered = self.descriptor()
            tampered['runPath'] += '-tampered'
            self.assertEqual(callback(tampered)['status'], 'invalidated')
            descriptor = self.descriptor()
            (Path(descriptor['fixturePath']) / 'source' / 'owned.txt').write_bytes(b'changed')
            self.assertEqual(callback(descriptor)['status'], 'no-go')
            with patch.object(prepare, '_candidate_state', side_effect=ValueError('dirty')):
                self.assertEqual(callback(self.descriptor(0, 0, 1))['status'], 'invalidated')
            treatment.assert_not_called()

    def test_existing_runtime_directory_is_never_adopted_or_removed(self):
        with self.callback_scope(), patch.object(prepare, 'run_treatment') as treatment:
            callback, _ = prepare.prepare_runtime_callback(self.plan)
            descriptor = self.descriptor()
            runtime = Path(descriptor['runPath']).parent
            runtime.mkdir()
            sentinel = runtime / 'preserve.txt'
            sentinel.write_bytes(b'preserve')
            self.assertEqual(callback(descriptor)['status'], 'no-go')
            treatment.assert_not_called()
            self.assertEqual(sentinel.read_bytes(), b'preserve')

    def test_source_change_after_treatment_retains_sample_and_stops(self):
        def treatment(fixture, mode, **kwargs):
            (Path(fixture['repository']) / 'owned.txt').write_bytes(b'unsafe fake mutation')
            return {'status': 'completed', 'syntheticTestOnly': True}
        with self.callback_scope(), patch.object(prepare, 'run_treatment', side_effect=treatment):
            callback, _ = prepare.prepare_runtime_callback(self.plan)
            result = callback(self.descriptor())
        self.assertEqual(result['status'], 'no-go')
        self.assertTrue(result['retainedSample']['syntheticTestOnly'])

    def test_existing_symlink_and_git_ancestor_roots_reject_before_builder(self):
        destination = self.root / 'future'
        destination.symlink_to(self.root / 'absent')
        with self.callback_scope(), patch.object(prepare, 'build_fixture') as builder:
            with self.assertRaises(ValueError):
                prepare.prepare_runtime_callback(self.plan)
            builder.assert_not_called()
        destination.unlink()
        (self.root / '.git').mkdir()
        with self.callback_scope(), patch.object(prepare, 'build_fixture') as builder:
            with self.assertRaises(ValueError):
                prepare.prepare_runtime_callback(self.plan)
            builder.assert_not_called()
        self.assertFalse(destination.exists())

    def test_unknown_treatment_failure_is_inconclusive_without_mutating_proof(self):
        with self.callback_scope(), patch.object(prepare, 'run_treatment', side_effect=RuntimeError('fake unknown error')):
            callback, _ = prepare.prepare_runtime_callback(self.plan)
            result = callback(self.descriptor())
        self.assertEqual(result['status'], 'inconclusive')
        self.assertEqual(result['error']['type'], 'RuntimeError')

    def test_source_mutation_with_unexpected_error_cannot_be_hidden_as_inconclusive(self):
        def treatment(fixture, mode, **kwargs):
            (Path(fixture['repository']) / 'owned.txt').write_bytes(b'changed on error')
            raise RuntimeError('fake unexpected error')
        with self.callback_scope(), patch.object(prepare, 'run_treatment', side_effect=treatment):
            callback, _ = prepare.prepare_runtime_callback(self.plan)
            result = callback(self.descriptor())
        self.assertEqual(result['status'], 'no-go')
        self.assertEqual(result['reason'], 'prepared-source-mutation-on-error')
        self.assertEqual(result['error']['type'], 'RuntimeError')


if __name__ == '__main__':
    unittest.main()
