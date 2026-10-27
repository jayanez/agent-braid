# SPDX-License-Identifier: AGPL-3.0-only
"""Admission accounting regressions; no native/source/model experiment."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid.forecast_admission import PhaseLedger, source_envelope, source_digest
from agent_braid.forecast_data import ForecastError


ROOT = Path(__file__).resolve().parents[1]


class AdmissionAccountingTests(unittest.TestCase):
    def ledger(self, **changes):
        config = dict(bounds={p: 2 for p in ('prepare', 'grant', 'dispatch', 'verify')},
                      total=8, max_active=2)
        config.update(changes)
        return PhaseLedger(**config)

    def test_source_routes_distinguish_worker_inspection_from_direct_tree_verification(self):
        serial = source_envelope(ROOT, mode='serial', final_verifier='runtime')
        direct = source_envelope(ROOT, mode='parallel', final_verifier='runtime')
        inspected = source_envelope(ROOT, mode='parallel', final_verifier='policy')
        self.assertEqual([1793, 769, 1025, 256], [r['gitRequests'] for r in serial['phases']])
        self.assertEqual(5380, direct['gitRequests'])
        self.assertEqual(6662, inspected['gitRequests'])
        self.assertEqual(1538, inspected['phases'][-1]['gitRequests'])
        self.assertNotEqual(direct['finalVerifier'], inspected['finalVerifier'])
        self.assertIsNone(inspected['wholeFlowWallUpperBoundNs'])
        self.assertIsNone(inspected['minimumMeasuredGitRequests'])
        self.assertFalse(inspected['executionAuthorization'])
        self.assertFalse(inspected['actualProfileAdmitted'])
        self.assertTrue(inspected['blockers'])

    def test_source_drift_refuses_before_any_subprocess_or_host_observation(self):
        expected = source_digest(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            clone = Path(directory)
            from agent_braid.forecast_admission import SOURCE_FILES
            for name in SOURCE_FILES:
                target = clone / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            target = clone / SOURCE_FILES[0]
            target.write_bytes(target.read_bytes() + b'\n# drift\n')
            with patch('subprocess.Popen', side_effect=AssertionError('native launch')):
                with self.assertRaisesRegex(ForecastError, 'admission-source-drift'):
                    source_envelope(clone, mode='serial', final_verifier='runtime',
                                    expected_source_digest=expected)

    def test_missing_reservations_and_underfunded_whole_flow_refuse(self):
        for changes in (dict(bounds={'dispatch': 256}), dict(total=7),
                        dict(max_active=True), dict(max_active=3),
                        dict(bounds=dict(prepare=True, grant=2, dispatch=2, verify=2))):
            with self.subTest(changes=changes), self.assertRaises(ForecastError):
                self.ledger(**changes)

    def test_model_pin_covers_ledger_and_validation_dependencies(self):
        from agent_braid.forecast_admission import SOURCE_FILES
        with tempfile.TemporaryDirectory() as directory:
            clone=Path(directory)
            for name in SOURCE_FILES:
                target=clone/name; target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes((ROOT/name).read_bytes())
            for name in ('agent_braid/forecast_admission.py','agent_braid/forecast_data.py'):
                target=clone/name; original=target.read_bytes()
                target.write_bytes(original+b'\n# changed ledger or validator\n')
                with self.subTest(name=name), self.assertRaisesRegex(ForecastError,'admission-source-drift'):
                    source_envelope(clone,mode='serial',final_verifier='runtime')
                target.write_bytes(original)

    def test_dispatch_cannot_spend_verification_reservation(self):
        ledger = self.ledger()
        for phase in ('prepare', 'grant', 'dispatch'):
            ledger.enter(phase)
            for _ in range(2):
                token = ledger.reserve()
                ledger.launched(token)
                ledger.finished(token)
        with self.assertRaisesRegex(ForecastError, 'phase-budget-exhausted'):
            ledger.reserve()
        ledger.enter('verify')
        token = ledger.reserve()
        ledger.launched(token)
        ledger.finished(token)
        report = ledger.receipt()
        self.assertEqual(3, report['phases']['dispatch']['attempted'])
        self.assertEqual(2, report['phases']['dispatch']['launched'])
        self.assertEqual(1, report['phases']['verify']['launched'])
        self.assertFalse(report['accountingHealthy'])

    def test_failed_start_is_accepted_but_never_reported_as_launched(self):
        ledger = self.ledger()
        ledger.enter('prepare')
        token = ledger.reserve()
        ledger.start_failed(token)
        report = ledger.receipt()
        self.assertEqual(dict(attempted=1, accepted=1, launched=0, finished=0,
                              startFailed=1, denied=0), report['phases']['prepare'])
        self.assertEqual(0, report['outstandingReservations'])
        self.assertFalse(report['accountingHealthy'])
        with self.assertRaises(ForecastError):
            ledger.launched(token)

    def test_failure_stops_work_but_keeps_one_terminal_verification_path(self):
        for failure in ('start', 'concurrency'):
            with self.subTest(failure=failure):
                ledger = self.ledger(max_active=1)
                ledger.enter('prepare')
                token = ledger.reserve()
                if failure == 'start':
                    ledger.start_failed(token)
                else:
                    with self.assertRaises(ForecastError):
                        ledger.reserve()
                    ledger.launched(token)
                    ledger.finished(token)
                with self.assertRaisesRegex(ForecastError, 'admission-stopped'):
                    ledger.reserve()
                with self.assertRaisesRegex(ForecastError, 'admission-stopped'):
                    ledger.enter('grant')
                ledger.enter('verify')
                verifier = ledger.reserve()
                ledger.start_failed(verifier)
                with self.assertRaisesRegex(ForecastError, 'admission-stopped'):
                    ledger.reserve()
                self.assertFalse(ledger.receipt()['accountingHealthy'])

    def test_two_workers_share_one_atomic_reservation_limit(self):
        ledger = self.ledger(bounds={p: 8 for p in ('prepare', 'grant', 'dispatch', 'verify')},
                             total=32)
        ledger.enter('prepare')
        def reserve(_):
            try:
                return ledger.reserve()
            except ForecastError:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            tokens = list(pool.map(reserve, range(8)))
        self.assertEqual(2, len([t for t in tokens if t is not None]))
        self.assertEqual(2, ledger.receipt()['peakOutstandingReservations'])
        self.assertEqual(6, ledger.receipt()['phases']['prepare']['denied'])
        with self.assertRaisesRegex(ForecastError, 'outstanding-reservations'):
            ledger.enter('grant')

    def test_ticket_lifecycle_and_phase_order_cannot_be_replayed(self):
        ledger = self.ledger()
        with self.assertRaises(ForecastError):
            ledger.reserve()
        ledger.enter('prepare')
        token = ledger.reserve()
        with self.assertRaises(ForecastError):
            ledger.finished(token)
        ledger.launched(token)
        ledger.finished(token)
        for action in (lambda: ledger.finished(token), lambda: ledger.launched(token),
                       lambda: ledger.enter('prepare'), lambda: ledger.enter('dispatch')):
            with self.assertRaises(ForecastError):
                action()
        ledger.enter('grant')

    def test_configuration_and_receipts_are_copied_without_admission_claims(self):
        bounds = {p: 2 for p in ('prepare', 'grant', 'dispatch', 'verify')}
        ledger = self.ledger(bounds=bounds)
        bounds['prepare'] = 999
        report = ledger.receipt()
        self.assertEqual(2, report['phaseBounds']['prepare'])
        report['phases']['prepare']['accepted'] = 999
        self.assertEqual(0, ledger.receipt()['phases']['prepare']['accepted'])
        self.assertFalse(report['executionAuthorization'])
        self.assertFalse(report['nativeObservation'])
        self.assertFalse(report['cleanupConfirmed'])


if __name__ == '__main__':
    unittest.main()
