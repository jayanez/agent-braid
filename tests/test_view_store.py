# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T015: in-memory loom ring, seq assignment, caps, eviction gaps and subscribers."""
from copy import deepcopy
from pathlib import Path
import threading
import unittest

from agent_braid import view_loom
from agent_braid.view_loom import LoomError, validate_event
from agent_braid.view_store import LoomStore, StoreError, SubscriberDropped


def event(kind="strand.update", data=None, seq=1, **extra):
    base = {
        "schemaVersion": view_loom.SCHEMA_VERSION, "seq": seq, "kind": kind,
        "at": {"relMs": 0, "basis": "viewer-monotonic"},
        "source": {"adapter": "viewer", "evidenceRef": None, "host": "braid", "verification": "derived"},
        "assurance": {"compatibilityClass": None, "notAGuarantee": True},
        "executionAuthorization": False,
        "data": data if data is not None else {"strandId": "s1", "state": "running", "toolName": None},
    }
    base.update(extra)
    return base


def strand_open(strand_id):
    return event("strand.open", {"strandId": strand_id, "host": "claude", "role": "agent",
                                 "label": "x", "parentStrandId": None})


def crossing(index):
    return event("crossing.classified", {
        "reportId": "r1", "left": f"a{index}", "right": f"b{index}", "classification": "unknown",
        "sharedResources": [], "reasons": [], "constraints": [],
        "evidence": {"method": "m", "coverage": ["unknown"], "ruleSet": "r"}},
        assurance={"compatibilityClass": 1, "notAGuarantee": True})


def wave(kind, schedule, number):
    return event(kind, {"scheduleId": schedule, "wave": number, "strands": ["s1"]})


def grant(kind, grant_id):
    return event(kind, {"grantId": grant_id, "action": "execute", "derived": False})


def fill(store, count):
    for _ in range(count):
        store.append(event())


def gaps(items):
    return [item for item in items if item["kind"] == "observation.gap"]


class AppendTests(unittest.TestCase):
    def test_seq_is_assigned_monotonically_from_one_whatever_the_input_says(self):
        store = LoomStore()
        stored = [store.append(event(seq=seq)) for seq in (900, 3, 3)]
        self.assertEqual([item["seq"] for item in stored], [1, 2, 3])
        self.assertEqual([item["seq"] for item in store.replay()], [1, 2, 3])

    def test_caller_event_is_not_mutated_or_aliased(self):
        store = LoomStore()
        original = event(seq=77)
        before = deepcopy(original)
        stored = store.append(original)
        self.assertEqual(original, before)
        original["data"]["state"] = "idle"
        self.assertEqual(store.replay()[0]["data"]["state"], "running")
        self.assertIsNot(stored, original)

    def test_stored_events_are_valid_contract_events(self):
        store = LoomStore()
        store.append(event())
        validate_event(store.replay()[0])

    def test_invalid_event_is_refused_and_consumes_no_seq(self):
        store = LoomStore()
        bad = event()
        bad["executionAuthorization"] = True
        with self.assertRaises(LoomError) as raised:
            store.append(bad)
        self.assertEqual(raised.exception.reason, "execution-authorization")
        self.assertEqual(store.append(event())["seq"], 1)
        self.assertEqual(store.stats()["count"], 1)

    def test_non_dict_is_refused(self):
        with self.assertRaises(LoomError):
            LoomStore().append("not an event")

    def test_constructor_rejects_bad_bounds(self):
        for kwargs in ({"max_events": 0}, {"max_events": view_loom.MAX_EVENTS + 1},
                       {"max_subscribers": 0}, {"subscriber_queue": 0}):
            with self.assertRaises(ValueError, msg=str(kwargs)):
                LoomStore(**kwargs)

    def test_defaults_follow_the_contract(self):
        stats = LoomStore().stats()
        self.assertEqual(stats["limits"], {"events": 50_000, "strands": 256, "crossings": 4096,
                                           "waves": 64, "grants": 1024, "subscribers": 8})

    def test_concurrent_producers_get_unique_contiguous_seq(self):
        store = LoomStore()
        seen = []
        guard = threading.Lock()

        def produce():
            for _ in range(200):
                stored = store.append(event())
                with guard:
                    seen.append(stored["seq"])

        threads = [threading.Thread(target=produce) for _ in range(8)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(seen), list(range(1, 1601)))
        self.assertEqual([item["seq"] for item in store.replay()], list(range(1, 1601)))


class EvictionTests(unittest.TestCase):
    def test_ring_never_exceeds_its_bound_and_keeps_the_newest(self):
        store = LoomStore(max_events=5)
        fill(store, 12)
        stats = store.stats()
        self.assertEqual((stats["count"], stats["oldestSeq"], stats["headSeq"], stats["evicted"]), (5, 8, 12, 7))
        self.assertEqual([item["seq"] for item in store.replay(after_seq=7)], [8, 9, 10, 11, 12])

    def test_replay_from_the_start_announces_the_evicted_range_once(self):
        store = LoomStore(max_events=5)
        fill(store, 12)
        items = store.replay()
        gap, rest = items[0], items[1:]
        validate_event(gap)
        self.assertEqual(gap["kind"], "observation.gap")
        self.assertEqual(gap["data"], {"reason": "ring-evicted", "strandId": None, "fromSeq": 1, "toSeq": 7})
        self.assertEqual(gap["seq"], 7)
        self.assertEqual(gap["source"]["verification"], "derived")
        self.assertEqual([item["seq"] for item in rest], [8, 9, 10, 11, 12])
        self.assertEqual(len(gaps(items)), 1)

    def test_replay_gap_covers_only_what_the_client_missed(self):
        store = LoomStore(max_events=5)
        fill(store, 12)
        gap = store.replay(after_seq=4)[0]
        self.assertEqual((gap["data"]["fromSeq"], gap["data"]["toSeq"]), (5, 7))

    def test_no_gap_when_the_client_is_contiguous_with_the_ring(self):
        store = LoomStore(max_events=5)
        fill(store, 12)
        for after in (7, 8, 11):
            self.assertEqual(gaps(store.replay(after_seq=after)), [])
        self.assertEqual(store.replay(after_seq=12), [])

    def test_resume_beyond_the_newest_event_is_refused_not_silently_skipped(self):
        store = LoomStore()
        fill(store, 5)
        for call in (lambda: store.replay(after_seq=6), lambda: store.subscribe(after_seq=99)):
            with self.assertRaises(StoreError) as raised:
                call()
            self.assertEqual(raised.exception.reason, "resume-ahead")
        self.assertEqual(store.stats()["subscribers"], 0)

    def test_append_returns_a_copy_that_cannot_corrupt_the_ring(self):
        store = LoomStore()
        stored = store.append(event())
        stored["seq"] = 999
        self.assertEqual([item["seq"] for item in store.replay()], [1])

    def test_no_gap_before_any_eviction(self):
        store = LoomStore(max_events=5)
        fill(store, 5)
        self.assertEqual([item["seq"] for item in store.replay()], [1, 2, 3, 4, 5])
        self.assertEqual(gaps(store.replay()), [])

    def test_resume_delivers_each_retained_event_exactly_once_in_order(self):
        store = LoomStore(max_events=50)
        fill(store, 30)
        first = store.replay()[:10]
        rest = store.replay(after_seq=first[-1]["seq"])
        self.assertEqual([item["seq"] for item in first + rest], list(range(1, 31)))

    def test_gap_seq_chains_into_the_next_resume(self):
        store = LoomStore(max_events=5)
        fill(store, 12)
        gap = store.replay(after_seq=2)[0]
        again = store.replay(after_seq=gap["seq"])
        self.assertEqual([item["seq"] for item in again], [8, 9, 10, 11, 12])

    def test_replay_limit_and_validation(self):
        store = LoomStore()
        fill(store, 10)
        self.assertEqual([item["seq"] for item in store.replay(after_seq=2, limit=3)], [3, 4, 5])
        for bad in (-1, 1.5, "1", True, None):
            with self.assertRaises(ValueError, msg=repr(bad)):
                store.replay(after_seq=bad)
        with self.assertRaises(ValueError):
            store.replay(limit=0)

    def test_eviction_of_a_stored_gap_is_still_announced(self):
        store = LoomStore(max_events=3)
        store.append(event("observation.gap", {"reason": "not-observed", "strandId": None,
                                               "fromSeq": None, "toSeq": None}))
        fill(store, 5)
        gap = store.replay()[0]
        self.assertEqual(gap["data"]["reason"], "ring-evicted")
        self.assertEqual((gap["data"]["fromSeq"], gap["data"]["toSeq"]), (1, 3))

    def test_full_size_ring_evicts_at_the_contract_bound(self):
        store = LoomStore()
        fill(store, view_loom.MAX_EVENTS + 3)
        stats = store.stats()
        self.assertEqual((stats["count"], stats["oldestSeq"], stats["evicted"]), (50_000, 4, 3))


class CapTests(unittest.TestCase):
    def test_strand_cap_refuses_with_one_stream_truncated_gap(self):
        store = LoomStore()
        for index in range(256):
            self.assertIsNotNone(store.append(strand_open(f"s{index}")))
        head = store.stats()["headSeq"]
        self.assertIsNone(store.append(strand_open("over1")))
        self.assertIsNone(store.append(strand_open("over2")))
        items = store.replay(after_seq=head)
        self.assertEqual(len(items), 1, "one gap per exhausted cap, not one per refusal")
        validate_event(items[0])
        self.assertEqual(items[0]["data"], {"reason": "stream-truncated", "strandId": None,
                                            "fromSeq": None, "toSeq": None})
        self.assertEqual(store.stats()["refused"], {"strands": 2})

    def test_crossing_cap(self):
        store = LoomStore()
        for index in range(4096):
            self.assertIsNotNone(store.append(crossing(index)))
        self.assertIsNone(store.append(crossing(4096)))
        self.assertEqual(store.stats()["refused"], {"crossings": 1})

    def test_wave_cap_counts_distinct_schedule_wave_pairs(self):
        store = LoomStore()
        for number in range(64):
            self.assertIsNotNone(store.append(wave("wave.started", "sch1", number)))
        self.assertIsNotNone(store.append(wave("wave.finished", "sch1", 3)))
        self.assertIsNotNone(store.append(wave("wave.started", "sch1", 3)))
        self.assertIsNone(store.append(wave("wave.started", "sch2", 0)))
        self.assertIsNone(store.append(wave("wave.finished", "sch2", 0)))
        self.assertEqual(store.stats()["refused"], {"waves": 2})

    def test_grant_cap_counts_distinct_grants_across_grant_kinds(self):
        store = LoomStore()
        for index in range(1024):
            self.assertIsNotNone(store.append(grant("grant.issued", f"g{index}")))
        self.assertIsNotNone(store.append(grant("grant.consumed", "g5")))
        self.assertIsNone(store.append(grant("grant.issued", "g-new")))
        self.assertIsNone(store.append(grant("grant.refused", "g-new")))
        self.assertEqual(store.stats()["refused"], {"grants": 2})

    def test_repeat_of_a_known_strand_is_not_a_new_strand(self):
        store = LoomStore()
        for index in range(256):
            store.append(strand_open(f"s{index}"))
        self.assertIsNotNone(store.append(strand_open("s0")))
        self.assertIsNone(store.append(strand_open("extra")))

    def test_uncapped_kinds_flow_when_a_cap_is_full(self):
        store = LoomStore()
        for index in range(256):
            store.append(strand_open(f"s{index}"))
        store.append(strand_open("extra"))
        self.assertIsNotNone(store.append(event()))

    def test_independent_caps_each_announce_once(self):
        store = LoomStore()
        for index in range(256):
            store.append(strand_open(f"s{index}"))
        for index in range(4096):
            store.append(crossing(index))
        for attempt in range(3):
            store.append(strand_open(f"x{attempt}"))
            store.append(crossing(5000 + attempt))
        self.assertEqual(len(gaps(store.replay())), 2)
        self.assertEqual(store.stats()["refused"], {"strands": 3, "crossings": 3})

    def test_invalid_event_is_a_validation_error_before_any_cap_is_consulted(self):
        store = LoomStore(caps={"strands": 1})
        store.append(strand_open("a"))
        bad = strand_open("b")
        bad["data"]["role"] = "overlord"
        with self.assertRaises(LoomError):
            store.append(bad)
        self.assertEqual(store.stats()["refused"], {})

    def test_caps_may_be_tightened_but_not_raised(self):
        store = LoomStore(caps={"strands": 2})
        store.append(strand_open("a"))
        store.append(strand_open("b"))
        self.assertIsNone(store.append(strand_open("c")))
        with self.assertRaises(ValueError):
            LoomStore(caps={"strands": 257})
        with self.assertRaises(ValueError):
            LoomStore(caps={"nonsense": 1})
        with self.assertRaises(ValueError):
            LoomStore(caps={"strands": "2"})


class SubscriberTests(unittest.TestCase):
    def test_subscriber_limit_is_eight_and_slots_are_reusable(self):
        store = LoomStore()
        subscribers = [store.subscribe() for _ in range(8)]
        with self.assertRaises(StoreError) as raised:
            store.subscribe()
        self.assertEqual(raised.exception.reason, "subscriber-limit")
        self.assertEqual(store.stats()["subscribers"], 8)
        subscribers[0].close()
        subscribers[0].close()  # idempotent
        self.assertEqual(store.stats()["subscribers"], 7)
        store.subscribe()

    def test_live_subscriber_receives_new_events_in_order(self):
        store = LoomStore()
        fill(store, 3)
        subscriber = store.subscribe()
        self.assertIsNone(subscriber.get(timeout=0))
        fill(store, 2)
        self.assertEqual([subscriber.get(timeout=0)["seq"] for _ in range(2)], [4, 5])
        self.assertIsNone(subscriber.get(timeout=0))

    def test_subscribe_after_seq_replays_backlog_then_goes_live_without_loss_or_duplicates(self):
        store = LoomStore()
        fill(store, 6)
        subscriber = store.subscribe(after_seq=2)
        fill(store, 2)
        self.assertEqual([subscriber.get(timeout=0)["seq"] for _ in range(6)], [3, 4, 5, 6, 7, 8])
        self.assertIsNone(subscriber.get(timeout=0))

    def test_backlog_is_exempt_from_the_slow_consumer_bound(self):
        store = LoomStore(subscriber_queue=3)
        fill(store, 10)
        subscriber = store.subscribe(after_seq=0)
        fill(store, 2)
        self.assertEqual([subscriber.get(timeout=0)["seq"] for _ in range(12)], list(range(1, 13)))

    def test_resume_behind_the_ring_yields_the_gap_first(self):
        store = LoomStore(max_events=5)
        fill(store, 12)
        subscriber = store.subscribe(after_seq=3)
        first = subscriber.get(timeout=0)
        self.assertEqual((first["kind"], first["data"]["fromSeq"], first["data"]["toSeq"]),
                         ("observation.gap", 4, 7))
        self.assertEqual([subscriber.get(timeout=0)["seq"] for _ in range(5)], [8, 9, 10, 11, 12])

    def test_live_subscriber_overtaken_by_eviction_sees_a_gap_not_silence(self):
        store = LoomStore(max_events=4, subscriber_queue=100)
        subscriber = store.subscribe()
        fill(store, 10)
        first = subscriber.get(timeout=0)
        self.assertEqual((first["data"]["reason"], first["data"]["fromSeq"], first["data"]["toSeq"]),
                         ("ring-evicted", 1, 6))
        self.assertEqual([subscriber.get(timeout=0)["seq"] for _ in range(4)], [7, 8, 9, 10])

    def test_slow_subscriber_is_dropped_not_blocking_the_producer(self):
        store = LoomStore(subscriber_queue=3)
        slow = store.subscribe()
        fast = store.subscribe()
        for _ in range(3):
            store.append(event())
            fast.get(timeout=0)
        store.append(event())  # fourth unread event for `slow` exceeds its bound of 3
        self.assertEqual(store.stats()["subscribers"], 1)
        with self.assertRaises(SubscriberDropped) as raised:
            slow.get(timeout=0)
        self.assertEqual(raised.exception.last_seq, 0)
        self.assertEqual(fast.get(timeout=0)["seq"], 4)

    def test_dropped_subscriber_reports_what_it_consumed_and_can_resume_losslessly(self):
        store = LoomStore(subscriber_queue=2)
        slow = store.subscribe()
        store.append(event())
        slow.get(timeout=0)
        fill(store, 3)
        with self.assertRaises(SubscriberDropped) as raised:
            slow.get(timeout=0)
        self.assertEqual(raised.exception.last_seq, 1)
        resume = store.subscribe(after_seq=raised.exception.last_seq)
        self.assertEqual([resume.get(timeout=0)["seq"] for _ in range(3)], [2, 3, 4])

    def test_drop_frees_the_slot_for_a_new_subscriber(self):
        store = LoomStore(subscriber_queue=1, max_subscribers=1)
        store.subscribe()
        fill(store, 2)
        self.assertEqual(store.stats()["subscribers"], 0)
        store.subscribe()

    def test_closed_subscriber_gets_nothing_and_raises(self):
        store = LoomStore()
        subscriber = store.subscribe()
        subscriber.close()
        store.append(event())
        with self.assertRaises(SubscriberDropped):
            subscriber.get(timeout=0)

    def test_context_manager_closes(self):
        store = LoomStore()
        with store.subscribe():
            self.assertEqual(store.stats()["subscribers"], 1)
        self.assertEqual(store.stats()["subscribers"], 0)

    def test_get_blocks_until_an_event_arrives(self):
        store = LoomStore()
        subscriber = store.subscribe()
        threading.Timer(0.05, lambda: store.append(event())).start()
        self.assertEqual(subscriber.get(timeout=5)["seq"], 1)

    def test_get_times_out_with_none(self):
        self.assertIsNone(LoomStore().subscribe().get(timeout=0.01))

    def test_blocked_get_wakes_when_closed(self):
        store = LoomStore()
        subscriber = store.subscribe()
        outcome = []

        def consume():
            try:
                subscriber.get(timeout=5)
            except SubscriberDropped as exc:
                outcome.append(exc)

        thread = threading.Thread(target=consume)
        thread.start()
        threading.Timer(0.05, subscriber.close).start()
        thread.join(5)
        self.assertEqual(len(outcome), 1)

    def test_subscribe_after_seq_validation(self):
        with self.assertRaises(ValueError):
            LoomStore().subscribe(after_seq=-2)

    def test_producers_never_block_on_a_stalled_subscriber(self):
        store = LoomStore(max_events=100, subscriber_queue=10)
        store.subscribe()
        done = threading.Event()

        def produce():
            fill(store, 5000)
            done.set()

        threading.Thread(target=produce, daemon=True).start()
        self.assertTrue(done.wait(10))
        self.assertEqual(store.stats()["subscribers"], 0)


class ReadOnlyTests(unittest.TestCase):
    def test_module_has_no_file_or_ownership_surface(self):
        source = (Path(__file__).resolve().parents[1] / "agent_braid/view_store.py").read_text(encoding="utf-8")
        for token in ("open(", "write_text", "write_bytes", "ownership", "subprocess", "import os", "socket"):
            self.assertNotIn(token, source, token)

    def test_stored_events_keep_execution_authorization_false(self):
        store = LoomStore()
        store.append(event())
        self.assertTrue(all(item["executionAuthorization"] is False for item in store.replay()))


if __name__ == "__main__":
    unittest.main()
