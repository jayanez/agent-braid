# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-070 REQ-005, REQ-007, REQ-008: wizard, setup opt-in and boundaries."""
import ast
from contextlib import redirect_stdout
from io import StringIO
import json
import os
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
MODULES = ('lightning_schema', 'lightning_config', 'lightning_store', 'lightning_cli', 'lightning_resources', 'lightning_adapter', 'lightning_redact')


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
        answers = ['', 'codex', 'claude-code', 'gepa', '9', '2', '', '', '', 'no']
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

    def test_a_git_failure_in_an_arm_run_prints_a_refusal_not_a_traceback(self):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--algorithm', 'gepa']
        preview = json.loads(run(*flags)[1])
        self.assertEqual(run(*flags, '--apply', '--preview-digest', preview['previewDigest'])[0], 0)
        from agent_braid import lightning_arm
        with patch.object(lightning_arm.subprocess, 'run', side_effect=subprocess.CalledProcessError(128, 'git')):
            code, _, err = run('lightning', 'run', '--home', str(self.home), '--fake-hosts', '--seed-run', 'seed')
        self.assertEqual(code, 2)
        self.assertIn('lightning refused (source-unavailable)', err)
        self.assertNotIn('Traceback', err)


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
        allowed_local = {'lightning_config', 'lightning_schema', 'lightning_store', 'plugin_registry',
                         'lightning_runner', 'lightning_resources', 'lightning_arm', 'lightning_adapter'}  # SPEC-074: consent gate; SPEC-071/072: the CLI delegates runs lazily; BL.0 modules launch nothing
        for name in MODULES:
            tree = ast.parse((ROOT / 'agent_braid' / f'{name}.py').read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    self.assertTrue(set(a.name for a in node.names) <= allowed_local
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


BL2_ALLOWED = {'plugin_registry', 'harness_host_claude',  # SPEC-070/071 runner and host setup
               'harness_evaluation', 'system_one',  # SPEC-072 T013: record formats only, never decide()
               'spec069_scoring', 'spec069_native_runs', 'spec069_fixture_workspace', 'build_native_plugin',
               'spec072_development_arms'}  # T010 reuses the BL.2 lab-script profile, token and gate helpers
BL2_FORBIDDEN_NAMES = {'decide', 'begin', 'execute', 'recover', 'harness_promotion',
                       'import_module', '__import__'}  # no dynamic import around the static checks
BL2_FORBIDDEN_MODULES = ('agent_braid.harness_promotion', 'agent_braid.harness_auto_promotion',
                         'agent_braid.harness_lifecycle', 'agent_braid.runtime_policy', 'agent_braid.mcp_runtime',
                         'agent_braid.tooling_mcp', 'agent_braid.plugin_mcp', 'agent_braid.forecast_mcp',
                         'agent_braid.system_one_verified_mcp', 'agent_braid.mcp_advice',
                         'agent_braid.git_exec', 'agent_braid.git_runtime', 'agent_braid.git_runtime_process',
                         'agent_braid.runtime_scheduler', 'agent_braid.tooling_source_runtime', 'mcp')
SKILL = ROOT / 'integrations/agent-braid/skills/agent-braid-analyze/SKILL.md'


def bl2_files():
    return sorted([*(ROOT / 'agent_braid').glob('lightning_*.py'), *(ROOT / 'scripts').glob('spec072_*.py')])


class BL2BoundaryTests(unittest.TestCase):
    """SPEC-072 REQ-009 / SC-009 (procedure_009): BL.2 has no promotion, execution, MCP or dependency path."""

    def test_imports_stay_within_stdlib_lightning_and_the_allowlist(self):
        for path in bl2_files():
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.ImportFrom):
                    parts = node.module.split('.') if node.module else []
                    if node.level == 0 and parts[0] not in ('scripts', 'agent_braid'):
                        self.assertIn(parts[0], sys.stdlib_module_names, (path.name, node.module))
                        continue
                    if node.level == 0:
                        parts = parts[1:]  # drop the package; the first remaining part is the module
                    for name in parts[:1] or [a.name for a in node.names]:
                        self.assertTrue(name.startswith('lightning_') or name in BL2_ALLOWED, (path.name, name))
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split('.')[0], sys.stdlib_module_names, (path.name, alias.name))

    def test_no_promotion_execution_recovery_or_grant_call(self):
        for path in (ROOT / 'agent_braid').glob('lightning_*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                name = (node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name)
                        else node.name.split('.')[-1] if isinstance(node, ast.alias) else None)
                if name is not None:
                    self.assertNotIn(name, BL2_FORBIDDEN_NAMES, path.name)
                    self.assertFalse('grant' in name.lower(), (path.name, name))

    def test_import_closure_loads_no_promotion_execution_or_mcp_module(self):
        modules = [f'agent_braid.{p.stem}' if p.parent.name == 'agent_braid' else f'scripts.{p.stem}' for p in bl2_files()]
        probe = ('import importlib, json, sys\n'
                 f'for m in {modules!r}: importlib.import_module(m)\n'
                 f'print(json.dumps(sorted(m for m in sys.modules if m in {BL2_FORBIDDEN_MODULES!r} '
                 f'or m.startswith("mcp."))))')
        out = subprocess.run([sys.executable, '-c', probe], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), [])

    def test_no_mcp_tool_or_plugin_manifest_exposes_lightning(self):
        for path in (ROOT / 'agent_braid').glob('*mcp*.py'):
            self.assertNotIn('lightning', path.read_text().lower(), path.name)
        for path in (ROOT / 'integrations').rglob('*.json'):
            self.assertNotIn('lightning', path.read_text().lower(), path)

    def test_no_runtime_dependency(self):
        import tomllib
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
        self.assertEqual(project['dependencies'], [])
        self.assertFalse(any('lightning' in k for k in project.get('optional-dependencies', {})))

    def test_fake_optimization_run_leaves_the_skill_file_and_reports_the_best_by_hash(self):
        from agent_braid import lightning_arm, lightning_runner
        from agent_braid.harness_host_claude import ENV_DENY
        from agent_braid.lightning_resources import split_skill
        env = {k: v for k, v in os.environ.items() if not k.endswith('_API_KEY') and k not in ENV_DENY}
        before = (SKILL.read_bytes(), SKILL.stat().st_mtime_ns)

        def profile(name, **algo):
            return lightning_config.build(
                {'rollout': {'repetitions': 1, 'hosts': ['claude-code']}, 'algorithm': {'name': name, **algo}})

        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp).resolve() / 'home'
            lightning_runner.run(home, profile('baseline'), run_id='seed', fake_hosts=True, environ=env)
            summary = lightning_arm.run_arm(home, profile('gepa', rounds=1, minibatch=2), seed_run='seed',
                                            run_id='gepa', fake_hosts=True, environ=env)
        self.assertEqual((SKILL.read_bytes(), SKILL.stat().st_mtime_ns), before)
        self.assertRegex(summary['bestSha256'], r'\A[0-9a-f]{64}\Z')
        dumped = json.dumps(summary)
        body = split_skill(SKILL.read_text())[1]
        for line in (l for l in body.splitlines() if len(l) > 40):
            self.assertNotIn(json.dumps(line)[1:-1], dumped)


if __name__ == '__main__':
    unittest.main()
