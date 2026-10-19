# SPDX-License-Identifier: AGPL-3.0-only
"""Private v9 driver preparation and synchronized accounting; no launch command.

A staged-tree inspection binds available bytes, not their build authority or a
running host. The current v8 profile cannot become v9 by supplying this receipt.
No caller boolean, callback or MCP envelope can open the native boundary here.
"""
from dataclasses import dataclass
from functools import wraps
import hashlib

from .forecast_bootstrap import bootstrap_ready
from .forecast_data import canonical, digest, integer, pin, require
from .forecast_exec_budget import ExecAllocation, PartitionLedger
from .forecast_host_census import inspect_staged_host
from .forecast_manager_escrow import GateBinding, ManagerEscrowState


def serialized(method):
    @wraps(method)
    def call(self,*args,**kwargs):
        with self.escrow.lock:return method(self,*args,**kwargs)
    return call


@dataclass(frozen=True)
class DriverPreparation:
    profile_identity: str
    source_digest: str
    manifest_sha256: str
    inventory_digest: str
    provenance_sha256: str
    nonce: str
    census_record: bytes
    binding: GateBinding

    def __post_init__(self):
        for value in (self.profile_identity,self.source_digest,self.manifest_sha256,
                      self.inventory_digest,self.provenance_sha256,self.nonce):pin(value)
        require(type(self.census_record) is bytes and type(self.binding) is GateBinding and
                self.binding.identity==self.profile_identity,'v9-driver-preparation-binding')

    @property
    def identity(self):
        return digest({'profile':self.profile_identity,'source':self.source_digest,
                       'manifest':self.manifest_sha256,'inventory':self.inventory_digest,
                       'provenance':self.provenance_sha256,'nonce':self.nonce,
                       'censusSha256':hashlib.sha256(self.census_record).hexdigest(),
                       'managerStartTicks':self.binding.manager_start_ticks,
                       'managerSha256':self.binding.manager_sha256,'workerUid':self.binding.worker_uid,
                       'phaseSeconds':list(self.binding.allocation.seconds),
                       'phaseGitRequests':list(self.binding.allocation.requests),
                       'executorSha256':self.binding.executor_sha256,
                       'allocation':self.binding.allocation.manifest()})


def prepare_driver(profile,root,manifest_bytes,*,expected_manifest_sha256,nonce,
                   manager_start_ticks):
    """Explicit offline preparation only; caller pins remain unaccredited inputs."""
    from .forecast_linux_profile import LinuxAdmissionProfile
    require(type(profile) is LinuxAdmissionProfile,'v9-driver-profile-type')
    census=inspect_staged_host(root,manifest_bytes,expected_manifest_sha256=expected_manifest_sha256)
    require(census['sourceDigest']==profile.source_digest,'v9-driver-source-binding')
    fields={'manager':'manager_sha256','operatorPython':'operator_sha256',
            'operatorLauncher':'operator_entry_sha256','workerPython':'worker_sha256',
            'execCensus':'census_sha256'}
    require(all(census['bindings'][role]['sha256']==getattr(profile,field)
                for role,field in fields.items()),'v9-driver-artifact-binding')
    binding=GateBinding(profile.identity,profile.manager_sha256,census['bindings']['executor']['sha256'],
                        manager_start_ticks,profile.uid,ExecAllocation.from_profile(profile))
    return DriverPreparation(profile.identity,profile.source_digest,census['manifestSha256'],
                             census['inventoryDigest'],census['provenanceSha256'],nonce,
                             canonical(census),binding)


class V9Driver:
    """One finite accounting session. Receipts never authorize dispatch or closure.

    Broker reservations describe attempts, not effective launches. The native v2
    broker/manager wiring, immutable outer guard and final observer are pending.
    Failed or unfinished sessions cannot restart, refund, or reset the origin.
    """
    def __init__(self,preparation,origin_ns):
        require(type(preparation) is DriverPreparation,'v9-driver-preparation-type')
        self.preparation=preparation;self.preparation_identity=preparation.identity
        integer(origin_ns,1)
        self.escrow=ManagerEscrowState(preparation.binding,origin_ns)
        self.broker=PartitionLedger(preparation.binding.allocation,'broker',origin_ns)
        self.last_ns=origin_ns;self.failed=False;self.finished=False

    def _check(self,now):
        require(self.preparation.identity==self.preparation_identity and not self.failed and
                not self.finished and not self.escrow.failed and not self.broker.failed,
                'v9-driver-failed-or-drift')
        integer(now,self.last_ns,self.broker.whole_deadline-1);self.last_ns=now
        require(self.broker.phase==self.escrow.ledger.phase and
                self.broker.deadline==self.escrow.ledger.deadline,'v9-driver-partition-drift')
        # A missed phase deadline cannot be replaced by a fresh phase allocation.
        if self.broker.phase>=0:require(now<self.broker.deadline,'v9-driver-phase-expired')

    @serialized
    def fail(self):
        self.failed=True;self.escrow.fail();self.broker.failed=True

    @serialized
    def begin(self,owner_pid,*,now_ns):
        try:
            self._check(now_ns);self.escrow.begin(owner_pid,now_ns=now_ns)
            self.broker.enter(0,self.escrow.ledger.deadline,now_ns=now_ns)
        except BaseException:self.fail();raise

    @serialized
    def advance(self,phase,*,now_ns):
        try:
            self._check(now_ns)
            require(not any(r['state']=='reserved' for r in self.broker.records),
                    'v9-driver-broker-outstanding')
            self.escrow.advance(phase,now_ns=now_ns)
            self.broker.enter(phase,self.escrow.ledger.deadline,now_ns=now_ns)
        except BaseException:self.fail();raise

    @serialized
    def reserve_broker(self,key,pid,*,now_ns):
        try:
            self._check(now_ns)
            return self.broker.reserve(key,pid,now_ns=now_ns)
        except BaseException:self.fail();raise

    @serialized
    def finish_broker(self,ticket,*,continued,now_ns):
        try:
            self._check(now_ns);self.broker.finish(ticket,continued=continued)
            require(continued,'v9-driver-broker-outcome-unknown')
        except BaseException:self.fail();raise

    @serialized
    def finish_accounting(self,*,now_ns):
        try:
            self._check(now_ns)
            require(self.broker.phase==4 and self.escrow.completed==list(range(6)) and
                    self.escrow.outstanding is None and self.escrow.pending is None and
                    not any(r['state']=='reserved' for r in self.broker.records),
                    'v9-driver-incomplete')
            self.finished=True
        except BaseException:self.fail();raise

    def native_entry(self,profile):
        """Fail before sockets, mounts, ELF loading, manager or service requests."""
        from .forecast_linux_profile import LinuxAdmissionProfile
        require(type(profile) is LinuxAdmissionProfile and
                profile.identity==self.preparation.profile_identity,'v9-driver-profile-drift')
        bootstrap_ready(profile)
        # No override argument: qualifying the new immutable driver is a future change.
        require(False,'v9-driver-native-integration-and-outer-guard-pending')

    @serialized
    def receipt(self):
        return {'version':'fc1-v9-driver-accounting-v1','preparationIdentity':self.preparation_identity,
                'originalOriginNs':self.broker.origin_ns,'originalCloseByNs':self.broker.whole_deadline,
                'accountingFinished':self.finished,'failed':self.failed,
                'escrow':self.escrow.receipt(),'broker':self.broker.receipt(),
                'artifactProvenanceAccepted':False,'hostActivationClosed':False,
                'externalWatchdogAccepted':False,'wholeFlowCleanupVerified':False,
                'operationalBudgetClosed':False,'nativeQualification':False,
                'executionAuthorization':False}


def offline_v9_plan(preparation, profile, origin_ns):
    """Compose rendered unit text without emitting a Linux admission profile.

    Mount lifecycle is assigned to the root syscall owner; no manager mount job
    is rendered. Implicit dependencies, source/object and lifecycle cost closure
    are still unknown, so this plan cannot pass require_closed_job_graph.
    """
    from .forecast_linux_profile import LinuxAdmissionProfile
    from .forecast_bootstrap import offline_bootstrap_v4
    from .forecast_v9_renderer import render_offline_v9
    require(type(preparation) is DriverPreparation and type(profile) is LinuxAdmissionProfile,
            'v9-plan-types')
    require(profile.identity == preparation.profile_identity and
            profile.source_digest == preparation.source_digest and
            ExecAllocation.from_profile(profile) == preparation.binding.allocation and
            profile.manager_sha256 == preparation.binding.manager_sha256 and
            profile.uid == preparation.binding.worker_uid, 'v9-plan-profile-binding')
    integer(origin_ns, 1)
    roles = ('supervisor', 'anchor', 'operator', 'prepare', 'verify', 'terminal')
    graph = {'version': 'fc1-offline-job-graph-v9',
             'preparationIdentity': preparation.identity,
             'roles': [{'role': role, 'phase': phase,
                        'after': [] if i == 0 else [roles[i-1]],
                        'execAccountingOwner': 'escrow'}
                       for i, (role, phase) in enumerate(zip(roles, (0,0,0,0,3,4), strict=True))],
             'mountOwner': 'root-syscall-owner', 'managerMountJobs': [],
             'implicitDependenciesClosed': False, 'automaticServiceStartsClosed': False,
             'restart': False, 'nativeGraphClosed': False}
    graph['renderer'] = render_offline_v9(profile)
    bootstrap = offline_bootstrap_v4(preparation, origin_ns, digest(graph),
                                     unit_sha256=graph['renderer']['unitSha256'])
    return {'version': 'fc1-offline-v9-integration-v1', 'graph': graph,
            'bootstrap': bootstrap, 'allocation': preparation.binding.allocation.manifest(),
            'brokerLauncherVersion': 'fc1-offline-broker-launcher-v2',
            'profileV9Emitted': False, 'candidateReadyForNativeAdmission': False,
            'operationalBudgetClosed': False, 'nativeQualification': False,
            'executionAuthorization': False}


class OfflineV9Integration:
    """Single offline session sharing both partitions and the original clock."""
    def __init__(self, preparation, profile, origin_ns):
        from .forecast_launcher import OfflineBrokerV2
        self.plan_bytes = canonical(offline_v9_plan(preparation, profile, origin_ns))
        self.identity = hashlib.sha256(self.plan_bytes).hexdigest()
        self.driver = V9Driver(preparation, origin_ns)
        self.broker = OfflineBrokerV2(self.driver, self.identity)

    def receipt(self):
        import json
        with self.driver.escrow.lock:
            if (type(self.plan_bytes) is not bytes or
                    hashlib.sha256(self.plan_bytes).hexdigest() != self.identity or
                    self.broker.integration_identity != self.identity):
                self.driver.fail()
                require(False, 'v9-integration-rendered-plan-drift')
            plan = json.loads(self.plan_bytes)
            return {'version': 'fc1-offline-v9-integration-receipt-v1',
                    'integrationIdentity': self.identity,
                    'renderedUnitDigest': plan['graph']['renderer']['unitSetDigest'],
                    'dependencyInventoryDigest': plan['graph']['renderer']['dependencyInventoryDigest'],
                    'bootstrapDigest': digest(plan['bootstrap']),
                    'driver': self.driver.receipt(), 'broker': self.broker.receipt(),
                    'profileV9Emitted': False, 'nativeQualification': False,
                    'executionAuthorization': False}
