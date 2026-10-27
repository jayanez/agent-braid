# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T025 and T028 (REQ-016): governance static tests.

Every rule is a pure function over source text, a schema, an emitted object or a list of
paths. Each test runs the rule on the real deliverables and then on a seeded violating
fixture, which must fail with exactly that rule. The bounds tests of T013 and T025 are in
``tests/test_orchestration_bounds.py``.
"""

from __future__ import annotations

import ast
import functools
import json
from pathlib import Path
import re
import unittest

from agent_braid import ownership
from tests.test_ownership_receipt import BASE, TREE, declaration, observed, receipt_for

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/057-claude-orchestration-advisory"
DELIVERABLES = ("agent_braid/ownership.py", "agent_braid/ownership_cli.py", "agent_braid/path_overlap.py")
# The only package modules a deliverable may import: the analyzer, the bounded Git helpers and each other.
INTERNAL_IMPORTS = {"analysis", "git_adapter", "git_process", "ownership", "path_overlap"}
NETWORK_IMPORTS = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "telnetlib", "xmlrpc", "asyncio", "socketserver",
    "selectors", "webbrowser",
}
PROCESS_IMPORTS = {"subprocess", "multiprocessing", "pty", "pexpect"}
PROCESS_CALLS = {"system", "popen", "Popen", "fork", "spawn", "posix_spawn", "execv", "execve", "execvp", "execl"}
HOST_BINARY = re.compile(r"^claude(\.exe)?(\s|$)", re.IGNORECASE)
COMMANDS = ("expand-ownership", "check-ownership", "audit-isolation", "report-recovery")
# Modules that may name the commands: the registration, the implementation and the dispatcher.
COMMAND_FILES = {"cli.py", "ownership_cli.py", "ownership.py"}
NOT_PLUGIN_COMPONENTS = {"hooks", "mods", "agents", "monitors", "channels"}
COMPILER_OR_PLANNER = re.compile(r"compil|planner|hook_?profile", re.IGNORECASE)
HAR3_MODULES = ("harness_hooks", "harness_orchestration", "harness_lifecycle")


def _source(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


@functools.cache
def package_modules() -> dict[str, str]:
    """Source text of every module of the package, read once."""
    return {p.name: p.read_text(encoding="utf-8") for p in sorted((ROOT / "agent_braid").glob("*.py"))}


def _imports(tree: ast.AST) -> tuple[set[str], set[str]]:
    """Top-level absolute modules and first-segment package-relative modules of every import."""
    absolute: set[str] = set()
    relative: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            absolute.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level and node.module:
                relative.add(node.module.split(".")[0])
            elif node.level:
                relative.update(alias.name for alias in node.names)
            else:
                absolute.add((node.module or "").split(".")[0])
    return absolute, relative


def _strings(tree: ast.AST) -> list[str]:
    return [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)]


def source_violations(source: str) -> set[str]:
    """Governance rules a deliverable's source breaks; empty when it breaks none."""
    tree = ast.parse(source)
    absolute, relative = _imports(tree)
    out: set[str] = set()
    if relative - INTERNAL_IMPORTS:
        out.add("runtime-or-grant-import")
    if absolute & NETWORK_IMPORTS:
        out.add("socket")
    if "mcp" in absolute or relative & {"plugin_mcp", "tooling_mcp"}:
        out.add("mcp-tool")
    called = {n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", "")
              for n in ast.walk(tree) if isinstance(n, ast.Call)}
    if absolute & PROCESS_IMPORTS or called & PROCESS_CALLS:
        out.add("direct-process")
    if any(HOST_BINARY.match(text) for text in _strings(tree)):
        out.add("host-binary")
    if any(isinstance(n, (ast.FunctionDef, ast.ClassDef)) and COMPILER_OR_PLANNER.search(n.name)
           for n in ast.walk(tree)):
        out.add("compiler-or-planner")
    return out


def authorization_violations(value, where: str = "$") -> list[str]:
    """Locations of an ``executionAuthorization`` member that is not the boolean false."""
    found: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "executionAuthorization" and item is not False:
                found.append(f"{where}.{key}")
            found.extend(authorization_violations(item, f"{where}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(authorization_violations(item, f"{where}[{index}]"))
    return found


def schema_violations(schema, where: str = "$") -> list[str]:
    """Locations where a schema lets ``executionAuthorization`` be anything but the constant false."""
    found: list[str] = []
    if isinstance(schema, dict):
        for key, item in schema.items():
            if key == "executionAuthorization" and item != {"const": False}:
                found.append(f"{where}.{key}")
            found.extend(schema_violations(item, f"{where}.{key}"))
    elif isinstance(schema, list):
        for index, item in enumerate(schema):
            found.extend(schema_violations(item, f"{where}[{index}]"))
    return found


def component_violations(paths) -> list[str]:
    """Plugin paths that add a hook, mod, agent, monitor or channel, or an orchestration skill."""
    found = []
    for path in paths:
        parts = path.split("/")
        if NOT_PLUGIN_COMPONENTS & set(parts):
            found.append(path)
        elif "skills" in parts and re.search(r"orchestrat|ownership", path, re.IGNORECASE):
            found.append(path)
    return found


def command_leaks(files: dict[str, str]) -> list[str]:
    """Files that name a SPEC-057 command although they are not the registration, implementation or dispatcher."""
    return sorted(name for name, text in files.items()
                  if name not in COMMAND_FILES and any(command in text for command in COMMANDS))


def deliverable_violations(paths) -> list[str]:
    """Deliverable paths that are a hook-profile compiler, an orchestration planner or a HAR.3 module."""
    return [p for p in paths
            if COMPILER_OR_PLANNER.search(Path(p).stem) or Path(p).stem in HAR3_MODULES]


class SourceRuleTests(unittest.TestCase):
    SEEDED = {
        "runtime-or-grant-import": "from .plugin_registry import grant\n",
        "socket": "import socket\n",
        "mcp-tool": "from mcp.server import Server\n",
        "direct-process": "import subprocess\nsubprocess.run(['git'])\n",
        "host-binary": "ARGV = ['claude', '--print']\n",
        "compiler-or-planner": "def compile_hook_profile(profile):\n    return profile\n",
    }

    def test_deliverables_break_no_rule(self):
        for relative in DELIVERABLES:
            self.assertEqual(source_violations(_source(relative)), set(), relative)

    def test_each_seeded_violation_is_caught_by_exactly_its_rule(self):
        for rule, source in self.SEEDED.items():
            self.assertEqual(source_violations(source), {rule}, rule)

    def test_scheduler_runtime_and_registry_imports_are_runtime_imports(self):
        for module in ("runtime_scheduler", "plugin_registry", "harness_admission", "tooling_hosts"):
            self.assertEqual(source_violations(f"from .{module} import x\n"), {"runtime-or-grant-import"}, module)
        self.assertEqual(source_violations("from . import plugin_registry\n"), {"runtime-or-grant-import"})

    def test_host_binary_is_caught_in_every_spelling_a_launch_takes(self):
        for text in ("claude", "Claude.exe", "claude --print -p x"):
            self.assertEqual(source_violations(f"X = {text!r}\n"), {"host-binary"}, text)
        self.assertEqual(source_violations("X = 'the claude code host'\n"), set())

    def test_launch_through_the_standard_library_is_caught(self):
        for call in ("os.system('x')", "os.popen('x')", "os.execvp('x', [])", "os.posix_spawn('x', [], {})"):
            self.assertEqual(source_violations(f"import os\n{call}\n"), {"direct-process"}, call)


class CommandScopeTests(unittest.TestCase):
    def test_commands_are_named_only_by_their_own_modules(self):
        files = package_modules()
        self.assertTrue(set(files) >= COMMAND_FILES)
        self.assertEqual(command_leaks(files), [])

    def test_a_command_named_in_the_mcp_server_is_a_new_tool(self):
        files = {"cli.py": "check-ownership", "plugin_mcp.py": "name='check-ownership'"}
        self.assertEqual(command_leaks(files), ["plugin_mcp.py"])

    def _importers(self, *modules: str) -> set[str]:
        importers = set()
        for name, text in package_modules().items():
            _, relative = _imports(ast.parse(text))
            if relative & set(modules):
                importers.add(name)
        return importers

    def test_only_the_dispatcher_and_the_implementation_import_the_deliverables(self):
        self.assertEqual(self._importers("ownership", "ownership_cli"), {"cli.py", "ownership_cli.py"})

    def test_the_overlap_rule_is_shared_not_copied(self):
        self.assertEqual(self._importers("path_overlap"), {"ownership.py", "runtime_scheduler.py"})


class ExecutionAuthorizationTests(unittest.TestCase):
    SCHEMAS = sorted((SPEC / "contracts").glob("*.schema.json"))

    def test_every_schema_that_names_the_member_pins_it_to_false(self):
        named = [p for p in self.SCHEMAS if "executionAuthorization" in p.read_text(encoding="utf-8")]
        self.assertGreaterEqual(len(named), 4)
        for path in named:
            self.assertEqual(schema_violations(json.loads(path.read_text(encoding="utf-8"))), [], path.name)

    def test_a_schema_that_lets_the_member_vary_is_caught(self):
        for loose in ({"type": "boolean"}, {"enum": [False, True]}, {"const": True}, {}):
            schema = {"properties": {"executionAuthorization": loose}}
            self.assertEqual(schema_violations(schema), ["$.properties.executionAuthorization"], loose)

    def test_contract_examples_authorize_nothing(self):
        examples = sorted((SPEC / "contracts").glob("*.example*.json"))
        self.assertTrue(examples)
        for path in examples:
            self.assertEqual(authorization_violations(json.loads(path.read_text(encoding="utf-8"))), [], path.name)

    def test_emitted_objects_authorize_nothing(self):
        decl = declaration()
        expansion = ownership.expand_declaration(decl, TREE, repo_root="/repo", pinned_commit=BASE)
        receipt = receipt_for(decl, {"a": observed(("M", "src/b.py")), "b": observed()})
        for label, emitted in (("preflight", ownership.build_preflight(expansion)), ("receipt", receipt)):
            self.assertIn("executionAuthorization", json.dumps(emitted), label)
            self.assertEqual(authorization_violations(emitted), [], label)

    def test_a_seeded_authorization_is_caught_wherever_it_is_nested(self):
        for seeded in ({"executionAuthorization": True}, {"a": [{"executionAuthorization": "false"}]},
                       {"x": {"executionAuthorization": 0}}):
            self.assertTrue(authorization_violations(seeded), seeded)
        self.assertEqual(authorization_violations({"executionAuthorization": False}), [])


class PluginPackageTests(unittest.TestCase):
    PLUGIN = ROOT / "integrations/agent-braid"

    def test_plugin_source_adds_no_component_or_orchestration_skill(self):
        paths = [p.relative_to(self.PLUGIN).as_posix() for p in self.PLUGIN.rglob("*")]
        self.assertTrue(paths)
        self.assertEqual(component_violations(paths), [])

    def test_seeded_components_are_caught(self):
        for path in ("hooks/hooks.json", "plugin/mods/panel.js", "agents/orchestrator.md", "monitors/m.json",
                     "plugin/channels/c.json", "skills/orchestration/SKILL.md", "skills/ownership/SKILL.md"):
            self.assertEqual(component_violations([path]), [path], path)
        self.assertEqual(component_violations(["skills/analyze/SKILL.md", "plugin/.mcp.json"]), [])

    def test_package_test_keeps_its_no_component_assertions(self):
        tree = ast.parse(_source("tests/test_plugin_package.py"))
        tuples = [tuple(e.value for e in n.elts) for n in ast.walk(tree)
                  if isinstance(n, ast.Tuple) and n.elts and all(isinstance(e, ast.Constant) for e in n.elts)]
        self.assertTrue(any({"hooks", "mods", "agents", "monitors"} <= set(t) for t in tuples))

    def test_no_deliverable_ships_in_the_package(self):
        text = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                         for p in self.PLUGIN.rglob("*") if p.is_file())
        for command in COMMANDS:
            self.assertNotIn(command, text)


class HarCrossReferenceTests(unittest.TestCase):
    def test_deliverables_hold_no_compiler_planner_or_har3_module(self):
        self.assertEqual(deliverable_violations(DELIVERABLES), [])
        for path in ("agent_braid/hook_profile_compiler.py", "agent_braid/orchestration_planner.py",
                     "agent_braid/harness_hooks.py", "agent_braid/harness_orchestration.py",
                     "agent_braid/harness_lifecycle.py"):
            self.assertEqual(deliverable_violations([path]), [path], path)

    def test_cross_reference_states_what_is_reused_and_what_is_independent(self):
        plan = (SPEC / "plan.md").read_text(encoding="utf-8")
        section = plan.split("### HAR.3 cross-reference", 1)[1].split("\n### ", 1)[0]
        for token in ("T005", "T006", "T011", "specs/050-braid-harness-adaptation", "Reused", "Independent"):
            self.assertIn(token, section, token)
        for module in HAR3_MODULES:
            self.assertIn(f"agent_braid/{module}.py", section, module)


if __name__ == "__main__":
    unittest.main()
