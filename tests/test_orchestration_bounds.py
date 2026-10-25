# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T013 (REQ-017): fixed bounds of the ownership declaration, one past each."""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
import unittest

from agent_braid import ownership

MODULE = Path(ownership.__file__)
FORBIDDEN_IMPORTS = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "telnetlib", "xmlrpc", "asyncio",
    "subprocess", "multiprocessing", "ctypes", "pty", "signal", "webbrowser", "shutil", "tempfile",
}


def _unit(name: str, **extra):
    unit = {"id": name, "surface": "batch", "reads": [], "writes": []}
    unit.update(extra)
    return unit


def _declaration(units=None, **extra):
    data = {"schemaVersion": ownership.SCHEMA_VERSION, "units": units or [_unit("a"), _unit("b")]}
    data.update(extra)
    return data


def _codes(data) -> list[str]:
    return [d.code for d in ownership.validate_declaration(data)]


class BoundTests(unittest.TestCase):
    def test_units_at_and_one_past_the_bound(self):
        at = _declaration([_unit(f"u{i}") for i in range(ownership.MAX_UNITS)])
        self.assertEqual(_codes(at), [])
        past = _declaration([_unit(f"u{i}") for i in range(ownership.MAX_UNITS + 1)])
        self.assertEqual(_codes(past), ["too-many-units"])
        self.assertEqual(_codes(_declaration([_unit("a")])), ["too-few-units"])

    def test_paths_per_list_at_and_one_past_the_bound(self):
        for name in ownership._UNIT_PATH_LISTS:
            with self.subTest(list=name):
                data = _declaration()
                data["units"][0][name] = [f"p{i}" for i in range(ownership.MAX_PATHS)]
                if name == "criticalReads":
                    data["units"][0]["reads"] = list(data["units"][0][name])
                self.assertEqual(_codes(data), [])
                data["units"][0][name] = [f"p{i}" for i in range(ownership.MAX_PATHS + 1)]
                self.assertIn("too-many-paths", _codes(data))

    def test_exemption_paths_at_and_one_past_the_bound(self):
        paths = [f"p{i}" for i in range(ownership.MAX_PATHS)]
        data = _declaration()
        data["units"][0].update(reads=paths[:256], writes=paths[256:], creates=["extra"])
        data["unattributedWriterExemptions"] = [{"ruleId": "r", "writer": "human", "paths": paths}]
        self.assertEqual(_codes(data), [])
        data["unattributedWriterExemptions"][0]["paths"] = paths + ["extra"]
        self.assertIn("too-many-paths", _codes(data))

    def test_string_length_at_and_one_past_the_bound(self):
        data = _declaration()
        data["units"][0]["writes"] = ["a" * ownership.MAX_STRING]
        self.assertEqual(_codes(data), [])
        data["units"][0]["writes"] = ["a" * (ownership.MAX_STRING + 1)]
        self.assertEqual(_codes(data), ["string-too-long"])
        data = _declaration(base={"ref": "a" * 129})
        self.assertEqual(_codes(data), ["bad-format"])
        data = _declaration(units=[_unit("a" * 65), _unit("b")])
        self.assertEqual(_codes(data), ["bad-format"])
        data = _declaration(units=[_unit("a" * 257), _unit("b")])
        self.assertEqual(_codes(data), ["string-too-long"])

    def test_multibyte_strings_count_characters(self):
        data = _declaration()
        data["units"][0]["writes"] = ["é" * ownership.MAX_STRING]
        self.assertEqual(_codes(data), [])
        data["units"][0]["writes"] = ["é" * (ownership.MAX_STRING + 1)]
        self.assertEqual(_codes(data), ["string-too-long"])

    def test_exemption_rules_at_and_one_past_the_bound(self):
        def rules(count):
            return [{"ruleId": f"r{i}", "writer": "human", "paths": ["a.py"]} for i in range(count)]

        data = _declaration()
        data["units"][0]["writes"] = ["a.py"]
        data["unattributedWriterExemptions"] = rules(ownership.MAX_EXEMPTIONS)
        self.assertEqual(_codes(data), [])
        data["unattributedWriterExemptions"] = rules(ownership.MAX_EXEMPTIONS + 1)
        self.assertEqual(_codes(data), ["too-many-exemptions"])

    def test_dependencies_at_and_one_past_the_bound(self):
        units = [_unit(f"u{i}") for i in range(ownership.MAX_UNITS)]
        units[0]["dependsOn"] = [f"u{i}" for i in range(1, ownership.MAX_UNITS)]
        self.assertEqual(len(units[0]["dependsOn"]), ownership.MAX_DEPENDENCIES)
        self.assertEqual(_codes(_declaration(units)), [])
        units[0]["dependsOn"].append("u1x")
        self.assertIn("too-many-dependencies", _codes(_declaration(units)))

    def test_shared_resources_at_and_one_past_the_bound(self):
        data = _declaration()
        data["units"][0]["sharedResources"] = [{"class": "other"}] * ownership.MAX_SHARED_RESOURCES
        self.assertEqual(_codes(data), [])
        data["units"][0]["sharedResources"] = [{"class": "other"}] * (ownership.MAX_SHARED_RESOURCES + 1)
        self.assertEqual(_codes(data), ["too-many-shared-resources"])

    def test_input_size_at_and_one_past_the_bound(self):
        base = json.dumps(_declaration()).encode()
        at = base + b" " * (ownership.MAX_DECLARATION_BYTES - len(base))
        self.assertEqual(len(at), ownership.MAX_DECLARATION_BYTES)
        self.assertEqual(ownership.load_declaration(at), _declaration())
        with self.assertRaises(ownership.DeclarationRefused) as caught:
            ownership.load_declaration(at + b" ")
        self.assertEqual([d.code for d in caught.exception.diagnostics], ["input-too-large"])

    def test_oversized_file_is_refused_without_reading_it_whole(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "big.json"
            path.write_bytes(b" " * (ownership.MAX_DECLARATION_BYTES + 4096))
            with self.assertRaises(ownership.DeclarationRefused) as caught:
                ownership.load_declaration_file(path)
            self.assertEqual(caught.exception.diagnostics[0].code, "input-too-large")


class ExpansionBoundTests(unittest.TestCase):
    def test_maximal_declaration_expands_within_bounds(self):
        import time

        files = frozenset(f"d{u}/f{i}.py" for u in range(ownership.MAX_UNITS) for i in range(ownership.MAX_PATHS))
        tree = ownership.BaseTree(files)
        units = []
        for u in range(ownership.MAX_UNITS):
            unit = _unit(f"u{u}", reads=[f"d{u}/f{i}.py" for i in range(ownership.MAX_PATHS)],
                         writes=[f"d{u}/f{i}.py" for i in range(ownership.MAX_PATHS)], creates=[f"n{u}/"])
            unit["complete"] = False
            units.append(unit)
        started = time.monotonic()
        expansion = ownership.expand_declaration(
            {"schemaVersion": ownership.SCHEMA_VERSION, "base": {"ref": "develop"}, "units": units}, tree)
        records = ownership.to_aim(expansion)
        self.assertLess(time.monotonic() - started, 30)
        self.assertEqual(len(records), ownership.MAX_UNITS)
        self.assertLessEqual(max(len(u.exact["writes"]) for u in expansion.units), ownership.MAX_PATHS)

    def test_pattern_work_is_bounded(self):
        tree = ownership.BaseTree(frozenset(f"d/f{i}.py" for i in range(12000)))
        units = [_unit("a", writes=[f"d/*{i}.x" for i in range(ownership.MAX_PATHS)]), _unit("b")]
        expansion = ownership.expand_declaration(
            {"schemaVersion": ownership.SCHEMA_VERSION, "base": {"ref": "develop"}, "units": units}, tree)
        self.assertIn("expansion-bound", expansion.units[0].reasons)
        self.assertEqual(expansion.units[0].coverage, "partial")


class PurityTests(unittest.TestCase):
    def _imports(self) -> set[str]:
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    self.assertEqual((node.level, node.module), (1, "path_overlap"), "only the neutral overlap helper")
                    continue
                names.add((node.module or "").split(".")[0])
        return names

    def test_module_imports_only_the_standard_library(self):
        imports = self._imports()
        self.assertTrue(imports)
        self.assertEqual(imports - set(sys.stdlib_module_names), set())

    def test_module_imports_no_network_socket_or_process_helper(self):
        self.assertEqual(self._imports() & FORBIDDEN_IMPORTS, set())

    def test_overlap_helper_is_pure_and_standard_library_only(self):
        tree = ast.parse((MODULE.parent / "path_overlap.py").read_text(encoding="utf-8"))
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        froms = {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        self.assertEqual(imports | froms, {"__future__"})

    def test_module_calls_no_process_or_dynamic_execution_primitive(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        names = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        attrs = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertEqual(names & {"eval", "exec", "compile", "__import__"}, set())
        self.assertEqual(attrs & {"system", "popen", "Popen", "run", "fork", "spawn"}, set())

    def test_module_is_read_only(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "open":
                modes = [a.value for a in node.args[1:2] if isinstance(a, ast.Constant)]
                self.assertEqual(modes, ["rb"])
        source = MODULE.read_text(encoding="utf-8")
        for token in (".write(", "write_text", "write_bytes", ".unlink(", ".mkdir(", "os.remove"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
