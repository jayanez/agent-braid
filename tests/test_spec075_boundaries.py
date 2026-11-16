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
# Allow-list: every module lightning_export.py imports, top-level or lazy. Adding one needs a conscious edit here.
STDLIB = {'__future__', 'datetime', 'hashlib', 'json', 'os', 'pathlib', 're', 'shutil', 'stat', 'tempfile'}
CLOSURE_FORBIDDEN = ('socket', 'asyncio', 'ssl', 'http', 'http.client', 'urllib.request', 'multiprocessing')
FORBIDDEN_MODULES = ('agent_braid.harness_promotion', 'agent_braid.harness_auto_promotion',
                     'agent_braid.harness_lifecycle', 'agent_braid.runtime_policy', 'agent_braid.mcp_runtime',
                     'agent_braid.tooling_mcp', 'agent_braid.plugin_mcp', 'agent_braid.forecast_mcp',
                     'agent_braid.mcp_advice', 'agent_braid.git_exec', 'agent_braid.git_runtime',
                     'agent_braid.lightning_runner', 'agent_braid.lightning_hosts', 'agent_braid.system_one_shadow')
# Bare names (identifiers, imports, definitions) and attribute names that must not appear in the export or CLI
# modules, so dead code or a rare path cannot hold a process, exec or dynamic-import call the runtime guard misses.
FORBIDDEN_NAMES = {'decide', 'begin', 'execute', 'recover', 'harness_promotion', 'import_module', '__import__',
                   'exec', 'eval', 'compile', 'importlib', 'popen', 'system', 'fork', 'forkpty', 'Popen',
                   'check_output', 'check_call', 'create_connection', 'socketpair', 'getaddrinfo'}
# Process and socket entry points: forbidden as attributes (`os.popen`, `subprocess.check_output`); the export's
# own `check_output` (output-path check) is a definition and a plain call, not an attribute of a module.
ATTRIBUTE_ONLY = {'check_output', 'check_call', 'Popen', 'popen', 'system', 'fork', 'forkpty', 'create_connection',
                  'socketpair', 'getaddrinfo'}
FORBIDDEN_PREFIXES = ('exec', 'spawn', 'posix_spawn')  # execl*, execv*, spawnl*, spawnv*, posix_spawn(p)
DYNAMIC_TARGETS = {'os', 'subprocess', 'socket', 'importlib', 'builtins', 'sys', 'shutil'}  # getattr(<module>, ...)


def blocked(name):
    def refuse(*args, **kwargs):
        raise AssertionError(f'boundary: {name} called')
    return refuse


def snapshot():
    """The process-global state a guarded test touches."""
    return (dict(os.environ), {(m.__name__, n): getattr(m, n, None) for m, names in BLOCKED.items() for n in names},
            os.getcwd())


def names_in(tree):
    """(kind, name, node) for every identifier, attribute, import alias and definition in a module."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            yield 'name', node.id, node
        elif isinstance(node, ast.Attribute):
            yield 'attribute', node.attr, node
        elif isinstance(node, ast.alias):
            yield 'alias', node.name.split('.')[-1], node
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            yield 'definition', node.name, node


def forbidden(kind, name):
    if kind == 'attribute' and name == 'compile':
        return False  # re.compile; the builtin compile() is a Name
    if name in ATTRIBUTE_ONLY:
        return kind == 'attribute'
    return name in FORBIDDEN_NAMES or (name.startswith(FORBIDDEN_PREFIXES) and name not in ('executionAuthorization',))


class StaticTests(unittest.TestCase):
    # lightning_cli.py imports are covered by tests.test_lightning_cli.BoundaryTests (MODULES includes it).
    def test_export_imports_only_the_allow_listed_modules(self):
        tree = ast.parse((ROOT / 'agent_braid/lightning_export.py').read_text())
        for node in ast.walk(tree):  # top-level and lazy imports alike
            if isinstance(node, ast.ImportFrom) and node.level:
                names = {node.module} if node.module else {a.name for a in node.names}
                self.assertLessEqual(names, LOCAL, node.module)
            elif isinstance(node, ast.ImportFrom):
                self.assertIn(node.module, STDLIB, node.module)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertIn(alias.name, STDLIB, alias.name)

    def test_no_promotion_execution_process_or_dynamic_code_name(self):
        for name in ('lightning_export.py', 'lightning_cli.py'):
            for kind, found, node in names_in(ast.parse((ROOT / 'agent_braid' / name).read_text())):
                self.assertFalse(forbidden(kind, found), (name, kind, found))
                self.assertNotIn('grant', found.lower(), (name, found))
                if kind == 'name' and found == 'getattr':
                    pass  # checked on the call below
            for node in ast.walk(ast.parse((ROOT / 'agent_braid' / name).read_text())):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in (
                        'getattr', 'setattr', 'vars', 'globals', '__import__'):
                    target = node.args[0] if node.args else None
                    self.assertFalse(isinstance(target, ast.Name) and target.id in DYNAMIC_TARGETS,
                                     (name, node.func.id, getattr(target, 'id', None)))
                    for arg in node.args[1:]:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            self.assertFalse(forbidden('attribute', arg.value), (name, arg.value))

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
        self.assertEqual(no_export_tools(), [])

    def test_a_neutral_tool_name_is_caught(self):
        from agent_braid import mcp_runtime
        with patch.object(mcp_runtime, 'TOOLS', (*mcp_runtime.TOOLS, 'dataset')):
            self.assertEqual(no_export_tools(), ['dataset'])

    def test_no_runtime_dependency(self):
        project = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']
        self.assertEqual(project.get('dependencies', []), [])


def no_export_tools():
    """Tool names and descriptions of every MCP surface that mention export, dataset or lightning."""
    from agent_braid import mcp_runtime, plugin_mcp, tooling_mcp
    from tests.test_spec069_schema_delivery import FAKE_TYPES, _Router
    words = ('export', 'dataset', 'lightning')
    found = [tool for tool in mcp_runtime.TOOLS if any(w in tool.lower() for w in words)]
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        for name in ('s', 'r'):
            (base / name).mkdir()
        services = [tooling_mcp.ToolingService(tooling_mcp.ToolingConfig(base / 's', base / 'r')),
                    tooling_mcp.ToolingService(tooling_mcp.ToolingConfig(base / 's', base / 'r',
                                                                          grant_store=base / 'g', runtime_enabled=True))]
        for service in services:
            found += [tool for tool in service.tools if any(w in tool.lower() for w in words)]
        workspace = plugin_mcp.WorkspaceService('ws', tooling_mcp.ToolingConfig(base / 's', base / 'r'))
        for tool in plugin_mcp.tool_listing(_Router({'ws': workspace}), FAKE_TYPES):
            text = f'{tool.name} {tool.description}'.lower()
            found += [tool.name] if any(w in text for w in words) else []
    return found


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
        canary = new_run(self.home, 'run-canary')
        rollout(canary, 'ro-c', 'raw-c', [('read /Users/canaryuser/plan', 'ok')], task='task-c', d4=True)
        host = new_run(self.home, 'run-host')
        rollout(host, 'ro-h', 'raw-h', [('host', 'host')], task='task-h', d4=True, label='host-run', model='m')
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
            (0, ['--run', 'run-1', '--kind', 'supervised', '--level', 'transition', '--out', str(self.base / 'b'),
                 '--outcome-field']),
            (0, ['--run', 'run-1', '--kind', 'rollout', '--level', 'transition', '--out', str(self.base / 'c'),
                 '--dry-run']),
            (2, ['--all', '--kind', 'rollout', '--level', 'trajectory', '--out', str(self.base / 'h')]),  # host: terms
            (0, ['--help']),
            (2, ['--run', 'missing', '--kind', 'rollout', '--level', 'trajectory', '--out', str(self.base / 'd')]),
            (2, ['--kind', 'other']),
            (2, ['--all', '--kind', 'rollout', '--level', 'trajectory', '--out', str(self.base / 'a')]),
            (2, ['--run', 'run-canary', '--kind', 'rollout', '--level', 'trajectory', '--balance', 'none',
                 '--out', str(self.base / 'e')]),  # canary-detected
            (2, ['--run', 'run-host', '--kind', 'rollout', '--level', 'trajectory', '--out', str(self.base / 'f')]),
            (2, ['--run', 'run-host', '--kind', 'rollout', '--level', 'trajectory', '--out', str(self.base / 'f'),
                 '--terms-decision', 'terms/none.json']),  # terms-gate-missing with a named record
        ]
        for expected, args in cases:
            with self.subTest(args=args[:2]):
                code, out, err = self.cli(*base, *args)
                self.assertEqual(code, expected, err)
                self.assertNotIn('boundary:', out + err)
                if expected == 0 and out.lstrip().startswith('{'):
                    self.assertIs(json.loads(out)['executionAuthorization'], False)

    def refusal(self, runs, code, **kwargs):
        options = {'kind': 'rollout', 'level': 'trajectory', 'now': T0 + 60, **kwargs}
        with self.assertRaises(export.ExportError) as caught:
            export.export_dataset(self.home, runs, out=self.base / 'refused', **options)
        self.assertEqual(caught.exception.code, code)
        self.assertFalse((self.base / 'refused').exists())

    def test_every_export_refusal_runs_offline(self):
        self.refusal(['run-canary'], 'canary-detected', balance='none')
        self.refusal(['run-host'], 'terms-gate-missing')
        self.refusal(['run-host'], 'terms-gate-missing', terms_decision='terms/none.json')
        self.refusal(['missing'], 'store-missing')
        self.refusal(['run-1'], 'invalid-argument', kind='other')
        (self.base / 'busy').mkdir()
        (self.base / 'busy' / 'x').write_text('x')
        with self.assertRaises(export.ExportError) as caught:
            export.export_dataset(self.home, ['run-1'], kind='rollout', level='trajectory', out=self.base / 'busy')
        self.assertEqual(caught.exception.code, 'output-not-empty')

    def test_consent_and_disabled_refusals_run_offline(self):
        consent(self.home, 'none')  # writes the profile under the guard: no process or socket either
        self.refusal(['run-1'], 'no-records')
        code, _, err = self.cli('lightning', 'export', '--home', str(self.home), '--run', 'run-1', '--kind', 'rollout',
                                '--level', 'trajectory', '--out', str(self.base / 'g'))
        self.assertEqual((code, 'boundary:' in err), (2, False))
        self.assertIn('(export-disabled)', err)

    def test_every_stub_fires_inside_the_export(self):
        for module, names in BLOCKED.items():
            for name in names:
                if not hasattr(module, name):
                    continue
                with self.subTest(stub=f'{module.__name__}.{name}'), \
                        patch.object(export, 'scan', lambda *a, _m=module, _n=name, **k: getattr(_m, _n)()), \
                        self.assertRaisesRegex(AssertionError, f'boundary: {module.__name__}.{name} called'):
                    export.export_dataset(self.home, ['run-1'], kind='rollout', level='trajectory',
                                          out=self.base / 'x', now=T0 + 60)
                self.assertFalse((self.base / 'x').exists())

    def test_a_process_inside_a_refusal_path_fails(self):
        for target, runs, record in (('scan', ['run-canary'], None), ('load_terms_decision', ['run-host'], 'terms/n.json')):
            with self.subTest(target=target), \
                    patch.object(export, target, lambda *a, **k: os.popen('true')), \
                    self.assertRaisesRegex(AssertionError, 'boundary: os.popen called'):
                export.export_dataset(self.home, runs, kind='rollout', level='trajectory', out=self.base / 'y',
                                      balance='none', now=T0 + 60, terms_decision=record)


class IsolationTests(unittest.TestCase):
    # Runs GuardedTests a second time, inside a snapshot, on purpose: it is the only way to compare the global
    # state before and after the guarded tests from within the suite.
    def test_guarded_tests_leave_no_process_global_state(self):
        before = snapshot()
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(GuardedTests)
        result = unittest.TextTestRunner(stream=StringIO()).run(suite)
        self.assertTrue(result.wasSuccessful(), result.failures + result.errors)
        self.assertEqual(snapshot(), before)


if __name__ == '__main__':
    unittest.main()
