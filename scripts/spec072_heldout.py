# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 T010 (REQ-008, REQ-011): one command for the held-out evaluation of A0, A1 and A2.

It first checks the protocol freeze (``lightning_runner.check_protocol_freeze``) and that the development evidence
is the one the freeze records, then resolves the three preregistered arms from ``evidence/development-arms.json``:

- A0: the ``final`` analyze guidance of this checkout, which must be the seed both arms optimized;
- A1: the best APO candidate body and A2: the best GEPA candidate body, read by sha256 from the laboratory run
  stores (``RunStore.candidate_text``) and verified against that sha256.

The exploratory arms E1/E2 are development-only (Amendment 1 item 6) and never run here.

With ``--execute`` each arm runs once on the held-out set (10 cases x 3 repetitions, ``claude-code`` only,
Amendment 1), model pinned, subscription route, with the plugin built once per arm (``build_candidate('final')``
plus ``candidate_plugin`` for A1/A2). A run id is recorded in the evidence before its run starts; a recorded arm is
resumed if unfinished and never run again once complete. When all three arms are complete the analysis plan is
applied (per host and arm: D4 verdict from ``summarize``, Wilson 95 % intervals, schema validity and canary hits;
paired per-prompt comparison of A1 and A2 against A0 with an exact two-sided sign test; the H1 rule) and the
SPEC-049 pair (A = A0, C = A2) is written through ``lightning_evaluation.spec049_pair``.

Without ``--execute`` it prints the plan and its cost and launches nothing::

    .venv-speckit/bin/python -m scripts.spec072_heldout            # plan and cost only
    .venv-speckit/bin/python -m scripts.spec072_heldout --execute  # runs (owner yes required)

The credential is ``CLAUDE_CODE_OAUTH_TOKEN`` from the environment or the Keychain item the development script
uses; it is never printed. Paid-route variables are refused (``lightning_runner.parent_gate``). The evidence holds
hashes, counts, verdicts and run ids only, never prompt, response or skill text.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from math import ceil, comb
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid import lightning_arm as arm_mod  # noqa: E402
from agent_braid import lightning_config as config  # noqa: E402
from agent_braid import lightning_evaluation as evaluation  # noqa: E402
from agent_braid import lightning_reward as reward_mod  # noqa: E402
from agent_braid import lightning_runner as runner  # noqa: E402
from agent_braid import lightning_store as store_mod  # noqa: E402
from agent_braid import plugin_registry as registry  # noqa: E402
from agent_braid.lightning_hosts import Secrets, utc_now  # noqa: E402
from agent_braid.lightning_resources import sha256_text, split_skill  # noqa: E402
from scripts import spec072_development_arms as dev  # noqa: E402

SPEC = 'specs/072-lightning-prompt-optimization'
DEVELOPMENT = f'{SPEC}/evidence/development-arms.json'
OUT = f'{SPEC}/evidence/heldout-arms.json'
REGISTRATION_OUT = f'{SPEC}/evidence/heldout-registration.json'
REPORT_OUT = f'{SPEC}/evidence/heldout-evaluation-record.json'
HOST = dev.HOST
REQUIRED_HOSTS = evaluation.REQUIRED_HOSTS
REPETITIONS = dev.REPETITIONS
SECONDS_PER_ROLLOUT = dev.SECONDS_PER_ROLLOUT
ARMS = ('A0', 'A1', 'A2')
DEVELOPMENT_RUNS = {'A1': 'apo', 'A2': 'gepa'}  # E1/E2 are development-only and never resolved here
ROLES = {'A0': 'baseline', 'A1': 'apo-secondary-descriptive', 'A2': 'gepa-primary'}
FORBIDDEN_KEYS = ('"parsedAttempts"', '"request"', '"prompt"', '"report"', '"skillText"', '"body"')
# Refusals that stop an arm for good (protocol stopping rules: paid route, leaked credential); a resume would hide them.
SAFETY_REFUSALS = ('route-unverified', 'credential-leak')
MAX_CANARY_HITS = 100_000


class HeldoutError(ValueError):
    """Refusal with a fixed code; the message never carries prompt, response or skill text."""

    def __init__(self, message: str, code: str):
        self.code = code
        super().__init__(message)


# --- arms ------------------------------------------------------------------------------------------------------


def check_development(root: Path) -> dict:
    """The development evidence, required to be the file the protocol freeze records."""
    freeze = json.loads((root / runner.PROTOCOL_FREEZE).read_text())
    raw = (root / DEVELOPMENT).read_bytes()
    bound = freeze.get('developmentEvidence', {})
    if bound.get('path') != DEVELOPMENT or hashlib.sha256(raw).hexdigest() != bound.get('sha256'):
        raise HeldoutError('The development evidence differs from the one the freeze records',
                           'development-evidence-changed')
    return json.loads(raw)


def resolve_arms(home: Path, root: Path, development: dict, target: str) -> dict:
    """A0, A1 and A2 with their candidate hashes and full skill texts (the texts never reach the evidence)."""
    raw = (root / target).read_text(encoding='utf-8')
    front, body = split_skill(raw)
    runs = development.get('runs', {})
    for name in DEVELOPMENT_RUNS.values():
        run = runs.get(name)
        if not isinstance(run, dict) or not run.get('runId') or not run.get('bestSha256'):
            raise HeldoutError(f'The development evidence has no finished {name} arm', 'development-arm-missing')
        if run.get('stop') or run.get('refusal'):
            raise HeldoutError(f'The {name} development arm did not finish', 'development-arm-missing')
        source = run.get('source', {})
        if source.get('arm') != 'final' or run.get('seedSha256') != sha256_text(body) \
                or source.get('seedSkillSha256') != sha256_text(raw):
            raise HeldoutError('The checkout guidance is not the seed the arms optimized', 'a0-source-drift')
    arms = {'A0': {'arm': 'A0', 'role': ROLES['A0'], 'candidateSha256': sha256_text(body),
                   'skillSha256': sha256_text(raw), 'developmentRun': development.get('seedRun'),
                   'skillText': raw}}
    for label, name in DEVELOPMENT_RUNS.items():
        run = runs[name]
        sha = run['bestSha256']
        try:
            text = store_mod.RunStore(home, run['runId']).candidate_text(sha)
        except store_mod.StoreError as exc:
            raise HeldoutError(f'The best {name} candidate cannot be read from run {run["runId"]}: {exc.code}',
                               exc.code) from exc
        if sha256_text(text) != sha:
            raise HeldoutError(f'The best {name} candidate does not match its sha256', 'candidate-hash-mismatch')
        skill = front + text
        arms[label] = {'arm': label, 'role': ROLES[label], 'candidateSha256': sha, 'skillSha256': sha256_text(skill),
                       'developmentRun': run['runId'], 'skillText': skill}
    return arms


def public(arm: dict) -> dict:
    return {k: v for k, v in arm.items() if k != 'skillText'}


# --- plan ------------------------------------------------------------------------------------------------------


def heldout_config() -> dict:
    return config.build(dev.answers('baseline'))


def plan(root: Path, arms: dict, recorded: dict, home: Path, model: str, freeze: dict) -> dict:
    work = runner.plan(heldout_config(), 'held-out', root)
    per_arm = work['withinBudget']
    rows = {}
    for label in ARMS:
        run_id = recorded.get(label, {}).get('runId')
        rows[label] = {**public(arms[label]), 'runId': run_id, 'state': arm_state(home, run_id, per_arm)}
    pending = sum(per_arm - row['state']['completed'] for row in rows.values())
    return {'task': 'SPEC-072 T010 held-out evaluation (REQ-008)', 'promptSet': 'held-out', 'host': HOST,
            'requiredHosts': list(REQUIRED_HOSTS), 'model': model, 'cases': work['cases'],
            'repetitions': work['repetitions'], 'rolloutsPerArm': per_arm, 'totalRollouts': per_arm * len(ARMS),
            'pendingRollouts': pending, 'secondsPerRollout': SECONDS_PER_ROLLOUT,
            'roughMinutes': ceil(pending * SECONDS_PER_ROLLOUT / 60),
            'route': 'subscription (no extra cash)', 'arms': rows, 'protocolFreeze': freeze,
            'excluded': 'E1/E2 are development-only (Amendment 1 item 6)', 'executionAuthorization': False}


def scored_results(store: store_mod.RunStore) -> dict[str, dict]:
    """The FIRST attempt result per rollout id that is not a quota stop. A refused rollout scores as a failed
    attempt; the runner retries refused rollouts on resume, and a retry never replaces the first result, so a
    quota stop cannot give one arm a second chance the others did not get."""
    first: dict[str, dict] = {}
    for record in store.read('result'):
        if record.value['stop'] is None:
            first.setdefault(record.value['rolloutId'], record.value)
    return first


def arm_state(home: Path, run_id: str | None, planned: int) -> dict:
    """``pending`` (no run), ``resume`` (a run that stopped short), ``complete`` (never run again) or ``refused``
    (a safety refusal, which no resume or analysis may pass). A rollout counts once it has an attempt result that is
    not a quota stop (``scored_results``)."""
    if not run_id:
        return {'status': 'pending', 'completed': 0}
    store = store_mod.RunStore(home, run_id)
    if not store.root.exists():
        return {'status': 'pending', 'completed': 0}
    store.manifest()
    results = scored_results(store)
    done = min(len(results), planned)
    safety = sorted({r['refusal'] for r in results.values() if r['refusal'] in SAFETY_REFUSALS})
    if safety:
        return {'status': 'refused', 'completed': done, 'refusal': safety[0]}
    return {'status': 'complete' if done >= planned else 'resume', 'completed': done}


def check_run_candidate(home: Path, run_id: str, skill_sha256: str) -> None:
    """A recorded run may only ever have evaluated its arm's candidate (checked before resuming and before scoring)."""
    seen = {r.candidate_sha256 for r in store_mod.RunStore(home, run_id).read('rollout')}
    if seen - {skill_sha256}:
        raise HeldoutError(f'Run {run_id} did not evaluate its arm candidate', 'arm-candidate-mismatch')


# --- analysis (pure, stdlib only) ------------------------------------------------------------------------------


def sign_test(improved: int, worsened: int) -> float:
    """Exact two-sided sign test over the prompts that changed; 1.0 when none did."""
    n = improved + worsened
    if n == 0:
        return 1.0
    k = min(improved, worsened)
    tail = sum(comb(n, i) for i in range(k + 1))
    return min(1.0, 2 * tail / 2 ** n)


def paired(base: list[dict], other: list[dict]) -> dict:
    """Per held-out prompt, first-attempt successes over repetitions in ``other`` versus ``base``."""
    def counts(vectors):
        out: dict[str, int] = {}
        for v in vectors:
            out[v['caseId']] = out.get(v['caseId'], 0) + bool(v['validFirstAttempt'])
        return out
    a, b = counts(base), counts(other)
    cases = sorted(set(a) | set(b))
    improved = sum(b.get(c, 0) > a.get(c, 0) for c in cases)
    worsened = sum(b.get(c, 0) < a.get(c, 0) for c in cases)
    return {'prompts': len(cases), 'improved': improved, 'unchanged': len(cases) - improved - worsened,
            'worsened': worsened, 'signTestPTwoSided': round(sign_test(improved, worsened), 6)}


def h1_rule(a0: dict, a2: dict) -> dict:
    """The protocol's decision rule per required host; an arm with a canary hit is invalidated (item 5)."""
    per_host = {}
    for host in REQUIRED_HOSTS:
        base = a0['summary']['hosts'][host]['verdict'] if a0['canaryHits'] == 0 else 'invalidated'
        primary = a2['summary']['hosts'][host]['verdict'] if a2['canaryHits'] == 0 else 'invalidated'
        if base == 'meets':
            per_host[host] = 'not-assessable'
        elif base == 'misses' and primary == 'meets':
            per_host[host] = 'supported'
        else:
            per_host[host] = 'not-supported'
    values = set(per_host.values())
    overall = ('not-assessable' if 'not-assessable' in values
               else 'supported' if values == {'supported'} else 'not-supported')
    return {'outcome': overall, 'hosts': per_host}


def analyze_arm(vectors: list[dict], cases: int, repetitions: int) -> dict:
    from scripts import spec069_scoring as scoring
    summary = scoring.summarize({HOST: vectors}, REQUIRED_HOSTS, cases, repetitions)
    trials = len(vectors)
    valid = sum(bool(v['schemaValid']) for v in vectors)
    host = summary['hosts'][HOST]
    return {'summary': summary, 'canaryHits': sum(v['canaryHits'] for v in vectors),
            'schemaValidity': {'valid': valid, 'trials': trials,
                               'rate': round(valid / trials, 6) if trials else None},
            'intervals': {HOST: {'firstAttempt': host.get('firstAttemptInterval'),
                                 'withinRetry': host.get('withinRetryInterval')}}}


def analysis(vectors: dict[str, list[dict]], cases: int, repetitions: int) -> dict:
    arms = {label: analyze_arm(vectors[label], cases, repetitions) for label in ARMS}
    comparisons = {f'{label}-vs-A0': {HOST: paired(vectors['A0'], vectors[label])} for label in ('A1', 'A2')}
    return {'arms': arms, 'paired': comparisons, 'h1': h1_rule(arms['A0'], arms['A2']),
            'notes': ['A1 (APO) is descriptive and never changes H1',
                      'interval overlap and the sign test are reported but do not change the rule',
                      'a canary hit in a held-out run invalidates that arm']}


# --- reading a held-out run (after it ran) ---------------------------------------------------------------------


def replay_reward(result: dict, case: dict, canary_hit: bool, scoring, scoring_sha: str) -> dict:
    """The stored reward of ``result``, replayed and verified against its ``rewardSha256``. The reward event only
    says whether the canary was hit; the hashed reward carries the runner's exact count (stdout plus tool-call
    occurrences), so for a hit the count is recovered as the one that reproduces the stored hash."""
    reward = reward_mod.replay(result['rolloutId'], case, result['parsedAttempts'], canary_hits=int(canary_hit),
                               components=['schema', 'd4', 'canary'], scoring=scoring, scoring_sha256=scoring_sha)
    for count in range(1, MAX_CANARY_HITS + 1) if canary_hit else (0,):
        reward['canaryHits'] = count  # the count changes no other field once it is above zero
        if reward_mod.reward_sha256(reward) == result['rewardSha256']:
            return reward
    raise HeldoutError(f'Rollout {result["rolloutId"]} does not replay to its stored reward', 'replay-mismatch')


def run_vectors(home: Path, root: Path, run_id: str, skill_sha256: str) -> list[dict]:
    """Per-rollout D4 vectors of a finished held-out run, re-scored from its content-free parsed attempts."""
    from scripts import spec069_scoring as scoring
    store = store_mod.RunStore(home, run_id)
    check_run_candidate(home, run_id, skill_sha256)
    cases = {c['id']: c for c in json.loads((root / runner.PROMPT_FILES['held-out']).read_text())['cases']}
    hit = {event.rollout_id for event in store.read('event')
           if event.event_type == 'reward' and event.data['reward']['reason'] == 'canary-hit'}
    scoring_sha = reward_mod.check_scoring(root)
    out = []
    for rollout_id, result in sorted(scored_results(store).items()):
        if result['promptSet'] != 'held-out':
            raise HeldoutError(f'Run {run_id} is not a held-out run', 'prompt-set-mismatch')
        host, case_id = rollout_id.split('.')[:2]
        if result['refusal'] is not None:  # a refused rollout is a failed attempt, as in development re-scoring
            out.append({'host': host, 'caseId': case_id, 'repetition': result['repetition'],
                        'validFirstAttempt': False, 'validWithinRetry': False, 'schemaValid': False,
                        'canaryHits': 0})
            continue
        reward = replay_reward(result, cases[case_id], rollout_id in hit, scoring, scoring_sha)
        out.append({'host': host, 'caseId': case_id, 'repetition': result['repetition'],
                    'validFirstAttempt': reward['d4FirstAttempt'], 'validWithinRetry': reward['d4WithinRetry'],
                    'schemaValid': reward['schemaValid'], 'canaryHits': reward['canaryHits']})
    return [v for v in out if v['host'] == HOST]


def pair(result: dict, arms: dict, root: Path, protocol_sha256: str, costs: dict) -> tuple:
    def arm_input(label):
        return {'arm': label, 'candidateSha256': arms[label]['candidateSha256'],
                'canaryHits': result['arms'][label]['canaryHits'], 'summary': result['arms'][label]['summary']}
    registration, report = evaluation.spec049_pair(
        baseline=arm_input('A0'), primary=arm_input('A2'),
        heldout_sha256=reward_mod.frozen_hashes(root)[runner.PROMPT_FILES['held-out']],
        protocol_sha256=protocol_sha256, costs=costs)
    if report.to_dict()['h1'] != result['h1']:
        raise HeldoutError('The SPEC-049 pair disagrees with the protocol rule', 'h1-mismatch')
    return registration, report


# --- evidence --------------------------------------------------------------------------------------------------


def assert_content_free(text: str, arms: dict, secrets: Secrets) -> None:
    """Refuse evidence that carries a credential, an attempt payload key or any line of a skill text."""
    secrets.assert_clean('held-out evidence', text)
    for key in FORBIDDEN_KEYS:
        if key in text:
            raise HeldoutError(f'Evidence carries a content field {key}', 'evidence-not-content-free')
    for arm in arms.values():
        for line in arm['skillText'].splitlines():
            line = line.strip()
            # the evidence is JSON: a line with quotes, backslashes or tabs appears there escaped
            if len(line) >= 40 and (line in text or json.dumps(line, ensure_ascii=False)[1:-1] in text):
                raise HeldoutError(f'Evidence carries {arm["arm"]} skill text', 'evidence-not-content-free')


def write_evidence(root: Path, record: dict, arms: dict, secrets: Secrets) -> Path:
    text = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False, default=str) + '\n'
    assert_content_free(text, arms, secrets)
    path = root / OUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def load_evidence(root: Path) -> dict:
    path = root / OUT
    return json.loads(path.read_text()) if path.is_file() else {}


def new_run_id(label: str) -> str:
    return f'heldout-{label.lower()}-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


HELDOUT_OUTPUTS = frozenset({OUT, REGISTRATION_OUT, REPORT_OUT})


def dirty_paths(root: Path) -> set[str]:
    """Working-tree changes (tracked or untracked), repository-relative."""
    text = subprocess.run(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=all'],
                          capture_output=True, text=True, check=True).stdout
    return {line[3:].strip() for line in text.splitlines() if line.strip()}


def build_allow_dirty(root: Path) -> bool:
    """The build needs a clean tree. This command's own evidence files (written before the first rollout so a stop
    can resume) are the only change it tolerates; anything else is refused."""
    dirty = dirty_paths(root)
    if dirty - HELDOUT_OUTPUTS:
        raise HeldoutError('Commit or remove these changes before the held-out run: '
                           + ', '.join(sorted(dirty - HELDOUT_OUTPUTS)), 'dirty-checkout')
    return bool(dirty)


def build_plugin(label: str, skill_text: str, work: Path) -> Path:
    from scripts import spec069_native_runs as driver
    cache = Path(os.environ.get('TMPDIR', '/tmp')) / 'agent-braid-lightning-build-cache'  # as lightning_runner.run
    base = driver.build_candidate('final', work, cache, build_allow_dirty(ROOT))[0]
    return base if label == 'A0' else arm_mod.candidate_plugin(base, skill_text, work / 'arm-candidate')  # build_candidate already writes work/candidate


def execute_arms(home: Path, root: Path, arms: dict, record: dict, *, cfg: dict, models: dict, environ: dict,
                 secrets: Secrets, planned: int, run=runner.run, build=build_plugin) -> int:
    """Run each arm once, in order; record the run id before it starts; resume a stopped arm; skip a complete one."""
    for label in ARMS:
        entry = record['arms'][label]
        recorded = entry.get('state') or {}
        state = arm_state(home, entry.get('runId'), planned)
        if state['status'] == 'pending' and entry.get('runId') and recorded.get('completed', 0) > 0:
            raise HeldoutError(f'The recorded {label} run {entry["runId"]} has rollouts but no store under this '
                               'home; refusing to run the arm again', 'run-store-missing')
        if state['status'] != 'pending':
            check_run_candidate(home, entry['runId'], arms[label]['skillSha256'])
        entry['state'] = state
        if (entry.get('status') or {}).get('refusal') in SAFETY_REFUSALS:
            state = entry['state'] = {**state, 'status': 'refused', 'refusal': entry['status']['refusal']}
        if state['status'] == 'refused':
            write_evidence(root, record, arms, secrets)
            return 1  # a safety refusal stops the arm; neither a resume nor the analysis may pass it
        if state['status'] == 'complete':
            continue  # never re-run a completed arm
        run_id = entry.get('runId') or new_run_id(label)
        entry['runId'] = run_id
        write_evidence(root, record, arms, secrets)  # the id is on disk before any rollout
        resume = state['status'] == 'resume'
        try:
            with tempfile.TemporaryDirectory(prefix='lightning-heldout-') as tmp:
                plugin = build(label, arms[label]['skillText'], Path(tmp))
                status = run(home, cfg, run_id=run_id, resume=resume, prompt_set='held-out', plugin_dir=plugin,
                             environ=environ, arm='final', models=models, skill_text=arms[label]['skillText'])
        except runner.RunnerError as exc:
            status = {'runId': run_id, 'refusal': exc.code, 'stop': None}
        except (subprocess.CalledProcessError, ValueError, OSError) as exc:
            status = {'runId': run_id, 'refusal': 'arm-error', 'stop': None, 'detail': type(exc).__name__}
        entry['status'] = status
        entry['state'] = arm_state(home, run_id, planned)
        record['invocations'][-1]['runs'][label] = {'runId': run_id, 'resumed': resume, 'stop': status.get('stop'),
                                                    'refusal': status.get('refusal')}
        write_evidence(root, record, arms, secrets)
        if status.get('stop') or status.get('refusal') or entry['state']['status'] != 'complete':
            return 1  # a quota stop ends the phase; rerun the same command to resume
    return 0


def finish_analysis(home: Path, root: Path, arms: dict, record: dict, dev_runs: dict, summary: dict,
                    protocol_sha: str, secrets: Secrets) -> None:
    """Score the three complete arms, apply the analysis plan and write the SPEC-049 pair (A = A0, C = A2)."""
    vectors = {label: run_vectors(home, root, record['arms'][label]['runId'], arms[label]['skillSha256'])
               for label in ARMS}
    result = analysis(vectors, summary['cases'], summary['repetitions'])
    costs = {'A': {'heldOutRollouts': len(vectors['A0']),
                   'developmentRollouts': dev_runs['baseline']['completed'], 'optimizerCalls': 0},
             'C': {'heldOutRollouts': len(vectors['A2']), 'developmentRollouts': dev_runs['gepa']['rollouts'],
                   'optimizerCalls': dev_runs['gepa']['optimizerCalls']}}
    registration, report = pair(result, arms, root, protocol_sha, costs)
    for relative, rec in ((REGISTRATION_OUT, registration), (REPORT_OUT, report)):
        assert_content_free(rec.canonical_bytes.decode('utf-8'), arms, secrets)
        (root / relative).write_bytes(rec.canonical_bytes)
    record['analysis'] = result
    record['pair'] = {'registration': {'path': REGISTRATION_OUT, 'sha256': registration.sha256},
                      'evaluationRecord': {'path': REPORT_OUT, 'sha256': report.sha256}}


def main(argv: list[str] | None = None, root: Path = ROOT) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--home', type=Path, default=dev.DEFAULT_HOME, help='dedicated private laboratory home')
    parser.add_argument('--model', default=arm_mod.DEFAULT_MODEL, help='pinned Claude Code model')
    parser.add_argument('--execute', action='store_true', help='run on the subscription (spends quota)')
    args = parser.parse_args(argv)
    home = args.home.expanduser().absolute()

    try:
        protocol_sha = runner.check_protocol_freeze(root)  # REQ-001: before anything else
    except runner.RunnerError as exc:
        print(json.dumps({'protocolFreeze': {'status': 'refused', 'code': exc.code}}, indent=2))
        print(f'refused ({exc.code}): {exc}', file=sys.stderr)
        return 2
    freeze = {'status': 'frozen', 'protocolSha256': protocol_sha}
    try:
        development = check_development(root)
        if args.model != development.get('pinnedModel'):  # Amendment 1 item 4: the arms' model, for every rollout
            raise HeldoutError('The model differs from the one the development arms pinned', 'model-not-pinned')
        target = heldout_config()['target']['path']
        arms = resolve_arms(home, root, development, target)
    except HeldoutError as exc:
        print(json.dumps({'protocolFreeze': freeze, 'refusal': exc.code}, indent=2))
        print(f'refused ({exc.code}): {exc}', file=sys.stderr)
        return 2
    previous = load_evidence(root)
    summary = plan(root, arms, previous.get('arms', {}), home, args.model, freeze)
    print(json.dumps({'plan': summary, 'execute': args.execute}, indent=2))
    if not args.execute:
        print('dry run: nothing launched. Add --execute to run.', file=sys.stderr)
        return 0

    try:
        runner.parent_gate(dict(os.environ))
    except runner.RunnerError as exc:
        print(f'refused ({exc.code}): {exc}. Run it from a terminal without those variables.', file=sys.stderr)
        return 2
    token = os.environ.get(dev.TOKEN) or dev.keychain_token()
    if not token:
        print(f'refused: {dev.TOKEN} is not set and the Keychain has no {dev.KEYCHAIN_SERVICE!r} item.',
              file=sys.stderr)
        return 2
    environ = dict(os.environ, **{dev.TOKEN: token})
    secrets = Secrets([token])
    home.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    preview = registry.plan_setup(home, [], lightning='lab')
    registry.apply(home, preview, preview['previewDigest'])
    cfg = dev.apply_profile(home, 'baseline')

    record = {'evidenceVersion': 1, 'task': summary['task'], 'label': 'host-run', 'promptSet': 'held-out',
              'host': HOST, 'requiredHosts': list(REQUIRED_HOSTS), 'pinnedModel': args.model,
              'protocolSha256': protocol_sha,
              'heldOutSha256': reward_mod.frozen_hashes(root)[runner.PROMPT_FILES['held-out']],
              'developmentEvidenceSha256': hashlib.sha256((root / DEVELOPMENT).read_bytes()).hexdigest(),
              'generatedAt': utc_now(), 'executionAuthorization': False,
              'arms': {label: {**previous.get('arms', {}).get(label, {}), **public(arms[label])} for label in ARMS},
              'invocations': [*previous.get('invocations', []), {'generatedAt': utc_now(), 'runs': {}}],
              'analysis': None, 'pair': None}
    try:
        code = execute_arms(home, root, arms, record, cfg=cfg, models={HOST: args.model}, environ=environ,
                            secrets=secrets, planned=summary['rolloutsPerArm'])
        if code == 0:
            finish_analysis(home, root, arms, record, development['runs'], summary, protocol_sha, secrets)
    except HeldoutError as exc:
        record['refusal'] = exc.code
        print(f'refused ({exc.code}): {exc}', file=sys.stderr)
        code = 2
    path = write_evidence(root, record, arms, secrets)
    print(json.dumps({'evidence': str(path), 'h1': (record['analysis'] or {}).get('h1'),
                      'arms': {k: {'runId': v.get('runId'), 'state': v.get('state')}
                               for k, v in record['arms'].items()}}, indent=2))
    return code


if __name__ == '__main__':
    sys.exit(main())
