# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T006 (REQ-006 / SC-006, procedure_006): the ``units`` kind of ``analyze-work``."""

from __future__ import annotations

import builtins
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import jsonschema
from referencing import Registry, Resource

from agent_braid import analysis, tooling_mcp, units
from agent_braid.tooling_mcp import ToolingConfig, ToolingService
from scripts import spec069_generate_corpus as generator
from tests.spec069_differential import ROOT, load_corpus

GOLDEN = generator.UNITS_OUTPUT / "golden"
SCOPE = generator.GOLDEN_SCOPE
AIM_SCHEMA = json.loads((ROOT / "schemas/0.2.0-draft/agent-interaction-metadata.schema.json").read_text())
INPUT_SCHEMA = json.loads((ROOT / "schemas/0.1.0-alpha/analysis-input.schema.json").read_text())
SEMANTIC_CODES = {"duplicate unit id": "duplicate-unit-id", "unknown dependency": "unknown-dependency",
                  "self dependency": "self-dependency", "cyclic dependencies": "cyclic-dependencies",
                  "resources differ only by letter case": "case-only-duplicate-resource",
                  "case-only difference inside one unit": "case-only-duplicate-resource"}


def golden_request(name: str) -> dict:
    return json.loads((GOLDEN / f"{name}.request.json").read_text())


def request(*items: dict) -> dict:
    return generator.units_request(*items)


unit = generator.unit


class UnitsServiceCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        source, results = Path(self.temp.name) / "source", Path(self.temp.name) / "results"
        source.mkdir(), results.mkdir()
        self.service = ToolingService(ToolingConfig(source, results))

    def call(self, kind: str, value) -> dict:
        return self.service.invoke("analyze-work", {"kind": kind, "request": value}, threading.Event())

    def accepted(self, value) -> dict:
        envelope = self.call("units", value)
        self.assertEqual(envelope["status"], "ok", envelope["summary"])
        return envelope["result"]

    def refused(self, value) -> str:
        envelope = self.call("units", value)
        self.assertEqual(envelope["status"], "refused", envelope["summary"])
        self.assertLessEqual(len(envelope["summary"]), 1024)
        return envelope["summary"]

    def pairs(self, value) -> list[dict]:
        return self.accepted(value)["report"]["interactions"]


class GoldenTests(UnitsServiceCase):
    def test_goldens_validate_against_the_aim_and_envelope_schemas(self):
        record = jsonschema.Draft202012Validator(AIM_SCHEMA)
        registry = Registry().with_resources([(AIM_SCHEMA["$id"], Resource.from_contents(AIM_SCHEMA))])
        envelope = jsonschema.Draft202012Validator(INPUT_SCHEMA, registry=registry)
        for name in generator.GOLDEN_REQUESTS:
            constructed = json.loads((GOLDEN / f"{name}.constructed.json").read_text())
            with self.subTest(name):
                envelope.validate(constructed)
                for item in constructed["operations"]:
                    record.validate(item)

    def test_construction_equals_the_golden_bytes(self):
        for name in generator.GOLDEN_REQUESTS:
            built = units.construct(golden_request(name), SCOPE)["constructedRequest"]
            with self.subTest(name):
                self.assertEqual(generator.golden_bytes(built), (GOLDEN / f"{name}.constructed.json").read_text())

    def test_t010_request_through_analyze_work(self):
        """SC-006 main path: golden bytes, replay through kind aim, conflicting, partial, provenance."""
        with patch.object(units, "workspace_scope", lambda root: SCOPE):
            result = self.accepted(golden_request("t010-readme-conflict"))
        constructed = result["constructedRequest"]
        self.assertEqual(generator.golden_bytes(constructed),
                         (GOLDEN / "t010-readme-conflict.constructed.json").read_text())
        (pair,) = result["report"]["interactions"]
        self.assertEqual(pair["classification"], "conflicting")
        self.assertEqual(pair["constraints"], ["serialize-or-isolate"])
        self.assertEqual(pair["evidence"]["coverage"], ["partial"])
        self.assertEqual({op["coverage"]["status"] for op in result["report"]["operations"]}, {"partial"})
        self.assertEqual(result["provenance"]["construction"], "agent-braid.units-declaration/0.1.0-alpha")
        self.assertEqual(result["provenance"]["source"], "units declaration")
        self.assertIs(result["provenance"]["executionAuthorization"], False)
        replay = self.call("aim", constructed)
        self.assertEqual(replay["status"], "ok")
        self.assertEqual(tooling_mcp._json_bytes(replay["result"]["report"]),
                         tooling_mcp._json_bytes(result["report"]))

    def test_digests_follow_the_contract_construction_table(self):
        """Recomputed here from the contract text, not from the module's helpers."""
        constructed = json.loads((GOLDEN / "ordered.constructed.json").read_text())
        rules = "agent-braid.units-declaration/0.1.0-alpha"
        for item in constructed["operations"]:
            self.assertEqual(item["definition"], {"id": rules, "digest": "sha256:" + hashlib.sha256(rules.encode()).hexdigest()})
            declaration = {
                "construction": rules, "workspace": SCOPE, "id": item["instanceId"],
                "dependencies": item["dependencies"],
                "effects": [{"kind": e["kind"], "resource": e["resource"].removeprefix(f"repo://{SCOPE}/")}
                            for e in item["effects"]["declared"]],
            }
            text = json.dumps(declaration, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
            self.assertEqual(item["inputDigest"], "sha256:" + hashlib.sha256(text.encode()).hexdigest())
            self.assertEqual(item["attemptId"], item["instanceId"])
            self.assertEqual(item["evidence"][0]["method"], "declared")
            self.assertEqual(item["evidence"][0]["assuranceClass"], 0)
            self.assertEqual(item["effects"]["inferred"] + item["effects"]["observed"], [])
            self.assertEqual(item["readVersions"], {})

    def test_different_declarations_have_different_input_digests(self):
        variants = [
            request(unit("u", ("write", "README.md"))),
            request(unit("u", ("read", "README.md"))),
            request(unit("u", ("write", "docs/README.md"))),
            request(unit("v", ("write", "README.md"))),
            request(unit("u", ("write", "README.md")), unit("w", ("write", "x"))),
        ]
        variants[4]["units"][0]["dependencies"] = ["w"]
        digests = {units.construct(v, SCOPE)["constructedRequest"]["operations"][0]["inputDigest"] for v in variants}
        self.assertEqual(len(digests), len(variants))
        other_scope = units.construct(variants[0], "f" * 32)["constructedRequest"]["operations"][0]["inputDigest"]
        self.assertNotIn(other_scope, digests)


class NegativeControlTests(UnitsServiceCase):
    def test_dot_slash_alias_is_the_same_resource(self):
        (pair,) = self.pairs(golden_request("dot-slash-alias"))
        self.assertEqual(pair["classification"], "conflicting")
        self.assertEqual(len(pair["sharedResources"]), 1)
        self.assertTrue(pair["sharedResources"][0].endswith("/README.md"))

    def test_other_lexical_aliases_are_the_same_resource(self):
        for left, right in (("docs/guide.md", "docs//guide.md"), ("docs", "docs/"),
                            ("docs/guide.md", "docs/./guide.md"), ("docs/caf\u00e9.md", "docs/cafe\u0301.md")):
            with self.subTest(left=left, right=right):
                (pair,) = self.pairs(request(unit("a", ("write", left)), unit("b", ("write", right))))
                self.assertEqual(pair["classification"], "conflicting")

    def test_claimed_complete_coverage_is_recorded_as_partial(self):
        claimed = golden_request("t010-readme-conflict")
        for item in claimed["units"]:
            item["coverage"] = "complete"
        result = self.accepted(claimed)
        self.assertEqual({op["effects"]["coverage"]["status"] for op in result["constructedRequest"]["operations"]},
                         {"partial"})
        plain = self.accepted(golden_request("t010-readme-conflict"))
        self.assertEqual(tooling_mcp._json_bytes(result), tooling_mcp._json_bytes(plain))

    def test_disjoint_units_are_unknown_never_independent_candidate(self):
        (pair,) = self.pairs(golden_request("disjoint-claimed-complete"))
        self.assertEqual(pair["classification"], "unknown")
        self.assertEqual(pair["constraints"], ["serialize-unless-stronger-evidence"])
        self.assertNotIn("completenessBasis", pair)

    def test_no_accepted_corpus_request_is_independent_candidate(self):
        seen = set()
        for case in load_corpus("units"):
            if case["expect"]["service"] == "accepts":
                for pair in self.pairs(case["request"]):
                    seen.add(pair["classification"])
                    self.assertNotEqual(pair["classification"], "independent-candidate", case["id"])
        self.assertLessEqual({"ordered", "conflicting", "unknown"}, seen)

    def test_dependencies_order_units(self):
        (pair,) = self.pairs(golden_request("ordered"))
        self.assertEqual(pair["classification"], "ordered")
        self.assertEqual(pair["constraints"], ["preserve-dependency-order"])

    def test_sc006_refusals_follow_req007(self):
        structural = {
            "dot-dot path": (request(unit("u", ("write", "../secret-dir/x"))), "/units/0/effects/0/resource"),
            "absolute path": (request(unit("u", ("write", "/etc/secret-host-file"))), "/units/0/effects/0/resource"),
            "33 units": (request(*[unit(f"u{i}", ("write", f"f{i}")) for i in range(33)]), "/units"),
            "257-byte identifier": (request(unit("s" * 257, ("write", "a"))), "/units/0/id"),
            "unsupported effect kind": (request(unit("u", ("modify-secret", "a"))), "/units/0/effects/0/kind"),
        }
        for label, (value, pointer) in structural.items():
            with self.subTest(label):
                summary = self.refused(value)
                self.assertIn(f" at {pointer}; expected ", summary)
                for secret in ("secret-dir", "secret-host-file", "s" * 40, "modify-secret"):
                    self.assertNotIn(secret, summary)
        semantic = {
            "case-only duplicate": (request(unit("u", ("write", "Secret.md")), unit("v", ("write", "secret.md"))),
                                    "case-only-duplicate-resource"),
            "duplicate identifier": (request(unit("dup-secret", ("write", "a")), unit("dup-secret", ("write", "b"))),
                                     "duplicate-unit-id"),
            "unknown dependency": (request(unit("u", ("write", "a"), dependencies=["ghost-secret"])), "unknown-dependency"),
        }
        for label, (value, code) in semantic.items():
            with self.subTest(label):
                summary = self.refused(value)
                self.assertTrue(summary.endswith(f"[{code}]"), summary)
                self.assertNotIn("ecret", summary)

    def test_unknown_keys_are_tokenized(self):
        value = request(unit("u", ("write", "a")))
        value["units"][0]["sk-live-SECRET0123"] = "value-that-must-not-leak"
        value["api_key_SECRET"] = 1
        summary = self.refused(value)
        self.assertNotIn("SECRET", summary)
        self.assertNotIn("value-that-must-not-leak", summary)
        self.assertIn(analysis.key_token("api_key_SECRET"), summary)

    def test_two_runs_give_identical_bytes(self):
        first = self.accepted(golden_request("ordered"))
        second = self.accepted(golden_request("ordered"))
        self.assertEqual(tooling_mcp._json_bytes(first), tooling_mcp._json_bytes(second))
        self.assertEqual(json.dumps(first), json.dumps(second))  # insertion order too, not only sorted keys

    def test_construction_is_identical_across_processes_and_hash_seeds(self):
        script = ("import json,sys; from agent_braid import units; "
                  "print(json.dumps(units.analyze(json.load(sys.stdin), sys.argv[1])))")
        payload = (GOLDEN / "ordered.request.json").read_text()
        outputs = set()
        for seed in ("0", "1", "4242"):
            process = subprocess.run([sys.executable, "-c", script, SCOPE], input=payload, capture_output=True,
                                     text=True, cwd=ROOT, env=dict(os.environ, PYTHONHASHSEED=seed), check=True)
            outputs.add(process.stdout)
        self.assertEqual(len(outputs), 1)
        self.assertEqual(json.loads(outputs.pop()), units.analyze(golden_request("ordered"), SCOPE))

    def test_construction_never_touches_the_filesystem(self):
        def refuse(*_args, **_kwargs):
            raise AssertionError("filesystem access during construction")
        value = request(unit("a", ("write", "README.md")), unit("b", ("read", "./README.md")))
        with patch.object(builtins, "open", refuse), patch.object(os, "stat", refuse), \
                patch.object(os, "lstat", refuse), patch.object(os, "scandir", refuse), \
                patch.object(os, "listdir", refuse):
            units.analyze(value, SCOPE)

    def test_unsupported_kind_is_still_refused(self):
        envelope = self.call("unit", request(unit("u", ("write", "a"))))
        self.assertEqual(envelope["status"], "refused")
        self.assertIn("Unsupported analysis kind", envelope["summary"])


class CorpusRefusalTests(UnitsServiceCase):
    """REQ-007 for the units corpus: pointer and expected form, or a fixed code."""

    def test_structural_refusals_name_pointer_and_expected_form(self):
        checked = 0
        for case in load_corpus("units"):
            if case["layer"] not in {"structural", "adapter"} or case["expect"]["service"] != "refuses":
                continue
            with self.subTest(case["id"], label=case["label"]):
                summary = self.refused(case["request"])
                self.assertIn(f" at {case['pointer'] or '/'}; expected ", summary)
            checked += 1
        self.assertGreater(checked, 70)

    def test_batch_refusals_carry_fixed_codes_and_pointers(self):
        checked = 0
        for case in load_corpus("units"):
            if case["layer"] != "batch" or case["label"] not in SEMANTIC_CODES:
                continue
            with self.subTest(case["id"], label=case["label"]):
                summary = self.refused(case["request"])
                self.assertTrue(summary.endswith(f" at {case['pointer']} [{SEMANTIC_CODES[case['label']]}]"), summary)
            checked += 1
        self.assertEqual(checked, len(SEMANTIC_CODES))


class BoundsAndScopeTests(UnitsServiceCase):
    def test_bounds_equal_the_adapter_bounds(self):
        self.assertEqual(units.MAX_UNITS, tooling_mcp.MAX_OPERATIONS)
        self.assertEqual(units.MAX_IDENTIFIER_BYTES, tooling_mcp.MAX_IDENTIFIER_BYTES)
        self.assertEqual(tooling_mcp._operation_count(request(*[unit(f"u{i}", ("write", "a")) for i in range(5)])), 5)

    def test_negative_control_adapter_bounds_still_apply_if_units_bounds_drift(self):
        """A7: the shared adapter bounds refuse even when the units module's own bounds are loosened."""
        with patch.object(units, "MAX_UNITS", 64):
            summary = self.refused(request(*[unit(f"u{i}", ("write", f"f{i}")) for i in range(33)]))
            self.assertTrue(summary.startswith("analyze-work refused: Request exceeds the 32-operation adapter limit"))
        with patch.object(units, "MAX_IDENTIFIER_BYTES", 4096):
            summary = self.refused(request(unit("i" * 257, ("write", "a")), unit("j", ("write", "b"))))
            self.assertIn("Operation identifier exceeds 256 bytes", summary)

    def test_scope_is_derived_from_the_configured_source_root(self):
        result = self.accepted(request(unit("u", ("write", "README.md"))))
        scope = units.workspace_scope(self.service.config.source_root)
        self.assertEqual(result["provenance"]["workspaceScope"], scope)
        resource = result["constructedRequest"]["operations"][0]["effects"]["declared"][0]["resource"]
        self.assertEqual(resource, f"repo://{scope}/README.md")
        self.assertNotIn(str(self.service.config.source_root), json.dumps(result))

    def test_invalid_scope_is_an_internal_error_not_a_constructed_record(self):
        for scope in ("", "../x", "A" * 32, "a" * 31):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                units.construct(request(unit("u", ("write", "a"))), scope)


class PluginScopeTests(unittest.TestCase):
    """A4: the plugin strips workspaceId before the service; the derived scope equals it."""

    from tests import test_plugin_registry as _registry
    setUp = _registry.PluginRegistryTests.setUp
    install = _registry.PluginRegistryTests.install

    def test_units_resources_carry_the_registered_workspace_id(self):
        from agent_braid.plugin_mcp import PluginRouter
        from agent_braid.plugin_registry import load
        self.install()
        router = PluginRouter(self.home)
        (identifier,) = [row["workspaceId"] for row in load(self.home)["workspaces"]]
        envelope = router.invoke("analyze-work", {"workspaceId": identifier, "kind": "units",
                                                  "request": golden_request("t010-readme-conflict")},
                                 threading.Event())
        self.assertEqual(envelope["status"], "ok", envelope["summary"])
        self.assertEqual(envelope["result"]["provenance"]["workspaceScope"], identifier)
        for item in envelope["result"]["constructedRequest"]["operations"]:
            self.assertTrue(item["effects"]["declared"][0]["resource"].startswith(f"repo://{identifier}/"))
        self.assertEqual(units.workspace_scope(router.services[identifier].config.source_root), identifier)


if __name__ == "__main__":
    unittest.main()
