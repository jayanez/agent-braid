# SPDX-License-Identifier: AGPL-3.0-only
"""T008 lab driver controls: records, window, expiry, reading parsing; nothing native runs."""
import contextlib
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import har_t008_unit as driver  # noqa: E402
import har_t009_attempt as t9  # noqa: E402
from agent_braid import harness_hosts as hh  # noqa: E402
from agent_braid import harness_hosts_native as hn  # noqa: E402

ISSUED = hn.issued_records((ROOT / driver.ISSUANCE).read_bytes(), **driver.TRUSTED)
QUALIFICATION = "specs/065-native-claude-containment/evidence/qualification/"
SUPERSEDED_ISSUANCE = QUALIFICATION + "issuance-2026-11-06.json"
SUPERSEDED_DECISIONS = "specs/048-harness-variant-laboratory/evidence/founder-decisions-20261106.json"


class DriverTests(unittest.TestCase):
    def refused(self, when):
        with self.assertRaises(t9.AttemptRefused) as cm:
            driver.check_window(when, ISSUED)
        return cm.exception.reasons

    def test_units_are_limited_to_the_founders_window_and_the_issued_validity(self):
        self.assertEqual(self.refused(datetime(2026, 11, 6, 12, tzinfo=timezone.utc)), ["outside-founder-window"])
        self.assertEqual(self.refused(datetime(2026, 12, 1, tzinfo=timezone.utc)), ["outside-founder-window"])
        driver.check_window(datetime(2026, 11, 10, 12, tzinfo=timezone.utc), ISSUED)
        # the founder's terms of 2026-11-13 are those of 2026-11-06: same window, same cap
        self.assertEqual(driver.WINDOW, (datetime(2026, 11, 9, 20, 30, tzinfo=timezone.utc),
                                         datetime(2026, 11, 30, 23, 59, tzinfo=timezone.utc)))

    def test_the_cohort_is_capped_below_the_d2_maximum(self):
        self.assertEqual(driver.MAX_UNITS, 4)
        self.assertEqual(driver.parser().get_default("units"), 4)

    def test_reset_instants_parse_or_are_refused(self):
        day = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
        self.assertIsNone(driver._local(day, "25:99", driver._CLOCK))
        self.assertIsNone(driver._local(day, "2026-13-40 10:00", driver._DATE_CLOCK))
        self.assertIsInstance(driver._local(day, "2026-11-16 21:00", driver._DATE_CLOCK), int)

    def test_the_pinned_founder_record_parses_to_claude_authorized_and_codex_refused(self):
        raw = (ROOT / driver.FOUNDER_DECISIONS).read_bytes()
        decisions = hh.parse_profile_decisions(raw, expected_sha256=driver.FOUNDER_DECISIONS_SHA256)
        self.assertTrue(decisions["claude"].authorized)
        self.assertEqual(decisions["codex"].reason, "not-qualified: not installed")


    def test_a_unit_must_be_able_to_end_inside_the_window(self):
        end = driver.WINDOW[1]
        self.assertEqual(self.refused(end - timedelta(minutes=29)), ["outside-founder-window"])
        driver.check_window(end - timedelta(minutes=30), ISSUED)


class RecordTests(unittest.TestCase):
    """SPEC-065 T013 superseded the 2026-11-06 issuance (void on macOS 26B131); the founder re-authorized the same
    terms on the 2026-11-13 records (founder-decisions-20261113.json). The driver names only those."""

    def test_the_driver_names_the_2026_11_13_records(self):
        self.assertEqual(driver.ISSUANCE, QUALIFICATION + "issuance-2026-11-13.json")
        self.assertEqual(driver.ISSUANCE_SHA256, sha256((ROOT / driver.ISSUANCE).read_bytes()).hexdigest())
        self.assertEqual(driver.ENVIRONMENT, QUALIFICATION + "t009-20261113c/environment.json")
        self.assertEqual(driver.TRUSTED, {
            "containment_sha256": "fa59fbae9286f0794331aedcebe782b99767819dc4a30f37a08713509be9fa6a",
            "host_sha256": "9022b771382a239be3a4d399dfb9c949ef29f4276aeebb0b5db735e9a67a847f"})
        self.assertEqual(driver.FOUNDER_DECISIONS,
                         "specs/048-harness-variant-laboratory/evidence/founder-decisions-20261113.json")
        self.assertEqual(sha256((ROOT / driver.FOUNDER_DECISIONS).read_bytes()).hexdigest(),
                         driver.FOUNDER_DECISIONS_SHA256)
        self.assertEqual(ISSUED.environment_sha256, json.loads((ROOT / driver.ENVIRONMENT).read_bytes())
                         ["environmentSha256"])
        self.assertEqual(ISSUED.expires_at, 1797178485)

    def test_the_superseded_issuance_is_refused(self):
        with self.assertRaises(hn.NativeWiringError) as cm:
            hn.issued_records((ROOT / SUPERSEDED_ISSUANCE).read_bytes(), **driver.TRUSTED)
        self.assertEqual(cm.exception.reason, "qualification-drift")
        with mock.patch.object(driver, "ISSUANCE", SUPERSEDED_ISSUANCE), \
                self.assertRaises(hn.NativeWiringError) as cm:
            driver.trusted_inputs(None)
        self.assertEqual(cm.exception.reason, "issuance-drift")

    def test_the_superseded_founder_record_is_refused(self):
        with mock.patch.object(driver, "FOUNDER_DECISIONS", SUPERSEDED_DECISIONS), \
                self.assertRaises(hh.HostGateError) as cm:
            driver.decision_inputs()
        self.assertEqual(cm.exception.reason, "record-drift")

    def test_the_founder_record_names_exactly_the_records_the_driver_trusts(self):
        bound = json.loads((ROOT / driver.FOUNDER_DECISIONS).read_bytes())["qualificationRecords"]
        self.assertEqual(bound, {
            "issuance": driver.ISSUANCE, "issuanceSha256": driver.ISSUANCE_SHA256,
            "bundle": QUALIFICATION + "t009-20261113c/",
            "bundleSha256": "c241079d7760c1b7144e9f39ea2282973d2de3a9078359153564553e684f4bb7",
            "containmentSha256": driver.TRUSTED["containment_sha256"], "hostSha256": driver.TRUSTED["host_sha256"],
            "environmentSha256": ISSUED.environment_sha256, "expiresAt": ISSUED.expires_at})

    def test_the_founder_record_keeps_the_terms_and_grants_nothing(self):
        value = json.loads((ROOT / driver.FOUNDER_DECISIONS).read_bytes())
        self.assertEqual(value["supersedes"].split(" ")[0], SUPERSEDED_DECISIONS)
        for key in ("executionAuthorization", "nativeAdmission", "promotionAuthorization"):
            self.assertIs(value[key], False)
        answers = {a["id"]: a for a in value["founderAnswers"]}
        self.assertEqual(answers["T008-6"]["answer"], "Mismos términos, nuevos registros (Recommended)")
        self.assertEqual(answers["T008-7"]["answer"], "Lanzador root sin GUI (Recommended)")


class LedgerTests(unittest.TestCase):
    """The founder's cap of four units holds for the whole cohort: every attempt counts its started units in its own
    directory, and a new label never resets the count."""

    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="braid-t008-ledger-"))
        self.addCleanup(shutil.rmtree, self.parent, True)

    def test_units_are_summed_over_every_attempt_and_a_label_is_used_once(self):
        self.assertEqual(driver.units_started(self.parent), 0)
        self.assertEqual(driver.units_started(self.parent / "missing"), 0)
        driver.write_ledger(self.parent / "t008-20261114a", 0, create=True)
        driver.write_ledger(self.parent / "t008-20261114a", 3)
        (self.parent / "t008-20261114b").mkdir()  # a crash before its ledger: counts nothing
        self.assertEqual(driver.units_started(self.parent), 3)
        with self.assertRaises(t9.AttemptRefused) as cm:
            driver.write_ledger(self.parent / "t008-20261114a", 0, create=True)
        self.assertEqual(cm.exception.reasons, ["attempt-label-used"])
        self.assertEqual(json.loads((self.parent / "t008-20261114a" / driver.LEDGER).read_text()),
                         {"unitsStarted": 3})

    def test_an_unreadable_or_planted_ledger_refuses(self):
        cases = {"bad-json": "{", "negative": '{"unitsStarted": -1}', "text": '{"unitsStarted": "4"}', "list": "[]"}
        for name, content in cases.items():
            with self.subTest(case=name):
                entry = self.parent / name
                entry.mkdir()
                (entry / driver.LEDGER).write_text(content)
                with self.assertRaises(t9.AttemptRefused) as cm:
                    driver.units_started(self.parent)
                self.assertEqual(cm.exception.reasons, ["unit-ledger-unreadable"])
                shutil.rmtree(entry)
        (self.parent / "link").symlink_to(self.parent)
        with self.assertRaises(t9.AttemptRefused):
            driver.units_started(self.parent)


class DryRunTests(unittest.TestCase):
    """The dry run (the launcher's passwordless check) runs every no-quota check the cohort runs: the environment
    hash recomputed in the lab's own session against the issued one, the window, the records and the unit ledger."""

    NOW = datetime(2026, 11, 14, 12, tzinfo=timezone.utc)

    def setUp(self):
        self.parent = Path(tempfile.mkdtemp(prefix="braid-t008-dry-"))
        self.addCleanup(shutil.rmtree, self.parent, True)
        self.argv = ["--attempt", "t008-20261114a", "--operator-account", "founder", "--claude", "/c",
                     "--interpreter", "/p", "--interpreter-root", "/r", "--config-dir", "/cfg", "--run-root", "/run",
                     "--arena-parent", "/arena", "--out-dir", str(self.parent / "t008-20261114a")]

    def patched(self, observed=None):
        observed = {"environmentSha256": ISSUED.environment_sha256} if observed is None else observed
        report = {"verdict": "ready", "checks": [], "failed": [], "observed": observed,
                  "executionAuthorization": False}
        return contextlib.ExitStack(), report

    def dry_run(self, observed=None, now=NOW):
        stack, report = self.patched(observed)
        out = io.StringIO()
        with stack:
            stack.enter_context(mock.patch.object(driver.t9, "preflight", return_value=report))
            stack.enter_context(mock.patch.object(driver, "trusted_inputs", return_value=(ISSUED, {}, None)))
            stack.enter_context(contextlib.redirect_stdout(out))
            code = driver.main(self.argv + ["--dry-run"], system=object(), clock=lambda: now)
        return code, json.loads(out.getvalue())

    def test_the_issued_environment_is_ready(self):
        code, report = self.dry_run()
        self.assertEqual((code, report["verdict"], report["wiring"]), (0, "ready", "ok"))
        self.assertEqual((report["issuedExpiresAt"], report["unitsRemaining"]), (ISSUED.expires_at, 4))
        self.assertIs(report["executionAuthorization"], False)

    def test_another_environment_or_none_refuses(self):
        for observed in ({"environmentSha256": "e91007d8626998d49ccb574bc241752bccc5134616598dd76b8f63630f9d818a"},
                         {}):
            with self.subTest(observed=observed):
                code, report = self.dry_run(observed)
                self.assertEqual((code, report["verdict"], report["wiring"]), (2, "refused", "environment-drift"))

    def test_outside_the_window_refuses(self):
        code, report = self.dry_run(now=datetime(2026, 12, 1, tzinfo=timezone.utc))
        self.assertEqual((code, report["wiring"]), (2, "outside-founder-window"))

    def test_a_superseded_founder_record_refuses(self):
        with mock.patch.object(driver, "FOUNDER_DECISIONS", SUPERSEDED_DECISIONS):
            code, report = self.dry_run()
        self.assertEqual((code, report["wiring"]), (2, "decision-record:record-drift"))

    def test_spent_units_are_carried_over_and_exhaust_the_cohort(self):
        driver.write_ledger(self.parent / "t008-20261113a", 3, create=True)
        self.assertEqual(self.dry_run()[1]["unitsRemaining"], 1)
        driver.write_ledger(self.parent / "t008-20261113a", 4)
        code, report = self.dry_run()
        self.assertEqual((code, report["wiring"]), (2, "cohort-units-exhausted"))

    def run_cohort(self, **patches):
        stack, report = self.patched()
        ask = mock.Mock(side_effect=AssertionError("asked the operator"))
        with stack:
            stack.enter_context(mock.patch.object(driver.t9, "preflight", return_value=report))
            stack.enter_context(mock.patch.object(driver, "trusted_inputs", return_value=(ISSUED, {}, None)))
            for name, value in patches.items():
                stack.enter_context(mock.patch.object(driver, name, value))
            with self.assertRaises(t9.AttemptRefused) as cm:
                driver.run_cohort(driver.parser().parse_args(self.argv + ["--founder-go"]), object(), ask=ask,
                                  say=lambda _: None, clock=lambda: self.NOW)
        ask.assert_not_called()
        return cm.exception.reasons

    def test_a_cohort_on_a_superseded_record_refuses_before_any_prompt(self):
        self.assertEqual(self.run_cohort(FOUNDER_DECISIONS=SUPERSEDED_DECISIONS), ["decision-record:record-drift"])

    def test_an_exhausted_cohort_refuses_before_any_prompt(self):
        driver.write_ledger(self.parent / "t008-20261113a", 4, create=True)
        self.assertEqual(self.run_cohort(), ["cohort-units-exhausted"])

    def test_ctrl_c_before_the_units_still_prints_one_report(self):
        for reported, printed in ((False, True), (True, False)):
            interrupt = KeyboardInterrupt()
            if reported:
                interrupt.t008_reported = True
            out = io.StringIO()
            with self.subTest(reported=reported), mock.patch.object(driver, "run_cohort", side_effect=interrupt), \
                    contextlib.redirect_stdout(out):
                self.assertEqual(driver.main(self.argv + ["--founder-go"], system=object()), 130)
                self.assertEqual(bool(out.getvalue()), printed)
                if printed:
                    self.assertEqual(json.loads(out.getvalue())["verdict"], "cohort-aborted")


if __name__ == "__main__":
    unittest.main()
