# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T011 (REQ-011 / SC-011): the export opens no socket, starts no process, loads no model, adds no
dependency and is not reachable from any MCP tool.

Static half: imports of `lightning_export` (standard library and listed local modules only), the import closure of
`lightning_export` and `lightning_cli` in a fresh interpreter, no promotion/execution/recovery name, no MCP module or
tool naming the export, no runtime dependency. Dynamic half: `export_dataset` and `lightning export` (export, dry
run, help, refusals) run with every socket, process and exec entry point replaced by a failing stub. Every patch is
registered with addCleanup, and a test checks that the process-global state is the same after a guarded test.
"""
import ast
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from agent_braid import lightning_export as export
from agent_braid.cli import main
from tests.spec075_fixtures import T0, consent, new_run, rollout

ROOT = Path(__file__).resolve().parents[1]
BLOCKED = {socket: ('socket', 'create_connection', 'socketpair', 'getaddrinfo', 'fromfd'),
           subprocess: ('Popen', 'run', 'call', 'check_call', 'check_output'),
           os: ('system', 'popen', 'fork', 'forkpty', 'posix_spawn', 'posix_spawnp', 'execv', 'execve', 'execvp',
                'execvpe', 'spawnv', 'spawnve')}
LOCAL = {'lightning_adapter', 'lightning_config', 'lightning_redact', 'lightning_store', 'plugin_registry',
         'trace_adapter'}  # the modules lightning_export may import
NETWORK_ROOTS = {'socket', 'subprocess', 'http', 'urllib', 'asyncio', 'ssl', 'select', 'selectors', 'multiprocessing',
                 'concurrent', 'ctypes'}
CLOSURE_FORBIDDEN = ('socket', 'asyncio', 'ssl', 'http', 'http.client', 'urllib.request', 'multiprocessing')
FORBIDDEN_MODULES = ('agent_braid.harness_promotion', 'agent_braid.harness_auto_promotion',
                     'agent_braid.harness_lifecycle', 'agent_braid.runtime_policy', 'agent_braid.mcp_runtime',
                     'agent_braid.tooling_mcp', 'agent_braid.plugin_mcp', 'agent_braid.forecast_mcp',
                     'agent_braid.mcp_advice', 'agent_braid.git_exec', 'agent_braid.git_runtime',
                     'agent_braid.lightning_runner', 'agent_braid.lightning_hosts', 'agent_braid.system_one_shadow')
FORBIDDEN_NAMES = {'decide', 'begin', 'execute', 'recover', 'harness_promotion', 'import_module', '__import__',
                   'exec', 'eval'}


def blocked(name):
    def refuse(*args, **kwargs):
        raise AssertionError(f'boundary: {name} called')
    return refuse


def snapshot():
    """The process-global state a guarded test touches."""
    return (dict(os.environ), {(m.__name__, n): getattr(m, n, None) for m, names in BLOCKED.items() for n in names},
            os.getcwd())


class StaticTests(unittest.TestCase):
    def test_export_imports_only_the_standard_library_and_listed_modules(self):
        tree = ast.parse((ROOT / 'agent_braid/lightning_export.py').read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level:
                names = {node.module} if node.module else {a.name for a in node.names}
                self.assertLessEqual(names, LOCAL, node.module)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                roots = [a.name.split('.')[0] for a in node.names] if isinstance(node, ast.Import) \
                    else [node.module.split('.')[0]]
                for root in roots:
                    self.assertIn(root, sys.stdlib_module_names, root)
                    self.assertNotIn(root, NETWORK_ROOTS, root)

    def test_no_promotion_execution_or_dynamic_code_name(self):
        for name in ('lightning_export.py', 'lightning_cli.py'):
            for node in ast.walk(ast.parse((ROOT / 'agent_braid' / name).read_text())):
                found = (node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name)
                         else node.name.split('.')[-1] if isinstance(node, ast.alias)
                         else node.name if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                         else None)
                if found is not None:
                    self.assertNotIn(found, FORBIDDEN_NAMES, (name, found))
                    self.assertNotIn('grant', found.lower(), (name, found))

    def test_import_closure_loads_no_network_promotion_or_mcp_module(self):
        probe = ('import importlib, json, sys\n'
                 'importlib.import_module("agent_braid.lightning_export")\n'
                 'importlib.import_module("agent_braid.lightning_cli")\n'
                 f'bad = {CLOSURE_FORBIDDEN + FORBIDDEN_MODULES!r}\n'
                 'print(json.dumps(sorted(m for m in sys.modules if m in bad or m.startswith("mcp")\n'
                 '                        or m.startswith("torch") or m.startswith("transformers"))))')
        out = subprocess.run([sys.executable, '-c', probe], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout), [])

    def test_no_mcp_module_tool_or_manifest_exposes_export(self):
        for path in (ROOT / 'agent_braid').glob('*mcp*.py'):
            text = path.read_text().lower()
            self.assertNotIn('lightning', text, path.name)
        for path in (ROOT / 'integrations').rglob('*.json'):
            self.assertNotIn('lightning export', path.read_text(errors='replace').lower(), path)
        from agent_braid import mcp_runtime
        self.assertFalse(any('export' in tool or 'lightning' in tool for tool in mcp_runtime.TOOLS))

    def test_no_runtime_dependency(self):
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
        self.assertEqual(project.get('dependencies', []), [])


class GuardedTests(unittest.TestCase):
    """Every socket, process and exec entry point fails; each patch is undone by addCleanup."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name).resolve()
        environment = patch.dict(os.environ, {'HOME': str(self.base / 'user')})
        environment.start()
        self.addCleanup(environment.stop)
        self.home = self.base / 'home'
        consent(self.home)  # before the guard: init itself is covered by the SPEC-074 boundary tests
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'redacted',
                 '--trace-sources', 'rollout', '--export']
        out = self.cli(*flags)[1]
        self.assertEqual(self.cli(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])[0], 0)
        run = new_run(self.home)
        rollout(run, 'ro-0', 'raw-0', [('ok ask', 'ok')], task='task-a', d4=True)
        rollout(run, 'ro-1', 'raw-1', [('bad ask', 'no')], task='task-a', d4=False)
        for module, names in BLOCKED.items():
            for name in names:
                if hasattr(module, name):
                    guard = patch.object(module, name, blocked(f'{module.__name__}.{name}'))
                    guard.start()
                    self.addCleanup(guard.stop)

    def cli(self, *args):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), patch('sys.stderr', err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_export_dataset_runs_offline(self):
        for kind, extra in (('rollout', {}), ('supervised', {'outcome_field': True})):
            for level in export.LEVELS:
                with self.subTest(kind=kind, level=level):
                    manifest = export.export_dataset(self.home, ['run-1'], kind=kind, level=level,
                                                     out=self.base / f'{kind}-{level}', now=T0 + 60, **extra)
                    self.assertEqual(manifest['canaryScan'], 'clean')

    def test_every_cli_export_path_runs_offline(self):
        base = ['lightning', 'export', '--home', str(self.home)]
        cases = [
            (0, ['--run', 'run-1', '--kind', 'rollout', '--level', 'trajectory', '--out', str(self.base / 'a')]),
            (0, ['--all', '--kind', 'supervised', '--level', 'transition', '--out', str(self.base / 'b'),
                 '--outcome-field']),
            (0, ['--all', '--kind', 'rollout', '--level', 'transition', '--out', str(self.base / 'c'), '--dry-run']),
            (0, ['--help']),
            (2, ['--run', 'missing', '--kind', 'rollout', '--level', 'trajectory', '--out', str(self.base / 'd')]),
            (2, ['--kind', 'other']),
            (2, ['--all', '--kind', 'rollout', '--level', 'trajectory', '--out', str(self.base / 'a')]),
        ]
        for expected, args in cases:
            with self.subTest(args=args[:2]):
                code, out, err = self.cli(*base, *args)
                self.assertEqual(code, expected, err)
                self.assertNotIn('boundary:', out + err)
                if expected == 0 and out.lstrip().startswith('{'):
                    self.assertIs(json.loads(out)['executionAuthorization'], False)

    def test_the_guard_fails_a_socket_or_process_inside_the_export(self):
        for name, call in (('socket', lambda *a, **k: socket.create_connection(('127.0.0.1', 9))),
                           ('process', lambda *a, **k: subprocess.run(['true'])),
                           ('system', lambda *a, **k: os.system('true'))):
            with self.subTest(name=name), patch.object(export, 'scan', call), \
                    self.assertRaisesRegex(AssertionError, 'boundary:'):
                export.export_dataset(self.home, ['run-1'], kind='rollout', level='trajectory',
                                      out=self.base / f'x-{name}', now=T0 + 60)
            self.assertFalse((self.base / f'x-{name}').exists())


class IsolationTests(unittest.TestCase):
    def test_guarded_tests_leave_no_process_global_state(self):
        before = snapshot()
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(GuardedTests)
        result = unittest.TextTestRunner(stream=StringIO()).run(suite)
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)
        self.assertEqual(snapshot(), before)


if __name__ == '__main__':
    unittest.main()
