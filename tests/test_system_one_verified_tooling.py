# SPDX-License-Identifier: AGPL-3.0-only
"""Actual ToolingService evidence over the live finite decision context."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import test_system_one_verified_selection as fixtures
from agent_braid import git_runtime, tooling_mcp
from agent_braid import system_one_verified_tooling as transport
from agent_braid.system_one import canonical, digest, thaw, CancellationToken


class VerifiedToolingTests(unittest.TestCase):
    observations = []

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

    def context(self, language='en', representation='controlled', request=None, **kw):
        return transport.ToolingRequestContext(canonical(request or self.builder.request(language, representation)),
                                               self.fixture.owned, **kw)

    def test_four_views_real_service_complete_evidence_and_same_budget(self):
        before = self.fixture.inventory()
        for lang in ('en', 'es'):
            for rep in ('controlled', 'symbolic'):
                with self.subTest(lang=lang, rep=rep), self.context(lang, rep) as context:
                    proposal = context.propose()
                    original = proposal['decision']
                    budget = context.context.git_budget
                    calls = []
                    prepare = git_runtime.prepare_run
                    def observed(*args, **kw):
                        calls.append(kw['budget'])
                        return prepare(*args, **kw)
                    with patch.object(git_runtime, 'prepare_run', observed):
                        result = context.consume(canonical(proposal))
                    self.assertEqual(result['status'], 'answered', thaw(result))
                    self.assertEqual(proposal['consumerId'], 'mcp-service')
                    self.assertEqual(result['consumerId'], 'mcp-service')
                    self.assertEqual(calls, [budget])
                    self.assertEqual(result['preparedDigest'], digest(context.prepared))
                    self.assertEqual(context.prepared['request'], proposal['runtimeRequest'])
                    self.assertEqual(result['decisionDigest'], digest(original))
                    self.assertTrue(context.transport_receipt['completeBodyVerified'])
                    self.assertGreater(context.transport_receipt['chunks'], 0)
                    self.assertEqual(result['counters']['consumerCalls'], 1)
                    self.assertEqual(result['counters']['nativeCalls'], 1)
                    self.assertEqual(result['usage']['cleanup'], 'removed')
                    self.assertFalse(context.context.git_budget.temp_root.exists())
                    self.assertFalse(Path(context.prepared['runDirectory']).exists())
                    self.assertFalse(result['executionAuthorization'])
                    for key in ['executeCalls', 'recoverCalls', 'grantWrites', 'persistentRunAllocations']:
                        self.assertEqual(result['counters'][key], 0)
                    type(self).observations.append({'consumer': 'mcp-service', 'case': 'positive',
                        'language': lang, 'representation': rep, 'expected': 'answered',
                        'result': thaw(result), 'transport': deepcopy(context.transport_receipt)})
        self.assertEqual(self.fixture.inventory(), before)

    def test_defer_and_wrong_recipient_both_languages_before_service(self):
        from agent_braid import system_one_verified_ir as ir
        for lang in ('en', 'es'):
            request = self.builder.request(lang)
            request['source']['task']['options'] = {'k0': [], 'k1': ['a', 'a'], 'k2': ['b'], 'wait': None}
            program = deepcopy(self.builder.program)
            program['plans'] = deepcopy(request['source']['task']['options'])
            request['interpretation'] = thaw(ir.render(program, lang, 'controlled', checkpoint=lambda *_: None))
            with self.context(request=request) as context, patch.object(transport, 'bound_service', side_effect=AssertionError('dispatch')):
                proposal = context.propose()
                result = context.consume(canonical(proposal))
                self.assertEqual(result['status'], 'semantic-defer')
                self.assertEqual([result['counters'][k] for k in ['treeBuildCalls', 'nativeCalls', 'consumerCalls']], [0, 0, 0])
                type(self).observations.append({'consumer': 'mcp-service', 'case': 'defer', 'language': lang,
                    'representation': 'controlled', 'expected': 'semantic-defer', 'result': thaw(result)})
            with self.context(lang) as context:
                proposal = thaw(context.propose())
                proposal['consumerId'] = 'mcp-stdio'
                proposal['proposalDigest'] = digest({k: v for k, v in proposal.items() if k != 'proposalDigest'})
                result = context.consume(canonical(proposal))
                self.assertEqual(result['status'], 'refused')
                self.assertEqual(result['reasonCodes'], ('consumer-mismatch',))
                self.assertEqual(result['counters']['nativeCalls'], 0)
                self.assertIsNone(context.prepared)
                type(self).observations.append({'consumer': 'mcp-service', 'case': 'wrong-recipient', 'language': lang,
                    'representation': 'controlled', 'expected': 'refused', 'result': thaw(result)})

    def test_invalid_k0_and_registry_drift_for_both_consumers_EN_ES(self):
        from agent_braid import system_one_verified_ir as ir
        from agent_braid import system_one_verified_registry as registry
        from agent_braid.system_one_verified_stdio import StdioRequestContext
        for cls in (transport.ToolingRequestContext, StdioRequestContext):
            for lang in ('en', 'es'):
                request = self.builder.request(lang)
                request['source']['task']['options']['k0'] = ['a', 'a']
                program = deepcopy(self.builder.program)
                program['plans']['k0'] = ['a', 'a']
                request['interpretation'] = thaw(ir.render(program, lang, 'controlled', checkpoint=lambda *_: None))
                with cls(canonical(request), self.fixture.owned) as context:
                    proposal = context.propose()
                    self.assertEqual(proposal['decision']['selectedOptionId'], 'k1')
                    result = context.consume(canonical(proposal))
                    self.assertEqual(result['status'], 'answered', thaw(result))
                    self.assertEqual(context.prepared['request']['order'], ('b', 'a'))
                    type(self).observations.append({'consumer': cls.consumer_id, 'case': 'invalid-k0',
                        'language': lang, 'representation': 'controlled', 'expected': 'answered',
                        'result': thaw(result), 'transport': deepcopy(context.transport_receipt)})
                with cls(canonical(self.builder.request(lang)), self.fixture.owned) as context:
                    raw = canonical(context.propose())
                    with patch.object(registry, 'resolve', side_effect=ValueError('verifier-mismatch')):
                        result = context.consume(raw)
                    self.assertEqual(result['reasonCodes'], ('verifier-mismatch',))
                    self.assertEqual(result['counters']['nativeCalls'], 0)
                    self.assertEqual(result['counters']['consumerCalls'], 0)
                    type(self).observations.append({'consumer': cls.consumer_id, 'case': 'registry-drift',
                        'language': lang, 'representation': 'controlled', 'expected': 'refused', 'result': thaw(result)})

    def test_artifact_chunk_guards_and_inline_reference_agreement(self):
        with tempfile.TemporaryDirectory() as root:
            service = tooling_mcp.ToolingService(tooling_mcp.ToolingConfig(
                Path(self.builder.source['task']['request']['repository']), Path(root)))
            envelope = service._envelope('prepare', 'ok', {'padding': 'x' * 300000})
            value, evidence = transport.artifact_value(envelope, service.read_resource)
            self.assertEqual(value, {'padding': 'x' * 300000})
            self.assertEqual(evidence['chunks'], 3)
            mutations = [('offset', False), ('offset', True), ('offset', 1), ('length', 0), ('totalBytes', 1),
                         ('chunkSha256', '0' * 64), ('artifactSha256', '0' * 64),
                         ('artifactId', 'other'), ('encoding', 'utf8'), ('data', '%%%')]
            for key, bad in mutations:
                with self.subTest(key=key, bad=bad):
                    def read(uri):
                        mime, text = service.read_resource(uri)
                        obj = json.loads(text)
                        if obj.get('offset') == 0:
                            obj[key] = bad
                        return mime, canonical(obj).decode()
                    with self.assertRaises(ValueError):
                        transport.artifact_value(envelope, read)
            altered = deepcopy(envelope)
            altered['result']['sha256'] = '0' * 64
            with self.assertRaises(ValueError):
                transport.artifact_value(altered, service.read_resource)
            for key, artifact in list(service.artifacts.items()):
                service.artifacts[key] = replace(artifact, data=b'corrupted')
            with self.assertRaises(ValueError):
                transport.artifact_value(envelope, service.read_resource)

    def test_raw_dup_extra_and_provenance_corruption_never_answer(self):
        for raw in (b'{"a":1,"a":2}', b'{"extra":true}', b'{"x":NaN}', b'[]'):
            with self.context() as context, patch.object(git_runtime, 'prepare_run', side_effect=AssertionError('dispatch')):
                context.propose()
                result = context.consume(raw)
                self.assertEqual(result['status'], 'refused')
                self.assertEqual(result['counters']['nativeCalls'], 0)
        actual = tooling_mcp.ToolingService._envelope
        def corrupt(service, *args, **kw):
            value = actual(service, *args, **kw)
            value['provenance']['inputDigest'] = '0' * 64
            return value
        with self.context() as context, patch.object(tooling_mcp.ToolingService, '_envelope', corrupt):
            result = context.consume(canonical(context.propose()))
            self.assertEqual(result['status'], 'refused')
            self.assertIn('evidence-incomplete', result['reasonCodes'])
            self.assertIsNone(context.prepared)

    def test_cancel_during_resource_delivery_suppresses_prepared_success(self):
        token = CancellationToken()
        actual = tooling_mcp.ToolingService.read_resource
        def cancel(service, *args, **kw):
            value = actual(service, *args, **kw)
            token.cancel()
            return value
        with self.context(cancellation=token) as context, patch.object(tooling_mcp.ToolingService, 'read_resource', cancel):
            result = context.consume(canonical(context.propose()))
            self.assertEqual(result['status'], 'refused')
            self.assertIn('cancelled', result['reasonCodes'])
            self.assertIsNone(context.prepared)
            self.assertEqual(result['usage']['cleanup'], 'removed')

    def test_default_service_catalog_and_resource_limits_are_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            service = tooling_mcp.ToolingService(tooling_mcp.ToolingConfig(
                Path(self.builder.source['task']['request']['repository']), Path(root)))
            self.assertEqual(service.tools, ('analyze-work', 'analyze', 'prepare'))
            self.assertEqual(type(service.runtime).__name__, 'RuntimeTools')
            self.assertEqual(tooling_mcp.MAX_FRAME_BYTES, 1048576)
            self.assertEqual(tooling_mcp.MAX_ARTIFACT_BYTES, 8388608)
            self.assertFalse(service.plans)

    def test_transport_bytes_share_original_aggregate_output_ceiling(self):
        with self.context() as context:
            context.propose()
            budget = context.context.git_budget
            start, spent = budget.started_at, budget.output_bytes
            with context.context.phase('transportEvidence'):
                transport.charge(context.context, b'x')
                self.assertEqual(budget.output_bytes, spent + 1)
                self.assertEqual(budget.started_at, start)
                self.assertTrue(transport.GitCommandBudget.record_output(
                    budget, budget.max_output_bytes - budget.output_bytes))
                with self.assertRaisesRegex(ValueError, 'input-budget-exceeded'):
                    transport.charge(context.context, b'x')
                self.assertEqual(budget.output_bytes, budget.max_output_bytes)


if __name__ == '__main__':
    unittest.main()
