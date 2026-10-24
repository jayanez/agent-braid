# SPDX-License-Identifier: AGPL-3.0-only
"""Offline durable-attempt journal controls: real process kills at each durable boundary.

Fixture children and the driver process are real; nothing here launches a host, model or
paid route, and the simulated backend confines nothing (see harness_lab).
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

from agent_braid import harness_journal as journal
from agent_braid import harness_lab as lab
from agent_braid.harness_admission import RECEIPT_FORMAT, Reservation
from agent_braid.system_one import canonical
from tests.test_harness_lab import make_inventory, manifest_for

NOW = 1_800_000_000
REPO = Path(__file__).resolve().parent.parent
BOUNDARIES = ("after-start", "after-checkpoint", "after-run", "after-terminal")
TORN = ("torn-start", "torn-cp01", "torn-end")


def fixture_bytes(effects: str, pidfile: str, sleep: int = 0) -> bytes:
    return f'''
import json, os, time
with open({effects!r}, "a") as f:
    f.write("effect\\n")
open({pidfile!r}, "w").write(str(os.getpid()))
time.sleep({sleep})
for e in ({{"seq": 0, "kind": "start"}}, {{"seq": 1, "kind": "terminal", "state": "completed"}}):
    print(json.dumps(e))
'''.encode()


def reservation_for(manifest, rid="case-1", at=NOW, ttl=200) -> Reservation:
    return Reservation(canonical({
        "format": RECEIPT_FORMAT, "id": rid, "admissionSha256": "a" * 64,
        "manifestSha256": manifest.sha256, "envelopeSha256": "b" * 64, "reservedAt": at,
        "expiresAt": at + ttl, "reservedJournalBytes": 1 << 20, "executionAuthorization": False}))


def drive(boundary: str, root: str, effects: str, pidfile: str, sleep: int) -> None:
    """Child-process body: run the attempt and SIGKILL itself at ``boundary``."""
    fixture = fixture_bytes(effects, pidfile, sleep)
    manifest = manifest_for(fixture)
    path, kill = Path(root), lambda: os.kill(os.getpid(), signal.SIGKILL)
    if boundary.startswith("torn-"):  # die after the temp record is written, before publication
        real_rename, target = os.rename, f".{boundary[5:]}"

        def rename(src, dst, **kwargs):
            if target in str(dst):
                kill()
            return real_rename(src, dst, **kwargs)
        os.rename = rename
    journal.begin_attempt(path, manifest, attempt_id="attempt-1",
                          reservation=reservation_for(manifest), now=NOW)
    if boundary == "after-start":
        kill()
    journal.checkpoint(path, manifest, attempt_id="attempt-1", completed=[],
                       pending=["dispatch"], artifacts={}, now=NOW)
    if boundary == "after-checkpoint":
        kill()
    result = lab.run_fixture(manifest, fixture, backend=lab.SimulatedContainment(),
                             attempt_id="attempt-1", inventory=make_inventory(), now=NOW,
                             retention_seconds=60, limits=lab.FixtureLimits(wall_seconds=30))
    if boundary == "after-run":
        kill()
    journal.finish_attempt(path, manifest, attempt_id="attempt-1", result=result, now=NOW)
    kill()


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.root = base / "journal"
        self.root.mkdir(mode=0o700)
        self.effects, self.pidfile = str(base / "effects.log"), str(base / "pid")
        self.fixture = fixture_bytes(self.effects, self.pidfile)
        self.manifest = manifest_for(self.fixture)

    def reserve(self, rid="case-1", **over):
        return reservation_for(self.manifest, rid, **over)

    def begin(self, attempt_id="attempt-1", rid="case-1", now=NOW, **over):
        return journal.begin_attempt(self.root, self.manifest, attempt_id=attempt_id,
                                     reservation=over.pop("reservation", None) or self.reserve(rid),
                                     now=now)

    def inspect(self, attempt_id="attempt-1", manifest=None, now=NOW):
        return journal.inspect_attempt(self.root, manifest or self.manifest,
                                       attempt_id=attempt_id, now=now)

    def refuses(self, reason, call, *args, **kwargs):
        with self.assertRaises(journal.JournalError) as caught:
            call(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def effect_count(self):
        try:
            return len(Path(self.effects).read_text().splitlines())
        except FileNotFoundError:
            return 0

    def names(self):
        return sorted(p.name for p in self.root.iterdir() if p.name != ".lock")

    def run_attempt(self, attempt_id="attempt-1", rid="case-1"):
        return journal.run_journaled(
            self.root, self.manifest, self.fixture, attempt_id=attempt_id,
            reservation=self.reserve(rid), backend=lab.SimulatedContainment(),
            inventory=make_inventory(), now=NOW, retention_seconds=60,
            limits=lab.FixtureLimits(wall_seconds=5))


class KillTests(Base):
    def spawn(self, boundary, sleep=0):
        return subprocess.Popen(
            [sys.executable, "-c",
             "import sys; from tests.test_harness_journal import drive; drive(*sys.argv[1:5], int(sys.argv[5]))",
             boundary, str(self.root), self.effects, self.pidfile, str(sleep)],
            cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_sigkill_at_each_durable_boundary(self):
        expected = {"after-start": ("started", None), "after-checkpoint": ("checkpointed", None),
                    "after-run": ("checkpointed", None), "after-terminal": ("ended", "completed")}
        for boundary in BOUNDARIES:
            with self.subTest(boundary=boundary):
                self.tearDown(), self.setUp()
                proc = self.spawn(boundary)
                self.assertEqual(proc.wait(timeout=60), -signal.SIGKILL)  # really killed
                status = self.inspect()
                self.assertEqual((status.phase, status.state), expected[boundary])
                self.assertEqual(self.effect_count(), 0 if boundary in ("after-start",
                                 "after-checkpoint") else 1)
                self.assertFalse(status.redispatch_allowed or status.permission_renewed)
                # the same reservation can never dispatch again, killed or not
                self.refuses("admission-consumed" if boundary == "after-terminal"
                             else "unreconciled-attempt", self.begin, "attempt-2")
                reconciled = journal.reconcile_attempt(self.root, self.manifest,
                                                       attempt_id="attempt-1", now=NOW)
                if boundary == "after-terminal":
                    self.assertEqual((reconciled.state, reconciled.source),
                                     ("completed", "terminal"))
                else:  # the fixture may even have finished, but completion is never fabricated
                    self.assertEqual((reconciled.state, reconciled.outcome, reconciled.source),
                                     ("interrupted", "unknown", "recovery"))
                self.assertEqual(reconciled, journal.reconcile_attempt(
                    self.root, self.manifest, attempt_id="attempt-1", now=NOW))
                self.refuses("admission-consumed", self.begin, "attempt-2")
                self.refuses("admission-expired", self.begin, "attempt-2", "case-2",
                             now=NOW + 1000)
                self.assertEqual(self.effect_count(), 0 if boundary in ("after-start",
                                 "after-checkpoint") else 1)

    def test_sigkill_between_write_and_publish_leaves_a_recoverable_journal(self):
        # (boundary, attempt durable?, fixture effects, status after kill)
        cases = {"torn-start": (False, 0), "torn-cp01": (True, 0), "torn-end": (True, 1)}
        for boundary in TORN:
            with self.subTest(boundary=boundary):
                self.tearDown(), self.setUp()
                proc = self.spawn(boundary)
                self.assertEqual(proc.wait(timeout=60), -signal.SIGKILL)
                durable, effects = cases[boundary]
                self.assertTrue(any(n.startswith(".tmp-") for n in os.listdir(self.root)))
                self.assertEqual(self.effect_count(), effects)
                if not durable:  # nothing was published, so nothing was consumed
                    self.refuses("unknown-attempt", self.inspect)
                    self.assertEqual(self.begin().phase, "started")
                    continue
                self.assertEqual(self.inspect().state, None)
                reconciled = journal.reconcile_attempt(self.root, self.manifest,
                                                       attempt_id="attempt-1", now=NOW)
                self.assertEqual((reconciled.state, reconciled.outcome), ("interrupted", "unknown"))
                self.assertFalse(any(n.startswith(".tmp-") for n in os.listdir(self.root)))
                self.refuses("admission-consumed", self.begin, "attempt-2")
                self.assertEqual(self.effect_count(), effects)

    def test_killed_while_the_fixture_child_runs(self):
        fixture = fixture_bytes(self.effects, self.pidfile, sleep=30)
        self.manifest = manifest_for(fixture)
        proc = self.spawn("after-run", sleep=30)
        try:
            deadline = time.monotonic() + 30
            while not (Path(self.pidfile).exists() and Path(self.pidfile).read_text()):
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.05)
            proc.kill()
            proc.wait(timeout=30)
        finally:
            try:
                os.killpg(int(Path(self.pidfile).read_text()), signal.SIGKILL)
            except (OSError, ValueError):
                pass
        status = self.inspect()
        self.assertEqual((status.phase, status.state), ("checkpointed", None))
        self.assertEqual(self.effect_count(), 1)
        self.assertEqual(journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1",
                                                   now=NOW).state, "interrupted")
        self.refuses("admission-consumed", self.begin, "attempt-2")
        self.assertEqual(self.effect_count(), 1)

    def test_next_attempt_needs_reconcile_and_a_new_reservation(self):
        self.begin()
        self.refuses("unreconciled-attempt", self.begin, "attempt-2", "case-2")
        journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1", now=NOW)
        self.refuses("admission-consumed", self.begin, "attempt-2", "case-1")
        self.assertEqual(self.begin("attempt-2", "case-2").phase, "started")  # separately admitted


class AttemptTests(Base):
    def test_run_records_terminal_and_everything_is_non_authorizing(self):
        status = self.run_attempt()
        self.assertEqual((status.phase, status.state, status.outcome, status.source),
                         ("ended", "completed", "recorded", "terminal"))
        self.assertEqual(status.records, 3)
        self.assertEqual(self.names(), ["attempt-1.cp01.json", "attempt-1.end.json",
                                        "attempt-1.start.json"])
        self.assertFalse(status.executionAuthorization or status.to_dict()["executionAuthorization"]
                         or status.redispatch_allowed or status.permission_renewed)
        for name in self.names():
            self.assertEqual(os.stat(self.root / name).st_mode & 0o777, 0o600)
            self.assertIs(json.loads((self.root / name).read_bytes())["executionAuthorization"],
                          False)
        with self.assertRaises(FrozenInstanceError):
            status.state = "failed"
        self.assertEqual(self.effect_count(), 1)

    def test_lossy_or_failed_run_is_recorded_as_observed_never_upgraded(self):
        broken = b'import json\nprint(json.dumps({"seq": 0, "kind": "start"}))\n'
        self.fixture, self.manifest = broken, manifest_for(broken)
        status = self.run_attempt()
        self.assertEqual(status.state, "unobserved")
        self.assertNotEqual(status.state, "completed")

    def test_checkpoint_chain_carries_work_and_no_renewal(self):
        self.begin()
        journal.checkpoint(self.root, self.manifest, attempt_id="attempt-1", completed=["a"],
                           pending=["b", "c"], artifacts={"out.txt": "c" * 64}, now=NOW + 1)
        status = journal.checkpoint(self.root, self.manifest, attempt_id="attempt-1",
                                    completed=["a", "b"], pending=["c"], artifacts={}, now=NOW + 2)
        self.assertEqual((status.completed, status.pending, status.records),
                         (("a", "b"), ("c",), 3))
        record = json.loads((self.root / "attempt-1.cp02.json").read_bytes())
        self.assertIs(record["permissionRenewed"], False)
        self.assertEqual(record["prevSha256"],
                         sha256((self.root / "attempt-1.cp01.json").read_bytes()).hexdigest())
        reconciled = journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1",
                                               now=NOW + 3)
        self.assertEqual((reconciled.completed, reconciled.pending), (("a", "b"), ("c",)))
        self.refuses("attempt-ended", journal.checkpoint, self.root, self.manifest,
                     attempt_id="attempt-1", completed=[], pending=[], artifacts={}, now=NOW + 4)

    def test_checkpoint_bounds_and_shape(self):
        self.begin()
        good = dict(completed=[], pending=[], artifacts={}, now=NOW)
        for bad in ({"completed": ["a"], "pending": ["a"]}, {"completed": ["BAD"]},
                    {"completed": [str(i) for i in range(17)]}, {"pending": "ab"},
                    {"artifacts": {"../x": "c" * 64}}, {"artifacts": {"x": "nothash"}},
                    {"artifacts": {f"f{i}": "c" * 64 for i in range(33)}}, {"artifacts": []}):
            self.refuses("invalid-checkpoint", journal.checkpoint, self.root, self.manifest,
                         attempt_id="attempt-1", **{**good, **bad})
        for _ in range(journal.MAX_CHECKPOINTS):
            journal.checkpoint(self.root, self.manifest, attempt_id="attempt-1", **good)
        self.refuses("checkpoint-budget-exhausted", journal.checkpoint, self.root, self.manifest,
                     attempt_id="attempt-1", **good)

    def test_reconcile_twice_writes_nothing_new(self):
        self.begin()
        first = journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1", now=NOW)
        before = {n: (self.root / n).read_bytes() for n in self.names()}
        self.assertEqual(first, journal.reconcile_attempt(self.root, self.manifest,
                                                          attempt_id="attempt-1", now=NOW + 5))
        self.assertEqual(before, {n: (self.root / n).read_bytes() for n in self.names()})
        self.refuses("attempt-ended", self.finish_with, self.run_for_result())

    def run_for_result(self):
        return lab.run_fixture(self.manifest, self.fixture, backend=lab.SimulatedContainment(),
                               attempt_id="attempt-1", inventory=make_inventory(), now=NOW,
                               retention_seconds=60, limits=lab.FixtureLimits(wall_seconds=5))

    def finish_with(self, result, manifest=None, attempt_id="attempt-1"):
        return journal.finish_attempt(self.root, manifest or self.manifest,
                                      attempt_id=attempt_id, result=result, now=NOW)

    def test_finish_refuses_foreign_result_and_double_finish(self):
        self.begin()
        result = self.run_for_result()
        self.begin_other = None
        self.refuses("result-mismatch", self.finish_with, result, attempt_id="attempt-9")
        self.refuses("invalid-result", self.finish_with, object())
        self.finish_with(result)
        self.refuses("attempt-ended", self.finish_with, result)


class DriftAndAuthorityTests(Base):
    def test_other_manifest_or_unknown_attempt_is_drift(self):
        self.begin()
        other = manifest_for(self.fixture + b"\n# changed")
        for call in (lambda: journal.inspect_attempt(self.root, other, attempt_id="attempt-1", now=NOW),
                     lambda: journal.reconcile_attempt(self.root, other, attempt_id="attempt-1", now=NOW),
                     lambda: journal.checkpoint(self.root, other, attempt_id="attempt-1",
                                                completed=[], pending=[], artifacts={}, now=NOW)):
            self.refuses("manifest-drift", call)
        self.assertEqual(self.names(), ["attempt-1.start.json"])  # drift wrote nothing
        self.refuses("unknown-attempt", self.inspect, "attempt-9")

    def test_tampered_start_binding_is_drift_and_tampered_chain_is_corrupt(self):
        self.begin()
        path = self.root / "attempt-1.start.json"
        record = json.loads(path.read_bytes())
        record["fixtureSha256"] = "d" * 64
        path.write_bytes(canonical(record))
        self.refuses("fixture-drift", self.inspect)
        record["fixtureSha256"] = sha256(self.fixture).hexdigest()
        path.write_bytes(canonical(record))
        journal.checkpoint(self.root, self.manifest, attempt_id="attempt-1", completed=[],
                           pending=[], artifacts={}, now=NOW)
        record["at"] += 1  # rewrite the start only: the chain no longer matches
        path.write_bytes(canonical(record))
        self.refuses("corrupt-journal", self.inspect)

    def test_admission_must_match_manifest_window_and_shape(self):
        other = reservation_for(manifest_for(self.fixture + b"\n# other"))
        self.refuses("admission-mismatch", self.begin, reservation=other)
        self.refuses("admission-expired", self.begin, now=NOW + 200)
        self.refuses("admission-expired", self.begin, reservation=self.reserve(at=NOW + 5))
        wire = json.loads(self.reserve().canonical_bytes)
        wire["executionAuthorization"] = True
        self.refuses("invalid-reservation", self.begin, reservation=Reservation(canonical(wire)))
        self.refuses("invalid-reservation", self.begin, reservation=Reservation(b"not json"))
        self.refuses("invalid-reservation", self.begin, reservation={"id": "case-1"})
        self.assertEqual(self.names(), [])  # refusals consumed nothing

    def test_same_reservation_id_cannot_return_under_a_new_digest(self):
        self.begin()
        journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1", now=NOW)
        renamed = self.reserve(at=NOW)  # same id, different reservedAt => different bytes? ttl differs
        renamed = reservation_for(self.manifest, "case-1", ttl=150)
        self.refuses("admission-consumed", self.begin, "attempt-2", reservation=renamed)

    def test_attempt_id_reuse_and_clock_regression(self):
        self.begin()
        journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1", now=NOW)
        self.refuses("attempt-exists", self.begin, "attempt-1", "case-2")
        self.refuses("clock-regression", self.begin, "attempt-2", "case-2", now=NOW - 1,
                     reservation=self.reserve("case-2", at=NOW - 5))
        self.refuses("clock-regression", self.inspect, now=NOW - 1)


class StoreIntegrityTests(Base):
    def test_torn_and_foreign_entries_refuse_instead_of_repair(self):
        self.begin()
        (self.root / "attempt-1.cp01.json").write_bytes(b"")  # torn write
        for call in (self.inspect, self.begin):
            self.refuses("corrupt-journal", call) if call == self.inspect else \
                self.refuses("corrupt-journal", call, "attempt-2", "case-2")
        os.unlink(self.root / "attempt-1.cp01.json")
        (self.root / "stray.txt").write_text("x")
        self.refuses("corrupt-journal", self.inspect)

    def test_leftover_temp_files_are_ignored_counted_and_swept(self):
        self.begin()
        (self.root / ".tmp-0123456789abcdef").write_bytes(b"partial")
        self.assertEqual(self.inspect().phase, "started")
        (self.root / ".tmp-nothex").write_bytes(b"x")  # not our naming: foreign
        self.refuses("corrupt-journal", self.inspect)
        os.unlink(self.root / ".tmp-nothex")
        journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1", now=NOW)
        self.assertEqual([n for n in os.listdir(self.root) if n.startswith(".tmp-")], [])
        for index in range(journal.MAX_ENTRIES + 1):
            (self.root / f".tmp-{index:016x}").write_bytes(b"x")
        self.refuses("journal-budget-exhausted", self.inspect)

    def test_torn_published_record_still_refuses(self):
        self.begin()
        journal.checkpoint(self.root, self.manifest, attempt_id="attempt-1", completed=[],
                           pending=[], artifacts={}, now=NOW)
        journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1", now=NOW)
        (self.root / "attempt-1.cp01.json").write_bytes(b"")  # media damage mid-chain
        self.refuses("corrupt-journal", self.inspect)
        self.refuses("corrupt-journal", journal.reconcile_attempt, self.root, self.manifest,
                     attempt_id="attempt-1", now=NOW)

    def test_gap_orphan_and_post_end_records_refuse(self):
        self.begin()
        path = self.root / "attempt-1.start.json"
        for name in ("attempt-1.cp02.json", "attempt-2.end.json"):
            (self.root / name).write_bytes(path.read_bytes())
            self.refuses("corrupt-journal", self.inspect)
            os.unlink(self.root / name)
        journal.reconcile_attempt(self.root, self.manifest, attempt_id="attempt-1", now=NOW)
        (self.root / "attempt-1.cp01.json").write_bytes(path.read_bytes())
        self.refuses("corrupt-journal", self.inspect)

    def test_unsafe_records_and_unknown_fields_refuse(self):
        self.begin()
        path = self.root / "attempt-1.start.json"
        raw = path.read_bytes()
        os.chmod(path, 0o644)
        self.refuses("corrupt-journal", self.inspect)
        os.chmod(path, 0o600)
        os.unlink(path)
        os.symlink(self.root / "elsewhere", path)
        self.refuses("corrupt-journal", self.inspect)
        os.unlink(path)
        for tampered in (raw[:-1] + b',"extra":1}', raw.replace(b'"kind":"start"', b'"kind":"start","kind":"start"'),
                         b"x" * (journal.MAX_RECORD_BYTES + 1)):
            path.write_bytes(tampered)
            os.chmod(path, 0o600)
            self.refuses("corrupt-journal", self.inspect)

    def test_root_must_be_private_real_directory(self):
        loose = Path(self.temp.name) / "loose"
        loose.mkdir(mode=0o755)
        link = Path(self.temp.name) / "link"
        link.symlink_to(self.root)
        for root in (loose, link, Path(self.temp.name) / "missing", Path("relative"), str(self.root)):
            self.refuses("unsafe-root", journal.inspect_attempt, root, self.manifest,
                         attempt_id="attempt-1", now=NOW)
            self.refuses("unsafe-root", journal.begin_attempt, root, self.manifest,
                         attempt_id="attempt-1", reservation=self.reserve(), now=NOW)

    def test_journal_byte_and_attempt_budgets(self):
        small = Reservation(canonical({**json.loads(self.reserve().canonical_bytes),
                                       "reservedJournalBytes": 100}))
        self.refuses("journal-budget-exhausted", self.begin, reservation=small)
        self.assertEqual(self.names(), [])
        for index in range(journal.MAX_ATTEMPTS + 1):
            (self.root / f"a{index}.end.json").write_bytes(b"{}")
        self.refuses("journal-budget-exhausted", self.begin)

    def test_held_lock_and_unsafe_lock_refuse_without_state(self):
        import fcntl
        lock = os.open(self.root / ".lock", os.O_RDWR | os.O_CREAT, 0o600)
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            self.refuses("journal-busy", self.begin)
        finally:
            os.close(lock)
        os.write(os.open(self.root / ".lock", os.O_WRONLY), b"x")
        self.refuses("corrupt-journal", self.begin)
        self.assertEqual(self.names(), [])

    def test_concurrent_begins_have_one_winner(self):
        def attempt(index):
            try:
                self.begin(f"attempt-{index}", f"case-{index}")
                return True
            except journal.JournalError as exc:
                self.assertIn(exc.reason, ("journal-busy", "unreconciled-attempt"))
                return False
        with ThreadPoolExecutor(8) as pool:
            self.assertEqual(sum(pool.map(attempt, range(8))), 1)
        self.assertEqual(len(self.names()), 1)


class BoundaryTests(Base):
    def test_hostile_arguments_raise_only_the_domain_error(self):
        weird = (None, b"x", 1.5, True, object(), [], {}, "", "UPPER", "a" * 65, -1, 1 << 80)
        for value in weird:
            for call in (
                lambda v=value: journal.begin_attempt(self.root, v, attempt_id="attempt-1",
                                                      reservation=self.reserve(), now=NOW),
                lambda v=value: journal.begin_attempt(self.root, self.manifest, attempt_id=v,
                                                      reservation=self.reserve(), now=NOW),
                lambda v=value: journal.begin_attempt(self.root, self.manifest, attempt_id="attempt-1",
                                                      reservation=self.reserve(), now=v),
                lambda v=value: journal.checkpoint(self.root, self.manifest, attempt_id="attempt-1",
                                                   completed=v, pending=v, artifacts=v, now=NOW),
                lambda v=value: journal.finish_attempt(self.root, self.manifest,
                                                       attempt_id="attempt-1", result=v, now=NOW),
                lambda v=value: journal.inspect_attempt(v, self.manifest, attempt_id="attempt-1", now=NOW),
                lambda v=value: journal.reconcile_attempt(self.root, v, attempt_id="attempt-1", now=NOW),
            ):
                with self.assertRaises(journal.JournalError):
                    call()
        self.assertEqual(self.names(), [])

    def test_os_failure_while_writing_is_a_domain_error(self):
        from unittest import mock
        with mock.patch("agent_braid.harness_journal.os.fsync", side_effect=OSError(5, "x")):
            self.refuses("journal-io-failed", self.begin)

    def test_runner_refusal_after_start_leaves_attempt_open(self):
        with self.assertRaises(lab.LabError):
            journal.run_journaled(
                self.root, self.manifest, b"print(1)", attempt_id="attempt-1",
                reservation=self.reserve(), backend=lab.SimulatedContainment(),
                inventory=make_inventory(), now=NOW, retention_seconds=60)
        self.assertEqual(self.inspect().phase, "checkpointed")
        self.refuses("unreconciled-attempt", self.begin, "attempt-2", "case-2")


if __name__ == "__main__":
    unittest.main()
