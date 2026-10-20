# SPDX-License-Identifier: AGPL-3.0-only
"""Owned software-only end-to-end selection; no research labels/models/consumers."""
from copy import deepcopy
from pathlib import Path
import pickle
import shutil
import tempfile
import unittest
from unittest.mock import patch

# Import the module, not its TestCase: unittest must not rediscover its tests here.
import test_system_one_verified_acquisition as fixture_builder
from agent_braid import git_process
from agent_braid import system_one_verified_acquisition as acquisition
from agent_braid import system_one_verified_ir as ir
from agent_braid import system_one_verified_registry as registry
from agent_braid import system_one_verified_selection as selection
from agent_braid.system_one import CancellationToken, canonical, digest, freeze, thaw


class VerifiedSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = fixture_builder.VerifiedAcquisitionTests()
        cls.fixture.setUp()
        observed = cls.fixture.acquire()
        cls.program = thaw(observed['program'])
        cls.original_inventory = cls.fixture.inventory()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def setUp(self):
        self.source = deepcopy(self.fixture.source)
        self.program = deepcopy(type(self).program)

    def budgets(self):
        return {'decisionBudgetMs': 30000, 'acquisitionBudgetMs': 60000, 'prepareBudgetMs': 120000,
            'stageBudgetMs': {name: 1000 if name == 'cleanup' else 30000 for name in selection._STAGES},
            'maxHunkApplications': 128, 'maxGitCommands': 512, 'maxOutputBytes': 16777216,
            'maxCommandOutputBytes': 8388608, 'maxScratchBytes': 67108864, 'terminationMode': 'cooperative'}

    def request(self, language='en', representation='controlled'):
        return {'format': 's1-verified-request-v1', 'requestId': 'owned-request', 'source': deepcopy(self.source),
            'interpretation': thaw(ir.render(self.program, language, representation, checkpoint=lambda *_: None)),
            'budgets': self.budgets(), 'executionAuthorization': False}

    def run_request(self, request=None, **kwargs):
        return selection.evaluate(canonical(request or self.request()), self.fixture.owned, **kwargs)

    def test_four_views_actual_source_selection_and_exact_bodies(self):
        for language in ('en', 'es'):
            for representation in ('controlled', 'symbolic'):
                with self.subTest(language=language, representation=representation):
                    request = self.request(language, representation)
                    with selection.VerifiedRequestContext(canonical(request), self.fixture.owned) as context:
                        producer = context.decide()
                        self.assertEqual(producer['status'], 'answered')
                        self.assertEqual(producer['selectedOptionId'], 'k0')
                        self.assertEqual(producer['reasonCodes'], ())
                        self.assertEqual(producer['usage']['cleanup'], 'unknown')
                        bodies = context.evidence
                        self.assertEqual(set(bodies), {'snapshot', 'interpretation', 'verifierResult'})
                        snapshot, verifier = bodies['snapshot'], bodies['verifierResult']
                        self.assertEqual(set(snapshot), {'format', 'sourceRequestDigest', 'snapshot',
                            'snapshotDigest', 'domainId', 'irVersion', 'irDigest', 'grammarVersion',
                            'observationContract', 'bounds', 'program', 'observedEffects', 'declaredEffects',
                            'coverage', 'executionAuthorization'})
                        self.assertEqual(set(verifier), {'format', 'registryDigest', 'verifierDigest',
                            'snapshotDigest', 'irDigest', 'optionIds', 'plans', 'eligibleOptionIds',
                            'status', 'reasonCodes', 'executionAuthorization'})
                        self.assertEqual(snapshot['sourceRequestDigest'], digest(request['source']))
                        self.assertEqual(snapshot['snapshotDigest'], digest(snapshot['snapshot']))
                        self.assertEqual(snapshot['irDigest'], digest(snapshot['program']))
                        self.assertEqual(producer['requestDigest'], digest(request))
                        self.assertEqual(producer['snapshotDigest'], snapshot['snapshotDigest'])
                        self.assertEqual(producer['irDigest'], snapshot['irDigest'])
                        self.assertEqual(producer['registryDigest'], selection._REGISTRY_DIGEST)
                        self.assertEqual(producer['verifierDigest'], selection._VERIFIER_PIN)
                        self.assertEqual(producer['policyDigest'], digest(selection._POLICY))
                        self.assertEqual(producer['eligibilityDigest'], digest(verifier))
                        task = request['source']['task']
                        self.assertEqual(producer['optionSetDigest'], digest({'options': task['options'], 'optionOrder': task['optionOrder']}))
                        self.assertEqual(verifier['eligibleOptionIds'], ('k0', 'k1'))
                        self.assertEqual(tuple(plan['optionId'] for plan in verifier['plans']), ('k2', 'k0', 'k1'))
                        expected = (('snapshot', snapshot), ('interpretation', request['interpretation']), ('verifier-result', verifier))
                        self.assertEqual(producer['evidenceRefs'], freeze([{'kind': kind, 'digest': digest(body)} for kind, body in expected]))
                        self.assertNotEqual(producer['evidenceRefs'][0]['digest'], producer['snapshotDigest'])
                        self.assertEqual(snapshot['program'], freeze(self.program))
                        self.assertTrue(all(set(plan) == {'optionId', 'valid', 'complete', 'goalAchieved',
                            'cost', 'failure', 'trace', 'finalBlobs'} for plan in verifier['plans']))
                        with self.assertRaises(TypeError):
                            bodies['snapshot']['program']['files']['new.txt'] = ()
                    final = context.decision
                    self.assertEqual(final['status'], 'answered')
                    self.assertEqual(final['usage']['cleanup'], 'removed')
                    self.assertEqual(final['usage']['termination'], 'stopped')
                    self.assertGreater(final['usage']['gitCommands'], 0)
                    self.assertGreater(final['usage']['acquisitionNs'], 0)
                    self.assertGreater(final['usage']['decisionNs'], 0)
                    self.assertGreater(final['usage']['cleanupNs'], 0)
                    self.assertIsNone(final['usage']['prepareNs'])
                    self.assertEqual(producer['usage']['cleanup'], 'unknown')
                    self.assertIs(context.publish(), final)
                    self.assertFalse(context.git_budget.temp_root.exists())
                    self.assertEqual(self.fixture.inventory(), self.original_inventory)

    def test_exact_decision_shape_and_legacy_contract_unchanged(self):
        result = self.run_request()
        self.assertEqual(set(result), {'format', 'requestId', 'requestDigest', 'snapshotDigest', 'irDigest',
            'registryDigest', 'verifierDigest', 'policyDigest', 'optionSetDigest', 'eligibilityDigest',
            'status', 'selectedOptionId', 'reasonCodes', 'evidenceRefs', 'usage', 'executionAuthorization'})
        self.assertEqual(set(result['usage']), {'acquisitionNs', 'decisionNs', 'prepareNs', 'cleanupNs',
            'entryToCleanupNs', 'stages', 'hunkApplications', 'gitCommands', 'outputBytes', 'peakScratchBytes',
            'termination', 'cleanup'})
        from agent_braid.system_one import InvalidDecision, validate_response
        with self.assertRaises(InvalidDecision):
            validate_response(thaw(result), request=None)
        self.assertFalse(result['executionAuthorization'])

    def test_wrong_goal_is_defer_with_null_selection_and_complete_evidence(self):
        self.source['task']['goal'][0]['blob'] = '1' * 40
        self.program['goal'][self.source['task']['goal'][0]['path']] = '1' * 40
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned) as context:
            result = context.decide()
            self.assertEqual(result['status'], 'semantic-defer')
            self.assertIsNone(result['selectedOptionId'])
            self.assertEqual(result['reasonCodes'], ('no-goal-reaching-plan',))
            self.assertEqual(context.evidence['verifierResult']['eligibleOptionIds'], ('wait',))
            self.assertEqual(len(context.evidence['verifierResult']['plans']), 3)
        self.assertEqual(context.decision['status'], 'semantic-defer')

    def test_k0_invalid_still_selects_k1_and_retains_failed_plan(self):
        self.source['task']['options']['k0'] = ['a', 'a']
        self.program['plans']['k0'] = ['a', 'a']
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned) as context:
            result = context.decide()
            self.assertEqual(result['selectedOptionId'], 'k1')
            plans = {plan['optionId']: plan for plan in context.evidence['verifierResult']['plans']}
            self.assertEqual(plans['k0']['failure']['reason'], 'operation-precondition')

    def assert_early_refusal(self, raw, reason):
        with patch.object(acquisition, 'acquire') as acquire, patch.object(selection.tempfile, 'mkdtemp') as scratch:
            result = selection.evaluate(raw, self.fixture.owned)
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(result['reasonCodes'], (reason,))
        self.assertEqual(result['evidenceRefs'], ())
        self.assertIsNone(result['requestId'])
        self.assertIsNone(result['requestDigest'])
        self.assertIsNone(result['selectedOptionId'])
        self.assertEqual(result['usage']['termination'], 'not-started')
        self.assertEqual(result['usage']['cleanup'], 'not-allocated')
        acquire.assert_not_called()
        scratch.assert_not_called()

    def test_raw_parser_refuses_before_source_and_scratch(self):
        raw = canonical(self.request())
        variants = [(b'\xef\xbb\xbf' + raw, 'invalid-envelope'), (raw + b'{}', 'invalid-envelope'),
            (b'{"format":1,"format":2}', 'invalid-envelope'), (b'{"x":NaN}', 'invalid-envelope'),
            (b'{"x":' + b'[' * 17 + b'0' + b']' * 17 + b'}', 'invalid-envelope'),
            (b'{"x":"\\ud800"}', 'invalid-envelope'), (b'{"x":9223372036854775808}', 'invalid-envelope'),
            (b' ' * 1048577, 'input-budget-exceeded'), (raw.decode(), 'invalid-envelope')]
        for value, reason in variants:
            with self.subTest(raw=str(value)[:60]):
                self.assert_early_refusal(value, reason)

    def test_exact_budgets_types_keys_ranges_before_source(self):
        edits = [lambda b: b.pop('prepareBudgetMs'), lambda b: b.update(terminationMode='hard'),
            lambda b: b.update(hiddenContext=True), lambda b: b.update(decisionBudgetMs=True),
            lambda b: b.update(maxHunkApplications=129), lambda b: b.update(maxGitCommands=0),
            lambda b: b.update(maxOutputBytes=1), lambda b: b.update(maxScratchBytes=67108865),
            lambda b: b['stageBudgetMs'].update(extra=1), lambda b: b['stageBudgetMs'].pop('cleanup'),
            lambda b: b['stageBudgetMs'].update(verification=30001),
            lambda b: b['stageBudgetMs'].update(acquisition=60001)]
        for edit in edits:
            request = self.request()
            edit(request['budgets'])
            with self.subTest(edit=edit):
                self.assert_early_refusal(canonical(request), 'invalid-budget')

    def test_exact_envelope_source_and_interpretation_fields(self):
        cases = [(lambda r: r.update(confidence=1), 'invalid-envelope'),
            (lambda r: r.update(executionAuthorization=True), 'invalid-envelope'),
            (lambda r: r.update(format='decision-stdlib-v1'), 'unsupported-version'),
            (lambda r: r.update(requestId='\x00bad'), 'invalid-envelope'),
            (lambda r: r['source']['task']['request'].update(baseRevision='HEAD'), 'invalid-envelope'),
            (lambda r: r['source']['task']['goal'][0].update(blob='0' * 40), 'invalid-envelope'),
            (lambda r: r['source']['task']['request']['operations'][0].update(uncertainPaths=['first.txt']), 'incomplete-observation'),
            (lambda r: r['interpretation'].update(confidence=1), 'invalid-envelope'),
            (lambda r: r['interpretation'].update(executionAuthorization=True), 'invalid-envelope'),
            (lambda r: r['interpretation'].update(language='fr'), 'text-mismatch')]
        for edit, reason in cases:
            request = self.request()
            edit(request)
            with self.subTest(edit=edit):
                self.assert_early_refusal(canonical(request), reason)

    def test_text_goal_and_declaration_mismatches_refuse_without_partial_plans(self):
        request = self.request()
        payload_program = deepcopy(self.program)
        payload_program['goal']['first.txt'] = '1' * 40
        request['interpretation'] = thaw(ir.render(payload_program, 'en', 'controlled', checkpoint=lambda *_: None))
        result = self.run_request(request)
        self.assertEqual(result['reasonCodes'], ('text-mismatch',))
        self.assertEqual(result['evidenceRefs'], ())
        self.assertIsNone(result['eligibilityDigest'])
        request = self.request()
        request['source']['declaredEffects']['a'][0]['after'] = '1' * 40
        self.assertEqual(self.run_request(request)['reasonCodes'], ('declaration-mismatch',))

    def test_registry_source_drift_and_exception_text_are_sanitized(self):
        with tempfile.TemporaryDirectory() as folder:
            changed = Path(folder) / 'changed.py'
            changed.write_text('changed source\n')
            with patch.object(registry, '_VERIFIER_SOURCE', changed):
                result = self.run_request()
        self.assertEqual(result['reasonCodes'], ('verifier-mismatch',))
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(result['evidenceRefs'], ())
        with patch.object(acquisition, 'acquire', side_effect=RuntimeError('/private/path secret stderr')):
            result = self.run_request()
        self.assertEqual(result['reasonCodes'], ('internal-failure',))
        self.assertNotIn('secret', str(result))

    def test_shared_budget_reacquisition_and_reverification_no_reset(self):
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned) as context:
            producer = context.decide()
            budget, started = context.git_budget, context.git_budget.started_at
            commands, output, hunks = budget.commands, budget.output_bytes, producer['usage']['hunkApplications']
            snapshot = context.reacquire()
            self.assertEqual(snapshot, context.evidence['snapshot'])
            self.assertIs(context.git_budget, budget)
            self.assertEqual(budget.started_at, started)
            self.assertEqual(budget.commands, commands * 2)
            self.assertEqual(budget.output_bytes, output * 2)
            self.assertEqual(context.revalidate(), context.evidence['verifierResult'])
            self.assertEqual(budget.commands, commands * 3)
            self.assertEqual(context._hunks, hunks * 2)
            self.assertEqual(context._counts['verification'], 4)
        self.assertEqual(context.decision['status'], 'answered')
        self.assertEqual(context.decision['usage']['gitCommands'], commands * 3)
        self.assertEqual(context.decision['usage']['hunkApplications'], hunks * 2)

    def test_shared_command_counter_refuses_before_another_child(self):
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned) as context:
            context.decide()
            budget = context.git_budget
            commands = budget.commands
            budget.max_commands = commands  # trusted test tightens; never a wire reset
            with patch.object(git_process.subprocess, 'Popen', wraps=git_process.subprocess.Popen) as spawn:
                with self.assertRaisesRegex(ValueError, '^work-budget-exceeded$'):
                    context.reacquire()
                self.assertEqual(spawn.call_count, 0)
            self.assertEqual(budget.commands, commands + 1)
        self.assertEqual(context.decision['reasonCodes'], ('work-budget-exceeded',))

    def test_zero_and_aggregate_hunk_caps_never_publish_partial_answer(self):
        request = self.request()
        request['budgets']['maxHunkApplications'] = 0
        result = self.run_request(request)
        self.assertEqual(result['reasonCodes'], ('work-budget-exceeded',))
        self.assertIsNone(result['selectedOptionId'])
        request['budgets']['maxHunkApplications'] = 20
        with selection.VerifiedRequestContext(canonical(request), self.fixture.owned) as context:
            self.assertEqual(context.decide()['status'], 'answered')
            with self.assertRaisesRegex(ValueError, '^work-budget-exceeded$'):
                context.revalidate()
        self.assertEqual(context.decision['status'], 'refused')
        self.assertEqual(context.evidence, {})
        self.assertLessEqual(context.decision['usage']['hunkApplications'], 20)

    def test_existing_cancelled_token_and_shared_live_token_are_not_reset(self):
        token = CancellationToken()
        token.cancel()
        result = self.run_request(cancellation=token)
        self.assertEqual(result['reasonCodes'], ('cancelled',))
        self.assertTrue(token.cancelled)
        token = CancellationToken()
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned, cancellation=token) as outer:
            result = self.run_request(cancellation=token)
            self.assertEqual(result['reasonCodes'], ('invalid-envelope',))
            self.assertEqual(outer.decide()['status'], 'answered')
        self.assertEqual(self.run_request(cancellation=token)['status'], 'answered')

    def test_cancel_latches_to_same_git_event_and_prevents_reacquire(self):
        token = CancellationToken()
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned, cancellation=token) as context:
            context.decide()
            budget = context.git_budget
            commands = budget.commands
            token.cancel()
            self.assertTrue(budget.cancel_event.is_set())
            with patch.object(acquisition, 'acquire') as acquire:
                with self.assertRaisesRegex(ValueError, '^cancelled$'):
                    context.reacquire()
                acquire.assert_not_called()
            self.assertIs(context.git_budget, budget)
            self.assertEqual(budget.commands, commands)
        self.assertEqual(context.decision['reasonCodes'], ('cancelled',))
        self.assertEqual(context.decision['usage']['cleanup'], 'removed')

    def test_cancellation_between_cleanup_and_publication_wins(self):
        token = CancellationToken()
        context = selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned, cancellation=token)
        producer = context.decide()
        context.close()
        token.cancel()
        result = context.publish()
        self.assertEqual(result['reasonCodes'], ('cancelled',))
        self.assertEqual(producer['status'], 'answered')
        self.assertEqual(producer['usage']['cleanup'], 'unknown')
        for key in ('registryDigest', 'verifierDigest', 'policyDigest', 'eligibilityDigest'):
            self.assertEqual(result[key], producer[key])  # known pins survive; semantic bodies do not
        self.assertEqual(context.evidence, {})
        self.assertEqual(result['evidenceRefs'], ())
        self.assertIs(context.publish(), result)
        token.claim()
        token.release()

    def test_deadline_equality_and_cleanup_reservation_before_allocation(self):
        now = [0]
        request = self.request()
        request['budgets']['prepareBudgetMs'] = 30000
        request['budgets']['stageBudgetMs']['cleanup'] = 30000
        with patch.object(selection.tempfile, 'mkdtemp') as scratch:
            with selection.VerifiedRequestContext(canonical(request), self.fixture.owned, clock=lambda: now[0]) as context:
                self.assertEqual(context.decide()['reasonCodes'], ('deadline-exceeded',))
            scratch.assert_not_called()
        request = self.request()
        with selection.VerifiedRequestContext(canonical(request), self.fixture.owned, clock=lambda: now[0]) as context:
            now[0] = request['budgets']['prepareBudgetMs'] * 1000000
            with patch.object(acquisition, 'acquire') as acquire:
                self.assertEqual(context.decide()['reasonCodes'], ('deadline-exceeded',))
                acquire.assert_not_called()
        self.assertEqual(context.decision['usage']['cleanup'], 'removed')
        self.assertEqual(context.decision['status'], 'refused')

    def test_memoized_acquisition_and_decision_deadlines_do_not_restart(self):
        now = [selection.monotonic_ns()]
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned, clock=lambda: now[0]) as context:
            context.decide()
            end = context._acquire_end
            now[0] = end
            with patch.object(acquisition, 'acquire') as acquire:
                with self.assertRaisesRegex(ValueError, '^deadline-exceeded$'):
                    context.reacquire()
                acquire.assert_not_called()
            self.assertEqual(context._acquire_end, end)
        now[0] = selection.monotonic_ns()
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned, clock=lambda: now[0]) as context:
            context.decide()
            end = context._decision_end
            now[0] = end
            with self.assertRaisesRegex(ValueError, '^deadline-exceeded$'):
                context.revalidate()
            self.assertEqual(context._decision_end, end)
        self.assertEqual(context.decision['status'], 'refused')

    def test_stage_caps_nested_verification_and_cancellation_before_seal(self):
        token = CancellationToken()
        original = selection.ir.verify_program
        def cancel_after(*args, **kwargs):
            value = original(*args, **kwargs)
            token.cancel()
            return value
        with patch.object(selection.ir, 'verify_program', side_effect=cancel_after):
            result = self.run_request(cancellation=token)
        self.assertEqual(result['reasonCodes'], ('cancelled',))
        self.assertEqual(result['evidenceRefs'], ())
        self.assertTrue(any(row['name'] == 'verification' and row['outcome'] == 'cancelled'
                            for row in result['usage']['stages']))

    def test_cleanup_failure_is_visible_refusal_and_token_is_released(self):
        token = CancellationToken()
        context = selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned, cancellation=token)
        context.decide()
        scratch = context.git_budget.temp_root
        try:
            with patch.object(selection.shutil, 'rmtree', side_effect=OSError('sensitive path')):
                context.close()
            result = context.publish()
            self.assertEqual(result['reasonCodes'], ('internal-failure',))
            self.assertEqual(result['usage']['cleanup'], 'failed')
            self.assertEqual(result['usage']['termination'], 'stopped')
            self.assertTrue(scratch.is_dir())
            token.claim()
            token.release()
        finally:
            shutil.rmtree(scratch)

    def test_no_use_after_close_serialization_or_mutable_request(self):
        context = selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned)
        context.decide()
        with self.assertRaises(TypeError):
            pickle.dumps(context)
        with self.assertRaises(TypeError):
            context.request['budgets']['maxGitCommands'] = 0
        context.close()
        with self.assertRaisesRegex(ValueError, '^invalid-envelope$'):
            context.decide()
        with self.assertRaisesRegex(ValueError, '^invalid-envelope$'):
            context.reacquire()
        with self.assertRaisesRegex(ValueError, '^invalid-envelope$'):
            context.checkpoint('verification', 0)
        context.publish()
        context.close()
        self.assertEqual(self.fixture.inventory(), self.original_inventory)

    def test_published_snapshot_is_immutable_even_after_later_cancellation(self):
        token = CancellationToken()
        context = selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned, cancellation=token)
        context.decide()
        final = context.publish()
        token.cancel()
        self.assertIs(context.publish(), final)
        self.assertEqual(final['status'], 'answered')
        with self.assertRaises(TypeError):
            final['usage']['cleanup'] = 'failed'

    def test_row_saturation_latches_live_refusal_and_reserves_actual_cleanup(self):
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned) as context:
            producer = context.decide()
            original_evidence = context.evidence
            self.assertEqual(producer['status'], 'answered')
            self.assertTrue(original_evidence)
            # Reach the boundary through valid public stage scopes, not private
            # counter fabrication. Keep row64 available for actual cleanup.
            for _ in range(63 - len(producer['usage']['stages'])):
                with context.phase('selection'):
                    pass
            with self.assertRaisesRegex(ValueError, '^work-budget-exceeded$'):
                context.checkpoint('verification', 0)
            self.assertEqual(context.decision['status'], 'refused')
            self.assertEqual(context.decision['reasonCodes'], ('work-budget-exceeded',))
            self.assertIsNone(context.decision['selectedOptionId'])
            self.assertEqual(context.decision['evidenceRefs'], ())
            self.assertEqual(context.evidence, {})
            self.assertEqual(context.decide()['status'], 'refused')
            with self.assertRaisesRegex(ValueError, '^work-budget-exceeded$'):
                with context.phase('interpretation'):
                    self.fail('semantic work must remain blocked after refusal')
            self.assertEqual(producer['status'], 'answered')
            self.assertEqual(producer['usage']['cleanup'], 'unknown')
            self.assertTrue(original_evidence['verifierResult']['eligibleOptionIds'])
        final = context.decision
        self.assertEqual(final['reasonCodes'], ('work-budget-exceeded',))
        self.assertEqual(final['status'], 'refused')
        self.assertEqual(len(final['usage']['stages']), 64)
        self.assertEqual(final['usage']['stages'][-1]['name'], 'cleanup')
        self.assertEqual(final['usage']['stages'][-1]['outcome'], 'completed')
        self.assertEqual(final['usage']['cleanup'], 'removed')
        self.assertIsNone(final['usage']['prepareNs'])
        self.assertIs(context.publish(), final)
        self.assertEqual(producer['status'], 'answered')

    def test_inclusive_raw_byte_boundary_and_canonical_request_digest(self):
        request = self.request()
        raw = canonical(request)
        padded = raw + b' ' * (1048576 - len(raw))
        result = selection.evaluate(padded, self.fixture.owned)
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['requestDigest'], digest(request))
        self.assert_early_refusal(padded + b' ', 'input-budget-exceeded')

    def test_parsing_time_is_charged_before_scratch_allocation(self):
        now = [selection.monotonic_ns()]
        request = self.request()
        original = selection._admit
        def delayed(raw):
            value = original(raw)
            now[0] += request['budgets']['prepareBudgetMs'] * 1000000
            return value
        with patch.object(selection, '_admit', side_effect=delayed), patch.object(selection.tempfile, 'mkdtemp') as scratch:
            with selection.VerifiedRequestContext(canonical(request), self.fixture.owned, clock=lambda: now[0]) as context:
                self.assertEqual(context.decide()['reasonCodes'], ('deadline-exceeded',))
            scratch.assert_not_called()

    def test_phase_expiry_is_latched_even_when_trusted_caller_catches_it(self):
        now = [selection.monotonic_ns()]
        request = self.request()
        request['budgets']['stageBudgetMs']['nativeCheck'] = 1
        with selection.VerifiedRequestContext(canonical(request), self.fixture.owned, clock=lambda: now[0]) as context:
            self.assertEqual(context.decide()['status'], 'answered')
            with self.assertRaisesRegex(ValueError, '^deadline-exceeded$'):
                with context.phase('nativeCheck'):
                    now[0] += 1000000  # equality expires the child, well before outer end
            self.assertLess(now[0], context._outer_end)
        self.assertEqual(context.decision['reasonCodes'], ('deadline-exceeded',))
        self.assertEqual(context.decision['evidenceRefs'], ())
        self.assertTrue(any(row['name'] == 'nativeCheck' and row['outcome'] == 'expired'
                            for row in context.decision['usage']['stages']))

    def test_actual_verification_stage_cap_and_failed_checkpoint_are_latched(self):
        now = [selection.monotonic_ns()]
        request = self.request()
        request['budgets']['stageBudgetMs']['verification'] = 1
        original = selection.ir.verify_program
        def delayed(*args, **kwargs):
            value = original(*args, **kwargs)
            now[0] += 1000000
            return value
        with patch.object(selection.ir, 'verify_program', side_effect=delayed):
            with selection.VerifiedRequestContext(canonical(request), self.fixture.owned, clock=lambda: now[0]) as context:
                self.assertEqual(context.decide()['reasonCodes'], ('deadline-exceeded',))
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned) as context:
            context.decide()
            with self.assertRaisesRegex(ValueError, '^work-budget-exceeded$'):
                context.checkpoint('verification', 129)
        self.assertEqual(context.decision['reasonCodes'], ('work-budget-exceeded',))

    def test_rehashed_changed_observation_is_not_accepted_as_freshness(self):
        with selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned) as context:
            context.decide()
            snapshot = context.evidence['snapshot']
            altered = {'program': thaw(snapshot['program']),
                'binding': {'snapshot': snapshot['snapshot'], 'snapshotDigest': snapshot['snapshotDigest'],
                            'executionAuthorization': False},
                'observedEffects': snapshot['observedEffects'], 'declaredEffects': snapshot['declaredEffects'],
                'coverage': snapshot['coverage']}
            altered['program']['goal']['first.txt'] = '1' * 40
            with patch.object(acquisition, 'acquire', return_value=freeze(altered)):
                with self.assertRaisesRegex(ValueError, '^source-drift$'):
                    context.reacquire()
        self.assertEqual(context.decision['reasonCodes'], ('source-drift',))
        self.assertEqual(context.evidence, {})

    def test_cleanup_overrun_remains_visible_even_when_directory_was_removed(self):
        now = [selection.monotonic_ns()]
        context = selection.VerifiedRequestContext(canonical(self.request()), self.fixture.owned, clock=lambda: now[0])
        context.decide()
        original = selection.shutil.rmtree
        def slow(path):
            original(path)
            now[0] = context._outer_end
        with patch.object(selection.shutil, 'rmtree', side_effect=slow):
            context.close()
        result = context.publish()
        self.assertEqual(result['reasonCodes'], ('deadline-exceeded',))
        self.assertEqual(result['usage']['cleanup'], 'removed')
        self.assertEqual(result['usage']['stages'][-1]['outcome'], 'expired')
        self.assertGreater(result['usage']['cleanupNs'], 0)


if __name__ == '__main__':
    unittest.main()
