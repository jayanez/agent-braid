# SPDX-License-Identifier: AGPL-3.0-only
"""Core-only adversarial integration with real native replay and preparation."""
from copy import deepcopy
from pathlib import Path
import pickle
import time
import unittest
from unittest.mock import patch

import test_system_one_verified_selection as fixtures
from agent_braid import git_replay, git_runtime
from agent_braid import system_one_verified_consumers as consumers
from agent_braid.system_one import canonical, digest, thaw, CancellationToken


class VerifiedCoreConsumerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.VerifiedSelectionTests.setUpClass()
        cls.fixture = fixtures.VerifiedSelectionTests.fixture
        cls.observations = []

    @classmethod
    def tearDownClass(cls):
        fixtures.VerifiedSelectionTests.tearDownClass()

    def setUp(self):
        self.builder = fixtures.VerifiedSelectionTests()
        self.builder.setUp()

    def request(self, language='en', representation='controlled'):
        return self.builder.request(language, representation)

    def open(self, request=None, **kwargs):
        return consumers.CoreRequestContext(canonical(request or self.request()), self.fixture.owned, **kwargs)

    def rehash(self, value):
        value['proposalDigest'] = digest({k: v for k, v in value.items() if k != 'proposalDigest'})
        return canonical(value)

    def test_actual_native_four_views_and_complete_body_shared_budget(self):
        before = self.fixture.inventory()
        selected, trees = [], []
        for lang in ('en', 'es'):
            for representation in ('symbolic', 'controlled'):
                with self.subTest(lang=lang, representation=representation), self.open(self.request(lang, representation)) as c:
                    proposal = c.propose()
                    producer = proposal['decision']
                    budget = c.context.git_budget
                    commands = budget.commands
                    result = c.consume(canonical(proposal))
                    self.assertEqual(result['status'], 'answered', thaw(result))
                    self.assertIs(c.context.git_budget, budget)
                    self.assertGreater(budget.commands, commands)
                    self.assertEqual(result['usage']['gitCommands'], budget.commands)
                    self.assertEqual(set(result), {'format', 'consumerId', 'requestDigest',
                        'proposalDigest', 'decisionDigest', 'status', 'reasonCodes', 'preparedDigest',
                        'evidence', 'counters', 'usage', 'executionAuthorization'})
                    self.assertEqual(result['decisionDigest'], digest(producer))
                    self.assertEqual(result['proposalDigest'], proposal['proposalDigest'])
                    self.assertEqual(result['requestDigest'], proposal['requestDigest'])
                    self.assertEqual(result['preparedDigest'], digest(c.prepared))
                    self.assertEqual(c.prepared['request'], proposal['runtimeRequest'])
                    self.assertEqual(c.prepared['steps'][-1]['outputTree'], result['evidence']['expectedFinalTree'])
                    self.assertEqual(result['evidence'], {'nativeVerified': True,
                        'expectedFinalTree': proposal['runtimeRequest']['expectedFinalTree'],
                        'observedFinalTree': proposal['runtimeRequest']['expectedFinalTree'], 'preparedBodyChecked': True})
                    self.assertEqual(thaw(result['counters']), {'acquisitionCalls': 2, 'verifierCalls': 2,
                        'treeBuildCalls': 2, 'nativeCalls': 1, 'consumerCalls': 1, 'executeCalls': 0,
                        'recoverCalls': 0, 'grantWrites': 0, 'persistentRunAllocations': 0})
                    self.assertEqual(result['usage']['cleanup'], 'removed')
                    self.assertEqual(result['usage']['termination'], 'stopped')
                    self.assertIsInstance(result['usage']['prepareNs'], int)
                    self.assertGreater(result['usage']['prepareNs'], 0)
                    self.assertEqual(result['usage']['prepareNs'], result['usage']['entryToCleanupNs'])
                    self.assertEqual(producer['usage']['cleanup'], 'unknown')
                    self.assertIsNone(producer['usage']['prepareNs'])
                    self.assertFalse(result['executionAuthorization'])
                    self.assertFalse(c.prepared['sourcePromotion'])
                    self.assertFalse(Path(c.prepared['runDirectory']).exists())
                    names = [s['name'] for s in result['usage']['stages']]
                    for name in ('expectedTree', 'handoffRevalidation', 'nativeCheck', 'nativePrepare', 'cleanup'):
                        self.assertIn(name, names)
                    selected.append(producer['selectedOptionId']);trees.append(result['evidence']['expectedFinalTree'])
                    type(self).observations.append({'case':'two-operation-positive','language':lang,
                        'representation':representation,'expected':'answered','result':thaw(result)})
                    self.assertEqual(c.context.publish()['status'], 'answered')
                    with self.assertRaises(TypeError):result['status'] = 'refused'
        self.assertEqual(selected, ['k0'] * 4)
        self.assertEqual(len(set(trees)), 1)
        self.assertEqual(self.fixture.inventory(), before)

    def test_defer_both_languages_never_reaches_tree_native_or_prepare(self):
        for lang in ('en', 'es'):
            request = self.request(lang)
            request['source']['task']['options'] = {'k0': ['a', 'a'], 'k1': [], 'k2': ['b'], 'wait': None}
            program = deepcopy(self.builder.program);program['plans'] = deepcopy(request['source']['task']['options'])
            from agent_braid import system_one_verified_ir as ir
            request['interpretation'] = thaw(ir.render(program, lang, 'controlled', checkpoint=lambda *_: None))
            with self.subTest(lang=lang), self.open(request) as c, patch.object(git_replay, 'produce', side_effect=AssertionError('unexpected native')), patch.object(git_runtime, 'prepare_run', side_effect=AssertionError('unexpected prepare')):
                proposal = c.propose();result = c.consume(canonical(proposal))
                self.assertEqual(result['status'], 'semantic-defer', thaw(result))
                type(self).observations.append({'case':'no-valid-offered-plan','language':lang,
                    'representation':'controlled','expected':'semantic-defer','result':thaw(result)})
                self.assertIsNone(proposal['runtimeRequest']);self.assertIsNone(c.prepared)
                self.assertEqual(result['reasonCodes'], ('no-goal-reaching-plan',))
                self.assertTrue(all(v is None for v in result['evidence'].values()))
                for name in ('treeBuildCalls', 'nativeCalls', 'consumerCalls'):
                    self.assertEqual(result['counters'][name], 0)

    def test_forged_rehashed_bodies_refuse_before_fresh_source_or_native(self):
        for lang in ('en', 'es'):
            for target in ('consumer', 'choice', 'tree', 'snapshot', 'request', 'extra'):
                with self.subTest(lang=lang, target=target), self.open(self.request(lang)) as c:
                    proposal = thaw(c.propose())
                    if target == 'consumer':proposal['consumerId'] = 'mcp-service'
                    elif target == 'choice':
                        proposal['decision']['selectedOptionId'] = 'k1'
                        proposal['decisionDigest'] = digest(proposal['decision'])
                    elif target == 'tree':proposal['runtimeRequest']['expectedFinalTree'] = '1' * 40
                    elif target == 'snapshot':
                        proposal['snapshot']['program']['goal']['first.txt'] = '1' * 40
                        proposal['snapshot']['irDigest'] = digest(proposal['snapshot']['program'])
                    elif target == 'request':
                        proposal['request']['budgets']['maxGitCommands'] = 512
                        proposal['request']['requestId'] = 'another-request'
                        proposal['requestDigest'] = digest(proposal['request'])
                    else:proposal['confidence'] = 1
                    used = c.context.git_budget.commands
                    result = c.consume(self.rehash(proposal))
                    self.assertEqual(result['status'], 'refused')
                    self.assertEqual(c.context.git_budget.commands, used)
                    self.assertEqual(result['counters']['acquisitionCalls'], 1)
                    self.assertEqual(result['counters']['nativeCalls'], 0)
                    self.assertEqual(result['counters']['consumerCalls'], 0)
                    self.assertIsNone(result['preparedDigest'])
                    type(self).observations.append({'case':'forged-'+target,'language':lang,
                        'representation':'controlled','expected':'refused','result':thaw(result)})

    def test_raw_duplicate_bom_extra_and_size_refuse_without_dispatch(self):
        for mutate in (lambda b:b'{"format":0,'+b[1:], lambda b:b'\xef\xbb\xbf'+b, lambda b:b+b'x', lambda b:b' '*(1048577)):
            with self.open() as c:
                proposal = c.propose();used=c.context.git_budget.commands
                result=c.consume(mutate(canonical(proposal)))
                self.assertEqual(result['status'], 'refused')
                self.assertEqual(c.context.git_budget.commands, used)
                self.assertEqual(result['counters']['nativeCalls'], 0)

    def test_external_proposal_cannot_manufacture_active_binding(self):
        with self.open() as original:
            raw=canonical(original.propose())
        with self.open() as other:
            result=other.consume(raw)
            self.assertEqual(result['status'], 'refused')
            self.assertIn('evidence-incomplete',result['reasonCodes'])
            self.assertEqual(result['counters']['nativeCalls'],0)
        with self.open() as c:
            c.propose()
            with self.assertRaises(TypeError):pickle.dumps(c)

    def test_k0_invalid_selects_k1_both_languages(self):
        from agent_braid import system_one_verified_ir as ir
        for lang in ('en','es'):
            request=self.request(lang);request['source']['task']['options']['k0']=['a','a']
            program=deepcopy(self.builder.program);program['plans']['k0']=['a','a']
            request['interpretation']=thaw(ir.render(program,lang,'controlled',checkpoint=lambda *_:None))
            result,body=consumers.prepare_core(canonical(request),self.fixture.owned)
            self.assertEqual(result['status'],'answered',thaw(result));self.assertEqual(body['request']['order'],('b','a'))

    def test_source_loss_and_registry_drift_stop_before_native(self):
        from agent_braid import system_one_verified_registry as registry
        for lang in ('en','es'):
            with self.open(self.request(lang)) as c:
                raw=canonical(c.propose())
                with patch.object(registry,'resolve',side_effect=ValueError('verifier-mismatch')):
                    result=c.consume(raw)
                self.assertEqual(result['status'],'refused');self.assertEqual(result['counters']['nativeCalls'],0)
            with self.open(self.request(lang)) as c:
                raw=canonical(c.propose());marker=self.fixture.repo/'.owned-native-fixture';contents=marker.read_bytes();marker.unlink()
                try:result=c.consume(raw)
                finally:marker.write_bytes(contents)
                self.assertEqual(result['status'],'refused');self.assertEqual(result['counters']['nativeCalls'],0)

    def test_shared_command_and_byte_allowances_cannot_restart(self):
        for field in ('maxGitCommands','maxOutputBytes'):
            with self.open() as c:
                raw=canonical(c.propose());budget=c.context.git_budget
                if field=='maxGitCommands':budget.max_commands=budget.commands
                else:budget.max_output_bytes=budget.output_bytes
                result=c.consume(raw)
                self.assertEqual(result['status'],'refused')
                self.assertEqual(result['counters']['nativeCalls'],0)
                self.assertIs(c.context.git_budget,budget)

    def test_native_disagreement_and_prepared_body_drift_refuse(self):
        actual=git_replay.produce
        with self.open() as c:
            raw=canonical(c.propose())
            def bad(*args,**kwargs):
                bundle,plan=actual(*args,**kwargs)
                bundle['schedules'][0]['finalTree']='1'*40
                bundle['evidenceDigest']=git_replay._bundle_digest(bundle)
                plan['evidenceDigest']=bundle['evidenceDigest'];plan['planDigest']=git_replay._plan_digest(plan)
                return bundle,plan
            with patch.object(git_replay,'produce',side_effect=bad):result=c.consume(raw)
            self.assertEqual(result['status'],'refused');self.assertIn('target-tree-mismatch',result['reasonCodes'])
            self.assertEqual(result['counters']['consumerCalls'],0)
        actualprepare=git_runtime.prepare_run
        with self.open() as c:
            raw=canonical(c.propose())
            def badprepare(*args,**kwargs):
                body=actualprepare(*args,**kwargs);body['request']['expectedFinalTree']='1'*40;return body
            with patch.object(git_runtime,'prepare_run',side_effect=badprepare):result=c.consume(raw)
            self.assertEqual(result['status'],'refused');self.assertIsNone(c.prepared)

    def test_cancellation_during_native_preparation_and_sealing_suppresses_success(self):
        actual=git_runtime.prepare_run
        for where in ('prepare','seal'):
            token=CancellationToken()
            with self.subTest(where=where),self.open(cancellation=token) as c:
                raw=canonical(c.propose())
                def cancelprepare(*args,**kwargs):
                    value=actual(*args,**kwargs);token.cancel();return value
                record=c._record
                def cancelrecord(*args):
                    value=record(*args);token.cancel();return value
                with patch.object(git_runtime,'prepare_run',side_effect=cancelprepare if where=='prepare' else actual),patch.object(c,'_record',side_effect=cancelrecord if where=='seal' else record):
                    result=c.consume(raw)
                self.assertEqual(result['status'],'refused');self.assertIsNone(c.prepared)
                self.assertIn('cancelled',result['reasonCodes']);self.assertEqual(result['usage']['cleanup'],'removed')
            token.claim();token.release()

    def test_stage_command_cap_checks_real_shared_native_entry(self):
        now=[time.monotonic_ns()]
        with self.open(clock=lambda:now[0]) as c:
            raw=canonical(c.propose());actual=git_replay.produce
            def expired(*args,**kwargs):
                now[0]+=30_000_000_000
                return actual(*args,**kwargs)
            with patch.object(git_replay,'produce',side_effect=expired):result=c.consume(raw)
            self.assertEqual(result['status'],'refused');self.assertIn('deadline-exceeded',result['reasonCodes'])
            self.assertEqual(result['counters']['consumerCalls'],0)

    def test_invalid_ingress_and_no_execution_or_recovery_entry(self):
        for raw in (b'{}',b'{"format":NaN}'):
            with patch.object(git_runtime,'execute_run',side_effect=AssertionError('execute forbidden')),patch.object(git_runtime,'recover_run',side_effect=AssertionError('recover forbidden')):
                result,body=consumers.prepare_core(raw,self.fixture.owned)
            self.assertEqual(result['status'],'refused');self.assertIsNone(body)
            for name in ('nativeCalls','consumerCalls','executeCalls','recoverCalls','grantWrites','persistentRunAllocations'):
                self.assertEqual(result['counters'][name],0)

    def test_default_native_apis_remain_compatible_and_budget_identity_is_exact(self):
        with self.open() as c:
            proposal=c.propose();request=thaw(proposal['runtimeRequest'])
            analysis={k:request[k] for k in ('repository','baseRevision','operations')}
            analysis=deepcopy(analysis);analysis['gitAnalysisRequestVersion']='0.1.0-alpha'
            analysis['operations']=[{k:v for k,v in op.items() if k!='declaredWrites'} for op in analysis['operations']]
            normal=git_replay.produce(analysis)
            with c._phase('nativeCheck'):shared=git_replay.produce(analysis,budget=c.context.git_budget)
            self.assertEqual(normal,shared)

    def test_native_summary_without_complete_evidence_is_rejected(self):
        with self.open() as c:
            raw=canonical(c.propose())
            with patch.object(git_replay,'produce',return_value=({'schedules':[]}, {'executionAuthorization':False,'verificationStatus':'verified'})):
                result=c.consume(raw)
            self.assertEqual(result['status'],'refused')
            self.assertIn('native-not-verified',result['reasonCodes'])
            self.assertEqual(result['counters']['consumerCalls'],0)

    def test_three_and_four_operations_multifile_with_unchanged_base_entry(self):
        import test_system_one_verified_acquisition as acquisition_fixtures
        from agent_braid import system_one_verified_ir as ir
        f=acquisition_fixtures.VerifiedAcquisitionTests();f.setUp();self.addCleanup(f.doCleanups)
        for name,path in (('c','third.txt'),('d','fourth.txt')):
            f.git('reset','--hard',f.base)
            (f.repo/path).write_text(name+'-addition\n')
            f.git('add',path);f.git('commit','-m',name)
            f.sources[name]=f.git('rev-parse','HEAD').decode().strip()
            f.fixture['operations'][name]={path:[name+'-addition\n']}
        f.git('reset','--hard',f.base)
        for count in (3,4):
            original_sources=deepcopy(f.sources);original_operations=deepcopy(f.fixture['operations'])
            f.sources={k:v for k,v in original_sources.items() if k in 'abcd'[:count]}
            f.fixture['operations']={k:v for k,v in original_operations.items() if k in 'abcd'[:count]}
            source=f.make_source();order=list('abcd'[:count])
            source['task']['options']={'k0':order,'k1':order[::-1],'k2':['a','a'],'wait':None}
            program=f.acquire(source=source)['program']
            for lang in ('en','es'):
                request=self.request(lang);request['source']=source
                request['interpretation']=thaw(ir.render(program,lang,'controlled',checkpoint=lambda *_:None))
                with self.subTest(count=count,lang=lang), consumers.CoreRequestContext(canonical(request),f.owned) as c:
                    proposal=c.propose();result=c.consume(canonical(proposal))
                    self.assertEqual(result['status'],'answered',thaw(result))
                    self.assertEqual(len(c.prepared['steps']),count)
                    self.assertEqual(c.prepared['request']['order'],tuple(order))
                    self.assertEqual(c.prepared['baseTree'],f.git('rev-parse',f.base+'^{tree}').decode().strip())
                    self.assertEqual(c.prepared['steps'][-1]['outputTree'],proposal['runtimeRequest']['expectedFinalTree'])
                    type(self).observations.append({'case':str(count)+'-operation-positive','language':lang,
                        'representation':'controlled','expected':'answered','result':thaw(result)})
            f.sources=original_sources;f.fixture['operations']=original_operations

    def test_failed_seal_factory_is_terminal_before_token_reuse(self):
        token=CancellationToken()
        with self.open(cancellation=token) as c:
            c.propose()
            def fail(_):raise RuntimeError('local factory diagnostic')
            with self.assertRaises(RuntimeError):c.context.seal(fail)
            # Let the next owner claim BEFORE any idempotent publish call, so
            # this regression cannot accidentally seal the broken old context.
            token.claim()
            try:
                with patch.object(c.context,'_build',side_effect=AssertionError('must never retry')):
                    with self.assertRaisesRegex(ValueError,'invalid-envelope'):
                        c.context.seal(lambda decision:decision)
                self.assertEqual(c.context.publish()['status'],'refused')
                self.assertEqual(c.context.publish()['reasonCodes'],('internal-failure',))
            finally:token.release()

    def test_consumer_factory_failure_returns_only_terminal_refusal(self):
        with self.open() as c:
            raw=canonical(c.propose());record=c._record;calls=[]
            def fail_once(decision):
                calls.append(decision['status'])
                if len(calls)==1:raise RuntimeError('result construction failure')
                return record(decision)
            with patch.object(c,'_record',side_effect=fail_once):result=c.consume(raw)
            self.assertEqual(calls,['answered','refused'])
            self.assertEqual(result['status'],'refused')
            self.assertEqual(result['reasonCodes'],('internal-failure',))
            self.assertIsNone(c.prepared);self.assertIsNone(result['preparedDigest'])

    def test_known_consumer_reasons_are_exact_without_spurious_internal_failure(self):
        for field,value,reason in (('consumerId','mcp-service','consumer-mismatch'),
                                   ('runtimeRequest',None,'runtime-request-mismatch')):
            with self.subTest(field=field),self.open() as c:
                proposal=thaw(c.propose());proposal[field]=value
                result=c.consume(self.rehash(proposal))
                self.assertEqual(result['status'],'refused')
                self.assertEqual(result['reasonCodes'],(reason,))

    def test_cancel_before_revalidation_does_not_count_unentered_work(self):
        token=CancellationToken()
        with self.open(cancellation=token) as c:
            raw=canonical(c.propose());commands=c.context.git_budget.commands;token.cancel()
            result=c.consume(raw)
            self.assertEqual(result['status'],'refused')
            self.assertEqual(result['reasonCodes'],('cancelled',))
            self.assertEqual(result['counters']['acquisitionCalls'],1)
            self.assertEqual(result['counters']['verifierCalls'],1)
            self.assertEqual(result['usage']['gitCommands'],commands)
            self.assertEqual(result['counters']['nativeCalls'],0)

    def test_failed_registry_revalidation_counts_only_actual_verifier_entries(self):
        from agent_braid import system_one_verified_registry as registry
        with self.open() as c:
            raw=canonical(c.propose())
            with patch.object(registry,'resolve',side_effect=ValueError('verifier-mismatch')):
                result=c.consume(raw)
            self.assertEqual(result['counters']['acquisitionCalls'],2)
            self.assertEqual(result['counters']['verifierCalls'],1)
            self.assertEqual(result['reasonCodes'],('verifier-mismatch',))

    def test_native_prepare_resource_caps_are_not_relaxed_by_outer_budget(self):
        from agent_braid.git_process import GitCommandLimitExceeded,GitExecutionTimeout
        # Native preparation's 2MiB per-command cap is stricter than the outer8MiB.
        with self.open() as c:
            c.propose();budget=c.context.git_budget
            with c._phase('nativePrepare'):
                budget.begin_command(30)
                self.assertTrue(budget.record_output(2*1024*1024))
                self.assertFalse(budget.record_output(1))
            self.assertEqual(budget.max_command_output_bytes,8*1024*1024)
        # The original8MiB native aggregate output cap remains stricter than16MiB outer.
        with self.open() as c:
            c.propose();budget=c.context.git_budget
            with c._phase('nativePrepare'):
                for _ in range(4):
                    budget.begin_command(30);self.assertTrue(budget.record_output(2*1024*1024))
                budget.begin_command(30);self.assertFalse(budget.record_output(1))
            self.assertEqual(budget.max_output_bytes,16*1024*1024)
        # Count *admissions*, with no child spawned in this boundary control.
        with self.open() as c:
            c.propose();budget=c.context.git_budget
            with self.assertRaises(GitCommandLimitExceeded):
                with c._phase('nativePrepare'):
                    for _ in range(257):budget.begin_command(30)
            self.assertEqual(budget.max_commands,512)
        now=[time.monotonic_ns()];request=self.request()
        request['budgets']['prepareBudgetMs']=300000
        request['budgets']['stageBudgetMs']['nativePrepare']=180000
        with self.open(request,clock=lambda:now[0]) as c:
            c.propose();budget=c.context.git_budget
            with self.assertRaises(GitExecutionTimeout):
                with c._phase('nativePrepare'):
                    now[0]+=60_000_000_000
                    budget.begin_command(30)
