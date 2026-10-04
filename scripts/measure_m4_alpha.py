#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Descriptive fixed-corpus serial/parallel total-cost measurements; no host calls."""
from __future__ import annotations
from contextlib import contextmanager
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import statistics
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from agent_braid import git_replay,git_runtime,runtime_policy
from agent_braid.git_process import GitCommandBudget
from tests import test_git_runtime as fixtures


def inventory():
    names=['agent_braid/runtime_policy.py','agent_braid/runtime_scheduler.py',
           'agent_braid/git_runtime.py','agent_braid/git_runtime_process.py',
           'agent_braid/git_process.py','agent_braid/git_replay.py','agent_braid/git_adapter.py',
           'agent_braid/git_exec.py','agent_braid/analysis.py','research/lab/model.py',
           'scripts/measure_m4_alpha.py','specs/021-m4-alpha-runtime/measurement-protocol.md',
           'tests/test_git_runtime.py']
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in names}


@contextmanager
def budgets():
    records=[];original=GitCommandBudget.__post_init__
    def observe(value):
        original(value);records.append(value)
    with patch.object(GitCommandBudget,'__post_init__',observe):yield records


def treatment(fixture,request,mode):
    origin=time.monotonic_ns();parent=time.process_time_ns()
    child=resource.getrusage(resource.RUSAGE_CHILDREN)
    with budgets() as phases:
        with tempfile.TemporaryDirectory(prefix='agent-braid-measurement-treatment-',dir=fixture.root) as directory:
            root=Path(directory)
            evidence,advisory=git_replay.produce(git_runtime._analysis_request(request))
            plan=runtime_policy.prepare_policy_run(request,root/'result',replay_evidence=evidence,
                                                   advisory_plan=advisory,mode=mode)
            grant=runtime_policy.issue_operator_grant(plan,root/'grants',acknowledge=plan['planDigest'])
            report=runtime_policy.execute_policy_run(plan,root/'grants',grant['grantId'])
            verification=git_runtime.verify_run(request,root/'result')
            if verification['status']!='verified-completed':raise RuntimeError('unverified result')
            if fixture.snapshot(fixture.repo)!=fixture.before:raise RuntimeError('source changed')
            observed=report.get('preparation')
        # Treatment-owned run/grants and preparation scratch are already cleaned.
        after=resource.getrusage(resource.RUSAGE_CHILDREN)
    return {'mode':mode,'wallNs':time.monotonic_ns()-origin,
            'parentCpuNs':time.process_time_ns()-parent,
            'childUserCpuNs':int((after.ru_utime-child.ru_utime)*10**9),
            'childSystemCpuNs':int((after.ru_stime-child.ru_stime)*10**9),
            'processLifetimePeakChildRssBytes':int(after.ru_maxrss)*(1 if sys.platform=='darwin' else 1024),
            'gitCommands':sum(p.commands for p in phases),
            'capturedOutputBytes':sum(p.output_bytes for p in phases),
            'sampledPeakPhaseScratchBytes':max((p.peak_scratch_bytes for p in phases),default=0),
            'boundedPhaseCount':len(phases),'resultTree':verification['resultTree'],
            'manifestDigest':plan['runtimeManifest']['manifestDigest'],
            'runtimeManifest':plan['runtimeManifest'],
            'preparationEvidence':observed,
            'planDigest':plan['planDigest'],
            'observedPeakWorkerIntervals':observed['observedPeakWorkerIntervals'] if observed else 1,
            'workerEvidenceDigest':observed['evidenceDigest'] if observed else None}


def run(output):
    if output.expanduser().resolve().is_relative_to(ROOT):
        raise ValueError("measurement output must be outside the candidate checkout")
    before=inventory()
    git=lambda *args:subprocess.check_output(['git','-C',str(ROOT),*args],timeout=30).decode().strip()
    if git('status','--porcelain'):raise RuntimeError('measurement requires a clean frozen candidate')
    candidate=git('rev-parse','HEAD');fixture=fixtures.GitRuntimeTests()
    with patch.dict(os.environ, {'GIT_AUTHOR_DATE':'2000-01-01T00:00:00+00:00',
                                 'GIT_COMMITTER_DATE':'2000-01-01T00:00:00+00:00'}):
        fixture.setUp()
    pairs=[]
    try:
        for order in (['a','b'],['b','a']):
            request=json.loads(json.dumps(fixture.request));request['order']=order
            for repetition in range(3):
                modes=['serial','parallel'] if repetition%2==0 else ['parallel','serial']
                samples={mode:treatment(fixture,request,mode) for mode in modes}
                if samples['serial']['resultTree']!=samples['parallel']['resultTree']:
                    raise RuntimeError('serial/parallel disagreement')
                ratio=Fraction(samples['serial']['wallNs'],samples['parallel']['wallNs'])
                pairs.append({'order':order,'repetition':repetition+1,
                              'exposure':'first' if repetition==0 else 'subsequent',
                              'treatmentOrder':modes,'samples':samples,'equivalentFinalTree':True,
                              'serialOverParallelWallRatio':{'numerator':ratio.numerator,'denominator':ratio.denominator}})
    finally:fixture.doCleanups()
    ratios=[Fraction(p['serialOverParallelWallRatio']['numerator'],p['serialOverParallelWallRatio']['denominator']) for p in pairs]
    median=statistics.median(ratios)
    record={'m4AlphaMeasurementVersion':'0.1.0-alpha','candidateCommit':candidate,'inputs':before,
            'candidateInputsChangedDuringRun':before!=inventory(),
            'candidateWorkingTreeChangedDuringRun':bool(git('status','--porcelain')),
            'environment':{'python':platform.python_version(),'platform':platform.system(),
                           'machine':platform.machine(),'git':git('--version')},
            'pairs':pairs,'medianSerialOverParallelWallRatio':{'numerator':median.numerator,'denominator':median.denominator},
            'utilityOutcome':'positive-descriptive' if median>1 else 'negative-or-null-descriptive',
            'limits':['Six descriptive pairs only; uncontrolled OS caches/background activity.',
                      'Constructor instrumentation captures all bounded phase counts/output; overhead is included.',
                      'RSS is a process-lifetime maximum, not a per-run allocation peak.',
                      'Worker interval overlap is observational, not simultaneous CPU proof.',
                      'Safety controls and four-worker/dependency probes belong to separate reproduction records.',
                      'No host/model calls, semantic correctness, scientific result or whole-M4 acceptance.']}
    if record['candidateInputsChangedDuringRun'] or record['candidateWorkingTreeChangedDuringRun']:
        record['status']='invalidated';code=2
    else:record['status']='captured';code=0
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':record['status'],'utilityOutcome':record['utilityOutcome'],'output':str(output)}))
    return code


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args().output))
