# SPDX-License-Identifier: AGPL-3.0-only
"""Full-boundary diagnostic accounting, safety errors and explicit capture gates."""
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_braid.utility_accounting import PHASES, UtilityAccounting
from agent_braid.utility_fixtures import build_fixture, validate_prepared_manifest
from scripts import measure_m4_utility as utility


class UtilityHarnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "source.git"
        self.source.mkdir()
        (self.source / "owned").write_bytes(b"immutable")
        request = {"request": "immutable"}
        replay = {"replay": "immutable"}
        self.fixture = {"blockId": "independent-2-1024", "repository": str(self.source),
                        "runtimeRequest": request, "replayRequest": replay,
                        "expectedFinalTree": "expected-tree"}
        for kind, value in (("runtime", request), ("replay", replay)):
            raw = json.dumps(value).encode()
            path = self.root / (kind + ".json")
            path.write_bytes(raw)
            self.fixture[kind + "RequestPath"] = str(path)
            self.fixture[kind + "RequestSha256"] = hashlib.sha256(raw).hexdigest()
        self.calls = []
        self.destinations = []

    def accounting(self, **kwargs):
        tick = iter(range(1000))
        return UtilityAccounting(monotonic=lambda: next(tick) / 1000,
                                 parent_cpu=lambda: 0.0, child_cpu=lambda: (0.0, 0.0),
                                 lifetime_rss=lambda: 0, **kwargs)

    def pipeline(self, *, execute_error=None, tree="expected-tree", mutate_source=False):
        stack = ExitStack()
        self.addCleanup(stack.close)

        def replay(request):
            self.calls.append("replay")
            self.assertEqual(request, self.fixture["replayRequest"])
            return {"evidence": True}, {"executionAuthorization": False}

        def prepare(request, destination, **kwargs):
            self.calls.append("preparation")
            self.assertEqual(request, self.fixture["runtimeRequest"])
            self.assertEqual(kwargs["advisory_plan"]["executionAuthorization"], False)
            self.destinations.append(Path(destination).parent)
            return {"planDigest": "bound-plan", "runtimeManifest": {"owned": True}}

        def grant(plan, store, **kwargs):
            self.calls.append("grant")
            self.assertEqual(kwargs["acknowledge"], plan["planDigest"])
            return {"grantId": "purpose-bound"}

        def execute(plan, store, grant_id, **kwargs):
            self.calls.append("execution")
            self.assertEqual(grant_id, "purpose-bound")
            if mutate_source:
                (self.source / "owned").write_bytes(b"changed")
            if execute_error:
                raise execute_error
            return {"runtime": {"status": "completed"}}

        def verify(request, destination):
            self.calls.append("independent_verification")
            return {"status": "verified-completed", "resultTree": tree}

        stack.enter_context(patch.object(utility.git_replay, "produce", side_effect=replay))
        stack.enter_context(patch.object(utility.runtime_policy, "prepare_policy_run", side_effect=prepare))
        stack.enter_context(patch.object(utility.runtime_policy, "issue_operator_grant", side_effect=grant))
        stack.enter_context(patch.object(utility.runtime_policy, "execute_policy_run", side_effect=execute))
        stack.enter_context(patch.object(utility.git_runtime, "verify_run", side_effect=verify))

    def test_all_phases_include_grant_verification_cleanup_and_residual(self):
        self.pipeline()
        result = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting)
        observation = result["accounting"]
        self.assertEqual(result["operational"]["status"], "completed")
        self.assertIs(observation["complete"], True)
        self.assertEqual([p["name"] for p in observation["phases"]], list(PHASES))
        self.assertEqual(observation["outer"]["wallNs"],
                         sum(p["wallNs"] for p in observation["phases"]) + observation["residualWallNs"])
        self.assertGreater(observation["residualWallNs"], 0)
        self.assertEqual(self.calls, ["replay", "preparation", "grant", "execution", "independent_verification"])
        self.assertFalse(self.destinations[0].exists())
        self.assertIsNone(result["operational"]["workerOverlap"]["peakIntervals"])
        self.assertEqual(json.loads(result["operationalEncoded"]), result["operational"])
        self.assertEqual(result["operationalEncodedBytes"], len(result["operationalEncoded"].encode()))
        self.assertEqual(result["observerFinalization"]["startWallNs"], observation["outer"]["endWallNs"])

    def test_request_drift_refuses_before_any_runtime_boundary(self):
        self.pipeline()
        Path(self.fixture["runtimeRequestPath"]).write_bytes(b"tampered")
        result = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting)
        self.assertEqual(result["operational"]["status"], "no-go")
        self.assertEqual(self.calls, [])
        self.assertFalse(result["accounting"]["complete"])
        self.assertEqual((self.source / "owned").read_bytes(), b"immutable")

    def test_preparation_source_drift_stops_before_runtime(self):
        self.pipeline()
        self.fixture["preparedSourceFingerprint"] = utility.source_fingerprint(self.source)
        (self.source / "owned").write_bytes(b"changed-before-input")
        result = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting)
        self.assertEqual(result["status"], "no-go")
        self.assertEqual(self.calls, [])

    def test_existing_caller_scope_is_preserved(self):
        self.pipeline()
        existing = self.root / "existing"
        existing.mkdir()
        marker = existing / "keep"
        marker.write_bytes(b"owned-by-caller")
        result = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting,
                                       treatment_root=existing)
        self.assertNotEqual(result["status"], "completed")
        self.assertEqual(self.calls, [])
        self.assertEqual(marker.read_bytes(), b"owned-by-caller")

    def test_invalid_or_overlapping_leaves_refuse_before_dispatch(self):
        self.pipeline()
        for run_leaf, grant_leaf in (("../run", "grants"), ("run", "run"), ("run", "/grants")):
            with self.subTest(run_leaf=run_leaf, grant_leaf=grant_leaf):
                with self.assertRaises(ValueError):
                    utility.run_treatment(self.fixture, "serial", run_leaf=run_leaf,
                                          grant_leaf=grant_leaf)
        self.assertEqual(self.calls, [])

    def test_wrong_tree_is_no_go_and_owned_destination_is_cleaned(self):
        self.pipeline(tree="wrong-tree")
        result = utility.run_treatment(self.fixture, "parallel", accounting_factory=self.accounting)
        self.assertEqual(result["operational"]["status"], "no-go")
        self.assertEqual(result["operational"]["error"]["type"], "UnsafeDiagnostic")
        self.assertFalse(self.destinations[0].exists())

    def test_failed_execution_is_retained_and_never_completed_by_cleanup(self):
        self.pipeline(execute_error=RuntimeError("worker timeout"))
        result = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting)
        self.assertEqual(result["operational"]["status"], "inconclusive")
        self.assertEqual(result["operational"]["error"]["message"], "worker timeout")
        self.assertFalse(result["accounting"]["complete"])
        self.assertNotIn("independent_verification", self.calls)
        self.assertFalse(self.destinations[0].exists())

    def test_source_mutation_on_success_or_failure_is_no_go(self):
        for failure in (None, RuntimeError("dispatch failed")):
            with self.subTest(failure=failure):
                (self.source / "owned").write_bytes(b"immutable")
                self.pipeline(execute_error=failure, mutate_source=True)
                result = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting)
                self.assertEqual(result["operational"]["status"], "no-go")
                self.assertFalse(self.destinations[-1].exists())

    def test_fresh_private_destinations_for_each_treatment(self):
        self.pipeline()
        first = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting)
        second = utility.run_treatment(self.fixture, "parallel", accounting_factory=self.accounting)
        self.assertEqual([first["operational"]["status"], second["operational"]["status"]],
                         ["completed", "completed"])
        self.assertNotEqual(self.destinations[0], self.destinations[1])

    def test_supplemental_overlap_uses_union_and_not_sum(self):
        result = utility.worker_overlap({"wallNs": 10, "observedPeakWorkerIntervals": 2,
            "workers": [{"startedNs": 1, "finishedNs": 5}, {"startedNs": 3, "finishedNs": 8}]})
        self.assertEqual(result["unionNs"], 7)
        self.assertEqual(result["peakIntervals"], 2)
        with self.assertRaises(utility.UnsafeDiagnostic):
            utility.worker_overlap({"wallNs": 10, "observedPeakWorkerIntervals": 1,
                "workers": [{"startedNs": 1, "finishedNs": 11}]})

    def test_observer_output_is_fresh_and_does_not_modify_operational_wall(self):
        self.pipeline()
        result = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting)
        wall = result["accounting"]["outer"]["wallNs"]
        output = self.root / "result.json"
        observer = utility._write_new(output, result)
        self.assertEqual(json.loads(output.read_bytes())["accounting"]["outer"]["wallNs"], wall)
        self.assertEqual(observer["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        with self.assertRaises(FileExistsError):
            utility._write_new(output, {"replacement": True})

    def test_cli_help_and_registered_flag_refusal(self):
        script = str(utility.ROOT / "scripts/measure_m4_utility.py")
        help_result = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--diagnostic-block", help_result.stdout)
        output = self.root / "registered.json"
        result = subprocess.run([sys.executable, script, "--output", str(output), "--registered"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(output.exists())

    def test_excluded_diagnostic_is_not_success_or_an_executed_pair(self):
        output = self.root / "excluded.json"
        with patch.object(utility, "_git", side_effect=lambda *args: "" if args[0] == "status" else "candidate"), \
                patch.object(utility, "run_treatment") as treatment:
            code = utility.run(utility.DEFAULT_MANIFEST, output,
                               diagnostic_block="independent-2-1048576")
        self.assertEqual(code, 2)
        record = json.loads(output.read_bytes())
        self.assertEqual(record["status"], "excluded-not-run")
        self.assertEqual(record["diagnosticPairs"], [])
        self.assertEqual(len(record["inventory"]), 9)
        self.assertIs(record["registeredMeasurementExecuted"], False)
        treatment.assert_not_called()

    def test_cleanup_failure_preserves_encoded_report_and_final_status(self):
        self.pipeline()
        actual_cleanup = tempfile.TemporaryDirectory.cleanup

        def failed_cleanup(value):
            actual_cleanup(value)
            raise OSError("owned cleanup could not finish")

        with patch.object(tempfile.TemporaryDirectory, "cleanup", failed_cleanup):
            result = utility.run_treatment(self.fixture, "serial", accounting_factory=self.accounting)
        self.assertEqual(result["operational"]["status"], "completed")
        self.assertEqual(json.loads(result["operationalEncoded"]), result["operational"])
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["cleanupError"]["message"], "owned cleanup could not finish")
        self.assertFalse(result["accounting"]["complete"])


class UtilityRealBoundaryTests(unittest.TestCase):
    def test_owned_pinned_fixture_runs_both_full_verified_paths(self):
        manifest = validate_prepared_manifest(utility.DEFAULT_MANIFEST.read_bytes())
        with tempfile.TemporaryDirectory() as directory:
            fixture = build_fixture(manifest["blocks"][0], Path(directory) / "fixture")
            before = utility.source_fingerprint(Path(fixture["repository"]))
            for mode in ("serial", "parallel"):
                with self.subTest(mode=mode):
                    runtime_root = Path(directory) / ("runtime-" + mode)
                    fixture["preparedSourceFingerprint"] = before
                    sample = utility.run_treatment(fixture, mode, treatment_root=runtime_root,
                                                   run_leaf="run", grant_leaf="grants")
                    self.assertEqual(Path(sample["operational"]["independentVerification"]["runDirectory"]),
                                     (runtime_root / "run").resolve())
                    self.assertFalse(runtime_root.exists())
                    self.assertEqual(sample["operational"]["status"], "completed", sample)
                    self.assertEqual(sample["operational"]["resultTree"], fixture["expectedFinalTree"])
                    self.assertTrue(sample["accounting"]["complete"])
                    self.assertGreater(sample["accounting"]["gitCommands"], 0)
                    self.assertGreater(sample["accounting"]["acceptedBudgetOutputBytes"], 0)
                    self.assertEqual(before, utility.source_fingerprint(Path(fixture["repository"])))


if __name__ == "__main__":
    unittest.main()
