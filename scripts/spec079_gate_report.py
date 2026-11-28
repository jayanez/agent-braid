# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T008 (REQ-009): the gate report of the fixed-tool arm on ``v4-test``.

Re-scores the stored results of the run with the unchanged SPEC-069 scorer, applies the preregistered analysis
(``lightning_heldout_v2.analyse``, OD-1) and adds the H1, H3 and H4 counts of the evaluation protocol: ``units``
usage per class and overall, ``units-cannot-answer-independence`` refusals and their ``aim`` retries, rollouts
that call ``analyze`` and never ``analyze-work``, the ``validWithinRetry`` passing share, the run's config digest
and how many traced rollouts made no tool call or used ``ToolSearch``, ``Skill`` and ``analyze-work``. A missing rollout
result counts as a failed rollout and a repeated ``rolloutId`` keeps its last result. No prompt text or transcript
is written, only ids, classes, counts and the scorer's first reason per failure; that reason is scorer text and
can quote a refusal or a request field value.

    python -m scripts.spec079_gate_report --run-id <id> [--home <lab home>] [--review <review.json>] \\
        > specs/079-kind-choice-tool-fix/evidence/gate-v4-report.json
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from agent_braid import lightning_heldout_v2 as v2
from agent_braid import lightning_heldout_v4 as v4
from agent_braid import lightning_store as store
from scripts import spec069_scoring as scoring

ROOT = Path(__file__).resolve().parents[1]
LAB = Path.home() / '.local/state/agent-braid/lightning-lab'
SCHEMA = 'braid-lightning-v4-gate/v0.1'
PROMPT_SET = 'v4-test'
REPETITIONS = 3
REDIRECT = 'units cannot report independence'  # the T001 refusal text, as summarised in parsed attempts
ANALYZE_WORK, ANALYZE = 'analyze-work', 'analyze'


def _tool(name: str) -> str:
    return name.rsplit('__', 1)[-1]


def _share(passing: int, n: int) -> dict:
    low, high = v2.wilson_interval(passing, n)
    return {'passing': passing, 'of': n, 'share': passing / n, 'wilson95': [low, high]}


def invocation(tool_lists: list[list[str]]) -> dict:
    """How many rollouts reached each step towards ``analyze-work``, from the recorded tool names alone."""
    names = [{_tool(name) for name in tools} for tools in tool_lists]
    return {'tracedRollouts': len(names),
            'noToolCall': sum(1 for n in names if not n),
            'toolSearch': sum(1 for n in names if 'ToolSearch' in n),
            'skill': sum(1 for n in names if 'Skill' in n),
            'analyzeWork': sum(1 for n in names if ANALYZE_WORK in n)}


def report(home: Path, run_id: str, review: dict | None = None) -> dict:
    sha = v4.check_freeze(ROOT, PROMPT_SET)  # the whole frozen record still holds
    freeze = v4.load_freeze(ROOT)
    run = store.RunStore(home, run_id)
    cases = json.loads((ROOT / v4.PROMPT_FILES[PROMPT_SET]).read_text())['cases']
    by_id = {c['id']: c for c in cases}
    results = list({r.value['rolloutId']: r.value for r in run.read('result')}.values())  # a rerun replaces
    if not results:
        raise SystemExit('refused: the run has no results')
    if {r['promptSetSha256'] for r in results} - {sha}:
        raise SystemExit('refused: the run is not on the frozen v4-test split')
    traces = {line['record']['attemptId']: line['record'] for line in run.read_content() if 'record' in line}
    first = {c['id']: [False] * REPETITIONS for c in cases}
    retry = {c['id']: [False] * REPETITIONS for c in cases}
    seen = {c['id']: [False] * REPETITIONS for c in cases}
    failures, units = [], Counter()
    redirects = redirect_recovered = analyze_only = 0
    analyze_only_by_class, units_by_class, first_kind = Counter(), Counter(), Counter()
    for result in sorted(results, key=lambda r: r['rolloutId']):
        case_id, rep = result['rolloutId'].split('.')[1], result['repetition'] - 1
        case = by_id[case_id]
        seen[case_id][rep] = True
        attempts = result['parsedAttempts']
        if result['refusal'] or result['stop']:
            valid = within = False
            reason = result['refusal'] or result['stop']
        else:
            score = scoring.score_case(case, attempts)
            valid, within = score['validFirstAttempt'], score['validWithinRetry']
            reason = (score['reasons'] or [None])[0]
        first[case_id][rep], retry[case_id][rep] = valid, within
        if not valid:
            failures.append({'rolloutId': result['rolloutId'], 'class': case['class'], 'reason': reason})
        kinds = [a.get('kind') for a in attempts]
        first_kind[kinds[0] if kinds else 'none'] += 1
        if 'units' in kinds:
            units['rollouts'] += 1
            units_by_class[case['class']] += 1
        for i, attempt in enumerate(attempts):
            if attempt.get('kind') == 'units' and REDIRECT in (attempt.get('refusalSummary') or ''):
                redirects += 1
                later = attempts[i + 1] if i + 1 < len(attempts) else None
                if later and later.get('kind') == 'aim' and later.get('accepted'):
                    redirect_recovered += 1
        tools = {_tool(c['tool']) for c in traces.get(result['attemptId'], {}).get('toolCalls', [])}
        if ANALYZE in tools and ANALYZE_WORK not in tools:
            analyze_only += 1
            analyze_only_by_class[case['class']] += 1
    missing = [f'{cid}.r{i + 1}' for cid, reps in seen.items() for i, ok in enumerate(reps) if not ok]
    for rollout in missing:  # protocol: a missing result is a failed rollout
        failures.append({'rolloutId': f'claude-code.{rollout}', 'class': by_id[rollout.split('.')[0]]['class'],
                         'reason': 'missing-result'})
    zero = {cid for cid, t in first.items() if not any(t)}
    if review is not None and set(review) != zero:
        raise SystemExit('refused: the review must name exactly the 0/3 prompts')
    body = v2.analyse(cases, first, {k: v['classification'] for k, v in (review or {}).items()})
    body['review'] = dict(review or {})
    class_sizes = Counter(c['class'] for c in cases)
    within_pass = sum(1 for t in retry.values() if sum(t) >= v2.PASS_MIN)
    first_pass = sum(1 for t in first.values() if sum(t) >= v2.PASS_MIN)
    rewards = [e.data['reward'] for e in run.read('event') if e.event_type == 'reward']
    n = len(cases) * REPETITIONS
    probe = 'kind-choice-probe'
    return {
        'schema': SCHEMA, 'runId': run_id, 'promptSet': PROMPT_SET, 'promptSetSha256': sha,
        'freezeCommit': freeze['commit'], 'pluginCommit': freeze['pluginCommit'],
        'pluginVersion': freeze.get('pluginVersion'), 'frozenFiles': freeze['files'],
        'rollouts': len(results), 'missingResults': missing,
        'startedAt': min(r['startedAt'] for r in results), 'endedAt': max(r['endedAt'] for r in results),
        'hostVersions': dict(Counter(r['hostVersion'] for r in results)),
        'models': dict(Counter(r['model'] for r in results)),
        'keySources': dict(Counter(r['keySource'] for r in results)),
        'refusals': dict(Counter(r['refusal'] for r in results if r['refusal'])),
        'stops': dict(Counter(r['stop'] for r in results if r['stop'])),
        'canaryHits': sum(1 for r in rewards if r['reason'] == 'canary-hit'),
        'analysis': body,
        'zeroPrompts': sorted(zero),
        'h1UnitsUsage': {'overall': {'rollouts': units['rollouts'], 'of': n},
                         probe: {'rollouts': units_by_class[probe], 'of': class_sizes[probe] * REPETITIONS},
                         'byClass': dict(sorted(units_by_class.items())), 'v3TestReference': '19/300'},
        'redirectRefusals': {'count': redirects, 'followedByValidAim': redirect_recovered},
        'h3AnalyzeOnly': {'overall': analyze_only, 'of': n, 'byClass': dict(sorted(analyze_only_by_class.items())),
                          'threshold': 'fewer than 6 of 300'},
        'h4ValidWithinRetry': {'withinRetry': _share(within_pass, len(cases)),
                               'firstAttempt': _share(first_pass, len(cases))},
        'firstRequestKind': dict(sorted(first_kind.items())),
        'configDigest': run.manifest()['configDigest'],
        'invocation': invocation([[c['tool'] for c in traces[r['attemptId']].get('toolCalls', [])]
                                  for r in results if r['attemptId'] in traces]),
        'failures': failures, 'executionAuthorization': False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--home', type=Path, default=LAB)
    parser.add_argument('--review', type=Path, help='JSON: {caseId: {classification, rationale}}')
    args = parser.parse_args(argv)
    review = json.loads(args.review.read_text()) if args.review else None
    print(json.dumps(report(args.home, args.run_id, review), indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
