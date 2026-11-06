# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-048/T008 native wiring controls with deterministic doubles; nothing native runs here."""
from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest

from agent_braid import harness_containment_macos as mac
from agent_braid import harness_host_claude as hc
from agent_braid import harness_hosts as hh
from agent_braid import harness_hosts_native as hn
from agent_braid import harness_quota
from tests.test_harness_hosts import caps, decisions
from tests.test_harness_transport_claude import (
    BUILD_TEXT, WINDOW, Fixture, good_chunks, init, line)
from tests.test_harness_host_claude import SESSION, make_inventory

ROOT = Path(__file__).resolve().parents[1]
ISSUANCE = ROOT / "specs/065-native-claude-containment/evidence/qualification/issuance-2026-11-06.json"
ENVIRONMENT = ROOT / "specs/065-native-claude-containment/evidence/qualification/t009-20261106a/environment.json"
TRUSTED_CONTAINMENT = "b7641c8a48b9c4a2ef6213fa42fa429ae56b279df86c5da33db07e67ff83f834"
TRUSTED_HOST = "8c1a38fe054a09a44a29b53f9aad757500991e1d74aaa655ec4584bcd886178d"
BASE = datetime(2026, 11, 10, 12, 0, tzinfo=timezone.utc)
NOW = int(BASE.timestamp())
HEX = "a" * 64


def observation(**over):
    value = dict(host="claude", observed_at=NOW - 30, plan="max", route="subscription",
                 five_hour_percent=20, five_hour_resets_at=NOW + 3 * 3600, weekly_percent=10,
                 weekly_resets_at=NOW + 4 * 86400, extra_usage_enabled=False)
    value.update(over)
    return hh.QuotaObservation(**value)


class IssuedRecordTests(unittest.TestCase):
    def load(self, raw=None, **over):
        kw = dict(containment_sha256=TRUSTED_CONTAINMENT, host_sha256=TRUSTED_HOST) | over
        return hn.issued_records(ISSUANCE.read_bytes() if raw is None else raw, **kw)

    def test_committed_issuance_yields_the_canonical_records_the_backend_verifies(self):
        issued = self.load()
        self.assertEqual(sha256(issued.containment).hexdigest(), TRUSTED_CONTAINMENT)
        self.assertEqual(sha256(issued.host).hexdigest(), TRUSTED_HOST)
        self.assertEqual(issued.expires_at, 1796580464)
        self.assertEqual(issued.environment_sha256,
                         "e91007d8626998d49ccb574bc241752bccc5134616598dd76b8f63630f9d818a")
        self.assertFalse(issued.executionAuthorization)

    def test_wrong_trusted_hash_or_edited_record_refuses(self):
        for over in ({"containment_sha256": "0" * 64}, {"host_sha256": "0" * 64}):
            with self.assertRaises(hn.NativeWiringError) as cm:
                self.load(**over)
            self.assertEqual(cm.exception.reason, "qualification-drift")
        value = json.loads(ISSUANCE.read_bytes())
        value["records"]["host"]["evidenceSha256"] = HEX
        with self.assertRaises(hn.NativeWiringError):
            self.load(json.dumps(value).encode())

    def test_only_issued_non_authorizing_records_are_accepted(self):
        for path, new in ((("decision", "disposition"), "withdrawn"), (("executionAuthorization",), True)):
            value = json.loads(ISSUANCE.read_bytes())
            target = value
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = new
            with self.assertRaises(hn.NativeWiringError) as cm:
                self.load(json.dumps(value).encode())
            self.assertEqual(cm.exception.reason, "invalid-issuance")


class QualifiedPolicyTests(unittest.TestCase):
    MACHINE = dict(account="braidlab", run_root="/Users/braidlab/t009/run",
                   config_dir="/Users/braidlab/t009/config",
                   claude="/usr/local/libexec/braid/claude-2.1.292",
                   interpreter="/usr/local/libexec/braid/python312/bin/python3.12",
                   interpreter_sha256="b" * 64,
                   interpreter_root="/usr/local/libexec/braid/python312", proxy_port=18080)

    def environment(self, **over):
        policy = mac.ContainmentPolicy(claude_sha256="c" * 64, claude_version=mac.CLAUDE_VERSION,
                                       sandbox_exec_sha256="d" * 64, **self.MACHINE)
        value = {"claudeSha256": "c" * 64, "claudeVersion": mac.CLAUDE_VERSION,
                 "sandboxExecSha256": "d" * 64, "probeCatalogSha256": policy.probe_catalog_sha256,
                 "profileSha256": sha256(policy.render("launch")).hexdigest()}
        value.update(over)
        return value

    def build(self, environment=None, **over):
        return hn.qualified_policy(self.environment() if environment is None else environment,
                                   **(self.MACHINE | over))

    def test_policy_is_built_only_from_the_qualified_pins_and_has_no_extra_endpoints(self):
        policy = self.build()
        self.assertEqual((policy.claude_sha256, policy.sandbox_exec_sha256), ("c" * 64, "d" * 64))
        self.assertEqual((policy.helpers, policy.refresh_endpoints), ((), ()))

    def test_any_difference_from_the_qualified_inputs_refuses(self):
        cases = (self.environment(claudeVersion="2.1.293"), self.environment(probeCatalogSha256="e" * 64),
                 self.environment(profileSha256="e" * 64))
        for env in cases:
            with self.assertRaises((hn.NativeWiringError, mac.LabError)):
                self.build(env)
        with self.assertRaises((hn.NativeWiringError, mac.LabError)):
            self.build(run_root="/Users/braidlab/other/run")  # profile bytes move, so profileSha256 drifts

    def test_the_committed_environment_document_is_the_one_the_policy_checks(self):
        env = json.loads(ENVIRONMENT.read_bytes())
        self.assertEqual(env["claudeVersion"], mac.CLAUDE_VERSION)
        self.assertEqual(env["probeCatalogSha256"], mac.CLAUDE_VERSION and hn.probe_catalog_sha256())


class UnhashedGuardTests(unittest.TestCase):
    def test_current_files_match_the_qualified_commit(self):
        hn.guard_unhashed(ROOT / "agent_braid")

    def test_a_symlinked_module_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in hn.UNHASHED:
                (Path(tmp) / name).write_bytes((ROOT / "agent_braid" / name).read_bytes())
            target = Path(tmp) / "elsewhere.py"
            (Path(tmp) / "system_one.py").rename(target)
            (Path(tmp) / "system_one.py").symlink_to(target)
            with self.assertRaises(hn.NativeWiringError):
                hn.guard_unhashed(Path(tmp))

    def test_a_changed_file_blocks_unless_the_founder_approved_that_exact_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in hn.UNHASHED:
                (Path(tmp) / name).write_bytes((ROOT / "agent_braid" / name).read_bytes())
            hn.guard_unhashed(Path(tmp))
            changed = Path(tmp) / "system_one.py"
            changed.write_bytes(changed.read_bytes() + b"# edit\n")
            with self.assertRaises(hn.NativeWiringError) as cm:
                hn.guard_unhashed(Path(tmp))
            self.assertEqual(cm.exception.reason, "unhashed-file-changed")
            digest = sha256(changed.read_bytes()).hexdigest()
            hn.guard_unhashed(Path(tmp), approved={"system_one.py": digest})
            with self.assertRaises(hn.NativeWiringError):
                hn.guard_unhashed(Path(tmp), approved={"system_one.py": HEX})


class ReadingTests(unittest.TestCase):
    def test_observation_maps_to_the_quota_module_reading(self):
        reading = hn.reading_of(observation(observed_at=NOW - 60))
        self.assertEqual(reading["source"], harness_quota.SOURCE)
        self.assertEqual((reading["fiveHourPercent"], reading["weeklyPercent"]), (20, 10))
        decision = harness_quota.admit(reading, BASE, {"unitsUsed": 0, "cohortWeeklyPercent": 0})
        self.assertTrue(decision.proceed)


class UnitInputsTests(unittest.TestCase):
    def test_inputs_carry_exactly_the_backends_pins_and_run_through_the_native_transport(self):
        fx = Fixture(self, chunks=good_chunks())
        manifest, context = hn.unit_inputs(
            environment_sha256=fx.env_sha, claude_sha256=fx.exe_sha,
            containment_sha256=fx.qualification.sha256,
            host_qualification_sha256=fx.host_qualification.sha256)
        self.assertEqual(manifest.data["host"]["requested"]["route"], "subscription")
        self.assertEqual(manifest.data["effects"]["write"], ("lab/guidance/main.md",))
        transport = fx.transport(pre=hn.reading_of(observation(observed_at=1_793_000_000)))
        transport.verify_containment(manifest, fx.host_qualification, 1_799_999_999)

    def test_a_different_pin_is_refused_by_the_transport_before_launch(self):
        fx = Fixture(self, chunks=good_chunks())
        manifest, _ = hn.unit_inputs(
            environment_sha256=fx.env_sha, claude_sha256="0" * 64,
            containment_sha256=fx.qualification.sha256,
            host_qualification_sha256=fx.host_qualification.sha256)
        with self.assertRaises(hc.ClaudeHostError):
            fx.transport().verify_containment(manifest, fx.host_qualification, 1_799_999_999)


class NativeUnitTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture(self, chunks=good_chunks())
        self.fx.qualification = self.fx.backend_qualification(expiresAt=NOW + 40 * 86400)
        self.fx.host_qualification = self.fx.host_record(expiresAt=NOW + 40 * 86400)
        self.fx.launcher.qualification = self.fx.qualification
        self.fx.launcher.host_qualification = self.fx.host_qualification
        self.manifest, self.context = hn.unit_inputs(
            environment_sha256=self.fx.env_sha, claude_sha256=self.fx.exe_sha,
            containment_sha256=self.fx.qualification.sha256,
            host_qualification_sha256=self.fx.host_qualification.sha256)
        self.host_raw = self.fx.host_qualification.canonical_bytes
        self.run = hh.HostQualificationRun(decisions(), caps(), "claude", self.fx.env_sha,
                                           observation(observed_at=NOW - 3600))

    def unit(self, *, after="default", before=None, **over):
        after_obs = (observation(observed_at=NOW + 120, five_hour_percent=22, weekly_percent=11)
                     if after == "default" else after)
        kw = dict(run=self.run, backend=self.fx.launcher, workdir=self.fx.tmp,
                  containment=self.host_raw, containment_sha256=self.fx.host_qualification.sha256,
                  manifest=self.manifest, context=self.context,
                  request=hc.ClaudeRequest(session_id=SESSION),
                  compatibility=WINDOW, inventory=make_inventory(), attempt_id="t008-u0",
                  before=before or observation(), read_after=lambda: after_obs, now=lambda: BASE,
                  retention_seconds=3600, settle_now=lambda: NOW + 130, environ={})
        return hn.run_native_unit(**(kw | over))

    def test_a_complete_unit_admits_runs_and_settles_within_the_caps(self):
        outcome = self.unit()
        self.assertTrue(outcome.record.completed and outcome.record.within_caps)
        self.assertEqual((outcome.record.five_hour_delta, outcome.record.weekly_delta), (2, 1))
        self.assertEqual(outcome.result.transport, "native")
        self.assertFalse(outcome.executionAuthorization)
        self.assertTrue(self.run.verdict().qualified)

    def test_admission_refusal_never_launches(self):
        with self.assertRaises(hh.HostGateError) as cm:
            self.unit(before=observation(weekly_percent=81))
        self.assertEqual(cm.exception.reason, "weekly-stop")
        self.assertEqual(self.fx.launcher.run_calls, [])

    def test_containment_not_the_issued_host_record_never_launches(self):
        with self.assertRaises(hh.HostGateError):
            self.unit(containment_sha256="0" * 64)
        self.assertEqual(self.fx.launcher.run_calls, [])

    def test_a_failed_run_still_settles_the_unit_and_latches_the_stop(self):
        self.fx.launcher.chunks = [line(init(claude_code_version=BUILD_TEXT, apiKeySource="ANTHROPIC_API_KEY"))]
        outcome = self.unit()
        self.assertFalse(outcome.record.completed)
        verdict = self.run.verdict()
        self.assertFalse(verdict.qualified)
        self.assertEqual(len(verdict.units), 1)

    def test_a_host_error_settles_not_completed_latches_the_stop_and_reraises(self):
        self.fx.launcher.fail = hc.ClaudeHostError("transport-failed")
        with self.assertRaises(hc.ClaudeHostError):
            self.unit()
        verdict = self.run.verdict()
        self.assertFalse(verdict.units[0].completed)
        self.assertEqual((self.run.stopped, verdict.qualified, verdict.open_unit),
                         ("unit-incomplete", False, False))

    def test_a_failing_clock_at_settlement_never_reads_as_qualified(self):
        def broken():
            raise RuntimeError("clock")
        with self.assertRaises(RuntimeError):
            self.unit(settle_now=broken)
        self.assertFalse(self.run.verdict().qualified)
        self.assertEqual(self.run.stopped, "unit-unsettled")

    def test_a_lost_after_reading_error_is_a_breach_not_a_crash(self):
        def boom():
            raise ValueError("typed")
        self.assertEqual(self.unit(after=None, read_after=boom).record.breach, "missing-observation")

    def test_missing_after_reading_is_a_breach_and_stops_the_cohort(self):
        outcome = self.unit(after=None)
        self.assertEqual(outcome.record.breach, "missing-observation")
        self.assertEqual(self.run.stopped, "missing-observation")

    def test_cohort_state_for_the_quota_gate_comes_from_the_run_not_the_caller(self):
        self.unit()
        seen = []
        original = harness_quota.admit

        def spy(pre, now, cohort):
            seen.append(dict(cohort))
            return original(pre, now, cohort)
        harness_quota.admit = spy
        try:
            self.fx.launcher.chunks = good_chunks()
            self.unit(before=observation(observed_at=NOW + 125, weekly_percent=11),
                      now=lambda: datetime.fromtimestamp(NOW + 130, timezone.utc),
                      after=observation(observed_at=NOW + 2000, five_hour_percent=24, weekly_percent=12),
                      settle_now=lambda: NOW + 2010)
        finally:
            harness_quota.admit = original
        self.assertEqual(seen, [{"unitsUsed": 1, "cohortWeeklyPercent": 1}])


if __name__ == "__main__":
    unittest.main()
