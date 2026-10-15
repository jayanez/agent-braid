# SPDX-License-Identifier: AGPL-3.0-only
"""Strict host interpretation of bounded observations from the pinned guest."""
import base64,hashlib,json
ROOT='/mnt/fc2-engine/docker'
CONFIG=b'{"bridge":"none","ip-forward":false,"ip-masq":false,"ip6tables":false,"iptables":false,"live-restore":false,"log-level":"error","userland-proxy":false}\n'

def unique(pairs):
 result={}
 for key,value in pairs:
  if key in result:raise ValueError('duplicate-json-key')
  result[key]=value
 return result

def http_json(raw):
 if len(raw)>1048576:raise ValueError('http-budget')
 head,separator,body=raw.partition(b'\r\n\r\n')
 if not separator:raise ValueError('http-framing')
 lines=head.split(b'\r\n')
 if lines[0] not in (b'HTTP/1.0 200 OK',b'HTTP/1.1 200 OK'):raise ValueError('http-status')
 headers={}
 for line in lines[1:]:
  key,colon,value=line.partition(b':');key=key.strip().lower()
  if not colon or key in headers:raise ValueError('http-headers')
  headers[key]=value.strip()
 if b'transfer-encoding' in headers:raise ValueError('unsupported-http-transfer')
 if b'content-length' in headers and int(headers[b'content-length'])!=len(body):raise ValueError('http-length')
 return json.loads(body,object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('non-finite-json')))

def prerequisites(events):
 if events.get('daemonExecIdentity')!=b'yes':raise ValueError('daemon-executable-identity')
 if events.get('prerequisiteReady')!=b'yes':raise ValueError('prerequisite-marker')
 if events.get('runtimeSearchPath')!=b'/usr/bin/runc':raise ValueError('runc-search-path')
 if events.get('runtimeShimSearchPath')!=b'/usr/bin/containerd-shim-runc-v2':raise ValueError('runtime-shim-search-path')
 info=http_json(events['infoHttp'])
 if (not isinstance(info,dict) or info.get('DockerRootDir')!=ROOT or type(info.get('ID')) is not str or not info['ID']
     or info.get('LiveRestoreEnabled') is not False or type(info.get('Containers')) is not int or info['Containers']!=0):raise ValueError('engine-info')
 if http_json(events['imagesHttp'])!=[] or http_json(events['containersHttp'])!=[]:raise ValueError('engine-not-empty')
 return info

def identity(raw):
 text=raw.decode('ascii');pid,sep,rest=text.partition(' (');_,sep2,tail=rest.rpartition(') ')
 if not sep or not sep2:raise ValueError('stat-framing')
 fields=tail.split()
 if len(fields)<20 or fields[0]=='Z':raise ValueError('stat-dead-or-short')
 value={'pid':int(pid),'birthTicks':int(fields[19]),'cpuTicks':int(fields[11])+int(fields[12]),'scope':'daemon-process-only-before-crash'}
 if value['pid']<=1 or value['birthTicks']<1 or value['cpuTicks']<0:raise ValueError('stat-values')
 return value

def parse_events(text):
 if len(text.encode('utf-8'))>1048576:raise ValueError('console-budget')
 events={}
 for line in text.splitlines():
  if not line.startswith('FC2_ENGINE_EVENT '):continue
  _,_,tail=line.partition('FC2_ENGINE_EVENT ');key,sep,encoded=tail.partition(' ')
  if not sep or key in events or len(events)>=32:raise ValueError('event-framing-or-duplicate')
  events[key]=base64.b64decode(encoded,validate=True)
 return events

def parse_console(text):
 events=parse_events(text)
 info=prerequisites(events);launched=identity(events['launchedStat']);before=identity(events['preCrashStat'])
 if launched['pid']!=before['pid'] or launched['birthTicks']!=before['birthTicks'] or before['cpuTicks']<launched['cpuTicks']:raise ValueError('birth-or-counter-drift')
 integers={key:int(events[key]) for key in ['signal','waitStatus','readinessProbes','wallNs','clockTicksPerSecond','postFaultClientStatus','postFaultBytes']}
 if (events['status']!=b'engine-ready-and-owned-daemon-crashed' or integers['signal']!=1 or integers['waitStatus']!=137
  or not 1<=integers['readinessProbes']<=200 or not 0<=integers['wallNs']<=55000000000
  or integers['clockTicksPerSecond']<=0 or integers['postFaultClientStatus']<=0 or integers['postFaultBytes']!=0):raise ValueError('engine-outcome')
 if events['configurationSha256'].decode()!=hashlib.sha256(CONFIG).hexdigest():raise ValueError('config-drift')
 if events.get('daemonLogDrainComplete')!=b'yes':raise ValueError('daemon-log-drain-incomplete')
 if events.get('daemonConfigValidated')!=b'yes':raise ValueError('daemon-config-validation-missing')
 return {'version':'agent-braid-owned-engine-shell-qualification-v2','status':'engine-ready-and-owned-daemon-crashed',
  'engineReady':True,'ownedDaemonCrash':True,'daemonSignalSent':True,'shellWaitStatus':137,'imagesCreated':0,
  'imagesObserved':0,'containersCreated':0,'containersObserved':0,'forecastCalls':0,'workerConformanceAccepted':False,
  'fullDeploymentCostAccepted':False,'executionAuthorization':False,'namespace':'fc2-engine-qualification','dataRoot':ROOT,
  'socket':'/run/fc2-engine/docker.sock','cleanupConfirmed':False,'launchedIdentity':launched,'preCrashIdentity':before,
  'wallNs':integers['wallNs'],'readinessProbes':integers['readinessProbes'],'clockTicksPerSecond':integers['clockTicksPerSecond'],
  'engineId':info['ID'],'serverVersion':info.get('ServerVersion'),'bootId':events['bootId'].decode().strip(),
  'cgroupControllers':events['cgroupControllers'].decode().split(),'configurationSha256':events['configurationSha256'].decode(),
  'costGaps':['daemon-final-ticks-after-crash','containerd-cpu','VM-host-cpu-and-memory','final-export','no-model-or-worker-in-this-diagnostic']}
