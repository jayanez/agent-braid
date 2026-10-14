# SPDX-License-Identifier: AGPL-3.0-only
from pathlib import Path
import agent_braid
import os
import signal
import tempfile
import unittest
from unittest.mock import patch

from agent_braid.forecast_cost import summarize_cost_ledger
from agent_braid.forecast_data import parse_record
from scripts.reproduce_forecast_cost import reproduce, main


class ForecastCostProcedureTests(unittest.TestCase):
    def setUp(self):
        # Unit fixture only: real installed verification is a separate process.
        self.purelib = patch('scripts.reproduce_forecast_cost.sysconfig.get_path',
                             return_value=str(Path(agent_braid.__file__).resolve().parent.parent))
        self.purelib.start(); self.addCleanup(self.purelib.stop)

    def test_baseline_cost_capture_is_no_model_and_keeps_unknowns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(strict=True)
            with patch('agent_braid.forecast_worker.DockerCPUWorker._start') as load:
                self.assertEqual(0, reproduce(root))
                load.assert_not_called()
            ledger = parse_record((root / 'ledger.json').read_bytes())
            summary = summarize_cost_ledger(ledger)
            payload = parse_record((root / 'payload.json').read_bytes())
            self.assertEqual(['forecast', 'forecast', 'unavailable'], [p['status'] for p in payload['forecasts']])
            self.assertFalse(payload['modelLoaded'])
            self.assertGreater(summary['cpuNsByDomain']['coordinator'], 0)
            self.assertGreater(summary['memoryObservations'][0]['bytes'], 0)
            self.assertIsNone(summary['cpuNsByDomain']['worker-container'])
            self.assertIn('prior-artifacts:prior-setup-unallocated', summary['gaps'])
            self.assertIn('publication:final-receipt-write-after-seal', summary['gaps'])
            self.assertTrue(ledger['cleanupConfirmed'])
            self.assertEqual({'payload.json', 'ledger.json', 'summary.json'}, {p.name for p in root.iterdir()})
            for path in root.iterdir(): self.assertEqual(0o600, path.stat().st_mode & 0o777)

    def test_existing_output_is_refused_before_session_work(self):
        with tempfile.TemporaryDirectory() as tmp, patch('sys.argv', [
            'cost', '--output-directory', tmp, '--artifact-digest', 'a' * 64,
        ]), patch('agent_braid.forecast_advice.ForecastSession') as session:
            with self.assertRaises(FileExistsError): main()
            session.assert_not_called()
            self.assertEqual([], list(Path(tmp).iterdir()))

    def test_changed_package_identity_keeps_failed_preflight_without_loading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(strict=True)
            with patch('agent_braid.forecast_advice.ForecastSession') as session:
                self.assertEqual(2, reproduce(root, 'a' * 64))
                session.assert_not_called()
            ledger = parse_record((root / 'ledger.json').read_bytes())
            phase = next(p for p in ledger['phases'] if p['id'] == 'package-identity')
            self.assertEqual('failed', phase['status'])
            self.assertNotEqual('a' * 64, ledger['artifactDigest'])
            self.assertFalse((root / 'payload.json').exists())
            summary = parse_record((root / 'summary.json').read_bytes())
            self.assertEqual('synthetic-cost-procedure-failed', summary['error'])

    def test_source_checkout_origin_refuses_and_preserves_preflight_cost(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(strict=True)
            with patch('scripts.reproduce_forecast_cost.sysconfig.get_path', return_value=str(root)), \
                 patch('agent_braid.forecast_advice.ForecastSession') as session:
                self.assertEqual(2, reproduce(root))
                session.assert_not_called()
            ledger = parse_record((root / 'ledger.json').read_bytes())
            self.assertIsNone(ledger['artifactDigest'])
            self.assertIn('artifact:not-observed', summarize_cost_ledger(ledger)['gaps'])
            self.assertFalse((root / 'payload.json').exists())

    def test_interrupt_during_forecast_is_persisted_after_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(strict=True)
            with patch('agent_braid.forecast_advice.ForecastSession.predict', side_effect=KeyboardInterrupt):
                self.assertEqual(130, reproduce(root))
            ledger = parse_record((root / 'ledger.json').read_bytes())
            phase = next(p for p in ledger['phases'] if p['id'] == 'baseline')
            self.assertEqual('failed', phase['status']); self.assertTrue(ledger['cleanupConfirmed'])
            summary = parse_record((root / 'summary.json').read_bytes())
            self.assertEqual('synthetic-cost-procedure-interrupted', summary['error'])

    def test_cleanup_failure_is_persisted_without_confirming_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(strict=True)
            with patch('agent_braid.forecast_advice.ForecastSession.close', side_effect=SystemExit):
                self.assertEqual(2, reproduce(root))
            ledger = parse_record((root / 'ledger.json').read_bytes())
            self.assertFalse(ledger['cleanupConfirmed'])
            self.assertIn('cleanup:unconfirmed', summarize_cost_ledger(ledger)['gaps'])

    def test_sigterm_during_final_export_is_queued_until_receipts_persist(self):
        from scripts import reproduce_forecast_cost as driver
        original = driver._write
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(strict=True) / 'new-output'
            def interrupted(directory, name, value):
                if name == 'ledger.json': os.kill(os.getpid(), signal.SIGTERM)
                return original(directory, name, value)
            with patch('sys.argv', ['cost', '--output-directory', str(root)]), \
                 patch.object(driver, '_write', side_effect=interrupted):
                self.assertEqual(143, main())
            ledger = parse_record((root / 'ledger.json').read_bytes())
            self.assertTrue(ledger['cleanupConfirmed'])
            summary = parse_record((root / 'summary.json').read_bytes())
            self.assertEqual('synthetic-cost-procedure-interrupted', summary['error'])

    def test_sigterm_during_cleanup_is_queued_without_skipping_cleanup(self):
        from agent_braid.forecast_advice import ForecastSession
        original = ForecastSession.close
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(strict=True) / 'new-output'
            def interrupted(session):
                os.kill(os.getpid(), signal.SIGTERM)
                return original(session)
            with patch('sys.argv', ['cost', '--output-directory', str(root)]), \
                 patch.object(ForecastSession, 'close', interrupted):
                self.assertEqual(143, main())
            ledger = parse_record((root / 'ledger.json').read_bytes())
            self.assertTrue(ledger['cleanupConfirmed'])
            summary = parse_record((root / 'summary.json').read_bytes())
            self.assertEqual('synthetic-cost-procedure-interrupted', summary['error'])

    def test_sigterm_after_new_output_creation_keeps_registered_preflight(self):
        original = Path.mkdir
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(strict=True) / 'new-output'
            def interrupted(path, *args, **kwargs):
                result = original(path, *args, **kwargs)
                if path == root: os.kill(os.getpid(), signal.SIGTERM)
                return result
            with patch('sys.argv', ['cost', '--output-directory', str(root)]), \
                 patch.object(Path, 'mkdir', interrupted):
                self.assertEqual(143, main())
            ledger = parse_record((root / 'ledger.json').read_bytes())
            self.assertIsNone(ledger['artifactDigest'])
            summary = parse_record((root / 'summary.json').read_bytes())
            self.assertEqual('synthetic-cost-procedure-interrupted', summary['error'])
