# SPDX-License-Identifier: AGPL-3.0-only
"""Quota gate controls (SPEC-065 T004); synthetic readings only, no quota source read."""
import ast
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import unittest

from agent_braid import harness_quota as quota

NOW = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
LATER = NOW + timedelta(minutes=20)


def reading(at: datetime = NOW, five: int = 31, weekly: int = 41, extra: bool = False,
            **over) -> dict:
    value = {"source": quota.SOURCE, "observedAt": at.strftime("%Y-%m-%dT%H:%M:%SZ"),
             "fiveHourPercent": five, "weeklyPercent": weekly, "extraUsageEnabled": extra}
    value.update(over)
    return value


def cohort(units: int = 0, weekly: int = 0) -> dict:
    return {"unitsUsed": units, "cohortWeeklyPercent": weekly}


class GateTest(unittest.TestCase):
    def assertProceeds(self, decision: quota.QuotaDecision) -> None:
        self.assertTrue(decision.proceed)
        self.assertEqual(decision.reason, "within-caps")
        self.assertFalse(decision.executionAuthorization)

    def assertRefused(self, decision: quota.QuotaDecision, reason: str) -> None:
        self.assertFalse(decision.proceed)
        self.assertEqual(decision.reason, reason)
        self.assertFalse(decision.executionAuthorization)


class AdmitTests(GateTest):
    def test_fresh_reading_within_caps_proceeds(self):
        decision = quota.admit(reading(), NOW + timedelta(minutes=5), cohort(15, 14))
        self.assertProceeds(decision)
        self.assertEqual(decision.evidence["pre"], reading())
        self.assertEqual(decision.evidence["cohort"], cohort(15, 14))

    def test_boundaries_admitted(self):
        self.assertProceeds(quota.admit(reading(five=89, weekly=80), NOW, cohort()))

    def test_missing_reading(self):
        self.assertRefused(quota.admit(None, NOW, cohort()), "missing-pre-reading")

    def test_unparseable_readings(self):
        bad = [
            "31 %", [], {}, reading(extra="no"), reading(five=101), reading(weekly=-1),
            reading(five=31.0), reading(five=True), reading(weekly="41"),
            reading(observedAt="2026-11-01T12:00:00"), reading(observedAt="yesterday Z"),
            reading(observedAt=1761998400), reading(observedAt="2026-11-01T12:00:00+01:00Z"),
            reading(observedAt="2026-11-01Z"), reading(observedAt="2026-W44-7T12:00:00Z"),
            reading(observedAt="20261101T120000Z"), reading(observedAt="2026-11-01 12:00:00Z"),
            reading(observedAt="2026-11-01T12:00Z"), reading(observedAt="2026-13-01T12:00:00Z"),
            {k: v for k, v in reading().items() if k != "weeklyPercent"},
            reading(resetsAt="2026-11-01T17:00:00Z"),
        ]
        for raw in bad:
            with self.subTest(raw=raw):
                self.assertRefused(quota.admit(raw, NOW, cohort()), "unparseable-reading")

    def test_fractional_seconds_accepted(self):
        decision = quota.admit(reading(observedAt="2026-11-01T11:59:59.5Z"), NOW, cohort())
        self.assertProceeds(decision)
        self.assertEqual(decision.evidence["pre"]["observedAt"], "2026-11-01T11:59:59.500000Z")

    def test_unsupported_source(self):
        self.assertRefused(quota.admit(reading(source="statusline"), NOW, cohort()),
                           "unsupported-reading-source")

    def test_stale_reading(self):
        at = NOW - timedelta(minutes=5, seconds=1)
        self.assertRefused(quota.admit(reading(at), NOW, cohort()), "stale-pre-reading")
        self.assertProceeds(quota.admit(reading(NOW - timedelta(minutes=5)), NOW, cohort()))

    def test_future_dated_reading(self):
        at = NOW + timedelta(seconds=1)
        self.assertRefused(quota.admit(reading(at), NOW, cohort()), "future-dated-pre-reading")

    def test_weekly_above_80(self):
        self.assertRefused(quota.admit(reading(weekly=81), NOW, cohort()), "weekly-above-stop")

    def test_extra_usage_enabled(self):
        self.assertRefused(quota.admit(reading(extra=True), NOW, cohort()), "extra-usage-enabled")

    def test_five_hour_at_or_above_90(self):
        for five in (90, 100):
            with self.subTest(five=five):
                self.assertRefused(quota.admit(reading(five=five), NOW, cohort()),
                                   "five-hour-at-start-limit")

    def test_unit_cap(self):
        for units in (16, 17):
            with self.subTest(units=units):
                self.assertRefused(quota.admit(reading(), NOW, cohort(units)), "unit-cap-reached")

    def test_cohort_weekly_cap(self):
        for weekly in (15, 16):
            with self.subTest(weekly=weekly):
                self.assertRefused(quota.admit(reading(), NOW, cohort(weekly=weekly)),
                                   "cohort-weekly-cap-reached")

    def test_cohort_state_absent(self):
        self.assertRefused(quota.admit(reading(), NOW, None), "cohort-state-absent")

    def test_cohort_state_invalid(self):
        for raw in ({}, cohort(-1), cohort(weekly=101), cohort(True), {"unitsUsed": 0},
                    {**cohort(), "extra": 1}, (0, 0)):
            with self.subTest(raw=raw):
                self.assertRefused(quota.admit(reading(), NOW, raw), "cohort-state-invalid")

    def test_reading_checked_before_cohort(self):
        self.assertRefused(quota.admit(None, NOW, None), "missing-pre-reading")

    def test_naive_or_missing_clock_rejected(self):
        for now in (NOW.replace(tzinfo=None), "2026-11-01T12:00:00Z", None):
            with self.subTest(now=now), self.assertRaises(TypeError):
                quota.admit(reading(), now, cohort())

    def test_clock_in_other_zone_normalised(self):
        cet = timezone(timedelta(hours=1))
        self.assertProceeds(quota.admit(reading(), NOW.astimezone(cet), cohort()))

    def test_decision_is_immutable_and_never_authorizes(self):
        decision = quota.admit(reading(), NOW, cohort())
        with self.assertRaises(FrozenInstanceError):
            decision.proceed = False
        with self.assertRaises(TypeError):
            decision.evidence["kind"] = "other"
        with self.assertRaises(TypeError):
            quota.QuotaDecision(True, "x", {}, executionAuthorization=True)


class SettleTests(GateTest):
    def test_within_caps_records_post_and_delta(self):
        decision = quota.settle(reading(), reading(LATER, five=41, weekly=43), LATER, cohort(3, 12))
        self.assertProceeds(decision)
        evidence = decision.evidence
        self.assertEqual(evidence["post"], reading(LATER, five=41, weekly=43))
        self.assertEqual((evidence["fiveHourDelta"], evidence["weeklyDelta"]), (10, 2))
        self.assertEqual(evidence["cohort"], cohort(4, 14))

    def test_cohort_exactly_15_proceeds(self):
        self.assertProceeds(quota.settle(reading(), reading(LATER, weekly=44), LATER,
                                         cohort(weekly=12)))

    def test_session_above_10_percent_stops(self):
        decision = quota.settle(reading(), reading(LATER, five=42), LATER, cohort())
        self.assertRefused(decision, "session-above-five-hour-cap")
        self.assertEqual(decision.evidence["fiveHourDelta"], 11)

    def test_cohort_above_15_weekly_stops(self):
        decision = quota.settle(reading(), reading(LATER, weekly=45), LATER, cohort(weekly=12))
        self.assertRefused(decision, "cohort-above-weekly-cap")
        self.assertEqual(decision.evidence["cohort"]["cohortWeeklyPercent"], 16)

    def test_post_reading_controls(self):
        span_end = NOW + quota.MAX_READING_SPAN
        cases = [
            (None, LATER, "missing-post-reading"),
            (reading(LATER, five="x"), LATER, "unparseable-reading"),
            (reading(LATER), LATER + timedelta(minutes=6), "stale-post-reading"),
            (reading(LATER), LATER - timedelta(seconds=1), "future-dated-post-reading"),
            (reading(NOW - timedelta(seconds=1)), NOW, "post-reading-not-after-pre-reading"),
            (reading(NOW), NOW, "post-reading-not-after-pre-reading"),
            (reading(span_end + timedelta(seconds=1)), span_end + timedelta(seconds=1),
             "reading-span-too-long"),
            (reading(LATER, five=5), LATER, "usage-window-reset"),
            (reading(LATER, weekly=2), LATER, "usage-window-reset"),
            (reading(LATER, extra=True), LATER, "extra-usage-enabled"),
        ]
        for post, now, reason in cases:
            with self.subTest(reason=reason, now=now):
                self.assertRefused(quota.settle(reading(), post, now, cohort()), reason)

    def test_post_reading_start_conditions_stop(self):
        cases = [(reading(five=85), reading(LATER, five=90), "five-hour-at-start-limit"),
                 (reading(weekly=79), reading(LATER, weekly=81), "weekly-above-stop")]
        for pre, post, reason in cases:
            with self.subTest(reason=reason):
                self.assertRefused(quota.settle(pre, post, LATER, cohort()), reason)

    def test_reading_span_boundary(self):
        end = NOW + quota.MAX_READING_SPAN
        self.assertProceeds(quota.settle(reading(), reading(end), end, cohort()))

    def test_pre_reading_required(self):
        self.assertRefused(quota.settle(None, reading(LATER), LATER, cohort()), "missing-pre-reading")

    def test_pre_reading_not_refreshed_at_settle(self):
        self.assertProceeds(quota.settle(reading(), reading(LATER), LATER, cohort()))

    def test_cohort_state_absent(self):
        self.assertRefused(quota.settle(reading(), reading(LATER), LATER, None), "cohort-state-absent")


class ProbeTests(GateTest):
    def test_probe_within_cap_proceeds(self):
        decision = quota.admit_probe(reading(), NOW, 2)
        self.assertProceeds(decision)
        self.assertEqual(decision.evidence["kind"], "live-probe")
        self.assertEqual(decision.evidence["probesStarted"], 2)

    def test_probe_session_cap(self):
        for started in (3, 4):
            with self.subTest(started=started):
                self.assertRefused(quota.admit_probe(reading(), NOW, started),
                                   "probe-session-cap-reached")

    def test_probe_count_invalid(self):
        for started in (-1, True, 1.0, None):
            with self.subTest(started=started):
                self.assertRefused(quota.admit_probe(reading(), NOW, started), "probe-count-invalid")

    def test_probe_reading_controls(self):
        cases = [
            (None, "missing-pre-reading"),
            (reading(five="31"), "unparseable-reading"),
            (reading(NOW - timedelta(minutes=6)), "stale-pre-reading"),
            (reading(NOW + timedelta(minutes=1)), "future-dated-pre-reading"),
            (reading(weekly=81), "weekly-above-stop"),
            (reading(extra=True), "extra-usage-enabled"),
            (reading(five=90), "five-hour-at-start-limit"),
        ]
        for raw, reason in cases:
            with self.subTest(reason=reason):
                self.assertRefused(quota.admit_probe(raw, NOW, 0), reason)

    def test_settle_probe_within_cap(self):
        decision = quota.settle_probe(reading(), reading(LATER, five=33), LATER)
        self.assertProceeds(decision)
        self.assertEqual(decision.evidence["fiveHourDelta"], 2)

    def test_settle_probe_controls(self):
        cases = [
            (reading(LATER, five=34), LATER, "probe-above-five-hour-cap"),
            (None, LATER, "missing-post-reading"),
            (reading(LATER), LATER + timedelta(minutes=6), "stale-post-reading"),
            (reading(NOW), NOW, "post-reading-not-after-pre-reading"),
            (reading(LATER, five=1), LATER, "usage-window-reset"),
            (reading(LATER, five=32, extra=True), LATER, "extra-usage-enabled"),
            (reading(LATER, five=32, weekly=95), LATER, "weekly-above-stop"),
        ]
        for post, now, reason in cases:
            with self.subTest(reason=reason):
                self.assertRefused(quota.settle_probe(reading(), post, now), reason)


class BindingTests(unittest.TestCase):
    def test_module_imports_no_io_or_process_surface(self):
        tree = ast.parse(Path(quota.__file__).read_text(encoding="utf-8"))
        imported = {alias.name.split(".")[0] for node in ast.walk(tree)
                    if isinstance(node, ast.Import) for alias in node.names}
        imported |= {(node.module or "").split(".")[0] for node in ast.walk(tree)
                     if isinstance(node, ast.ImportFrom)}
        self.assertLessEqual(imported, {"__future__", "collections", "dataclasses", "datetime",
                                        "re", "types", "typing"})
        calls = {node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertFalse(calls & {"now", "utcnow", "today", "time"})
        self.assertNotIn("open", {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)})

    def test_caps_match_founder_records(self):
        root = Path(__file__).resolve().parents[1] / "specs"
        d2 = json.loads((root / "049-harness-evaluation-learning/evidence/registration"
                         / "d2-caps-founder-decision-20261031.json").read_text())["caps"]
        nc = {d["id"]: d for d in json.loads(
            (root / "065-native-claude-containment/evidence/founder-decisions-20261031.json")
            .read_text())["decisions"]}
        self.assertEqual((d2["perSessionMaxPercentOf5HourWindow"],
                          d2["cohortMaxPercentOfWeeklyAllModels"], d2["maxNativeUnits"]),
                         (quota.SESSION_MAX_FIVE_HOUR, quota.COHORT_MAX_WEEKLY, quota.MAX_UNITS))
        self.assertEqual(quota.SESSION_WALL, timedelta(minutes=d2["perUnitWallTimeMinutes"]))
        self.assertIn(f"above {quota.WEEKLY_STOP_ABOVE} %", d2["stopConditions"][0])
        nc6, nc10 = nc["NC-6"]["decision"], nc["NC-10"]["decision"]
        self.assertEqual(quota.FRESHNESS, timedelta(minutes=nc6["freshnessMinutes"]))
        self.assertIn(f"below {quota.FIVE_HOUR_START_BELOW} %", nc6["startRule"])
        self.assertIn(f"more than {quota.SESSION_MAX_FIVE_HOUR} %", nc6["stopRule"])
        self.assertIn("Claude Desktop usage card", nc6["source"])
        self.assertEqual((nc10["maxLiveSessionsPerAttempt"], nc10["perSessionMaxPercentOf5HourWindow"]),
                         (quota.PROBE_MAX_SESSIONS, quota.PROBE_MAX_FIVE_HOUR))


if __name__ == "__main__":
    unittest.main()
