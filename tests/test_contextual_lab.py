# SPDX-License-Identifier: AGPL-3.0-only
"""Finite contextual controls; no test supplies theorem or execution approval."""
from copy import deepcopy
from itertools import permutations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from research.contextual_lab import check, source_bindings, verify
from research.contextual_lab import checker
from research.lab import model

ROOT = Path(__file__).resolve().parents[1]


def assign(identifier, target, expression, **fields):
    return {"id": identifier, "kind": "assign", "target": target,
            "dependencies": [], "readVersions": {}, "expression": expression, **fields}


def hidden_request():
    fixture = {"modelVersion": model.MODEL, "state": {"hidden": 0, "visible": 0},
               "versions": {"hidden": 0, "visible": 0},
               "operations": [assign("a", "hidden", {"int": 1}),
                              assign("b", "hidden", {"int": 2}),
                              assign("c", "visible", {"read": "hidden"})],
               "observation": {"mode": "projection", "resources": ["visible"]}}
    return {"requestVersion": checker.VERSION, "fixture": fixture,
            "leftPrefix": ["a", "b"], "rightPrefix": ["b", "a"],
            "suffixes": [[], ["c"]], "caps": {"checks": 20_000, "steps": 120_000},
            "sourceBindings": source_bindings()}


class ContextualChecksTests(unittest.TestCase):
    def test_terminal_match_with_distinguishing_suffix(self):
        report = check(hidden_request())
        self.assertEqual(report["checks"][0]["comparison"], "matching")
        self.assertEqual(report["verdict"], "divergent")
        self.assertEqual(report["witness"]["suffix"], ["c"])
        self.assertEqual(report["checks"][1]["outcomes"]["left"]["state"]["visible"], 2)
        self.assertEqual(report["checks"][1]["outcomes"]["right"]["state"]["visible"], 1)
        self.assertEqual(report["prefixes"]["left"]["outcome"]["pending"], ["c"])
        self.assertEqual(report["prefixes"]["left"]["fragmentOutcome"]["pending"], [])
        self.assertEqual(verify(report)["status"], "verified")
        self.assertFalse(report["executionAuthorization"])
        self.assertFalse(report["proofAccepted"])

    def test_exact_observation_restores_pending_before_observe(self):
        request = hidden_request(); request["fixture"]["observation"] = {"mode": "exact"}
        report = check(request)
        first = report["checks"][0]
        self.assertEqual(first["observations"]["left"]["pending"], ["c"])
        self.assertEqual(first["fragmentOutcomes"]["left"]["pending"], [])
        self.assertEqual(report["witness"]["suffix"], [])

    def test_suffix_binding_and_bounds(self):
        request = hidden_request()
        report = check(request)
        for alter in (lambda r: r["request"].update(suffixes=[[]]),
                      lambda r: r["request"]["caps"].update(checks=19_999),
                      lambda r: r.update(verdict="equivalent-for-listed-continuations"),
                      lambda r: r["checks"][1]["outcomes"]["left"]["state"].update(visible=0),
                      lambda r: r.update(reportHash="sha256:" + "0" * 64),
                      lambda r: r["sourceBindings"].update({"research/lab/model.py": "0" * 64})):
            altered = deepcopy(report); alter(altered)
            self.assertEqual(verify(altered)["status"], "rejected")
        for suffixes in ([['c']], [[], []], [[], ['a']], [[], ['c', 'c']]):
            bad = deepcopy(request); bad["suffixes"] = suffixes
            with self.subTest(suffixes=suffixes), self.assertRaises(model.Invalid):
                check(bad)
        request["suffixes"] = [[]]
        limited = check(request)
        self.assertEqual(limited["verdict"], "equivalent-for-listed-continuations")
        self.assertEqual(limited["coverage"]["requested"], 1)
        self.assertIn("events", limited["checks"][0]["rawDifferences"])

    def test_caps_logical_cache_hits_and_steps(self):
        full = check(hidden_request())
        self.assertEqual(full["costs"], {"checks": 12, "steps": 10, "actualReplays": 4, "cacheHits": 6})
        for key, value in (("checks", 0), ("steps", 0), ("checks", 11), ("steps", 9)):
            request = hidden_request(); request["caps"][key] = value
            report = check(request)
            self.assertEqual(report["verdict"], "inconclusive")
            self.assertIsNotNone(report["coverage"]["capReason"])
            self.assertTrue(report["coverage"]["unvisited"])
            self.assertLessEqual(report["costs"][key], value)
            self.assertEqual(verify(report)["status"], "verified")

    def test_report_byte_reservation_exhaustion_and_minimum_envelope(self):
        request = hidden_request()
        bound = checker._configuration_bound(request["fixture"])
        # Fits the prefix block but refuses the larger next check before retention.
        maximum = len(model.canonical(request)) + 32_768 + 8 * bound + 8000
        with patch.object(checker, "REPORT_BYTES", maximum):
            report = check(request)
            self.assertEqual(report["verdict"], "inconclusive")
            self.assertEqual(report["coverage"]["capReason"], "report-byte-cap")
            self.assertEqual(report["coverage"]["completed"], 0)
            self.assertEqual(report["coverage"]["unvisited"], [0, 1])
            self.assertLessEqual(len(model.canonical(report)), maximum)
            self.assertEqual(verify(report)["status"], "verified")
        with patch.object(checker, "REPORT_BYTES", 100):
            with self.assertRaisesRegex(model.Invalid, "minimum report"):
                check(request)
            self.assertEqual(verify({"request": request})["status"], "rejected")

    def test_prelude_exhaustion_has_explicit_unavailable_placeholders(self):
        request = hidden_request(); request["caps"]["checks"] = 0
        report = check(request)
        self.assertEqual(report["coverage"]["capLocation"],
                         {"phase": "prefix-and-initial-probe-preparation"})
        for side in ("left", "right"):
            self.assertFalse(report["prefixes"][side]["available"])
            self.assertIsNone(report["prefixes"][side]["outcome"])
            self.assertEqual(report["initialEnabledness"][side]["c"]["status"], "unavailable")
            self.assertEqual(report["coverage"]["prelude"]["prefixes"][side], "unvisited")
            self.assertEqual(report["coverage"]["prelude"]["initialProbes"][side]["c"], "unvisited")
        envelope = len(model.canonical(report))
        with patch.object(checker, "REPORT_BYTES", envelope + 32_768 + 100):
            byte_report = check(hidden_request())
            self.assertEqual(byte_report["coverage"]["capReason"], "report-byte-cap")
            self.assertFalse(byte_report["prefixes"]["left"]["available"])
            self.assertEqual(byte_report["coverage"]["unvisited"], [0, 1])
            self.assertEqual(byte_report["costs"]["actualReplays"], 0)

    def test_replay_mapping_matches_unchanged_full_interpreter(self):
        request = hidden_request()
        report = check(request)
        for side, key in (("left", "leftPrefix"), ("right", "rightPrefix")):
            full = model.run(request["fixture"], request[key] + ["c"])
            self.assertEqual(report["checks"][1]["outcomes"][side], full)
        self.assertEqual(model.digest(request), report["requestHash"])

    def test_reachability_dependencies_and_unsupported_extensions_reject(self):
        for change in (lambda r: r.update(rightPrefix=["a"]),
                       lambda r: r["fixture"]["operations"][0].update(dependencies=["c"]),
                       lambda r: r["fixture"]["operations"][0].update(guard={"op": "eq", "left": {"int": 0}, "right": {"int": 1}}),
                       lambda r: r["fixture"]["operations"][2].update(expression={"result": "a"}),
                       lambda r: r["fixture"]["operations"][2].update(expression={"event": "a"}),
                       lambda r: r["fixture"]["operations"][2].update(kind="external-action"),
                       lambda r: r["caps"].update(checks=True)):
            request = hidden_request(); change(request)
            with self.assertRaises(model.Invalid):
                check(request)
        request = hidden_request()
        request["fixture"]["operations"] += [assign(str(i), "visible", {"int": i}) for i in range(4)]
        with self.assertRaises(model.Invalid):
            check(request)

    def test_suffix_limit_and_dependency_closed_partial_fragments(self):
        request = hidden_request()
        request["leftPrefix"] = request["rightPrefix"] = []
        request["fixture"]["operations"][1]["dependencies"] = ["a"]
        request["suffixes"] = [[], ["a"], ["a", "b"]]
        report = check(request)
        self.assertEqual(report["initialEnabledness"]["left"]["b"]["status"], "blocked")
        self.assertEqual(report["verdict"], "equivalent-for-listed-continuations")
        self.assertEqual(report["checks"][1]["outcomes"]["left"]["pending"], ["b", "c"])
        request["suffixes"] = [[], ["b"]]
        with self.assertRaisesRegex(model.Invalid, "dependency order"):
            check(request)
        request["suffixes"] = [[]] * 721
        with self.assertRaisesRegex(model.Invalid, "suffix count"):
            check(request)

    def test_determinism_no_input_mutation_source_binding_and_public_api(self):
        request = hidden_request(); before = deepcopy(request)
        first = check(request); second = check(request)
        self.assertEqual(model.canonical(first), model.canonical(second))
        self.assertEqual(request, before)
        self.assertIs(check, checker.check)
        self.assertIs(verify, checker.verify)
        self.assertIs(source_bindings, checker.source_bindings)
        request["sourceBindings"]["research/lab/model.py"] = "0" * 64
        with self.assertRaisesRegex(model.Invalid, "source binding"):
            check(request)
        with patch.object(checker, "_read_sources", return_value={}):
            with self.assertRaisesRegex(model.Invalid, "loaded source"):
                source_bindings()

    def test_configuration_bound_includes_unicode_and_all_raw_dimensions(self):
        request = hidden_request()
        fixture = request["fixture"]
        resources = {("\u2603" * 256) + str(i): model.LIMIT for i in range(60)}
        # Names remain within the existing model bound.
        resources = {key[:253] + str(i): value for i, (key, value) in enumerate(resources.items())}
        fixture["state"].update(resources); fixture["versions"].update(dict.fromkeys(resources, 0))
        outcome = model.run(fixture, ["a", "b", "c"])
        self.assertLess(len(model.canonical(outcome)), checker._configuration_bound(fixture))


class ContextualControlsTests(unittest.TestCase):
    def test_omitted_premises_and_event_order(self):
        request = hidden_request()
        request["fixture"]["operations"][1] = assign("b", "visible", {"int": 2})
        request["suffixes"] = [[], ["c"]]
        request["fixture"]["observation"] = {"mode": "projection", "resources": ["visible"]}
        projected = check(request)
        self.assertEqual(projected["verdict"], "equivalent-for-listed-continuations")
        self.assertIn("events", projected["checks"][0]["rawDifferences"])
        request["fixture"]["observation"] = {"mode": "exact"}
        exact = check(request)
        self.assertEqual(exact["verdict"], "divergent")
        self.assertEqual(exact["witness"]["suffix"], [])

    def test_guard_enabledness_and_stale_version_failures_are_inconclusive(self):
        request = hidden_request()
        request["fixture"]["operations"][2]["guard"] = {"op": "eq", "left": {"read": "hidden"}, "right": {"int": 2}}
        report = check(request)
        self.assertEqual(report["verdict"], "inconclusive")
        self.assertEqual(report["initialEnabledness"]["left"]["c"]["status"], "enabled")
        self.assertEqual(report["initialEnabledness"]["right"]["c"]["status"], "blocked")
        self.assertEqual(report["checks"][1]["outcomes"]["right"]["pending"], ["c"])
        request["fixture"]["operations"][2].pop("guard")
        request["fixture"]["operations"][2]["readVersions"] = {"hidden": 0}
        stale = check(request)
        self.assertEqual(stale["verdict"], "inconclusive")
        for side in ("left", "right"):
            self.assertEqual(stale["checks"][1]["outcomes"][side]["reason"], "stale read version")
            self.assertEqual(stale["checks"][1]["outcomes"][side]["versions"]["hidden"], 2)

    def test_return_values_remain_raw_under_projection(self):
        request = hidden_request()
        request["fixture"]["operations"][2] = {"id": "c", "kind": "read", "target": "hidden", "dependencies": [], "readVersions": {}}
        report = check(request)
        self.assertEqual(report["verdict"], "equivalent-for-listed-continuations")
        self.assertEqual(report["checks"][1]["outcomes"]["left"]["results"]["c"], 2)
        self.assertEqual(report["checks"][1]["outcomes"]["right"]["results"]["c"], 1)
        self.assertIn("results", report["checks"][1]["rawDifferences"])

    def test_initial_only_pair_match_does_not_cover_reachable_context(self):
        request = hidden_request()
        request["fixture"]["operations"] = [assign("a", "hidden", {"read": "hidden"}, kind="add"),
                                               assign("b", "hidden", {"read": "hidden"}, kind="multiply"),
                                               assign("c", "hidden", {"int": 2})]
        request["fixture"]["observation"] = {"mode": "projection", "resources": ["hidden"]}
        request["suffixes"] = [[]]
        initial = check(request)
        self.assertEqual(initial["verdict"], "equivalent-for-listed-continuations")
        request["leftPrefix"] = ["c", "a", "b"]
        request["rightPrefix"] = ["c", "b", "a"]
        context = check(request)
        self.assertEqual(context["verdict"], "divergent")
        self.assertEqual(context["checks"][0]["outcomes"]["left"]["state"]["hidden"], 16)
        self.assertEqual(context["checks"][0]["outcomes"]["right"]["state"]["hidden"], 8)

    def test_errors_and_failed_pending_inventory_retain_partial_effects(self):
        request = hidden_request()
        request["fixture"]["operations"][2]["target"] = "missing-resource"
        report = check(request)
        self.assertEqual(report["verdict"], "inconclusive")
        self.assertEqual(report["initialEnabledness"]["left"]["c"]["status"], "error")
        self.assertEqual(report["checks"][1]["outcomes"]["left"]["state"]["hidden"], 2)
        self.assertEqual(report["checks"][1]["outcomes"]["left"]["pending"], ["c"])
        self.assertEqual(len(report["checks"][1]["outcomes"]["left"]["events"]), 2)


class ContextualProofMappingTests(unittest.TestCase):
    def manifest(self):
        return json.loads((ROOT / "examples/contextual-lab/anchored-manifest.json").read_text())

    def test_anchored_relations_and_exclusions(self):
        from scripts.crosscheck_contextual_proof_mapping import crosscheck
        report = crosscheck(self.manifest())
        self.assertEqual(report["status"], "finite-mapping-match")
        self.assertEqual([row["orders"] for row in report["cases"]], [2, 6, 24])
        self.assertEqual([row["adjacentChecks"] for row in report["cases"]], [0, 6, 24])
        self.assertEqual([row["farChecks"] for row in report["cases"]], [0, 0, 24])
        self.assertEqual([row["involutiveChecks"] for row in report["cases"]], [2, 12, 72])
        self.assertEqual([row["distinctChronologicalTraceHashes"] for row in report["cases"]], [2, 6, 24])
        self.assertTrue(all(row["rejected"] for row in report["excluded"]))
        self.assertEqual(len(report["excluded"]), 4)
        self.assertFalse(report["proofAccepted"])
        self.assertFalse(report["executionAuthorization"])

    def test_mapping_oracle_detects_corrupted_implementation(self):
        from scripts import crosscheck_contextual_proof_mapping as mapping
        original = mapping.implementation.replay

        def corrupted(request, order):
            result = original(request, order)
            result["final"] = []
            return result

        with patch.object(mapping.implementation, "replay", corrupted):
            result = mapping.crosscheck(self.manifest())
        self.assertEqual(result["status"], "divergent")
        self.assertIn("flattening", result["cases"][0]["mismatches"])

    def test_mapping_cli_and_determinism(self):
        from scripts.crosscheck_contextual_proof_mapping import canonical, crosscheck
        first = crosscheck(self.manifest()); second = crosscheck(self.manifest())
        self.assertEqual(canonical(first), canonical(second))
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).resolve() / "mapping.json"
            result = subprocess.run([
                sys.executable, "scripts/crosscheck_contextual_proof_mapping.py", "--manifest",
                "examples/contextual-lab/anchored-manifest.json", "--output", str(output)],
                cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(output.read_bytes()), first)


class ContextualCliTests(unittest.TestCase):
    def test_cli_check_verify_paths_and_invalid_parser(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            request, output = base / "request.json", base / "report.json"
            request.write_bytes(model.canonical(hidden_request()))
            args = [sys.executable, "-m", "research.contextual_lab", "check", str(request), "--output", str(output)]
            result = subprocess.run(args, cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(output.read_bytes())["verdict"], "divergent")
            verified = subprocess.run([sys.executable, "-m", "research.contextual_lab", "verify", str(output)], cwd=ROOT, capture_output=True)
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            collision = subprocess.run(args, cwd=ROOT, capture_output=True)
            self.assertEqual(collision.returncode, 1)
            link = base / "link.json"; link.symlink_to(output)
            rejected = subprocess.run(args[:-1] + [str(link)], cwd=ROOT, capture_output=True)
            self.assertEqual(rejected.returncode, 1)
            request.write_text('{"PRIVATE-SENTINEL":1,"PRIVATE-SENTINEL":2}')
            malformed = subprocess.run(args[:-1] + [str(base / "bad-output.json")], cwd=ROOT, capture_output=True)
            self.assertEqual(malformed.returncode, 1)
            self.assertNotIn(b"PRIVATE-SENTINEL", malformed.stdout + malformed.stderr)
            self.assertFalse((base / "bad-output.json").exists())


if __name__ == "__main__":
    unittest.main()
