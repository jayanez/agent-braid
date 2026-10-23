# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic episode-cluster diagnostics; no experiment or utility acceptance."""
from copy import deepcopy
import math
import random
from statistics import median

from .forecast_data import canonical, digest, finite, identifier, integer, keys, require
from .forecast_pairs import validate_paired_rehearsal
from .forecast_shadow import validate_shadow_recovery

_ARMS = ('serial-reference', 'non-model-reference', 'forecast-choice')
_PARTITIONS = ('development', 'calibration', 'holdout')


def _plan(plan, episodes):
    keys(plan, ('version', 'primaryGroups', 'roster', 'cyclesPerEpisode',
                'minimumEpisodes', 'seed', 'replicates', 'confidence',
                'minimumRatio', 'lowerBoundMinimum'))
    require(plan['version'] == 'agent-braid-synthetic-report-plan-v1', 'unsupported-report-plan')
    groups = plan['primaryGroups']
    require(type(groups) is list and 1 <= len(groups) <= 16, 'invalid-primary-groups')
    for group in groups: identifier(group)
    require(len(set(groups)) == len(groups), 'duplicate-primary-group')
    roster = plan['roster']
    require(type(roster) is dict and set(roster) == {e['episodeGroup'] for e in episodes},
            'report-roster-drift')
    require(all(type(g) is str and g in groups for g in roster.values()), 'unregistered-report-group')
    integer(plan['cyclesPerEpisode'], 1, 16)
    integer(plan['minimumEpisodes'], 2, 4096)
    integer(plan['seed'])
    integer(plan['replicates'], 32, 4096)
    require(len(episodes) * plan['replicates'] <= 1000000, 'bootstrap-budget-exceeded')
    require(.5 < finite(plan['confidence']) < 1, 'invalid-confidence-level')
    require(finite(plan['minimumRatio']) >= 1 and finite(plan['lowerBoundMinimum']) >= 1,
            'invalid-report-threshold')


def _cycle(raw):
    require(raw is None or type(raw) is dict and set(raw) <= set(_ARMS), 'invalid-cycle-fixture')
    arms = {}
    for arm in _ARMS:
        cost = None if raw is None else raw.get(arm)
        if cost is None:
            arms[arm] = {'baseTicks': None, 'advisoryTicks': None, 'totalTicks': None}
        else:
            keys(cost, ('baseTicks', 'advisoryTicks'))
            base, overhead = cost['baseTicks'], cost['advisoryTicks']
            integer(base, 1, 10**12); integer(overhead, 0, 10**12)
            arms[arm] = {'baseTicks': base, 'advisoryTicks': overhead, 'totalTicks': base + overhead}
    candidate = arms['forecast-choice']['totalTicks']
    ratios, margins = {}, {}
    for reference in _ARMS[:2]:
        total = arms[reference]['totalTicks']
        ratios[reference] = total / candidate if total is not None and candidate is not None else None
        margins[reference] = total - candidate if total is not None and candidate is not None else None
    return {'arms': arms, 'ratios': ratios, 'additionalOverheadBreakEvenTicks': margins,
            'complete': all(a['totalTicks'] is not None for a in arms.values())}


def _statistics(values, plan, stratum):
    """Percentile bootstrap of episode medians, never of individual cycles."""
    point = median(values) if values else None
    if len(values) < 2:
        return {'episodeCount': len(values), 'medianRatio': point, 'interval': None,
                'intervalReason': 'fewer-than-two-independent-fixture-episodes'}
    rng = random.Random(int(digest({'seed': plan['seed'], 'stratum': stratum}), 16))
    draws = sorted(median(rng.choices(values, k=len(values))) for _ in range(plan['replicates']))
    tail = (1 - plan['confidence']) / 2
    return {'episodeCount': len(values), 'medianRatio': point,
            'interval': [draws[math.floor(tail * (len(draws)-1))],
                         draws[math.ceil((1-tail) * (len(draws)-1))]], 'intervalReason': None}


def synthetic_utility_report(signals, operations, *, paired, pairing, plan, timing_fixtures,
                             shadow_context=None):
    """Analyze declared fixture costs against recomputed decisions and arm outcomes.

    Missing episodes, cycles and arm costs remain explicit. Fixture ticks are
    caller assumptions, not measured wall time or full deployment costs. The
    report does not freeze a real registration or certify independence in nature.
    """
    canonical({'plan': plan, 'timings': timing_fixtures, 'shadow': shadow_context})
    require(type(pairing) is dict, 'invalid-report-pairing')
    validated = validate_paired_rehearsal(paired, signals, operations, **pairing)
    episodes = validated['episodes']
    _plan(plan, episodes)
    require(type(timing_fixtures) is dict and set(timing_fixtures) <= set(plan['roster']),
            'unregistered-timing-fixture')
    shadow = None
    if shadow_context is not None:
        keys(shadow_context, ('receipt', 'monitorPolicy', 'events'))
        checked = validate_shadow_recovery(shadow_context['receipt'], signals, operations,
                                          paired=paired, pairing=pairing,
                                          monitor_policy=shadow_context['monitorPolicy'],
                                          events=shadow_context['events'])
        shadow = {k: checked[k] for k in ('receiptDigest', 'modeAfter', 'cancelled', 'rolledBack')}
    records = []
    for episode in sorted(episodes, key=lambda e: e['episodeGroup']):
        group = episode['episodeGroup']
        supplied = timing_fixtures.get(group, [])
        require(type(supplied) is list and len(supplied) <= plan['cyclesPerEpisode'], 'invalid-cycle-count')
        cycles = [_cycle(supplied[i] if i < len(supplied) else None)
                  for i in range(plan['cyclesPerEpisode'])]
        reasons = []
        if any(arm['status'] != 'simulated-completed' for arm in episode['arms']):
            reasons.append('invalid-paired-arm')
        if episode['forecastStatus'] != 'forecast': reasons.append('forecast-fallback')
        if not all(c['complete'] for c in cycles): reasons.append('missing-cycle-cost')
        records.append({'episodeGroup': group, 'partition': episode['partition'],
                        'primaryGroup': plan['roster'][group], 'decisionDigest': episode['decisionDigest'],
                        'arms': [{'arm': a['arm'], 'status': a['status'], 'reasonCodes': a['reasonCodes']}
                                 for a in episode['arms']],
                        'adviceReasonCodes': episode['adviceReasonCodes'], 'cycles': cycles,
                        'reasonCodes': reasons, 'eligibleForComparison': not reasons,
                        'episodeMedianRatios': {ref: median(c['ratios'][ref] for c in cycles)
                                               if not reasons else None for ref in _ARMS[:2]},
                        'additionalOverheadBreakEvenTicks': {
                            ref: median(c['additionalOverheadBreakEvenTicks'][ref] for c in cycles)
                            if not reasons else None for ref in _ARMS[:2]}})
    groups = []
    for partition in _PARTITIONS:
        for group in sorted(plan['primaryGroups']):
            rows = [r for r in records if r['partition'] == partition and r['primaryGroup'] == group]
            eligible = [r for r in rows if r['eligibleForComparison']]
            comparisons = {ref: _statistics([r['episodeMedianRatios'][ref] for r in eligible], plan,
                                            [partition, group, ref]) for ref in _ARMS[:2]}
            primary = comparisons['non-model-reference']
            reasons = []
            if len(eligible) < plan['minimumEpisodes']: reasons.append('insufficient-independent-episodes')
            if len(eligible) != len(rows): reasons.append('incomplete-or-fallback-episodes')
            status = 'inconclusive'
            if not reasons:
                low, high = primary['interval']
                if primary['medianRatio'] >= plan['minimumRatio'] and low > plan['lowerBoundMinimum']:
                    status = 'thresholds-met'
                elif primary['medianRatio'] < plan['minimumRatio'] or high <= plan['lowerBoundMinimum']:
                    status = 'thresholds-not-met'
                else: reasons.append('interval-does-not-resolve-threshold')
            groups.append({'partition': partition, 'primaryGroup': group, 'intendedEpisodes': len(rows),
                           'eligibleEpisodes': len(eligible), 'status': status, 'reasonCodes': reasons,
                           'comparisons': comparisons})
    holdout = [g for g in groups if g['partition'] == 'holdout']
    diagnostic = ('synthetic-positive' if all(g['status'] == 'thresholds-met' for g in holdout)
                  else 'synthetic-inconclusive' if any(g['status'] == 'inconclusive' for g in holdout)
                  else 'synthetic-negative')
    if shadow is not None and (shadow['cancelled'] or shadow['rolledBack']):
        diagnostic = 'synthetic-inconclusive'
    report = {'version': 'agent-braid-synthetic-utility-report-v1',
              'pairedReceiptDigest': validated['receiptDigest'], 'planDigest': digest(plan),
              'timingFixtureDigest': digest(timing_fixtures), 'shadow': shadow,
              'episodes': records, 'groups': groups, 'diagnostic': diagnostic,
              'method': {'statistic': 'median-of-episode-medians-of-paired-cycle-ratios',
                         'resamplingUnit': 'episodeGroup', 'interval': 'percentile-bootstrap-floor-ceil',
                         'confidence': plan['confidence'], 'seed': plan['seed'],
                         'replicates': plan['replicates'], 'groupRule': 'all-primary-holdout-groups',
                         'coverageGuaranteed': False},
              'costs': {'unit': 'synthetic-tick', 'boundary': 'fixture-base-plus-advisory-overhead',
                        'fullDeploymentCosts': None, 'reason': 'not-observed'},
              'provenance': 'synthetic-simulation', 'utilityAccepted': False,
              'realWorkloadEvidence': False, 'executionAuthorization': False}
    report['receiptDigest'] = digest(report)
    return report


def validate_synthetic_utility_report(receipt, signals, operations, **kwargs):
    """Recompute the complete report; a re-signed receipt confers no authority."""
    expected = synthetic_utility_report(signals, operations, **kwargs)
    require(digest(receipt) == digest(expected), 'synthetic-report-drift')
    return deepcopy(expected)
