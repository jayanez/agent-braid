# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T017: bounded --watch polling of artifact directories (procedure_006)."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import time
import unittest
from unittest import mock

from agent_braid import view_adapters, view_serve, view_tail
from agent_braid.view_loom import canonical_bytes, validate_event
from agent_braid.view_model import build_model
from agent_braid.view_store import LoomStore
from agent_braid.view_tail import ArtifactTail, TailError

FIXTURES = Path(__file__).resolve().parent / "fixtures/view/artifacts"


def install(root, name, fixture):
    target = Path(root) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(FIXTURES / fixture, target)
    return target


def kinds(store):
    return [event["kind"] for event in store.replay()]


def gaps(store):
    return [event for event in store.replay()
            if event["kind"] == "observation.gap" and event["data"]["reason"] == "stream-truncated"]


class TailCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.root = self.base / "root"
        self.root.mkdir()
        self.outside = self.base / "outside"
        self.outside.mkdir()
        self.store = LoomStore()

    def tail(self, *roots, **kwargs):
        return ArtifactTail(self.store, list(roots or [self.root]), **kwargs)


class ContractBoundTests(unittest.TestCase):
    def test_the_bounds_are_the_contract_values(self):
        self.assertEqual((view_tail.MAX_ROOTS, view_tail.MAX_ENTRIES, view_tail.POLL_SECONDS), (8, 4096, 0.5))
        self.assertEqual(view_adapters.MAX_ARTIFACT_BYTES, 16 * 1024 * 1024)
        self.assertEqual(ArtifactTail.__init__.__kwdefaults__["max_file_bytes"], 16 * 1024 * 1024)

    def test_every_known_name_maps_to_an_adapter_and_state_json_is_the_runtime_file(self):
        self.assertEqual(len(set(view_tail.KNOWN_ARTIFACTS.values())), len(view_tail.KNOWN_ARTIFACTS))
        self.assertIn("state.json", view_tail.KNOWN_ARTIFACTS)
        self.assertTrue(all(name.endswith(".json") and "/" not in name for name in view_tail.KNOWN_ARTIFACTS))


class IngestTests(TailCase):
    def test_a_known_artifact_becomes_rehashed_adapter_events(self):
        path = install(self.root, "state.json", "runtime-state-ready.json")
        self.assertEqual(self.tail().poll_once(), 1)
        (event,) = self.store.replay()
        self.assertEqual(event["kind"], "runtime.phase")
        self.assertEqual(event["source"]["verification"], "rehashed")
        self.assertEqual(event["source"]["evidenceRef"],
                         {"path": "state.json", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        self.assertIs(event["executionAuthorization"], False)

    def test_unknown_names_are_ignored(self):
        install(self.root, "notes.json", "runtime-state-ready.json")
        install(self.root, "analysis-file-edits.json", "analysis-file-edits.json")
        install(self.root, "State.json", "runtime-state-ready.json")
        self.assertEqual(self.tail().poll_once(), 0)
        self.assertEqual(self.store.stats()["headSeq"], 0)

    def test_nested_artifacts_get_a_root_relative_posix_evidence_path_in_sorted_order(self):
        install(self.root, "runs/b/state.json", "runtime-state-ready.json")
        install(self.root, "runs/a/state.json", "runtime-state-completed.json")
        install(self.root, "state.json", "runtime-state-ready.json")
        self.tail().poll_once()
        paths = [event["source"]["evidenceRef"]["path"] for event in self.store.replay()]
        self.assertEqual(sorted(paths), sorted(["state.json", "runs/a/state.json", "runs/b/state.json"]))
        self.assertEqual(paths, ["state.json", "runs/a/state.json", "runs/b/state.json"])

    def test_every_family_is_read_by_its_own_adapter(self):
        names = {
            "analysis.json": "analysis-file-edits.json", "git-replay-plan.json": "git-replay-plan.json",
            "scheduler-preparation.json": "scheduler-preparation.json", "operator-grant.json": "grant-issued.json",
            "state.json": "runtime-state-ready.json", "hazard-notice.json": "hazard-notice-preflight.json",
            "ownership-receipt.json": "ownership-receipt-hazards.json", "gate-result.json": "gate-result-certified.json",
        }
        self.assertEqual(set(names), set(view_tail.KNOWN_ARTIFACTS))
        for name, fixture in names.items():
            install(self.root, name, fixture)
        self.tail(wall_clock=lambda: 1793603993).poll_once()  # before the grant's expiry
        adapters = {event["source"]["adapter"] for event in self.store.replay()}
        self.assertEqual(adapters, {"analysis-report", "git-replay-plan", "scheduler-preparation", "runtime-grant",
                                    "runtime-state", "ownership-notice", "ownership-receipt", "workflow-gate"})
        for event in self.store.replay():
            validate_event(event)
            self.assertEqual(event["source"]["verification"], "rehashed")

    def test_an_unchanged_file_is_not_stored_again_and_a_touched_one_adds_nothing(self):
        path = install(self.root, "state.json", "runtime-state-ready.json")
        tail = self.tail()
        self.assertEqual(tail.poll_once(), 1)
        self.assertEqual(tail.poll_once(), 0)
        later = time.time() + 5
        os.utime(path, (later, later))
        self.assertEqual(tail.poll_once(), 0)
        self.assertEqual(self.store.stats()["headSeq"], 1)

    def test_a_changed_file_is_stored_again_under_its_new_hash(self):
        path = install(self.root, "state.json", "runtime-state-ready.json")
        tail = self.tail()
        tail.poll_once()
        shutil.copyfile(FIXTURES / "runtime-state-completed.json", path)
        self.assertEqual(tail.poll_once(), 1)
        first, second = self.store.replay()
        self.assertNotEqual(first["source"]["evidenceRef"]["sha256"], second["source"]["evidenceRef"]["sha256"])
        self.assertEqual(second["source"]["evidenceRef"]["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_a_file_that_appears_later_is_picked_up(self):
        tail = self.tail()
        self.assertEqual(tail.poll_once(), 0)
        install(self.root, "runs/x/state.json", "runtime-state-ready.json")
        self.assertEqual(tail.poll_once(), 1)

    def test_unreadable_content_is_a_source_unsupported_gap_not_a_crash(self):
        (self.root / "state.json").write_bytes(b"{not json")
        self.assertEqual(self.tail().poll_once(), 1)
        (event,) = self.store.replay()
        self.assertEqual((event["kind"], event["data"]["reason"]), ("observation.gap", "source-unsupported"))

    def test_the_grant_adapter_gets_the_viewer_clock(self):
        install(self.root, "operator-grant.json", "grant-issued.json")
        self.tail(wall_clock=lambda: 1793604293 + 10).poll_once()
        self.assertEqual(kinds(self.store), ["grant.issued", "grant.expired"])
        other = LoomStore()
        ArtifactTail(other, [self.root], wall_clock=lambda: 1793603993).poll_once()
        self.assertEqual([e["kind"] for e in other.replay()], ["grant.issued"])

    def test_the_tail_writes_nothing_under_the_watched_roots(self):
        install(self.root, "runs/a/state.json", "runtime-state-ready.json")
        install(self.root, "analysis.json", "analysis-file-edits.json")

        def snapshot():
            return sorted((str(p.relative_to(self.root)), p.stat().st_mtime_ns, p.stat().st_size)
                          for p in self.root.rglob("*"))
        before = snapshot()
        tail = self.tail()
        tail.poll_once()
        tail.poll_once()
        self.assertEqual(snapshot(), before)

    def test_a_recorded_copy_of_the_watched_events_replays_to_the_same_model_shape(self):
        install(self.root, "analysis.json", "analysis-file-edits.json")
        install(self.root, "runs/a/state.json", "runtime-state-completed.json")
        self.tail().poll_once()
        recorded = b"".join(canonical_bytes(event) for event in self.store.replay())
        replayed = LoomStore()
        view_serve.load_replay(replayed, recorded)
        live, again = build_model(self.store.replay()), build_model(replayed.replay())
        self.assertEqual(live["eventCount"], again["eventCount"])
        self.assertEqual([(e["element"], e["seq"]) for e in live["elements"]],
                         [(e["element"], e["seq"]) for e in again["elements"]])
        self.assertEqual(live["counters"]["unverifiedElements"], 0)
        self.assertEqual(again["counters"]["unverifiedElements"], len(again["elements"]))


class SymbolicLinkTests(TailCase):
    def test_a_symlink_to_a_file_outside_the_root_under_a_known_name_is_not_read(self):
        install(self.outside, "secret.json", "runtime-state-ready.json")
        (self.root / "state.json").symlink_to(self.outside / "secret.json")
        with mock.patch.object(view_tail, "read_artifact", wraps=view_tail.read_artifact) as reader:
            self.assertEqual(self.tail().poll_once(), 0)
        reader.assert_not_called()
        self.assertEqual(self.store.stats()["headSeq"], 0)

    def test_a_symlink_to_a_file_inside_the_root_is_not_read_either(self):
        install(self.root, "real.json", "runtime-state-ready.json")
        (self.root / "state.json").symlink_to(self.root / "real.json")
        self.assertEqual(self.tail().poll_once(), 0)

    def test_a_symlinked_directory_is_not_entered(self):
        install(self.outside, "state.json", "runtime-state-ready.json")
        (self.root / "linked").symlink_to(self.outside, target_is_directory=True)
        self.assertEqual(self.tail().poll_once(), 0)
        self.assertEqual(self.store.stats()["headSeq"], 0)

    def test_a_link_swapped_in_after_the_scan_is_refused_by_the_reader(self):
        target = install(self.root, "state.json", "runtime-state-ready.json")
        install(self.outside, "state.json", "runtime-state-completed.json")
        tail = self.tail()
        real_walk = tail._walk

        def swap(root, budget):
            found = list(real_walk(root, budget))
            target.unlink()
            target.symlink_to(self.outside / "state.json")
            return iter(found)
        tail._walk = swap
        self.assertEqual(tail.poll_once(), 0)
        self.assertEqual(self.store.stats()["headSeq"], 0)

    def test_a_symlink_as_the_watched_root_is_resolved_once_at_start(self):
        install(self.outside, "state.json", "runtime-state-ready.json")
        link = self.base / "link"
        link.symlink_to(self.outside, target_is_directory=True)
        tail = self.tail(link)
        self.assertEqual(tail.poll_once(), 1)

    def test_a_fifo_under_a_known_name_is_not_opened(self):
        os.mkfifo(self.root / "state.json")
        self.assertEqual(self.tail().poll_once(), 0)


class BoundTests(TailCase):
    def test_more_than_eight_roots_watch_the_first_eight_and_store_one_gap(self):
        roots = []
        for index in range(10):
            root = self.base / f"r{index}"
            root.mkdir()
            install(root, "state.json", "runtime-state-ready.json")
            roots.append(root)
        tail = self.tail(*roots)
        tail.poll_once()
        self.assertEqual(kinds(self.store).count("runtime.phase"), 8)
        self.assertEqual(len(gaps(self.store)), 1)
        tail.poll_once()
        self.assertEqual(len(gaps(self.store)), 1)

    def test_eight_roots_are_within_the_bound(self):
        roots = []
        for index in range(8):
            root = self.base / f"r{index}"
            root.mkdir()
            roots.append(root)
        self.tail(*roots).poll_once()
        self.assertEqual(gaps(self.store), [])

    def test_the_same_root_named_twice_counts_once(self):
        install(self.root, "state.json", "runtime-state-ready.json")
        self.assertEqual(self.tail(self.root, self.root, self.base / "root" / ".." / "root").poll_once(), 1)

    def test_entries_beyond_the_bound_are_not_read_and_make_one_gap(self):
        for index in range(6):
            install(self.root, f"d{index}/state.json", "runtime-state-ready.json")
        tail = self.tail(max_entries=8)
        tail.poll_once()
        self.assertEqual(kinds(self.store).count("runtime.phase"), 2)  # 6 directories, then 2 files fit the 8
        self.assertEqual(len(gaps(self.store)), 1)
        tail.poll_once()
        self.assertEqual(len(gaps(self.store)), 1)  # reported once while the bound stays exceeded
        self.assertEqual(kinds(self.store).count("runtime.phase"), 2)

    def test_a_bound_that_clears_and_is_exceeded_again_is_reported_again(self):
        for index in range(4):
            install(self.root, f"f{index}/state.json", "runtime-state-ready.json")
        tail = self.tail(max_entries=5)
        tail.poll_once()
        self.assertEqual(len(gaps(self.store)), 1)
        for index in range(2, 4):
            shutil.rmtree(self.root / f"f{index}")
        tail.poll_once()
        self.assertEqual(len(gaps(self.store)), 1)
        for index in range(2, 4):
            install(self.root, f"f{index}/state.json", "runtime-state-ready.json")
        tail.poll_once()
        self.assertEqual(len(gaps(self.store)), 2)

    def test_entries_are_bounded_across_all_roots(self):
        second = self.base / "second"
        second.mkdir()
        for index in range(3):
            install(self.root, f"a{index}/state.json", "runtime-state-ready.json")
            install(second, f"b{index}/state.json", "runtime-state-ready.json")
        self.tail(self.root, second, max_entries=7).poll_once()
        self.assertEqual(len(gaps(self.store)), 1)
        self.assertLess(kinds(self.store).count("runtime.phase"), 6)

    def test_a_file_over_the_size_bound_is_not_read_and_makes_one_gap(self):
        path = install(self.root, "state.json", "runtime-state-ready.json")
        size = path.stat().st_size
        tail = self.tail(max_file_bytes=size - 1)
        with mock.patch.object(view_tail, "read_artifact", wraps=view_tail.read_artifact) as reader:
            tail.poll_once()
            tail.poll_once()
        reader.assert_not_called()
        self.assertEqual(kinds(self.store), ["observation.gap"])
        self.assertEqual(len(gaps(self.store)), 1)

    def test_an_oversized_file_that_keeps_changing_adds_one_gap(self):
        path = install(self.root, "state.json", "runtime-state-ready.json")
        tail = self.tail(max_file_bytes=path.stat().st_size - 1)
        tail.poll_once()
        path.write_bytes(path.read_bytes() + b" ")
        tail.poll_once()
        path.write_bytes(path.read_bytes() + b" ")
        tail.poll_once()
        self.assertEqual(len(gaps(self.store)), 1)

    def test_a_root_inside_another_root_is_not_watched_twice(self):
        install(self.root, "sub/state.json", "runtime-state-ready.json")
        self.assertEqual(self.tail(self.root / "sub", self.root).poll_once(), 1)
        self.assertEqual(self.tail(self.root, self.root / "sub").poll_once(), 1)

    def test_a_huge_directory_is_listed_only_up_to_the_bound(self):
        for index in range(50):
            (self.root / f"f{index:03d}").write_text("x")
        tail = self.tail(max_entries=5)
        with mock.patch.object(view_tail, "islice", wraps=view_tail.islice) as limited:
            tail.poll_once()
        self.assertEqual(limited.call_args[0][1], 6)
        self.assertEqual(len(gaps(self.store)), 1)

    def test_a_file_at_the_size_bound_is_read(self):
        path = install(self.root, "state.json", "runtime-state-ready.json")
        self.assertEqual(self.tail(max_file_bytes=path.stat().st_size).poll_once(), 1)
        self.assertEqual(gaps(self.store), [])

    def test_an_oversized_file_that_shrinks_is_read_afterwards(self):
        path = install(self.root, "state.json", "runtime-state-completed.json")
        tail = self.tail(max_file_bytes=path.stat().st_size - 1)
        tail.poll_once()
        self.assertEqual(kinds(self.store), ["observation.gap"])
        shutil.copyfile(FIXTURES / "runtime-state-ready.json", path)
        self.assertEqual(tail.poll_once(), 1)
        self.assertEqual(kinds(self.store), ["observation.gap", "runtime.phase"])

    def test_a_file_that_grows_past_the_bound_while_being_read_is_skipped(self):
        install(self.root, "state.json", "runtime-state-ready.json")
        tail = self.tail()
        with mock.patch.object(view_tail, "read_artifact", side_effect=view_adapters.AdapterError("grew")):
            self.assertEqual(tail.poll_once(), 0)
        self.assertEqual(self.store.stats()["headSeq"], 0)

    def test_the_gap_is_a_derived_stream_truncated_observation(self):
        for index in range(3):
            install(self.root, f"d{index}/state.json", "runtime-state-ready.json")
        self.tail(max_entries=2).poll_once()
        (gap,) = gaps(self.store)
        self.assertEqual(gap["source"]["verification"], "derived")
        self.assertEqual(gap["source"]["adapter"], "viewer")
        self.assertIsNone(gap["source"]["evidenceRef"])
        self.assertEqual(gap["at"]["basis"], "viewer-monotonic")

    def test_an_unreadable_directory_does_not_stop_the_scan(self):
        install(self.root, "ok/state.json", "runtime-state-ready.json")
        locked = self.root / "locked"
        locked.mkdir()
        locked.chmod(0)
        self.addCleanup(locked.chmod, 0o700)
        self.tail().poll_once()
        self.assertEqual(kinds(self.store), ["runtime.phase"])


class ConstructionTests(TailCase):
    def test_roots_must_exist_and_be_directories(self):
        (self.base / "file").write_text("x")
        for root in (self.base / "missing", self.base / "file"):
            with self.subTest(root=root.name), self.assertRaises(TailError) as caught:
                self.tail(root)
            self.assertEqual(caught.exception.reason, "root")

    def test_limits_must_be_positive(self):
        for kwargs in ({"interval": 0}, {"max_roots": 0}, {"max_entries": 0}, {"max_file_bytes": 0}):
            with self.subTest(**kwargs), self.assertRaises(ValueError):
                self.tail(**kwargs)


class ThreadTests(TailCase):
    def wait_for(self, predicate, limit=5.0):
        deadline = time.monotonic() + limit
        while not predicate() and time.monotonic() < deadline:
            time.sleep(0.01)
        return predicate()

    def test_the_background_thread_polls_until_stopped(self):
        with self.tail(interval=0.02):
            install(self.root, "state.json", "runtime-state-ready.json")
            self.assertTrue(self.wait_for(lambda: self.store.stats()["headSeq"] == 1))
            install(self.root, "runs/y/state.json", "runtime-state-completed.json")
            self.assertTrue(self.wait_for(lambda: self.store.stats()["headSeq"] == 2))
        head = self.store.stats()["headSeq"]
        install(self.root, "runs/z/state.json", "runtime-state-completed.json")
        time.sleep(0.2)
        self.assertEqual(self.store.stats()["headSeq"], head)

    def test_a_failing_scan_does_not_kill_the_thread(self):
        tail = self.tail(interval=0.02)
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("boom")
            return 0
        tail.poll_once = flaky
        with tail:
            self.assertTrue(self.wait_for(lambda: len(calls) >= 3))

    def test_start_twice_is_refused_and_stop_is_idempotent(self):
        tail = self.tail(interval=0.02)
        tail.start()
        with self.assertRaises(RuntimeError):
            tail.start()
        tail.stop()
        tail.stop()

    def test_the_default_interval_is_half_a_second(self):
        self.assertEqual(self.tail().interval, 0.5)


if __name__ == "__main__":
    unittest.main()
