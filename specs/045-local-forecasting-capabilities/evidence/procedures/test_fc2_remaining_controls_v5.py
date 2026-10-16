import importlib.util,io,json,os,subprocess,sys,tempfile,time,unittest
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
spec=importlib.util.spec_from_file_location('remaining',Path(__file__).with_name('fc2_remaining_controls_v5.py'))
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)
class ControlsAdmissionTests(unittest.TestCase):
    def test_plan_is_read_only_and_never_checks_or_grants_artifact_authority(self):
        with patch.object(driver.sys,'argv',['controls','--manifest','missing','--output','missing']),patch.object(driver,'DeploymentArtifactVerifier') as verifier,patch.object(driver,'ForecastSession') as session,redirect_stdout(io.StringIO()) as stream:
            self.assertEqual(0,driver.main())
        verifier.assert_not_called();session.assert_not_called();self.assertEqual(9,json.loads(stream.getvalue())['maxForecastRequests'])
    def test_missing_owner_admission_refuses_before_output_and_any_model_or_docker_call(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'result.json'
            with patch.object(driver.sys,'argv',['controls','--execute','--manifest','fake','--output',str(output)]),patch.object(driver,'read_input',return_value={}),patch.object(driver,'DeploymentArtifactVerifier') as verifier,patch.object(driver,'ForecastSession') as session,patch.object(driver.subprocess,'run') as run:
                verifier.return_value.verify.return_value=None
                with self.assertRaisesRegex(Exception,'artifact-not-approved'):driver.main()
            self.assertFalse(output.exists());session.assert_not_called();run.assert_not_called()
    def test_existing_output_is_preserved_before_any_model_or_docker_call(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'result.json';output.write_text('preserve')
            with patch.object(driver.sys,'argv',['controls','--execute','--manifest','fake','--output',str(output)]),patch.object(driver,'read_input',return_value={}),patch.object(driver,'DeploymentArtifactVerifier'),patch.object(driver,'ForecastSession') as session,patch.object(driver.subprocess,'run') as run:
                with self.assertRaises(FileExistsError):driver.main()
            self.assertEqual('preserve',output.read_text());session.assert_not_called();run.assert_not_called()
class BoundedControlProcessTests(unittest.TestCase):
    def test_both_output_streams_are_capped_during_read_and_owned_process_exits(self):
        for fd in (1,2):
            seen={}
            with self.assertRaisesRegex(Exception,'control-output-budget'):
                driver.bounded_process([sys.executable,'-c',f'import os;os.write({fd},b"x"*2097152)'],{},time.monotonic()+3,seen)
            self.assertLessEqual(len(seen['stdout']),driver.MAX_BYTES);self.assertLessEqual(seen['stderrBytes'],driver.MAX_BYTES)
            self.assertTrue(seen['processExited'])
    def test_timeout_stops_only_the_process_created_for_this_control(self):
        seen={};start=time.monotonic()
        with self.assertRaisesRegex(Exception,'control-deadline-exceeded'):
            driver.bounded_process([sys.executable,'-c','import time;time.sleep(5)'],{},start+.1,seen)
        self.assertLess(time.monotonic()-start,3);self.assertTrue(seen['processExited'])
        with self.assertRaises(ProcessLookupError):os.kill(seen['ownedPid'],0)
    def test_bounded_stdout_stderr_and_nonzero_exit_are_retained(self):
        seen={};result=driver.bounded_process([sys.executable,'-c','import os;os.write(1,b"out");os.write(2,b"err");raise SystemExit(17)'],{},time.monotonic()+3,seen)
        self.assertEqual((17,b'out',b'err'),(result.returncode,result.stdout,result.stderr));self.assertTrue(seen['completed'])
class RunBoundaryTests(unittest.TestCase):
    def test_atomic_claim_allows_only_one_competing_process(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve();script=Path(__file__).with_name('fc2_remaining_controls_v5.py').resolve()
            code="import importlib.util,sys;from pathlib import Path;s=importlib.util.spec_from_file_location('control',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.claim_run(Path(sys.argv[2]),'b'*64,'a'*64)"
            processes=[subprocess.Popen([sys.executable,'-c',code,str(script),str(root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
            results=[p.communicate(timeout=5) for p in processes]
            self.assertEqual(1,sum(p.returncode==0 for p in processes));self.assertEqual(1,len(list(root.glob('fc2-run-*.json'))))
            self.assertTrue(any(b'FileExistsError' in error for _,error in results))
            claim=json.loads(next(root.glob('fc2-run-*.json')).read_text());self.assertTrue(claim['oneRun'])
    def test_complete_reservation_is_checked_before_claim_or_model(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'receipt.json';wheel=Path(__file__).parent/'wheels-independent-reproduction/agent_braid-0.1.0a1-py3-none-any.whl'
            argv=['controls','--execute','--manifest','fake','--output',str(output),'--host-wheel',str(wheel)]
            with patch.object(driver.sys,'argv',argv),patch.object(driver,'read_input',return_value={}),patch.object(driver,'DeploymentArtifactVerifier') as verifier,patch.object(driver,'ForecastSession') as model,patch.object(driver,'claim_run') as claim,patch.object(driver.sysconfig,'get_paths',return_value={'purelib':str(Path(driver.agent_braid.__file__).resolve().parent.parent)}),patch.object(driver.time,'monotonic_ns',return_value=100000000000),patch.object(driver.time,'monotonic',return_value=105),redirect_stdout(io.StringIO()):
                verifier.return_value.verify.return_value=SimpleNamespace(source_record_digest='b'*64)
                self.assertEqual(2,driver.main())
            model.assert_not_called();claim.assert_not_called();receipt=json.loads(output.read_text());self.assertEqual(0,receipt['forecastRequests']);self.assertFalse(receipt['runClaimed'])
            self.assertEqual('complete-procedure-reservation-unavailable',receipt['rows'][-1]['reason'])
    def test_interrupted_public_attempt_is_retained_and_owned_session_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'receipt.json'
            wheel=Path(__file__).parent/'wheels-independent-reproduction/agent_braid-0.1.0a1-py3-none-any.whl'
            fake=SimpleNamespace(adapter=SimpleNamespace(worker=None),predict=lambda *a,**k: (_ for _ in ()).throw(KeyboardInterrupt()))
            closed=[];fake.close=lambda:closed.append(True)
            attestation=SimpleNamespace(source_record_digest='b'*64)
            argv=['controls','--execute','--manifest','fake','--output',str(output),'--host-wheel',str(wheel)]
            with patch.object(driver.sys,'argv',argv),patch.object(driver,'read_input',return_value={}),patch.object(driver,'DeploymentArtifactVerifier') as verifier,patch.object(driver,'ForecastSession',return_value=fake),patch.object(driver,'claim_run'),patch.object(driver.sysconfig,'get_paths',return_value={'purelib':str(Path(driver.agent_braid.__file__).resolve().parent.parent)}),redirect_stdout(io.StringIO()):
                verifier.return_value.verify.return_value=attestation
                self.assertEqual(2,driver.main())
            receipt=json.loads(output.read_text());self.assertEqual('inconclusive',receipt['status']);self.assertEqual(1,receipt['forecastRequests']);self.assertEqual('attempted',receipt['rows'][0]['status']);self.assertTrue(closed)
            self.assertEqual('KeyboardInterrupt',receipt['rows'][-1]['exceptionType'])
class ChildFrameRegressionTests(unittest.TestCase):
    def child(self,code):
        p=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        self.addCleanup(self.cleanup,p);return p
    def cleanup(self,p):
        if p.poll() is None:p.kill()
        p.wait(timeout=2);p.stdout.close();p.stderr.close()
    def test_cli_single_line_json_is_bytes_and_complete_output_retained(self):
        p=self.child('import json;print(json.dumps({"status":"forecast","median":[[3.0]]}))');seen={}
        frames=driver.child_frames(p,1,2,seen)
        self.assertEqual([{'status':'forecast','median':[[3.0]]}],frames)
        self.assertEqual(frames,seen['parsedFrames']);self.assertEqual(frames[0],json.loads(seen['stdout']))
    def test_fragmented_mcp_two_records_and_stderr_are_preserved(self):
        code='import os,time;os.write(1,b"{\\"id\\":1}\\n{\\"id\\":");os.write(2,b"diagnostic");time.sleep(.05);os.write(1,b"2}\\n")'
        p=self.child(code);seen={};frames=driver.child_frames(p,2,2,seen)
        self.assertEqual([{'id':1},{'id':2}],frames);self.assertEqual(10,seen['stderrBytes']);self.assertEqual(frames,[json.loads(x) for x in seen['stdout'].splitlines()])
    def test_malformed_second_frame_retains_raw_and_first_valid_frame(self):
        p=self.child('import os;os.write(1,b"{\\"id\\":1}\\nnot-json\\n")');seen={}
        with self.assertRaises(Exception):driver.child_frames(p,2,2,seen)
        self.assertIn('not-json',seen['stdout']);self.assertEqual([{'id':1}],seen['parsedFrames'])
    def test_stdout_is_bounded_before_retaining_oversize_chunk(self):
        p=self.child('import os;os.write(1,b"x"*2097152)');seen={}
        with self.assertRaisesRegex(Exception,'child-output-budget'):driver.child_frames(p,1,2,seen)
        self.assertLessEqual(len(seen['stdout']),driver.MAX_BYTES)

if __name__=='__main__':unittest.main()
