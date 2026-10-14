# SPDX-License-Identifier: AGPL-3.0-only
import subprocess,sys,tempfile,threading,time,unittest
from pathlib import Path
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
