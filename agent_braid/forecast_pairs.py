# SPDX-License-Identifier: AGPL-3.0-only
"""Paired policy rehearsal with an in-memory executor and synthetic grants only.

No callback, subprocess, filesystem, model or runtime execution is accepted.
Clock intervals and result identities are fixture assumptions, not observations.
"""
from copy import deepcopy

from .forecast_data import ForecastError, digest, integer, require
from .forecast_decisions import simulate_decisions
from .forecast_policy import validate_advice

_ARMS = ('serial-reference', 'non-model-reference', 'forecast-choice')
_PHASES = ('data-preparation', 'forecast', 'advice', 'replay',
           'isolated-preparation', 'grants', 'isolated-execution', 'verification',
           'cleanup', 'export')
_FAULTS = ('timeout', 'cancel', 'verification-mismatch')


def _grant(row, arm):
    value = {'version': 'agent-braid-simulation-grant-fixture-v1',
             'scope': 'simulation-only', 'episodeGroup': row['episodeGroup'],
             'arm': arm['arm'], 'decisionDigest': row['receiptDigest'],
             'planDigest': arm['planDigest'], 'executionAuthorization': False}
    return {**value, 'fixtureDigest': digest(value)}


def synthetic_grant_fixtures(decisions):
    """Make caller-owned fixture tokens; these are never operator grants.

    The harness independently recomputes decisions and checks every token at use.
    A copied/re-signed token cannot authorize a different arm, plan or episode.
    """
    return {row['episodeGroup']+'/'+arm['arm']: _grant(row, arm)
            for row in decisions['decisions'] if row['status'] == 'mapped'
            for arm in row['arms']}


def rehearse_paired_policies(signals, operations, *, evaluation, frozen, decisions,
                            grants, order_seed=0, faults=None, use_offsets=None):
    """Rehearse frozen arms, refusal, cancellation and interval reconciliation.

    Caller-supplied grants/faults are simulation fixtures, not authority or live
    fault injection. Arm order rotates deterministically by origin before any
    outcome. Cancellation retains subsequent arms as not run for that origin.
    Unknown full-deployment costs remain unknown, even on a successful rehearsal.
    """
    integer(order_seed)
    require(type(decisions) is dict, 'invalid-paired-decisions')
    expected = simulate_decisions(signals, operations, evaluation=evaluation,
                                  frozen=frozen, mode=decisions.get('mode'))
    require(digest(decisions) == digest(expected), 'paired-decision-drift')
    faults = {} if faults is None else deepcopy(faults)
    use_offsets = {} if use_offsets is None else deepcopy(use_offsets)
    roster = {row['episodeGroup']+'/'+arm for row in expected['decisions'] for arm in _ARMS}
    groups = {row['episodeGroup'] for row in expected['decisions']}
    require(type(grants) is dict and set(grants) <= roster, 'invalid-simulation-grants')
    require(type(faults) is dict and set(faults) <= roster
            and all(v in _FAULTS for v in faults.values()), 'invalid-simulation-faults')
    require(type(use_offsets) is dict and set(use_offsets) <= groups, 'invalid-use-offsets')
    for offset in use_offsets.values(): integer(offset)
    grants = deepcopy(grants)
    clock = 0
    episodes = []
    for origin, decision in enumerate(expected['decisions']):
        rotation = (order_seed+origin) % len(_ARMS)
        order = _ARMS[rotation:]+_ARMS[:rotation]
        rows = []
        cancelled = False
        for index, name in enumerate(order):
            arm = next(a for a in decision['arms'] if a['arm'] == name)
            scope = digest({'episodeGroup': decision['episodeGroup'], 'arm': name,
                            'decisionDigest': decision['receiptDigest'], 'orderSeed': order_seed})
            row = {'arm': name, 'orderIndex': index, 'scopeDigest': scope,
                   'executionKind': 'in-memory-fixture',
                   'resultSemantics': 'asserted-fixture-equivalence-not-git-verification',
                   'action': arm['action'], 'planDigest': arm['planDigest'],
                   'status': 'not-run-after-cancellation' if cancelled else 'refused',
                   'reasonCodes': [], 'simulatedResultDigest': None, 'phases': [],
                   'executionAuthorization': False}
            rows.append(row)
            if cancelled: continue
            if decision['status'] != 'mapped':
                row['reasonCodes'] = list(decision['reasonCodes'])
                continue
            now = decision['cutoffNs']+use_offsets.get(decision['episodeGroup'], 0)
            try:
                require(now >= decision['cutoffNs'], 'decision-not-yet-available')
                validate_advice(decision['advice'], decision['request'], now_ns=now)
            except ForecastError as error:
                row['reasonCodes'] = [str(error)]
                continue
            key = decision['episodeGroup']+'/'+name
            fault = faults.get(key)
            candidate = next(c for c in decision['candidates'] if c['planDigest'] == arm['planDigest'])
            require(candidate['eligible'] is True, 'ineligible-simulation-plan')
            # A canonical manifest is shared by serial/parallel candidate plans;
            # equivalence here is a fixture assertion, never Git verification.
            result = digest(candidate['plan']['descriptors']['manifest'])
            stopped = False
            produced = None
            for phase in _PHASES:
                if stopped and phase not in ('cleanup', 'export'): continue
                start = clock
                clock += 1  # one fixture tick; no observed wall/CPU/memory units
                state = 'simulated-completed'
                if phase == 'grants' and digest(grants.get(key)) != digest(_grant(decision, arm)):
                    row.update(status='refused', reasonCodes=['simulation-grant-mismatch'])
                    stopped = True
                    state = 'simulated-refused'
                elif phase == 'isolated-execution' and fault in ('timeout', 'cancel'):
                    row.update(status='timed-out' if fault == 'timeout' else 'cancelled',
                               reasonCodes=['simulated-'+fault])
                    stopped = True
                    cancelled = fault == 'cancel'
                    state = 'simulated-failed'
                elif phase == 'isolated-execution':
                    produced = digest({'corrupted': result}) if fault == 'verification-mismatch' else result
                    row['simulatedResultDigest'] = produced
                elif phase == 'verification':
                    if produced != result:
                        row.update(status='failed-verification', reasonCodes=['simulated-result-mismatch'])
                        state = 'simulated-failed'
                    else:
                        row.update(status='simulated-completed')
                row['phases'].append({'stage': phase, 'startTick': start,
                                      'endTick': clock, 'status': state})
        episodes.append({'episodeGroup': decision['episodeGroup'],
                         'decisionDigest': decision['receiptDigest'], 'partition': decision['partition'],
                         'forecastStatus': decision['request']['forecast']['status'] if decision['request'] else None,
                         'adviceReasonCodes': list(decision['advice']['reasonCodes']) if decision['advice'] else list(decision['reasonCodes']),
                         'order': list(order), 'arms': rows,
                         'status': 'synthetic-descriptive' if all(r['status'] == 'simulated-completed' for r in rows)
                         else 'inconclusive'})
    result = {'version': 'agent-braid-paired-policy-rehearsal-v1',
              'decisionReportDigest': expected['receiptDigest'], 'policyDigest': frozen['policyDigest'],
              'fixtureDigest': digest({'grants': grants, 'faults': faults, 'useOffsets': use_offsets,
                                      'orderSeed': order_seed}),
              'episodes': episodes, 'costs': {'unit': 'synthetic-tick', 'totalTicks': clock,
                  'boundary': 'simulated-data-preparation-through-export',
                  'fullDeploymentCosts': None, 'reason': 'not-measured-no-runtime-executed'},
              'provenance': 'synthetic-simulation', 'utilityAccepted': False,
              'realWorkloadEvidence': False, 'executionAuthorization': False}
    result['summary'] = {'intendedEpisodes': len(episodes), 'intendedArms': 3*len(episodes),
                         'invalidEpisodes': sum(e['status'] == 'inconclusive' for e in episodes),
                         'completedArms': sum(r['status'] == 'simulated-completed'
                                              for e in episodes for r in e['arms'])}
    result['receiptDigest'] = digest(result)
    return result


def validate_paired_rehearsal(receipt, signals, operations, **kwargs):
    """Recompute all fixture intervals/outcomes; a re-signed checksum is not proof."""
    expected = rehearse_paired_policies(signals, operations, **kwargs)
    require(digest(receipt) == digest(expected), 'paired-rehearsal-drift')
    return deepcopy(expected)
