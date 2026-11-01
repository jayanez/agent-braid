# SPDX-License-Identifier: AGPL-3.0-only
"""T008 host-profile gate controls with deterministic records; no native session runs."""
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import json
from pathlib import Path
import unittest

from agent_braid import harness_host_claude as hc
from agent_braid import harness_hosts as hh
from agent_braid.harness_lab import ENFORCED_EFFECTS
from agent_braid.system_one import canonical

FOUNDER_SHA256 = "38bedbba82de5c219f3c0a3f6c8f2e3a0309824abeea536862bdc20e3ab4eddc"
D2_SHA256 = "b1851e1c1e0d075368cd8193c97ae1e322fcce8a5d94f23762f3dd4aed4d2d88"
NOW = 1_800_000_000
ENV = "e" * 64
EVIDENCE = "f" * 64


def founder_record(**over):
    value = {
        "recordVersion": "spec048-founder-review-v1",
        "decisions": [
            {"task": "SPEC-048/T010", "item": "Human review", "decision": "reviewed-accepted"},
            {"task": "SPEC-048/T008", "item": "Claude profile qualification",
             "decision": "qualification-authorized"},
            {"task": "SPEC-048/T008", "item": "Codex profile qualification",
             "decision": "not-qualified"},
        ],
        "hostObservation": {"host": {"claude": "/opt/homebrew/bin/claude 2.1.292 (Claude Code)",
                                     "codex": "absent (command -v codex: not found)"}},
        "executionAuthorization": False, "nativeAdmission": False, "promotionAuthorization": False,
    }
    value.update(over)
    return json.dumps(value, indent=2).encode()


def caps_record(**over):
    caps = {"perUnitWallTimeMinutes": 30, "perSessionMaxPercentOf5HourWindow": 10,
            "cohortMaxPercentOfWeeklyAllModels": 15, "maxNativeUnits": 16,
            "stopConditions": ["weekly all-models window above 80 % before the next unit",
                               "extra usage enabled", "quota reading unavailable or stale"]}
    caps.update(over.pop("caps", {}))
    value = {"recordVersion": "spec049-d2-caps-founder-decision-v1", "caps": caps,
             "additionalCashEur": 0, "executionAuthorization": False, "nativeAdmission": False,
             "promotionAuthorization": False}
    value.update(over)
    return json.dumps(value, indent=2).encode()


def decisions(raw=None):
    raw = founder_record() if raw is None else raw
    return hh.parse_profile_decisions(raw, expected_sha256=sha256(raw).hexdigest())


def caps(raw=None):
    raw = caps_record() if raw is None else raw
    return hh.parse_d2_caps(raw, expected_sha256=sha256(raw).hexdigest())


def quota(**over):
    value = dict(host="claude", observed_at=NOW, plan="max", route="subscription",
                 five_hour_percent=31, five_hour_resets_at=NOW + 3600, weekly_percent=41,
                 weekly_resets_at=NOW + 86_400, extra_usage_enabled=False)
    value.update(over)
    return hh.QuotaObservation(**value)


def qualification(**over):
    value = {"format": hc.QUALIFICATION_FORMAT, "host": "claude", "environmentSha256": ENV,
             "enforced": list(ENFORCED_EFFECTS), "expiresAt": NOW + 7200,
             "evidenceSha256": EVIDENCE, **over}
    raw = canonical(value)
    return raw, sha256(raw).hexdigest()


def gate(host="claude", baseline=None, **over):
    return hh.HostQualificationRun(decisions(), caps(), host=host, environment_sha256=ENV,
                                   baseline=baseline or quota(), **over)


def admit(run, observation=None, *, now=NOW, containment=None):
    raw, digest = containment or qualification()
    return run.admit_unit(observation or quota(observed_at=now), containment=raw,
                          containment_sha256=digest, now=now)


class DecisionRecordTests(unittest.TestCase):
    def test_independent_host_decisions(self):
        parsed = decisions()
        self.assertEqual(set(parsed), {"claude", "codex"})
        self.assertTrue(parsed["claude"].authorized)
        self.assertFalse(parsed["codex"].authorized)
        self.assertEqual(parsed["codex"].reason, "not-qualified: not installed")
        self.assertEqual(parsed["claude"].record_sha256, sha256(founder_record()).hexdigest())

    def test_record_hash_must_match(self):
        with self.assertRaises(hh.HostGateError) as caught:
            hh.parse_profile_decisions(founder_record(), expected_sha256="0" * 64)
        self.assertEqual(caught.exception.reason, "record-drift")

    def test_missing_host_decision_stays_refused(self):
        raw = founder_record(decisions=[{"task": "SPEC-048/T008",
                                         "item": "Claude profile qualification",
                                         "decision": "qualification-authorized"}])
        parsed = decisions(raw)
        self.assertTrue(parsed["claude"].authorized)
        self.assertFalse(parsed["codex"].authorized)
        self.assertEqual(parsed["codex"].reason, "not-qualified: no decision")

    def test_duplicate_or_unknown_decisions_refuse(self):
        claude = {"task": "SPEC-048/T008", "item": "Claude profile qualification",
                  "decision": "qualification-authorized"}
        for rows in ([claude, claude],
                     [dict(claude, decision="qualified")],
                     [dict(claude, item="Gemini profile qualification")]):
            with self.subTest(rows=rows), self.assertRaises(hh.HostGateError):
                decisions(founder_record(decisions=rows))

    def test_record_granting_authority_refuses(self):
        for key in ("executionAuthorization", "nativeAdmission", "promotionAuthorization"):
            with self.subTest(key=key), self.assertRaises(hh.HostGateError):
                decisions(founder_record(**{key: True}))
        with self.assertRaises(hh.HostGateError):
            decisions(founder_record(recordVersion="spec048-founder-review-v2"))
        with self.assertRaises(hh.HostGateError):
            decisions(b"not json")

    def test_codex_installed_but_unqualified_has_generic_reason(self):
        raw = founder_record(hostObservation={"host": {"codex": "/usr/bin/codex"}})
        self.assertEqual(decisions(raw)["codex"].reason, "not-qualified")

    def test_decision_is_immutable(self):
        with self.assertRaises(FrozenInstanceError):
            decisions()["codex"].decision = "qualification-authorized"


class RepositoryRecordTests(unittest.TestCase):
    """The actual founder records bound by evidence/t008.json."""

    def test_committed_founder_records_parse(self):
        root = Path(__file__).resolve().parents[1] / "specs"
        review = (root / "048-harness-variant-laboratory/evidence/founder-review-20261031.json").read_bytes()
        d2 = (root / "049-harness-evaluation-learning/evidence/registration/"
              "d2-caps-founder-decision-20261031.json").read_bytes()
        parsed = hh.parse_profile_decisions(review, expected_sha256=FOUNDER_SHA256)
        self.assertEqual({h: d.reason for h, d in parsed.items()},
                         {"claude": "qualification-authorized",
                          "codex": "not-qualified: not installed"})
        self.assertEqual(hh.parse_d2_caps(d2, expected_sha256=D2_SHA256).max_units, 16)


class CapsRecordTests(unittest.TestCase):
    def test_founder_caps(self):
        parsed = caps()
        self.assertEqual((parsed.unit_wall_seconds, parsed.session_max_five_hour_percent,
                          parsed.cohort_max_weekly_percent, parsed.max_units,
                          parsed.weekly_stop_percent, parsed.additional_cash_eur),
                         (1800, 10, 15, 16, 80, 0))

    def test_caps_drift_or_spend_refuses(self):
        for raw in (caps_record(additionalCashEur=5), caps_record(caps={"maxNativeUnits": 17}),
                    caps_record(caps={"stopConditions": []}), caps_record(nativeAdmission=True),
                    caps_record(caps={"perUnitWallTimeMinutes": "30"}),
                    caps_record(caps={"perSessionMaxPercentOf5HourWindow": 10.0}),
                    caps_record(additionalCashEur=0.0)):
            with self.subTest(raw=raw[:80]), self.assertRaises(hh.HostGateError):
                caps(raw)
        with self.assertRaises(hh.HostGateError) as caught:
            hh.parse_d2_caps(caps_record(), expected_sha256="1" * 64)
        self.assertEqual(caught.exception.reason, "record-drift")


class ObservationTests(unittest.TestCase):
    def test_invalid_observations_refuse(self):
        for over in ({"five_hour_percent": 101}, {"weekly_percent": -1},
                     {"extra_usage_enabled": 0}, {"host": "gemini"}, {"observed_at": "now"},
                     {"weekly_percent": True}, {"route": ""}):
            with self.subTest(over=over), self.assertRaises(hh.HostGateError):
                quota(**over)

    def test_observation_binds_hash(self):
        self.assertEqual(quota().sha256, quota().sha256)
        self.assertNotEqual(quota().sha256, quota(weekly_percent=42).sha256)
        self.assertEqual(quota(five_hour_percent=31.5).to_dict()["fiveHourPercent"], 31.5)


class GateTests(unittest.TestCase):
    def test_codex_profile_refused_independently(self):
        with self.assertRaises(hh.HostGateError) as caught:
            gate(host="codex", baseline=quota(host="codex"))
        self.assertEqual(caught.exception.reason, "not-qualified: not installed")

    def test_decisions_are_snapshotted_and_stop_is_read_only(self):
        parsed = decisions()
        run = hh.HostQualificationRun(parsed, caps(), host="claude", environment_sha256=ENV,
                                      baseline=quota())
        parsed["claude"] = parsed["codex"]
        self.assertTrue(run.verdict().decision.authorized)
        with self.assertRaises(AttributeError):
            run.stopped = None
        with self.assertRaises(hh.HostGateError):
            hh.HostQualificationRun({"claude": parsed["codex"]}, caps(), host="claude",
                                    environment_sha256=ENV, baseline=quota())

    def test_baseline_and_environment_must_match_host(self):
        for baseline in (quota(host="codex"), quota(route="api-key"),
                         quota(extra_usage_enabled=True)):
            with self.subTest(baseline=baseline), self.assertRaises(hh.HostGateError):
                gate(baseline=baseline)
        with self.assertRaises(hh.HostGateError):
            hh.HostQualificationRun(decisions(), caps(), host="claude", environment_sha256="x",
                                    baseline=quota())

    def test_admits_one_unit_and_settles_within_caps(self):
        run = gate()
        ticket = admit(run)
        self.assertEqual(ticket.index, 0)
        self.assertEqual(ticket.deadline, NOW + 1800)
        record = run.settle_unit(ticket, quota(observed_at=NOW + 600, five_hour_percent=34,
                                               weekly_percent=42), completed=True, now=NOW + 600)
        self.assertTrue(record.within_caps)
        self.assertEqual((record.five_hour_delta, record.weekly_delta), (3, 1))
        verdict = run.verdict()
        self.assertTrue(verdict.qualified)
        self.assertEqual(verdict.host, "claude")
        self.assertEqual(verdict.to_dict()["units"][0]["afterSha256"], record.after_sha256)
        self.assertFalse(verdict.to_dict()["executionAuthorization"])

    def test_missing_or_stale_observation_stops(self):
        for observation in (None, quota(observed_at=NOW - 301), quota(observed_at=NOW + 1),
                            quota(host="codex")):
            with self.subTest(observation=observation):
                run = gate()
                raw, digest = qualification()
                with self.assertRaises(hh.HostGateError):
                    run.admit_unit(observation, containment=raw, containment_sha256=digest,
                                   now=NOW)
                self.assertIsNotNone(run.stopped)
                with self.assertRaises(hh.HostGateError) as caught:
                    admit(run)
                self.assertEqual(caught.exception.reason, "stopped")

    def test_stop_conditions_before_unit(self):
        cases = {"extra-usage-enabled": quota(extra_usage_enabled=True),
                 "weekly-stop": quota(weekly_percent=81),
                 "paid-route": quota(route="api-key"),
                 "window-reset": quota(weekly_resets_at=NOW + 90_000),
                 "window-reset ": quota(weekly_percent=40),
                 "cohort-cap": quota(weekly_percent=56),
                 "five-hour-headroom": quota(five_hour_percent=91),
                 "window-reset-imminent": quota(five_hour_resets_at=NOW + 1800)}
        for reason, observation in cases.items():
            with self.subTest(reason=reason):
                run = gate()
                with self.assertRaises(hh.HostGateError) as caught:
                    admit(run, observation)
                self.assertEqual(caught.exception.reason, reason.strip())
                self.assertEqual(run.stopped, reason.strip())

    def test_weekly_at_eighty_still_admits_when_cohort_allows(self):
        run = gate(baseline=quota(weekly_percent=70))
        admit(run, quota(weekly_percent=80))

    def test_containment_verified_before_every_unit(self):
        bad = {"host-mismatch": qualification(host="codex"),
               "qualification-drift": (qualification()[0], "0" * 64),
               "containment-environment": qualification(environmentSha256="d" * 64),
               "containment-expired": qualification(expiresAt=NOW + 1800)}
        for reason, containment in bad.items():
            with self.subTest(reason=reason):
                run = gate()
                with self.assertRaises(hh.HostGateError) as caught:
                    admit(run, containment=containment)
                self.assertEqual(caught.exception.reason, reason)
        run = gate()
        run.settle_unit(admit(run), quota(observed_at=NOW + 10), completed=True, now=NOW + 10)
        with self.assertRaises(hh.HostGateError) as caught:
            admit(run, quota(observed_at=NOW + 20), now=NOW + 20,
                  containment=qualification(expiresAt=NOW + 1820))
        self.assertEqual(caught.exception.reason, "containment-expired")

    def test_older_reading_cannot_hide_a_later_one(self):
        run = gate()
        early = quota(observed_at=NOW)
        run.settle_unit(admit(run, early), quota(observed_at=NOW + 60, weekly_percent=44),
                        completed=True, now=NOW + 60)
        with self.assertRaises(hh.HostGateError) as caught:
            admit(run, early, now=NOW + 100)
        self.assertEqual(caught.exception.reason, "stale-observation")

    def test_weekly_reservation_uses_largest_observed_delta(self):
        run = gate()
        run.settle_unit(admit(run), quota(observed_at=NOW + 60, weekly_percent=46),
                        completed=True, now=NOW + 60)
        with self.assertRaises(hh.HostGateError) as caught:  # 5 used + 5 reserved + 5 > 14
            admit(run, quota(observed_at=NOW + 100, weekly_percent=51), now=NOW + 100)
        self.assertEqual(caught.exception.reason, "cohort-cap")
        self.assertTrue(run.verdict().qualified)  # budget stop keeps prior evidence
        run = gate(baseline=quota(weekly_percent=70))
        run.settle_unit(admit(run, quota(weekly_percent=70)),
                        quota(observed_at=NOW + 60, weekly_percent=74), completed=True, now=NOW + 60)
        with self.assertRaises(hh.HostGateError) as caught:  # 78 + 4 reserved > 80
            admit(run, quota(observed_at=NOW + 100, weekly_percent=78), now=NOW + 100)
        self.assertEqual(caught.exception.reason, "weekly-stop")

    def test_integrity_stop_after_evidence_disqualifies(self):
        run = gate()
        run.settle_unit(admit(run), quota(observed_at=NOW + 1), completed=True, now=NOW + 1)
        with self.assertRaises(hh.HostGateError):
            admit(run, quota(observed_at=NOW + 2, route="api-key"), now=NOW + 2)
        self.assertEqual(run.stopped, "paid-route")
        self.assertFalse(run.verdict().qualified)

    def test_one_open_unit_and_unit_cap(self):
        run = gate()
        ticket = admit(run)
        with self.assertRaises(hh.HostGateError) as caught:
            admit(run)
        self.assertEqual(caught.exception.reason, "unit-open")
        run.settle_unit(ticket, quota(observed_at=NOW + 1), completed=True, now=NOW + 1)
        run = gate(baseline=quota(weekly_percent=41))
        now = NOW
        for _ in range(16):
            ticket = admit(run, quota(observed_at=now), now=now)
            run.settle_unit(ticket, quota(observed_at=now + 1), completed=True, now=now + 1)
            now += 2
        with self.assertRaises(hh.HostGateError) as caught:
            admit(run, quota(observed_at=now), now=now)
        self.assertEqual(caught.exception.reason, "unit-cap")

    def test_settlement_breaches_stop_the_cohort(self):
        cases = {"session-cap": (quota(observed_at=NOW + 5, five_hour_percent=42), NOW + 5),
                 "cohort-cap": (quota(observed_at=NOW + 5, weekly_percent=57), NOW + 5),
                 "unit-wall-time": (quota(observed_at=NOW + 1801), NOW + 1801),
                 "extra-usage-enabled": (quota(observed_at=NOW + 5, extra_usage_enabled=True),
                                         NOW + 5),
                 "window-reset": (quota(observed_at=NOW + 5, five_hour_resets_at=NOW + 9000),
                                  NOW + 5),
                 "stale-observation": (quota(observed_at=NOW + 5), NOW + 400),
                 "stale-observation ": (quota(observed_at=NOW), NOW + 5),
                 "inconsistent-observation": (quota(observed_at=NOW + 5, weekly_percent=40),
                                              NOW + 5),
                 "missing-observation": (None, NOW + 5)}
        for reason, (after, now) in cases.items():
            with self.subTest(reason=reason):
                run = gate()
                record = run.settle_unit(admit(run), after, completed=True, now=now)
                self.assertFalse(record.within_caps)
                self.assertEqual(record.breach, reason.strip())
                self.assertEqual(run.stopped, reason.strip())
                self.assertFalse(run.verdict().qualified)

    def test_settle_requires_the_open_ticket(self):
        run = gate()
        ticket = admit(run)
        with self.assertRaises(hh.HostGateError):
            run.settle_unit(replace(ticket, index=3), quota(observed_at=NOW + 1),
                            completed=True, now=NOW + 1)
        run.settle_unit(ticket, quota(observed_at=NOW + 1), completed=True, now=NOW + 1)
        with self.assertRaises(hh.HostGateError):
            run.settle_unit(ticket, quota(observed_at=NOW + 2), completed=True, now=NOW + 2)

    def test_incomplete_session_does_not_qualify(self):
        run = gate()
        record = run.settle_unit(admit(run), quota(observed_at=NOW + 1), completed=False,
                                 now=NOW + 1)
        self.assertTrue(record.within_caps)
        self.assertFalse(run.verdict().qualified)
        self.assertFalse(gate().verdict().qualified)  # no unit at all


class BothHostTests(unittest.TestCase):
    def test_partial_qualification_never_implies_both_hosts(self):
        run = gate()
        run.settle_unit(admit(run), quota(observed_at=NOW + 1), completed=True, now=NOW + 1)
        claude = run.verdict()
        codex = hh.refused_verdict(decisions()["codex"])
        self.assertTrue(claude.qualified)
        self.assertFalse(codex.qualified)
        self.assertEqual(codex.stopped, "not-qualified: not installed")
        self.assertFalse(hh.both_hosts_accepted({"claude": claude, "codex": codex}))
        self.assertFalse(hh.both_hosts_accepted({"claude": claude}))
        self.assertFalse(hh.both_hosts_accepted({"claude": claude, "codex": claude}))
        with self.assertRaises(hh.HostGateError):
            hh.refused_verdict(decisions()["claude"])
        borrowed = replace(claude, host="codex")
        self.assertFalse(borrowed.qualified)
        self.assertFalse(hh.both_hosts_accepted({"claude": claude, "codex": borrowed}))


if __name__ == "__main__":
    unittest.main()
