# SPDX-License-Identifier: AGPL-3.0-only
"""Offline shadow lifecycle over recomputed paired fixtures; no runtime hooks."""
from copy import deepcopy

from .forecast_data import digest, integer, keys, require
from .forecast_pairs import validate_paired_rehearsal
from .forecast_trace import SyntheticAdviceMonitor


def rehearse_shadow_recovery(signals, operations, *, paired, pairing, monitor_policy, events):
    """Bind later synthetic labels to frozen shadow decisions and retain recovery.

    Events contain episodeGroup, observedAtNs, kind (outcome/cancel), and an
    outcome only for outcome events. Observed time is fixture time, never a host
    clock. Cancellation stops ingestion for this rehearsal; rollback stops new
    advice while retaining later labels for already frozen decisions. Neither
    changes any paired arm, plan, grant or outcome. No resumed execution exists.
    """
    require(type(pairing) is dict, 'invalid-shadow-pairing')
    validated = validate_paired_rehearsal(paired, signals, operations, **pairing)
    decisions = pairing['decisions']
    require(decisions['mode'] == 'shadow', 'shadow-mode-required')
    require(type(events) is list and len(events) <= 4096, 'invalid-shadow-events')
    monitor = SyntheticAdviceMonitor(monitor_policy)
    rows = {r['episodeGroup']: r for r in decisions['decisions']}
    seen = set()
    records = []
    cancelled = False
    previous_time = -1
    for event in deepcopy(events):
        require(type(event) is dict, 'invalid-shadow-event')
        kind = event.get('kind')
        require(kind in ('outcome', 'cancel'), 'invalid-shadow-event-kind')
        fields = ('episodeGroup', 'observedAtNs', 'kind')
        keys(event, fields + (('outcome',) if kind == 'outcome' else ()))
        now = event['observedAtNs']
        integer(now)
        require(now >= previous_time, 'shadow-observation-order')
        previous_time = now
        group = event['episodeGroup']
        require(type(group) is str and group in rows, 'unknown-shadow-episode')
        decision = rows[group]
        require(now >= decision['cutoffNs'], 'shadow-event-before-decision')
        advice = decision['advice']
        record = {'eventDigest': digest(event), 'episodeGroup': group,
                  'decisionDigest': decision['receiptDigest'], 'kind': kind,
                  'observedAtNs': now, 'status': 'retained-after-cancellation',
                  'referenceAction': advice['referenceAction'] if advice else None,
                  'selectedAction': advice['referenceAction'] if advice else None,
                  'fallbackReasons': list(advice['reasonCodes'] if advice else decision['reasonCodes']),
                  'trace': None, 'executionAuthorization': False}
        if not cancelled and kind == 'cancel':
            cancelled = True
            record['status'] = 'cancelled-observation-session'
        elif not cancelled:
            require(decision['status'] == 'mapped', 'shadow-decision-not-mapped')
            outcome = event['outcome']
            require(type(outcome) is dict, 'invalid-shadow-outcome')
            require(type(outcome.get('availableAtNs')) is int
                    and outcome['availableAtNs'] <= now, 'shadow-label-not-available')
            # Identity is the forecast target and time, not the label value or
            # delivery timestamp: re-signing or late redelivery cannot recount it.
            identity = (group, outcome.get('targetId'), outcome.get('eventNs'))
            require(all(type(v) in (str, int) for v in identity), 'invalid-shadow-label-identity')
            require(identity not in seen, 'duplicate-shadow-label')
            trace = monitor.observe(advice, decision['request']['forecast'], outcome)
            seen.add(identity)
            record.update(status='observed-synthetic-label', trace=trace)
        record['modeAfter'] = 'off' if cancelled or monitor.rolled_back else 'shadow'
        records.append(record)
    overhead = sum(p['endTick'] - p['startTick'] for episode in validated['episodes']
                   for arm in episode['arms'] if arm['arm'] == 'forecast-choice'
                   for p in arm['phases'] if p['stage'] in ('forecast', 'advice'))
    result = {'version': 'agent-braid-synthetic-shadow-recovery-v1',
              'pairedReceiptDigest': validated['receiptDigest'],
              'decisionReportDigest': decisions['receiptDigest'],
              'monitorPolicyDigest': digest(monitor_policy), 'eventsDigest': digest(events),
              'frozenDecisions': [
                  {'episodeGroup': row['episodeGroup'], 'decisionDigest': row['receiptDigest'],
                   'status': row['status'],
                   'referenceAction': row['advice']['referenceAction'] if row['advice'] else None,
                   'selectedPlanDigest': row['advice']['selectedPlanDigest'] if row['advice'] else None,
                   'proposedAction': row['advice']['proposedAction'] if row['advice'] else None,
                   'fallbackReasons': list(row['advice']['reasonCodes'] if row['advice'] else row['reasonCodes']),
                   'pairedArmStatuses': {arm['arm']: arm['status'] for arm in episode['arms']}}
                  for row, episode in zip(decisions['decisions'], validated['episodes'])],
              'records': records, 'cancelled': cancelled, 'rolledBack': monitor.rolled_back,
              'modeAfter': 'off' if cancelled or monitor.rolled_back else 'shadow',
              'pendingOutcomePolicy': 'retain-frozen-decisions-no-runtime-recovery',
              'costs': {'advisoryTicks': overhead, 'unit': 'synthetic-tick',
                        'scope': 'forecast-and-advice-phases-of-forecast-choice-arm',
                        'fullDeploymentCosts': None, 'reason': 'not-measured-no-runtime-executed'},
              'provenance': 'synthetic-simulation', 'executionAuthorization': False,
              'realWorkloadEvidence': False, 'utilityAccepted': False}
    result['receiptDigest'] = digest(result)
    return result


def validate_shadow_recovery(receipt, signals, operations, **kwargs):
    """Recompute fixture bindings and the entire lifecycle, never trust a checksum."""
    expected = rehearse_shadow_recovery(signals, operations, **kwargs)
    require(digest(receipt) == digest(expected), 'shadow-recovery-drift')
    return deepcopy(expected)
