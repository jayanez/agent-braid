# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic protocol and own-process controls; never runs guest shell commands."""
import base64,hashlib,importlib.util,json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1] / 'scripts' / 'forecast_engine_probe'
sys.path.insert(0,str(ROOT))
import engine_protocol as protocol
spec=importlib.util.spec_from_file_location('shell_probe',ROOT/'approved_engine_probe.py');probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)

def http(value):
 body=json.dumps(value,separators=(',',':')).encode()
 return b'HTTP/1.0 200 OK\r\nContent-Length: '+str(len(body)).encode()+b'\r\n\r\n'+body

def process_stat(pid=42,birth=123,cpu=1):
 fields=['S']+['0']*21;fields[11]=str(cpu);fields[12]='0';fields[19]=str(birth)
 return (str(pid)+' (dockerd) '+' '.join(fields)).encode()

def events():
 return {'daemonExecIdentity':b'yes','runtimeSearchPath':b'/usr/bin/runc','runtimeShimSearchPath':b'/usr/bin/containerd-shim-runc-v2','prerequisiteReady':b'yes','infoHttp':http({'DockerRootDir':protocol.ROOT,'ID':'synthetic-id','LiveRestoreEnabled':False,'Containers':0,'ServerVersion':'synthetic'}),
  'imagesHttp':http([]),'containersHttp':http([]),'launchedStat':process_stat(),'preCrashStat':process_stat(cpu=3),
  'status':b'engine-ready-and-owned-daemon-crashed','signal':b'1','waitStatus':b'137','readinessProbes':b'1','wallNs':b'1000000',
  'clockTicksPerSecond':b'100','postFaultClientStatus':b'1','postFaultBytes':b'0','bootId':b'synthetic-boot',
  'cgroupControllers':b'cpu memory pids','configurationSha256':hashlib.sha256(protocol.CONFIG).hexdigest().encode(),'daemonLogDrainComplete':b'yes','daemonConfigValidated':b'yes'}

def console(value):
 return '\n'.join('FC2_ENGINE_EVENT '+key+' '+base64.b64encode(raw).decode() for key,raw in value.items())+'\n'

class ShellProtocolTests(unittest.TestCase):
 def test_guest_script_parses_as_bash_without_executing(self):
  result=subprocess.run(['/bin/bash','-n',str(ROOT/'guest_engine_probe.sh')],capture_output=True,text=True)
  self.assertEqual(0,result.returncode,result.stderr)

 def test_existing_dev_mount_is_detected_without_remount(self):
  script=(ROOT/'guest_engine_probe.sh').read_text()
  parser=script.split('# BEGIN PURE MOUNT-TABLE PARSER\n',1)[1].split('# END PURE MOUNT-TABLE PARSER',1)[0]
  with tempfile.TemporaryDirectory() as tmp:
   table=Path(tmp)/'mounts'
   cases=[('proc /proc proc rw 0 0\n','',0),
    ('devtmpfs /dev devtmpfs rw,nosuid 0 0\n','devtmpfs',0),
    ('/dev/vda /dev ext4 rw,relatime 0 0\n','ext4',0),
    ('devtmpfs /dev devtmpfs rw 0 0\ndevtmpfs /dev devtmpfs rw 0 0\n','',2)]
   for content,expected,exit_code in cases:
    table.write_text(content)
    result=subprocess.run(['/bin/bash','-c',parser+'\nfc2_mount_type /dev "$1"','mount-parser-test',str(table)],capture_output=True,text=True)
    self.assertEqual(exit_code,result.returncode)
    self.assertEqual(expected,result.stdout)

 def test_valid_guest_observation_and_host_guard(self):
  result=protocol.parse_console(console(events()));self.assertTrue(probe.engine_qualified(result));self.assertEqual(3,result['preCrashIdentity']['cpuTicks'])
 def test_missing_or_negative_daemon_executable_identity_cannot_admit_or_qualify(self):
  for value in [None,b'no']:
   sample=events()
   if value is None:sample.pop('daemonExecIdentity')
   else:sample['daemonExecIdentity']=value
   with self.assertRaisesRegex(ValueError,'daemon-executable-identity'):protocol.prerequisites(sample)
   with self.assertRaisesRegex(ValueError,'daemon-executable-identity'):protocol.parse_console(console(sample))

 def test_incomplete_diagnostic_preserves_failed_log_drain(self):
  sample={'status':b'incomplete','daemonLogAvailable':b'yes','daemonLogDrainComplete':b'no',
          'daemonLogBase64':b'partial','daemonLogBytes':b'7','daemonLogTruncated':b'no'}
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'console';path.write_text(console(sample));path.chmod(0o600)
   result=probe.guest_receipt(path)
  self.assertFalse(result['daemonLogDrainComplete'])
  self.assertFalse(result['ownedDaemonCrash'])

 def test_incomplete_log_is_decoded_exactly_once_including_base64_looking_bytes(self):
  for detail in [b'',b'YWJj',b'ordinary log: not base64\n',b'\xff\x00binary']:
   with self.subTest(detail=detail),tempfile.TemporaryDirectory() as tmp:
    sample={'status':b'incomplete','daemonLogAvailable':b'yes','daemonLogDrainComplete':b'yes',
            'daemonLogBase64':detail,'daemonLogBytes':str(len(detail)).encode(),'daemonLogTruncated':b'no'}
    path=Path(tmp)/'console';path.write_text(console(sample));path.chmod(0o600)
    result=probe.guest_receipt(path)
    self.assertEqual(detail,base64.b64decode(result['daemonLogBase64']))
    self.assertEqual(detail.decode('utf-8',errors='replace'),result['daemonLogText'])
    self.assertFalse(result['ownedDaemonCrash']);self.assertFalse(result['executionAuthorization'])

 def test_incomplete_log_missing_payload_or_inconsistent_length_refuses(self):
  for patch_value in [{'daemonLogBytes':b'6'},{'daemonLogTruncated':b'yes'},{'daemonLogBytes':b'-1'},
                      {'daemonLogBase64':None}]:
   sample={'status':b'incomplete','daemonLogAvailable':b'yes','daemonLogDrainComplete':b'yes',
           'daemonLogBase64':b'partial','daemonLogBytes':b'7','daemonLogTruncated':b'no'}
   for key,value in patch_value.items():
    if value is None:sample.pop(key)
    else:sample[key]=value
   with self.subTest(patch=patch_value),tempfile.TemporaryDirectory() as tmp:
    path=Path(tmp)/'console';path.write_text(console(sample));path.chmod(0o600)
    with self.assertRaises((KeyError,ValueError)):probe.guest_receipt(path)

 def test_unknown_runc_search_path_refuses(self):
  sample=events();sample['runtimeSearchPath']=b'/missing/runc'
  with self.assertRaisesRegex(ValueError,'runc-search-path'):protocol.prerequisites(sample)
  sample=events();sample['runtimeShimSearchPath']=b'/missing/containerd-shim-runc-v2'
  with self.assertRaisesRegex(ValueError,'runtime-shim-search-path'):protocol.prerequisites(sample)
 def test_bad_root_live_restore_or_nonempty_population_refuses(self):
  for field,value in [('DockerRootDir','/var/lib/docker'),('LiveRestoreEnabled',True),('Containers',True)]:
   sample=events();info=protocol.http_json(sample['infoHttp']);info[field]=value;sample['infoHttp']=http(info)
   with self.assertRaises(ValueError):protocol.prerequisites(sample)
  for field in ['imagesHttp','containersHttp']:
   sample=events();sample[field]=http([{}])
   with self.assertRaises(ValueError):protocol.prerequisites(sample)
 def test_http_duplicate_framing_length_and_nonfinite_refuse(self):
  cases=[b'HTTP/1.0 200 OK\r\nContent-Length: 3\r\n\r\n[]',b'HTTP/1.0 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n[]',
   b'HTTP/1.0 200 OK\r\nX: a\r\nX: b\r\n\r\n[]',b'HTTP/1.0 200 OK\r\n\r\n{"x":1,"x":2}',b'HTTP/1.0 200 OK\r\n\r\nNaN']
  for raw in cases:
   with self.assertRaises(ValueError):protocol.http_json(raw)
 def test_identity_signal_clock_and_fault_evidence_refuse(self):
  for field,value in [('daemonLogDrainComplete',b'no'),('preCrashStat',process_stat(pid=43)),('preCrashStat',process_stat(birth=124)),('preCrashStat',process_stat(cpu=0)),
   ('signal',b'0'),('waitStatus',b'0'),('wallNs',b'55000000001'),('postFaultBytes',b'1'),('readinessProbes',b'201')]:
   sample=events();sample[field]=value
   with self.assertRaises(ValueError):protocol.parse_console(console(sample))
 def test_duplicate_or_missing_events_refuse(self):
  raw=console(events())
  with self.assertRaises(ValueError):protocol.parse_console(raw+raw.splitlines()[0]+'\n')
  sample=events();del sample['launchedStat']
  with self.assertRaises(KeyError):protocol.parse_console(console(sample))
 def fixture(self,root):
  state=root/'state';state.mkdir(mode=0o700);assets=root/'assets';assets.mkdir(mode=0o700)
  p=assets/'engine-shell-approval-request-v8.json';probe.write(p,{'assets':[]});psha=probe.sha(p)
  probe.write(state/'owner-engine-shell-probe-v8-decision.json',{'scope':probe.SCOPE,'decision':'admitted','proposalSha256':psha,
   'issuedAtUnixNs':time.time_ns()-1000000000,'expiresAtUnixNs':time.time_ns()+60000000000})
  dsha=probe.sha(state/'owner-engine-shell-probe-v8-decision.json');probe.write(state/'owner-engine-shell-probe-v8-pins.json',
   {'version':'agent-braid-owned-engine-shell-pins-v2','approvals':[{'scope':probe.SCOPE,'proposalSha256':psha,'decisionSha256':dsha}]})
  return state,assets,psha
 def fake_run(self,sample,interrupt=False):
  with tempfile.TemporaryDirectory() as tmp:
   state,assets,psha=self.fixture(Path(tmp).resolve());real_popen=subprocess.Popen
   vm={'version':'agent-braid-owned-engine-shell-vm-probe-v2','status':'stopped','enginePreflightValidated':True,'guestCompletionSeen':True,
    'vmCreated':True,'vmStarted':True,'vmStopped':True,'cleanupConfirmed':True,'consoleBudgetExceeded':False,'guestCpus':1,
    'guestMemoryBytes':4294967296,'networkDevices':0,'sharedDirectories':0,'checkpointExposed':False,'forecastCalls':0,
    'daemonState':'not-inspected','executionAuthorization':False,'wallNs':100,'consoleBytes':0}
   def fake(args,**kwargs):
    path=Path(args[1])/'guest-console.txt';probe.write(path,{});path.write_text(console(sample))
    child=real_popen([sys.executable,'-c','print('+repr(json.dumps(vm))+')'],**kwargs)
    if interrupt:os.kill(os.getpid(),probe.signal.SIGTERM)
    return child
   with patch.object(probe,'ROOT',assets),patch.object(probe,'STATE',state),patch('sys.argv',['probe','--execute']),patch.object(probe.subprocess,'run'),patch.object(probe.subprocess,'Popen',side_effect=fake):code=probe.main()
   retained=json.loads((assets/('execution-'+psha[:16])/'result.json').read_bytes())
   self.assertTrue(retained['cleanupConfirmed']);self.assertTrue(retained['pinRemoved']);self.assertTrue(retained['claimPreserved'])
   return code,retained
 def test_fake_success_consumes_once(self):
  code,result=self.fake_run(events());self.assertEqual(0,code);self.assertTrue(result['qualified'])
 def test_fake_failed_fault_retains_physical_cleanup(self):
  sample=events();sample['signal']=b'0';code,result=self.fake_run(sample);self.assertEqual(2,code);self.assertFalse(result['qualified'])
 def test_fake_interrupt_is_durable(self):
  code,result=self.fake_run(events(),True);self.assertEqual(2,code);self.assertEqual(probe.signal.SIGTERM,result['interruptedSignal'])
 def test_absent_pin_does_not_create_vm(self):
  with tempfile.TemporaryDirectory() as tmp:
   state,assets,_=self.fixture(Path(tmp).resolve());(state/'owner-engine-shell-probe-v8-pins.json').unlink()
   probe.write(state/'owner-engine-shell-probe-v8-pins.json',{'version':'agent-braid-owned-engine-shell-pins-v2','approvals':[]})
   with patch.object(probe,'ROOT',assets),patch.object(probe,'STATE',state),patch('sys.argv',['probe','--execute']),patch.object(probe.subprocess,'Popen') as child:
    with self.assertRaisesRegex(ValueError,'owner-pin-absent'):probe.main()
    child.assert_not_called()

 def test_daemon_log_summary_parses_tail_count_value_and_truncation(self):
  guest=(ROOT/'guest_engine_probe.sh').read_text()
  function=guest.split('fc2_log_summary() {\n',1)[1].split('\n}\n',1)[0]
  script='fc2_log_summary() {\n'+function+'\n}\nfc2_log_summary "$1" "$2" || exit 2; printf "%s %s %s\n" "$fc2_log_bytes" "$fc2_log_tail_bytes" "$fc2_log_truncated"'
  with tempfile.TemporaryDirectory() as tmp:
   counter=Path(tmp)/'counter'
   counter.write_text('0\n')
   small=subprocess.run(['/bin/bash','-c',script,'summary', '243',str(counter)],capture_output=True,text=True)
   self.assertEqual(0,small.returncode,small.stderr);self.assertEqual('243 0 no\n',small.stdout)
   counter.write_text('7232\n')
   large=subprocess.run(['/bin/bash','-c',script,'summary','32768',str(counter)],capture_output=True,text=True)
   self.assertEqual(0,large.returncode,large.stderr);self.assertEqual('40000 7232 yes\n',large.stdout)
   counter.write_text('invalid\n')
   bad=subprocess.run(['/bin/bash','-c',script,'summary','1',str(counter)],capture_output=True,text=True)
   self.assertNotEqual(0,bad.returncode)
 def test_persistent_daemon_log_write_is_hard_bounded_and_fifo_drains_while_writer_stays_open(self):
  import threading
  guest=(ROOT/'guest_engine_probe.sh').read_text()
  function=guest.split('fc2_drain_daemon_output() {\n',1)[1].split('\n}\n',1)[0].replace('/usr/bin/dd','/bin/dd')
  with tempfile.TemporaryDirectory() as tmp:
   fifo=Path(tmp)/'daemon.fifo';log=Path(tmp)/'daemon.log';tail=Path(tmp)/'tail.count';os.mkfifo(fifo)
   script='fc2_drain_daemon_output() {\n'+function+'\n}\nexec 3< "$1"; fc2_drain_daemon_output 3 "$2" "$3"'
   proc=subprocess.Popen(['/bin/bash','-c',script,'bounded-fifo',str(fifo),str(log),str(tail)])
   def writer():
    with fifo.open('wb',buffering=0) as stream:
     stream.write(b'x'*40000)
     time.sleep(3.2)
     stream.write(b'y'*1000000)
   thread=threading.Thread(target=writer);thread.start()
   time.sleep(3.05)
   self.assertTrue(proc.poll() is None,'drainer exited while live FIFO writer remained open')
   self.assertEqual(32768,log.stat().st_size)
   thread.join(timeout=2);self.assertFalse(thread.is_alive(),'live FIFO writer blocked because excess output was not drained')
   self.assertEqual(0,proc.wait(timeout=2))
   self.assertEqual(b'1007232',tail.read_bytes().strip())
 def test_incomplete_daemon_startup_retains_only_bounded_diagnostics(self):
  guest=(ROOT/'guest_engine_probe.sh').read_text()
  self.assertIn('fc2_diagnostics=/mnt/fc2-engine/diagnostics',guest)
  self.assertIn('fc2_daemon_log=$fc2_diagnostics/daemon.log',guest)
  self.assertIn('/usr/bin/dd iflag=fullblock bs=32768 count=1 status=none > "$fc2_path"',guest)
  self.assertIn('/usr/bin/wc -c > "$fc2_tail_path"',guest)
  self.assertIn('IFS= read -r fc2_log_tail_bytes',guest)
  self.assertNotIn('/usr/bin/timeout -k1 2 /usr/bin/wc',guest)
  self.assertIn('fc2_j<20',guest)
  self.assertIn('--validate --config-file="$fc2_base/daemon.json"',guest)
  self.assertIn('"userland-proxy":false',guest)
  self.assertIn('export PATH=/usr/bin:/usr/sbin:/bin:/sbin',guest)
  self.assertIn('fc2_emit runtimeSearchPath',guest)
  self.assertIn('fc2_emit runtimeShimSearchPath',guest)
  self.assertIn('/usr/bin/containerd-shim-runc-v2',guest)
  pins=json.loads((ROOT/'guest-binary-pins.json').read_text())
  self.assertEqual('709fa03b8b731c50ce3241247a4945b49c14e3ef0d8584c0159daf291fcb151f',pins['/usr/bin/containerd-shim-runc-v2'])
  self.assertIn('/usr/bin/mkfifo -m600 "$fc2_log_fifo"',guest)
  self.assertIn('( exec /usr/bin/dockerd',guest)
  self.assertLess(guest.index('fc2_exec_ready != 1'),guest.index('fc2_ready=0'))
  detail=b'dockerd exited before socket creation'
  sample={'daemonLogAvailable':b'yes','daemonLogBytes':str(len(detail)).encode(),
   'daemonLogTruncated':b'no','daemonLogBase64':detail,'daemonLogDrainComplete':b'yes','daemonConfigValidated':b'yes',
   'daemonExecIdentity':b'no','readinessProbes':b'2','signal':b'0','waitStatus':b'0','status':b'incomplete'}
  with tempfile.TemporaryDirectory() as tmp:
   console_path=Path(tmp)/'console';console_path.write_text(console(sample))
   console_path.chmod(0o600)
   parsed=probe.guest_receipt(console_path)
  self.assertTrue(parsed['diagnosticOnly']);self.assertFalse(parsed['engineReady'])
  self.assertFalse(parsed['ownedDaemonCrash']);self.assertFalse(parsed['executionAuthorization'])
  self.assertEqual(detail.decode(),parsed['daemonLogText']);self.assertEqual(2,parsed['readinessProbes'])

 def test_synthetic_launcher_failure_is_retained_without_qualification(self):
  detail=b'dockerd exited before socket creation'
  sample={'daemonLogAvailable':b'yes','daemonLogBytes':str(len(detail)).encode(),
   'daemonLogTruncated':b'no','daemonLogBase64':detail,'daemonLogDrainComplete':b'yes','daemonConfigValidated':b'yes',
   'daemonExecIdentity':b'no','readinessProbes':b'2','signal':b'0','waitStatus':b'0','status':b'incomplete'}
  code,result=self.fake_run(sample)
  self.assertEqual(2,code);self.assertFalse(result['qualified']);self.assertTrue(result['cleanupConfirmed'])
  self.assertTrue(result['guestResult']['diagnosticOnly']);self.assertFalse(result['guestResult']['executionAuthorization'])
  self.assertIn('socket creation',result['guestResult']['daemonLogText'])

 def test_daemon_diagnostic_truncation_is_explicit_and_bounded(self):
  detail=b'x'*40000
  sample={'daemonLogAvailable':b'yes','daemonLogBytes':b'40000','daemonLogTruncated':b'yes','daemonLogDrainComplete':b'yes','daemonConfigValidated':b'yes',
   'daemonLogBase64':detail[:32768],'daemonExecIdentity':b'no',
   'readinessProbes':b'0','signal':b'0','waitStatus':b'0','status':b'incomplete'}
  with tempfile.TemporaryDirectory() as tmp:
   console_path=Path(tmp)/'console';console_path.write_text(console(sample));console_path.chmod(0o600)
   parsed=probe.guest_receipt(console_path)
  self.assertEqual(40000,parsed['daemonLogBytes']);self.assertTrue(parsed['daemonLogTruncated'])
  self.assertEqual(32768,len(base64.b64decode(parsed['daemonLogBase64'])))
 def test_rejected_preflight_cannot_reach_signal_and_exports_abort_event(self):
  guest=(ROOT/'guest_engine_probe.sh').read_text()
  function=guest.split('# BEGIN PURE ADMISSION CHECK\n')[1].split('# END PURE ADMISSION CHECK')[0]
  script='set -e; fc2_emit() { printf "%s %s\\n" "$1" "$2"; }; '+function+'\nfc2_require_crash_admission "$1"; printf SIGNAL'
  for token,code,output in [('FC2_ABORT_OWN_DAEMON_CRASH',2,'hostPreflightRejected yes\n'),
                            ('unknown',1,''),('FC2_ADMIT_OWN_DAEMON_CRASH',0,'SIGNAL')]:
   result=subprocess.run(['/bin/bash','-c',script,'admission-test',token],capture_output=True,text=True)
   self.assertEqual((code,output),(result.returncode,result.stdout))

 def test_native_rejection_sends_abort_and_waits_for_guest_diagnostic(self):
  # The host schedules bounded physical stop only after sending a rejection.
  source=(ROOT/'main.swift.in').read_text()
  rejected=source.split('preflightRejected.setEventHandler {')[1].split('}; preflightRejected.resume()')[0]
  self.assertIn('FC2_ABORT_OWN_DAEMON_CRASH',rejected)
  self.assertIn('.now() + 5',rejected)
  self.assertNotIn('FC2_ADMIT_OWN_DAEMON_CRASH',rejected)

 def test_http_transport_does_not_half_close_on_request_stdin_eof(self):
  # This checks the pinned guest command, not Linux socat runtime behavior.
  guest=(ROOT/'guest_engine_probe.sh').read_text()
  api=guest.split('fc2_api() {')[1].split('\n}',1)[0]
  self.assertIn('STDIO,ignoreeof',api)
  self.assertIn('/usr/bin/timeout -k1 1',api)
  self.assertIn('/usr/bin/head -c1048577',api)

if __name__=='__main__':unittest.main()
