# SPDX-License-Identifier: AGPL-3.0-only
"""One APO or GEPA arm run for Braid Lightning (SPEC-072 REQ-004, REQ-005, REQ-007, T009).

`agent-braid lightning run` with `algorithm.name` apo or gepa lands here. Each candidate body is evaluated by a SPEC-071
sub-run on the development cases it is scored on, with the candidate packaged into a copy of one built plugin; the
optimizer goes through the runner's sandboxed channel. Nothing here touches the held-out set or the repository skill.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

from . import lightning_runner as runner_mod
from . import lightning_store as store_mod
from .lightning_algorithm import QUOTA_STOPS, rescore
from .lightning_apo import APO, MAX_ROUNDS
from .lightning_gepa import GEPA
from .lightning_resources import sha256_text, split_skill

ALGORITHMS = {'apo': APO, 'gepa': GEPA}
PACKAGED_SKILL = Path('skills/analyze/SKILL.md')
SOURCES = ('baseline', 'final')  # SPEC-069 plugin arms; the evaluation protocol's A0 is ``baseline``
DEFAULT_MODEL = 'claude-sonnet-5-5'  # the T010 model, as in scripts/spec071_real_baseline.py


def source_skill(source: str, target: str, root: Path) -> tuple[str, dict]:
    """The seed skill text and its provenance for a plugin arm: ``baseline`` is the guidance at the SPEC-069
    BASELINE_COMMIT (A0); ``final`` is this checkout's working tree."""
    if source not in SOURCES:
        raise runner_mod.RunnerError('Unknown source arm', 'config-enum')
    if source == 'final':
        commit = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True,
                                check=True).stdout.strip()
        return (root / target).read_text(encoding='utf-8'), {'arm': 'final', 'commit': commit, 'workingTree': True}
    from scripts.spec069_native_runs import BASELINE_COMMIT
    done = subprocess.run(['git', '-C', str(root), 'show', f'{BASELINE_COMMIT}:{target}'], capture_output=True)
    if done.returncode:
        raise runner_mod.RunnerError('The baseline commit has no such skill file', 'config-shape')
    return done.stdout.decode('utf-8'), {'arm': 'baseline', 'commit': BASELINE_COMMIT, 'workingTree': False}


def _cases(root: Path) -> list[str]:
    return [c['id'] for c in json.loads((root / runner_mod.PROMPT_FILES['development']).read_text())['cases']]


def estimate(config: dict, root: Path) -> dict:
    """Upper bounds of one arm's rollouts and optimizer calls, before the budget caps (dry run)."""
    algo, rollout, budget = config['algorithm'], config['rollout'], config['budget']
    name = algo['name']
    if name not in ALGORITHMS:
        raise runner_mod.RunnerError('Only apo and gepa run as optimization arms', 'config-enum')
    cases, hosts = len(_cases(root)), len(rollout['hosts'])
    size = min(algo['minibatch'], cases)
    full = cases * rollout['repetitions'] * hosts
    if name == 'apo':
        rounds = min(algo['rounds'], MAX_ROUNDS)
        parents = [1] + [algo['beamWidth']] * (rounds - 1)
        calls = sum(p * (1 + algo['branchFactor']) for p in parents)
        rollouts = sum(p * algo['branchFactor'] for p in parents) * size * hosts + full
    else:
        rounds = algo['rounds']
        calls = rounds
        rollouts = rounds * (size * hosts + full)  # every child accepted: the worst case
    return {'algorithm': name, 'rounds': rounds, 'hosts': list(rollout['hosts']), 'developmentCases': cases,
            'upperBound': {'rollouts': rollouts, 'optimizerCalls': calls},
            'budget': {'maxRollouts': budget['maxRollouts'], 'maxOptimizerCalls': budget['maxOptimizerCalls']},
            'atMost': {'rollouts': min(rollouts, budget['maxRollouts']),
                       'optimizerCalls': min(calls, budget['maxOptimizerCalls'])},
            'optimizerHost': config['optimizer']['host'], 'quotaNote': (
                'each rollout is one host session and each optimizer call one Claude Code call on the subscription; '
                'a quota stop ends the arm and `--resume` continues it'),
            'executionAuthorization': False}


def seed_vectors(home, run_id: str, root: Path) -> list[dict]:
    """The seed's full development vectors, re-scored from a finished baseline run's attempt results."""
    latest: dict[str, dict] = {}
    for record in store_mod.RunStore(home, run_id).read('result'):
        value = record.value
        if value['promptSet'] != 'development':
            raise runner_mod.RunnerError('The seed run must be a development run', 'holdout-contamination')
        if value['stop'] is None:
            latest[value['rolloutId']] = value
    vectors = [rescore(v) for v in latest.values()]
    missing = set(_cases(root)) - {v['caseId'] for v in vectors}
    if missing:
        raise runner_mod.RunnerError('The seed run does not cover every development case', 'seed-incomplete')
    return vectors


def candidate_plugin(base: Path, skill_text: str, destination: Path) -> Path:
    """A copy of a built plugin whose packaged analyze skill is the candidate."""
    from scripts.build_native_plugin import package_skill
    market = base.parents[1]
    shutil.copytree(market, destination, symlinks=True)
    plugin = destination / base.relative_to(market)
    target = plugin / PACKAGED_SKILL
    if not target.is_file():
        raise runner_mod.RunnerError('The built plugin has no packaged analyze skill', 'isolation-failed')
    target.write_text(package_skill(skill_text), encoding='utf-8')
    return plugin


class CandidateEvaluator:
    """``evaluator(body, case_ids, repetitions) -> [attempt-result record]`` through a SPEC-071 sub-run per call."""

    def __init__(self, home, config: dict, run_id: str, *, base_plugin: Path, front: str, workdir: Path,
                 fake_hosts: bool = False, environ: dict | None = None, arm: str = 'baseline',
                 models: dict[str, str] | None = None):
        self.home, self.config, self.run_id = home, config, run_id
        self.base, self.front, self.workdir = base_plugin, front, workdir
        self.fake_hosts, self.environ, self.arm, self.models = fake_hosts, environ, arm, models

    def __call__(self, body: str, case_ids: list[str], repetitions: int) -> list[dict]:
        text = self.front + body
        key = hashlib.sha256(json.dumps([sha256_text(body), case_ids, repetitions]).encode()).hexdigest()[:12]
        sub = f'{self.run_id}-e{key}'
        store = store_mod.RunStore(self.home, sub)
        copy = self.workdir / sub
        plugin = self.base if self.fake_hosts else candidate_plugin(self.base, text, copy)
        try:
            status = runner_mod.run(self.home, self.config, run_id=sub, resume=store.root.exists(),
                                    prompt_set='development', fake_hosts=self.fake_hosts, plugin_dir=plugin,
                                    environ=self.environ, case_ids=case_ids, repetitions=repetitions,
                                    skill_text=text, arm=self.arm, models=self.models)
        finally:
            shutil.rmtree(copy, ignore_errors=True)
        if status['stop']:
            raise runner_mod.RunnerError('The candidate evaluation stopped', status['stop'])
        if status['refusal']:
            raise runner_mod.RunnerError('The candidate evaluation was refused', status['refusal'])
        latest: dict[str, dict] = {}
        for record in store.read('result'):
            if record.value['stop'] is None:
                latest[record.value['rolloutId']] = record.value
        return list(latest.values())


def run_arm(home, config: dict, *, seed_run: str, run_id: str | None = None, resume: bool = False,
            fake_hosts: bool = False, plugin_dir: Path | None = None, environ: dict | None = None,
            rng_seed: int = 0, source: str = 'baseline', models: dict[str, str] | None = None) -> dict:
    """Run (or resume) one optimization arm; return its content-free summary.

    ``source`` pins where the arm starts (default ``baseline``, the evaluation protocol's A0): the seed skill text
    and the base plugin for candidate sub-runs both come from that SPEC-069 plugin arm, so a candidate differs
    from A0 only in the skill text. ``models`` pins the host model per host for the sub-runs and the optimizer.
    """
    name = config['algorithm']['name']
    if name not in ALGORITHMS:
        raise runner_mod.RunnerError('Only apo and gepa run as optimization arms', 'config-enum')
    if resume and not run_id:
        raise runner_mod.RunnerError('--resume needs the run id', 'resume-needs-run-id')
    root = runner_mod.checkout_root()
    raw, provenance = source_skill(source, config['target']['path'], root)
    run_id = run_id or f'{name}-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    seeds = seed_vectors(home, seed_run, root)
    journaled = sum(e['kind'] == 'call' for e in store_mod.RunStore(home, run_id).read_journal()) if resume else 0
    models = dict(models or {})
    host_options = {'environ': environ} if environ is not None else {}
    optimizer_host = config['optimizer']['host']
    channel = runner_mod.OptimizerChannel(optimizer_host, fake_hosts=fake_hosts, first_call=journaled + 1,
                                          model=models.get(optimizer_host), **host_options)
    front = split_skill(raw)[0]
    provenance = {**provenance, 'seedSkillSha256': sha256_text(raw)}
    try:
        with tempfile.TemporaryDirectory(prefix='lightning-arm-') as tmp:
            work = Path(tmp)
            if plugin_dir is not None:
                base = plugin_dir
            else:
                from scripts import spec069_native_runs as driver
                base = driver.fake_plugin(work) if fake_hosts else driver.build_candidate(
                    source, work, work / 'build-cache', False)[0]
            evaluator = CandidateEvaluator(home, config, run_id, base_plugin=base, front=front, workdir=work,
                                           fake_hosts=fake_hosts, environ=environ, arm=source, models=models)
            options = {'evaluator': evaluator, 'optimizer': channel, 'seed_vectors': seeds}
            algorithm = APO(**options) if name == 'apo' else GEPA(**options, rng_seed=rng_seed)
            algorithm.seed_text, algorithm.source = raw, provenance
            summary = algorithm.run(home, config, run_id=run_id, resume=resume)
    finally:
        channel.close()
    summary.update(seedRun=seed_run, label='pipeline-only' if fake_hosts else 'host-run',
                   quotaStopped=summary['stop'] in QUOTA_STOPS, source=provenance, models=models)
    return summary
