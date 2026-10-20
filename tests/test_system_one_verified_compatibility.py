# SPDX-License-Identifier: AGPL-3.0-only
"""T07 software compatibility, without learned/workload acceptance claims."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import system_one as legacy
from agent_braid import system_one_verified_selection as selection
from agent_braid import system_one_verified_consumers as consumers
from agent_braid import system_one_verified_tooling as tooling
from agent_braid import system_one_verified_stdio as stdio
from tests.test_system_one_core import fixture


class VerifiedCompatibilityTests(unittest.TestCase):
    def test_fresh_integrated_imports_deny_network_processes_and_optional_runtimes(self):
        # A fresh interpreter guards attempts, including modules that would later
        # remove themselves from sys.modules. Guards intentionally remain active
        # through discovery and after-import legacy decisions, not just import.
        code = r'''
import sys, json, importlib.abc
from agent_braid import system_one as s
from agent_braid.system_one_backends import capabilities
from agent_braid.system_one_router import router_registry_manifest
from tests.test_system_one_core import fixture
blocked = ('torch', 'transformers', 'huggingface_hub', 'agent_braid_system_one', 'mcp')
attempts = []
class Deny(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in blocked or (fullname.startswith('research.') and fullname not in ('research.lab', 'research.lab.model')):
            attempts.append(fullname)
            raise AssertionError('forbidden optional import: ' + fullname)
sys.meta_path.insert(0, Deny())
events = []
def audit(name, args):
    if name in ('socket.connect', 'socket.bind', 'socket.getaddrinfo', 'subprocess.Popen',
                'os.system', 'os.posix_spawn', 'os.fork'):
        events.append(name)
        raise AssertionError('import/discovery effect: ' + name)
sys.addaudithook(audit)
before = s.canonical({'capabilities': s.thaw(capabilities()), 'registry': s.thaw(router_registry_manifest())})
def answers():
    rows=[]
    for language in ('en', 'es'):
        for kind, options, chosen in (
            ('boolean', [{'id':'false','description':''},{'id':'true','description':''}], 'true'),
            ('choice', [{'id':'z','description':''},{'id':'a','description':''}], 'a'),
            ('score', [{'id':'low','description':'','value':-2},{'id':'high','description':'','value':7}], 'high')):
            v=fixture(); v['questions'][0].update(type=kind,options=options,instructions='Synthetic only' if language=='en' else 'Solo sintético')
            v['state']['ruleAnswers']['q']=chosen; v['stateDigest']=s.digest(v['state'])
            raw=s.canonical(v); out=s.evaluate(raw)
            s.validate_response(out, request=s.validate_request(raw))
            assert out['status']=='answered' and out['answers'][0]['choiceId']==chosen
            assert out['executionAuthorization'] is False
            rows.append({k:out[k] for k in ('status','answers','policyDigest','modelManifestDigest','calibrationStatus','executionAuthorization')})
    return rows
baseline=answers()
from agent_braid import system_one_verified_ir, system_one_verified_acquisition, system_one_verified_registry
from agent_braid import system_one_verified_selection
assert not any(n == 'research' or n.startswith('research.') for n in sys.modules)
from agent_braid import system_one_verified_consumers, system_one_verified_tooling, system_one_verified_stdio
assert before == s.canonical({'capabilities':s.thaw(capabilities()),'registry':s.thaw(router_registry_manifest())})
assert baseline == answers()
assert not attempts and not events
assert sorted(n for n in sys.modules if n == 'research' or n.startswith('research.')) == ['research', 'research.lab', 'research.lab.model']
assert not any(n.split('.')[0] in blocked for n in sys.modules)
print(json.dumps({'legacyCases':len(baseline),'imports':7,'forbiddenAttempts':attempts,'effectAttempts':events}))
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
                                timeout=30, check=True)
        self.assertEqual(json.loads(result.stdout), {'legacyCases': 6, 'imports': 7,
                         'forbiddenAttempts': [], 'effectAttempts': []})

    def test_all_consumer_ingresses_refuse_legacy_and_raw_authority_before_source(self):
        raws = [legacy.canonical(fixture()), legacy.canonical(legacy.evaluate(legacy.canonical(fixture()))),
                b'{"format":"s1-verified-request-v1","format":"s1-verified-request-v1"}',
                b'{"executionAuthorization":true}', b'{"confidence":1}',
                b'{"a":NaN}', b'\xef\xbb\xbf{}', b'{} trailing']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for cls in (consumers.CoreRequestContext, tooling.ToolingRequestContext, stdio.StdioRequestContext):
                for raw in raws:
                    with self.subTest(consumer=cls.consumer_id, raw=raw[:64]):
                        with patch.object(selection.acquisition, 'acquire', side_effect=AssertionError('source')), \
                             patch.object(selection.tempfile, 'mkdtemp', side_effect=AssertionError('scratch')), \
                             patch.object(stdio, '_command', side_effect=AssertionError('child')):
                            with cls(raw, root) as context:
                                with self.assertRaisesRegex(ValueError, '^invalid-envelope$'):
                                    context.propose()
                                result = context.consume(b'{}')
                                self.assertEqual(result['status'], 'refused')
                                self.assertEqual(result['reasonCodes'], ('invalid-envelope',))
                                self.assertIsNone(context.prepared)
                                self.assertTrue(all(v == 0 for v in result['counters'].values()))
                                self.assertEqual(result['usage']['cleanup'], 'not-allocated')
                                self.assertFalse(result['executionAuthorization'])
            self.assertEqual(list(root.iterdir()), [])

    def test_empty_and_repeated_options_stay_semantic_failures_EN_ES(self):
        from agent_braid import system_one_verified_ir as ir
        program = json.loads((Path(__file__).parent / 'fixtures/system_one_verified_ir.json').read_text())['program']
        program['plans']['k0'] = []
        program['plans']['k1'] = ['a', 'a', 'b']
        for language in ('en', 'es'):
            for representation in ('controlled', 'symbolic'):
                with self.subTest(language=language, representation=representation):
                    payload = ir.render(program, language, representation, checkpoint=lambda *_: None)
                    parsed = ir.interpret(payload, checkpoint=lambda *_: None)
                    result = ir.verify_program(parsed, ('wait', 'k1', 'k0', 'k2'),
                                               max_hunks=128, checkpoint=lambda *_: None)
                    self.assertEqual(result['status'], 'answered')
                    self.assertEqual(result['choice'], 'k2')
                    self.assertEqual(result['eligible'], ('k2',))
                    self.assertFalse(result['plans']['k0']['valid'])
                    self.assertEqual(result['plans']['k0']['failure']['reason'], 'final-goal')
                    self.assertFalse(result['plans']['k1']['valid'])
                    self.assertEqual(result['plans']['k1']['failure'], {'step': 1, 'reason': 'operation-precondition'})
                    self.assertFalse(result['executionAuthorization'])

    def test_default_catalog_and_legacy_identity_survive_private_contexts(self):
        from agent_braid.system_one_backends import capabilities
        from agent_braid.system_one_router import router_registry_manifest
        from agent_braid.tooling_mcp import ToolingService, ToolingConfig
        before = legacy.canonical({'capabilities': legacy.thaw(capabilities()),
                                   'registry': legacy.thaw(router_registry_manifest())})
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, results = root / 'source', root / 'results'
            source.mkdir(); results.mkdir()
            service = ToolingService(ToolingConfig(source, results))
            tools_before = service.tools
            for cls in (consumers.CoreRequestContext, tooling.ToolingRequestContext, stdio.StdioRequestContext):
                with cls(b'{}', root) as context:
                    context.consume(b'{}')
            self.assertEqual(service.tools, tools_before)
            self.assertEqual(service.tools, ('analyze-work', 'analyze', 'prepare'))
            self.assertEqual(type(service.runtime).__name__, 'RuntimeTools')
            self.assertFalse(service.plans)
        after = legacy.canonical({'capabilities': legacy.thaw(capabilities()),
                                  'registry': legacy.thaw(router_registry_manifest())})
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()
