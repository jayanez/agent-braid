#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Fresh-process bounded alpha core/protocol reproduction; no live model credentials."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import platform
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def inputs():
    names=set()
    for directory in ('agent_braid','research/lab','schemas'):
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/directory).rglob('*')
                     if p.is_file() and p.suffix in {'.py','.json'})
    names.update(['tests/test_git_runtime.py','tests/test_m4_alpha_policy.py',
                  'tests/test_m4_alpha_scheduler.py','tests/test_m4_alpha_mcp.py',
                  'scripts/reproduce_m4_alpha.py','docs/adr/0019-bounded-local-git-runtime.md',
                  'docs/adr/0020-bounded-m4-alpha-runtime.md','CONSTITUTION.md','GOVERNANCE.md',
                  'specs/021-m4-alpha-runtime/spec.md','specs/021-m4-alpha-runtime/g1-contract.md',
                  'specs/021-m4-alpha-runtime/c2-execution-contract.md'])
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(names)}


def run(output):
    output=output.expanduser().resolve()
    if output.is_relative_to(ROOT):raise ValueError('evidence output must be outside the candidate checkout')
    git=lambda *args:subprocess.check_output(['git','-C',str(ROOT),*args],timeout=30).decode().strip()
    if git('status','--porcelain'):raise ValueError('reproduction requires a clean frozen candidate')
    candidate=git('rev-parse','HEAD');before=inputs()
    command=[sys.executable,'-m','unittest','-v','tests.test_git_runtime',
             'tests.test_m4_alpha_policy','tests.test_m4_alpha_scheduler','tests.test_m4_alpha_mcp']
    timed_out=False
    try:
        process=subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1800)
        raw=process.stdout;code=process.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out=True;raw=exc.output or b'';code=124
    output.parent.mkdir(parents=True,exist_ok=True);log=output.with_suffix('.txt');log.write_bytes(raw)
    text=raw.decode('utf-8',errors='replace');match=re.search(r'Ran (\d+) tests in',text)
    skipped=[line for line in text.splitlines() if ' ... skipped ' in line]
    record={'m4AlphaReproductionVersion':'0.1.0-alpha','candidateCommit':candidate,'inputs':before,
            'candidateInputsChangedDuringRun':before!=inputs(),
            'candidateWorkingTreeChangedDuringRun':bool(git('status','--porcelain')),
            'environment':{'python':platform.python_version(),'git':git('--version'),
                           'platform':platform.system(),'machine':platform.machine()},
            'command':'python -m unittest -v tests.test_git_runtime tests.test_m4_alpha_policy tests.test_m4_alpha_scheduler tests.test_m4_alpha_mcp',
            'exitCode':code,'timedOut':timed_out,'tests':int(match.group(1)) if match else None,
            'skipped':skipped,'logSha256':hashlib.sha256(raw).hexdigest(),
            'limits':['Owned fixed-patch core and deterministic stdio peer only; no real-host evidence.',
                      'Fresh Python process on recorded platform, not external independent validation.',
                      'Controlled checkpoint interruption; no power-loss or hostile same-UID claim.',
                      'No model calls, host credentials, source promotion or arbitrary-code execution.',
                      'Observed worker overlap is not a CPU parallelism or speedup guarantee.',
                      'Passing reproduction does not imply independent Luna review or founder whole-M4 acceptance.']}
    if record['candidateInputsChangedDuringRun'] or record['candidateWorkingTreeChangedDuringRun']:
        record['status']='invalidated';record['exitCode']=2
    elif code==0 and match and not skipped:record['status']='passed'
    elif code==0:
        record['status']='incomplete';record['exitCode']=2
    else:record['status']='failed'
    output.write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':record['status'],'exitCode':record['exitCode'],'output':str(output)}))
    return record['exitCode']


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args().output))
