# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T012, T013: artifact adapters bound to evidence (procedure_002, procedure_003)."""
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from agent_braid import analysis, view_adapters, view_loom
from agent_braid.view_adapters import (
    AdapterError, SUPPORTED_VERSIONS, events_from_analysis, events_from_gate_result, events_from_git_plan,
    events_from_grant, events_from_hazard_notice, events_from_ownership_receipt, events_from_runtime_state,
    events_from_scheduler, read_artifact,
)
from agent_braid.view_loom import canonical_bytes, validate_event

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures/view/artifacts"
MODULE = ROOT / "agent_braid/view_adapters.py"


def raw(name):
    return (FIXTURES / name).read_bytes()


def doc(name):
    return json.loads(raw(name))


def dump(value):
    return json.dumps(value, sort_keys=True).encode("utf-8")


def kinds(events):
    return [event["kind"] for event in events]


def of_kind(events, kind):
    return [event for event in events if event["kind"] == kind]


def stream(events):
    return b"".join(canonical_bytes(event) for event in events)


# family -> (adapter function, fixture name, adapter name, version field)
FAMILIES = {
    "analysis": (events_from_analysis, "analysis-file-edits.json", "analysis-report", "reportVersion"),
    "git-plan": (events_from_git_plan, "git-replay-plan.json", "git-replay-plan", "gitPlanVersion"),
    "scheduler": (events_from_scheduler, "scheduler-preparation.json", "scheduler-preparation",
                  "runtimePreparationEvidenceVersion"),
    "grant": (events_from_grant, "grant-issued.json", "runtime-grant", "runtimeOperatorGrantVersion"),
    "state": (events_from_runtime_state, "runtime-state-completed.json", "runtime-state",
              "gitRuntimeStateVersion"),
    "notice": (events_from_hazard_notice, "hazard-notice-receipt.json", "ownership-notice", "schemaVersion"),
    "receipt": (events_from_ownership_receipt, "ownership-receipt-hazards.json", "ownership-receipt",
                "schemaVersion"),
    "gate": (events_from_gate_result, "gate-result-certified.json", "workflow-gate", "schemaVersion"),
}
PATH = "runs/example/artifact.json"


def run(family, data=None, **options):
    function, name, _, _ = FAMILIES[family]
    return function(raw(name) if data is None else data, path=PATH, **options)


class ContractTests(unittest.TestCase):
    def test_every_event_of_every_family_passes_the_loom_validator(self):
        for family, (_, name, adapter, _) in FAMILIES.items():
            with self.subTest(family):
                events = run(family)
                self.assertTrue(events)
                for event in events:
                    self.assertIs(validate_event(event), event)
                    self.assertIs(event["executionAuthorization"], False)
                    self.assertEqual(event["source"]["adapter"], adapter)
                    self.assertEqual(event["source"]["host"], "braid")
                    self.assertEqual(event["source"]["verification"], "rehashed")
                    self.assertEqual(event["source"]["evidenceRef"],
                                     {"path": PATH, "sha256": hashlib.sha256(raw(name)).hexdigest()})
                self.assertEqual([event["seq"] for event in events], list(range(1, len(events) + 1)))

    def test_output_is_byte_identical_across_runs(self):
        for family in FAMILIES:
            with self.subTest(family):
                self.assertEqual(stream(run(family)), stream(run(family)))
                view_loom.parse_stream(stream(run(family)))

    def test_seq_start_offsets_the_numbering_and_is_checked(self):
        events = run("analysis", seq_start=41)
        self.assertEqual(events[0]["seq"], 41)
        self.assertEqual([event["seq"] for event in events], list(range(41, 41 + len(events))))
        for bad in (0, -1, view_loom.MAX_SEQ):
            with self.subTest(bad), self.assertRaises(view_loom.LoomError):
                run("analysis", seq_start=bad)

    def test_the_hash_follows_the_artifact_bytes(self):
        original = run("state")[0]["source"]["evidenceRef"]["sha256"]
        tampered = run("state", raw("runtime-state-completed.json") + b" ")[0]["source"]["evidenceRef"]["sha256"]
        self.assertNotEqual(original, tampered)

    def test_an_invalid_evidence_path_is_refused(self):
        for bad in ("../outside.json", "/abs/path.json", "a\\b.json", "C:/x.json", ""):
            with self.subTest(bad), self.assertRaises(view_loom.LoomError):
                events_from_runtime_state(raw("runtime-state-completed.json"), path=bad)

    def test_the_support_table_names_loom_adapters_and_a_version_each(self):
        self.assertEqual(set(SUPPORTED_VERSIONS), {adapter for _, _, adapter, _ in FAMILIES.values()})
        self.assertLessEqual(set(SUPPORTED_VERSIONS), set(view_loom.ADAPTERS))
        for family, (_, _, adapter, field) in FAMILIES.items():
            with self.subTest(family):
                self.assertEqual(SUPPORTED_VERSIONS[adapter][0], field)
                self.assertTrue(SUPPORTED_VERSIONS[adapter][1])


class UnsupportedSourceTests(unittest.TestCase):
    def assert_gap(self, events, adapter):
        self.assertEqual(kinds(events), ["observation.gap"])
        event = events[0]
        self.assertEqual(event["data"], {"reason": "source-unsupported", "strandId": None,
                                         "fromSeq": None, "toSeq": None})
        self.assertEqual(event["source"]["adapter"], adapter)
        self.assertIsNone(event["assurance"]["compatibilityClass"])
        validate_event(event)

    def test_another_version_yields_a_gap_never_a_guess(self):
        for family, (_, name, adapter, field) in FAMILIES.items():
            for version in ("9.9.9", "0.1.0-alpha ", 1, None):
                with self.subTest(family=family, version=version):
                    changed = doc(name)
                    changed[field] = version
                    self.assert_gap(run(family, dump(changed)), adapter)
            with self.subTest(family=family, missing=True):
                changed = doc(name)
                del changed[field]
                self.assert_gap(run(family, dump(changed)), adapter)

    def test_unparseable_or_misshapen_bytes_yield_a_gap(self):
        cases = {
            "empty": b"", "not json": b"{", "array": b"[]", "scalar": b"1",
            "duplicate member": b'{"gitRuntimeStateVersion":"0.1.0-alpha","gitRuntimeStateVersion":"x"}',
            "nan": b'{"a":NaN}', "nesting": b"[" * 100000, "bad utf-8": b"\xff\xfe",
        }
        for family, (_, _, adapter, _) in FAMILIES.items():
            for label, data in cases.items():
                with self.subTest(family=family, case=label):
                    self.assert_gap(run(family, data), adapter)

    def test_a_supported_version_with_missing_or_mistyped_content_yields_a_gap(self):
        mutations = {
            "analysis": lambda d: d.pop("interactions"),
            "git-plan": lambda d: d.update(waves="a"),
            "scheduler": lambda d: d["workers"][0].update(startedNs="1"),
            "grant": lambda d: d.update(action="destroy"),
            "state": lambda d: d.update(phase="exploded"),
            "notice": lambda d: d["hazards"][0].update(kind="mystery"),
            "receipt": lambda d: d["units"][0].update(observation="maybe"),
            "gate": lambda d: d["phases"][0].update(status="fine"),
        }
        for family, mutate in mutations.items():
            with self.subTest(family):
                changed = doc(FAMILIES[family][1])
                mutate(changed)
                self.assert_gap(run(family, dump(changed)), FAMILIES[family][2])

    def test_the_gap_still_names_the_hash_of_what_was_read(self):
        data = b"{}"
        event = run("analysis", data)[0]
        self.assertEqual(event["source"]["evidenceRef"]["sha256"], hashlib.sha256(data).hexdigest())


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.report = doc("analysis-mixed.json")
        self.events = run("analysis", raw("analysis-mixed.json"))

    def test_the_fixtures_are_what_the_analyzer_produces(self):
        source = json.loads((ROOT / "examples/analysis/file-edits.json").read_text(encoding="utf-8"))
        self.assertEqual(analysis.analyze(source), doc("analysis-file-edits.json"))
        self.assertEqual(self.report["summary"]["pairCount"], len(self.report["interactions"]))
        self.assertEqual({pair["classification"] for pair in self.report["interactions"]},
                         {"independent-candidate", "ordered", "conflicting", "unknown"})

    def assert_matches_source(self, events, report):
        reports = of_kind(events, "analysis.report")
        self.assertEqual(len(reports), 1)
        summary = report["summary"]["classifications"]
        self.assertEqual(reports[0]["data"], {
            "reportId": report["analysisId"],
            "operationCount": report["summary"]["operationCount"],
            "pairCount": report["summary"]["pairCount"],
            "summary": {"independentCandidate": summary["independent-candidate"], "ordered": summary["ordered"],
                        "conflicting": summary["conflicting"], "unknown": summary["unknown"]},
            "uncertainty": report["uncertainty"],
            "limits": report["limits"],
        })
        crossings = of_kind(events, "crossing.classified")
        self.assertEqual(len(crossings), len(report["interactions"]))
        for event, pair in zip(crossings, report["interactions"], strict=True):
            self.assertEqual(event["data"], {
                "reportId": report["analysisId"], "left": pair["left"], "right": pair["right"],
                "classification": pair["classification"], "sharedResources": pair["sharedResources"],
                "reasons": pair["reasons"], "constraints": pair["constraints"],
                "evidence": {"method": pair["evidence"]["method"], "coverage": pair["evidence"]["coverage"],
                             "ruleSet": pair["evidence"]["ruleSet"]},
            })
            self.assertEqual(event["assurance"]["compatibilityClass"], pair["evidence"]["assuranceClass"])
        strands = of_kind(events, "strand.open")
        self.assertEqual([event["data"]["strandId"] for event in strands],
                         [operation["instanceId"] for operation in report["operations"]])
        for event in strands:
            self.assertEqual(event["data"]["role"], "operation")
            self.assertIsNone(event["data"]["parentStrandId"])

    def test_report_strands_and_one_crossing_per_pair_equal_the_source(self):
        self.assert_matches_source(self.events, self.report)
        self.assertEqual(kinds(self.events),
                         ["analysis.report"] + ["strand.open"] * 5 + ["crossing.classified"] * 10
                         + ["strand.update"])

    def test_an_ordered_pair_with_a_declared_dependency_is_a_declared_wait_in_v02(self):
        # T061: edit-after-roadmap lists edit-roadmap in its dependencies and the pair is ordered.
        waits = [event for event in self.events if event["kind"] == "strand.update"]
        self.assertEqual(len(waits), 1)
        self.assertEqual(waits[0]["schemaVersion"], view_loom.SCHEMA_VERSION_V02)
        self.assertEqual(waits[0]["data"], {"strandId": "edit-after-roadmap", "state": "waiting", "toolName": None,
                                            "waitingOn": "edit-roadmap", "waitingBasis": "declared"})
        self.assertEqual(waits[0]["at"]["basis"], "sequence-only")
        self.assertEqual(waits[0]["source"]["verification"], "rehashed")

    def test_no_wait_without_a_dependency_direction_and_a_dependency_on_no_operation_is_a_gap(self):
        report = deepcopy(self.report)
        for operation in report["operations"]:
            operation["dependencies"] = []
        self.assertNotIn("strand.update", kinds(run("analysis", dump(report))))
        broken = deepcopy(self.report)
        pair = next(p for p in broken["interactions"] if p["classification"] == "ordered")
        pair["right"] = "not-an-operation"
        for operation in broken["operations"]:
            if operation["instanceId"] == pair["left"]:
                operation["dependencies"] = ["not-an-operation"]
        events = run("analysis", dump(broken))
        self.assertNotIn("strand.update", kinds(events))
        self.assertEqual([g["data"]["reason"] for g in of_kind(events, "observation.gap")], ["shape-unpinned"])

    def test_scheduler_and_runtime_state_emit_no_wait(self):
        for family in ("scheduler", "state"):
            with self.subTest(family=family):
                self.assertNotIn("waitingOn", json.dumps(run(family)))

    def test_the_small_example_report_maps_one_pair(self):
        events = run("analysis")
        self.assertEqual(kinds(events), ["analysis.report", "strand.open", "strand.open", "crossing.classified"])
        self.assert_matches_source(events, doc("analysis-file-edits.json"))

    def test_all_four_classifications_are_kept_with_their_class(self):
        by_class = {event["data"]["classification"]: event["assurance"]["compatibilityClass"]
                    for event in of_kind(self.events, "crossing.classified")}
        self.assertEqual(by_class, {"independent-candidate": 1, "ordered": 0, "conflicting": 0, "unknown": 0})

    def test_a_reclassified_pair_or_remapped_value_fails_the_comparison(self):
        reclassified = deepcopy(self.events)
        pair = of_kind(reclassified, "crossing.classified")[0]
        pair["data"]["classification"] = "ordered"
        with self.assertRaises(AssertionError):
            self.assert_matches_source(reclassified, self.report)
        raised_class = deepcopy(self.events)
        of_kind(raised_class, "crossing.classified")[0]["assurance"]["compatibilityClass"] = 5
        with self.assertRaises(AssertionError):
            self.assert_matches_source(raised_class, self.report)
        mutated = deepcopy(self.report)
        mutated["interactions"][0]["classification"] = "ordered"
        with self.assertRaises(AssertionError):
            self.assert_matches_source(self.events, mutated)
        self.assert_matches_source(run("analysis", dump(mutated)), mutated)

    def test_a_pair_over_the_field_caps_becomes_a_stream_truncated_gap(self):
        for label, change in (
            ("resources", lambda pair: pair.update(sharedResources=[f"repo://r/{n}" for n in range(17)])),
            ("reasons", lambda pair: pair.update(reasons=[f"reason {n}" for n in range(9)])),
            ("constraints", lambda pair: pair.update(constraints=[f"c{n}" for n in range(9)])),
            ("long text", lambda pair: pair.update(reasons=["x" * 257])),
        ):
            with self.subTest(label):
                changed = deepcopy(self.report)
                change(changed["interactions"][2])
                events = run("analysis", dump(changed))
                self.assertEqual(len(events), len(self.events))
                gaps = of_kind(events, "observation.gap")
                self.assertEqual([event["data"]["reason"] for event in gaps], ["stream-truncated"])
                self.assertEqual(len(of_kind(events, "crossing.classified")), 9)
                self.assertEqual(events.index(gaps[0]), 1 + 5 + 2)
                self.assertEqual(gaps[0]["source"]["evidenceRef"]["sha256"],
                                 hashlib.sha256(dump(changed)).hexdigest())
                self.assertEqual([event["seq"] for event in events], list(range(1, len(events) + 1)))

    def test_an_oversized_report_summary_list_is_a_gap_in_place_of_the_report(self):
        changed = deepcopy(self.report)
        changed["uncertainty"] = [f"u{n}" for n in range(17)]
        events = run("analysis", dump(changed))
        self.assertEqual(kinds(events), ["observation.gap"])
        self.assertEqual(events[0]["data"]["reason"], "source-unsupported")

    def test_independent_candidates_are_never_promoted(self):
        changed = deepcopy(self.report)
        for pair in changed["interactions"]:
            pair["classification"] = "unknown"
            pair["evidence"]["assuranceClass"] = 0
        events = run("analysis", dump(changed))
        self.assertNotIn("independent-candidate",
                         {event["data"]["classification"] for event in of_kind(events, "crossing.classified")})


class GitPlanTests(unittest.TestCase):
    def test_waves_mode_and_fallback_order_equal_the_plan(self):
        plan = doc("git-replay-plan.json")
        events = run("git-plan")
        self.assertEqual(kinds(events), ["wave.planned"])
        self.assertEqual(events[0]["data"], {
            "planId": plan["planDigest"], "mode": plan["mode"], "waves": plan["waves"],
            "serialSlots": len(plan["fallbackOrder"]),
        })
        self.assertEqual(events[0]["data"]["mode"], "candidate-preparation-waves")
        self.assertIsNone(events[0]["assurance"]["compatibilityClass"])

    def test_serial_fallback_and_manual_review_keep_their_modes(self):
        plan = doc("git-replay-plan.json")
        serial = dict(plan, mode="serial-fallback", waves=[["a"], ["b"]])
        event = run("git-plan", dump(serial))[0]
        self.assertEqual((event["data"]["mode"], event["data"]["waves"], event["data"]["serialSlots"]),
                         ("serial-fallback", [["a"], ["b"]], 2))
        manual = dict(plan, mode="manual-review", waves=[], fallbackOrder=None)
        event = run("git-plan", dump(manual))[0]
        self.assertEqual((event["data"]["mode"], event["data"]["waves"], event["data"]["serialSlots"]),
                         ("manual-review", [], 0))

    def test_an_unknown_mode_is_a_gap_not_a_guess(self):
        events = run("git-plan", dump(dict(doc("git-replay-plan.json"), mode="free-for-all")))
        self.assertEqual(events[0]["data"]["reason"], "source-unsupported")


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.evidence = doc("scheduler-preparation.json")
        self.events = run("scheduler")

    def test_waves_and_workers_equal_the_preparation_evidence(self):
        workers = self.evidence["workers"]
        schedule = self.evidence["scheduleDigest"]
        opens = of_kind(self.events, "strand.open")
        closes = of_kind(self.events, "strand.close")
        self.assertEqual({event["data"]["strandId"] for event in opens}, {w["operationId"] for w in workers})
        self.assertEqual({event["data"]["strandId"] for event in closes}, {w["operationId"] for w in workers})
        for event in opens:
            self.assertEqual(event["data"]["role"], "worker")
            self.assertEqual(event["data"]["host"], "braid")
            worker = next(w for w in workers if w["operationId"] == event["data"]["strandId"])
            self.assertEqual(event["at"], {"relMs": worker["startedNs"] // 1_000_000, "basis": "artifact-relative"})
        for event in closes:
            worker = next(w for w in workers if w["operationId"] == event["data"]["strandId"])
            self.assertEqual(event["at"]["relMs"], worker["finishedNs"] // 1_000_000)
            self.assertEqual(event["data"]["outcome"], "ok")
        for number in sorted({w["wave"] for w in workers}):
            members = [w for w in workers if w["wave"] == number]
            started = next(e for e in of_kind(self.events, "wave.started") if e["data"]["wave"] == number)
            finished = next(e for e in of_kind(self.events, "wave.finished") if e["data"]["wave"] == number)
            for event in (started, finished):
                self.assertEqual(event["data"]["scheduleId"], schedule)
                self.assertEqual(event["data"]["strands"], [w["operationId"] for w in members])
            self.assertEqual(started["at"]["relMs"], min(w["startedNs"] for w in members) // 1_000_000)
            self.assertEqual(finished["at"]["relMs"], max(w["finishedNs"] for w in members) // 1_000_000)

    def test_events_are_ordered_in_time_with_a_wave_started_before_its_strands(self):
        times = [event["at"]["relMs"] for event in self.events]
        self.assertEqual(times, sorted(times))
        self.assertEqual(self.events[0]["kind"], "wave.started")
        self.assertEqual(self.events[-1]["kind"], "wave.finished")

    def test_two_waves_keep_their_order_and_membership(self):
        changed = deepcopy(self.evidence)
        changed["workers"][1]["wave"] = 1
        changed["workers"][1]["startedNs"] = changed["workers"][0]["finishedNs"] + 5
        changed["workers"][1]["finishedNs"] = changed["workers"][1]["startedNs"] + 1_000_000
        events = run("scheduler", dump(changed))
        started = of_kind(events, "wave.started")
        self.assertEqual([(e["data"]["wave"], e["data"]["strands"]) for e in started],
                         [(0, ["a"]), (1, ["b"])])
        self.assertLess(events.index(of_kind(events, "wave.finished")[0]), events.index(started[1]))

    def test_impossible_or_missing_worker_timing_is_a_gap(self):
        for label, change in (
            ("backwards", lambda d: d["workers"][0].update(finishedNs=d["workers"][0]["startedNs"] - 1)),
            ("zero length", lambda d: d["workers"][0].update(finishedNs=d["workers"][0]["startedNs"])),
            ("negative", lambda d: d["workers"][0].update(startedNs=-1)),
            ("no workers", lambda d: d.update(workers=[])),
        ):
            with self.subTest(label):
                changed = deepcopy(self.evidence)
                change(changed)
                self.assertEqual(kinds(run("scheduler", dump(changed))), ["observation.gap"])

    def test_a_wave_number_outside_the_contract_is_a_gap(self):
        changed = deepcopy(self.evidence)
        changed["workers"][0]["wave"] = 64
        self.assertEqual(kinds(run("scheduler", dump(changed))), ["observation.gap"])

    def test_no_machine_path_leaves_the_worker_records(self):
        text = json.dumps(self.events)
        self.assertNotIn("worker.git", text)


class GrantTests(unittest.TestCase):
    def test_an_issued_grant_keeps_its_action_and_id(self):
        grant = doc("grant-issued.json")
        events = run("grant")
        self.assertEqual(kinds(events), ["grant.issued"])
        self.assertEqual(events[0]["data"], {"grantId": grant["grantId"], "action": grant["action"],
                                             "derived": False})
        self.assertEqual(events[0]["source"]["verification"], "rehashed")

    def test_each_action_is_kept_verbatim(self):
        for action in ("execute", "resume", "abort"):
            with self.subTest(action):
                events = run("grant", dump(dict(doc("grant-issued.json"), action=action)))
                self.assertEqual(events[0]["data"]["action"], action)

    def test_a_consumed_grant_yields_issued_then_consumed(self):
        grant = doc("grant-consumed.json")
        events = run("grant", raw("grant-consumed.json"))
        self.assertEqual(kinds(events), ["grant.issued", "grant.consumed"])
        for event in events:
            self.assertEqual(event["data"], {"grantId": grant["grantId"], "action": "execute", "derived": False})
        events = run("grant", raw("grant-consumed.json"), now=grant["expiresAt"] + 10_000)
        self.assertEqual(kinds(events), ["grant.issued", "grant.consumed"])

    def test_expiry_is_derived_only_when_the_viewer_clock_passes_the_recorded_validity(self):
        grant = doc("grant-issued.json")
        self.assertEqual(kinds(run("grant")), ["grant.issued"])
        self.assertEqual(kinds(run("grant", now=grant["expiresAt"] - 1)), ["grant.issued"])
        events = run("grant", now=grant["expiresAt"])
        self.assertEqual(kinds(events), ["grant.issued", "grant.expired"])
        expired = events[1]
        self.assertEqual(expired["data"], {"grantId": grant["grantId"], "action": "execute", "derived": True})
        self.assertEqual(expired["source"]["verification"], "derived")
        self.assertEqual(expired["source"]["evidenceRef"], events[0]["source"]["evidenceRef"])
        self.assertEqual(expired["at"], {"relMs": (grant["expiresAt"] - grant["issuedAt"]) * 1000,
                                         "basis": "artifact-relative"})
        self.assertEqual(stream(run("grant", now=grant["expiresAt"])), stream(events))

    def test_a_non_integer_clock_is_refused(self):
        for bad in (1.5, "9", True):
            with self.subTest(bad), self.assertRaises(TypeError):
                run("grant", now=bad)

    def test_a_grant_that_ends_before_it_starts_is_a_gap(self):
        grant = doc("grant-issued.json")
        grant["expiresAt"] = grant["issuedAt"] - 1
        events = run("grant", dump(grant), now=grant["issuedAt"])
        self.assertEqual(kinds(events), ["observation.gap"])


class RuntimeStateTests(unittest.TestCase):
    def test_phase_and_manifest_digest_equal_the_state(self):
        for name in ("runtime-state-ready.json", "runtime-state-completed.json"):
            with self.subTest(name):
                state = doc(name)
                events = events_from_runtime_state(raw(name), path=PATH)
                self.assertEqual(kinds(events), ["runtime.phase"])
                self.assertEqual(events[0]["data"], {"manifestDigest": state["manifestDigest"],
                                                     "phase": state["phase"]})

    def test_every_source_phase_is_kept(self):
        for phase in ("initializing", "ready", "applying", "completed", "aborting", "aborted"):
            with self.subTest(phase):
                state = dict(doc("runtime-state-ready.json"), phase=phase)
                self.assertEqual(run("state", dump(state))[0]["data"]["phase"], phase)

    def test_a_remapped_phase_fails_the_comparison(self):
        state = doc("runtime-state-completed.json")
        event = run("state")[0]
        self.assertEqual(event["data"]["phase"], state["phase"])
        self.assertNotEqual(run("state", dump(dict(state, phase="aborted")))[0]["data"]["phase"],
                            event["data"]["phase"])


def hazards(events):
    return [(e["data"]["hazardKind"], e["data"]["units"], e["data"]["stage"])
            for e in of_kind(events, "hazard.noticed")]


class HazardNoticeTests(unittest.TestCase):
    def test_every_hazard_and_every_unit_is_kept_in_order(self):
        for name, stage in (("hazard-notice-receipt.json", "receipt"), ("hazard-notice-preflight.json", "preflight")):
            with self.subTest(name):
                notice = doc(name)
                events = events_from_hazard_notice(raw(name), path=PATH)
                self.assertEqual(kinds(events), ["hazard.noticed"] * len(notice["hazards"]))
                self.assertEqual(hazards(events), [(h["kind"], h["units"], stage) for h in notice["hazards"]])
                for event in events:
                    self.assertIsNone(event["assurance"]["compatibilityClass"])
                    self.assertEqual(event["at"]["basis"], "sequence-only")

    def test_the_fixtures_have_the_shape_of_each_stage(self):
        for name in ("hazard-notice-receipt.json", "hazard-notice-preflight.json"):
            notice = doc(name)
            self.assertEqual(notice["deliveredVia"], "pull")
            self.assertTrue(notice["hazards"])
        self.assertEqual(doc("hazard-notice-receipt.json")["recheck"].split("-")[1], "check")
        self.assertEqual(doc("hazard-notice-preflight.json")["recheck"].split("-")[1], "expand")

    def test_a_hazard_with_the_most_units_the_source_allows_keeps_all_of_them(self):
        notice = doc("hazard-notice-receipt.json")
        units = [f"unit-{n}" for n in range(32)]
        notice["hazards"] = [dict(h, units=units) for h in notice["hazards"][:1]]
        events = run("notice", dump(notice))
        self.assertEqual(events[0]["data"]["units"], units)

    def test_no_repository_path_or_notice_text_reaches_the_events(self):
        text = json.dumps(run("notice")) + json.dumps(events_from_hazard_notice(
            raw("hazard-notice-preflight.json"), path=PATH))
        for forbidden in ("zz/new.py", "src/a.py", "loose.txt", "repository-derived", "validUntil", "noticeId"):
            self.assertNotIn(forbidden, text)

    def test_a_recheck_without_a_stage_or_with_authorization_is_a_gap(self):
        notice = doc("hazard-notice-receipt.json")
        for label, change in (
            ("audit", lambda d: d.update(recheck="rerun-audit-isolation")),
            ("recovery", lambda d: d.update(recheck="rerun-report-recovery")),
            ("free text", lambda d: d.update(recheck="rerun-check-ownership now")),
            ("not text", lambda d: d.update(recheck=3)),
            ("authorized", lambda d: d.update(executionAuthorization=True)),
            ("absent authorization", lambda d: d.pop("executionAuthorization")),
        ):
            with self.subTest(label):
                changed = deepcopy(notice)
                change(changed)
                events = run("notice", dump(changed))
                self.assertEqual(kinds(events), ["observation.gap"])
                self.assertEqual(events[0]["data"]["reason"], "source-unsupported")

    def test_a_hazard_beyond_the_event_caps_makes_the_artifact_unsupported_not_shortened(self):
        notice = doc("hazard-notice-receipt.json")
        notice["hazards"][0]["units"] = [f"u{n}" for n in range(129)]
        self.assertEqual(kinds(run("notice", dump(notice))), ["observation.gap"])

    def test_a_hazard_with_a_cut_path_list_adds_a_stream_truncated_gap(self):
        notice = doc("hazard-notice-receipt.json")
        notice["hazards"][1]["data"]["truncated"] = True
        events = run("notice", dump(notice))
        self.assertEqual(kinds(events), ["hazard.noticed"] * len(notice["hazards"]) + ["observation.gap"])
        self.assertEqual(events[-1]["data"]["reason"], "stream-truncated")

    def test_a_notice_with_no_hazard_yields_no_event_that_could_read_as_clean(self):
        notice = dict(doc("hazard-notice-receipt.json"), hazards=[])
        self.assertEqual(run("notice", dump(notice)), [])


class OwnershipReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = doc("ownership-receipt-hazards.json")
        self.events = run("receipt")

    def test_each_finding_maps_to_its_hazard_kind_and_units(self):
        self.assertEqual(hazards(self.events), [
            ("partial-coverage", ["a"], "receipt"),
            ("undeclared-write", ["a"], "receipt"),
            ("sibling-area-write", ["a", "b"], "receipt"),
            ("not-observed", ["c"], "receipt"),
            ("unattributed-writer", [], "receipt"),
        ])
        for event in self.events:
            self.assertIsNone(event["assurance"]["compatibilityClass"])

    def test_the_receipt_hazards_equal_the_notice_built_from_the_same_receipt(self):
        notice = events_from_hazard_notice(raw("hazard-notice-receipt.json"), path=PATH)
        self.assertEqual(sorted(hazards(self.events), key=repr), sorted(hazards(notice), key=repr))

    def test_a_fully_observed_receipt_without_findings_yields_nothing_that_reads_clean(self):
        self.assertEqual(events_from_ownership_receipt(raw("ownership-receipt-clean.json"), path=PATH), [])

    def test_not_observed_units_are_hazards_never_clean(self):
        receipt = doc("ownership-receipt-clean.json")
        receipt["units"][0].update(observation="not-observed", coverage="partial",
                                   notObservedReason="no-source-supplied")
        events = run("receipt", dump(receipt))
        self.assertEqual(hazards(events), [("not-observed", [receipt["units"][0]["id"]], "receipt")])

    def test_a_cut_list_adds_one_stream_truncated_gap_naming_the_receipt(self):
        receipt = deepcopy(self.receipt)
        receipt["truncations"] = [{"list": "unknown", "unitId": "a", "total": 900},
                                  {"list": "unattributedWriters", "total": 70}]
        events = run("receipt", dump(receipt))
        self.assertEqual(kinds(events), ["hazard.noticed"] * 5 + ["observation.gap"])
        self.assertEqual(events[-1]["data"]["reason"], "stream-truncated")
        self.assertEqual(events[-1]["source"]["evidenceRef"]["sha256"], hashlib.sha256(dump(receipt)).hexdigest())
        self.assertEqual([e["seq"] for e in events], list(range(1, 7)))

    def test_a_clean_looking_receipt_that_was_cut_is_not_empty(self):
        receipt = doc("ownership-receipt-clean.json")
        receipt["truncations"] = [{"list": "unknown", "unitId": "a", "total": 3}]
        self.assertEqual(kinds(run("receipt", dump(receipt))), ["observation.gap"])

    def test_unknown_values_or_an_authorization_are_a_gap(self):
        for label, change in (
            ("coverage", lambda d: d["units"][0].update(coverage="mostly")),
            ("authorized", lambda d: d.update(executionAuthorization=True)),
            ("no units", lambda d: d.pop("units")),
            ("writers", lambda d: d.update(unattributedWriters="x")),
            ("bad unit id", lambda d: d["units"][0].update(id="not an id!")),
        ):
            with self.subTest(label):
                changed = deepcopy(self.receipt)
                change(changed)
                events = run("receipt", dump(changed))
                self.assertEqual([e["data"]["reason"] for e in events], ["source-unsupported"])

    def test_no_path_or_digest_text_reaches_the_events(self):
        text = json.dumps(self.events)
        for forbidden in ("zz/new.py", "src/a.py", "loose.txt", "sha256:7"):
            self.assertNotIn(forbidden, text)


class GateResultTests(unittest.TestCase):
    NAMES = ("gate-result-certified.json", "gate-result-hazards-found.json", "gate-result-refused.json")

    def test_phases_and_status_equal_the_source_and_the_result_is_class_zero(self):
        for name in self.NAMES:
            with self.subTest(name):
                result = doc(name)
                events = events_from_gate_result(raw(name), path=PATH)
                phases = of_kind(events, "gate.phase")
                self.assertEqual([(e["data"]["phase"], e["data"]["status"]) for e in phases],
                                 [(p["name"], p["status"]) for p in result["phases"]])
                outcome = of_kind(events, "gate.result")
                self.assertEqual(len(outcome), 1)
                self.assertEqual(outcome[0]["data"]["status"], result["status"])
                self.assertEqual(outcome[0]["data"]["operationCount"], result["operationCount"])
                self.assertEqual(outcome[0]["assurance"]["compatibilityClass"], 0)
                self.assertEqual({e["data"]["gateId"] for e in events if e["kind"].startswith("gate.")},
                                 {"sha256:" + hashlib.sha256(raw(name)).hexdigest()})
                for event in phases:
                    self.assertIsNone(event["assurance"]["compatibilityClass"])

    def test_the_fixtures_cover_the_gate_outcomes_the_producer_makes(self):
        self.assertEqual([doc(name)["status"] for name in self.NAMES], ["ok-certified", "hazards-found", "refused"])
        self.assertEqual([p["status"] for p in doc("gate-result-refused.json")["phases"]],
                         ["refused", "not-run", "not-run", "not-run", "ok"])

    def test_a_gate_result_never_yields_a_crossing_or_a_strand(self):
        for name in self.NAMES:
            with self.subTest(name):
                events = events_from_gate_result(raw(name), path=PATH)
                self.assertEqual(set(kinds(events)) - {"observation.gap"}, {"gate.phase", "gate.result"})
        hazardous = doc("gate-result-hazards-found.json")
        self.assertIn("conflicting", {p["classification"] for p in hazardous["analysis"]["interactions"]})

    def test_every_status_keeps_its_value(self):
        for status in ("refused", "busy", "inconclusive", "hazards-found", "ok-analyzed", "ok-certified"):
            with self.subTest(status):
                changed = dict(doc("gate-result-certified.json"), status=status)
                self.assertEqual(of_kind(run("gate", dump(changed)), "gate.result")[0]["data"]["status"], status)

    def test_a_result_without_an_analysis_adds_a_not_observed_gap(self):
        refused = events_from_gate_result(raw("gate-result-refused.json"), path=PATH)
        self.assertEqual(kinds(refused)[-2:], ["gate.result", "observation.gap"])
        self.assertEqual(refused[-1]["data"], {"reason": "not-observed", "strandId": None,
                                               "fromSeq": None, "toSeq": None})
        self.assertNotIn("observation.gap", kinds(run("gate")))

    def test_a_different_class_authorization_or_phase_is_a_gap(self):
        base = doc("gate-result-certified.json")
        for label, change in (
            ("class", lambda d: d["assurance"].update(compatibilityClass="1-syntactic")),
            ("authorized", lambda d: d.update(executionAuthorization=True)),
            ("other gate", lambda d: d.update(gate="other-gate")),
            ("phase", lambda d: d["phases"][1].update(name="improvise")),
            ("status", lambda d: d.update(status="approved")),
            ("operations", lambda d: d.update(operationCount=5000)),
            ("no phases", lambda d: d.pop("phases")),
        ):
            with self.subTest(label):
                changed = deepcopy(base)
                change(changed)
                events = run("gate", dump(changed))
                self.assertEqual([e["data"]["reason"] for e in events], ["source-unsupported"])


class AbsenceTests(unittest.TestCase):
    """procedure_003 at the adapter level: absence is an event or a gap and never counts as clean."""

    @staticmethod
    def clean_count(events):
        return sum(1 for event in events if event["kind"] == "crossing.classified"
                   and event["data"]["classification"] == "independent-candidate")

    def test_an_unknown_pair_and_partial_coverage_are_carried_not_counted_as_independent(self):
        report = doc("analysis-mixed.json")
        events = run("analysis", raw("analysis-mixed.json"))
        crossings = of_kind(events, "crossing.classified")
        self.assertTrue([e for e in crossings if e["data"]["classification"] == "unknown"])
        self.assertEqual(self.clean_count(events), report["summary"]["classifications"]["independent-candidate"])
        self.assertEqual(of_kind(events, "analysis.report")[0]["data"]["summary"]["unknown"],
                         report["summary"]["classifications"]["unknown"])
        partial = [e for e in crossings if "partial" in e["data"]["evidence"]["coverage"]]
        self.assertTrue(all(e["data"]["classification"] != "independent-candidate" for e in partial))






class ReadArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "runs").mkdir()
        (self.root / "runs/a.json").write_bytes(b'{"x":1}')

    def test_reads_a_regular_file_inside_the_root(self):
        self.assertEqual(read_artifact(self.root, "runs/a.json"), b'{"x":1}')

    def test_refuses_escapes_links_missing_oversized_and_non_files(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside)
        (outside / "secret.json").write_bytes(b"{}")
        os.symlink(outside / "secret.json", self.root / "runs/link.json")
        os.symlink(outside, self.root / "dirlink")
        os.symlink(self.root / "runs", self.root / "innerlink")
        (self.root / "big.json").write_bytes(b"0" * 33)
        cases = ("../x.json", "runs/../../x.json", "/abs.json", "", "runs/link.json", "dirlink/secret.json", "innerlink/a.json",
                 "missing.json", "runs", "big.json", "bad\x00name.json")
        for path in cases:
            with self.subTest(path), self.assertRaises(AdapterError):
                read_artifact(self.root, path, limit=32)
        self.assertEqual(read_artifact(self.root, "big.json", limit=33), b"0" * 33)

    def test_adapters_accept_what_read_artifact_returns(self):
        (self.root / "runs/state.json").write_bytes(raw("runtime-state-completed.json"))
        data = read_artifact(self.root, "runs/state.json")
        self.assertEqual(events_from_runtime_state(data, path="runs/state.json")[0]["data"]["phase"], "completed")


class IsolationTests(unittest.TestCase):
    def test_the_module_imports_no_ownership_module_and_names_no_ownership_command(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                prefix = "." * node.level + (node.module or "")
                imported.add(prefix)
                imported.update(f"{prefix}.{alias.name}" for alias in node.names)
        for name in imported:
            self.assertFalse(any(part.startswith("ownership") for part in name.split(".")), name)
        text = MODULE.read_text(encoding="utf-8")
        for command in ("expand-ownership", "check-ownership", "audit-isolation", "report-recovery"):
            self.assertNotIn(command, text)
        self.assertNotIn("import ownership", text)

    def test_the_module_stays_stdlib_plus_the_contract(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        stdlib = {"__future__", "hashlib", "json", "os", "stat", "pathlib", "typing"}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertLessEqual({alias.name.split(".")[0] for alias in node.names}, stdlib)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    self.assertEqual((node.level, node.module), (1, "view_loom"))
                else:
                    self.assertIn(node.module.split(".")[0], stdlib)


if __name__ == "__main__":
    unittest.main()
