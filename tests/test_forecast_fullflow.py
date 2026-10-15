# SPDX-License-Identifier: AGPL-3.0-only
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_lab import signal_episode
from agent_braid.forecast_outputs import envelope
from agent_braid.forecast_fullflow import validate_model_batch, run_selected_flow


def simulated_batch(window, nonce):
    rows = []
    for horizon in (1, 5, 1):
        packet = envelope(window, horizon, model_digest='b'*64,
                          quantiles=[[[3., 4., 5.] for _ in range(horizon)]])
        rows.append({'horizon': horizon, 'wallNs': 10, 'forecast': packet})
    batch = dict(version='agent-braid-selected-model-batch-v1', runNonce=nonce,
                 sourceKind='synthetic-simulation', manifestDigest='b'*64,
                 inputDigest=digest(window), rows=rows, backendCalls=2,
                 cacheHit=True, cleanupConfirmed=True, collectorDigest='c'*64,
                 counterReceiptDigest='d'*64)
    batch['receiptDigest'] = digest(batch)
    return batch


class FullFlowTests(unittest.TestCase):
    def test_valid_batch_has_three_session_calls_but_only_two_model_calls(self):
        window=signal_episode('constant',seed=20261015)['window']
        result=validate_model_batch(simulated_batch(window,'a'*32),window,'a'*32,'synthetic-simulation')
        self.assertEqual(2,result['backendCalls']); self.assertEqual(3,len(result['rows']))

    def test_batch_rejects_prior_nonce_altered_window_extra_call_and_fake_cache(self):
        window=signal_episode('constant',seed=20261015)['window']
        original=simulated_batch(window,'a'*32)
        for field,value in [('runNonce','e'*32),('inputDigest','e'*64),('backendCalls',3),
                            ('cacheHit',False),('cleanupConfirmed',False),('sourceKind','authentic-on-synthetic')]:
            with self.subTest(field=field):
                bad=deepcopy(original);bad[field]=value
                bad['receiptDigest']=digest({k:v for k,v in bad.items() if k!='receiptDigest'})
                with self.assertRaises(ForecastError):
                    validate_model_batch(bad,window,'a'*32,'synthetic-simulation')

    def test_complete_host_flow_retains_six_verified_arms_and_payload_boundary(self):
        from agent_braid.runtime_policy import issue_operator_grant
        def operator(plan,root): return issue_operator_grant(plan,root,acknowledge=plan['planDigest'])
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp).resolve()/'new'
            code=run_selected_flow(output,collector=simulated_batch,operator=operator,
                                   artifact_digest='a'*64,source_kind='synthetic-simulation')
            self.assertEqual(0,code)
            record=json.loads((output/'operation.json').read_bytes())
            payload=json.loads((output/'payload.json').read_bytes())
            self.assertEqual(2,len(payload['pairedEpisodes']))
            self.assertTrue(all(a['status']=='completed' for e in payload['pairedEpisodes'] for a in e['arms']))
            self.assertTrue(record['payloadPublicationIncluded']);self.assertFalse(record['attestationPublicationIncluded'])
            self.assertIn('publication:final-receipt-write-after-seal',record['costSummary']['gaps'])
            self.assertFalse(record['fullDeploymentCostAccepted']);self.assertFalse(record['utilityAccepted'])
            self.assertEqual(2,record['backendCalls']); self.assertTrue(record['cleanupConfirmed'])
            self.assertEqual('authentic-on-synthetic',record['ledger']['sourceKind'])
            self.assertEqual('synthetic-simulation',record['modelSourceKind'])
            self.assertTrue(all(p.stat().st_mode & 0o777==0o600 for p in output.iterdir()))

    def test_existing_output_refuses_before_collecting(self):
        with tempfile.TemporaryDirectory() as tmp:
            collector=Mock()
            with self.assertRaises(FileExistsError):
                run_selected_flow(Path(tmp).resolve(),collector=collector,operator=Mock(),artifact_digest='a'*64)
            collector.assert_not_called()

    def test_invalid_external_grants_keep_all_attempts_and_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp).resolve()/'new'
            code=run_selected_flow(output,collector=simulated_batch,operator=lambda *a:{'grantId':'missing'},
                                   artifact_digest='a'*64,source_kind='synthetic-simulation')
            self.assertEqual(2,code)
            payload=json.loads((output/'payload.json').read_bytes())
            self.assertEqual(6,sum(len(e['arms']) for e in payload['pairedEpisodes']))
            self.assertTrue(all(a['status']=='failed' for e in payload['pairedEpisodes'] for a in e['arms']))
            record=json.loads((output/'operation.json').read_bytes())
            self.assertEqual('incomplete-selected-flow',record['error']);self.assertFalse(record['fullDeploymentCostAccepted'])

    def test_collection_interrupt_retains_terminal_receipt_without_fake_cleanup(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp).resolve()/'new'
            code=run_selected_flow(output,collector=Mock(side_effect=KeyboardInterrupt),operator=Mock(),artifact_digest='a'*64)
            self.assertEqual(130,code)
            record=json.loads((output/'operation.json').read_bytes())
            self.assertFalse(record['cleanupConfirmed']);self.assertEqual(0,record['backendCalls'])
            self.assertTrue(any(p['status']=='failed' for p in record['ledger']['phases']))

    def test_export_failure_retains_partial_files_and_uncovered_publication(self):
        from agent_braid import forecast_fullflow as flow
        original=flow._write
        def failed(directory,name,value):
            if name=='payload.json':raise OSError('synthetic-storage-failure')
            return original(directory,name,value)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp).resolve()/'new'
            with patch.object(flow,'_write',side_effect=failed):
                code=run_selected_flow(output,collector=simulated_batch,operator=lambda *a:{'grantId':'missing'},
                                       artifact_digest='a'*64,source_kind='synthetic-simulation')
            self.assertEqual(2,code)
            record=json.loads((output/'operation.json').read_bytes())
            self.assertFalse(record['payloadPublicationIncluded']);self.assertTrue(record['cleanupConfirmed'])

    def test_mid_arm_interrupt_and_timeout_preserve_partial_and_unattempted_roster(self):
        import subprocess
        for error,reason,code in ((KeyboardInterrupt(),'paired-arm-cancelled',130),
                                  (subprocess.TimeoutExpired('synthetic-grant',1),'paired-arm-timed-out',2)):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as tmp:
                output=Path(tmp).resolve()/'partial'
                def interrupted_operator(*args):
                    intent=json.loads((output/'arm-progress-0-1-start.json').read_bytes())
                    self.assertEqual('started-outcome-unknown',intent['activeArm']['status'])
                    self.assertEqual(2,len(intent['notRunArms']))
                    raise error
                self.assertEqual(code,run_selected_flow(output,collector=simulated_batch,
                    operator=interrupted_operator,artifact_digest='a'*64,source_kind='synthetic-simulation'))
                payload=json.loads((output/'payload.json').read_bytes())
                self.assertEqual([],payload['pairedEpisodes'])
                self.assertEqual(1,len(payload['partialEpisodes']))
                partial=payload['partialEpisodes'][0]
                self.assertEqual(partial,json.loads((output/'arm-progress-0-1-end.json').read_bytes()))
                self.assertEqual(1,len(partial['arms']));self.assertEqual(2,len(partial['notRunArms']))
                self.assertEqual(reason,partial['arms'][0]['reason'])
                self.assertGreater(partial['arms'][0]['wallNs'],0)
                result=json.loads((output/'operation.json').read_bytes())
                self.assertFalse(result['cleanupConfirmed']);self.assertFalse(result['fullDeploymentCostAccepted'])

    def test_terminal_storage_failure_propagates_and_keeps_existing_payload(self):
        from agent_braid import forecast_fullflow as flow
        original=flow._write
        def failed(directory,name,value):
            if name=='operation.json':raise OSError('synthetic-terminal-storage-failure')
            return original(directory,name,value)
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp).resolve()/'storage'
            with patch.object(flow,'_write',side_effect=failed):
                with self.assertRaises(OSError):
                    run_selected_flow(output,collector=Mock(side_effect=ValueError('no-worker')),
                                      operator=Mock(),artifact_digest='a'*64)
            self.assertTrue((output/'payload.json').exists())
            self.assertTrue((output/'start.json').exists())
            self.assertFalse((output/'operation.json').exists())

    def test_public_driver_default_cannot_dispatch_collector(self):
        from scripts.reproduce_forecast_fullflow import main
        with patch('sys.argv',['fullflow']), patch('agent_braid.forecast_fullflow.run_selected_flow') as run:
            self.assertEqual(0,main())
            run.assert_not_called()
