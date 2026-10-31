# SPDX-License-Identifier: AGPL-3.0-only
"""Private external bootstrap escrow; never starts a manager or issues a grant.

The external supervisor must reserve BEFORE creating the operator. Importing its
receipt later is allowed only through an independently supplied root authority,
never from a client's self-declared approval. Callbacks are integration points,
not native accreditation. The immutable readiness gate remains mandatory.
"""
from copy import deepcopy
import hashlib
import json
import time
import os
import sys

from .forecast_data import digest, integer, pin, require

ROLES=('supervisor','anchor','operator')


def execution_targets(profile):
    """Work/actor scopes only; supervisor and watchdog survive cancellation."""
    stem='fc1'+profile.identity
    return ['/'+stem+'.slice/'+stem+'-root.slice/'+stem+'-operator.service',
            '/'+stem+'.slice/'+stem+'-workers.slice']


def bootstrap_ready(profile):
    """Both immutable gates precede native providers, authority IPC and starts."""
    manifest=profile.manifest()
    require(manifest.get('execAdmissionEnforced') is True and
            manifest.get('bootstrapSupervisionAccepted') is True,
            'bootstrap-native-readiness-pending')


def watchdog_observation(plan,value,*,admitted_ns,now_ns,armed_ns=None):
    """Check a qualified root provider's readback; data alone is not authority.

    RuntimeMaxSec is relative to unit activation, never this absolute watchdog.
    Its independent implementation/issuer death handling remain native gates.
    """
    contract=plan['supervision']
    require(type(value) is dict and set(value)==set(contract)|
            {'armedAtNs','observedAtNs','running','planDigest'},'bootstrap-watchdog-fields')
    require(all(value[k]==v and type(value[k]) is type(v) for k,v in contract.items()) and
            value['running'] is True and value['planDigest']==digest(plan),
            'bootstrap-absolute-watchdog-required')
    integer(value['armedAtNs'],plan['originNs'],admitted_ns)
    integer(value['observedAtNs'],admitted_ns,now_ns)
    require(now_ns<min(plan['phaseDeadlineNs'],contract['cancelAtNs']) and
            (armed_ns is None or value['armedAtNs']==armed_ns),'bootstrap-watchdog-late-or-rearmed')


def bootstrap_plan(profile,origin_ns,nonce):
    """Freeze exact unit definitions, clock and authority challenge as data only."""
    integer(origin_ns,1);pin(nonce)
    units=profile.units(remaining_seconds=sum(p.wall_seconds for p in profile.limits))
    require(type(units) is dict and 0<len(units)<=32,'bootstrap-unit-roster')
    pins={}
    for name,value in units.items():
        require(type(name) is str and type(value) is str and len(value.encode())<=65536,
                'bootstrap-unit-size-type')
        pins[name]=hashlib.sha256(value.encode()).hexdigest()
    stem='fc1'+profile.identity
    roles={'supervisor':stem+'-supervisor.service','anchor':stem+'.service',
           'operator':stem+'-operator.service'}
    require(all(name in pins for name in roles.values()),'bootstrap-units-missing')
    deadline=origin_ns+sum(p.wall_seconds for p in profile.limits)*10**9
    return {'version':'fc1-external-bootstrap-v3','profileIdentity':profile.identity,
            'originNs':origin_ns,'phaseDeadlineNs':origin_ns+profile.limits[0].wall_seconds*10**9,
            'wholeDeadlineNs':deadline,
            'supervision':{'scope':'/'+stem+'.slice','targets':execution_targets(profile),
                           'originNs':origin_ns,
                           'cancelAtNs':deadline-10**9,'closeByNs':deadline,
                           'managerIndependent':True,'issuerExitRevokes':True},
            'nonce':nonce,'unitSha256':pins,'roles':roles,
            'managerSha256':profile.manager_sha256,'operatorSha256':profile.operator_sha256,
            'operatorEntrySha256':profile.operator_entry_sha256,
            'maximumStartupEntries':3,'nativeCoverageAccepted':False,
            'executionAuthorization':False}


class ExternalBootstrapEscrow:
    """Operator-selected supervisor API, not an MCP/client-supplied backend.

    provider.authorize_start / read_loaded / observe_started are independent root
    readbacks. backend.request_start is the exact manager adapter. A future native
    qualification must prove their provenance, no hidden execs and cost boundary.
    No default backend or subprocess/systemctl fallback exists.
    """
    def __init__(self,profile,origin_ns,nonce,*,provider,backend,clock=time.monotonic_ns):
        self.profile=profile;self.plan=bootstrap_plan(profile,origin_ns,nonce)
        self.plan_digest=digest(self.plan);self.provider=provider;self.backend=backend;self.clock=clock
        self.records=[];self.failed=False
        self.watchdog_observations=[];self.cleanup=None

    def _unchanged(self):
        require(digest(bootstrap_plan(self.profile,self.plan['originNs'],self.plan['nonce']))
                ==self.plan_digest and digest(self.plan)==self.plan_digest,'bootstrap-plan-drift')

    def reserve(self,role):
        """Pure write-ahead accounting; not authority to launch the reserved unit."""
        try:
            self._unchanged();now=self.clock()
            require(not self.failed and len(self.records)<len(ROLES) and role==ROLES[len(self.records)],
                    'bootstrap-role-order-or-retry')
            require(all(r['state']=='independently-observed' for r in self.records),
                    'bootstrap-prior-start-unconfirmed')
            require(self.plan['originNs']<=now<self.plan['phaseDeadlineNs'],'bootstrap-deadline')
            # These consume existing ordinary prepare exec slots, not extra quota.
            require(2*self.profile.limits[0].requests+3>=len(self.records)+1,'bootstrap-prepare-cap')
            unit=self.plan['roles'][role]
            record={'reservation':len(self.records),'role':role,'unit':unit,
                    'unitSha256':self.plan['unitSha256'][unit],'admittedAtNs':now,
                    'attempted':True,'admitted':False,'launched':False,'pid':None,
                    'processStartTicks':None,
                    'observedAtNs':None,'job':None,'state':'reserved'}
            self.records.append(record)
            return deepcopy(record)
        except BaseException:
            self.failed=True;raise

    def dispatch(self,role):
        # Current real profile is always false: no callback/native action happens.
        bootstrap_ready(self.profile)
        RootBootstrapAuthority.guard()
        record=slot=None
        try:
            record=self.reserve(role);slot=self.records[record['reservation']]
            require(self.provider.authorize_start(deepcopy(self.plan),deepcopy(record)) is True,
                    'bootstrap-external-authority-required')
            loaded=self.provider.read_loaded(deepcopy(self.plan),record['unit'])
            require(loaded=={'profileIdentity':self.profile.identity,
                            'managerSha256':self.profile.manager_sha256,
                            'unit':record['unit'],'unitSha256':record['unitSha256'],
                            'absoluteDeadlineNs':self.plan['wholeDeadlineNs']},
                    'bootstrap-loaded-definition')
            self._watchdog(record)
            require(self.clock()<self.plan['phaseDeadlineNs'],'bootstrap-deadline')
            slot.update(admitted=True,state='dispatch-indeterminate')
            job=self.backend.request_start(record['unit'],deepcopy(slot),self.plan['phaseDeadlineNs'])
            require(type(job) is str and 0<len(job)<=128,'bootstrap-job-identity')
            slot['job']=job
            observed=self.provider.observe_started(deepcopy(self.plan),deepcopy(slot))
            require(type(observed) is dict and set(observed)=={'pid','processStartTicks','observedAtNs','unitSha256','unaccountedExecs'},
                    'bootstrap-observation-fields')
            integer(observed['pid'],1);integer(observed['observedAtNs'],slot['admittedAtNs'])
            integer(observed['processStartTicks'],1)
            require(observed['observedAtNs']<=self.clock()<self.plan['phaseDeadlineNs'] and
                    observed['unitSha256']==slot['unitSha256'] and
                    type(observed['unaccountedExecs']) is int and observed['unaccountedExecs']==0,
                    'bootstrap-independent-start-unverified')
            slot.update(pid=observed['pid'],observedAtNs=observed['observedAtNs'],
                        processStartTicks=observed['processStartTicks'],
                        launched=True,state='independently-observed')
            self._watchdog(record)
            return deepcopy(slot)
        except BaseException as failure:
            self.failed=True
            # Unknown launch remains an attempted/admitted consumed reservation.
            if slot is not None and slot['state']=='reserved':slot['state']='refused-consumed'
            if self.cleanup is None and any(r['admitted'] for r in self.records):
                request={'event':'revokeBootstrap','planDigest':self.plan_digest,
                         'nonce':self.plan['nonce'],'scope':self.plan['supervision']['scope'],
                         'targets':deepcopy(self.plan['supervision']['targets']),
                         'requestedAtNs':self.clock(),'closeByNs':self.plan['wholeDeadlineNs']}
                self.cleanup={'attempted':True,'confirmed':False,'request':deepcopy(request)}
                try:
                    # The qualified external watchdog must also act if a manager
                    # callback blocks. This exception path is additional only.
                    result=self.provider.cancel_and_verify_empty(deepcopy(self.plan),
                                                               deepcopy(request))
                    require(type(result) is dict and set(result)==set(request)|{'observedAtNs','populated'}
                            and all(result[k]==v and type(result[k]) is type(v) for k,v in request.items())
                            and result['populated'] is False,'bootstrap-cleanup-unconfirmed')
                    integer(result['observedAtNs'],request['requestedAtNs'],self.clock())
                    require(result['observedAtNs']<=self.clock()<self.plan['wholeDeadlineNs'],
                            'bootstrap-cleanup-outside-budget')
                    self.cleanup.update(confirmed=True,observation=deepcopy(result))
                except BaseException as error:
                    failure.add_note('Bootstrap cleanup unconfirmed: '+type(error).__name__)
            raise

    def _watchdog(self,record):
        value=self.provider.read_watchdog(deepcopy(self.plan))
        armed=self.watchdog_observations[0]['armedAtNs'] if self.watchdog_observations else None
        watchdog_observation(self.plan,value,admitted_ns=record['admittedAtNs'],
                             now_ns=self.clock(),armed_ns=armed)
        self.watchdog_observations.append(deepcopy(value))

    def receipt(self):
        self._unchanged()
        return {'plan':deepcopy(self.plan),'planDigest':self.plan_digest,
                'records':deepcopy(self.records),'failed':self.failed,
                'watchdogObservations':deepcopy(self.watchdog_observations),'cleanup':deepcopy(self.cleanup),
                'nativeCoverageAccepted':False,'executionAuthorization':False}


class RootBootstrapAuthority:
    """Private root-only channel to the separately owned pre-start escrow issuer.

    Caller is the trusted root supervisor, never worker JSON/MCP. Peer PID and ELF
    SHA are external operator pins. Kernel/source/entry provenance still needs
    native accreditation; a root callback or receipt hash cannot provide it.
    """
    @staticmethod
    def guard():
        require(sys.platform=='linux' and os.geteuid()==0,'bootstrap-root-only')

    def __init__(self,profile,channel,*,issuer_pid,issuer_sha256,expected_plan_digest,view):
        bootstrap_ready(profile)
        self.guard();integer(issuer_pid,1);pin(issuer_sha256);pin(expected_plan_digest)
        from .forecast_operator_bridge import peer
        peer(channel,uid=0,pid=issuer_pid)
        view.guard();start=view.state(issuer_pid)['start'];view.executable(issuer_pid,issuer_sha256)
        require(view.state(issuer_pid)['start']==start,'bootstrap-issuer-reused')
        self.identity=profile.identity;self.channel=channel;self.issuer_pid=issuer_pid
        self.issuer_sha256=issuer_sha256;self.expected_plan_digest=expected_plan_digest
        self.issuer_start=start
        self.view=view;self.sequence=0
        channel.settimeout(1);channel.set_inheritable(False)

    def verify_prior(self,receipt):
        self.guard()
        from .forecast_operator_bridge import peer,send,receive
        peer(self.channel,uid=0,pid=self.issuer_pid)
        require(self.view.state(self.issuer_pid)['start']==self.issuer_start,'bootstrap-issuer-reused')
        self.view.executable(self.issuer_pid,self.issuer_sha256)
        deadline=receipt['plan']['phaseDeadlineNs'];remaining=(deadline-time.monotonic_ns())/10**9
        require(remaining>0,'bootstrap-deadline');self.channel.settimeout(min(1,remaining))
        self.sequence+=1
        request={'event':'verifyPriorBootstrap','profileIdentity':self.identity,
                 'sequence':self.sequence,'planDigest':self.expected_plan_digest,
                 'receiptDigest':digest(receipt)}
        send(self.channel,request)
        reply=receive(self.channel)
        require(time.monotonic_ns()<deadline and self.view.state(self.issuer_pid)['start']==self.issuer_start,
                'bootstrap-issuer-stale-or-late')
        self.view.account(len(json.dumps(request).encode())+
                          len(json.dumps(reply).encode()))
        # The issuer must compare its own retained PRE-start escrow; a producer
        # report/current PID lookup is not an implementation of this contract.
        return reply=={**request,'priorEscrowVerified':True}


class EscrowAuthorityServer:
    """One private root verification of the issuer's own retained start history.

    No caller may provide its own receipt, authority callback or allowed peer PID.
    This server is not started here. Its native packaging, source/entry identity,
    manager adapter, absolute watchdog and costs still need accreditation.
    """
    def __init__(self,escrow,*,view):
        bootstrap_ready(escrow.profile)
        RootBootstrapAuthority.guard()
        require(not escrow.failed and len(escrow.records)==len(ROLES) and
                all(r['state']=='independently-observed' for r in escrow.records),
                'bootstrap-issuer-history-incomplete')
        self.escrow=escrow;self.view=view;self.retained=escrow.receipt();self.used=False

    def serve_once(self,channel):
        RootBootstrapAuthority.guard()
        from .forecast_operator_bridge import peer,send,receive
        try:
            require(not self.used and not self.escrow.failed and self.escrow.receipt()==self.retained,
                    'bootstrap-issuer-replay-or-drift')
            self.used=True
            deadline=self.retained['plan']['phaseDeadlineNs']
            remaining=(deadline-time.monotonic_ns())/10**9
            require(remaining>0,'bootstrap-deadline');channel.settimeout(min(1,remaining))
            peer(channel,uid=0,pid=self.retained['records'][-1]['pid'])
            self.view.guard()
            for row in self.retained['records']:
                state=self.view.state(row['pid'])
                require(state['start']==row['processStartTicks'] and state['state']!='Z',
                        'bootstrap-start-no-longer-live')
            self.view.executable(self.retained['records'][-1]['pid'],self.escrow.profile.operator_sha256)
            request=receive(channel)
            expected={'event':'verifyPriorBootstrap','profileIdentity':self.escrow.profile.identity,
                      'sequence':1,'planDigest':self.escrow.plan_digest,'receiptDigest':digest(self.retained)}
            require(request==expected and time.monotonic_ns()<deadline,'bootstrap-issuer-request')
            reply={**expected,'priorEscrowVerified':True}
            self.view.account(len(json.dumps(request).encode())+len(json.dumps(reply).encode()))
            send(channel,reply)
            return {'retainedHistoryMatched':True,'nativeCoverageAccepted':False}
        except BaseException:
            self.escrow.failed=True;channel.close();raise


def adopt_bootstrap(profile,ledger,receipt,*,authority,now_ns):
    """Import prior externally authenticated permits before the actor owns ledger.

    authority verifies the external supervisor's retained PRE-start escrow
    through its private root-only authority/channel. Comparing hashes or reading current PIDs
    alone cannot prove prior permission. A worker/model cannot select this verifier.
    Native accreditation and actual manager/provider binaries remain separate gates.
    """
    bootstrap_ready(profile)
    RootBootstrapAuthority.guard()
    try:
        require(type(authority) is RootBootstrapAuthority and authority.identity==profile.identity,
                'bootstrap-root-authority-required')
        expected_plan_digest=authority.expected_plan_digest
        pin(expected_plan_digest)
        require(type(receipt) is dict and set(receipt)=={'plan','planDigest','records','failed',
                'nativeCoverageAccepted','executionAuthorization','watchdogObservations','cleanup'},'bootstrap-receipt-fields')
        plan=receipt['plan']
        require(type(plan) is dict and receipt['planDigest']==expected_plan_digest==digest(plan),
                'bootstrap-receipt-binding')
        require(plan==bootstrap_plan(profile,ledger.origin_ns,plan['nonce']) and
                receipt['failed'] is False and ledger.identity==profile.identity and
                receipt['nativeCoverageAccepted'] is False and receipt['executionAuthorization'] is False and
                ledger.phase==-1 and not ledger.records and not ledger._broker_attached,
                'bootstrap-actor-origin-state')
        require(authority.verify_prior(deepcopy(receipt)) is True,
                'bootstrap-prior-escrow-unverified')
        rows=receipt['records'];require(type(rows) is list and len(rows)==len(ROLES),'bootstrap-entry-roster')
        observations=receipt['watchdogObservations']
        require(receipt['cleanup'] is None and type(observations) is list and len(observations)==2*len(ROLES),
                'bootstrap-watchdog-roster')
        armed=None
        for index,value in enumerate(observations):
            watchdog_observation(plan,value,admitted_ns=rows[index//2]['admittedAtNs'],
                                 now_ns=now_ns,armed_ns=armed)
            armed=value['armedAtNs']
        # Validate every row before mutating the actor's ledger.
        fields={'reservation','role','unit','unitSha256','admittedAtNs','attempted','admitted','processStartTicks',
                'launched','pid','observedAtNs','job','state'}
        previous=ledger.origin_ns
        for index,row in enumerate(rows):
            require(type(row) is dict and set(row)==fields and type(row['reservation']) is int
                    and row['reservation']==index and row['role']==ROLES[index], 'bootstrap-entry-fields')
            unit=plan['roles'][row['role']]
            integer(row['pid'],1);integer(row['admittedAtNs'],previous);integer(row['observedAtNs'],row['admittedAtNs'])
            integer(row['processStartTicks'],1)
            require(row['unit']==unit and row['unitSha256']==plan['unitSha256'][unit]
                    and all(row[k] is True for k in ('attempted','admitted','launched'))
                    and row['state']=='independently-observed' and type(row['job']) is str
                    and 0<len(row['job'])<=128 and row['observedAtNs']<=now_ns<plan['phaseDeadlineNs'],
                    'bootstrap-entry-unverified')
            previous=row['observedAtNs']
        require(len({row['pid'] for row in rows})==len(ROLES),'bootstrap-distinct-processes')
        ledger.enter(0,plan['phaseDeadlineNs'],now_ns=now_ns)
        for row in rows:
            token=ledger.reserve('external-bootstrap',row['reservation'],row['pid'],
                                 now_ns=row['admittedAtNs'])
            ledger.finish(token,continued=True)
        return {'planDigest':expected_plan_digest,'startupEntriesConsumed':len(rows),
                'chargedPhaseIndex':0,'additionalExecAllowance':0,'nativeCoverageAccepted':False}
    except BaseException:
        ledger.failed=True;raise


def offline_bootstrap_v4(preparation, origin_ns, graph_digest, *, unit_sha256):
    """Data-only v4 binding; no adoption of v3 permits or provider invocation.

    Startup pairs belong exclusively to manager escrow. The owner entry consumes
    one additional escrow slot. These are accounting intentions, not start proof.
    """
    from .forecast_v9_driver import DriverPreparation
    require(type(preparation) is DriverPreparation, 'bootstrap-v4-preparation-type')
    integer(origin_ns, 1); pin(graph_digest)
    allocation = preparation.binding.allocation
    stem = 'fc1'+preparation.profile_identity
    names = {preparation.binding.unit(i) for i in range(6)} | {
        stem+'.slice', stem+'-root.slice', stem+'-workers.slice'}
    require(type(unit_sha256) is dict and set(unit_sha256) == names,
            'bootstrap-v4-unit-roster')
    for value in unit_sha256.values(): pin(value)
    return {'version': 'fc1-external-bootstrap-v4',
            'preparationIdentity': preparation.identity,
            'profileIdentity': preparation.profile_identity, 'graphDigest': graph_digest,
            'unitSha256': dict(unit_sha256),
            'nonce': preparation.nonce, 'originNs': origin_ns,
            'phaseDeadlineNs': origin_ns + allocation.seconds[0]*10**9,
            'wholeDeadlineNs': origin_ns + sum(allocation.seconds)*10**9,
            'startupRoles': list(ROLES), 'startupAccountingOwner': 'escrow',
            'startupExecAttempts': 7, 'brokerStartupExecAttempts': 0,
            'startupScope': 'external-owner-through-operator-before-prepare',
            'phaseZeroWorkerRoles': ['prepare'], 'phaseZeroWorkerExecAttempts': 2,
            'phaseZeroEscrowExecAttempts': 9,
            'nativeCoverageAccepted': False, 'executionAuthorization': False}
