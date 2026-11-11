# SPDX-License-Identifier: AGPL-3.0-only
# Rollout loop adapted from microsoft/agent-lightning agentlightning/controller/local_reconciler.py at commit
# bc3a9e80417d731744040df5d37117f9cc48005f (v1.0.3), Copyright (c) Microsoft Corporation, MIT License
# (LICENSES/Agent-Lightning-MIT.txt). Changes: the gateway queue and agent-class subprocess become headless host
# rollouts over a fixed prompt set; rollouts run sequentially (parallel 1) in a disposable sandboxed profile;
# the subscription route is enforced; records go to the private SPEC-070 store; no Kubernetes, no network
# listener. See docs/development/THIRD_PARTY.md.
"""Braid Lightning rollout runner (SPEC-071 REQ-003 to REQ-006, REQ-009, REQ-013).

The laboratory runs from an Agent Braid checkout: it reuses the SPEC-069 driver (plugin install, workspace
registration, fake hosts), fixture workspace and frozen scoring rules. It never calls ``execute`` or grant
paths, never starts from the MCP server, and every output carries ``executionAuthorization: false``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import lightning_hooks as hooks_mod
from . import lightning_reward as reward_mod
from . import lightning_store as store_mod
from .harness_host_claude import ENV_DENY, SUBSCRIPTION_KEY_SOURCES
from .lightning_hosts import (DeclaredLimit, HostConfig, OsSandbox, PARSERS, Profile, SafetyStop,
                              SecretLeak, Secrets, attempts_from, guard_leaks, probe_isolation, real_config_paths,
                              real_home, run_process, tool_class)
from .lightning_schema import FAILED, RESULT_SCHEMA, RUNNING, SUCCEEDED, AttemptResult, new_rollout

PROMPT_FILES = {'development': 'specs/069-aim-request-authoring/prompts/development.json',
                'held-out': 'specs/069-aim-request-authoring/prompts/held-out.json'}
# Subscription credentials read from this process's environment only (OD-1, decided 2026-11-08). OpenCode has none
# verified (OD-2): without a host-reported subscription key source it ends as route-unverified.
CREDENTIALS = {'claude-code': 'CLAUDE_CODE_OAUTH_TOKEN', 'opencode': None}
ACCEPTED_KEY_SOURCES = {'oauth'} | ({'none'} & SUBSCRIPTION_KEY_SOURCES)  # 'none': SPEC-069 fixture assumption
LIGHTNING_CANARY = 'braid-lightning-canary-' + hashlib.sha256(b'braid-lightning-canary').hexdigest()[:16]
CANARY_FILE = '.lightning-notes'  # a non-target file planted in every rollout workspace
QUOTA_PATTERNS = (
    ('weekly-stop', re.compile(r'(?i)weekly (usage )?limit')),
    ('five-hour-headroom', re.compile(r'(?i)(5|five)[- ]hour (usage )?limit|usage limit reached|rate limit')),
)


class RunnerError(ValueError):
    """A run is refused or stopped; ``code`` is from contracts/refusals.md."""

    def __init__(self, message: str, code: str):
        super().__init__(message)
        self.code = code


def utc(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def env_gate(env: dict[str, str]) -> None:
    """REQ-004: refuse a paid or redirected route before any launch. Names only, never values."""
    offending = sorted(k for k in env if k.endswith('_API_KEY') or k in ENV_DENY)
    if offending:
        raise RunnerError(f'Paid or redirected model route variables are present: {", ".join(offending)}',
                          'paid-route-refused')


# Model-provider credentials. The child environment is built from scratch and refuses any ``*_API_KEY`` (REQ-004);
# this process's own environment is checked only for provider keys, so unrelated tool keys (for example an MCP
# server's key) do not block a run but a provider key exported by mistake does.
PROVIDER_KEYS = ('ANTHROPIC_API_KEY', 'OPENAI_API_KEY', 'CODEX_API_KEY', 'GEMINI_API_KEY', 'GOOGLE_API_KEY',
                 'OPENROUTER_API_KEY', 'AWS_BEARER_TOKEN_BEDROCK')


def parent_gate(env: dict[str, str]) -> None:
    offending = sorted(k for k in env if k in PROVIDER_KEYS or k in ENV_DENY)
    if offending:
        raise RunnerError(f'Model provider route variables are present: {", ".join(offending)}', 'paid-route-refused')


def key_source_verdict(host: str, key_source: str | None) -> str | None:
    """None when the host-reported credential source is a subscription; else ``route-unverified``."""
    if host == 'claude-code' and key_source in ACCEPTED_KEY_SOURCES:
        return None
    if host == 'opencode' and key_source == 'oauth':
        return None
    return 'route-unverified'


def quota_stop(stdout: str, stderr: str) -> str | None:
    text = f'{stdout}\n{stderr}'
    for name, pattern in QUOTA_PATTERNS:
        if pattern.search(text):
            return name
    return None


def checkout_root() -> Path:
    """The laboratory needs an Agent Braid checkout (prompt sets, FREEZE, scoring rules, driver)."""
    root = Path(__file__).resolve().parents[1]
    if not (root / PROMPT_FILES['development']).is_file() or not (root / 'scripts/spec069_native_runs.py').is_file():
        raise RunnerError('The Braid Lightning laboratory runs from an Agent Braid checkout', 'lab-requires-checkout')
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def plan(config: dict, prompt_set: str, root: Path) -> dict:
    """The rollouts a run would execute, in order, within ``budget.maxRollouts``."""
    if prompt_set not in PROMPT_FILES:
        raise RunnerError('Unknown prompt set', 'config-enum')
    cases = json.loads((root / PROMPT_FILES[prompt_set]).read_text())['cases']
    rollout = config['rollout']
    order = [(host, case['id'], rep) for host in rollout['hosts'] for rep in range(1, rollout['repetitions'] + 1)
             for case in cases]
    cap = config['budget']['maxRollouts']
    return {'promptSet': prompt_set, 'hosts': list(rollout['hosts']), 'repetitions': rollout['repetitions'],
            'cases': len(cases), 'planned': len(order), 'withinBudget': min(len(order), cap),
            'maxRollouts': cap, 'parallel': rollout['parallel'], 'timeoutSeconds': rollout['timeoutSeconds'],
            'order': order[:cap], 'executionAuthorization': False}


def _fake_binary(root: Path, host: str) -> Path:
    return root / 'tests/fixtures/lightning-fake-hosts' / {'claude-code': 'claude', 'opencode': 'opencode'}[host]


def _host_binary(host: str) -> Path | None:
    found = shutil.which({'claude-code': 'claude', 'opencode': 'opencode'}[host])
    if host == 'opencode' and not found:
        candidate = Path('~/.opencode/bin/opencode').expanduser()
        found = str(candidate) if candidate.exists() else None
    return Path(found) if found else None


def _canary_hits(stdout: str, transcript) -> int:
    hits = stdout.count(LIGHTNING_CANARY)
    hits += sum(json.dumps(call.args, default=str).count(LIGHTNING_CANARY) for call in transcript.tool_calls)
    return hits


def run(home, config: dict, *, run_id: str | None = None, resume: bool = False, prompt_set: str = 'development',
        fake_hosts: bool = False, fake_variant: str = 'default', fake_key_source: str | None = 'none',
        plugin_dir: Path | None = None, hooks: hooks_mod.RolloutHooks | None = None,
        environ: dict[str, str] | None = None, arm: str = 'final', models: dict[str, str] | None = None) -> dict:
    """Run (or resume) the rollouts of ``plan``; return the run status."""
    environ = dict(os.environ if environ is None else environ)
    root = checkout_root()
    from scripts import spec069_fixture_workspace as fixture
    from scripts import spec069_native_runs as driver
    from scripts import spec069_scoring as scoring

    scoring_sha = reward_mod.check_scoring(root)
    prompt_sha = reward_mod.check_prompt_set(root, PROMPT_FILES[prompt_set])
    cases = {c['id']: c for c in json.loads((root / PROMPT_FILES[prompt_set]).read_text())['cases']}
    work = plan(config, prompt_set, root)
    label = 'pipeline-only' if fake_hosts else 'host-run'

    if resume:
        if not run_id:
            raise RunnerError('--resume needs the run id', 'resume-needs-run-id')
        store = store_mod.RunStore(home, run_id)
        store.manifest()
    else:
        run_id = run_id or 'run-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
        store = store_mod.RunStore(home, run_id)
        from .lightning_config import digest
        store.create(config_digest=digest(config))
    done = {(r.value['rolloutId']) for r in store.read('result') if r.value['refusal'] is None and r.value['stop'] is None}
    completed = len(done)

    # REQ-004: the child environment is built from scratch; the gate also checks this process's environment so a
    # paid key exported by mistake stops the run instead of being silently dropped.
    parent_gate(environ)
    secrets = Secrets()
    protected = real_config_paths(real_home())
    sandbox = OsSandbox(protected, enabled=not fake_hosts)
    profile = Profile(prefix='lightning-')
    if arm not in driver.ARMS:
        raise RunnerError('Unknown candidate arm', 'config-enum')
    status: dict = {'runId': run_id, 'label': label, 'promptSet': prompt_set, 'arm': arm, 'models': dict(models or {}), 'planned': work['withinBudget'],
                    'completedBefore': completed, 'stop': None, 'refusal': None, 'hosts': {},
                    'executionAuthorization': False}
    try:
        workdir = profile.make('work')
        if plugin_dir is None:
            plugin_dir = driver.fake_plugin(workdir) if fake_hosts else driver.build_candidate(
                arm, workdir, Path(environ.get('TMPDIR', '/tmp')) / 'agent-braid-lightning-build-cache', False)[0]
        passthrough: dict[str, str] = {}
        if fake_hosts:
            variant = fake_variant if fake_variant in driver.FAKE_VARIANTS else 'default'
            scenario = driver.build_fake_scenario(list(cases.values()), variant, scoring.reference_request)
            if fake_variant == 'canary':
                first = next(iter(cases.values()))['prompt']
                scenario[first]['text'] += ' ' + LIGHTNING_CANARY
            scenario_file = profile.make('fake') / 'scenario.json'
            scenario_file.write_text(json.dumps(scenario))
            planted = 'sk-ant-PLANTED-' + hashlib.sha256(b'planted').hexdigest()[:24]
            secrets.add(planted)
            passthrough = {'FAKE_SCENARIO': str(scenario_file), 'FAKE_VARIANT': variant,
                           'FAKE_PLANTED_SECRET': planted, 'FAKE_PYTHON': sys.executable}
            if fake_key_source is not None:
                passthrough['FAKE_KEY_SOURCE'] = fake_key_source
        candidate = root / config['target']['path']
        candidate_sha = hashlib.sha256(candidate.read_bytes()).hexdigest()
        count = completed
        for host_name in work['hosts']:
            binary = _fake_binary(root, host_name) if fake_hosts else _host_binary(host_name)
            if binary is None:
                status['hosts'][host_name] = {'status': 'declared-limit', 'limit': 'executable not found'}
                continue
            credential_name = CREDENTIALS[host_name]
            credential = environ.get(credential_name) if credential_name else None
            host = HostConfig(host_name, binary, (), credential_name or 'LIGHTNING_NO_CREDENTIAL',
                              model=(models or {}).get(host_name), fake=fake_hosts)
            ab_home = profile.make('hosts', host_name, 'agent-braid-home')
            env = driver.build_host_env(profile, host, credential or '', ab_home, passthrough)
            if not credential:
                env.pop(host.key_target, None)
            else:
                secrets.add(credential)
            env_gate(env)
            workspace = fixture.build(profile.make('hosts', host_name, 'workspace') / 'repo')
            (workspace / CANARY_FILE).write_text(f'Internal note {LIGHTNING_CANARY}\n')
            guard_leaks(f'{host_name} setup', env, [str(binary)], protected)
            if not sandbox.tool and not fake_hosts:
                raise RunnerError('No OS sandbox on this platform; refusing an unsandboxed real run', 'isolation-failed')
            try:
                probe = probe_isolation(env, Path(env['HOME']), sandbox, protected)
            except SafetyStop as exc:
                raise RunnerError(str(exc), 'isolation-failed') from exc
            version = driver.version_of(host, env, workspace, profile, protected, sandbox)
            ns = argparse.Namespace(max_turns=config['rollout']['maxTurns'], plugin_root_for={}, fake_hosts=fake_hosts)
            ns.plugin_root_for[host_name] = driver.install_plugin(host, plugin_dir, env, profile, workspace, protected,
                                                                  sandbox, ns)
            driver.write_host_policy(host, env)
            driver.register_workspace(ns.plugin_root_for[host_name], workspace, env, profile, protected, sandbox, ab_home)
            host_status = {'status': 'ran', 'version': version, 'probe': probe['sandbox'], 'rollouts': 0}
            status['hosts'][host_name] = host_status
            for (h, case_id, rep) in work['order']:
                if h != host_name:
                    continue
                rollout_id = f'{host_name}.{case_id}.r{rep}'
                if rollout_id in done:
                    continue
                if count >= work['maxRollouts']:
                    status['stop'] = 'unit-cap'
                    break
                case = cases[case_id]
                started = time.time()
                rollout = new_rollout(rollout_id, case_id, f'{host_name}.{case_id}', candidate_sha,
                                      hashlib.sha256(case['prompt'].encode()).hexdigest(), host_name, at=started,
                                      is_train=prompt_set == 'development',
                                      timeout_seconds=config['rollout']['timeoutSeconds'])
                attempt_id = f'a{int(started * 1000)}'
                running = rollout.transition(RUNNING, started, attempt_id=attempt_id)
                refusal = stop = None
                parsed, reward_sha, key_source, transcript_sha = [], None, None, hashlib.sha256(b'').hexdigest()
                model = None
                try:
                    hooks_mod.call(hooks, 'on_rollout_start', running.to_dict())
                    argv = driver.prompt_argv(host, case['prompt'], ns)
                    done_proc = run_process(argv, env, workspace, profile, protected, sandbox,
                                            config['rollout']['timeoutSeconds'], f'{host_name} {case_id}')
                    redacted = secrets.redact(done_proc.stdout)
                    secrets.assert_clean('transcript', redacted)
                    transcript_sha = hashlib.sha256(redacted.encode()).hexdigest()
                    transcript = PARSERS[host_name](done_proc.stdout)
                    key_source = transcript.key_source
                    model = transcript.models[0][:128] if transcript.models else None
                    quota = None if transcript.tool_calls else quota_stop(done_proc.stdout, done_proc.stderr)
                    if secrets.scan(done_proc.stdout + done_proc.stderr):
                        refusal = 'credential-leak'
                    elif done_proc.timed_out:
                        refusal = 'rollout-timeout'
                    elif quota:
                        stop = quota
                    elif key_source_verdict(host_name, key_source):
                        refusal = 'route-unverified'
                    elif any(tool_class(host_name, c) == 'denied' and not c.is_error for c in transcript.tool_calls):
                        raise SafetyStop(f'{host_name} {case_id}: a denied tool ran')
                    else:
                        attempts = attempts_from(transcript, host_name)
                        parsed = reward_mod.parsed_attempts(secrets.redact_json(attempts))
                        hits = _canary_hits(done_proc.stdout, transcript)
                        reward = reward_mod.compute(rollout_id, case, reward_mod.scoring_attempts(parsed),
                                                    canary_hits=hits, components=config['reward']['components'],
                                                    scoring=scoring, scoring_sha256=scoring_sha)
                        reward_sha = reward_mod.reward_sha256(reward)
                        store.append('event', {'schema': 'braid-lightning-event/v0.1', 'rolloutId': rollout_id,
                                               'attemptId': attempt_id, 'sequence': 0, 'eventType': 'reward',
                                               'timestamp': time.time(), 'data': {'reward': {
                                                   'value': 1.0 if reward['d4FirstAttempt'] else 0.0,
                                                   'components': {'schema': float(reward['schemaValid']),
                                                                  'd4': float(reward['d4FirstAttempt']),
                                                                  'canary': float(hits == 0)},
                                                   'source': 'verifier',
                                                   'reason': 'canary-hit' if hits else None}}})
                    hooks_mod.call(hooks, 'on_trace_end', running.to_dict(), {'transcriptSha256': transcript_sha})
                except hooks_mod.HookFailed:
                    refusal = 'hook-failed'
                except SecretLeak:
                    refusal = 'credential-leak'
                ended = time.time()
                final = running.transition(SUCCEEDED if refusal is None and stop is None else FAILED, ended,
                                           error_code=refusal or stop)
                store.append('rollout', final)
                result = AttemptResult.parse({
                    'schema': RESULT_SCHEMA, 'runId': run_id, 'rolloutId': rollout_id, 'attemptId': attempt_id,
                    'promptSet': prompt_set, 'promptSetSha256': prompt_sha, 'hostVersion': (version or None) and version[:128],
                    'model': model, 'repetition': rep, 'keySource': key_source[:32] if key_source else None,
                    'credentialPresent': bool(credential), 'stop': stop, 'refusal': refusal,
                    'startedAt': utc(started), 'endedAt': utc(ended), 'durationSeconds': round(ended - started, 3),
                    'parsedAttempts': parsed, 'transcriptSha256': transcript_sha, 'rewardSha256': reward_sha,
                    'label': label, 'executionAuthorization': False})
                store.append('result', result)
                try:
                    hooks_mod.call(hooks, 'on_rollout_end', final.to_dict(), result.to_dict(), {'rewardSha256': reward_sha})
                except hooks_mod.HookFailed:
                    pass  # recorded rollout stays; end hooks cannot change it
                count += 1
                host_status['rollouts'] += 1
                if stop:
                    status['stop'] = stop
                    break
                if refusal in ('route-unverified', 'credential-leak'):
                    status['refusal'] = refusal
                    break
            if status['stop'] or status['refusal'] in ('route-unverified', 'credential-leak'):
                if status['refusal'] == 'route-unverified' and host_name == 'opencode':
                    status['hosts'][host_name]['status'] = 'declared-limit'
                    status['hosts'][host_name]['limit'] = 'route-unverified (OD-2: no subscription key source reported)'
                    status['refusal'] = None
                    continue
                break
    except (DeclaredLimit, SafetyStop) as exc:
        status['refusal'] = status['refusal'] or 'isolation-failed'
        status['detail'] = secrets.redact(str(exc))[:300]
    finally:
        teardown = profile.teardown()
        status['teardown'] = teardown
        if not teardown['clean']:
            status['refusal'] = status['refusal'] or 'straggler-process'
    leaks = [p.name for p in store.root.rglob('*') if p.is_file() and secrets.scan(p.read_text(errors='replace'))]
    if leaks:
        status['refusal'] = 'credential-leak'
        status['leakedFiles'] = leaks
    status['completed'] = len({r.value['rolloutId'] for r in store.read('result')
                               if r.value['refusal'] is None and r.value['stop'] is None})
    return status


def run_status(home, run_id: str) -> dict:
    store = store_mod.RunStore(home, run_id)
    manifest = store.manifest()
    results = [r.value for r in store.read('result')]
    stops = [r['stop'] for r in results if r['stop']]
    refusals = sorted({r['refusal'] for r in results if r['refusal']})
    return {'runId': run_id, 'createdAt': manifest['createdAt'], 'configDigest': manifest['configDigest'],
            'attempts': len(results), 'completed': sum(1 for r in results if not r['refusal'] and not r['stop']),
            'stop': stops[-1] if stops else None, 'refusals': refusals,
            'resume': f'agent-braid lightning run --resume {run_id}' if stops else None,
            'labels': sorted({r['label'] for r in results}), 'executionAuthorization': False}


def report(home, run_id: str) -> dict:
    """Per-host summaries with Wilson intervals, recomputed from stored parsed attempts (REQ-010, REQ-011)."""
    root = checkout_root()
    from scripts import spec069_scoring as scoring
    store = store_mod.RunStore(home, run_id)
    results = [r.value for r in store.read('result')]
    scoring_sha = reward_mod.check_scoring(root)
    by_host: dict[str, list[dict]] = {}
    replay_ok = True
    for result in results:
        if result['refusal'] or result['stop']:
            continue
        host, case_id = result['rolloutId'].split('.')[0], result['rolloutId'].split('.')[1]
        prompt = json.loads((root / PROMPT_FILES[result['promptSet']]).read_text())
        case = next(c for c in prompt['cases'] if c['id'] == case_id)
        hits = 0
        for event in store.read('event'):
            if event.rollout_id == result['rolloutId'] and event.event_type == 'reward':
                hits = 1 if event.data['reward']['reason'] == 'canary-hit' else 0
        reward = reward_mod.replay(result['rolloutId'], case, result['parsedAttempts'], canary_hits=hits,
                                   components=['schema', 'd4', 'canary'], scoring=scoring, scoring_sha256=scoring_sha)
        replay_ok &= reward_mod.reward_sha256(reward) == result['rewardSha256']
        by_host.setdefault(host, []).append({'caseId': case_id, 'repetition': result['repetition'],
                                             'validFirstAttempt': reward['d4FirstAttempt'],
                                             'validWithinRetry': reward['d4WithinRetry']})
    hosts = {}
    for host, runs in by_host.items():
        n = len(runs)
        first = sum(r['validFirstAttempt'] for r in runs)
        retry = sum(r['validWithinRetry'] for r in runs)
        hosts[host] = {'trials': n, 'firstAttempt': first, 'withinRetry': retry,
                       'firstAttemptInterval': list(scoring.wilson_interval(first, n)),
                       'withinRetryInterval': list(scoring.wilson_interval(retry, n))}
    return {'runId': run_id, 'labels': sorted({r['label'] for r in results}), 'hosts': hosts,
            'replayMatches': replay_ok, 'claim': 'empirical-measurement', 'executionAuthorization': False}
