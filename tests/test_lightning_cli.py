# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-070 REQ-005, REQ-007, REQ-008: wizard, setup opt-in and boundaries."""
import ast
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_braid.cli import main
from agent_braid import lightning_config
from agent_braid.plugin_registry import configuration_digest, load, plan_setup, apply

ROOT = Path(__file__).resolve().parents[1]
MODULES = ('lightning_schema', 'lightning_config', 'lightning_store', 'lightning_cli')


def run(*args, inputs=None):
    out, err = StringIO(), StringIO()
    with redirect_stdout(out), patch('sys.stderr', err), \
            patch('builtins.input', side_effect=inputs or AssertionError('unexpected prompt')):
        code = main(list(args))
    return code, out.getvalue(), err.getvalue()


class WizardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def test_non_interactive_preview_then_apply_with_exact_digest(self):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--hosts', 'opencode',
                 '--algorithm', 'apo', '--max-rollouts', '60']
        code, out, _ = run(*flags)
        self.assertEqual(code, 0)
        preview = json.loads(out)
        self.assertFalse(lightning_config.config_path(self.home).exists())
        self.assertEqual(preview['config']['rollout']['hosts'], ['opencode'])
        self.assertFalse(preview['executionAuthorization'])
        self.assertTrue(any('EUR 0' in e for e in preview['effects']))
        self.assertEqual(run(*flags, '--apply', '--preview-digest', '0' * 64)[0], 2)
        code, out, _ = run(*flags, '--apply', '--preview-digest', preview['previewDigest'])
        self.assertEqual((code, json.loads(out)['configDigest']), (0, preview['configDigest']))
        code, out, _ = run('lightning', 'validate', '--home', str(self.home))
        self.assertEqual((code, json.loads(out)['status']), (0, 'valid'))
        # A second apply of the old preview is stale: the profile changed after it.
        self.assertEqual(run(*flags, '--apply', '--preview-digest', preview['previewDigest'])[0], 2)

    def test_interactive_wizard_keeps_defaults_and_reprompts_bad_answers(self):
        answers = ['', 'codex', 'claude-code', 'gepa', '9', '2', '', '', 'no']
        code, out, err = run('lightning', 'init', '--home', str(self.home), inputs=answers)
        self.assertEqual(code, 0, err)
        preview = json.loads(out)
        self.assertEqual(preview['config']['rollout']['hosts'], ['claude-code'])
        self.assertEqual(preview['config']['rollout']['repetitions'], 2)
        self.assertIn('try again', err)
        apply_with = preview['applyWith']
        self.assertIn('--non-interactive', apply_with)
        code, out, _ = run('lightning', 'init', '--home', str(self.home), *apply_with)
        self.assertEqual(code, 0)

    def test_apply_requires_non_interactive_and_unknown_flags_refuse(self):
        self.assertEqual(run('lightning', 'init', '--home', str(self.home), '--apply', '--preview-digest', 'x')[0], 2)
        self.assertEqual(run('lightning', 'init', '--home', str(self.home), '--non-interactive', '--repetitions', '9')[0], 2)
        self.assertEqual(run('lightning', 'validate', '--home', str(self.home))[0], 2)

    def test_status_reports_consent_and_runs(self):
        code, out, _ = run('lightning', 'status', '--home', str(self.home))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['setupConsent'], 'off')
        self.assertFalse(json.loads(out)['executionAuthorization'])


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def tearDown(self):
        self.tmp.cleanup()

    def test_lightning_consent_is_optional_and_digest_compatible(self):
        base = {'schema': 'agent-braid-plugin-registry/v0.2', 'telemetry': 'off', 'workspaces': []}
        self.assertEqual(configuration_digest(dict(base, lightning='off')), configuration_digest(base))
        preview = plan_setup(self.home, [], lightning='lab')
        self.assertTrue(any('Braid Lightning laboratory consent: lab' in e for e in preview['effects']))
        self.assertTrue(any('Earlier plugin versions refuse' in e and 'Lightning' in e for e in preview['effects']))
        apply(self.home, preview, preview['previewDigest'])
        self.assertEqual(load(self.home)['lightning'], 'lab')
        self.assertNotEqual(configuration_digest(load(self.home)), configuration_digest(base))
        preview = plan_setup(self.home, [], lightning='off')
        apply(self.home, preview, preview['previewDigest'])
        self.assertNotIn(b'lightning', (self.home / 'registry.json').read_bytes())
        with self.assertRaises(ValueError):
            plan_setup(self.home, [], lightning='auto')

    def test_setup_cli_flag(self):
        code, out, _ = run('plugin', 'setup', '--home', str(self.home), '--lightning', 'lab')
        self.assertEqual(code, 0)
        preview = json.loads(out)
        code, _, _ = run('plugin', 'setup', '--home', str(self.home), '--lightning', 'lab',
                         '--apply', '--preview-digest', preview['previewDigest'])
        self.assertEqual((code, load(self.home)['lightning']), (0, 'lab'))
        code, out, _ = run('lightning', 'status', '--home', str(self.home))
        self.assertEqual(json.loads(out)['setupConsent'], 'lab')

    def test_setup_skill_describes_the_step_without_choosing(self):
        text = (ROOT / 'integrations/agent-braid/plugin/setup/SKILL.md').read_text()
        self.assertIn('--lightning lab', text)
        self.assertIn('Never choose it for the user', text)


class BoundaryTests(unittest.TestCase):
    def test_modules_import_only_stdlib_and_open_no_sockets_or_processes(self):
        allowed_local = {'lightning_config', 'lightning_schema', 'lightning_store', 'plugin_registry'}
        for name in MODULES:
            tree = ast.parse((ROOT / 'agent_braid' / f'{name}.py').read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    self.assertTrue(set(a.name for a in node.names) <= allowed_local | {'lightning_config', 'lightning_store'}
                                    or node.module in allowed_local, (name, node.module))
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    roots = [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) else [node.module.split('.')[0]]
                    for root in roots:
                        self.assertIn(root, sys.stdlib_module_names, (name, root))
                        self.assertNotIn(root, {'socket', 'subprocess', 'http', 'urllib', 'asyncio'}, (name, root))

    def test_no_mcp_tool_mentions_lightning(self):
        for name in ('tooling_mcp.py', 'plugin_mcp.py'):
            self.assertNotIn('lightning', (ROOT / 'agent_braid' / name).read_text())

    def test_module_carries_upstream_notice(self):
        for name in ('lightning_schema', 'lightning_config', 'lightning_store'):
            text = (ROOT / 'agent_braid' / f'{name}.py').read_text()
            self.assertTrue(text.startswith('# SPDX-License-Identifier: AGPL-3.0-only'))
            self.assertIn('microsoft/agent-lightning', text)
            self.assertIn('MIT License', text)


if __name__ == '__main__':
    unittest.main()
