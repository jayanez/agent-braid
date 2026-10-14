# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
from unittest.mock import patch
from scripts.reproduce_forecast_cpu import additional_cases
from agent_braid.forecast_chronos_inputs import translate_inputs

class CpuProcedureTests(unittest.TestCase):
    def test_frozen_multivariate_and_causal_covariate_probes_have_exact_axes(self):
        cases=additional_cases();self.assertEqual(3,len(cases))
        multi=translate_inputs(cases[0][1],5)[0];self.assertEqual(2,len(multi['target']))
        future=translate_inputs(cases[2][1],5)[0]
        self.assertEqual(128,len(future['past_covariates']['calendar']));self.assertEqual(5,len(future['future_covariates']['calendar']))
        self.assertNotIn('future_target',future)
        self.assertEqual(additional_cases(),cases)

    def test_failed_shape_and_cancellation_attempts_keep_diagnostics_after_cleanup(self):
        from scripts import reproduce_forecast_cpu as procedure
        for fail_shape in (True,False):
            with self.subTest(fail_shape=fail_shape), tempfile.TemporaryDirectory() as directory:
                output=Path(directory)/'receipt.json'
                class Worker:
                    def __init__(self,*args,**kwargs):
                        self.loaded=True;self.container='owned';self.lock=threading.Lock();self.calls=0
                        self.last_diagnostics={'OOMKilled':False,'ExitCode':0,'cleanupConfirmed':True}
                    def forecast(self,window,horizon,*,cancellation=None,**kwargs):
                        self.calls+=1
                        if fail_shape and self.calls==169:
                            self.last_diagnostics={'OOMKilled':True,'ExitCode':137,'cleanupConfirmed':True}
                            return {'status':'unavailable','reason':'worker-oom'}
                        if cancellation is not None:
                            with self.lock:
                                cancellation.wait(timeout=1)
                                self.container=None
                            return {'status':'cancelled'}
                        return {'status':'forecast'}
                    def close(self):self.last_diagnostics={}
                verifier=SimpleNamespace(verify=lambda manifest:SimpleNamespace(source_record_digest='a'*64))
                with patch.object(procedure,'DeploymentArtifactVerifier',return_value=verifier), \
                     patch('agent_braid.forecast_cli.read_input',return_value={'synthetic':True}), \
                     patch('agent_braid.forecast_worker.DockerCPUWorker',Worker), \
                     patch('sys.argv',['procedure','--manifest','unused','--output',str(output)]), \
                     redirect_stdout(StringIO()):
                    result=procedure.main()
                packet=json.loads(output.read_text())
                self.assertTrue(packet['cleanup']['confirmed'])
                self.assertTrue(all(row['containerDiagnostics'] for row in packet['rows']))
                if fail_shape:
                    self.assertEqual(2,result)
                    self.assertEqual('shape-conformance',packet['rows'][-1]['role'])
                    self.assertEqual(137,packet['rows'][-1]['containerDiagnostics']['ExitCode'])
                else:
                    self.assertEqual(0,result)
                    self.assertEqual(173,len(packet['rows']))
                    self.assertTrue(packet['activeRequestCancellationObserved'])
                    self.assertEqual(['active-request-cancellation','cancel-control'],[row['role'] for row in packet['rows'][-2:]])
