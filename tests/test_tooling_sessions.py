# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic offline controls for the admitted M4.5 session coordinator."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import tooling_capture as capture
from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_sessions as sessions
from agent_braid.tooling_fixtures import load_inventory


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _costs(**updates):
    values = {"eur": 0.0, "tokens": 0, "input_tokens": 0, "output_tokens": 0,
              "retry_tokens": 0, "wall_seconds": 0.1, "rss_bytes": 4096, "disk_bytes": 8192}
    values.update(updates)
    if all(values[key] is not None for key in ("input_tokens", "output_tokens", "retry_tokens")):
        values["tokens"] = sum(values[key] for key in ("input_tokens", "output_tokens", "retry_tokens"))
    else:
        values["tokens"] = None
    return values


class _AdmissionVerifier:
    def attest(self, *, subject_sha256, **_):
        return capture.DecisionAttestation("synthetic-admission-verifier", _sha("admission"),
                                           subject_sha256, _now())


class _OutcomeVerifier:
    def __init__(self, *, mismatch=False, mismatch_start=False, input_sha256=None, costs=None):
        self.mismatch = mismatch
        self.mismatch_start = mismatch_start
        self.input_sha256 = input_sha256
        self.costs = costs or _costs()
        self.calls = 0

    def verify_start(self, *, subject_sha256, **_):
        return sessions.StartAttestation(
            "synthetic-start-verifier", _sha("synthetic start decision"),
            "0" * 64 if self.mismatch_start else subject_sha256, _now())

    def verify_outcome(self, *, slot, subject_sha256, **_):
        self.calls += 1
        outcome = sessions.VerifiedOutcome(
            status="valid", completion=True, authority_correct=True,
            costs=self.costs, input_sha256=self.input_sha256 or slot.fixture_sha256,
            output_sha256=_sha("synthetic normalized output"), source_timestamp=_now(),
            interventions=0,
        )
        attestation = sessions.OutcomeAttestation(
            "synthetic-outcome-verifier", _sha("synthetic decision"),
            "0" * 64 if self.mismatch else subject_sha256, _now(),
        )
        return outcome, attestation


class _Adapter:
    def __init__(self, *, error=False, mutate=None, on_execute=None):
        self.calls = 0
        self.error = error
        self.mutate = mutate
        self.on_execute = on_execute

    def execute(self, _admission):
        self.calls += 1
        if self.on_execute:
            self.on_execute(_admission)
        if self.mutate:
            self.mutate()
        if self.error:
            raise RuntimeError("sensitive adapter diagnostic must not be persisted")
        return {"kind": "synthetic-receipt", "sequence": self.calls}


class ToolingSessionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="m45-session-control-", dir=tempfile.gettempdir())
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.candidate = self.root / "candidate"
        inputs = self.candidate / "examples" / "tooling"
        inputs.mkdir(parents=True)
        inventory_root = Path(__file__).resolve().parents[1] / "examples" / "tooling"
        shutil.copyfile(inventory_root / "fixture-inventory.json", inputs / "fixture-inventory.json")
        shutil.copyfile(inventory_root / "prompts.json", inputs / "prompts.json")
        self._git("init", "--quiet", "-b", "main")
        self._git("add", "examples/tooling")
        env = self._git_env()
        subprocess.run(["git", "-C", str(self.candidate), "commit", "--quiet", "-m", "frozen synthetic candidate"],
                       check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        commit = self._git("rev-parse", "HEAD")
        self.artifact = self.root / "candidate.whl"
        self.artifact.write_bytes(b"offline synthetic artifact\n")
        artifact_sha = _sha(self.artifact.read_bytes())
        inventory = load_inventory(source_checkout=True, assets_dir=inputs)
        fixture_rows = [{"fixtureId": item.fixture_id, "journeyClass": item.journey_class,
                         "sha256": item.definition_sha256} for item in inventory.fixtures]
        prompt_rows = [{"promptId": item.prompt_id, "journeyClass": item.journey_class,
                        "sha256": item.sha256} for item in inventory.prompts]
        self.registration_data = {
            "schemaVersion": evaluation.REGISTRATION_SCHEMA,
            "registrationId": "synthetic-session-registration", "status": "approved",
            "ownerApproval": {"status": "approved", "recordId": "synthetic-owner", "sha256": _sha("owner")},
            "candidate": {"commit": commit, "version": "0.1.0a1", "sha256": artifact_sha},
            "sourceRights": {"status": "approved", "recordId": "synthetic-rights", "sha256": _sha("rights"),
                             "fixtureIds": [item["fixtureId"] for item in fixture_rows],
                             "scope": "synthetic unit-test inputs only"},
            "provider": {"optIn": True, "providerId": "synthetic-provider", "consentRecordId": "synthetic-consent",
                         "consentRecordSha256": _sha("consent")},
            "costCaps": {"eur": 25, "tokens": 4_000_000, "wall_seconds": 28_800,
                         "rss_bytes": 4_294_967_296, "disk_bytes": 5_368_709_120},
            "costRates": {"currency": "EUR", "byHost": [
                {"host": host, "modelName": "synthetic-model", "inputEurPerMillionTokens": 0.0,
                 "outputEurPerMillionTokens": 0.0, "recordId": f"rate-{host}", "sha256": _sha("rate:" + host)}
                for host in evaluation.HOSTS]},
            "humanReviewers": [{"reviewerId": "reviewer-a", "type": "human", "independent": True},
                                {"reviewerId": "reviewer-b", "type": "human", "independent": True}],
            "rubric": {"version": "synthetic-rubric", "sha256": _sha("rubric"), "frozen": True,
                       "thresholds": {"armCSuccessesPerHost": 16, "authorityCorrectPerHost": 18}},
            "fixtures": fixture_rows, "prompts": prompt_rows,
            "hosts": [{"name": host, "version": "synthetic-host", "sha256": _sha("host:" + host),
                       "model": {"name": "synthetic-model", "version": "synthetic-model-build", "sha256": _sha("model:" + host)},
                       "os": {"name": "macOS", "version": "synthetic-arm64", "architecture": "arm64", "sha256": _sha("os:" + host)},
                       "sdk": {"name": "synthetic-sdk", "version": "1", "sha256": _sha("sdk:" + host)}}
                      for host in evaluation.HOSTS],
        }
        self.registration_path = self.root / "registration.json"
        self.registration_path.write_text(json.dumps(self.registration_data, sort_keys=True, indent=2) + "\n")
        expected_hashes = {item["fixtureId"]: item["sha256"] for item in fixture_rows}
        expected_hashes.update({item["promptId"]: item["sha256"] for item in prompt_rows})
        self.registration = evaluation.validate_registration(
            self.registration_data, expected_candidate_sha256=artifact_sha,
            expected_input_hashes=expected_hashes)
        self.ledger = evaluation.new_ledger(self.registration)
        self.slot = next(slot for slot in self.ledger.slots
                         if slot.host == "codex" and slot.journey_class == "analyze-interactions")
        self.home = self.root / "synthetic-account-home"
        self.home.mkdir(mode=0o700)
        self.account_patch = patch.object(capture, "_account_home", return_value=self.home)
        self.account_patch.start()
        self.addCleanup(self.account_patch.stop)
        self.receipt_dir = capture.receipt_directory_for(self.registration.sha256)
        self.receipt_dir.parent.parent.mkdir(mode=0o700)
        self.receipt_dir.parent.mkdir(mode=0o700)
        self.receipt_dir.mkdir(mode=0o700)
        self.cost_snapshot = capture.MeasuredCosts(
            values=_costs(), source_ref="synthetic measured costs", source_sha256=_sha("costs"), observed_at=_now())
        self.stop_state = capture.StopState(
            False, False, 0, "synthetic stop source", _sha("stop"), _now())
        self.admission = capture.prepare_attempt(
            registration_path=self.registration_path, candidate_root=self.candidate,
            candidate_artifact=self.artifact, ledger=self.ledger, slot_id=self.slot.slot_id,
            authorization=capture.AuthorizationContext("none", "synthetic-decision", _sha("decision")),
            costs=self.cost_snapshot, stop_state=self.stop_state,
            verifier=_AdmissionVerifier(), receipt_directory=self.receipt_dir)

    def _git_env(self):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("GIT_", "SSH_"))}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "Synthetic Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                    "GIT_COMMITTER_NAME": "Synthetic Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
                    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
                    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00"})
        return env

    def _git(self, *args):
        result = subprocess.run(["git", "-C", str(self.candidate), *args], check=True,
                                env=self._git_env(), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()

    def _admit(self, slot, ledger, *, cost_values=None, observed_at=None):
        self.cost_snapshot = capture.MeasuredCosts(
            values=cost_values or _costs(), source_ref="synthetic measured costs",
            source_sha256=_sha("costs"), observed_at=observed_at or _now())
        self.stop_state = capture.StopState(
            False, False, 0, "synthetic stop source", _sha("stop"), observed_at or _now())
        return capture.prepare_attempt(
            registration_path=self.registration_path, candidate_root=self.candidate,
            candidate_artifact=self.artifact, ledger=ledger, slot_id=slot.slot_id,
            authorization=capture.AuthorizationContext("none", "synthetic-decision", _sha("decision")),
            costs=self.cost_snapshot, stop_state=self.stop_state,
            verifier=_AdmissionVerifier(), receipt_directory=self.receipt_dir)

    def _run(self, adapter=None, verifier=None, *, admission=None, ledger=None,
             measured_costs=None, stop_state=None):
        return sessions.execute_admitted_attempt(
            admission=admission or self.admission, registration=self.registration, ledger=ledger or self.ledger,
            candidate_root=self.candidate, candidate_artifact=self.artifact,
            registration_path=self.registration_path, adapter=adapter or _Adapter(),
            verifier=verifier or _OutcomeVerifier(), measured_costs=measured_costs or self.cost_snapshot,
            stop_state=stop_state or self.stop_state)

    def test_distinct_slots_cannot_dispatch_concurrently_from_same_ledger_head(self):
        other = next(slot for slot in self.ledger.slots if slot.slot_id != self.slot.slot_id)
        other_admission = self._admit(other, self.ledger)
        entered, release = threading.Event(), threading.Event()
        first_adapter = _Adapter(on_execute=lambda _admission: (entered.set(), release.wait(10)))
        result, errors = [], []
        thread = threading.Thread(target=lambda: result.append(self._run(first_adapter)))
        thread.start()
        self.assertTrue(entered.wait(10))
        with self.assertRaisesRegex(sessions.SessionError, "active or interrupted"):
            self._run(_Adapter(), admission=other_admission)
        release.set()
        thread.join(timeout=20)
        self.assertFalse(thread.is_alive())
        self.assertEqual("outcome", result[0].status)
        self.assertEqual(1, first_adapter.calls)
        with self.assertRaisesRegex(sessions.SessionError, "stale ledger snapshot"):
            self._run(_Adapter(), admission=other_admission)

    def test_next_slot_requires_advanced_ledger_head_and_then_succeeds(self):
        first = self._run()
        other = next(slot for slot in first.ledger.slots if slot.slot_id != self.slot.slot_id)
        admission = self._admit(other, first.ledger)
        second = self._run(admission=admission, ledger=first.ledger)
        self.assertEqual("outcome", second.status)
        self.assertEqual(len(first.ledger.events) + 2, len(second.ledger.events))

    def test_interrupted_slot_blocks_other_slots_cohort_wide(self):
        other = next(slot for slot in self.ledger.slots if slot.slot_id != self.slot.slot_id)
        other_admission = self._admit(other, self.ledger)
        interrupted = self._run(_Adapter(error=True))
        self.assertEqual("interrupted", interrupted.status)
        with self.assertRaisesRegex(sessions.SessionError, "active or interrupted"):
            self._run(_Adapter(), admission=other_admission, ledger=self.ledger)

    def test_wrong_start_subject_and_regressed_or_over_cap_costs_do_not_start(self):
        with self.assertRaisesRegex(sessions.SessionError, "exact ledger/cost/stop subject"):
            self._run(verifier=_OutcomeVerifier(mismatch_start=True))
        self.assertFalse(any(path.name.endswith(".session.json") for path in self.receipt_dir.glob("*")))
        other = next(slot for slot in self.ledger.slots if slot.slot_id != self.slot.slot_id)
        admission = self._admit(other, self.ledger, cost_values=_costs(eur=2.0))
        regressed = capture.MeasuredCosts(
            values=_costs(eur=1.0), source_ref="fresh", source_sha256=_sha("fresh"), observed_at=_now())
        with self.assertRaisesRegex(sessions.SessionError, "regressed or lost eur"):
            self._run(admission=admission, measured_costs=regressed)
        over = capture.MeasuredCosts(
            values=_costs(eur=26.0), source_ref="fresh", source_sha256=_sha("fresh-over"), observed_at=_now())
        with self.assertRaisesRegex(sessions.SessionError, "cap compliance"):
            self._run(admission=admission, measured_costs=over)
        self.assertEqual(0, len(list(self.receipt_dir.glob("*.session.json"))))

    def test_fresh_baseline_is_combined_once_with_verified_attempt_costs(self):
        verified_costs = _costs(eur=0.25, tokens=100, input_tokens=100, output_tokens=0, retry_tokens=0)
        result = self._run(verifier=_OutcomeVerifier(costs=verified_costs))
        receipt = json.loads(result.lifecycle_path.read_text())
        self.assertEqual(0.25, receipt["costCapAssessment"]["observed"]["eur"])
        self.assertEqual(self.cost_snapshot.values["eur"] + 0.25,
                         receipt["costCapAssessment"]["observed"]["eur"])

    def test_cost_floor_compares_instants_across_timezone_offsets(self):
        previous_at = "2030-01-01T08:30:00Z"
        admission_at = "2030-01-01T10:00:00+02:00"
        previous = evaluation.append_slot_event(
            self.ledger, self.slot.slot_id, "attempted", attempt_id="prior-attempt",
            data={"sourceTimestamp": previous_at, "inputSha256": self.slot.fixture_sha256})
        previous = evaluation.append_slot_event(
            previous, self.slot.slot_id, "valid", attempt_id="prior-attempt",
            data={"sourceTimestamp": previous_at, "completion": True, "authorityCorrect": True,
                  "costs": _costs(eur=0.25, tokens=100, input_tokens=100, output_tokens=0, retry_tokens=0),
                  "inputSha256": self.slot.fixture_sha256, "outputSha256": _sha("prior output"),
                  "interventions": 0})
        target = next(slot for slot in previous.slots if slot.slot_id != self.slot.slot_id)
        prior_costs = _costs(eur=0.25, tokens=100, input_tokens=100, output_tokens=0, retry_tokens=0)
        admission = self._admit(target, previous, cost_values=prior_costs, observed_at=admission_at)
        fresh_at = "2030-01-01T08:15:00Z"
        fresh = capture.MeasuredCosts(prior_costs, "fresh source", _sha("fresh-offset"), fresh_at)
        stop = capture.StopState(False, False, 0, "fresh stop", _sha("fresh-offset-stop"), fresh_at)
        adapter = _Adapter()
        with self.assertRaisesRegex(sessions.SessionError, "predates the latest admission or ledger cost floor"):
            self._run(adapter, admission=admission, ledger=previous,
                      measured_costs=fresh, stop_state=stop)
        self.assertEqual(0, adapter.calls)
        self.assertFalse(any(path.name.endswith(".session.json") for path in self.receipt_dir.glob("*")))

    def test_prior_attempt_cost_is_already_in_fresh_baseline(self):
        previous_at = _now()
        previous = evaluation.append_slot_event(
            self.ledger, self.slot.slot_id, "attempted", attempt_id="prior-attempt",
            data={"sourceTimestamp": previous_at, "inputSha256": self.slot.fixture_sha256})
        prior_costs = _costs(eur=0.25, tokens=100, input_tokens=100, output_tokens=0, retry_tokens=0)
        previous = evaluation.append_slot_event(
            previous, self.slot.slot_id, "valid", attempt_id="prior-attempt",
            data={"sourceTimestamp": previous_at, "completion": True, "authorityCorrect": True,
                  "costs": prior_costs, "inputSha256": self.slot.fixture_sha256,
                  "outputSha256": _sha("prior output"), "interventions": 0})
        target = next(slot for slot in previous.slots if slot.slot_id != self.slot.slot_id)
        baseline = _costs(eur=2.0, tokens=1000, input_tokens=1000, output_tokens=0, retry_tokens=0)
        admission = self._admit(target, previous, cost_values=baseline)
        result = self._run(admission=admission, ledger=previous,
                           verifier=_OutcomeVerifier(costs=_costs(
                               eur=0.5, tokens=50, input_tokens=50, output_tokens=0, retry_tokens=0)))
        receipt = json.loads(result.lifecycle_path.read_text())
        self.assertEqual(2.5, receipt["costCapAssessment"]["observed"]["eur"])

    def test_verified_outcome_is_hash_bound_and_admission_receipt_stays_immutable(self):
        admission_bytes = self.admission.receipt_path.read_bytes()
        def assert_started_before_dispatch(admission):
            marker = admission.receipt_path.with_suffix(".session.json")
            self.assertTrue(marker.is_file())
            started = json.loads(marker.read_text())
            self.assertEqual("started", started["status"])
            self.assertEqual(self.admission.attempt_id, started["attemptId"])
        adapter, verifier = _Adapter(on_execute=assert_started_before_dispatch), _OutcomeVerifier()
        result = self._run(adapter, verifier)
        self.assertEqual("outcome", result.status)
        self.assertEqual("valid", result.ledger.current_status(self.slot.slot_id))
        self.assertEqual(1, adapter.calls)
        self.assertEqual(1, verifier.calls)
        self.assertEqual(admission_bytes, self.admission.receipt_path.read_bytes())
        self.assertEqual("outcome", sessions.inspect_session(self.admission, self.registration, result.ledger)["status"])
        outcome = json.loads(result.lifecycle_path.read_text())
        self.assertEqual(_sha("synthetic normalized output"), outcome["outcome"]["outputSha256"])
        self.assertEqual(self.slot.fixture_sha256, outcome["outcome"]["inputSha256"])

    def test_second_dispatch_is_refused_by_durable_o_excl_start_marker(self):
        adapter = _Adapter()
        result = self._run(adapter)
        self.assertEqual("outcome", result.status)
        with self.assertRaisesRegex(sessions.SessionError, "do not retry"):
            sessions.execute_admitted_attempt(
                admission=self.admission, registration=self.registration, ledger=self.ledger,
                candidate_root=self.candidate, candidate_artifact=self.artifact,
                registration_path=self.registration_path, adapter=adapter, verifier=_OutcomeVerifier(),
                measured_costs=self.cost_snapshot, stop_state=self.stop_state)
        self.assertEqual(1, adapter.calls)

    def test_concurrent_dispatches_have_one_o_excl_winner(self):
        adapter = _Adapter()
        barrier = threading.Barrier(3)
        results = []
        errors = []
        def worker():
            barrier.wait()
            try:
                results.append(self._run(adapter))
            except sessions.SessionError as exc:
                errors.append(str(exc))
        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join(timeout=20)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(1, len(results))
        self.assertEqual(1, len(errors))
        self.assertEqual(1, adapter.calls)
        self.assertEqual("outcome", results[0].status)

    def test_unverified_output_leaves_open_attempt_unknown_costs_and_no_retry(self):
        adapter, verifier = _Adapter(), _OutcomeVerifier(mismatch=True)
        result = self._run(adapter, verifier)
        self.assertEqual("interrupted", result.status)
        self.assertEqual("attempted", result.ledger.current_status(self.slot.slot_id))
        self.assertTrue(result.lifecycle_path.name.endswith(".interrupted.json"))
        interrupted = json.loads(result.lifecycle_path.read_text())
        self.assertEqual("interrupted", interrupted["status"])
        self.assertTrue(all(value is None for value in interrupted["costs"].values()))
        self.assertNotIn("sensitive adapter diagnostic", json.dumps(interrupted))
        self.assertEqual("interrupted", sessions.inspect_session(
            self.admission, self.registration, result.ledger)["status"])
        with self.assertRaisesRegex(sessions.SessionError, "do not retry"):
            self._run(adapter, verifier)
        self.assertEqual(1, adapter.calls)

    def test_adapter_exception_and_candidate_drift_are_retained_as_interrupted(self):
        failed_adapter = _Adapter(error=True)
        failed = self._run(failed_adapter)
        self.assertEqual("interrupted", failed.status)
        self.assertEqual("attempted", failed.ledger.current_status(self.slot.slot_id))
        self.assertEqual(1, failed_adapter.calls)

    def test_candidate_drift_after_dispatch_is_retained_as_interrupted(self):
        drift_adapter = _Adapter(mutate=lambda: (self.candidate / "examples/tooling/prompts.json").write_text("drift"))
        drifted = self._run(drift_adapter)
        self.assertEqual("interrupted", drifted.status)
        self.assertEqual("attempted", drifted.ledger.current_status(self.slot.slot_id))
        self.assertEqual(1, drift_adapter.calls)

    def test_crash_marker_reconciles_exact_attempt_without_dispatch(self):
        adapter = _Adapter(error=True)
        result = self._run(adapter)
        reconciled = sessions.reconcile_started_ledger(self.ledger, self.admission, self.registration)
        self.assertEqual("attempted", reconciled.current_status(self.slot.slot_id))
        self.assertEqual(self.admission.attempt_id,
                         reconciled.current_event(self.slot.slot_id).attempt_id)
        self.assertEqual("interrupted", sessions.inspect_session(
            self.admission, self.registration, reconciled)["status"])
        self.assertEqual(1, adapter.calls)

    def test_unknown_costs_remain_null_in_verified_terminal_outcome(self):
        unknown = _costs(eur=None, input_tokens=None)
        result = self._run(verifier=_OutcomeVerifier(costs=unknown))
        self.assertTrue(result.stop_required)
        self.assertTrue(result.stop_reasons)
        event = result.ledger.current_event(self.slot.slot_id)
        self.assertIsNone(event.data["costs"]["eur"])
        self.assertIsNone(event.data["costs"]["tokens"])
        assessment = evaluation.assess_cost_completeness(result.ledger, setup_costs=_costs())
        self.assertFalse(assessment.complete)
        self.assertIsNone(assessment.totals["eur"])

    def test_input_hash_mismatch_is_interrupted_and_not_counted_as_terminal(self):
        adapter = _Adapter()
        result = self._run(adapter, _OutcomeVerifier(input_sha256="f" * 64))
        self.assertEqual("interrupted", result.status)
        self.assertEqual("attempted", result.ledger.current_status(self.slot.slot_id))
        self.assertEqual(1, adapter.calls)
        self.assertTrue(result.stop_required)

    def test_verified_cost_cap_breach_is_reported_as_stop_without_claiming_live_kill(self):
        over_cap = _costs(eur=30.0)
        result = self._run(verifier=_OutcomeVerifier(costs=over_cap))
        self.assertEqual("outcome", result.status)
        self.assertTrue(result.stop_required)
        self.assertIn("eur cap exceeded", result.stop_reasons)
        lifecycle = json.loads(result.lifecycle_path.read_text())
        self.assertTrue(lifecycle["costCapAssessment"]["stop"])


if __name__ == "__main__":
    unittest.main()
