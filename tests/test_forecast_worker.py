# SPDX-License-Identifier: AGPL-3.0-only
import subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from agent_braid.forecast_data import ForecastError,digest
from agent_braid.forecast_worker import DockerCPUWorker,PROFILE,SOURCE_REVISION,CHECKPOINT_REVISION,validate_manifest
from agent_braid.forecast_lease import WorkerLease
from agent_braid.forecast_authority import ArtifactApprovalAttestation
from tests.forecast_helpers import window

def manifest():
    return {'version':'agent-braid-chronos-cpu-manifest-v1','imageId':'sha256:'+'a'*64,
            'checkpointDirectory':'/not-provisioned/model','files':{'config.json':'b'*64,'model.safetensors':'c'*64},
            'engineSocket':'/not-provisioned/engine.sock','dependencyLockDigest':'d'*64,'libraryVersion':'2.3.2',
            'sourceRevision':SOURCE_REVISION,'checkpointRevision':CHECKPOINT_REVISION,'profile':dict(PROFILE)}

class TestControlVerifier:
    def verify(self,m):return ArtifactApprovalAttestation(digest(m),'e'*64,'owner-artifact-compute')

class ForecastWorkerTests(unittest.TestCase):
    def test_simulated_daemon_loss_preserves_container_identity_and_blocks_new_lease(self):
        # Pure synthetic fault injection. Never contacts or stops a Docker daemon.
        with tempfile.TemporaryDirectory() as tmp:
            worker=DockerCPUWorker(manifest(),artifact_verifier=TestControlVerifier())
            root=Path(tmp).resolve()/'lease';worker.lease=WorkerLease(worker.owner,worker.model_digest,directory=root)
            worker.lease.acquire();worker.container='a'*64;worker.loaded=True
            with patch.object(worker,'_write',side_effect=ForecastError('local-engine-unavailable')), \
                 patch.object(worker,'_inspect',side_effect=ForecastError('local-engine-unavailable')), \
                 patch.object(worker,'_docker') as docker:
                result=worker.forecast(window(),1)
                self.assertEqual('refused',result['status'])
                self.assertEqual(['owned-container-cleanup-pending'],result['reasonCodes'])
                self.assertFalse(result['executionAuthorization']);self.assertFalse(worker.loaded)
                self.assertEqual('a'*64,worker.container);self.assertIsNone(worker.last_diagnostics)
                with self.assertRaisesRegex(ForecastError,'cleanup-pending'):
                    WorkerLease('next','b'*64,directory=root).acquire()
                with self.assertRaisesRegex(ForecastError,'local-engine-unavailable'):worker.close()
                docker.assert_not_called()
            # Later container removal is insufficient to clear a released marker.
            # Recovery of that persistent marker remains an operator procedure.
            worker._inspect=lambda:{'State':{'Running':False,'OOMKilled':False,'ExitCode':1}}
            worker._docker=lambda *args,**kwargs:b''
            worker.close()
            successor=WorkerLease('recovered','b'*64,directory=root)
            self.assertTrue(worker.last_diagnostics['cleanupConfirmed'])
            with self.assertRaisesRegex(ForecastError,'cleanup-pending'):successor.acquire()

    def test_owned_oom_diagnostics_survive_cleanup_without_raw_engine_errors(self):
        worker=DockerCPUWorker(manifest(),artifact_verifier=TestControlVerifier());worker.container='a'*64
        worker._inspect=lambda:{'State':{'OOMKilled':True,'ExitCode':137,'Running':False,'Error':'private-engine-detail'}}
        worker._docker=lambda *args,**kwargs:b''
        worker.close();self.assertTrue(worker.last_diagnostics['oomKilled']);self.assertEqual(137,worker.last_diagnostics['exitCode'])
        self.assertTrue(worker.last_diagnostics['cleanupConfirmed']);self.assertNotIn('Error',worker.last_diagnostics);self.assertIsNone(worker.container)

    def test_docker_stdout_stderr_and_cancel_are_stream_bounded(self):
        worker=DockerCPUWorker(manifest(),artifact_verifier=TestControlVerifier());worker.private_config=Path('/not-read')
        for fd,reason in ((1,'docker-output-budget'),(2,'docker-stderr-budget')):
            worker._argv=lambda *args,fd=fd:[sys.executable,'-c',f'import os;os.write({fd},b"x"*2097152)']
            with self.assertRaisesRegex(ForecastError,reason):worker._docker('synthetic-control')
        worker._argv=lambda *args:[sys.executable,'-c','import time;time.sleep(5)']
        cancelled=threading.Event();timer=threading.Timer(.03,cancelled.set);timer.start()
        try:
            with self.assertRaisesRegex(ForecastError,'cancelled'):worker._docker('synthetic-control',cancellation=cancelled)
        finally:timer.join();worker.close()

    def test_uncertain_create_keeps_cleanup_marker_and_refuses_next_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            worker=DockerCPUWorker(manifest(),artifact_verifier=TestControlVerifier())
            root=Path(tmp).resolve()/'lease';worker.lease=WorkerLease(worker.owner,worker.model_digest,directory=root)
            worker.lease.acquire();worker.create_unconfirmed=True
            with self.assertRaisesRegex(ForecastError,'cleanup-pending'):worker.close()
            with self.assertRaisesRegex(ForecastError,'cleanup-pending'):WorkerLease('next','a'*64,directory=root).acquire()

    def test_digest_is_not_approval_and_changed_profile_refuses(self):
        m=manifest()
        with self.assertRaises(ForecastError):validate_manifest(m,artifact_verifier=None)
        m['profile']['memoryBytes']+=1
        with self.assertRaises(ForecastError):validate_manifest(m,artifact_verifier=TestControlVerifier())

    def test_manifest_is_copied_and_pending_files_refuse_before_container(self):
        m=manifest();worker=DockerCPUWorker(m,artifact_verifier=TestControlVerifier());m['libraryVersion']='main'
        self.assertEqual('2.3.2',worker.manifest['libraryVersion'])
        # Inject a synthetic private lease; no actual model or Docker call.
        with tempfile.TemporaryDirectory() as tmp:
            worker.lease=WorkerLease(worker.owner,worker.model_digest,directory=Path(tmp).resolve()/'lease')
            out=worker.forecast(window(),1)
            self.assertEqual('refused',out['status']);self.assertIsNone(worker.container);worker.close()

    def test_cross_process_lease_blocks_and_unclean_release_remains_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'lease';one=WorkerLease('one','a'*64,directory=root);one.acquire()
            code='from agent_braid.forecast_lease import WorkerLease;from pathlib import Path;WorkerLease("two","b"*64,directory=Path(__import__("sys").argv[1])).acquire()'
            result=subprocess.run([sys.executable,'-c',code,str(root)],capture_output=True,timeout=5)
            self.assertNotEqual(0,result.returncode);self.assertIn(b'worker-busy',result.stderr)
            one.release(cleanup_confirmed=False)
            with self.assertRaisesRegex(ForecastError,'cleanup-pending'):WorkerLease('three','c'*64,directory=root).acquire()

    def test_confirmed_cleanup_allows_next_owner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()/'lease';one=WorkerLease('one','a'*64,directory=root);one.acquire();one.release(cleanup_confirmed=True)
            two=WorkerLease('two','b'*64,directory=root);two.acquire();two.release(cleanup_confirmed=True)

    def test_pipe_read_hang_and_cancel_are_bounded(self):
        worker=DockerCPUWorker(manifest(),artifact_verifier=TestControlVerifier())
        worker.process=subprocess.Popen([sys.executable,'-c','import time;time.sleep(5)'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            with self.assertRaisesRegex(ForecastError,'deadline-exceeded'):worker._read(time.monotonic()+.03,None)
            event=threading.Event();event.set()
            with self.assertRaisesRegex(ForecastError,'cancelled'):worker._read(time.monotonic()+1,event)
        finally:worker._close_owned()

    def test_first_request_is_returned_once_then_resident_budget_is_one_second(self):
        worker=DockerCPUWorker(manifest(),artifact_verifier=TestControlVerifier());calls=[]
        def output(request):
            return {'status':'forecast','bindingDigest':request['bindingDigest'],'quantiles':[[[[1,2,3]]]],
                    'median':[[[2]]],'rssBytes':1024,'containerMemoryBytes':2048,'modelCpuNs':1}
        def start(deadline,cancellation,request):
            self.assertFalse(worker.loaded);self.assertEqual(130,deadline);calls.append(request);return output(request)
        worker._start=start;worker._checkpoint_deadline=lambda *args:None
        worker._write=lambda request,*args:calls.append(request)
        worker._read=lambda deadline,cancellation: (self.assertEqual(101,deadline) or output(calls[-1]))
        with patch('agent_braid.forecast_worker.time.monotonic_ns',return_value=100000000000), \
             patch('agent_braid.forecast_worker.time.monotonic',return_value=100):
            first=worker.forecast(window(),1);second=worker.forecast(window(),1)
        self.assertEqual('forecast',first['status']);self.assertTrue(worker.loaded)
        self.assertEqual('forecast',second['status']);self.assertEqual(2,len(calls))
        self.assertEqual(digest(window()),calls[0]['inputDigest']);worker.close()

    def test_first_timeout_or_invalid_result_never_establishes_readiness(self):
        for reason in ('deadline-exceeded','invalid-output'):
            worker=DockerCPUWorker(manifest(),artifact_verifier=TestControlVerifier())
            def start(deadline,cancellation,request):
                self.assertEqual(100.25,deadline)
                if reason=='deadline-exceeded':raise ForecastError(reason)
                return {'status':'forecast','bindingDigest':'f'*64}
            worker._start=start;worker._checkpoint_deadline=lambda *args:None
            with patch('agent_braid.forecast_worker.time.monotonic_ns',return_value=100000000000):
                result=worker.forecast(window(),1,deadline=100.25)
            self.assertFalse(worker.loaded);self.assertNotEqual('forecast',result['status']);worker.close()

    def test_resident_validation_and_binding_consume_the_same_one_second_budget(self):
        worker=DockerCPUWorker(manifest(),artifact_verifier=TestControlVerifier());worker.loaded=True
        with patch('agent_braid.forecast_worker.time.monotonic_ns',return_value=100000000000), \
             patch('agent_braid.forecast_worker.time.monotonic',return_value=102), \
             patch.object(worker,'_write') as write:
            result=worker.forecast(window(),1)
        write.assert_not_called();self.assertEqual('timed-out',result['status'])
        self.assertFalse(worker.loaded);worker.close()
