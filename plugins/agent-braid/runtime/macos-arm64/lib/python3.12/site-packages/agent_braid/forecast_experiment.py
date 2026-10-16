# SPDX-License-Identifier: AGPL-3.0-only
"""Owned synthetic paired policy harness; grants come from an external operator."""
from copy import deepcopy
from contextlib import contextmanager,nullcontext
from pathlib import Path
import random
import subprocess
import tempfile
import time
from .forecast_data import ForecastError,require,integer,digest,canonical,keys,pin
from .forecast_windows import compile_window
from .forecast_advice import ForecastSession
from .forecast_policy import advise

def paired_synthetic_episode(fixture,signal,*,operator,session=None,order_seed=1,cost_recorder=None,progress=None):
    """Execute every intended arm on fresh owned private runs; preserve failures."""
    episode_started=time.monotonic_ns()
    require(callable(operator),'independent-operator-required');integer(order_seed)
    require(progress is None or callable(progress),'invalid-progress-observer')
    require(signal.get('provenance')=='synthetic-simulation','real-source-not-admitted')
    from . import git_runtime,git_replay,runtime_policy
    root=Path(fixture['root']).resolve(strict=True);repo=Path(fixture['repository']).resolve(strict=True)
    require(repo.parent==root and repo.name=='source','fixture-scope-invalid')
    request=deepcopy(fixture['request']);episode=digest({'request':{k:v for k,v in request.items() if k!='repository'},'recipe':signal['recipe']})
    expected_source=fixture['sourceHead'];arms=['serial-reference','non-model-reference','forecast-choice'];random.Random(order_seed).shuffle(arms)
    own_session=session is None;session=ForecastSession() if session is None else session;results=[];cleanup_ns=0
    phase_count=0
    def phase(index,stage):
        nonlocal phase_count
        phase_count+=1
        return (nullcontext() if cost_recorder is None
                else cost_recorder.phase(episode[:16]+':'+str(index)+':'+str(phase_count),stage))
    @contextmanager
    def directory(index):
        with phase(index,'isolated-preparation'):
            scope=tempfile.TemporaryDirectory(prefix='arm-',dir=root)
        try:yield scope.name
        finally:
            with phase(index,'cleanup'):scope.cleanup()
    try:
        for index,arm in enumerate(arms):
            started=time.monotonic_ns();row={'arm':arm,'orderIndex':index,'status':'failed','mode':'serial','sourceKind':'authentic-on-synthetic',
                 'wallNs':None,'resultTree':None,'forecastStatus':None,'reason':None,'inputDigest':digest(request)}
            if progress is not None:
                progress(deepcopy({'episodeId':episode,'arms':results,
                    'activeArm':{'arm':arm,'orderIndex':index,'status':'started-outcome-unknown',
                                 'inputDigest':row['inputDigest']},
                    'notRunArms':arms[index+1:],'executionAuthorization':False}))
            try:
                head=subprocess.run(['git','--no-optional-locks','-C',str(repo),'rev-parse','HEAD'],capture_output=True,timeout=5,check=True)
                require(head.stdout.decode().strip()==expected_source,'fixture-source-drift')
                # Compile from the frozen raw events inside every treatment boundary.
                with phase(index,'data-preparation'):
                    original=signal['window'];window=compile_window(deepcopy(signal['events']),target_ids=original['targetIds'],units=original['units'],
                        grid_start_ns=original['gridStartNs'],step_ns=original['stepNs'],bins=len(original['values'][0]),cutoff_ns=original['cutoffNs'],
                        episode_group=original['episodeGroup'],resource_digest=original['resourceReceiptDigest'],partition_digest=original['partitionDigest'],transform_digest=original['transformDigest'])
                if arm=='forecast-choice':
                    with phase(index,'forecast'):
                        forecast=session.predict({'version':'agent-braid-forecast-request-v1','backend':'chronos2','window':window,'horizon':1,'alpha':.3})
                    row['forecastStatus']=forecast['status']
                    row['economicInputsKind']='synthetic-fixture-costs-not-observed-runtime-costs'
                    policy={'version':1,'partition':'development','targetId':'load','unit':'count','minimumRatio':1.1,'maximumIntervalWidth':100,
                            'advisoryOverheadNs':forecast['costs']['wallNs']}
                    with phase(index,'advice'):
                        advice=advise({'version':'agent-braid-advice-request-v1','mode':'consultative','window':window,'forecast':forecast,
                        'resource':signal['resource'],'resourceDigest':digest(signal['resource']),'nowNs':window['cutoffNs'],
                        'expiresNs':window['cutoffNs']+1,'referenceMode':'serial','policy':policy,
                        'catalogue':{'sourceKind':'synthetic','candidates':[
                            {'id':'serial','mode':'serial','planDigest':'a'*64,'baseWallNs':1000000000,'loadPenaltyNsPerUnit':0,'eligible':True},
                            {'id':'parallel','mode':'parallel','planDigest':'b'*64,'baseWallNs':500000000,'loadPenaltyNsPerUnit':1000000,
                             'eligible':not any(op['dependencies'] for op in request['operations'])}]}})
                    row['mode']=advice['selectedAction'];row['adviceDigest']=advice['packetDigest']
                with directory(index) as tmp:
                    destination=Path(tmp)
                    with phase(index,'replay'):
                        evidence,portable=git_replay.produce(git_runtime._analysis_request(request))
                    with phase(index,'isolated-preparation'):
                        plan=runtime_policy.prepare_policy_run(request,destination/'result',replay_evidence=evidence,advisory_plan=portable,mode=row['mode'])
                    with phase(index,'grants'):
                        grant=operator(deepcopy(plan),destination/'grants')
                    require(type(grant) is dict and 'grantId' in grant,'invalid-operator-grant')
                    with phase(index,'isolated-execution'):
                        report=runtime_policy.execute_policy_run(plan,destination/'grants',grant['grantId'])
                    with phase(index,'verification'):
                        verified=git_runtime.verify_run(request,destination/'result')
                    require(verified['status']=='verified-completed','unverified-outcome')
                    require(request['expectedFinalTree']==verified['resultTree'],'non-equivalent-outcome')
                    row.update(status='completed',resultTree=verified['resultTree'],planDigest=plan['planDigest'])
            except (ValueError,OSError,KeyError,TypeError):row['reason']='paired-arm-failed'
            except BaseException as error:
                row['reason']=('paired-arm-cancelled' if isinstance(error,(KeyboardInterrupt,SystemExit))
                               else 'paired-arm-timed-out' if isinstance(error,subprocess.TimeoutExpired)
                               else 'paired-arm-aborted')
                raise
            finally:
                row['wallNs']=time.monotonic_ns()-started;results.append(row)
                if progress is not None:
                    progress(deepcopy({'episodeId':episode,'arms':results,'activeArm':None,
                        'notRunArms':arms[index+1:],'executionAuthorization':False}))
        require(len(results)==3,'incomplete-intended-roster')
    finally:
        cleanup_started=time.monotonic_ns()
        if own_session:
            with phase('session','cleanup'):session.close()
        cleanup_ns=time.monotonic_ns()-cleanup_started
    total=time.monotonic_ns()-episode_started
    result={'version':'agent-braid-synthetic-policy-experiment-v1','episodeId':episode,'provenance':'authentic-on-synthetic',
            'independentUnit':'owned-synthetic-recipe-not-real-workload','arms':results,
            'costs':{'episodeWallNs':total,'armWallNs':sum(r['wallNs'] for r in results),'sessionCleanupNs':cleanup_ns,
                     'coordinatorResidualNs':total-sum(r['wallNs'] for r in results)-cleanup_ns,
                     'boundary':'data-compilation-through-arm-cleanup-and-owned-session-cleanup',
                     'exportIncluded':False,'externalSessionLifecycleIncluded':own_session,
                     'cpuNs':None,'cpuReason':'not-observed','memoryBytes':None,'memoryReason':'not-observed'},
            'status':'synthetic-descriptive' if all(r['status']=='completed' for r in results)
                and next(r for r in results if r['arm']=='forecast-choice')['forecastStatus']=='forecast' else 'inconclusive',
            'utilityAccepted':False,'executionAuthorization':False}
    result['receiptDigest']=digest(result);return result

def summarize_pairs(episodes):
    require(type(episodes) is list and 1<=len(episodes)<=4096,'invalid-episode-roster')
    seen=set();ratios=[];fallback_ratios=[];failed=0;fallback=0;runtime_complete=0
    for episode in episodes:
        keys(episode,('version','episodeId','provenance','independentUnit','arms','costs','status','utilityAccepted','executionAuthorization','receiptDigest'))
        require(episode['version']=='agent-braid-synthetic-policy-experiment-v1'
                and episode['provenance']=='authentic-on-synthetic' and episode['utilityAccepted'] is False
                and episode['executionAuthorization'] is False
                and episode['independentUnit']=='owned-synthetic-recipe-not-real-workload','invalid-experiment-scope')
        pin(episode['episodeId'])
        require(episode['episodeId'] not in seen,'duplicate-independent-episode');seen.add(episode['episodeId'])
        require(episode['receiptDigest']==digest({k:v for k,v in episode.items() if k!='receiptDigest'}),'experiment-receipt-drift')
        arms=episode['arms'];require(len(arms)==3 and {r['arm'] for r in arms}=={'serial-reference','non-model-reference','forecast-choice'},'incomplete-paired-roster')
        require({r['orderIndex'] for r in arms}=={0,1,2} and len({pin(r['inputDigest']) for r in arms})==1,'paired-input-or-order-drift')
        for row in arms:
            require(row['status'] in ('completed','failed') and row['mode'] in ('serial','parallel')
                    and row['sourceKind']=='authentic-on-synthetic','invalid-arm-scope')
            integer(row['wallNs'],1)
            if row['status']=='completed':require(type(row['resultTree']) is str and len(row['resultTree']) in (40,64),'missing-verified-tree')
        completed=[r['resultTree'] for r in arms if r['status']=='completed'];require(len(set(completed))<=1,'non-equivalent-arm-outcomes')
        costs=episode['costs'];keys(costs,('episodeWallNs','armWallNs','sessionCleanupNs','coordinatorResidualNs','boundary','exportIncluded','externalSessionLifecycleIncluded','cpuNs','cpuReason','memoryBytes','memoryReason'))
        for name in ('episodeWallNs','armWallNs','sessionCleanupNs','coordinatorResidualNs'):integer(costs[name])
        require(costs['armWallNs']==sum(r['wallNs'] for r in arms)
                and costs['episodeWallNs']==costs['armWallNs']+costs['sessionCleanupNs']+costs['coordinatorResidualNs']
                and costs['boundary']=='data-compilation-through-arm-cleanup-and-owned-session-cleanup'
                and costs['exportIncluded'] is False and type(costs['externalSessionLifecycleIncluded']) is bool
                and costs['cpuNs'] is costs['memoryBytes'] is None
                and costs['cpuReason']==costs['memoryReason']=='not-observed','experiment-cost-drift')
        if not all(r['status']=='completed' for r in arms):failed+=1;continue
        runtime_complete+=1
        reference=next(r for r in arms if r['arm']=='non-model-reference');chosen=next(r for r in arms if r['arm']=='forecast-choice')
        integer(reference['wallNs'],1);integer(chosen['wallNs'],1)
        if chosen['forecastStatus']!='forecast':fallback+=1;fallback_ratios.append(reference['wallNs']/chosen['wallNs']);continue
        ratios.append(reference['wallNs']/chosen['wallNs'])
    return {'intendedEpisodes':len(episodes),'completeEpisodes':len(ratios),'invalidEpisodes':failed,'pairedRatios':ratios,
            'runtimeCompleteEpisodes':runtime_complete,'fallbackEpisodes':fallback,'fallbackDiagnosticRatios':fallback_ratios,
            'status':'inconclusive' if failed or fallback else 'synthetic-descriptive','utilityAccepted':False,'realWorkloadEvidence':False}


def simulate_frozen_policy_arms(signals, operations, *, evaluation, frozen, mode='shadow'):
    """Rehearse frozen paired decisions only; no Git, session, operator or worker.

    This distinct offline path binds the development-selected reference and both
    synthetic candidate identities. It does not upgrade the historical measured
    fixture harness above into a registered or forecast-authorized experiment.
    """
    from .forecast_decisions import simulate_decisions
    return simulate_decisions(signals, operations, evaluation=evaluation, frozen=frozen, mode=mode)


def rehearse_frozen_policy_arms(signals, operations, **kwargs):
    """Integrate frozen decisions with the in-memory paired rehearsal only.

    This does not call the older measured Git harness or any operator/runtime.
    """
    from .forecast_pairs import rehearse_paired_policies
    return rehearse_paired_policies(signals, operations, **kwargs)
