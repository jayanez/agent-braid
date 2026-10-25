# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T012/T013: ownership declaration schema, fixtures and validator."""

from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import unittest

from jsonschema import Draft202012Validator

from agent_braid import ownership

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "specs" / "057-claude-orchestration-advisory" / "contracts"
SCHEMA_PATH = CONTRACTS / "ownership-declaration.schema.json"
EXAMPLE_PATH = CONTRACTS / "ownership-declaration.example.json"
FIXTURES = ROOT / "tests" / "fixtures" / "ownership"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


SCHEMA = _load(SCHEMA_PATH)
SCHEMA_VALIDATOR = Draft202012Validator(SCHEMA)
EXPECTATIONS = _load(FIXTURES / "expectations.json")


def _codes(data) -> list[str]:
    return [d.code for d in ownership.validate_declaration(data)]


def _declaration(units=None, **extra):
    unit = lambda name: {"id": name, "surface": "batch", "reads": [], "writes": [f"{name}.py"]}
    data = {"schemaVersion": ownership.SCHEMA_VERSION, "units": units or [unit("a"), unit("b")]}
    data.update(extra)
    return data


class SchemaContractTests(unittest.TestCase):
    def test_schema_is_a_valid_draft_2020_12_document(self):
        self.assertEqual(SCHEMA["$schema"], "https://json-schema.org/draft/2020-12/schema")
        Draft202012Validator.check_schema(SCHEMA)

    def test_surface_ids_are_the_closed_four_id_set(self):
        self.assertEqual(
            tuple(SCHEMA["$defs"]["unit"]["properties"]["surface"]["enum"]), ownership.SURFACES
        )
        self.assertEqual(ownership.SURFACES, ("workflow-tracks", "linked-sessions", "agent-teams", "batch"))

    def test_core_schema_has_no_vendor_member(self):
        names: set[str] = set()

        def walk(node):
            if isinstance(node, dict):
                names.update(node.get("properties", {}))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(SCHEMA)
        for name in names:
            self.assertIsNone(re.search(r"claude|anthropic|codex|openai|cursor|vendor", name, re.I), name)

    def test_no_member_can_carry_content(self):
        names: set[str] = set()

        def walk(node):
            if isinstance(node, dict):
                names.update(node.get("properties", {}))
                for value in node.values():
                    walk(value)
            elif isinstance(node, list):
                for value in node:
                    walk(value)

        walk(SCHEMA)
        for banned in ("content", "text", "prompt", "command", "transcript", "message", "body"):
            self.assertNotIn(banned, names)

    def test_validator_patterns_and_bounds_match_the_schema(self):
        defs = SCHEMA["$defs"]
        props = SCHEMA["properties"]
        self.assertEqual(ownership.PATH_PATTERN, defs["path"]["pattern"])
        self.assertEqual(ownership.MAX_STRING, defs["path"]["maxLength"])
        self.assertEqual(ownership.MAX_PATHS, defs["pathList"]["maxItems"])
        self.assertEqual(ownership.MAX_UNITS, props["units"]["maxItems"])
        self.assertEqual(ownership.MIN_UNITS, props["units"]["minItems"])
        self.assertEqual(ownership.MAX_EXEMPTIONS, props["unattributedWriterExemptions"]["maxItems"])
        self.assertEqual(ownership.MAX_DEPENDENCIES, defs["unit"]["properties"]["dependsOn"]["maxItems"])
        self.assertEqual(ownership.MAX_SHARED_RESOURCES, defs["unit"]["properties"]["sharedResources"]["maxItems"])
        self.assertEqual(ownership.REF_PATTERN, props["base"]["properties"]["ref"]["pattern"])
        self.assertEqual(ownership.COMMIT_PATTERN, props["base"]["properties"]["commit"]["pattern"])
        self.assertEqual(ownership.TOOL_PATTERN, props["importedFrom"]["properties"]["tool"]["pattern"])
        self.assertEqual(ownership.VERSION_PATTERN, props["importedFrom"]["properties"]["version"]["pattern"])
        self.assertEqual(
            ownership.IDENT_PATTERN, props["unattributedWriterExemptions"]["items"]["properties"]["ruleId"]["pattern"]
        )
        self.assertEqual(ownership.SCHEMA_VERSION, props["schemaVersion"]["const"])
        self.assertEqual(tuple(props["provenance"]["enum"]), ownership.PROVENANCES)
        self.assertEqual(
            tuple(props["unattributedWriterExemptions"]["items"]["properties"]["writer"]["enum"]), ownership.WRITERS
        )
        classes = defs["unit"]["properties"]["sharedResources"]["items"]["properties"]["class"]["enum"]
        self.assertEqual(tuple(classes), ownership.RESOURCE_CLASSES)

    def test_reserved_unit_id_is_refused_by_the_schema_pattern(self):
        pattern = re.compile(SCHEMA["$defs"]["unit"]["properties"]["id"]["pattern"])
        self.assertIsNone(pattern.search(ownership.RESERVED_UNIT_ID))
        self.assertIsNotNone(pattern.search("unattributed-2"))


class ValidFixtureTests(unittest.TestCase):
    def test_contract_example_is_accepted_by_schema_and_validator(self):
        data = _load(EXAMPLE_PATH)
        self.assertEqual(list(SCHEMA_VALIDATOR.iter_errors(data)), [])
        self.assertEqual(ownership.validate_declaration(data), ())

    def test_every_valid_fixture_is_accepted_by_schema_and_validator(self):
        names = EXPECTATIONS["valid"]
        self.assertEqual(sorted(p.name for p in (FIXTURES / "valid").glob("*.json")), names)
        for name in names:
            with self.subTest(name=name):
                data = _load(FIXTURES / "valid" / name)
                self.assertEqual(list(SCHEMA_VALIDATOR.iter_errors(data)), [])
                self.assertEqual(ownership.validate_declaration(data), ())
                self.assertEqual(ownership.load_declaration_file(FIXTURES / "valid" / name), data)


class InvalidFixtureTests(unittest.TestCase):
    def test_fixture_directory_matches_expectations(self):
        names = sorted(p.stem for p in (FIXTURES / "invalid").glob("*.json"))
        self.assertEqual(names, sorted(EXPECTATIONS["invalid"]))

    def test_every_invalid_fixture_is_refused_with_its_stable_code(self):
        for name, expected in EXPECTATIONS["invalid"].items():
            with self.subTest(name=name):
                data = _load(FIXTURES / "invalid" / f"{name}.json")
                self.assertIn(expected["code"], _codes(data))
                with self.assertRaises(ownership.DeclarationRefused) as caught:
                    ownership.load_declaration_file(FIXTURES / "invalid" / f"{name}.json")
                self.assertIn(expected["code"], [d.code for d in caught.exception.diagnostics])

    def test_schema_and_validator_agree_on_what_the_schema_can_express(self):
        for name, expected in EXPECTATIONS["invalid"].items():
            with self.subTest(name=name):
                data = _load(FIXTURES / "invalid" / f"{name}.json")
                rejected = bool(list(SCHEMA_VALIDATOR.iter_errors(data)))
                self.assertEqual(rejected, expected["schemaRejects"])

    def test_validator_only_rules_are_not_schema_guarantees(self):
        only = [n for n, e in EXPECTATIONS["invalid"].items() if not e["schemaRejects"]]
        self.assertEqual(
            sorted(only),
            [
                "critical-read-not-in-reads",
                "dependency-on-self",
                "dependency-unknown-unit",
                "duplicate-unit-id",
                "exemption-duplicate-rule-id",
                "exemption-path-undeclared",
            ],
        )

    def test_diagnostics_never_echo_repository_text(self):
        secret = "SECRET-token-9f3a"
        cases = [
            {**_declaration(), secret: 1},
            _declaration(units=[{"id": secret + "!", "surface": "batch", "reads": [], "writes": []}, _declaration()["units"][1]]),
            _declaration(units=[{"id": "a", "surface": secret, "reads": [], "writes": []}, _declaration()["units"][1]]),
            _declaration(base={"ref": secret + ".."}),
            _declaration(units=[{"id": "a", "surface": "batch", "reads": [], "writes": [secret + "\n"]}, _declaration()["units"][1]]),
            _declaration(units=[{"id": "a", "surface": "batch", "reads": [], "writes": [], "dependsOn": [secret]}, _declaration()["units"][1]]),
            _declaration(units=[{"id": "a", "surface": "batch", "reads": [], "writes": [], secret: []}, _declaration()["units"][1]]),
        ]
        for case in cases:
            diagnostics = ownership.validate_declaration(case)
            self.assertTrue(diagnostics)
            for diagnostic in diagnostics:
                self.assertNotIn(secret, repr(diagnostic))
                self.assertNotIn(secret, str(ownership.DeclarationRefused(diagnostics)))

    def test_every_class_of_the_text_exclusion_set_is_refused_also_before_a_line_feed(self):
        samples = _load(FIXTURES / "path-exclusion-set.json")
        self.assertGreaterEqual(len(samples), 16)
        for name, sample in samples.items():
            for variant in (sample, sample + "\n"):
                with self.subTest(name=name, line_feed=variant.endswith("\n")):
                    data = _declaration()
                    data["units"][0]["writes"] = [variant]
                    self.assertTrue(list(SCHEMA_VALIDATOR.iter_errors(data)))
                    self.assertIn("forbidden-character", _codes(data))

    def test_each_mutation_is_refused_for_the_same_reason_by_schema_and_validator(self):
        base = _declaration(
            base={"ref": "develop"},
            provenance="imported",
            importedFrom={"tool": "other-tool", "version": "1.0"},
        )
        self.assertEqual(ownership.validate_declaration(base), ())
        self.assertEqual(list(SCHEMA_VALIDATOR.iter_errors(base)), [])
        mutations = {
            "bad-base-commit": lambda d: d.__setitem__("base", {"commit": "ABC"}),
            "bad-tool": lambda d: d["importedFrom"].__setitem__("tool", "Other Tool"),
            "bad-version": lambda d: d["importedFrom"].__setitem__("version", "-1"),
            "extra-imported-member": lambda d: d["importedFrom"].__setitem__("url", "x"),
            "non-string-path": lambda d: d["units"][0].__setitem__("reads", [1]),
            "unit-not-object": lambda d: d["units"].__setitem__(0, "a"),
            "units-not-array": lambda d: d.__setitem__("units", {}),
            "bool-as-string": lambda d: d.__setitem__("provenance", True),
            "shared-resource-extra": lambda d: d["units"][0].__setitem__("sharedResources", [{"class": "other", "x": 1}]),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                data = copy.deepcopy(base)
                mutate(data)
                self.assertTrue(list(SCHEMA_VALIDATOR.iter_errors(data)))
                self.assertTrue(ownership.validate_declaration(data))


class ValidatorRuleTests(unittest.TestCase):
    def test_critical_read_must_be_an_entry_of_reads(self):
        data = _declaration()
        data["units"][0].update(reads=["src/x.py"], criticalReads=["src/x.py"])
        self.assertEqual(ownership.validate_declaration(data), ())
        data["units"][0]["criticalReads"] = ["src/y.py"]
        self.assertEqual(ownership.validate_declaration(data)[0].where, "units[0].criticalReads[0]")

    def test_dependencies_must_name_other_known_units(self):
        data = _declaration()
        data["units"][1]["dependsOn"] = ["a"]
        self.assertEqual(ownership.validate_declaration(data), ())

    def test_exemption_may_name_a_shared_resource_path(self):
        data = _declaration()
        data["units"][0]["sharedResources"] = [{"class": "lockfile", "path": "package-lock.json"}]
        data["unattributedWriterExemptions"] = [
            {"ruleId": "locks", "writer": "shared-tree", "paths": ["package-lock.json"]}
        ]
        self.assertEqual(ownership.validate_declaration(data), ())

    def test_multiple_refusals_are_all_reported_and_capped(self):
        data = _declaration()
        data["units"][0]["writes"] = ["a\n"] * 1 + [f"p{i}\n" for i in range(200)]
        diagnostics = ownership.validate_declaration(data)
        self.assertEqual(len(diagnostics), ownership.MAX_DIAGNOSTICS + 1)
        self.assertEqual(diagnostics[-1].code, "diagnostics-truncated")


class LoaderTests(unittest.TestCase):
    def test_loader_refuses_before_validation(self):
        cases = {
            "syntax": ("invalid-json", b"{"),
            "encoding": ("invalid-encoding", b"\xff\xfe"),
            "duplicate-key": ("invalid-json", b'{"schemaVersion": "x", "schemaVersion": "y"}'),
            "non-finite": ("invalid-json", b'{"units": NaN}'),
            "deep-nesting": ("invalid-json", b"[" * 100000),
            "too-large": ("input-too-large", b" " * (ownership.MAX_DECLARATION_BYTES + 1)),
        }
        for name, (code, raw) in cases.items():
            with self.subTest(name=name):
                with self.assertRaises(ownership.DeclarationRefused) as caught:
                    ownership.load_declaration(raw)
                self.assertEqual([d.code for d in caught.exception.diagnostics], [code])

    def test_loader_accepts_text_and_bytes(self):
        text = json.dumps(_declaration())
        self.assertEqual(ownership.load_declaration(text), ownership.load_declaration(text.encode()))

    def test_unreadable_file_is_a_stable_refusal(self):
        with self.assertRaises(ownership.DeclarationRefused) as caught:
            ownership.load_declaration_file(FIXTURES / "does-not-exist.json")
        self.assertEqual(caught.exception.diagnostics[0].code, "unreadable-input")


if __name__ == "__main__":
    unittest.main()
