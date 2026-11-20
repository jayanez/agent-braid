# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049/T014 cohort driver controls: pins, terms, cap, ledger, order and the cohort loop with doubles.

Nothing native runs: the pre-flight, the admission, the backend and the unit runner are replaced by doubles, and
the host results come from ``harness_host_claude.ClaudeHostDouble``. The SPEC-065 issuance of 2026-11-17 and the
owner's D2 per-cohort cap record are pinned, and so are the owner's 2026-11-20 admission, terms and host-profile
records (``PinnedRecordTests``). The other terms and admission records here are test records built from the
offline arm-C round (``tests.harness_t014_arm_c``).
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import har_t014_cohort as driver  # noqa: E402
import har_t009_attempt as t9  # noqa: E402
from agent_braid import harness_host_claude as hc  # noqa: E402
from agent_braid import harness_hosts as hh  # noqa: E402
from agent_braid import harness_hosts_native as hn  # noqa: E402
from agent_braid import harness_t014_native as tn  # noqa: E402
from agent_braid.system_one import canonical, digest  # noqa: E402
from tests import harness_t005_cohort as t005  # noqa: E402
from tests import harness_t014_arm_c as arm_c  # noqa: E402
from tests import test_harness_host_claude as host  # noqa: E402
from tests.test_harness_hosts import caps, decisions  # noqa: E402

NOW = datetime(2026, 12, 20, 12, 0, tzinfo=timezone.utc)
ISSUANCE_SHA = "e" * 64
ADMISSION_SHA = "f" * 64
_, _, DECISION, C_FILES = arm_c.contrastive_round(t005.build_units())
ARMS = {"A": tn.ARM_SHA256["A"], "B": tn.ARM_SHA256["B"], "C": DECISION.to_dict()["chosenCandidateSha256"]}


def terms_record(**over) -> dict:
    value = {"recordVersion": driver.TERMS_FORMAT, "plan": "P2", "unitCap": 16,
             "window": {"start": "2026-12-15T00:00:00Z", "end": "2027-01-10T00:00:00Z"},
             "issuanceSha256": ISSUANCE_SHA, "admissionSha256": ADMISSION_SHA, "arms": dict(ARMS),
             "armC": {"files": [{"path": p, "text": c.decode()} for p, c in C_FILES.items()],
                      "refinementDecision": DECISION.to_dict()},
             "profileSha256": "d" * 64, "workloadSha256": tn.WORKLOAD_SHA256, "model": "haiku",
             "executionAuthorization": False}
    return value | over


def admission_record(**over) -> dict:
    value = {"recordVersion": driver.ADMISSION_FORMAT, "disposition": "admitted", "issuanceSha256": ISSUANCE_SHA,
             "route": {"host": "claude", "model": "haiku", "route": "subscription", "additionalCashEur": 0},
             "candidates": dict(ARMS), "unitsFreezeSha256": tn.UNITS_FREEZE_SHA256, "executionAuthorization": False}
    return value | over


def pins():
    return mock.patch.multiple(driver, ISSUANCE_SHA256=ISSUANCE_SHA, ADMISSION_SHA256=ADMISSION_SHA)


def terms(**over) -> driver.Terms:
    with pins():
        return driver.parse_terms(canonical(terms_record(**over)))


class PinTests(unittest.TestCase):
    """The issuance, the cap record and the owner records are pinned; a placeholder still refuses, by name."""

    def test_a_placeholder_refuses(self):
        for path, digest in ((driver.PENDING, driver.PENDING), (driver.TERMS, driver.PENDING),
                             (driver.PENDING, driver.TERMS_SHA256)):
            with self.subTest(path=path, digest=digest), self.assertRaises(t9.AttemptRefused) as cm:
                driver.pinned(path, digest, "terms")
            self.assertEqual(cm.exception.reasons, ["terms-not-pinned"])

    def test_the_issuance_is_the_one_spec048_t008_pins(self):
        qualification = "specs/065-native-claude-containment/evidence/qualification/"
        self.assertEqual(driver.ISSUANCE, qualification + "issuance-2026-11-17.json")
        self.assertEqual((driver.ISSUANCE, driver.ISSUANCE_SHA256), (driver.t8.ISSUANCE, driver.t8.ISSUANCE_SHA256))
        self.assertEqual(driver.ENVIRONMENT, qualification + "t009-20261117c/environment.json")
        self.assertEqual(driver.TRUSTED, driver.t8.TRUSTED)
        raw = driver.pinned(driver.ISSUANCE, driver.ISSUANCE_SHA256, "issuance")
        issued = hn.issued_records(raw, **driver.TRUSTED)
        self.assertEqual(issued.expires_at, 1797545969)  # 2026-12-17T22:19:29Z
        self.assertEqual(issued.environment_sha256,
                         json.loads((ROOT / driver.ENVIRONMENT).read_bytes())["environmentSha256"])

    def test_the_cap_decision_is_pinned_and_says_per_cohort_16(self):
        record = json.loads(driver.pinned(driver.CAP_DECISION, driver.CAP_DECISION_SHA256, "cap-decision"))
        self.assertEqual(record["decision"]["disposition"], "d2-max-units-per-cohort")
        self.assertFalse(record.get("executionAuthorization", False))
        self.assertEqual(driver.UNIT_CAP, 16)

    def test_a_pinned_record_must_match_its_hash(self):
        record = "specs/049-harness-evaluation-learning/evidence/registration/t005-units-freeze-20261112.json"
        self.assertEqual(driver.pinned(record, tn.UNITS_FREEZE_SHA256, "x"), (ROOT / record).read_bytes())
        with self.assertRaises(t9.AttemptRefused) as cm:
            driver.pinned(record, "0" * 64, "x")
        self.assertEqual(cm.exception.reasons, ["x-drift"])
        with self.assertRaises(t9.AttemptRefused) as cm:
            driver.pinned("specs/none.json", "0" * 64, "x")
        self.assertEqual(cm.exception.reasons, ["x-missing"])

    def test_the_d2_caps_record_is_the_t008_one(self):
        self.assertEqual((driver.D2_CAPS, driver.D2_CAPS_SHA256), (driver.t8.D2_CAPS, driver.t8.D2_CAPS_SHA256))
        hh.parse_d2_caps((ROOT / driver.D2_CAPS).read_bytes(), expected_sha256=driver.D2_CAPS_SHA256)


class PinnedRecordTests(unittest.TestCase):
    """The owner's 2026-11-20 records: each pinned by path and SHA-256, cross-referenced and accepted by the driver."""

    ARM_C = "6674a8da7aab284f456a9cefd551ebddbb6546873a809ad6a3db48fedca1f7d9"

    def record(self, path, digest, name):
        return json.loads(driver.pinned(path, digest, name))

    def issued(self):
        return hn.issued_records(driver.pinned(driver.ISSUANCE, driver.ISSUANCE_SHA256, "issuance"), **driver.TRUSTED)

    def test_the_three_records_are_pinned_under_the_spec049_evidence(self):
        evidence = "specs/049-harness-evaluation-learning/evidence/"
        self.assertEqual(driver.ADMISSION, evidence + "native-admission/t004-admission-20261120.json")
        self.assertEqual(driver.TERMS, evidence + "registration/t014-terms-20261120.json")
        self.assertEqual(driver.PROFILE_DECISIONS, evidence + "registration/t014-profile-decisions-20261120.json")
        for path, digest, name in ((driver.ADMISSION, driver.ADMISSION_SHA256, "admission"),
                                   (driver.TERMS, driver.TERMS_SHA256, "terms"),
                                   (driver.PROFILE_DECISIONS, driver.PROFILE_DECISIONS_SHA256, "profile-decisions")):
            with self.subTest(name=name):
                value = self.record(path, digest, name)
                self.assertIs(value["executionAuthorization"], False)
                self.assertIs(value.get("promotionAuthorization"), False)

    def test_the_terms_parse_as_plan_p2_with_the_frozen_arm_c_and_the_owner_window(self):
        t = driver.parse_terms(driver.pinned(driver.TERMS, driver.TERMS_SHA256, "terms"))
        self.assertEqual((t.plan, t.cohort_units), ("P2", 15))
        self.assertEqual(t.arms, {"A": tn.ARM_SHA256["A"], "B": tn.ARM_SHA256["B"], "C": self.ARM_C})
        self.assertEqual(t.arm_c_files, C_FILES)
        self.assertEqual(t.refinement.sha256, DECISION.sha256)
        self.assertEqual(t.window, (datetime(2026, 11, 20, tzinfo=timezone.utc),
                                    datetime(2026, 12, 17, 22, 19, 29, tzinfo=timezone.utc)))
        self.assertEqual(int(t.window[1].timestamp()), self.issued().expires_at)  # ends at the issuance expiry
        value = self.record(driver.TERMS, driver.TERMS_SHA256, "terms")
        self.assertEqual(value["armC"]["statement"],
                         "arm C selected offline on synthetic-control probes, evaluated natively")
        self.assertEqual((value["unitCap"], value["capScope"]["sha256"]), (16, driver.CAP_DECISION_SHA256))
        self.assertIs(value["order"]["purgeBetweenUnits"], False)
        self.assertEqual((value["profileDecisions"], value["profileDecisionsSha256"]),
                         (driver.PROFILE_DECISIONS, driver.PROFILE_DECISIONS_SHA256))
        self.assertEqual(t.profile_sha256, digest(value["matchedProfile"]["record"]))  # R7 method, native cohort
        self.assertEqual(value["matchedProfile"]["record"]["containment"]["qualificationSha256"],
                         driver.TRUSTED["containment_sha256"])

    def test_the_admission_names_this_issuance_route_candidates_and_profile(self):
        t = driver.parse_terms(driver.pinned(driver.TERMS, driver.TERMS_SHA256, "terms"))
        driver.check_admission(driver.pinned(driver.ADMISSION, driver.ADMISSION_SHA256, "admission"), t)
        value = self.record(driver.ADMISSION, driver.ADMISSION_SHA256, "admission")
        self.assertEqual(value["ownerStatement"], "Admit (Recommended)")
        self.assertEqual(value["containment"]["validUntil"], "2026-12-17T22:19:29Z")
        self.assertEqual(value["hostProfile"]["profileDecisionsSha256"], driver.PROFILE_DECISIONS_SHA256)
        self.assertEqual(value["cashEnvelope"]["d2CapsSha256"], driver.D2_CAPS_SHA256)
        self.assertEqual(value["source"]["unitsFreeze"], tn.UNITS_FREEZE)

    def test_the_profile_decisions_authorize_claude_only_with_the_t008_11_limits(self):
        raw = driver.pinned(driver.PROFILE_DECISIONS, driver.PROFILE_DECISIONS_SHA256, "profile-decisions")
        found = hh.parse_profile_decisions(raw, expected_sha256=driver.PROFILE_DECISIONS_SHA256)
        self.assertTrue(found["claude"].authorized)
        self.assertFalse(found["codex"].authorized)
        claude = next(r for r in json.loads(raw)["decisions"] if r["item"] == "Claude profile qualification")
        self.assertEqual(claude["verdict"], "qualified-with-limits")
        t008 = json.loads((ROOT / "specs/048-harness-variant-laboratory/evidence/founder-decisions-20261120.json")
                          .read_bytes())
        verdict = next(r for r in t008["decisions"] if r["item"] == "Claude profile verdict")
        self.assertEqual(claude["limits"], verdict["limits"])
        self.assertEqual(json.loads(raw)["qualificationRecords"]["issuanceSha256"], driver.ISSUANCE_SHA256)

    def test_the_admission_passes_inside_the_window_with_the_pinned_records(self):
        issued = self.issued()
        report = {"observed": {"environmentSha256": issued.environment_sha256}}
        parent = Path(tempfile.mkdtemp(prefix="braid-t014-admit-"))
        self.addCleanup(shutil.rmtree, parent, True)
        args = types.SimpleNamespace(out_dir=str(parent / "t014-20261120a"))
        with mock.patch.object(driver, "trusted_inputs", return_value=(issued, object())):
            a = driver.admit(args, report, datetime(2026, 11, 20, 18, 0, tzinfo=timezone.utc))
            self.assertEqual((a.remaining, len(a.pending)), (15, 15))
            self.assertEqual(a.pending, driver.slots(a.registration))  # the registered order, unchanged
            self.assertEqual(a.registration.data["cohort"], "native")
            for when, reason in ((datetime(2026, 11, 19, 23, 0, tzinfo=timezone.utc), "outside-owner-window"),
                                 (datetime(2026, 12, 17, 22, 0, tzinfo=timezone.utc), "outside-owner-window")):
                with self.subTest(when=when), self.assertRaises(t9.AttemptRefused) as cm:
                    driver.admit(args, report, when)
                self.assertEqual(cm.exception.reasons, [reason])


class TermsTests(unittest.TestCase):
    def test_well_formed_terms_parse_and_register_a_native_cohort(self):
        t = terms()
        self.assertEqual((t.plan, t.cohort_units, t.arm_c_files), ("P2", 15, C_FILES))
        registration = driver.register(tn.units(), t)
        self.assertEqual(registration.data["cohort"], "native")
        self.assertEqual(registration.data["refinement"]["sha256"], DECISION.sha256)

    def test_the_cap_is_a_pinned_input(self):
        # owner decision 2026-11-17, D2 per-cohort cap: 16 for T014, T008 units not charged; P2 has 15 cells
        self.assertEqual(driver.UNIT_CAP, 16)
        self.assertEqual(terms().cohort_units, 15)
        for over in (dict(unitCap=17), dict(unitCap=12), dict(unitCap="16"), dict(unitCap=True)):
            with self.subTest(over=over), self.assertRaises(t9.AttemptRefused) as cm:
                terms(**over)
            self.assertEqual(cm.exception.reasons, ["terms-invalid"])

    def test_terms_refuse_any_mismatch(self):
        bad_c = {"path": tn.GUIDANCE_PATH, "text": "something else\n"}
        cases = (dict(plan="P1"), dict(workloadSha256="0" * 64), dict(model="sonnet"),
                 dict(issuanceSha256="0" * 64), dict(admissionSha256="0" * 64), dict(executionAuthorization=True),
                 dict(arms=ARMS | {"B": ARMS["A"]}), dict(arms={"A": ARMS["A"], "B": ARMS["B"]}),
                 dict(armC={"files": [bad_c], "refinementDecision": DECISION.to_dict()}),
                 dict(window={"start": "2027-01-10T00:00:00Z", "end": "2026-12-15T00:00:00Z"}),
                 dict(recordVersion="spec049-t014-terms-v0"), dict(profileSha256="nope"))
        for over in cases:
            with self.subTest(over=over), self.assertRaises(t9.AttemptRefused) as cm:
                terms(**over)
            self.assertEqual(cm.exception.reasons, ["terms-invalid"])

    def test_a_round_that_does_not_select_c_does_not_register(self):
        t = terms(arms=ARMS | {"C": tn.inventory_sha256({tn.GUIDANCE_PATH: b"x\n"})},
                  armC={"files": [{"path": tn.GUIDANCE_PATH, "text": "x\n"}],
                        "refinementDecision": DECISION.to_dict()})
        with self.assertRaises(t9.AttemptRefused) as cm:
            driver.register(tn.units(), t)
        self.assertEqual(cm.exception.reasons, ["registration:refinement-mismatch"])

    def test_the_admission_must_name_this_issuance_route_and_candidates(self):
        t = terms()
        with pins():
            driver.check_admission(canonical(admission_record()), t)
            for over in (dict(disposition="refused"), dict(issuanceSha256="0" * 64),
                         dict(route={"host": "claude", "model": "haiku", "route": "api", "additionalCashEur": 0}),
                         dict(candidates=ARMS | {"C": ARMS["B"]}), dict(unitsFreezeSha256="0" * 64)):
                with self.subTest(over=over), self.assertRaises(t9.AttemptRefused) as cm:
                    driver.check_admission(canonical(admission_record(**over)), t)
                self.assertEqual(cm.exception.reasons, ["admission-mismatch"])
            with self.assertRaises(t9.AttemptRefused) as cm:
                driver.check_admission(canonical(admission_record(executionAuthorization=True)), t)
            self.assertEqual(cm.exception.reasons, ["admission-invalid"])

    def test_the_window_and_the_issued_validity_bound_every_unit(self):
        expires = int(datetime(2027, 1, 5, tzinfo=timezone.utc).timestamp())
        t, issued = terms(), types.SimpleNamespace(expires_at=expires)
        driver.check_window(NOW, issued, t)
        for when, reason in ((datetime(2026, 12, 14, tzinfo=timezone.utc), "outside-owner-window"),
                             (datetime(2027, 1, 9, 23, 40, tzinfo=timezone.utc), "outside-owner-window"),
                             (datetime(2027, 1, 4, 23, 40, tzinfo=timezone.utc), "qualification-expiring")):
            with self.subTest(when=when), self.assertRaises(t9.AttemptRefused) as cm:
                driver.check_window(when, issued, t)
            self.assertEqual(cm.exception.reasons, [reason])


class OrderTests(unittest.TestCase):
    def test_the_registered_latin_square_order_has_fifteen_distinct_cells(self):
        registration = driver.register(tn.units(), terms())
        order = driver.slots(registration)
        self.assertEqual(len(order), 15)
        self.assertEqual(len(set(order)), 15)
        expected = registration.to_dict()["order"]
        for case in tn.HOLDOUT:
            self.assertEqual([a for c, a in order if c == case], expected[case])
        # rotated within the C03 family: three consecutive units start with A, B and C
        self.assertEqual([expected[c][0] for c in ("L1-C03-a", "L1-C03-b", "L1-C03-c")], ["A", "B", "C"])
        self.assertEqual([c for c, _ in order], sorted(c for c, _ in order))


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="braid-t014-ledger-"))
        self.addCleanup(shutil.rmtree, self.parent, True)

    def test_units_and_slots_are_summed_over_every_attempt_and_a_label_is_used_once(self):
        self.assertEqual(driver.started(self.parent), (0, []))
        driver.write_ledger(self.parent / "t014-20261220a", [], create=True)
        driver.write_ledger(self.parent / "t014-20261220a", ["L1-C01-a:A", "L1-C01-a:B"])
        driver.write_ledger(self.parent / "t014-20261221a", ["L1-C01-a:C"], create=True)
        (self.parent / "t014-20261221b").mkdir()  # a crash before its ledger counts nothing
        self.assertEqual(driver.started(self.parent), (3, ["L1-C01-a:A", "L1-C01-a:B", "L1-C01-a:C"]))
        with self.assertRaises(t9.AttemptRefused) as cm:
            driver.write_ledger(self.parent / "t014-20261220a", [], create=True)
        self.assertEqual(cm.exception.reasons, ["attempt-label-used"])

    def test_an_unreadable_planted_or_inconsistent_ledger_refuses(self):
        cases = {"bad-json": "{", "count": '{"unitsStarted": 2, "slots": ["a"]}', "text": '{"unitsStarted": "1"}',
                 "list": "[]", "noslots": '{"unitsStarted": 0}'}
        for name, content in cases.items():
            with self.subTest(case=name):
                entry = self.parent / name
                entry.mkdir()
                (entry / driver.LEDGER).write_text(content)
                with self.assertRaises(t9.AttemptRefused) as cm:
                    driver.started(self.parent)
                self.assertEqual(cm.exception.reasons, [f"{driver.LEDGER}-unreadable"])
                shutil.rmtree(entry)
        for label in ("a", "b"):  # the same slot started twice refuses
            driver.write_ledger(self.parent / label, ["L1-C01-a:A"], create=True)
        with self.assertRaises(t9.AttemptRefused):
            driver.started(self.parent)
        shutil.rmtree(self.parent / "b")
        (self.parent / "link").symlink_to(self.parent / "a")
        with self.assertRaises(t9.AttemptRefused):
            driver.started(self.parent)


class FakeBackend:
    def __init__(self, *args, **kwargs):
        self.qualification = types.SimpleNamespace(sha256="b" * 64)
        self.host_qualification = types.SimpleNamespace(sha256="c" * 64)
        self.run_evidence = []
        self.closed = False

    def close(self):
        self.closed = True


def observation(**over):
    at = int(NOW.timestamp())
    value = dict(host="claude", observed_at=at - 30, plan="max", route="subscription", five_hour_percent=20,
                 five_hour_resets_at=at + 3 * 3600, weekly_percent=10, weekly_resets_at=at + 4 * 86400,
                 extra_usage_enabled=False)
    return hh.QuotaObservation(**(value | over))


class CohortTests(unittest.TestCase):
    """The loop with doubles: order, ledger before launch, grading, the report and the stops."""

    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="braid-t014-cohort-"))
        self.addCleanup(shutil.rmtree, self.parent, True)
        self.terms = terms()
        issued = types.SimpleNamespace(environment_sha256="7" * 64, expires_at=int(NOW.timestamp()) + 30 * 86400,
                                       host=b"{}", host_sha256="c" * 64, containment=b"{}", containment_sha256="b" * 64)

        def admitted(parent):
            t, units = self.terms, tn.units()
            registration = driver.register(units, t)
            pending, remaining = driver.cohort_left(t, registration, parent)
            return driver.Admitted(issued, types.SimpleNamespace(claude_sha256="a" * 64), decisions(), caps(), t,
                                   units, registration, pending, remaining)
        self.admitted = admitted
        self.launches = []

    def args(self, attempt, units=15):
        return types.SimpleNamespace(attempt=attempt, units=units, founder_go=True, run_root=str(self.parent),
                                     config_dir=str(self.parent), arena_parent=str(self.parent),
                                     operator_account="founder", out_dir=str(self.parent / attempt))

    def unit(self, texts=None, fail_at=None, refuse_at=None):
        """A ``run_native_unit`` double: launches through ``on_launch``, answers from ``texts`` per cell."""
        def run_unit(*, run, manifest, attempt_id, on_launch, before, **_):
            index = len(self.launches)
            if refuse_at == index:
                raise hh.HostGateError("weekly-stop")
            ledger = json.loads((self.parent / attempt_id[:14] / driver.LEDGER).read_text())
            on_launch()
            self.launches.append((manifest.data["task"]["id"], ledger["unitsStarted"]))
            if fail_at == index:
                raise hc.ClaudeHostError("transport-failed")
            case = manifest.data["task"]["id"]
            text = (texts or {}).get(index, tn.expected_output(case).decode())
            result = host.run([host.init(), host.assistant({"type": "text", "text": text}), host.result()],
                              attempt_id=attempt_id)
            return hn.UnitOutcome(types.SimpleNamespace(completed=True, breach=None), result)
        return run_unit

    def cohort(self, attempt, run_unit, units=15):
        args = self.args(attempt, units)
        with mock.patch.object(t9, "preflight", return_value={"verdict": "ready", "observed": {}}), \
                mock.patch.object(driver, "admit", lambda a, r, n: self.admitted(self.parent)), \
                mock.patch.object(driver.t8, "read_observation", lambda *a, **k: observation()), \
                mock.patch.object(driver._probes, "credential_inventory", return_value=[]), \
                mock.patch.object(driver._probes, "make_f4_probe_runner", return_value=None):
            return driver.run_cohort(args, None, ask=lambda prompt: attempt, say=lambda *a: None,
                                     clock=lambda: NOW, backend_factory=FakeBackend, run_unit=run_unit)

    def test_the_cohort_runs_the_registered_order_and_reports_every_cell(self):
        report = self.cohort("t014-20261220a", self.unit(texts={1: "done: s1 s2\nrepeated: none"}))
        order = driver.slots(driver.register(tn.units(), terms()))
        self.assertEqual([c for c, _ in self.launches], [c for c, _ in order])
        self.assertEqual([n for _, n in self.launches], list(range(15)))  # ledger is written before each launch
        self.assertEqual(report["verdict"], "cohort-finished")
        outcomes = [r["outcome"] for r in report["hostRuns"]]
        self.assertEqual(outcomes.count("correct"), 14)
        self.assertEqual(outcomes[1], "incorrect")
        evaluated = report["evaluation"]
        self.assertEqual(len(evaluated["rows"]), 15)
        self.assertFalse(evaluated["verdictEligible"] or report["verdictEligible"] or report["executionAuthorization"])
        self.assertTrue(evaluated["costs"]["claimBlocked"])
        text = json.dumps(report)
        self.assertNotIn("repeated: none", text)
        self.assertNotIn("done: s1", text)
        ledger = json.loads((self.parent / "t014-20261220a" / driver.LEDGER).read_text())
        self.assertEqual(ledger["unitsStarted"], 15)

    def test_a_later_label_resumes_at_the_first_slot_not_started_and_reports_all_rows(self):
        first = self.cohort("t014-20261220a", self.unit(), units=4)
        self.assertEqual(len(first["evaluation"]["rows"]), 15)
        self.launches.clear()
        second = self.cohort("t014-20261221a", self.unit(), units=15)
        order = driver.slots(driver.register(tn.units(), terms()))
        self.assertEqual([c for c, _ in self.launches], [c for c, _ in order[4:]])
        graded = [r for r in second["evaluation"]["rows"] if r["outcome"] != "not-attempted"]
        self.assertEqual(len(graded), 15)
        with self.assertRaises(t9.AttemptRefused) as cm:
            self.cohort("t014-20261222a", self.unit())
        self.assertEqual(cm.exception.reasons, ["cohort-units-exhausted"])

    def test_the_cap_from_the_terms_ends_the_cohort(self):
        with mock.patch.object(driver, "UNIT_CAP", 4), mock.patch.object(driver, "PLANS", {"P2": 4}):
            self.terms = terms(unitCap=4)
            self.cohort("t014-20261220a", self.unit())
            self.assertEqual(len(self.launches), 4)
            with self.assertRaises(t9.AttemptRefused) as cm:
                self.cohort("t014-20261221a", self.unit())
            self.assertEqual(cm.exception.reasons, ["cohort-units-exhausted"])

    def test_the_ledger_refuses_a_seventeenth_unit(self):
        registration = driver.register(tn.units(), self.terms)
        driver.write_ledger(self.parent / "t014-20261220a", [f"x{i}" for i in range(16)], create=True)
        with self.assertRaises(t9.AttemptRefused) as cm:
            driver.cohort_left(self.terms, registration, self.parent)
        self.assertEqual(cm.exception.reasons, ["cohort-units-exhausted"])
        shutil.rmtree(self.parent / "t014-20261220a")
        driver.write_ledger(self.parent / "t014-20261220a", [f"x{i}" for i in range(14)], create=True)  # P2: 15 cells
        self.assertEqual(driver.cohort_left(self.terms, registration, self.parent)[1], 1)

    def test_a_refusal_before_launch_spends_nothing_and_stops(self):
        report = self.cohort("t014-20261220a", self.unit(refuse_at=2))
        self.assertEqual((report["verdict"], report["stopped"], len(report["hostRuns"])),
                         ("cohort-stopped", "weekly-stop", 2))
        self.assertEqual(json.loads((self.parent / "t014-20261220a" / driver.LEDGER).read_text())["unitsStarted"], 2)

    def test_a_host_error_after_launch_keeps_an_ungraded_row_and_stops(self):
        report = self.cohort("t014-20261220a", self.unit(fail_at=1))
        self.assertEqual((report["stopped"], [r["outcome"] for r in report["hostRuns"]]),
                         ("transport-failed", ["correct", "ungraded"]))
        rows = json.loads((self.parent / "t014-20261220a" / driver.ROWS).read_text())
        self.assertEqual(len(rows), 2)

    def test_a_cancel_or_a_missing_go_flag_never_starts(self):
        args = self.args("t014-20261220a")
        with mock.patch.object(t9, "preflight", return_value={"verdict": "ready", "observed": {}}), \
                mock.patch.object(driver, "admit", lambda a, r, n: self.admitted(self.parent)):
            with self.assertRaises(t9.AttemptRefused) as cm:
                driver.run_cohort(args, None, ask=lambda p: "no", say=lambda *a: None, clock=lambda: NOW,
                                  backend_factory=FakeBackend, run_unit=self.unit())
            self.assertEqual(cm.exception.reasons, ["operator-cancelled"])
            args.founder_go = False
            with self.assertRaises(t9.AttemptRefused) as cm:
                driver.run_cohort(args, None, ask=lambda p: args.attempt, say=lambda *a: None, clock=lambda: NOW,
                                  backend_factory=FakeBackend, run_unit=self.unit())
            self.assertEqual(cm.exception.reasons, ["founder-go-flag-missing"])
        self.assertEqual(self.launches, [])
        self.assertFalse((self.parent / "t014-20261220a").exists())


if __name__ == "__main__":
    unittest.main()
