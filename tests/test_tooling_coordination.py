# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import tooling_coordination as coordination


CANDIDATE = "a" * 40
TASK_A, TASK_B, TASK_C = "SPEC-044/OP001", "SPEC-044/OP002", "SPEC-044/T002"
RECEIPT = coordination.EvidenceRef("private:synthetic-receipt", "b" * 64)


def _process_claim(root, queue, barrier=None):
    try:
        if barrier is not None:
            barrier.wait(timeout=5)
        coordination.CoordinationRegistry(root).claim(
            TASK_A, owner="executor", candidate_sha256=CANDIDATE)
        queue.put("claimed")
    except coordination.CoordinationError:
        queue.put("refused")


class CoordinationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / "private-registry"
        self.registry = coordination.CoordinationRegistry(self.root)

    def initialize(self, tasks=None):
        self.registry.initialize(tasks or (
            coordination.TaskSpec(TASK_A, owner="executor"),
            coordination.TaskSpec(TASK_B, (TASK_A,), owner="executor"),
        ), candidate_sha256=CANDIDATE)

    def claim(self, task_id=TASK_A):
        return self.registry.claim(task_id, owner="executor", candidate_sha256=CANDIDATE)

    def test_restart_preserves_completed_dependencies_and_candidate(self):
        self.initialize()
        with self.assertRaisesRegex(coordination.CoordinationError, "dependencies"):
            self.claim(TASK_B)
        claim = self.claim()
        self.registry.start(claim, candidate_sha256=CANDIDATE)
        self.registry.finish(claim, candidate_sha256=CANDIDATE, evidence_refs=(RECEIPT,))
        restarted = coordination.CoordinationRegistry(self.root)
        self.assertEqual("complete", restarted.inspect()["tasks"][TASK_A]["status"])
        self.assertEqual(TASK_B, restarted.claim(
            TASK_B, owner="executor", candidate_sha256=CANDIDATE).task_id)
        self.assertEqual(0, self.root.stat().st_mode & 0o077)
        self.assertEqual(0, (self.root / "registry.json").stat().st_mode & 0o077)

    def test_missing_dependency_cycle_unknown_id_and_empty_plan_fail(self):
        plans = (
            (),
            (coordination.TaskSpec("SPEC-999/T001"),),
            (coordination.TaskSpec(TASK_A, (TASK_B,)),),
            (coordination.TaskSpec(TASK_A, (TASK_B,)),
             coordination.TaskSpec(TASK_B, (TASK_A,))),
        )
        for tasks in plans:
            with self.subTest(tasks=tasks), self.assertRaises(coordination.CoordinationError):
                self.registry.initialize(tasks, candidate_sha256=CANDIDATE)
        self.assertFalse((self.root / "registry.json").exists())

    def test_fixed_inventory_contains_24_originals_and_six_operational_tasks(self):
        self.assertEqual(30, len(coordination.M45_PENDING_TASK_IDS))
        self.assertNotIn("SPEC-044/T003", coordination.M45_PENDING_TASK_IDS)

    def test_candidate_drift_wrong_owner_and_forged_token_are_refused(self):
        self.initialize()
        for owner, candidate in (("other", CANDIDATE), ("executor", "c" * 40)):
            with self.assertRaises(coordination.CoordinationError):
                self.registry.claim(TASK_A, owner=owner, candidate_sha256=candidate)
        claim = self.claim()
        for forged in (replace(claim, token="0" * 32), replace(claim, owner="other")):
            with self.assertRaises(coordination.CoordinationError):
                self.registry.start(forged, candidate_sha256=CANDIDATE)
        with self.assertRaises(coordination.CoordinationError):
            self.registry.start(claim, candidate_sha256="c" * 40)
        self.assertEqual("claimed", self.registry.inspect()["tasks"][TASK_A]["status"])

    def test_only_prestart_claim_can_be_released(self):
        self.initialize()
        claim = self.claim()
        self.registry.release(claim, candidate_sha256=CANDIDATE, reason="prelaunch cancelled")
        fresh = self.claim()
        self.assertNotEqual(claim.token, fresh.token)
        self.registry.start(fresh, candidate_sha256=CANDIDATE)
        with self.assertRaises(coordination.CoordinationError):
            self.registry.release(fresh, candidate_sha256=CANDIDATE, reason="cannot replay")
        with self.assertRaises(coordination.CoordinationError):
            self.claim()
        with self.assertRaises(coordination.CoordinationError):
            self.registry.start(fresh, candidate_sha256=CANDIDATE)
        self.assertEqual("started", coordination.CoordinationRegistry(self.root).inspect()["tasks"][TASK_A]["status"])

    def test_native_interruption_retains_reservation_until_explicit_stop_receipt(self):
        self.initialize((coordination.TaskSpec(TASK_A, owner="executor", native=True),
                         coordination.TaskSpec(TASK_C, owner="executor", native=True),
                         coordination.TaskSpec(TASK_B, owner="executor")))
        claim = self.claim()
        self.registry.start(claim, candidate_sha256=CANDIDATE)
        self.registry.interrupt(claim, candidate_sha256=CANDIDATE, reason="outcome unknown")
        with self.assertRaisesRegex(coordination.CoordinationError, "native"):
            self.claim(TASK_C)
        self.assertEqual(TASK_B, self.claim(TASK_B).task_id)
        with self.assertRaisesRegex(coordination.CoordinationError, "stop receipt"):
            self.registry.finish(claim, candidate_sha256=CANDIDATE,
                                 status="failed", evidence_refs=(RECEIPT,))
        self.registry.finish(claim, candidate_sha256=CANDIDATE, status="failed",
                             evidence_refs=(RECEIPT,), native_stop_ref=RECEIPT)
        self.assertEqual(TASK_C, self.claim(TASK_C).task_id)
        with self.assertRaises(coordination.CoordinationError):
            self.claim()

    def test_block_requires_explicit_unblock_and_failed_dependency_stays_unready(self):
        self.initialize()
        self.registry.block(TASK_A, candidate_sha256=CANDIDATE, reason="login needed")
        with self.assertRaises(coordination.CoordinationError):
            self.claim()
        self.registry.unblock(TASK_A, candidate_sha256=CANDIDATE, reason="login restored")
        claim = self.claim()
        self.registry.start(claim, candidate_sha256=CANDIDATE)
        self.registry.finish(claim, candidate_sha256=CANDIDATE,
                             status="failed", evidence_refs=(RECEIPT,))
        with self.assertRaisesRegex(coordination.CoordinationError, "dependencies"):
            self.claim(TASK_B)

    def test_threads_and_processes_cannot_claim_same_task_twice(self):
        self.initialize()
        def attempt(_index):
            try:
                self.claim()
                return "claimed"
            except coordination.CoordinationError:
                return "refused"
        with ThreadPoolExecutor(max_workers=8) as pool:
            self.assertEqual(1, list(pool.map(attempt, range(8))).count("claimed"))
        context = multiprocessing.get_context("spawn")
        queue = context.Queue()
        process = context.Process(target=_process_claim, args=(str(self.root), queue))
        process.start()
        process.join(10)
        self.assertFalse(process.is_alive())
        self.assertEqual(0, process.exitcode)
        self.assertEqual("refused", queue.get(timeout=3))
        queue.close()

    def test_corruption_oversize_symlink_and_nonprivate_files_fail_closed(self):
        self.initialize()
        path = self.root / "registry.json"
        original = path.read_bytes()
        record = json.loads(original)
        record["tasks"][TASK_A]["status"] = "complete"
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError):
            self.registry.inspect()
        path.write_bytes(b" " * (coordination.MAX_REGISTRY_BYTES + 1))
        with self.assertRaises(coordination.CoordinationError):
            self.registry.inspect()
        path.write_bytes(original)
        path.chmod(0o644)
        with self.assertRaises(coordination.CoordinationError):
            self.registry.inspect()
        path.chmod(0o600)
        target = self.root / "replacement.json"
        path.rename(target)
        path.symlink_to(target)
        with self.assertRaises(coordination.CoordinationError):
            self.registry.inspect()

    def test_sealed_but_inconsistent_snapshot_is_rejected(self):
        self.initialize()
        path = self.root / "registry.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["tasks"][TASK_A]["status"] = "started"
        payload = {key: value for key, value in record.items() if key != "recordSha256"}
        record["recordSha256"] = hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        path.write_text(json.dumps(record), encoding="utf-8")
        with self.assertRaises(coordination.CoordinationError):
            self.registry.inspect()

    def test_completion_needs_bound_evidence_and_does_not_mutate_inspection(self):
        self.initialize()
        claim = self.claim()
        self.registry.start(claim, candidate_sha256=CANDIDATE)
        with self.assertRaises(coordination.CoordinationError):
            self.registry.finish(claim, candidate_sha256=CANDIDATE, evidence_refs=())
        inspected = self.registry.inspect()
        inspected["tasks"][TASK_A]["status"] = "complete"
        self.assertEqual("started", self.registry.inspect()["tasks"][TASK_A]["status"])

    def test_atomic_replace_failure_leaves_prior_snapshot_and_no_temporary_file(self):
        self.initialize()
        before = self.registry.inspect()
        with patch.object(coordination.os, "replace", side_effect=OSError("synthetic failure")):
            with self.assertRaises(coordination.CoordinationError):
                self.claim()
        self.assertEqual(before, self.registry.inspect())
        self.assertEqual([], list(self.root.glob(".registry-*")))
        self.assertEqual(TASK_A, self.claim().task_id)

    def test_actual_process_race_has_exactly_one_claim(self):
        self.initialize()
        context = multiprocessing.get_context("spawn")
        queue, barrier = context.Queue(), context.Barrier(2)
        processes = [context.Process(target=_process_claim, args=(str(self.root), queue, barrier))
                     for _ in range(2)]
        for process in processes:
            process.start()
        for process in processes:
            process.join(10)
            self.assertFalse(process.is_alive())
            self.assertEqual(0, process.exitcode)
        results = [queue.get(timeout=3) for _ in processes]
        queue.close()
        self.assertEqual(["claimed", "refused"], sorted(results))

    def test_duplicate_json_keys_and_hardlink_alias_are_refused(self):
        self.initialize()
        path = self.root / "registry.json"
        raw = path.read_bytes()
        path.write_bytes(b'{"schemaVersion":"duplicate",' + raw[1:])
        with self.assertRaises(coordination.CoordinationError):
            self.registry.inspect()
        path.write_bytes(raw)
        alias = self.root / "alias.json"
        alias.hardlink_to(path)
        with self.assertRaises(coordination.CoordinationError):
            self.registry.inspect()

    def test_reinitialize_and_unknown_task_never_reset_history(self):
        self.initialize()
        claim = self.claim()
        self.registry.start(claim, candidate_sha256=CANDIDATE)
        with self.assertRaises(coordination.CoordinationError):
            self.initialize()
        with self.assertRaises(coordination.CoordinationError):
            self.claim("SPEC-041/T010")
        self.assertEqual("started", self.registry.inspect()["tasks"][TASK_A]["status"])

    def test_sanitized_handoff_excludes_tokens_refs_owner_and_private_block_reason(self):
        self.initialize()
        self.registry.block(TASK_B, candidate_sha256=CANDIDATE,
                            reason="private-account@example.invalid must login")
        claim = self.claim()
        handoff = self.registry.sanitized_handoff()
        self.assertEqual("blocked", handoff["tasks"][TASK_B]["procedureStatus"])
        self.assertTrue(handoff["tasks"][TASK_B]["blocked"])
        raw = json.dumps(handoff)
        for field in (claim.token, "executor", "@", "private-account", "blockReason", "claimToken"):
            self.assertNotIn(field, raw)

    def test_malformed_types_cannot_bypass_snapshot_state_validation(self):
        self.initialize()
        path = self.root / "registry.json"
        original = path.read_bytes()
        for field, value in (("status", []), ("dependencies", [[]]), ("claimToken", 123)):
            with self.subTest(field=field):
                record = json.loads(original)
                record["tasks"][TASK_A][field] = value
                payload = {key: item for key, item in record.items() if key != "recordSha256"}
                record["recordSha256"] = hashlib.sha256(json.dumps(
                    payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
                path.write_text(json.dumps(record), encoding="utf-8")
                with self.assertRaises(coordination.CoordinationError):
                    self.registry.inspect()


if __name__ == "__main__":
    unittest.main()
