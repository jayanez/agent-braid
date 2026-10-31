# SPDX-License-Identifier: AGPL-3.0-only
"""Private v2 exec partitions. Pure accounting is never execution authority.

Escrow owns entry/executor/program attempts; the broker owns Git, descendants
and one pinned device verifier per phase. Their allowances cannot overlap.
"""
from copy import deepcopy
from dataclasses import dataclass
from threading import RLock

from .forecast_data import integer, pin, require

ESCROW = (9, 0, 0, 2, 2)
FIXED = (10, 1, 1, 3, 3)
ROLES = ('supervisor', 'anchor', 'operator', 'prepare', 'verify', 'terminal')
ROLE_PHASE = (0, 0, 0, 0, 3, 4)


@dataclass(frozen=True)
class ExecAllocation:
    profile_identity: str
    requests: tuple
    seconds: tuple

    def __post_init__(self):
        pin(self.profile_identity)
        require(type(self.requests) is tuple and type(self.seconds) is tuple and
                len(self.requests) == len(self.seconds) == 5, 'exec-v2-phase-roster')
        for n in self.requests: integer(n, 0, 65536)
        for n in self.seconds: integer(n, 1, 3600)
        require(self.requests[-1] == 0, 'exec-v2-terminal-git')
        require(self.total <= 65536, 'exec-v2-record-cap')

    @classmethod
    def from_profile(cls, profile):
        return cls(profile.identity, tuple(p.requests for p in profile.limits),
                   tuple(p.wall_seconds for p in profile.limits))

    def cap(self, owner, phase):
        integer(phase, 0, 4)
        require(owner in ('escrow', 'broker'), 'exec-v2-owner')
        return ESCROW[phase] if owner == 'escrow' else 2*self.requests[phase]+1

    @property
    def total(self):
        return 2*sum(self.requests)+sum(FIXED)

    def manifest(self):
        return {'version': 'fc1-exec-allocation-v2', 'profileIdentity': self.profile_identity,
                'escrow': list(ESCROW),
                'broker': [self.cap('broker', i) for i in range(5)],
                'phases': [2*n+fixed for n, fixed in zip(self.requests, FIXED, strict=True)],
                'total': self.total, 'nativeCoverageAccepted': False,
                'executionAuthorization': False}


class PartitionLedger:
    """One owner's disjoint quota, chosen by operator code rather than a frame.

    A reserved attempt is consumed before its syscall. Unknown outcomes fail the
    partition; unused allowance never becomes another owner's/phase's allowance.
    This object has no native methods, grants, refunds or authority callbacks.
    """
    def __init__(self, allocation, owner, origin_ns):
        require(type(allocation) is ExecAllocation and owner in ('escrow', 'broker'),
                'exec-v2-partition')
        self.allocation = allocation
        self.owner = owner
        self.origin_ns = integer(origin_ns, 1)
        self.whole_deadline = origin_ns+sum(allocation.seconds)*10**9
        self.phase = -1
        self.deadline = 0
        self.records = []
        self.keys = set()
        self.failed = False
        self.lock = RLock()

    def enter(self, phase, deadline_ns, *, now_ns):
        with self.lock:
            integer(phase, 0, 4); integer(deadline_ns, 1); integer(now_ns, self.origin_ns)
            require(not self.failed and phase == self.phase+1 and
                    now_ns < deadline_ns <= self.whole_deadline and
                    deadline_ns-now_ns <= self.allocation.seconds[phase]*10**9 and
                    not any(r['state'] == 'reserved' for r in self.records),
                    'exec-v2-transition')
            future = sum(self.allocation.seconds[phase+1:])*10**9
            require(deadline_ns <= self.whole_deadline-future, 'exec-v2-future-time-reserve')
            self.phase, self.deadline = phase, deadline_ns

    def reserve(self, key, pid, *, now_ns):
        with self.lock:
            integer(pid, 1); integer(now_ns, self.origin_ns)
            require(type(key) is str and 0 < len(key) <= 128 and not self.failed and
                    0 <= self.phase < 5 and now_ns < self.deadline,
                    'exec-v2-reservation-state')
            require((self.phase, key) not in self.keys, 'exec-v2-replay')
            rows = sum(r['phase'] == self.phase for r in self.records)
            if rows >= self.allocation.cap(self.owner, self.phase):
                self.failed = True
                require(False, 'exec-v2-partition-exhausted')
            token = len(self.records)
            self.keys.add((self.phase, key))
            self.records.append({'phase': self.phase, 'owner': self.owner, 'key': key,
                                 'pid': pid, 'admittedAtNs': now_ns, 'state': 'reserved'})
            return token

    def finish(self, token, *, continued):
        with self.lock:
            integer(token, 0, len(self.records)-1)
            require(type(continued) is bool and self.records[token]['state'] == 'reserved',
                    'exec-v2-finish')
            self.records[token]['state'] = 'continued-not-launch-proof' if continued else 'indeterminate-consumed'
            if not continued: self.failed = True

    def receipt(self):
        with self.lock:
            return {'version': 'fc1-exec-partition-v2', 'owner': self.owner,
                    'allocation': self.allocation.manifest(), 'originNs': self.origin_ns,
                    'phase': self.phase, 'failed': self.failed,
                    'records': deepcopy(self.records), 'nativeCoverageAccepted': False,
                    'executionAuthorization': False}


def module_dependency_budget(allocation, obligations):
    """Advisory subtotal illustrations only; never reserve, lend or grant quota.

    Wants edges can coalesce or recur, and conditions depend on boot/manager facts.
    Two execs/start is an explicit illustrative assumption, not a whole-flow bound.
    External modprobe binaries, install hooks and complete costs remain unqualified.
    """
    require(type(allocation) is ExecAllocation and type(obligations) is list and
            len(obligations)<=3, 'module-budget-input')
    targets=('modprobe@loop.service','modprobe@dm_mod.service','modprobe@dm_verity.service')
    stem='fc1'+allocation.profile_identity
    phases={stem+'-prepare.service':0,stem+'-verify.service':3,stem+'-terminal.service':4}
    expected={(kind,target) for kind in ('After','Wants') for target in targets}
    seen=set(); references=[]; by_phase=[0]*5
    for row in obligations:
        require(type(row) is dict and type(row.get('unit')) is str and row['unit'] in phases and row['unit'] not in seen and
                row.get('activationObserved') is False and row.get('effectiveContextVerified') is False,
                'module-budget-unverified-role-or-replay')
        edges=row.get('edges')
        require(type(edges) is list and len(edges)==6 and
                all(type(e) is dict and set(e)=={'kind','to'} and type(e['kind']) is str
                    and type(e['to']) is str for e in edges), 'module-budget-edge-fields')
        require({(e['kind'],e['to']) for e in edges}==expected,'module-budget-edge-roster')
        seen.add(row['unit']);references.extend(targets)
        by_phase[phases[row['unit']]]+=len(targets)
    distinct=sorted(set(references))
    return {'version':'fc1-offline-module-budget-obligations-v2',
            'sourceProjectionSites':len(seen),'wantsReferences':len(references),
            'distinctTargets':distinct,'observedActivations':None,
            'retainedAllocation':allocation.manifest(),
            'retainedEscrow':list(ESCROW),'brokerMayCoverTheseJobs':False,
            'outsideEscrowRoleRoster':distinct,'escrowCoverageVerified':False,
            'preExecCoverage':{
                'scope':'source inspection and protocol roster only; no native interception witness',
                'receiverNames':[stem+('.service' if role=='anchor' else '-'+role+'.service') for role in ROLES],
                'targets':[{'unit':target,'receiverNameEligible':False,
                            'site0SenderRequestsAdmission':False,'site1SenderRequestsAdmission':False,
                            'receiverWouldRejectForeignName':True,
                            'preExecRejectionObserved':False,'nativeCoverageAccepted':False}
                           for target in distinct],
                'receiverRejectionEstablishesInterception':False,
                'unitNameRecognitionEstablishesTargetBinding':False,
                'workerListenerCoversPID1SiblingServices':False,
                'ungatedFC1CgroupFence':'source rejects ungated spawn in /fc1-prefixed cgroup; actual external placement unobserved',
                'otherUnitRoute':'non-FC1 unit/cgroup can follow generic spawn/target exec; no global gate is established',
                'sourceScopeSha256':{
                    'research/native/fc1_systemd_gate.c':'e9b35021d53554cd93a521c8f4fa557c8dcf3ed8333bc9a482b5dba548d7fdfa',
                    'research/native/fc1_systemd_policy.h':'b2489b041fa39d64fa87aa26eabfcefafbcc8c9f7514ce94c9197d5338e4caae',
                    'agent_braid/forecast_systemd_patch.py':'cc276b81622d4e2079ef702bd11180d9fc5ecd325e8850b9c865edced3a5cce1',
                    'agent_braid/forecast_manager_escrow.py':'63a01202bab8d54e9ca83c8d15b6ddda93e1de956741dcd64f19975b7f0a07f9',
                    'agent_braid/forecast_launcher.py':'debfd9efaa6d5c89191681ed97b9f512fef8f9f97e5f8b0c1a46f9b330f094bc',
                    'agent_braid/forecast_exec_gate.py':'c7cecbf2fd2c2e42a02cb32e3e1e77ec3798ac3967e5f3125898c1f5b1864d7c'},
                'additionalRolesGranted':0,'additionalExecAllowanceGranted':0,
                'nativeQualification':False,'executionAuthorization':False},
            'illustrations':[
                {'assumption':'each distinct target starts once over the flow; no coalescing/restart proof',
                 'assumedStarts':len(distinct),'assumedExecAttemptsPerStart':2,
                 'subtotalExecAttempts':2*len(distinct),'isUpperBound':False},
                {'assumption':'each projected worker site starts every target once in its phase',
                 'assumedStarts':len(references),'assumedExecAttemptsPerStart':2,
                 'subtotalExecAttempts':2*len(references),
                 'extraAttemptsByPhase':[2*n for n in by_phase],'isUpperBound':False}],
            'execAttemptUpperBound':None,'wholeFlowCostUpperBound':None,
            'extraExecAllowanceGranted':0,'operationalBudgetClosed':False,
            'nativeQualification':False,'executionAuthorization':False,
            'sourceReview':{
                'commit':'3255daee1572366b74fe92f002a3d60ecbb27103',
                'sourceSha256':{
                    'units/modprobe@.service':'ac9abd099882e3c01d48786c143b2381c08a690da13984bbfa37ac1c84c8e91b',
                    'units/meson.build':'bcd236540f3628c565497f5a38b464070fb2a5754af5de50829b222c877223f4',
                    'src/shared/condition.c':'fc1f26ad21a2fea0713b72e2e76c2ca644fcbbac566fc1a46f2a6a366d77bd9e'},
                'templateCommand':'-modprobe -abq %i',
                'skipConditionsObserved':False,
                'capabilityConditionScope':'manager process bounding set; not worker CapabilityBoundingSet',
                'loadedConditionScope':'sysfs directory/initstate observations; built-in source config alone insufficient',
                'templateInstallGuard':'Meson entry has no HAVE_KMOD guard',
                'templateLimitations':'oneshot; StartLimitIntervalSec=0; no RemainAfterExit; no fixed binary path',
                'ignoredFailureProvesZeroCost':False},
            'blockers':['template/binary search path, exact modprobe binary and transitive behavior unqualified',
                        'boot conditions, coalescing/reactivations and total attempt bound unobserved',
                        'external job role/cgroup/pre-exec escrow coverage and full lifecycle costs unclosed']}
