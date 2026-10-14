# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded technical cost accounting; reported counters are not attestations.

This companion contract does not change forecast envelopes or M4.5 ledgers.
Times are offsets on one monotonic clock. CPU meters must cover disjoint
accounting domains, not nested parent/child cgroups. Memory is never added.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
import time

from .forecast_data import (
    canonical, digest, identifier, integer, keys, parse_record, pin,
    reconcile_phases, require,
)

VERSION = 'agent-braid-forecast-technical-cost-v1'
STAGES = (
    'data-preparation', 'artifact-provisioning', 'engine-startup',
    'model-startup', 'residency', 'forecast', 'failure-controls',
    'advice', 'cache', 'grants', 'replay', 'isolated-preparation', 'isolated-execution',
    'waiting-deferred', 'verification', 'export', 'cleanup',
)
CPU_DOMAINS = ('coordinator', 'client-children', 'worker-container', 'engine')
CPU_SCOPES = dict(zip(CPU_DOMAINS, (
    'coordinator-process-only', 'owned-clients-excluding-daemon-and-worker',
    'worker-cgroup-inclusive', 'daemon-processes-excluding-containers',
)))
MEMORY_SCOPES = ('process-lifetime-peak', 'cgroup-lifetime-peak', 'cgroup-sample')


def validate_cost_ledger(raw):
    """Validate integrity and accounting, without verifying measurement sources."""
    record = parse_record(canonical(raw))
    keys(record, ('version', 'runId', 'sourceKind', 'inputDigest', 'artifactDigest', 'artifactReason',
                  'wallNs', 'phases', 'cpu', 'memory', 'cleanupConfirmed',
                  'publicationIncluded', 'publicationReason', 'receiptDigest'))
    require(record['version'] == VERSION, 'unsupported-cost-version')
    identifier(record['runId'])
    require(record['sourceKind'] in ('synthetic-simulation', 'authentic-on-synthetic'),
            'unsupported-cost-source')
    pin(record['inputDigest'])
    if record['artifactDigest'] is None:
        identifier(record['artifactReason'])
    else:
        pin(record['artifactDigest'])
        require(record['artifactReason'] is None, 'invalid-artifact-reason')
    wall = integer(record['wallNs'])
    require(type(record['cleanupConfirmed']) is bool
            and type(record['publicationIncluded']) is bool, 'invalid-cost-completion')
    if record['publicationIncluded']:
        require(record['publicationReason'] is None, 'invalid-publication-reason')
    else:
        identifier(record['publicationReason'])
    phases = record['phases']
    require(type(phases) is list and len(phases) <= 1024, 'phase-budget-exceeded')
    ids = set()
    for phase in phases:
        keys(phase, ('id', 'stage', 'startedNs', 'finishedNs', 'status',
                     'accounting', 'reason', 'sourceDigest'))
        identifier(phase['id'])
        require(phase['id'] not in ids, 'duplicate-cost-phase')
        ids.add(phase['id'])
        require(phase['stage'] in STAGES, 'unsupported-cost-stage')
        require(phase['status'] in ('completed', 'failed', 'refused', 'cancelled',
                                    'timed-out', 'not-run'), 'invalid-cost-outcome')
        require(phase['accounting'] in ('observed', 'not-observed', 'reused',
                                        'not-applicable'), 'invalid-cost-accounting')
        if phase['accounting'] == 'observed':
            start, end = integer(phase['startedNs']), integer(phase['finishedNs'])
            require(start <= end <= wall and phase['reason'] is None,
                    'invalid-cost-interval')
            require(phase['status'] != 'not-run', 'observed-phase-not-run')
        else:
            require(phase['startedNs'] is None and phase['finishedNs'] is None,
                    'unobserved-cost-has-interval')
            identifier(phase['reason'])
            require(phase['status'] == 'not-run', 'unobserved-cost-has-outcome')
        if phase['sourceDigest'] is not None:
            pin(phase['sourceDigest'])
        require(phase['accounting'] != 'reused' or phase['sourceDigest'] is not None,
                'reused-cost-source-required')
    counters = record['cpu']
    require(type(counters) is list and len(counters) == len(CPU_DOMAINS),
            'incomplete-cpu-roster')
    domains, meters = set(), set()
    for row in counters:
        keys(row, ('domain', 'scope', 'meterId', 'startedNs', 'finishedNs', 'beforeNs',
                   'afterNs', 'reason', 'sourceDigest'))
        require(row['domain'] in CPU_DOMAINS and row['domain'] not in domains,
                'duplicate-cpu-domain')
        domains.add(row['domain'])
        require(row['scope'] == CPU_SCOPES[row['domain']], 'invalid-cpu-scope')
        if row['beforeNs'] is None:
            require(row['afterNs'] is None and row['meterId'] is None
                    and row['startedNs'] is None and row['finishedNs'] is None,
                    'inconsistent-cpu-counter')
            identifier(row['reason'])
        else:
            identifier(row['meterId'])
            require(row['meterId'] not in meters, 'overlapping-cpu-meter')
            meters.add(row['meterId'])
            before, after = integer(row['beforeNs']), integer(row['afterNs'])
            start, end = integer(row['startedNs']), integer(row['finishedNs'])
            require(before <= after and start <= end <= wall
                    and row['reason'] is None, 'invalid-cpu-counter')
        if row['sourceDigest'] is not None:
            pin(row['sourceDigest'])
    memory = record['memory']
    require(type(memory) is list and len(memory) <= 128, 'memory-budget-exceeded')
    memory_ids = set()
    for row in memory:
        keys(row, ('meterId', 'scope', 'observedAtNs', 'bytes', 'reason', 'sourceDigest',
                   'samplePeriodNs', 'limitBytes', 'limitReason'))
        identifier(row['meterId'])
        require(row['scope'] in MEMORY_SCOPES, 'invalid-memory-scope')
        if row['scope'] == 'cgroup-sample':
            integer(row['samplePeriodNs'], 1)
        else:
            require(row['samplePeriodNs'] is None, 'invalid-memory-sample-period')
        if row['limitBytes'] is None:
            identifier(row['limitReason'])
        else:
            integer(row['limitBytes'], 1)
            require(row['limitReason'] is None, 'invalid-memory-limit-reason')
        if row['bytes'] is None:
            require(row['observedAtNs'] is None, 'inconsistent-memory-counter')
            identifier(row['reason'])
        else:
            integer(row['bytes'])
            require(integer(row['observedAtNs']) <= wall and row['reason'] is None,
                    'invalid-memory-observation')
        key = (row['meterId'], row['scope'], row['observedAtNs'])
        require(key not in memory_ids, 'duplicate-memory-observation')
        memory_ids.add(key)
        if row['sourceDigest'] is not None:
            pin(row['sourceDigest'])
    require(record['receiptDigest'] == digest({k: v for k, v in record.items()
                                              if k != 'receiptDigest'}),
            'cost-integrity-drift')
    return record


def summarize_cost_ledger(raw):
    """Expose gaps, overlap and residual; never turn missing values into zero."""
    record = validate_cost_ledger(raw)
    observed = [p for p in record['phases'] if p['accounting'] == 'observed']
    wall = reconcile_phases([
        {'name': p['id'], 'startedNs': p['startedNs'], 'finishedNs': p['finishedNs']}
        for p in observed
    ], record['wallNs'])
    gaps = [stage + ':missing' for stage in STAGES
            if not any(p['stage'] == stage for p in record['phases'])]
    if record['artifactDigest'] is None:
        gaps.append('artifact:' + record['artifactReason'])
    # Reused setup is a visible sunk cost, not zero or an allocation decision.
    gaps += [p['id'] + ':' + p['reason'] for p in record['phases']
             if p['accounting'] in ('not-observed', 'reused')]
    cpu = {}
    for row in record['cpu']:
        cpu[row['domain']] = (None if row['beforeNs'] is None
                              else row['afterNs'] - row['beforeNs'])
        if row['beforeNs'] is None:
            gaps.append('cpu-' + row['domain'] + ':' + row['reason'])
        elif row['startedNs'] != 0 or row['finishedNs'] != record['wallNs']:
            gaps.append('cpu-' + row['domain'] + ':partial-boundary')
    if not record['memory']:
        gaps.append('memory:missing')
    gaps += ['memory-' + row['meterId'] + ':' + row['reason']
             for row in record['memory'] if row['bytes'] is None]
    if not record['cleanupConfirmed']:
        gaps.append('cleanup:unconfirmed')
    if not record['publicationIncluded']:
        gaps.append('publication:' + record['publicationReason'])
    phase_sum = sum(p['finishedNs'] - p['startedNs'] for p in observed)
    cpu_total = sum(cpu.values()) if all(v is not None for v in cpu.values()) else None
    require(phase_sum <= 2**63 - 1 and (cpu_total is None or cpu_total <= 2**63 - 1),
            'aggregate-cost-overflow')
    return {
        'receiptDigest': record['receiptDigest'], **wall,
        'phaseSumNs': phase_sum, 'residualScope': 'unattributed-wall-not-coordinator-cpu',
        'cpuNsByDomain': cpu,
        'reportedDisjointCpuNs': cpu_total,
        'memoryObservations': deepcopy(record['memory']),
        'gaps': sorted(gaps), 'reportedCoverageComplete': not gaps,
        'sourceBindingsVerified': False, 'fullDeploymentCostAccepted': False,
        'economicCostAccepted': False, 'executionAuthorization': False,
    }


class CostRecorder:
    """Observe owned host phases and coordinator CPU, including failed phases.

    Remote worker/engine counters require separate collectors. Publication of
    this recorder's final receipt occurs after sealing and remains a stated gap.
    An injected clock supports simulation; callers must label that provenance.
    """

    def __init__(self, run_id, input_digest, artifact_digest, *,
                 source_kind='authentic-on-synthetic', clock=time.monotonic_ns,
                 cpu_clock=time.process_time_ns):
        identifier(run_id); pin(input_digest)
        if artifact_digest is not None: pin(artifact_digest)
        self.clock, self.cpu_clock = clock, cpu_clock
        self.started, self.cpu_started = clock(), cpu_clock()
        self.active, self.sealed = set(), False
        self.record = {'version': VERSION, 'runId': run_id, 'sourceKind': source_kind,
                       'inputDigest': input_digest, 'artifactDigest': artifact_digest,
                       'artifactReason': 'not-observed' if artifact_digest is None else None,
                       'wallNs': None, 'phases': [], 'cpu': [], 'memory': [],
                       'cleanupConfirmed': False, 'publicationIncluded': False,
                       'publicationReason': 'final-receipt-write-after-seal'}

    def _id(self, phase_id, stage):
        require(not self.sealed, 'cost-recorder-sealed')
        require(len(self.record['phases']) + len(self.active) < 1024, 'phase-budget-exceeded')
        identifier(phase_id)
        require(stage in STAGES, 'unsupported-cost-stage')
        require(phase_id not in self.active
                and not any(p['id'] == phase_id for p in self.record['phases']),
                'duplicate-cost-phase')

    @contextmanager
    def phase(self, phase_id, stage):
        self._id(phase_id, stage)
        self.active.add(phase_id)
        start = self.clock() - self.started
        status = 'completed'
        try:
            yield
        except BaseException:
            status = 'failed'
            raise
        finally:
            self.record['phases'].append({
                'id': phase_id, 'stage': stage, 'startedNs': start,
                'finishedNs': self.clock() - self.started, 'status': status,
                'accounting': 'observed', 'reason': None, 'sourceDigest': None})
            self.active.remove(phase_id)

    def unavailable(self, phase_id, stage, reason, *, accounting='not-observed',
                    source_digest=None):
        self._id(phase_id, stage)
        require(accounting in ('not-observed', 'reused', 'not-applicable'),
                'invalid-cost-accounting')
        identifier(reason)
        if source_digest is not None:
            pin(source_digest)
        require(accounting != 'reused' or source_digest is not None,
                'reused-cost-source-required')
        self.record['phases'].append({
            'id': phase_id, 'stage': stage, 'startedNs': None, 'finishedNs': None,
            'status': 'not-run', 'accounting': accounting, 'reason': reason,
            'sourceDigest': source_digest})

    def seal(self, *, cleanup_confirmed=False):
        require(not self.sealed and not self.active, 'cost-recorder-not-quiescent')
        wall, cpu_end = self.clock() - self.started, self.cpu_clock()
        result = deepcopy(self.record)
        result['wallNs'], result['cleanupConfirmed'] = wall, cleanup_confirmed
        result['cpu'] = [{
            'domain': domain, 'scope': CPU_SCOPES[domain],
            'meterId': 'coordinator-process' if domain == 'coordinator' else None,
            'startedNs': 0 if domain == 'coordinator' else None,
            'finishedNs': wall if domain == 'coordinator' else None,
            'beforeNs': self.cpu_started if domain == 'coordinator' else None,
            'afterNs': cpu_end if domain == 'coordinator' else None,
            'reason': None if domain == 'coordinator' else 'not-observed', 'sourceDigest': None,
        } for domain in CPU_DOMAINS]
        result['receiptDigest'] = digest(result)
        validate_cost_ledger(result)
        self.sealed = True
        return result
