#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Candidate-bound documentary procedures for SPEC-039, not host acceptance.

Every procedure includes a mutation counterpart. Text checks establish only the
stated program/source contract. Tracking uses separately retained actual receipts.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import platform
import sys
from pathlib import Path
import re
import subprocess
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
PROGRAM = 'specs/039-ai-tooling-program/'
SPECS = ('039-ai-tooling-program','040-portable-mcp-surface','041-ai-tooling-skills',
         '042-ai-tooling-packaging','043-ai-tooling-journey','044-ai-tooling-evaluation')

def require(condition, message):
    if not condition:
        raise ValueError(message)

def procedure_capability_matrix(packet):
    text = packet[PROGRAM+'capability-matrix.md']
    rows = [line for line in text.splitlines() if line.startswith('|')]
    require(len(rows) == 16, 'incomplete capability/target tables')
    require(all(len(row.split('|')) in (6,7) for row in rows), 'missing matrix dimension')
    for term in ('Existing basis', 'M4.5 increment', 'Acceptance boundary',
                 'Actual host mandatory','Unclaimed','Host approval never substitutes'):
        require(term in text, 'missing capability boundary: '+term)

def procedure_m4_boundary(packet):
    text = packet[PROGRAM+'program.md']
    for term in ('negative utility','G4 NO-GO','grants no M4.5 capture or acceptance',
                 'new M3','cannot close M4','SPEC-038'):
        require(term in text, 'missing predecessor boundary: '+term)

def procedure_traceability(packet):
    for folder in SPECS:
        record = json.loads(packet['specs/'+folder+'/assurance.json'])
        reqs = record['requirements']
        require(len(reqs)==8, 'incomplete requirement inventory')
        tasks = packet['specs/'+folder+'/tasks.md']
        task_ids = re.findall(r'^- \[[ x]\] (T\d{3})', tasks, re.M)
        require(len(task_ids) >= 10 and len(set(task_ids)) == len(task_ids),
                'missing or duplicate task inventory')
        ids = set()
        for req in reqs:
            require(req['id'] not in ids, 'duplicate requirement'); ids.add(req['id'])
            require(req['id'] in tasks, 'untraced requirement')
            require(bool(req['scenarios']), 'missing scenarios')
            for sc in req['scenarios']:
                require(sc['id'] in tasks, 'untraced scenario')
                require(bool(sc['planned_evidence']), 'missing planned evidence')
                require(sc['test_name'] in packet['specs/'+folder+'/validation-plan.md']
                        or sc['test_file'].endswith('.py'), 'missing procedure reference')

def procedure_architecture_review(packet):
    text = packet['docs/adr/0021-codex-claude-tooling-integration.md']
    require('Proposed' in text, 'adoption was not granted')
    for term in ('grant','stdio','CLI','Constitution'):
        require(term.lower() in text.lower(), 'missing architecture boundary: '+term)
    require('SHALL' in packet['CONSTITUTION.md'], 'missing normative authority')

def procedure_research_provenance(packet):
    text = packet[PROGRAM+'research.md']
    for term in ('**Retrieved:**','Primary sources','v2.3.0','Alternatives','Remaining verification'):
        require(term.lower() in text.lower(), 'missing dated research/provenance: '+term)
    require('documentation and search snippets do not replace runtime observations' in text,
            'documentation mistaken for runtime evidence')
    require(len(re.findall(r'https://[^)\s]+',text)) >= 8, 'missing source inventory')

def procedure_tracking_scope(packet, proof):
    require(proof['audit']['scope']=='milestone:19', 'wrong reconciliation scope')
    require(proof['audit']['operations']==[], 'unreconciled tracking')
    expected=set(range(395,461))
    issues=proof['issues']['actualIssues']
    observed_issues = {i['issue_number'] for i in issues}
    require(expected <= observed_issues and len(observed_issues) == len(issues),
            'missing/duplicate stable issue membership')
    require(all(i['milestone']==19 for i in issues), 'wrong milestone membership')
    for view in ('Specs and tasks','By milestone'):
        observed=set()
        for page in proof['project']['tables']:
            if page['view'] != view: continue
            for row in page['rows']:
                observed.add(int(re.search(r'/issues/(\d+)',row['links'][0])[1]))
        require(observed==observed_issues, 'missing actual Project table members')
    board={n for page in proof['project']['boards'] for ns in page['columns'].values() for n in ns}
    require(board==observed_issues,'missing actual Project board members')
    require('one milestone' in packet[PROGRAM+'tasks.md'], 'missing stable tracking obligation')

def procedure_future_scope(packet):
    text=packet[PROGRAM+'program.md']
    routes=text.split('## Five future routes',1)
    require(len(routes)==2,'missing future routes')
    require(len([l for l in routes[1].splitlines() if l.startswith('|')])==7,'wrong future-route count')
    for term in ('Cursor','VS Code/GitHub Copilot','OpenCode','pi','add no v1 tasks'):
        require(term in routes[1], 'missing deferred route boundary: '+term)

def procedure_closure_boundary(packet):
    text=packet[PROGRAM+'program.md']
    for term in ('Mock clients\ncannot satisfy criterion 1','founder records bounded acceptance/closure',
                 'An unfavorable comparison is a valid result'):
        require(term in text, 'missing acceptance boundary: '+term)
    tasks=packet['specs/044-ai-tooling-evaluation/tasks.md']
    require('later human addendum/ratings/adjudication' in tasks,'missing deferred human gate')
    require('owner records closure' in tasks,'missing owner milestone decision')

PROCEDURES = (procedure_capability_matrix, procedure_m4_boundary,
    procedure_traceability, procedure_architecture_review,procedure_research_provenance,
    procedure_tracking_scope,procedure_future_scope,procedure_closure_boundary)
MUTATIONS = (
    (PROGRAM+'capability-matrix.md','Acceptance boundary','Removed dimension'),
    (PROGRAM+'program.md','G4 NO-GO','G4 GO'),
    ('specs/040-portable-mcp-surface/tasks.md','REQ-001','UNTRACED-001'),
    ('docs/adr/0021-codex-claude-tooling-integration.md','Proposed','Accepted'),
    (PROGRAM+'research.md','**Retrieved:**','Undated:'),
    None,
    (PROGRAM+'program.md','add no v1 tasks','add v1 tasks'),
    ('specs/044-ai-tooling-evaluation/tasks.md','owner records closure','tool records closure'))

def git_bytes(candidate, path):
    return subprocess.run(['git','show',candidate+':'+path],cwd=ROOT,
                          capture_output=True,check=True,timeout=20).stdout

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--tracking-readbacks',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    require(re.fullmatch('[0-9a-f]{40}',args.candidate) is not None,'full candidate required')
    names={PROGRAM+'capability-matrix.md',PROGRAM+'program.md',PROGRAM+'research.md',
           'docs/adr/0021-codex-claude-tooling-integration.md','CONSTITUTION.md'}
    names.update('specs/'+s+'/'+name for s in SPECS for name in ('tasks.md','assurance.json','validation-plan.md'))
    raw={name:git_bytes(args.candidate,name) for name in sorted(names)}
    packet={name:value.decode('utf-8') for name,value in raw.items()}
    proof={key:json.loads((args.tracking_readbacks/name).read_text()) for key,name in
           [('audit','after-audit.json'),('issues','plugin-readback.json'),('project','project-readback.json')]}
    require(not args.output.is_symlink(), 'output must not be a symlink')
    args.output = args.output.absolute()
    require(not args.output.resolve().is_relative_to(ROOT), 'output must be outside checkout')
    args.output.mkdir(mode=0o700, parents=True,exist_ok=False)
    args.output.chmod(0o700)
    results=[]
    for index,procedure in enumerate(PROCEDURES):
        if index==5: procedure(packet,proof)
        else: procedure(packet)
        mutated=copy.deepcopy(packet); badproof=copy.deepcopy(proof)
        if index==5: badproof['audit']['operations']=[{'action':'unknown'}]
        else:
            name,old,new=MUTATIONS[index]; require(old in mutated[name],'mutation did not select source')
            mutated[name]=mutated[name].replace(old,new)
        try:
            if index==5: procedure(mutated,badproof)
            else: procedure(mutated)
        except ValueError as error:
            rejection=str(error)
        else: raise ValueError('mutation accepted: '+procedure.__name__)
        results.append({'scenario':f'SC-{index+1:03}','procedure':procedure.__name__,
                        'positive':'passed','negative':'refused','rejection':rejection})
    hashes={name:hashlib.sha256(value).hexdigest() for name,value in raw.items()}
    receipt={'schema':'m45-program-procedures-v1','candidate':args.candidate,
        'at':datetime.now(timezone.utc).isoformat(),'candidateInputs':hashes,'results':results,
        'execution':{'command':[sys.executable,*sys.argv], 'cwd':str(ROOT),
                     'python':platform.python_version(), 'platform':platform.platform(),
                     'runnerSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
        'trackingReadbacks':{name:hashlib.sha256((args.tracking_readbacks/name).read_bytes()).hexdigest()
            for name in ('after-audit.json','plugin-readback.json','project-readback.json')},
        'limits':'Documentary/source contract plus historical actual tracking readbacks only. '
                 'No host invocation, ADR adoption, founder acceptance or scientific proof. '
                 'Tracking proof precedes newly added auxiliary tasks and later state reconciliation.'}
    out=args.output/'receipt.json';out.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');out.chmod(0o600)
    print(json.dumps({'outcome':'passed','procedures':len(results),'receiptSha256':hashlib.sha256(out.read_bytes()).hexdigest()}))

if __name__=='__main__': main()
