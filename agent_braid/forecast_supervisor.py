# SPDX-License-Identifier: AGPL-3.0-only
"""Private ephemeral-supervisor cancellation; no action on import or construction.

The watchdog runs in its own unit outside both execution targets. Its own root
slice still shares the fixed 512 MiB/16-task aggregate with operator and broker.
Native methods require the independently accepted profile; no caller JSON grants
that authority. An outer owner guard must cover the supervisor/watchdog startup.
"""
import os
from pathlib import Path
import select
import time

from .forecast_bootstrap import bootstrap_ready, bootstrap_plan, execution_targets
from .forecast_data import digest, integer, require
from .forecast_native import KernelView, mount_rows
from .forecast_operator_bridge import peer, receive

MIB=1024**2
READ_PARTITIONS={'operator':512*MIB,'supervisor':256*MIB,'anchor':256*MIB,'broker':1024*MIB}


class ExecutionScope:
    """Retain no-follow cgroup capabilities before release of any worker.

    Opening is explicit. Independent native qualification must additionally bind
    manager unit/cgroup identities and this entry/source to the operator permit.
    """
    def __init__(self,profile,*,origin_ns,nonce,view=None):
        self.origin_ns=integer(origin_ns,1);self.nonce=nonce
        self.plan=bootstrap_plan(profile,origin_ns,nonce);self.plan_digest=digest(self.plan)
        self.profile=profile;self.view=KernelView() if view is None else view
        self.targets=execution_targets(profile);self.handles=[];self.closed=False
        self.failed=False;self.revoked=False

    def verify_plan(self,plan):
        require(plan==self.plan and digest(plan)==self.plan_digest and
                plan==bootstrap_plan(self.profile,self.origin_ns,self.nonce),
                "supervisor-plan-drift")

    def open(self):
        bootstrap_ready(self.profile);self.verify_plan(self.plan);self.view.guard()
        require(not self.handles and not self.closed,'supervisor-scope-already-open')
        remaining=max(0,READ_PARTITIONS['anchor']-self.view.bytes_read)
        self.view.remaining=remaining if self.view.remaining is None else min(remaining,self.view.remaining)
        mount=mount_rows(self.view.read('/proc/self/mountinfo')).get('/sys/fs/cgroup')
        require(mount is not None and mount['type']=='cgroup2','supervisor-cgroup-v2')
        own=self.view.read('/proc/self/cgroup').decode().strip()
        require(own.startswith('0::/'),'supervisor-cgroup-shape')
        own=own[3:]
        require(all(own!=p and not own.startswith(p+'/') for p in self.targets),
                'supervisor-inside-cancel-target')
        try:
            for target in self.targets:
                fd=os.open('/sys/fs/cgroup',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
                kill=events=None
                try:
                    for part in Path(target).parts[1:]:
                        child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
                        os.close(fd);fd=child
                    kill=os.open('cgroup.kill',os.O_WRONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
                    events=os.open('cgroup.events',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
                    info=os.fstat(fd)
                    self.handles.append({'path':target,'directory':fd,'kill':kill,'events':events,
                                         'identity':(info.st_dev,info.st_ino)})
                except BaseException:
                    for descriptor in (events,kill,fd):
                        if descriptor is not None:os.close(descriptor)
                    raise
        except BaseException:
            self.failed=True;self.close();raise
        return self

    def snapshot(self):
        self.view.guard()
        require(not self.closed and len(self.handles)==2,'supervisor-scope-not-open')
        rows=[]
        for item in self.handles:
            info=os.fstat(item['directory'])
            require((info.st_dev,info.st_ino)==item['identity'],'supervisor-scope-replaced')
            os.lseek(item['events'],0,os.SEEK_SET);raw=os.read(item['events'],4097)
            self.view.account(len(raw));require(len(raw)<=4096,'supervisor-events-bound')
            fields=raw.decode().splitlines();values={}
            for line in fields:
                pair=line.split();require(len(pair)==2 and pair[0] not in values,'supervisor-events-shape')
                values[pair[0]]=pair[1]
            require(values.get('populated') in ('0','1'),'supervisor-populated-unknown')
            rows.append({'path':item['path'],'populated':values['populated']=='1',
                         'identity':list(item['identity'])})
        return rows

    def revoke(self,*,requested_ns,close_by_ns,clock=time.monotonic_ns):
        self.view.guard();integer(requested_ns,1);integer(close_by_ns,1)
        require(not self.revoked and not self.closed and len(self.handles)==2,'supervisor-revoke-state')
        self.verify_plan(self.plan)
        original_close=self.plan["wholeDeadlineNs"]
        requested_close=close_by_ns;close_by_ns=min(close_by_ns,original_close)
        self.revoked=True;first=None
        # A failure at one target MUST NOT skip revocation of the other target.
        for item in self.handles:
            try:
                require(os.write(item['kill'],b'1')==1,'supervisor-kill-write')
                self.view.account(1)
            except BaseException as error:
                if first is None:first=error
        if first is not None:self.failed=True;raise first
        require(requested_close<=original_close,"supervisor-deadline-extension")
        while clock()<close_by_ns:
            rows=self.snapshot();observed=clock()
            if requested_ns<=observed<close_by_ns and all(not r['populated'] for r in rows):
                return {'observedAtNs':observed,'targets':rows,'populated':False}
            select.select([],[],[],min(.01,max(0,(close_by_ns-clock())/10**9)))
        self.failed=True
        require(False,'supervisor-cleanup-outside-budget')

    def close(self):
        if self.closed:return
        self.closed=True;first=None
        for item in self.handles:
            for name in ('events','kill','directory'):
                try:os.close(item[name])
                except BaseException as error:
                    if first is None:first=error
        self.handles=[]
        if first is not None:self.failed=True;raise first


def watchdog_loop(plan,scope,channel,issuer_pidfd,*,issuer_pid,clock=time.monotonic_ns):
    """Separate watchdog unit: no manager calls, heartbeat extension or exec.

    The root issuer sends only a terminal stop request; EOF, issuer death, malformed
    traffic and expiry all revoke the same pinned targets. Tests use fake FDs only.
    Caller owns all FDs and must close them after retaining the result.
    """
    bootstrap_ready(scope.profile);scope.verify_plan(plan);scope.view.guard()
    contract=plan['supervision'];cause='expiry';request=None
    try:
        peer(channel,uid=0,pid=issuer_pid)
        while clock()<contract['cancelAtNs']:
            ready,_,_=select.select([channel,issuer_pidfd],[],[],
                min(.1,max(0,(contract['cancelAtNs']-clock())/10**9)))
            if issuer_pidfd in ready:cause='issuer-exit';break
            if channel in ready:
                channel.settimeout(min(.1,max(.000001,(contract['cancelAtNs']-clock())/10**9)))
                request=receive(channel)
                require(request=={'event':'closeControl','planDigest':digest(plan),'nonce':plan['nonce']},
                        'supervisor-watchdog-command')
                cause='terminal-request';break
    except BaseException:
        cause='authority-or-ipc-failure'
    requested=clock()
    result=scope.revoke(requested_ns=requested,close_by_ns=contract['closeByNs'],clock=clock)
    return {'planDigest':digest(plan),'nonce':plan['nonce'],'scope':contract['scope'],
            'cause':cause,'requestedAtNs':requested,'observation':result,
            'executionTargetsEmpty':True,'supervisorAndWatchdogExitVerified':False,
            'wholeFlowCleanupVerified':False,'nativeCoverageAccepted':False,'executionAuthorization':False}
