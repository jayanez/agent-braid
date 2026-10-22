# SPDX-License-Identifier: AGPL-3.0-only
"""Independent finite counts, partial effects, replay tampering and CLI controls."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from research.workload_lab.evidence import explore, verify
from research.workload_lab.model import InvalidWorkload, canonical, validate
from research.workload_lab.__main__ import load_file, main


def fixture():
    return {"model": "effectful-workload-simulation-v1",
            "initial": {"state": {"x": 0}, "versions": {"x": 0}, "aliases": {}},
            "operations": [{"id": name, "kind": "add-constant", "resource": "x",
                            "amount": amount, "dependencies": [], "outcomes": ["success"],
                            "effects": {"complete": True, "reads": ["x"],
                                        "writes": ["x"], "emits": []}}
                           for name, amount in (("a", 1), ("b", 2))],
            "observation": {"mode": "selected-values", "resources": ["x"]},
            "caps": {"paths": 20000, "steps": 120000, "events": 240000}}


class WorkloadExplorationTests(unittest.TestCase):
    def test_complete_and_truncated_domains(self):
        report = explore(fixture())
        self.assertEqual(report["coverage"], {
            "schedules": 2, "assignedPaths": 2, "attemptedPaths": 2,
            "completedPaths": 2, "partialPaths": 0, "unattemptedPaths": 0,
            "unresolvedUpperBound": 0, "steps": 4, "events": 0,
            "complete": True, "capReason": None})
        self.assertEqual([path["order"] for path in report["paths"]], [["a", "b"], ["b", "a"]])
        self.assertEqual([path["configuration"]["state"]["x"] for path in report["paths"]], [3, 3])
        self.assertEqual(report["comparison"], {"verdict": "terminal-projection-match",
                                                "mismatches": ["results"]})
        self.assertFalse(report["executionAuthorization"])
        for cap, amount, attempted, completed, steps in (
                ("paths", 0, 0, 0, 0), ("paths", 1, 1, 1, 2),
                ("steps", 0, 1, 0, 0), ("steps", 1, 1, 0, 1),
                ("steps", 3, 2, 1, 3)):
            with self.subTest(cap=cap, amount=amount):
                request = fixture(); request["caps"][cap] = amount
                result = explore(request)
                coverage = result["coverage"]
                self.assertFalse(coverage["complete"])
                self.assertEqual((coverage["attemptedPaths"], coverage["completedPaths"],
                                  coverage["steps"]), (attempted, completed, steps))
                self.assertEqual(coverage["partialPaths"], attempted - completed)
                self.assertEqual(coverage["unattemptedPaths"], 2 - attempted)
                self.assertEqual(coverage["unresolvedUpperBound"], 2 - completed)
                self.assertEqual(result["comparison"]["verdict"], "inconclusive")

    def test_exact_boundary_is_complete_and_zero_events_allows_nonemitters(self):
        request = fixture(); request["caps"] = {"paths": 2, "steps": 4, "events": 0}
        report = explore(request)
        self.assertTrue(report["coverage"]["complete"])
        self.assertIsNone(report["coverage"]["capReason"])
        request["observation"] = {"mode": "exact"}
        report = explore(request)
        self.assertEqual(report["comparison"]["verdict"], "divergent")

    def test_dependency_and_branch_product_counts_are_independent(self):
        request = fixture()
        request["operations"][1]["dependencies"] = ["a"]
        request["operations"][0]["outcomes"] = ["success", "error"]
        request["operations"][1]["outcomes"] = ["success", "error"]
        report = explore(request)
        self.assertEqual(report["coverage"]["schedules"], 1)
        self.assertEqual(report["coverage"]["assignedPaths"], 4)
        self.assertEqual(report["coverage"]["completedPaths"], 4)
        self.assertEqual(report["coverage"]["steps"], 6)
        self.assertEqual([p["branches"] for p in report["paths"]],
                         [["success", "success"], ["success", "error"],
                          ["error", "success"], ["error", "error"]])
        self.assertEqual(report["paths"][2]["configuration"]["pending"], ["b"])

    def test_six_operations_have_720_orders_without_unbounded_exploration(self):
        request = fixture()
        prototype = request["operations"][0]
        request["operations"] = [{**deepcopy(prototype), "id": str(i)} for i in range(6)]
        request["caps"]["paths"] = 0
        report = explore(request)
        self.assertEqual(report["coverage"]["schedules"], 720)
        self.assertEqual(report["coverage"]["assignedPaths"], 720)
        self.assertEqual(report["paths"], [])


    def test_byte_budget_stops_before_retaining_oversized_payload(self):
        request = fixture()
        step_bytes = len(canonical(explore(request)["paths"][0]["steps"][0])) + 1
        with mock.patch("research.workload_lab.explore.PATH_BYTES", 0):
            empty = explore(request)
        self.assertEqual((empty["coverage"]["attemptedPaths"], empty["coverage"]["capReason"]),
                         (0, "bytes"))
        with mock.patch("research.workload_lab.explore.PATH_BYTES", step_bytes):
            report = explore(request)
            self.assertEqual(verify(json.loads(canonical(report)))["status"], "verified")
        coverage = report["coverage"]
        self.assertEqual((coverage["attemptedPaths"], coverage["completedPaths"], coverage["steps"],
                          coverage["capReason"], coverage["complete"]), (1, 0, 1, "bytes", False))
        partial = report["paths"][0]
        self.assertEqual(len(partial["steps"]), 1)
        self.assertEqual((partial["configuration"]["outcome"], partial["configuration"]["reason"],
                          partial["configuration"]["pending"]), ("cap-exhausted", "bytes", ["b"]))
        self.assertLessEqual(len(canonical(partial["steps"])), step_bytes + 1)
        self.assertEqual(report["comparison"]["verdict"], "inconclusive")
        self.assertFalse(report["executionAuthorization"])


class WorkloadObservationTests(unittest.TestCase):
    def event_fixture(self):
        request = fixture()
        request["operations"] = [{"id": "a", "kind": "external-action", "resource": "x",
                                  "event": "notice", "dependencies": [],
                                  "outcomes": ["success", "send-then-error"]},
                                 {**request["operations"][1], "dependencies": ["a"]}]
        return request

    def test_send_then_error_retains_effect(self):
        report = explore(self.event_fixture())
        self.assertEqual(report["coverage"]["completedPaths"], 2)
        failed = report["paths"][1]["configuration"]
        self.assertEqual(failed["outcome"], "error")
        self.assertEqual(failed["state"], {"x": 0})
        self.assertEqual(failed["pending"], ["b"])
        self.assertEqual(failed["events"], [{"operationId": "a", "resource": "x",
                                             "name": "notice", "value": 0,
                                             "idempotencyKey": None}])
        self.assertEqual(report["comparison"]["verdict"], "inconclusive")
        self.assertEqual(report["traceSafety"]["partialFailurePaths"], [1])
        self.assertEqual(report["traceSafety"]["status"], "witness")

    def test_event_cap_retains_partial_path_without_emitting(self):
        request = self.event_fixture(); request["caps"]["events"] = 0
        report = explore(request)
        self.assertEqual(report["coverage"]["partialPaths"], 1)
        self.assertEqual(report["coverage"]["steps"], 0)
        self.assertEqual(report["coverage"]["events"], 0)
        config = report["paths"][0]["configuration"]
        self.assertEqual(config["events"], [])
        self.assertEqual(config["pending"], ["a", "b"])
        self.assertEqual(config["outcome"], "cap-exhausted")

    def test_projection_retains_successful_event_order_witness(self):
        request = self.event_fixture()
        request["operations"] = [{**request["operations"][0], "outcomes": ["success"]},
                                 {**request["operations"][0], "id": "b", "outcomes": ["success"]}]
        report = explore(request)
        self.assertEqual(report["comparison"]["verdict"], "terminal-projection-match")
        self.assertIn("events", report["comparison"]["mismatches"])
        self.assertTrue(report["traceSafety"]["eventOrderMismatch"])
        self.assertEqual(report["traceSafety"]["duplicateEventPaths"], [0, 1])
        self.assertEqual(report["traceSafety"]["status"], "witness")

    def test_event_budget_counts_actual_emissions_and_does_not_mask_stale_guards(self):
        request = self.event_fixture()
        request["operations"] = [{**request["operations"][0], "outcomes": ["success"],
                                  "idempotencyKey": "one"},
                                 {**request["operations"][0], "id": "b", "outcomes": ["success"],
                                  "idempotencyKey": "one"}]
        request["caps"]["events"] = 2
        report = explore(request)
        self.assertTrue(report["coverage"]["complete"])
        self.assertEqual(report["coverage"]["events"], 2)
        for path in report["paths"]:
            self.assertEqual(len(path["configuration"]["events"]), 1)
            self.assertEqual(sorted(path["configuration"]["results"].values()), [0, 1])
        request["caps"]["events"] = 1
        report = explore(request)
        self.assertEqual(report["coverage"]["completedPaths"], 1)
        self.assertEqual(report["coverage"]["partialPaths"], 1)
        self.assertEqual(report["coverage"]["events"], 1)
        request = self.event_fixture()
        request["operations"][0]["requiredVersion"] = 1
        request["caps"]["events"] = 0
        report = explore(request)
        self.assertTrue(report["coverage"]["complete"])
        self.assertEqual(report["paths"][0]["configuration"]["outcome"], "blocked")
        self.assertEqual(report["coverage"]["events"], 0)


class WorkloadEvidenceTests(unittest.TestCase):
    def test_report_schema_is_strict_but_never_replaces_replay(self):
        from jsonschema import Draft202012Validator
        schema_path = Path(__file__).resolve().parents[1] / "specs/024-effectful-workload-lab/contracts/report.schema.json"
        schema = json.loads(schema_path.read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        report = explore(fixture())
        validator.validate(report)
        extra = deepcopy(report); extra["safeParallelism"] = True
        self.assertFalse(validator.is_valid(extra))
        changed = deepcopy(report); changed["paths"][0]["configuration"]["state"]["x"] = 99
        validator.validate(changed)
        self.assertEqual(verify(changed)["status"], "rejected")
        capped = fixture(); capped["caps"]["steps"] = 0
        validator.validate(explore(capped))
        with mock.patch("research.workload_lab.explore.PATH_BYTES", 0):
            validator.validate(explore(fixture()))

    def test_tamper_coverage_and_cost_accounting(self):
        original = explore(fixture())
        self.assertEqual(verify(original)["status"], "verified")
        mutations = [lambda r: r["paths"].pop(),
                     lambda r: r["coverage"].update(steps=0),
                     lambda r: r["paths"][0]["branches"].__setitem__(0, "error"),
                     lambda r: r["paths"][0]["steps"][0]["after"]["state"].update(x=99),
                     lambda r: r["request"]["observation"].update(resources=[]),
                     lambda r: r["traceSafety"].update(status="safe"),
                     lambda r: r["sourceBindings"].clear(),
                     lambda r: r.update(executionAuthorization=True),
                     lambda r: r.update(proofAccepted=True)]
        for mutate in mutations:
            report = deepcopy(original); mutate(report)
            with self.subTest(mutation=mutate):
                self.assertEqual(verify(report)["status"], "rejected")
                self.assertFalse(verify(report)["executionAuthorization"])
        self.assertEqual(explore(fixture()), original)
        self.assertEqual(fixture()["initial"]["state"], {"x": 0})

    def test_invalid_executable_fields_never_reach_exploration(self):
        request = fixture(); request["operations"][0]["callback"] = lambda: self.fail("executed")
        with self.assertRaises(InvalidWorkload):
            validate(request)


class WorkloadCliTests(unittest.TestCase):
    def invoke(self, args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(args)
        return code, json.loads(output.getvalue())

    @staticmethod
    def rejected(reason):
        return {"status": "rejected", "reason": reason, "executionAuthorization": False}

    def test_exclusive_cli_roundtrip_and_verification_is_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); source = root / "request.json"; report = root / "report.json"
            source.write_bytes(canonical(fixture()))
            self.assertEqual(self.invoke(["explore", str(source), "--output", str(report)])[0], 0)
            before = report.read_bytes()
            self.assertEqual(self.invoke(["verify", str(report)])[1]["status"], "verified")
            self.assertEqual(report.read_bytes(), before)
            self.assertEqual(self.invoke(["explore", str(source), "--output", str(report)]),
                             (1, self.rejected("output-exists")))
            self.assertEqual(report.read_bytes(), before)
            self.assertEqual(self.invoke(["verify", str(report), "--output", str(root / "other")]),
                             (1, self.rejected("verify-is-read-only")))
            self.assertFalse((root / "other").exists())
            self.assertEqual(self.invoke(["explore", str(source), "--output", str(source)]),
                             (1, self.rejected("output-is-input")))
            self.assertEqual(self.invoke(["explore", str(source)]), (1, self.rejected("output-required")))
            self.assertEqual(source.read_bytes(), canonical(fixture()))
            self.assertEqual(os.stat(report).st_mode & 0o777, 0o600)

    def test_nonsymlink_regular_input_and_output_ancestors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve(); source = root / "request.json"
            source.write_bytes(canonical(fixture()))
            link = root / "linked.json"; link.symlink_to(source)
            self.assertEqual(self.invoke(["explore", str(link), "--output", str(root / "out")]),
                             (1, self.rejected("symlink-path")))
            parent_link = root / "alias"; parent_link.symlink_to(root, target_is_directory=True)
            self.assertEqual(self.invoke(["explore", str(source), "--output", str(parent_link / "out")]),
                             (1, self.rejected("symlink-path")))
            self.assertFalse((root / "out").exists())
            self.assertEqual(self.invoke(["explore", str(root / "missing.json"), "--output", str(root / "out")]),
                             (1, self.rejected("unavailable-path")))
            fifo = root / "pipe"; os.mkfifo(fifo)
            self.assertEqual(self.invoke(["verify", str(fifo)]), (1, self.rejected("not-regular-file")))
            with self.assertRaises(InvalidWorkload) as refused:
                load_file(source, limit=1)
            self.assertEqual(refused.exception.reason, "too-large")
            for name, data, reason in (("bad.json", b"{", "invalid-json"),
                                       ("utf16.json", canonical(fixture()).decode().encode("utf-16"), "invalid-json"),
                                       ("unknown.json", canonical({**fixture(), "extra": 1}), "invalid-request")):
                (root / name).write_bytes(data)
                self.assertEqual(self.invoke(["explore", str(root / name), "--output", str(root / (name + ".out"))]),
                                 (1, self.rejected(reason)))
                self.assertFalse((root / (name + ".out")).exists())


if __name__ == "__main__":
    unittest.main()
