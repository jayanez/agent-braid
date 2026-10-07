# SPDX-License-Identifier: AGPL-3.0-only
"""Pure fake callbacks; synthetic review stubs do not record human approval."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
import uuid

from agent_braid.utility_fixtures import validate_prepared_manifest
from agent_braid.utility_trials import (
    DISPATCH_BUDGET_NS, InvalidUtilityTrials, build_trial_plan,
    derive_admission_records, encode_trial_plan, run_trial_plan,
)

MANIFEST = Path(__file__).resolve().parents[1] / 'specs/022-m4-utility-followup/evidence/prepared-fixture-manifest.json'


def accounting(wall):
    cpu = {'parentCpuSeconds': 0.0, 'completedChildUserCpuSeconds': 0.0,
           'completedChildSystemCpuSeconds': 0.0}
    phases = []
    step = wall // 16
    for index, name in enumerate(['input', 'replay', 'preparation', 'grant', 'execution',
                                  'independent_verification', 'report_serialization', 'cleanup']):
        phases.append({'name': name, 'outcome': 'success', 'startWallNs': index * step,
                       'endWallNs': (index + 1) * step, 'wallNs': step, **cpu,
                       'gitCommands': 0, 'acceptedBudgetOutputBytes': 0,
                       'observedCapturedOutputBytes': None, 'sampledScratchPeakBytes': None,
                       'counterReasons': {'observedCapturedOutputBytes': 'synthetic unavailable',
                                          'sampledScratchPeakBytes': 'synthetic unavailable'}})
    return {'complete': True, 'outcome': 'success', 'errors': [], 'phases': phases,
            'outer': {'startWallNs': 0, 'endWallNs': wall, 'wallNs': wall, **cpu, 'counterReasons': {}},
            'residualWallNs': wall - 8 * step, 'gitBudgetCount': 0, 'gitCommands': 0,
            'acceptedBudgetOutputBytes': 0, 'observedCapturedOutputBytes': None,
            'sampledScratchPeakBytes': None, 'processLifetimeRssBytes': None,
            'optionalReasons': {f: 'synthetic unavailable' for f in
                               ['observedCapturedOutputBytes', 'sampledScratchPeakBytes', 'processLifetimeRssBytes']},
            'workerIntervals': {'unionWallNs': None, 'peakOccupancy': None, 'reason': 'synthetic unavailable'}}


def sample(block, mode, descriptor=None, serial_wall=200, parallel_wall=100):
    operations = [{'instanceId': i['instanceId'], 'attemptId': i['instanceId'] + '-attempt',
                   'source': {'kind': 'commit', 'revision': i['sourceCommit']},
                   'dependencies': i['dependencies'], 'uncertainPaths': [], 'declaredWrites': [i['path']]}
                  for i in block['operationIdentities']]
    path = descriptor['runPath'] if descriptor else '/synthetic-diagnostic-only/run'
    key = hashlib.sha256((path + block['blockId'] + mode).encode()).hexdigest()
    return {'status': 'completed', 'operational': {
        'status': 'completed', 'blockId': block['blockId'], 'mode': mode,
        'resultTree': block['expectedFinalTree'], 'grantId': str(uuid.uuid5(uuid.NAMESPACE_URL, key)),
        'planDigest': 'sha256:' + key, 'immutableSourceUnchanged': True,
        'runtimeManifest': {'request': {'gitRuntimeRequestVersion': '0.1.0-alpha',
          'repository': '/synthetic-private-source', 'baseRevision': block['baseCommit'],
          'expectedFinalTree': block['expectedFinalTree'], 'order': block['plannedOrder'], 'operations': operations}},
        'independentVerification': {'status': 'verified-completed', 'resultTree': block['expectedFinalTree'],
                                    'completedOperations': block['plannedOrder'], 'runDirectory': path}},
        'accounting': accounting(serial_wall if mode == 'serial' else parallel_wall)}


class UtilityTrialsTests(unittest.TestCase):
    def setUp(self):
        self.raw = MANIFEST.read_bytes()
        self.prepared = validate_prepared_manifest(self.raw)
        self.diagnostics = {}
        for block in self.prepared['blocks']:
            if block['directNumericExclusions']:
                continue
            record = {'recordVersion': 'spec022-diagnostic-preparation-v1', 'purpose': 'diagnostic-only',
                      'manifestSha256': hashlib.sha256(self.raw).hexdigest(),
                      'registeredMeasurementExecuted': False, 'candidateInputsChangedDuringRun': False,
                      'candidateCommit': '1' * 40, 'inputs': {'synthetic-test-source': 'a' * 64},
                      'status': 'prepared-or-diagnosed', 'diagnosticPairs': [{'blockId': block['blockId'],
                      'samples': [sample(block, mode) for mode in ['serial', 'parallel']]}]}
            self.diagnostics[block['blockId']] = json.dumps(record).encode()
        self.admissions = derive_admission_records(self.raw, self.diagnostics)
        self.plan = build_trial_plan(self.raw, self.admissions, candidate_commit='2' * 40,
                                    destination_root='/synthetic-test-never-created')
        self.review = {'decision': 'approved', 'reviewedCandidateCommit': self.plan['candidateCommit'],
                       'reviewedManifestSha256': hashlib.sha256(encode_trial_plan(self.plan)).hexdigest(),
                       'identity': 'SYNTHETIC UNIT TEST STUB; NOT HUMAN APPROVAL'}

    def callback(self, descriptor):
        return sample(descriptor['preparedBlock'], descriptor['mode'], descriptor)

    def run_plan(self, callback=None, clock=None):
        return run_trial_plan(self.plan, callback or self.callback,
                              registration_review=self.review, monotonic_ns=clock or (lambda: 0))

    def test_fixed_inventory_and_all_parity_destinations_are_retained(self):
        self.assertEqual(len(self.plan['blocks']), 9)
        self.assertEqual(sum(bool(b['pairs']) for b in self.plan['blocks']), 4)
        paths = []
        for block in self.plan['blocks']:
            self.assertEqual(len(block['pairs']), 22 if block['status'] == 'admitted' else 0)
            for index, pair in enumerate(block['pairs']):
                self.assertEqual(pair['category'], 'warmup' if index < 2 else 'measured')
                self.assertEqual(pair['treatmentOrder'], ['serial', 'parallel'] if index % 2 == 0 else ['parallel', 'serial'])
                paths.extend(t[key] for t in pair['treatments'] for key in ['fixturePath', 'runPath', 'grantPath'])
        self.assertEqual(len(paths), 528)
        self.assertEqual(len(set(paths)), 528)

    def test_matching_separate_review_required_before_any_callback(self):
        for review in [None, {}, {**self.review, 'decision': 'pending'},
                       {**self.review, 'reviewedManifestSha256': '0' * 64},
                       {**self.review, 'reviewedCandidateCommit': '0' * 40}]:
            called = []
            with self.subTest(review=review), self.assertRaisesRegex(InvalidUtilityTrials, 'review required'):
                run_trial_plan(self.plan, lambda d: called.append(d), registration_review=review)
            self.assertEqual(called, [])

    def test_complete_positive_and_negative_are_synthetic_chains_not_pooled(self):
        result = self.run_plan()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['blocks'][0]['medianPairedRatio'], 2)
        self.assertEqual(result['blocks'][6]['outcome'], 'complete-order-control')
        self.assertIsNone(result['blocks'][6]['medianPairedRatio'])
        negative = self.run_plan(lambda d: sample(d['preparedBlock'], d['mode'], d, 100, 200))
        self.assertEqual(negative['blocks'][0]['outcome'], 'negative-synthetic-diagnostic')
        self.assertEqual(negative['blocks'][0]['medianPairedRatio'], 0.5)

    def test_invalid_warmup_prevents_favorable_complete_case_summary(self):
        calls = []
        def callback(d):
            calls.append(d)
            value = self.callback(d)
            if len(calls) == 1:
                value['status'] = 'inconclusive'
            return value
        result = self.run_plan(callback)
        self.assertEqual(len(calls), 176)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['blocks'][0]['outcome'], 'inconclusive')
        self.assertIsNone(result['blocks'][0]['medianPairedRatio'])
        self.assertEqual(result['blocks'][0]['counts']['invalidPairs'], 1)

    def test_budget_stops_before_new_treatment_retaining_every_unexecuted_pair(self):
        now, calls = [0], []
        def callback(d):
            calls.append(d)
            now[0] = DISPATCH_BUDGET_NS
            return self.callback(d)
        result = self.run_plan(callback, lambda: now[0])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['status'], 'incomplete')
        self.assertEqual(result['stopReason'], 'dispatch-budget-exhausted')
        rows = [t for b in result['blocks'] for p in b['pairs'] for t in p['treatments']]
        self.assertEqual(len(rows), 176)
        self.assertEqual(sum(t['status'] == 'unexecuted' for t in rows), 175)
        self.assertEqual(len(result['blocks']), 9)
        self.assertTrue(all(b['medianPairedRatio'] is None for b in result['blocks']))

    def test_unsafe_tree_missing_verifier_paths_source_and_reused_grant_stop_global(self):
        for mutation in ['tree', 'verifier', 'path', 'source', 'grant']:
            calls = []
            def callback(d):
                calls.append(d)
                value = self.callback(d)
                op = value['operational']
                if mutation == 'tree': op['resultTree'] = '0' * 40
                if mutation == 'verifier': op.pop('independentVerification')
                if mutation == 'path': op['independentVerification']['runDirectory'] = '/wrong'
                if mutation == 'source': op['immutableSourceUnchanged'] = False
                if mutation == 'grant': op['grantId'] = '00000000-0000-4000-8000-000000000001'
                return value
            with self.subTest(mutation=mutation):
                result = self.run_plan(callback)
                self.assertEqual(result['status'], 'no-go')
                self.assertEqual(len(calls), 2 if mutation == 'grant' else 1)
                self.assertTrue(any(t['status'] == 'unexecuted' for b in result['blocks'] for p in b['pairs'] for t in p['treatments']))

    def test_callback_error_missing_final_accounting_and_missing_return_stay_invalid(self):
        for mutation in ['exception', 'missing', 'accounting', 'final-status']:
            def callback(d):
                if mutation == 'exception': raise RuntimeError('fake failure')
                if mutation == 'missing': return None
                value = self.callback(d)
                if mutation == 'accounting': value['accounting']['complete'] = False
                if mutation == 'final-status': value['status'] = 'inconclusive'
                return value
            with self.subTest(mutation=mutation):
                result = self.run_plan(callback)
                self.assertEqual(result['status'], 'incomplete')
                self.assertTrue(all(b['medianPairedRatio'] is None for b in result['blocks']))
                self.assertEqual(result['blocks'][0]['counts']['invalidPairs'], 22)

    def test_identity_drift_stops_and_retains_raw_record(self):
        calls = []
        def callback(d):
            calls.append(d)
            value = self.callback(d)
            value['operational']['runtimeManifest']['request']['baseRevision'] = '0' * 40
            return value
        result = self.run_plan(callback)
        self.assertEqual(result['status'], 'invalidated')
        self.assertEqual(len(calls), 1)
        self.assertEqual(result['blocks'][0]['pairs'][0]['treatments'][0]['sample']['operational']['runtimeManifest']['request']['baseRevision'], '0' * 40)

    def test_diagnostic_refusal_is_named_and_not_replaced(self):
        name = 'independent-2-1024'
        record = json.loads(self.diagnostics[name])
        record['status'] = 'inconclusive'
        record['diagnosticPairs'][0]['samples'][0]['status'] = 'inconclusive'
        changed = {**self.diagnostics, name: json.dumps(record).encode()}
        rows = derive_admission_records(self.raw, changed)
        self.assertEqual(rows[0]['status'], 'excluded-by-diagnostic-refusal')
        self.assertEqual(rows[0]['exclusions'], [{'reason': 'incomplete-treatment'}])
        plan = build_trial_plan(self.raw, rows, candidate_commit='2' * 40, destination_root='/synthetic-test')
        self.assertEqual(len(plan['blocks']), 9)
        self.assertEqual(plan['blocks'][0]['pairs'], [])

    def test_diagnostic_unsafe_missing_changed_inputs_and_missing_modes_reject(self):
        for mutation in ['unsafe', 'changed', 'missing-mode']:
            record = json.loads(self.diagnostics['independent-2-1024'])
            if mutation == 'unsafe': record['diagnosticPairs'][0]['samples'][0]['status'] = 'no-go'
            if mutation == 'changed': record['candidateInputsChangedDuringRun'] = True
            if mutation == 'missing-mode': record['diagnosticPairs'][0]['samples'].pop()
            with self.subTest(mutation=mutation), self.assertRaises(InvalidUtilityTrials):
                derive_admission_records(self.raw, {**self.diagnostics, 'independent-2-1024': json.dumps(record).encode()})

    def test_completed_diagnosis_requires_source_and_private_grant_plan_proofs(self):
        for mutation in ['missing-source', 'false-source', 'grant', 'plan', 'reuse-grant', 'reuse-plan']:
            record = json.loads(self.diagnostics['independent-2-1024'])
            first, second = [s['operational'] for s in record['diagnosticPairs'][0]['samples']]
            if mutation == 'missing-source': first.pop('immutableSourceUnchanged')
            if mutation == 'false-source': first['immutableSourceUnchanged'] = False
            if mutation == 'grant': first['grantId'] = 'invalid UUID'
            if mutation == 'plan': first['planDigest'] = 'unbound plan'
            if mutation == 'reuse-grant': second['grantId'] = first['grantId']
            if mutation == 'reuse-plan': second['planDigest'] = first['planDigest']
            with self.subTest(mutation=mutation), self.assertRaises(InvalidUtilityTrials):
                derive_admission_records(self.raw, {**self.diagnostics, 'independent-2-1024': json.dumps(record).encode()})

    def test_plan_rehash_cannot_change_denominator_order_or_known_exclusions(self):
        for mutation in ['pairs', 'parity', 'excluded']:
            plan = deepcopy(self.plan)
            if mutation == 'pairs': plan['blocks'][0]['pairs'].pop()
            if mutation == 'parity': plan['blocks'][0]['pairs'][0]['treatmentOrder'].reverse()
            if mutation == 'excluded': plan['blocks'][2]['status'] = 'admitted'
            body = {k: v for k, v in plan.items() if k != 'planDigest'}
            plan['planDigest'] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
            with self.subTest(mutation=mutation), self.assertRaises(InvalidUtilityTrials):
                encode_trial_plan(plan)

    def test_complete_flag_cannot_hide_missing_overlapping_or_unreconciled_phases(self):
        for mutation in ['missing', 'overlap', 'phase-sum', 'outer', 'residual', 'counter-missing', 'counter-negative', 'null-without-reason']:
            def callback(d):
                value = self.callback(d)
                a = value['accounting']
                if mutation == 'missing': a['phases'].pop()
                if mutation == 'overlap':
                    a['phases'][1]['startWallNs'] = 0
                    a['phases'][1]['wallNs'] = a['phases'][1]['endWallNs']
                if mutation == 'phase-sum':
                    a['phases'][0]['endWallNs'] = a['outer']['wallNs'] + 1
                    a['phases'][0]['wallNs'] = a['phases'][0]['endWallNs']
                if mutation == 'outer': a['outer']['endWallNs'] = 1
                if mutation == 'residual': a['residualWallNs'] += 1
                if mutation == 'counter-missing': a['phases'][0].pop('gitCommands')
                if mutation == 'counter-negative': a['phases'][0]['parentCpuSeconds'] = -1
                if mutation == 'null-without-reason': a['optionalReasons'].pop('processLifetimeRssBytes')
                return value
            with self.subTest(mutation=mutation):
                result = self.run_plan(callback)
                self.assertEqual(result['status'], 'incomplete')
                self.assertTrue(all(b['medianPairedRatio'] is None for b in result['blocks']))

    def test_redigested_plan_cannot_contradict_admission_or_exclusion_proof(self):
        for mutation in ['admission', 'exclusion', 'inputs']:
            plan = deepcopy(self.plan)
            if mutation == 'admission':
                plan['admissionRecords'][0]['status'] = 'excluded-by-diagnostic-refusal'
                plan['admissionRecords'][0]['exclusions'] = [{'reason': 'fake refusal'}]
            if mutation == 'exclusion': plan['blocks'][2]['exclusions'] = []
            if mutation == 'inputs': plan['admissionRecords'][0]['diagnosticInputHashes'] = {}
            body = {k: v for k, v in plan.items() if k != 'planDigest'}
            plan['planDigest'] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            with self.subTest(mutation=mutation), self.assertRaises(InvalidUtilityTrials):
                encode_trial_plan(plan)


if __name__ == '__main__':
    unittest.main()
