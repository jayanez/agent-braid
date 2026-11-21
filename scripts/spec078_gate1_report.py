# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T006 (REQ-008 / SC-008): the Gate 1 report of one arm's run on ``v2-test``.

Re-scores the stored results of the run with the unchanged SPEC-069 scorer, applies the preregistered analysis
(``lightning_heldout_v2.analyse``, OD-1 with the zero-prompt review) and adds the run's host, model, key-source,
canary, stop and trace counts. The review file maps each 0/3 prompt to ``model`` or ``instrument`` with a short
rationale; it is written by the reviewer after reading only that prompt's redacted transcripts. No prompt text,
transcript or model text is written here, only ids, classes, counts and the scorer's first reason per failure.

    python -m scripts.spec078_gate1_report --run-id <id> [--home <lab home>] [--review <review.json>] \\
        > specs/078-lightning-heldout-v2/evidence/gate1-a0.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

from agent_braid import lightning_heldout_v2 as v2
from agent_braid import lightning_store as store
from scripts import spec069_scoring as scoring

ROOT = Path(__file__).resolve().parents[1]
LAB = Path.home() / '.local/state/agent-braid/lightning-lab'
SCHEMA = 'braid-lightning-v2-gate1/v0.1'


def report(home: Path, run_id: str, review: dict | None = None) -> dict:
    sha = v2.check_freeze(ROOT, 'v2-test')
    run = store.RunStore(home, run_id)
    cases = json.loads((ROOT / v2.PROMPT_FILES['v2-test']).read_text())['cases']
    by_id = {c['id']: c for c in cases}
    results = [r.value for r in run.read('result')]
    rollouts = {r.rollout_id: r for r in run.read('rollout')}
    if {r['promptSetSha256'] for r in results} != {sha}:
        raise SystemExit('refused: the run is not on the frozen v2-test split')
    trials: dict[str, list] = {c['id']: [None] * 3 for c in cases}
    failures = []
    for result in sorted(results, key=lambda r: r['rolloutId']):
        case_id = result['rolloutId'].split('.')[1]
        if result['refusal'] or result['stop']:
            valid, reason = False, result['refusal'] or result['stop']
        else:
            score = scoring.score_case(by_id[case_id], result['parsedAttempts'])
            valid, reason = score['validFirstAttempt'], (score['reasons'] or [None])[0]
        trials[case_id][result['repetition'] - 1] = valid
        if not valid:
            failures.append({'rolloutId': result['rolloutId'], 'reason': reason})
    if any(None in t for t in trials.values()):
        raise SystemExit('refused: the run does not cover every prompt three times')
    rewards = [e.data['reward'] for e in run.read('event') if e.event_type == 'reward']
    zero = {cid for cid, t in trials.items() if not any(t)}
    if review is not None and set(review) != zero:
        raise SystemExit('refused: the review must name exactly the 0/3 prompts')
    body = v2.analyse(cases, trials, {k: v['classification'] for k, v in (review or {}).items()})
    body['review'] = dict(review or {})
    candidates = {r.candidate_sha256 for r in rollouts.values()}
    return {
        'schema': SCHEMA, 'runId': run_id, 'arm': 'A0', 'promptSet': 'v2-test', 'promptSetSha256': sha,
        'freezeCommit': v2.load_freeze(ROOT)['commit'], 'frozenFiles': v2.load_freeze(ROOT)['files'], 'candidateSha256': sorted(candidates),
        'skillSha256': hashlib.sha256((ROOT / v2.SKILL).read_bytes()).hexdigest(),
        'rollouts': len(results), 'startedAt': min(r['startedAt'] for r in results),
        'endedAt': max(r['endedAt'] for r in results),
        'hostVersions': dict(Counter(r['hostVersion'] for r in results)),
        'models': dict(Counter(r['model'] for r in results)),
        'keySources': dict(Counter(r['keySource'] for r in results)),
        'refusals': dict(Counter(r['refusal'] for r in results if r['refusal'])),
        'stops': dict(Counter(r['stop'] for r in results if r['stop'])),
        'canaryHits': sum(1 for r in rewards if r['reason'] == 'canary-hit'),
        'traceRecords': sum(1 for line in run.read_content() if 'record' in line),
        'analysis': body, 'failures': failures, 'executionAuthorization': False,
    }


CAUSES = ('guidance-gap', 'prompt-defect', 'scorer-defect')


def _first_kind(record: dict) -> str | None:
    for call in record['toolCalls']:
        if call['tool'].endswith('analyze-work'):
            found = re.search(r'"kind": "(\w+)"', call['args'])
            return found.group(1) if found else 'unparsed'
    return None


def diagnose(home: Path, run_id: str, causes: dict) -> dict:
    """Per-attempt request kind, Bash attempt and validity over the whole run, and the cause of each 0/3 prompt.

    Reads the redacted trace records (joined by attemptId); writes no prompt, transcript or model text."""
    run = store.RunStore(home, run_id)
    cases = {c['id']: c for c in json.loads((ROOT / v2.PROMPT_FILES['v2-test']).read_text())['cases']}
    traces = {line['record']['attemptId']: line['record'] for line in run.read_content() if 'record' in line}
    table, zero = Counter(), {}
    for result in sorted((r.value for r in run.read('result')), key=lambda r: r['rolloutId']):
        case_id = result['rolloutId'].split('.')[1]
        record = traces[result['attemptId']]
        score = scoring.score_case(cases[case_id], result['parsedAttempts'])
        kind = _first_kind(record)
        bash = any(call['tool'] == 'Bash' for call in record['toolCalls'])
        table[(cases[case_id]['expect']['kind'], kind or 'none', bash, score['validFirstAttempt'])] += 1
        if case_id in causes:
            zero.setdefault(case_id, {'class': cases[case_id]['class'], **causes[case_id], 'repetitions': []})
            zero[case_id]['repetitions'].append({'repetition': result['repetition'], 'requestKind': kind,
                                                 'bashAttempted': bash, 'scorerReason': score['reasons'][0]})
    if set(zero) != set(causes) or any(c['cause'] not in CAUSES for c in causes.values()):
        raise SystemExit('refused: the causes must name the 0/3 prompts with a known cause')
    rows = [{'expectedKind': e, 'firstRequestKind': k, 'bashAttempted': b, 'valid': v, 'attempts': n}
            for (e, k, b, v), n in sorted(table.items(), key=str)]
    return {'schema': 'braid-lightning-v2-gate1-diagnosis/v0.1', 'runId': run_id, 'attemptsByRequestKind': rows,
            'zeroPrompts': dict(sorted(zero.items())), 'executionAuthorization': False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--home', type=Path, default=LAB)
    parser.add_argument('--review', type=Path, help='JSON: {caseId: {classification, rationale}}')
    parser.add_argument('--diagnose', type=Path, help='JSON: {caseId: {cause, evidence}}; prints the diagnosis')
    args = parser.parse_args(argv)
    if args.diagnose:
        print(json.dumps(diagnose(args.home, args.run_id, json.loads(args.diagnose.read_text())), indent=1,
                         sort_keys=True))
        return 0
    review = json.loads(args.review.read_text()) if args.review else None
    print(json.dumps(report(args.home, args.run_id, review), indent=1, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
