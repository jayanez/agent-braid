# SPDX-License-Identifier: AGPL-3.0-only
"""Reproducible owned synthetic signals and bounded ordinary-text Git fixtures."""
from contextlib import contextmanager
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
from .forecast_data import require,integer,digest
from .forecast_windows import compile_window

FAMILIES=('constant','trend','seasonal','bursts','regime','missing','late','dependency-chain')

def signal_episode(family,*,seed,partition='development',horizon=10):
    require(family in FAMILIES and partition in ('development','calibration','holdout'),'unsupported-lab-stratum')
    integer(seed);require(horizon in (1,5,10),'unsupported-horizon');rng=random.Random(seed)
    recipe={'family':family,'seed':seed,'partition':partition,'version':1}
    group='episode-'+digest({'family':family,'seed':seed,'version':1})[:24]
    step=100000000;origin={'development':0,'calibration':1,'holdout':2}[partition]*1000000000000;cutoff=origin+127*step
    profile={'version':'agent-braid-forecast-resource-v1','sourceKind':'synthetic','profileId':'owned-lab',
             'hostId':'synthetic-local','executionContract':'authorized-serial-index-patch-v1','allowedModes':['serial','parallel'],
             'maxWorkers':4,'observedNs':cutoff,'expiresNs':cutoff+100*step,
             'caps':{'operations':4,'patchBytes':262144,'scratchBytes':67108864}}
    def value(index):
        if family=='constant':return 4.0
        if family=='trend':return 2+index*.05
        if family=='seasonal':return 5+3*math.sin(index*math.pi/8)
        if family=='bursts':return 15.0 if index%25<4 else 2.0
        if family=='regime':return 2.0 if index<80 else 9.0
        return 3+rng.random()
    series=[value(i) for i in range(128+horizon)];events=[]
    for i,v in enumerate(series[:128]):
        if family=='missing' and i%11==0:continue
        events.append({'targetId':'load','eventNs':origin+i*step,'availableAtNs':cutoff+step if family=='late' and i%11==0 else origin+i*step,'unit':'count','value':v})
    window=compile_window(events,target_ids=['load'],units=['count'],grid_start_ns=origin,step_ns=step,bins=128,cutoff_ns=cutoff,
                          episode_group=group,resource_digest=digest(profile),partition_digest=digest({'partition':partition,'seed':seed}),
                          transform_digest=digest({'transform':'identity','version':1}))
    return {'recipe':recipe,'episodeGroup':group,'partition':partition,'window':window,'resource':profile,
            'actual':series[128:],'events':events,'provenance':'synthetic-simulation'}

@contextmanager
def git_fixture(*,seed=1,operations=2,dependency_chain=False):
    integer(seed);integer(operations,2,4)
    with tempfile.TemporaryDirectory(prefix='agent-braid-forecast-fixture-') as tmp:
        root=Path(tmp).resolve();repo=root/'source';repo.mkdir();home=root/'home';home.mkdir(mode=0o700)
        env={'PATH':os.environ.get('PATH','/usr/bin:/bin'),'HOME':str(home),'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_GLOBAL':os.devnull,
             'GIT_TERMINAL_PROMPT':'0','GIT_AUTHOR_NAME':'Synthetic fixture','GIT_AUTHOR_EMAIL':'synthetic@example.invalid',
             'GIT_COMMITTER_NAME':'Synthetic fixture','GIT_COMMITTER_EMAIL':'synthetic@example.invalid',
             'GIT_AUTHOR_DATE':'2026-10-13T00:00:00Z','GIT_COMMITTER_DATE':'2026-10-13T00:00:00Z'}
        def git(*args):
            result=subprocess.run(['git','-c','core.hooksPath=/dev/null','-c','commit.gpgSign=false','-C',str(repo),*args],
                                  env=env,capture_output=True,timeout=5,check=True)
            return result.stdout.decode().strip()
        git('init','-q','-b','main')
        for i in range(operations):(repo/f'op{i}.txt').write_text(f'base {seed}\n')
        git('add','.');git('commit','-qm','base');base=git('rev-parse','HEAD');commits=[];ids=[]
        for i in range(operations):
            name=f'op{i}';ids.append(name);git('checkout','-q','-b',name,base)
            (repo/f'{name}.txt').write_text(f'changed {seed} {i}\n');git('add',f'{name}.txt');git('commit','-qm',name);commits.append(git('rev-parse','HEAD'))
        git('checkout','-q','main')
        for i in range(operations):(repo/f'op{i}.txt').write_text(f'changed {seed} {i}\n')
        git('add','.');expected=git('write-tree');git('reset','--hard','-q',base)
        request={'gitRuntimeRequestVersion':'0.1.0-alpha','repository':str(repo),'baseRevision':base,'expectedFinalTree':expected,'order':ids,
                 'operations':[{'instanceId':name,'attemptId':name+'-attempt','source':{'kind':'commit','revision':commit},
                                'dependencies':ids[i-1:i] if dependency_chain else [],'uncertainPaths':[],'declaredWrites':[name+'.txt']}
                               for i,(name,commit) in enumerate(zip(ids,commits))]}
        yield {'root':root,'repository':repo,'request':request,'seed':seed,'sourceHead':base}
