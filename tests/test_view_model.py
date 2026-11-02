# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T020: the pure viewer model (lanes, swaps, time axis, waves, markers, counters)."""
from copy import deepcopy
import json
from pathlib import Path
import unittest

from agent_braid import view_loom, view_model
from agent_braid.view_loom import LoomError
from agent_braid.view_model import build_model

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "specs/061-activity-viewer/contracts/loom-event.example.jsonl"
REPORT = "sha256:" + "a" * 64
PLAN = "sha256:" + "b" * 64
REF = {"path": "runs/x/a.json", "sha256": "1" * 64}

def ev(seq, kind, data, *, ms=None, cls=None, verification="rehashed", host="braid",
       basis="artifact-relative", ref=REF):
    return {
        "schemaVersion": view_loom.SCHEMA_VERSION, "seq": seq, "kind": kind,
        "at": {"relMs": seq * 100 if ms is None else ms, "basis": basis},
        "source": {"adapter": "analysis-report", "evidenceRef": deepcopy(ref), "host": host,
                   "verification": verification},
        "assurance": {"compatibilityClass": cls, "notAGuarantee": True},
        "executionAuthorization": False, "data": data,
    }


def strand(seq, sid, **kw):
    return ev(seq, "strand.open", {"host": "braid", "label": sid, "parentStrandId": None,
                                   "role": "operation", "strandId": sid}, **kw)


def crossing(seq, left, right, classification="independent-candidate", coverage=("complete",),
             cls=1, **kw):
    return ev(seq, "crossing.classified", {
        "reportId": REPORT, "left": left, "right": right, "classification": classification,
        "sharedResources": [], "reasons": ["r"], "constraints": ["c"],
        "evidence": {"method": "m", "coverage": list(coverage), "ruleSet": "rs"}}, cls=cls, **kw)


def gap(seq, reason, strand_id=None, **kw):
    return ev(seq, "observation.gap", {"reason": reason, "strandId": strand_id,
                                       "fromSeq": None, "toSeq": None}, **kw)


def hazard(seq, kind, units, **kw):
    return ev(seq, "hazard.noticed", {"units": units, "hazardKind": kind, "stage": "receipt"}, **kw)


def plan(seq, waves, mode="candidate-preparation-waves", **kw):
    return ev(seq, "wave.planned", {"planId": PLAN, "mode": mode, "waves": waves,
                                    "serialSlots": sum(len(w) for w in waves)}, **kw)


def grant(seq, kind, **kw):
    return ev(seq, f"grant.{kind}", {"grantId": "g1", "action": "execute", "derived": False}, **kw)


def example_events():
    return view_loom.parse_stream(EXAMPLE.read_bytes())


def by_seq(model, seq):
    return next(e for e in model["elements"] if e["seq"] == seq)


class LanesAndSwapsTests(unittest.TestCase):
    def test_one_lane_per_strand_in_open_order_without_pairs(self):
        model = build_model([strand(1, "c"), strand(2, "a"), strand(3, "b")])
        self.assertEqual([lane["strandId"] for lane in model["lanes"]], ["c", "a", "b"])
        self.assertEqual([lane["laneIndex"] for lane in model["lanes"]], [0, 1, 2])

    def test_lanes_are_reordered_to_keep_classified_pairs_adjacent(self):
        events = [strand(1, "a"), strand(2, "b"), strand(3, "c"), crossing(4, "a", "c")]
        model = build_model(events)
        order = [lane["strandId"] for lane in model["lanes"]]
        self.assertEqual(abs(order.index("a") - order.index("c")), 1)
        crossing_element = by_seq(model, 4)
        self.assertEqual(crossing_element["drawAs"], "swap")
        self.assertEqual(len(crossing_element["segments"]), 1)

    def test_independent_adjacent_pair_is_exactly_one_swap(self):
        model = build_model([strand(1, "a"), strand(2, "b"), crossing(3, "a", "b")])
        element = by_seq(model, 3)
        self.assertEqual(element["drawAs"], "swap")
        self.assertEqual(element["segments"], [
            {"fromLane": 0, "toLane": 1, "kind": "swap", "crossesStrand": True}])
        self.assertEqual(model["counters"]["swaps"], 1)

    def test_only_independent_candidate_pairs_are_swaps(self):
        events = [strand(1, "a"), strand(2, "b"),
                  crossing(3, "a", "b", "ordered", cls=2),
                  crossing(4, "a", "b", "conflicting", cls=0),
                  crossing(5, "a", "b", "unknown", cls=0, coverage=("unknown",))]
        model = build_model(events)
        self.assertEqual({by_seq(model, s)["drawAs"] for s in (3, 4, 5)},
                         {"ordered-link", "conflict-knot", "unknown-link"})
        self.assertEqual(model["counters"]["swaps"], 0)
        for seq in (3, 4, 5):
            self.assertFalse(any(seg["kind"] == "swap" for seg in by_seq(model, seq)["segments"]))

    def test_non_adjacent_pair_becomes_bridge_hops_that_never_cross_intermediate_strands(self):
        # a-b, b-c, c-d chain forces a-d to be non-adjacent in any order
        events = [strand(1, "a"), strand(2, "b"), strand(3, "c"), strand(4, "d"),
                  crossing(5, "a", "b"), crossing(6, "b", "c"), crossing(7, "c", "d"),
                  crossing(8, "a", "d")]
        model = build_model(events)
        order = [lane["strandId"] for lane in model["lanes"]]
        self.assertEqual(order, ["a", "b", "c", "d"])
        element = by_seq(model, 8)
        self.assertEqual(element["drawAs"], "bridge")
        self.assertFalse(element["isSwap"])
        self.assertEqual(element["classification"], "independent-candidate")
        self.assertEqual(element["lanes"], [0, 3])
        self.assertEqual(element["passesOverLanes"], [1, 2])
        self.assertEqual([(s["fromLane"], s["toLane"]) for s in element["segments"]],
                         [(0, 1), (1, 2), (2, 3)])
        self.assertTrue(all(not s["crossesStrand"] for s in element["segments"]))
        self.assertTrue(all(s["kind"] == "bridge" for s in element["segments"]))
        self.assertEqual(model["counters"]["bridges"], 1)
        self.assertEqual(model["counters"]["swaps"], 3)

    def test_segments_run_from_the_lower_to_the_higher_lane_whatever_the_pair_order(self):
        model = build_model([strand(1, "a"), strand(2, "b"), crossing(3, "b", "a", "ordered", cls=2)])
        element = by_seq(model, 3)
        self.assertEqual(element["left"], "b")
        self.assertEqual(element["lanes"], [0, 1])
        self.assertEqual((element["segments"][0]["fromLane"], element["segments"][0]["toLane"]), (0, 1))

    def test_crossing_with_undeclared_strand_gets_an_implicit_lane_sourced_by_the_crossing(self):
        model = build_model([strand(1, "a"), crossing(2, "a", "ghost")])
        ghost = next(lane for lane in model["lanes"] if lane["strandId"] == "ghost")
        self.assertFalse(ghost["declared"])
        self.assertEqual(ghost["seq"], 2)
        self.assertEqual(ghost["evidenceRef"], REF)

    def test_classes_are_categorical_labels_and_carry_the_not_a_guarantee_flag(self):
        model = build_model([strand(1, "a"), strand(2, "b"), crossing(3, "a", "b", cls=3)])
        element = by_seq(model, 3)
        self.assertEqual(element["compatibilityClass"], 3)
        self.assertTrue(element["notAGuarantee"])
        self.assertTrue(model["notAGuarantee"])
        self.assertFalse(model["executionAuthorization"])
        self.assertNotIn("safety", json.dumps(model).lower())

    def test_crossing_joins_its_report_uncertainty_and_limits_by_report_id(self):
        report = ev(2, "analysis.report", {
            "reportId": REPORT, "operationCount": 2, "pairCount": 1,
            "summary": {"independentCandidate": 1, "ordered": 0, "conflicting": 0, "unknown": 0},
            "uncertainty": ["u1"], "limits": ["l1"]})
        model = build_model([strand(1, "a"), report, strand(3, "b"), crossing(4, "a", "b")])
        joined = by_seq(model, 4)["report"]
        self.assertEqual(joined, {"seq": 2, "uncertainty": ["u1"], "limits": ["l1"]})
        self.assertIsNone(by_seq(build_model([strand(1, "a"), strand(2, "b"), crossing(3, "a", "b")]), 3)["report"])


class TimeAxisTests(unittest.TestCase):
    def test_x_is_monotonic_in_relms_and_seq_breaks_ties(self):
        events = [strand(1, "a", ms=100), strand(2, "b", ms=100), strand(3, "c", ms=250)]
        model = build_model(events)
        x = [by_seq(model, s)["x"] for s in (1, 2, 3)]
        self.assertEqual(x[0], x[1])
        self.assertLess(x[1], x[2])
        self.assertEqual([by_seq(model, s)["order"] for s in (1, 2, 3)], [0, 1, 2])

    def test_long_idle_span_is_compressed_and_marked(self):
        events = [strand(1, "a", ms=0), strand(2, "b", ms=1000), strand(3, "c", ms=601_000)]
        model = build_model(events, gap_threshold_ms=5000, gap_nominal_ms=500)
        self.assertEqual(model["axis"]["compressions"], [
            {"fromMs": 1000, "toMs": 601_000, "spanMs": 600_000, "shownMs": 500}])
        self.assertEqual(by_seq(model, 3)["x"], 1000 + 500)
        self.assertTrue(by_seq(model, 3)["afterCompressedGap"])
        self.assertFalse(by_seq(model, 2)["afterCompressedGap"])
        self.assertEqual(model["axis"]["spanMs"], 601_000)
        self.assertEqual(model["axis"]["shownSpan"], 1500)

    def test_span_at_threshold_is_not_compressed(self):
        model = build_model([strand(1, "a", ms=0), strand(2, "b", ms=5000)], gap_threshold_ms=5000)
        self.assertEqual(model["axis"]["compressions"], [])
        self.assertEqual(by_seq(model, 2)["x"], 5000)

    def test_sequence_only_events_carry_no_time_claim(self):
        events = [strand(1, "a", ms=100), strand(2, "b", ms=0, basis="sequence-only"),
                  strand(3, "c", ms=300)]
        model = build_model(events)
        seq_only = by_seq(model, 2)
        self.assertFalse(seq_only["timeKnown"])
        self.assertEqual(seq_only["x"], by_seq(model, 1)["x"])
        self.assertTrue(by_seq(model, 1)["timeKnown"])
        self.assertEqual(model["axis"]["basis"], "mixed")

    def test_axis_basis_is_uniform_when_all_events_agree(self):
        self.assertEqual(build_model([strand(1, "a")])["axis"]["basis"], "artifact-relative")
        self.assertEqual(build_model([])["axis"]["basis"], "sequence-only")

    def test_out_of_order_relms_still_gets_monotone_positions_by_time_then_seq(self):
        model = build_model([strand(1, "a", ms=500), strand(2, "b", ms=100)])
        self.assertLess(by_seq(model, 2)["x"], by_seq(model, 1)["x"])
        self.assertEqual(by_seq(model, 2)["order"], 0)

    def test_invalid_axis_parameters_are_refused(self):
        for kwargs in ({"gap_threshold_ms": 0}, {"gap_nominal_ms": 0},
                       {"gap_threshold_ms": 100, "gap_nominal_ms": 200}, {"gap_threshold_ms": 1.5}):
            with self.assertRaises(ValueError):
                build_model([], **kwargs)


class WavesAndMarkersTests(unittest.TestCase):
    def test_wave_plane_lists_member_lanes_and_is_labelled_advisory(self):
        events = [strand(1, "a"), strand(2, "b"), strand(3, "c"),
                  plan(4, [["a", "b"], ["c"]])]
        element = by_seq(build_model(events), 4)
        self.assertEqual(element["element"], "wave-plane")
        self.assertEqual(element["label"], "advisory plan, not a runtime measurement")
        self.assertEqual([w["strands"] for w in element["waves"]], [["a", "b"], ["c"]])
        self.assertEqual([w["width"] for w in element["waves"]], [2, 1])
        self.assertEqual(element["waves"][0]["lanes"], [0, 1])

    def test_planned_wave_width_is_shown_alone_without_serial_ratio(self):
        events = [strand(1, "a"), strand(2, "b"), strand(3, "c"), plan(4, [["a", "b", "c"]])]
        counters = build_model(events)["counters"]
        self.assertEqual(counters["plannedWaveWidth"], {
            "maxWidth": 3, "plans": 1,
            "label": "advisory plan, not a runtime measurement"})
        self.assertFalse(any(word in key.lower() for key in counters
                             for word in ("speedup", "ratio", "serial", "recovered", "avoided", "saved")))

    def test_wave_started_and_finished_are_markers_with_phase(self):
        data = {"scheduleId": "sha256:" + "c" * 64, "wave": 0, "strands": ["a"]}
        model = build_model([strand(1, "a"), ev(2, "wave.started", data), ev(3, "wave.finished", data)])
        self.assertEqual([by_seq(model, s)["phase"] for s in (2, 3)], ["started", "finished"])
        self.assertEqual(by_seq(model, 2)["lanes"], [0])

    def test_hazard_cone_is_anchored_at_every_named_unit(self):
        events = [strand(1, "a"), strand(2, "b"), hazard(3, "read-write", ["a", "b", "elsewhere"])]
        element = by_seq(build_model(events), 3)
        self.assertEqual(element["element"], "hazard-cone")
        self.assertEqual(element["lanes"], [0, 1])
        self.assertEqual(element["unanchoredUnits"], ["elsewhere"])
        self.assertEqual(element["units"], ["a", "b", "elsewhere"])

    def test_unverified_and_replayed_elements_carry_the_marker(self):
        events = [
            strand(1, "a"), strand(2, "b"),
            crossing(3, "a", "b", verification="unverified"),
            ev(4, "gate.result", {"gateId": "g", "status": "ok-analyzed", "operationCount": 2},
               cls=0, verification="unverified"),
            ev(5, "gate.result", {"gateId": "g", "status": "ok-analyzed", "operationCount": 2},
               cls=0),
        ]
        model = build_model(events)
        self.assertTrue(by_seq(model, 3)["unverified"])
        self.assertTrue(by_seq(model, 4)["unverified"])
        self.assertFalse(by_seq(model, 5)["unverified"])
        self.assertEqual(by_seq(model, 4)["compatibilityClass"], 0)
        self.assertEqual(by_seq(model, 4)["element"], "gate-ring")
        self.assertEqual(model["counters"]["unverifiedElements"], 2)

    def test_gaps_become_broken_strand_markers_anchored_to_the_lane(self):
        model = build_model([strand(1, "a"), gap(2, "ring-evicted", "a"), gap(3, "shape-unpinned")])
        self.assertEqual(by_seq(model, 2)["element"], "gap")
        self.assertEqual(by_seq(model, 2)["lanes"], [0])
        self.assertEqual(by_seq(model, 3)["lanes"], [])
        self.assertEqual(by_seq(model, 2)["reason"], "ring-evicted")

    def test_effort_total_is_unknown_not_zero_when_every_count_is_missing(self):
        base = {"strandId": "a", "basis": "host-estimate", "model": None, "inputTokens": None,
                "outputTokens": None, "cacheReadTokens": None, "cacheCreationTokens": None,
                "cachedInputTokens": None, "reasoningTokens": None, "costUsd": None,
                "durationMs": None}
        none = build_model([strand(1, "a"), ev(2, "effort.sample", base, verification="unverified")])
        self.assertIsNone(by_seq(none, 2)["knownTokens"])
        some = dict(base, inputTokens=10, outputTokens=5)
        known = build_model([strand(1, "a"), ev(2, "effort.sample", some, verification="unverified")])
        self.assertEqual(by_seq(known, 2)["knownTokens"], 15)
        self.assertEqual(by_seq(known, 2)["effortBasis"], "host-estimate")


class EvidenceAndBijectionTests(unittest.TestCase):
    def test_every_element_carries_the_evidence_ref_and_verification_of_its_source_event(self):
        events = example_events()
        model = build_model(events)
        source = {event["seq"]: event for event in events}
        for element in model["elements"]:
            event = source[element["seq"]]
            self.assertEqual(element["evidenceRef"], event["source"]["evidenceRef"], element["seq"])
            self.assertEqual(element["verification"], event["source"]["verification"])
            self.assertEqual(element["kind"], event["kind"])
        for lane in model["lanes"]:
            self.assertEqual(lane["evidenceRef"], source[lane["seq"]]["source"]["evidenceRef"])

    def test_bijection_between_elements_and_source_events(self):
        events = example_events()
        model = build_model(events)
        self.assertEqual([e["seq"] for e in model["elements"]], [e["seq"] for e in events])
        self.assertEqual(len({e["id"] for e in model["elements"]}), len(events))

    def test_table_lists_the_same_facts_as_the_elements(self):
        model = build_model(example_events())
        self.assertEqual([row["seq"] for row in model["table"]], [e["seq"] for e in model["elements"]])
        by = {row["seq"]: row for row in model["table"]}
        for element in model["elements"]:
            row = by[element["seq"]]
            self.assertEqual(row["kind"], element["kind"])
            self.assertEqual(row["verification"], element["verification"])
            self.assertEqual(row["evidencePath"], (element["evidenceRef"] or {}).get("path"))
            self.assertEqual(row["compatibilityClass"], element["compatibilityClass"])
            self.assertEqual(row["unverified"], element["unverified"])

    def test_example_stream_swaps_and_counters(self):
        model = build_model(example_events())
        crossings = [e for e in model["elements"] if e["element"] == "crossing"]
        self.assertEqual(len(crossings), 6)
        swaps = [e for e in crossings if e["drawAs"] == "swap"]
        self.assertEqual({e["classification"] for e in swaps}, {"independent-candidate"})
        for e in crossings:
            if e["classification"] != "independent-candidate":
                self.assertNotIn("swap", {seg["kind"] for seg in e["segments"]})
        counters = model["counters"]
        self.assertEqual(counters["conflictsFlagged"], 1)
        self.assertEqual(counters["independentCandidates"], 2)
        self.assertEqual(counters["unknownPairs"], 3)
        self.assertEqual(counters["orderedPairs"], 0)
        self.assertEqual(counters["gaps"]["total"], 1)
        self.assertEqual(counters["gaps"]["byReason"]["subagent-usage-unattributed"], 1)
        self.assertEqual(counters["hazards"]["total"], 1)
        self.assertEqual(counters["grants"]["issued"], 1)
        self.assertEqual(counters["gates"]["results"], 1)
        self.assertEqual(counters["plannedWaveWidth"]["maxWidth"], 2)

    def test_rejects_invalid_or_misordered_events_as_a_whole(self):
        bad = strand(1, "a")
        bad["executionAuthorization"] = True
        with self.assertRaises(LoomError):
            build_model([bad])
        with self.assertRaises(LoomError) as raised:
            build_model([strand(2, "a"), strand(2, "b")])
        self.assertEqual(raised.exception.reason, "seq-order")

    def test_model_is_json_serialisable_with_stable_key_order_not_required(self):
        json.dumps(build_model(example_events()), allow_nan=False)


class AbsenceTests(unittest.TestCase):
    def absence_events(self):
        return [
            strand(1, "a"), strand(2, "b"), strand(3, "c"), strand(4, "d"),
            crossing(5, "a", "b", "unknown", coverage=("complete", "unknown"), cls=0),
            crossing(6, "b", "c", "independent-candidate", coverage=("partial",), cls=1),
            crossing(7, "c", "d", "independent-candidate", coverage=(), cls=1),
            crossing(8, "a", "c", "independent-candidate", coverage=("complete",), cls=1),
            hazard(9, "not-observed", ["a"]),
            hazard(10, "partial-coverage", ["b"]),
            hazard(11, "unattributed-writer", ["c"]),
            hazard(12, "read-write", ["d"]),
            gap(13, "stream-truncated"), gap(14, "shape-unpinned"), gap(15, "ring-evicted"),
            gap(16, "host-unverified"), gap(17, "not-observed"), gap(18, "source-unsupported"),
            gap(19, "subagent-usage-unattributed"),
        ]

    def test_no_absence_case_is_counted_as_independent_or_conflict_free(self):
        counters = build_model(self.absence_events())["counters"]
        self.assertEqual(counters["independentCandidates"], 1)  # only the complete-coverage pair
        self.assertEqual(counters["unknownPairs"], 1)
        self.assertEqual(counters["conflictsFlagged"], 0)
        absence = counters["absence"]
        self.assertEqual(absence["unknownPairs"], 1)
        self.assertEqual(absence["independentWithIncompleteCoverage"], 2)
        self.assertEqual(absence["hazardsNotObserved"], 3)
        self.assertEqual(absence["gaps"], 7)

    def test_incomplete_coverage_independent_pair_is_marked_and_not_a_clean_swap(self):
        model = build_model(self.absence_events())
        partial = by_seq(model, 6)
        self.assertTrue(partial["incompleteCoverage"])
        self.assertTrue(partial["uncertain"])
        self.assertTrue(by_seq(model, 7)["incompleteCoverage"])  # empty coverage is not complete
        self.assertFalse(by_seq(model, 8)["incompleteCoverage"])
        self.assertFalse(by_seq(model, 8)["uncertain"])
        self.assertTrue(by_seq(model, 5)["uncertain"])

    def test_every_gap_reason_is_listed_with_zero_fill(self):
        by_reason = build_model(self.absence_events())["counters"]["gaps"]["byReason"]
        self.assertEqual(set(by_reason), set(view_loom.GAP_REASONS))
        self.assertTrue(all(count == 1 for count in by_reason.values()))
        empty = build_model([strand(1, "a")])["counters"]["gaps"]
        self.assertEqual(empty["total"], 0)
        self.assertEqual(set(empty["byReason"]), set(view_loom.GAP_REASONS))

    def test_a_model_that_drops_gaps_is_detectable(self):
        model = build_model(self.absence_events())
        self.assertEqual(len([e for e in model["elements"] if e["element"] == "gap"]), 7)

    def test_empty_stream_reports_nothing_as_clean(self):
        counters = build_model([])["counters"]
        self.assertEqual(counters["independentCandidates"], 0)
        self.assertIsNone(counters["plannedWaveWidth"]["maxWidth"])
        self.assertEqual(counters["plannedWaveWidth"]["plans"], 0)


class CapTests(unittest.TestCase):
    def test_strand_cap_drops_lanes_but_counters_still_count_every_crossing(self):
        events = [strand(i + 1, f"s{i}") for i in range(6)]
        events.append(crossing(7, "s4", "s5", "conflicting", cls=0))
        model = build_model(events, limits={"strands": 4})
        self.assertEqual(len(model["lanes"]), 4)
        self.assertEqual(model["truncated"], [{"what": "strands", "limit": 4, "dropped": 2}])
        element = by_seq(model, 7)
        self.assertEqual(element["drawAs"], "unplaced")
        self.assertEqual(element["segments"], [])
        self.assertEqual(model["counters"]["conflictsFlagged"], 1)
        self.assertEqual(model["counters"]["absence"]["truncated"], 2)

    def test_crossing_cap_drops_elements_not_counts(self):
        events = [strand(1, "a"), strand(2, "b")]
        events += [crossing(3 + i, "a", "b", "conflicting", cls=0) for i in range(5)]
        model = build_model(events, limits={"crossings": 2})
        self.assertEqual(len([e for e in model["elements"] if e["element"] == "crossing"]), 2)
        self.assertEqual(model["counters"]["conflictsFlagged"], 5)
        self.assertIn({"what": "crossings", "limit": 2, "dropped": 3}, model["truncated"])

    def test_wave_and_grant_caps(self):
        data = {"scheduleId": "sha256:" + "c" * 64, "wave": 0, "strands": []}
        events = [ev(i + 1, "wave.started", data) for i in range(3)]
        events += [grant(4 + i, "issued") for i in range(3)]
        model = build_model(events, limits={"waves": 1, "grants": 2})
        self.assertIn({"what": "waves", "limit": 1, "dropped": 2}, model["truncated"])
        self.assertIn({"what": "grants", "limit": 2, "dropped": 1}, model["truncated"])
        self.assertEqual(model["counters"]["grants"]["issued"], 3)

    def test_default_limits_match_the_spec(self):
        self.assertEqual(view_model.DEFAULT_LIMITS,
                         {"strands": 256, "crossings": 4096, "waves": 64, "grants": 1024})

    def test_unknown_limit_name_or_non_positive_value_is_refused(self):
        for limits in ({"nodes": 3}, {"strands": 0}, {"strands": True}):
            with self.assertRaises(ValueError):
                build_model([], limits=limits)

    def test_more_than_max_events_is_refused(self):
        events = [strand(i + 1, "a") for i in range(view_loom.MAX_EVENTS + 1)]
        with self.assertRaises(LoomError) as raised:
            build_model(events)
        self.assertEqual(raised.exception.reason, "too-many-events")


class DeterminismTests(unittest.TestCase):
    def test_same_events_give_byte_identical_models_and_input_is_untouched(self):
        events = example_events()
        before = deepcopy(events)
        first = json.dumps(build_model(events), sort_keys=True)
        second = json.dumps(build_model(deepcopy(events)), sort_keys=True)
        self.assertEqual(first, second)
        self.assertEqual(events, before)

    def test_model_does_not_alias_the_input_events(self):
        events = example_events()
        model = build_model(events)
        events[1]["data"]["limits"].append("mutated")
        self.assertNotIn("mutated", json.dumps(model))


class BoundaryTests(unittest.TestCase):
    def test_module_is_pure_and_names_no_ownership_or_io(self):
        source = (ROOT / "agent_braid/view_model.py").read_text(encoding="utf-8")
        for token in ("import os", "import socket", "import subprocess", "open(", "pathlib",
                      "ownership", "import time", "import random", "datetime"):
            self.assertNotIn(token, source, token)


if __name__ == "__main__":
    unittest.main()
