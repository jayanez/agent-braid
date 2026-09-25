# SPDX-License-Identifier: AGPL-3.0-only

from copy import deepcopy
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from agent_braid import git_counterexamples
from agent_braid.git_counterexamples import (
    _base_result,
    _run_supervised,
    _run_worker,
    _terminate_process_group,
    reduce_counterexample,
)
from agent_braid.git_replay import produce, _bundle_digest


class GitCounterexampleRealGitTests(unittest.TestCase):
    """End-to-end scenarios reachable with a real, small repository."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git(self.repo, "init", "-q", "-b", "main")
        self.git(self.repo, "config", "user.name", "Git counterexample test")
        self.git(self.repo, "config", "user.email", "test@example.invalid")
        (self.repo / "a.txt").write_text("base a\n", encoding="utf-8")
        (self.repo / "b.txt").write_text("base b\n", encoding="utf-8")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-qm", "base")
        self.base = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.left = self.commit_change("left", "a.txt", "left\n")
        self.right = self.commit_change("right", "b.txt", "right\n")

    @staticmethod
    def text(value):
        return value.decode().strip()

    @staticmethod
    def git(repo, *args, input_bytes=None):
        return subprocess.run(
            ["git", "-C", str(repo), *args], input=input_bytes,
            capture_output=True, check=True,
        ).stdout

    def commit_change(self, branch, path, content):
        self.git(self.repo, "checkout", "-qb", branch, self.base)
        (self.repo / path).write_text(content, encoding="utf-8")
        self.git(self.repo, "add", "--", path)
        self.git(self.repo, "commit", "-qm", branch)
        commit = self.text(self.git(self.repo, "rev-parse", "HEAD"))
        self.git(self.repo, "checkout", "-q", "main")
        return commit

    def request(self):
        return {
            "gitAnalysisRequestVersion": "0.1.0-alpha",
            "repository": str(self.repo),
            "baseRevision": self.base,
            "operations": [
                {"instanceId": "op-0", "attemptId": "a-0",
                 "source": {"kind": "commit", "revision": self.left},
                 "dependencies": [], "uncertainPaths": []},
                {"instanceId": "op-1", "attemptId": "a-1",
                 "source": {"kind": "commit", "revision": self.right},
                 "dependencies": [], "uncertainPaths": []},
            ],
        }

    def test_rejects_tampered_evidence_end_to_end(self):
        bundle, _plan = produce(self.request())
        tampered = deepcopy(bundle)
        tampered["operations"][0]["patchDigest"] = "sha256:" + "0" * 64
        tampered["evidenceDigest"] = _bundle_digest(tampered)
        result = reduce_counterexample(tampered, str(self.repo))
        self.assertEqual(result["status"], "rejected")
        self.assertIsNone(result["selectedOperationIds"])
        self.assertIsNone(result["witnessEvidence"])
        self.assertFalse(result["executionAuthorization"])
        self.assertEqual(result["originalEvidenceDigest"], tampered["evidenceDigest"])

    def test_rejects_verified_but_not_divergent_evidence_end_to_end(self):
        bundle, _plan = produce(self.request())
        self.assertEqual(bundle["result"], "equivalent-observed")
        result = reduce_counterexample(bundle, str(self.repo))
        self.assertEqual(result["status"], "rejected")
        self.assertIn("not eligible", result["reason"])

    def test_rejects_missing_source_git_objects_end_to_end(self):
        bundle, _plan = produce(self.request())
        empty = self.root / "empty"
        empty.mkdir()
        self.git(empty, "init", "-q", "-b", "main")
        self.git(empty, "config", "user.name", "t")
        self.git(empty, "config", "user.email", "t@example.invalid")
        (empty / "x.txt").write_text("x\n", encoding="utf-8")
        self.git(empty, "add", ".")
        self.git(empty, "commit", "-qm", "x")
        result = reduce_counterexample(bundle, str(empty))
        self.assertIn(result["status"], {"rejected", "unverified", "inconclusive"})
        self.assertIsNone(result["selectedOperationIds"])

    def test_rejects_garbage_evidence_without_crashing(self):
        for evidence in (None, "not-a-bundle", 42, {"partial": True}):
            with self.subTest(evidence=evidence):
                result = reduce_counterexample(evidence, str(self.repo))
                self.assertEqual(result["status"], "rejected")
                self.assertIsNone(result["selectedOperationIds"])

    def test_rejects_invalid_repository(self):
        bundle, _plan = produce(self.request())
        for repository in (None, "", "   ", 5):
            with self.subTest(repository=repository):
                result = reduce_counterexample(bundle, repository)
                self.assertEqual(result["status"], "rejected")

    def test_supervisor_kills_and_awaits_a_real_timeout(self):
        with mock.patch.object(git_counterexamples, "DEADLINE_SECONDS", 0.01):
            bundle, _plan = produce(self.request())
            started = time.monotonic()
            result = reduce_counterexample(bundle, str(self.repo))
            elapsed = time.monotonic() - started
        self.assertEqual(result["status"], "inconclusive")
        self.assertIn("deadline", result["reason"])
        self.assertIn("terminated", result["reason"])
        # The supervisor's own grace window bounds how long the kill+wait can take.
        self.assertLess(elapsed, 0.01 + git_counterexamples.SUPERVISOR_GRACE_SECONDS + 10)


class GitCounterexampleSupervisorUnitTests(unittest.TestCase):
    """Directly exercise the process-group supervisor with synthetic commands."""

    def test_fast_command_passes_through_without_timeout(self):
        command = ["python3", "-c", "import sys; sys.stdout.write(sys.stdin.read())"]
        outcome = _run_supervised(command, b"hello", deadline_seconds=10)
        self.assertTrue(outcome["started"])
        self.assertFalse(outcome["timed_out"])
        self.assertEqual(outcome["returncode"], 0)
        self.assertEqual(outcome["stdout"], b"hello")

    def test_slow_command_is_killed_and_reaped_within_the_deadline(self):
        command = ["python3", "-c", "import time; time.sleep(30)"]
        started = time.monotonic()
        outcome = _run_supervised(command, b"", deadline_seconds=0.2)
        elapsed = time.monotonic() - started
        self.assertTrue(outcome["timed_out"])
        self.assertLess(elapsed, 15)

    def test_exited_worker_with_pipe_holding_child_is_killed(self):
        command = ["python3", "-c", (
            "import subprocess,sys; "
            "subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])"
        )]
        started = time.monotonic()
        outcome = _run_supervised(command, b"", deadline_seconds=0.2)
        self.assertTrue(outcome["timed_out"])
        self.assertLess(time.monotonic() - started, 15)

    def test_timeout_kills_git_style_child_in_its_own_process_group(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "survived"
            child_code = (
                "import time,pathlib; time.sleep(1); "
                f"pathlib.Path({str(marker)!r}).write_text('survived')"
            )
            worker_code = (
                "import subprocess,time; "
                f"child=subprocess.Popen(['python3','-c',{child_code!r}], "
                "start_new_session=True); print(child.pid,flush=True); time.sleep(30)"
            )
            outcome = _run_supervised(["python3", "-c", worker_code], b"", 0.2)
            self.assertTrue(outcome["timed_out"])
            child_pid = int(outcome["stdout"].strip())
            try:
                time.sleep(1.2)
                self.assertFalse(marker.exists(), "child in a separate Git-style group survived")
            finally:
                try:
                    os.killpg(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_exited_worker_cannot_orphan_registered_git_child_group(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "survived"
            child_code = (
                "import time,pathlib; time.sleep(1); "
                f"pathlib.Path({str(marker)!r}).write_text('survived')"
            )
            worker_code = (
                "import subprocess,os; "
                "from agent_braid.git_counterexamples import _process_identity; "
                f"child=subprocess.Popen(['python3','-c',{child_code!r}], "
                "start_new_session=True); "
                "f=open(os.environ['AGENT_BRAID_REDUCER_CHILD_REGISTRY'],'a'); "
                "f.write(str(child.pid)+' '+_process_identity(child.pid)+'\\n'); "
                "f.close(); print(child.pid,flush=True)"
            )
            outcome = _run_supervised(["python3", "-c", worker_code], b"", 0.6)
            self.assertTrue(outcome["timed_out"])
            child_pid = int(outcome["stdout"].strip())
            try:
                time.sleep(1.2)
                self.assertFalse(marker.exists(), "orphaned Git-style child survived")
            finally:
                try:
                    os.killpg(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_stale_child_pid_identity_cannot_target_unrelated_session(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = Path(directory) / "child-pids"
            child = subprocess.Popen(["python3", "-c", "import time; time.sleep(5)"],
                                     start_new_session=True)
            try:
                registry.write_text(f"{child.pid} stale-birth-token\n")
                worker = subprocess.Popen(["python3", "-c", "pass"],
                                          start_new_session=True)
                worker.wait()
                _terminate_process_group(worker, registry)
                self.assertIsNone(child.poll(), "a stale registry entry killed another session")
            finally:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()

    def test_worker_does_not_inherit_unrelated_environment_values(self):
        command = ["python3", "-c", "import os; print(os.getenv('TEST_SECRET', 'absent'))"]
        with mock.patch.dict(os.environ, {"TEST_SECRET": "not-sent"}):
            outcome = _run_supervised(command, b"", deadline_seconds=5)
        self.assertEqual(outcome["stdout"].strip(), b"absent")

    def test_unstartable_command_is_reported_without_raising(self):
        outcome = _run_supervised(["agent-braid-definitely-not-a-real-binary"], b"", deadline_seconds=5)
        self.assertFalse(outcome["started"])

    def test_terminate_process_group_is_idempotent_on_a_finished_process(self):
        process = subprocess.Popen(["python3", "-c", "pass"], start_new_session=(os.name == "posix"))
        process.wait()
        _terminate_process_group(process)  # must not raise for an already-finished process


class GitCounterexampleReductionAlgorithmTests(unittest.TestCase):
    """Deterministic tests of the search algorithm against a controlled fake backend.

    A real all-complete divergent fixture was not found in bounded local probes.
    Positive reduction and minimality paths therefore use a deterministic fake
    ``git_replay.verify``/``produce`` backend. The real-Git tests cover rejection
    and timeout paths; these unit tests do not establish a real divergent witness.
    """

    @staticmethod
    def operation(instance_id, dependencies=()):
        return {
            "instanceId": instance_id,
            "attemptId": f"attempt-{instance_id}",
            "sourceCommit": "a" * 40,
            "dependencies": sorted(dependencies),
            "uncertainPaths": [],
            "patchDigest": "sha256:" + "1" * 64,
            "eligible": True,
            "ineligibleReasons": [],
        }

    def divergent_bundle(self, operation_ids, dependencies=None):
        dependencies = dependencies or {}
        return {
            "gitReplayEvidenceVersion": "0.1.0-alpha",
            "evidenceDigest": "sha256:" + "2" * 64,
            "repositoryId": "sha256:" + "3" * 64,
            "baseCommit": "b" * 40,
            "baseTree": "c" * 40,
            "operations": [
                self.operation(identifier, dependencies.get(identifier, ()))
                for identifier in operation_ids
            ],
            "analysisDigest": "sha256:" + "4" * 64,
            "provenanceDigest": "sha256:" + "5" * 64,
            "observationContract": "tracked-tree-v1",
            "executionContract": "isolated-index-patch-v1",
            "schedules": [],
            "result": "divergent",
            "limits": [],
            "executionAuthorization": False,
        }

    def fake_produce(self, divergent_subsets):
        """Build a produce() stand-in: divergent for the named ID sets, else equivalent."""

        def _produce(request):
            ids = tuple(sorted(op["instanceId"] for op in request["operations"]))
            result = "divergent" if frozenset(ids) in divergent_subsets else "equivalent-observed"
            bundle = self.divergent_bundle(ids)
            bundle["result"] = result
            bundle["evidenceDigest"] = "sha256:" + ("".join(ids) + "9" * 64)[:64]
            return bundle, {"mode": "manual-review"}

        return _produce

    def run_worker_with_fake_backend(self, bundle, divergent_subsets=frozenset(),
                                      deadline_seconds=120.0, max_attempts=10):
        with mock.patch.object(git_counterexamples.git_replay, "verify",
                                return_value={"status": "verified"}), \
             mock.patch.object(git_counterexamples.git_replay, "produce",
                                side_effect=self.fake_produce(divergent_subsets)):
            return _run_worker(
                {"evidence": bundle, "repository": "/tmp/does-not-matter"},
                deadline_seconds=deadline_seconds, max_attempts=max_attempts,
            )

    def test_two_operation_minimum_is_unchanged_without_any_search(self):
        bundle = self.divergent_bundle(["op-0", "op-1"])
        result = self.run_worker_with_fake_backend(bundle)
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["attemptCount"], 0)
        self.assertEqual(sorted(result["selectedOperationIds"]), ["op-0", "op-1"])

    def test_redundant_operation_is_removed_when_a_smaller_divergent_subset_exists(self):
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2"])
        result = self.run_worker_with_fake_backend(
            bundle, divergent_subsets={frozenset({"op-0", "op-2"})},
        )
        self.assertEqual(result["status"], "reduced")
        self.assertEqual(sorted(result["selectedOperationIds"]), ["op-0", "op-2"])
        self.assertIsNotNone(result["witnessEvidence"])
        self.assertEqual(result["witnessEvidence"]["result"], "divergent")
        # (op-0, op-1) is tried first and is not divergent; (op-0, op-2) is the witness.
        self.assertEqual(result["attemptCount"], 2)

    def test_ascending_size_and_stable_id_order_selects_the_first_qualifying_subset(self):
        # Two size-2 candidates would qualify; op-0/op-2 sorts before op-1/op-2.
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2", "op-3"])
        result = self.run_worker_with_fake_backend(
            bundle,
            divergent_subsets={
                frozenset({"op-1", "op-2"}),
                frozenset({"op-0", "op-2"}),
                frozenset({"op-0", "op-1", "op-3"}),
            },
        )
        self.assertEqual(result["status"], "reduced")
        self.assertEqual(sorted(result["selectedOperationIds"]), ["op-0", "op-2"])

    def test_no_smaller_qualifying_subset_leaves_the_original_witness_unchanged(self):
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2"])
        result = self.run_worker_with_fake_backend(bundle, divergent_subsets=frozenset())
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(sorted(result["selectedOperationIds"]), ["op-0", "op-1", "op-2"])
        self.assertEqual(result["witnessEvidenceDigest"], bundle["evidenceDigest"])
        # Only the dependency-closed proper subsets of size 2 are real attempts.
        self.assertEqual(result["attemptCount"], 3)

    def test_dependency_incomplete_subsets_are_discarded_not_attempted(self):
        # op-2 depends on op-1; any subset containing op-2 without op-1 is skipped.
        bundle = self.divergent_bundle(
            ["op-0", "op-1", "op-2"], dependencies={"op-2": ["op-1"]},
        )
        result = self.run_worker_with_fake_backend(bundle, divergent_subsets=frozenset())
        self.assertEqual(result["status"], "unchanged")
        # {op-0, op-2} and size-2 combos missing op-1 for op-2 are dependency-incomplete;
        # only {op-0, op-1} and {op-1, op-2} are genuine attempts.
        self.assertEqual(result["attemptCount"], 2)
        self.assertGreaterEqual(result["skippedDependencyIncompleteSubsets"], 1)

    def test_budget_exhaustion_by_attempt_cap_is_inconclusive_never_a_minimality_claim(self):
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2", "op-3"])
        result = self.run_worker_with_fake_backend(
            bundle, divergent_subsets=frozenset(), max_attempts=1,
        )
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["selectedOperationIds"])
        self.assertIsNone(result["witnessEvidence"])
        self.assertLessEqual(result["attemptCount"], 1)

    def test_budget_exhaustion_by_deadline_is_inconclusive_never_a_minimality_claim(self):
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2"])
        result = self.run_worker_with_fake_backend(
            bundle, divergent_subsets=frozenset(), deadline_seconds=0.0,
        )
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["selectedOperationIds"])
        self.assertIn("budget was exhausted", result["reason"])

    def test_candidate_verification_failure_cannot_be_a_reduced_witness(self):
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2"])
        with mock.patch.object(
            git_counterexamples.git_replay, "verify",
            side_effect=[{"status": "verified"},
                         {"status": "unverified", "reason": "missing source object"}],
        ), mock.patch.object(
            git_counterexamples.git_replay, "produce",
            side_effect=self.fake_produce({frozenset({"op-0", "op-1"})}),
        ):
            result = _run_worker({"evidence": bundle, "repository": "/tmp/x"})
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["selectedOperationIds"])
        self.assertEqual(result["attempts"][0]["verificationStatus"], "unverified")

    def test_candidate_replay_failure_cannot_support_unchanged_minimality(self):
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2"])
        with mock.patch.object(git_counterexamples.git_replay, "verify",
                               return_value={"status": "verified"}), \
             mock.patch.object(git_counterexamples.git_replay, "produce",
                               side_effect=git_counterexamples.git_replay.InvalidGitReplay(
                                   "missing source object")):
            result = _run_worker({"evidence": bundle, "repository": "/tmp/x"})
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["selectedOperationIds"])
        self.assertEqual(result["attemptCount"], 1)

    def test_verified_inconclusive_candidate_cannot_support_minimality(self):
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2"])

        def incomplete_candidate(request):
            ids = [operation["instanceId"] for operation in request["operations"]]
            candidate = self.divergent_bundle(ids)
            candidate["result"] = "inconclusive"
            return candidate, {"mode": "manual-review"}

        with mock.patch.object(git_counterexamples.git_replay, "verify",
                               return_value={"status": "verified"}), \
             mock.patch.object(git_counterexamples.git_replay, "produce",
                               side_effect=incomplete_candidate):
            result = _run_worker({"evidence": bundle, "repository": "/tmp/x"})
        self.assertEqual(result["status"], "inconclusive")
        self.assertIsNone(result["selectedOperationIds"])
        self.assertEqual(result["attempts"][0]["outcome"], "inconclusive")

    def test_a_smaller_divergent_subset_found_before_exhaustion_still_reports_reduced(self):
        # Even with a tight attempt cap, finding a witness on the very first
        # dependency-closed attempt must report "reduced", not "inconclusive".
        bundle = self.divergent_bundle(["op-0", "op-1", "op-2", "op-3"])
        result = self.run_worker_with_fake_backend(
            bundle, divergent_subsets={frozenset({"op-0", "op-1"})}, max_attempts=1,
        )
        self.assertEqual(result["status"], "reduced")
        self.assertEqual(sorted(result["selectedOperationIds"]), ["op-0", "op-1"])

    def test_unverified_input_is_never_treated_as_rejected_or_a_minimality_claim(self):
        bundle = self.divergent_bundle(["op-0", "op-1"])
        with mock.patch.object(git_counterexamples.git_replay, "verify",
                                return_value={"status": "unverified", "reason": "git infrastructure failure"}):
            result = _run_worker({"evidence": bundle, "repository": "/tmp/x"})
        self.assertEqual(result["status"], "unverified")
        self.assertIsNone(result["selectedOperationIds"])
        self.assertIsNone(result["witnessEvidence"])

    def test_verification_exception_is_reported_as_inconclusive_not_raised(self):
        bundle = self.divergent_bundle(["op-0", "op-1"])
        with mock.patch.object(git_counterexamples.git_replay, "verify",
                                side_effect=RuntimeError("boom")):
            result = _run_worker({"evidence": bundle, "repository": "/tmp/x"})
        self.assertEqual(result["status"], "inconclusive")

    def test_base_result_is_defensive_against_malformed_evidence(self):
        self.assertEqual(_base_result(None), {"originalEvidenceDigest": None, "originalOperationIds": []})
        self.assertEqual(_base_result({"evidenceDigest": 5}),
                          {"originalEvidenceDigest": None, "originalOperationIds": []})


if __name__ == "__main__":
    unittest.main()
