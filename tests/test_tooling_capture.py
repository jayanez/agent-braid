# SPDX-License-Identifier: AGPL-3.0-only
"""Offline admission controls; the verifier and decision records are synthetic."""
from __future__ import annotations

import copy
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_capture as capture
from agent_braid import tooling_subscription as subscription_policy
from agent_braid import tooling_model_identity as model_identity_policy
from agent_braid import tooling_sessions as sessions
from tests.test_tooling_subscription import _policy
from agent_braid.tooling_fixtures import load_inventory


def _sha(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


class _SyntheticVerifier:
    """Test-only attestor; it is not evidence of a human or provider decision."""

    def __init__(self, *, mismatch: bool = False):
        self.mismatch = mismatch

    def attest(self, *, registration, slot, authorization, costs, stop_state, subject_sha256,
               model_identity_observation=None):
        return capture.DecisionAttestation(
            verifier_id="synthetic-test-verifier",
            decision_sha256=_sha("synthetic decision").replace("0", "1", 1),
            subject_sha256=("f" * 64 if self.mismatch else subject_sha256),
            verified_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        )


class CaptureAdmissionTests(unittest.TestCase):
    """Exercise admission against copied pinned inputs and a private temp repo."""

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="m45-admission-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.candidate = self.root / "candidate"
        (self.candidate / "examples" / "tooling").mkdir(parents=True)
        source = Path(__file__).resolve().parents[1] / "examples" / "tooling"
        shutil.copyfile(source / "fixture-inventory.json",
                        self.candidate / "examples" / "tooling" / "fixture-inventory.json")
        shutil.copyfile(source / "prompts.json",
                        self.candidate / "examples" / "tooling" / "prompts.json")
        self._git("init", "--quiet", "-b", "main")
        self._git("add", "examples/tooling")
        env = self._git_env()
        subprocess.run(["git", "-C", str(self.candidate), "commit", "--quiet", "-m", "frozen candidate"],
                       check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.commit = self._git("rev-parse", "HEAD")
        self.artifact = self.root / "candidate.whl"
        self.artifact.write_bytes(b"synthetic immutable candidate artifact\n")
        self.artifact_sha256 = _sha(self.artifact.read_bytes())
        self.input_hashes = capture.input_hashes(self.candidate)
        self.registration_data = self._registration()
        self.registration_path = self.root / "registration.json"
        self._write_registration()
        self.valid_registration = evaluation.validate_registration(
            self.registration_data,
            expected_candidate_sha256=self.artifact_sha256,
            expected_input_hashes=self.input_hashes,
        )
        self.ledger = evaluation.new_ledger(self.valid_registration)
        self.account_home = self.root / "trusted-account-home"
        self.account_home.mkdir(mode=0o700)
        account_home_patch = patch.object(capture, "_account_home", return_value=self.account_home)
        account_home_patch.start()
        self.addCleanup(account_home_patch.stop)
        self.receipts = capture.receipt_directory_for(self.valid_registration.sha256)
        self.receipts.parent.parent.mkdir(mode=0o700)
        self.receipts.parent.mkdir(mode=0o700)
        self.receipts.mkdir(mode=0o700)
        self.costs = capture.MeasuredCosts(
            values={"eur": 0.0, "tokens": 0, "input_tokens": 0, "output_tokens": 0,
                    "retry_tokens": 0, "wall_seconds": 0.25, "rss_bytes": 1024,
                    "disk_bytes": 2048},
            source_ref="synthetic-cost-observation",
            source_sha256=_sha("synthetic costs"),
            observed_at="2026-10-08T09:59:00Z",
        )
        self.stop = capture.StopState(
            incident_open=False, unrecoverable_run=False,
            consecutive_infrastructure_failures=0,
            source_ref="synthetic-stop-state", source_sha256=_sha("synthetic stop"),
            observed_at="2026-10-08T09:59:00Z",
        )

    def _registration(self) -> dict:
        inventory = load_inventory(source_checkout=True,
                                   assets_dir=self.candidate / "examples" / "tooling")
        fixtures = [{"fixtureId": item.fixture_id, "journeyClass": item.journey_class,
                     "sha256": item.definition_sha256} for item in inventory.fixtures]
        prompts = [{"promptId": item.prompt_id, "journeyClass": item.journey_class,
                    "sha256": item.sha256} for item in inventory.prompts]
        hosts = []
        for host in evaluation.HOSTS:
            selector = "synthetic-model"
            auth_method = "chatgpt" if host == "codex" else "claude.ai"
            effective_config = {"selector": selector, "effort": "medium",
                "providerEndpoint": "https://api.openai.com/v1" if host == "codex" else "https://api.anthropic.com",
                "authMethod": auth_method,
                "hostSelection": {"source": "argv", "configRef": None, "flags": ["model-selector", "reasoning-effort"],
                                  "argv": ["selector", "effort"]}}
            hosts.append({
                "name": host, "version": "synthetic-host-build", "sha256": _sha("host:" + host),
                "model": {"name": "synthetic-model", "version": "test-model-build",
                          "sha256": _sha("model:" + host)},
                "os": {"name": "macOS", "version": "test-os", "architecture": "arm64",
                       "sha256": _sha("os:" + host)},
                "sdk": {"name": "mcp", "version": "2.3.0", "sha256": _sha("sdk:" + host)},
            })
        fixture_ids = [item["fixtureId"] for item in fixtures]
        return {
            "schemaVersion": evaluation.REGISTRATION_SCHEMA,
            "registrationId": "m45-synthetic-admission-control",
            "status": "approved",
            "ownerApproval": {"status": "approved", "recordId": "synthetic-owner", "sha256": _sha("owner")},
            "candidate": {"commit": self.commit, "version": "0.1.0a1", "sha256": self.artifact_sha256},
            "sourceRights": {"status": "approved", "recordId": "synthetic-rights",
                             "sha256": _sha("rights"), "fixtureIds": fixture_ids,
                             "scope": "synthetic unit-test definitions only"},
            "provider": {"optIn": True, "providerId": "synthetic-provider",
                         "consentRecordId": "synthetic-consent", "consentRecordSha256": _sha("consent")},
            "costCaps": {"eur": 25, "tokens": 4_000_000, "wall_seconds": 28_800,
                         "rss_bytes": 4_294_967_296, "disk_bytes": 5_368_709_120},
            "costRates": {"currency": "EUR", "byHost": [
                {"host": host, "modelName": "synthetic-model", "inputEurPerMillionTokens": 0.0,
                 "outputEurPerMillionTokens": 0.0, "recordId": "synthetic-rate-" + host,
                 "sha256": _sha("rate:" + host)} for host in evaluation.HOSTS]},
            "humanReviewers": [
                {"reviewerId": "synthetic-reviewer-one", "type": "human", "independent": True},
                {"reviewerId": "synthetic-reviewer-two", "type": "human", "independent": True}],
            "rubric": {"version": "synthetic-rubric", "sha256": _sha("rubric"), "frozen": True,
                       "thresholds": {"armCSuccessesPerHost": 16, "authorityCorrectPerHost": 18}},
            "fixtures": fixtures, "prompts": prompts, "hosts": hosts,
        }

    def _git_env(self):
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("GIT_", "SSH_"))}
        env.update({"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_AUTHOR_NAME": "Synthetic test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
                    "GIT_COMMITTER_NAME": "Synthetic test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
                    "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+00:00",
                    "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+00:00"})
        return env

    def _git(self, *args: str) -> str:
        result = subprocess.run(["git", "-C", str(self.candidate), *args], check=True,
                                env=self._git_env(), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
        return result.stdout.strip()

    def _write_registration(self):
        self.registration_path.write_text(
            json.dumps(self.registration_data, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8")

    def _slot(self, journey: str = "analyze-interactions") -> evaluation.AttemptSlot:
        return next(item for item in self.ledger.slots
                    if item.host == "codex" and item.journey_class == journey
                    and self.ledger.current_status(item.slot_id) == "not-started")

    def _authorization(self, journey: str) -> capture.AuthorizationContext:
        mode = {"refuse-missing-grant": "missing-grant",
                "execute-granted-batch-verify": "existing-grant",
                "inspect-recover-interruption": "interrupted-run"}.get(journey, "none")
        extra = {}
        if mode == "existing-grant":
            extra = {"grant_ref": "preexisting-test-grant-record", "grant_sha256": _sha("existing grant"),
                     "plan_sha256": _sha("plan"), "grant_action": "execute"}
        if mode == "interrupted-run":
            extra = {"grant_ref": "preexisting-test-recovery-grant", "grant_sha256": _sha("recovery grant"),
                     "plan_sha256": _sha("interrupted plan"), "grant_action": "resume",
                     "interrupted_run_ref": "external-test-interrupted-run",
                     "interrupted_run_sha256": _sha("interrupted run")}
        return capture.AuthorizationContext(mode, "synthetic-decision-package", _sha("decision"), **extra)

    def _prepare(self, *, journey="analyze-interactions", verifier="default",
                 authorization=None, costs=None, stop=None, receipt_directory=None,
                 model_identity_observation=None):
        slot = self._slot(journey)
        return capture.prepare_attempt(
            registration_path=self.registration_path,
            candidate_root=self.candidate,
            candidate_artifact=self.artifact,
            ledger=self.ledger,
            slot_id=slot.slot_id,
            authorization=authorization or self._authorization(journey),
            costs=costs or self.costs,
            stop_state=stop or self.stop,
            verifier=_SyntheticVerifier() if verifier == "default" else verifier,
            receipt_directory=receipt_directory or self.receipts,
            model_identity_observation=model_identity_observation,
        )

    def _upgrade_to_v2_route_identity(self):
        self.registration_data["schemaVersion"] = evaluation.REGISTRATION_SCHEMA_V2
        for host in self.registration_data["hosts"]:
            selector = host["model"]["name"]
            auth_method = "chatgpt" if host["name"] == "codex" else "claude.ai"
            effective_config = {"selector": selector, "effort": "medium",
                "providerEndpoint": "https://api.openai.com/v1" if host["name"] == "codex" else "https://api.anthropic.com",
                "authMethod": auth_method,
                "hostSelection": {"source": "argv", "configRef": None, "flags": ["model-selector", "reasoning-effort"],
                                  "argv": ["selector", "effort"]}}
            host["model"] = {"name": selector, "version": None, "sha256": None}
            host["modelIdentity"] = {
                "kind": "observable-requested-route", "selectorKind": "provider-alias",
                "selector": selector, "effort": "medium",
                "effectiveConfig": effective_config,
                "configSha256": model_identity_policy.canonical_json_sha256(effective_config),
                "cliBuild": {"version": host["version"], "sha256": host["sha256"]},
                "nativeCatalogEntry": {"observedAtUtc": "2026-10-09T08:00:00Z",
                    "sourceRef": "native-catalog", "catalogSha256": _sha("catalog:" + host["name"]),
                    "entrySha256": _sha("entry:" + host["name"])},
                "providerRoute": {"provider": "openai" if host["name"] == "codex" else "anthropic",
                    "accountSha256": _sha("account:" + host["name"]), "authMethod": auth_method},
                "backendAvailable": False, "immutableId": None,
                "backendDigestAvailable": False, "backendSha256": None,
            }
        self._write_registration()
        self.valid_registration = evaluation.validate_registration(
            self.registration_data, expected_candidate_sha256=self.artifact_sha256,
            expected_input_hashes=self.input_hashes)
        self.ledger = evaluation.new_ledger(self.valid_registration)
        self.receipts = capture.receipt_directory_for(self.valid_registration.sha256)
        self.receipts.mkdir(mode=0o700)

    def _model_observation(self, host="codex", **updates):
        registered = next(item for item in self.registration_data["hosts"] if item["name"] == host)["modelIdentity"]
        catalog = registered["nativeCatalogEntry"]
        values = dict(selector_kind=registered["selectorKind"], configured_selector=registered["selector"], reported_selector=None,
            effort=registered["effort"], config_sha256=registered["configSha256"],
            catalog_sha256=catalog["catalogSha256"], entry_sha256=catalog["entrySha256"],
            provider_route=registered["providerRoute"], backend_available=False, immutable_id=None,
            backend_sha256=None,
            observed_at_utc=datetime.now(timezone.utc), source_ref="synthetic model observer",
            source_sha256=_sha("model observation"))
        values.update(updates)
        return model_identity_policy.ModelIdentityObservation(**values)

    def test_v2_admission_receipt_binds_observable_model_identity_and_rejects_drift(self):
        self._upgrade_to_v2_route_identity()
        obs = self._model_observation()
        admission = self._prepare(model_identity_observation=obs)
        body = json.loads(admission.receipt_path.read_text(encoding="utf-8"))["receipt"]
        self.assertEqual(obs.as_dict(), body["modelIdentityObservation"])
        registered = next(host for host in self.registration_data["hosts"] if host["name"] == "codex")
        self.assertEqual(registered["modelIdentity"], body["hostBuild"]["modelIdentity"])
        changed = self._model_observation(config_sha256=_sha("drifted config"))
        with self.assertRaises(capture.CaptureAdmissionError):
            self._prepare(model_identity_observation=changed)
        with self.assertRaises(capture.CaptureAdmissionError):
            self._prepare()

        class MutatingVerifier(_SyntheticVerifier):
            def attest(self, **kwargs):
                kwargs["model_identity_observation"].provider_route["accountSha256"] = _sha("mutated account")
                return super().attest(**kwargs)

        with self.assertRaisesRegex(capture.CaptureAdmissionError, "expired or drifted"):
            self._prepare(model_identity_observation=self._model_observation(), verifier=MutatingVerifier())

    def test_receipt_binds_registration_candidate_input_host_prompt_and_measures(self):
        admission = self._prepare()
        saved = json.loads(admission.receipt_path.read_text(encoding="utf-8"))
        body = saved["receipt"]
        self.assertEqual(admission.receipt_sha256, _sha(json.dumps(
            body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")))
        self.assertEqual(self.valid_registration.sha256, body["registrationSha256"])
        self.assertEqual(self.commit, body["candidate"]["commit"])
        self.assertEqual(self.artifact_sha256, body["candidate"]["artifactSha256"])
        self.assertEqual("codex", body["slot"]["host"])
        self.assertIn("version", body["hostBuild"]["model"])
        self.assertTrue(body["slot"]["promptSha256"])
        self.assertEqual("admitted-not-started", body["status"])
        self.assertEqual("not-started", self.ledger.current_status(admission.slot_id))
        self.assertEqual(0o600, stat.S_IMODE(admission.receipt_path.stat().st_mode))

    def _subscription_registration(self):
        self.registration_data["billingPolicy"] = _policy()
        self._write_registration()
        self.valid_registration = evaluation.validate_registration(
            self.registration_data, expected_candidate_sha256=self.artifact_sha256,
            expected_input_hashes=self.input_hashes)
        self.ledger = evaluation.new_ledger(self.valid_registration)
        self.receipts = capture.receipt_directory_for(self.valid_registration.sha256)
        binding = subscription_policy.binding_from_registration(
            self.valid_registration, self._slot().slot_id, "codex")
        return subscription_policy.SubscriptionObservation(
            binding, "chatgpt", True, False, False, False, False, True, 0,
            "synthetic-account-billing-source", _sha("synthetic subscription"),
            datetime.now(timezone.utc))

    def _prepare_subscription(self, observation, verifier):
        return capture.prepare_attempt(
            registration_path=self.registration_path, candidate_root=self.candidate,
            candidate_artifact=self.artifact, ledger=self.ledger, slot_id=self._slot().slot_id,
            authorization=self._authorization("analyze-interactions"), costs=self.costs,
            stop_state=self.stop, verifier=verifier, receipt_directory=self.receipts,
            subscription=observation)

    def test_subscription_proof_is_bound_and_explicitly_verified(self):
        observation = self._subscription_registration()
        seen = []
        class Verifier(_SyntheticVerifier):
            def attest(self, *, subscription, **kwargs):
                seen.append(subscription)
                return super().attest(**kwargs)
        admitted = self._prepare_subscription(observation, Verifier())
        self.assertEqual(seen, [observation])
        self.assertEqual(admitted.subscription_binding, observation.binding)
        body = json.loads(admitted.receipt_path.read_text())["receipt"]
        self.assertEqual(body["subscription"], observation.as_dict())
        self.assertEqual(len(self.ledger.slots), 108)
        self.assertEqual(self.ledger.current_status(admitted.slot_id), "not-started")
        self.assertEqual(sessions._read_admission(admitted, self.valid_registration, self._slot())["receipt"], body)
        stripped = replace(admitted, subscription_binding=None)
        with self.assertRaisesRegex(sessions.SessionError, "subscription policy differs"):
            sessions._read_admission(stripped, self.valid_registration, self._slot())
        changed = replace(admitted, subscription_binding=replace(observation.binding, account_sha256="9" * 64))
        with self.assertRaisesRegex(sessions.SessionError, "subscription policy differs"):
            sessions._read_admission(changed, self.valid_registration, self._slot())

    def test_subscription_missing_paid_quota_and_legacy_verifier_refuse(self):
        observation = self._subscription_registration()
        for unsafe in (None, replace(observation, quota_available=False),
                       replace(observation, api_billing_enabled=True),
                       replace(observation, additional_spend_eur=None)):
            with self.subTest(unsafe=unsafe):
                with self.assertRaisesRegex(capture.CaptureAdmissionError, "subscription admission refused"):
                    self._prepare_subscription(unsafe, _SyntheticVerifier())
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "trusted decision verification failed"):
            self._prepare_subscription(observation, _SyntheticVerifier())
        self.assertFalse(self.receipts.exists())

    def test_each_privileged_journey_requires_exact_existing_context(self):
        for journey in ("execute-granted-batch-verify", "inspect-recover-interruption"):
            with self.subTest(journey=journey):
                admission = self._prepare(journey=journey)
                body = json.loads(admission.receipt_path.read_text())["receipt"]
                self.assertEqual(journey, body["slot"]["journeyClass"])
                self.assertTrue(body["authorization"]["grantSha256"])
                self.assertEqual("admitted-not-started", body["status"])

    def test_missing_grant_journey_has_explicitly_absent_grant_context(self):
        admission = self._prepare(journey="refuse-missing-grant")
        auth = json.loads(admission.receipt_path.read_text())["receipt"]["authorization"]
        self.assertEqual("missing-grant", auth["mode"])
        self.assertIsNone(auth["grantRef"])
        self.assertIsNone(auth["grantSha256"])

    def test_duplicate_admission_is_refused_without_overwriting_receipt(self):
        first = self._prepare()
        original = first.receipt_path.read_bytes()
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "already has an admission"):
            self._prepare()
        self.assertEqual(original, first.receipt_path.read_bytes())

    def test_alternate_receipt_directory_cannot_admit_the_same_cohort_slot(self):
        alternate = self.root / "alternate-receipts"
        alternate.mkdir(mode=0o700)
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "fixed per-user store"):
            self._prepare(receipt_directory=alternate)
        self.assertEqual([], list(alternate.iterdir()))

    def test_caller_overridden_home_does_not_change_the_cohort_store(self):
        first = self._prepare()
        alternate_home = self.root / "caller-home"
        alternate_home.mkdir(mode=0o700)
        with patch.dict(os.environ, {"HOME": str(alternate_home)}):
            self.assertEqual(self.receipts, capture.receipt_directory_for(self.valid_registration.sha256))
            with self.assertRaisesRegex(capture.CaptureAdmissionError, "already has an admission"):
                self._prepare()
        self.assertTrue(first.receipt_path.exists())

    def test_concurrent_admissions_for_one_slot_have_exactly_one_winner(self):
        gate = threading.Barrier(2)
        outcomes = []

        def admit():
            gate.wait(timeout=5)
            try:
                outcomes.append(("ok", self._prepare()))
            except capture.CaptureAdmissionError as exc:
                outcomes.append(("refused", str(exc)))

        workers = [threading.Thread(target=admit) for _ in range(2)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join(timeout=10)
        self.assertTrue(all(not worker.is_alive() for worker in workers))
        self.assertCountEqual(["ok", "refused"], [kind for kind, _ in outcomes])
        self.assertEqual(1, len(list(self.receipts.glob("slot-*.json"))))

    def test_authority_must_be_verified_and_attestation_must_bind_exact_subject(self):
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "trusted decision verifier is required"):
            self._prepare(verifier=None)
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "different admission subject"):
            self._prepare(verifier=_SyntheticVerifier(mismatch=True))
        self.assertEqual([], list(self.receipts.iterdir()))

    def test_missing_or_mismatched_existing_grant_context_refuses(self):
        slot = self._slot("execute-granted-batch-verify")
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "does not match"):
            self._prepare(journey=slot.journey_class, authorization=self._authorization("analyze-interactions"))
        invalid = self._authorization("execute-granted-batch-verify")
        invalid = capture.AuthorizationContext(
            mode=invalid.mode, decision_ref=invalid.decision_ref,
            decision_sha256=invalid.decision_sha256, plan_sha256=invalid.plan_sha256,
            grant_action="execute")
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "existing grant reference"):
            self._prepare(journey=slot.journey_class, authorization=invalid)

        recovery = self._authorization("inspect-recover-interruption")
        incomplete_recovery = capture.AuthorizationContext(
            mode=recovery.mode, decision_ref=recovery.decision_ref,
            decision_sha256=recovery.decision_sha256, grant_ref=recovery.grant_ref,
            grant_sha256=recovery.grant_sha256, plan_sha256=recovery.plan_sha256,
            grant_action="resume")
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "interrupted run reference"):
            self._prepare(journey="inspect-recover-interruption", authorization=incomplete_recovery)

    def test_unknown_or_exceeded_costs_fail_closed(self):
        unknown = copy.deepcopy(dict(self.costs.values)); unknown["tokens"] = None
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "cannot assume zero"):
            self._prepare(costs=capture.MeasuredCosts(unknown, "cost-source", _sha("cost"),
                                                      "2026-10-08T10:00:00Z"))
        high = copy.deepcopy(dict(self.costs.values)); high["eur"] = 26
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "cap compliance"):
            self._prepare(costs=capture.MeasuredCosts(high, "cost-source", _sha("cost"),
                                                      "2026-10-08T10:00:00Z"))
        high_tokens = copy.deepcopy(dict(self.costs.values)); high_tokens.update(
            {"input_tokens": 4_000_001, "tokens": 4_000_001})
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "cap compliance"):
            self._prepare(costs=capture.MeasuredCosts(high_tokens, "cost-source", _sha("cost"),
                                                      "2026-10-08T10:00:00Z"))
        self.assertEqual([], list(self.receipts.iterdir()))

    def test_cumulative_cost_snapshot_cannot_erase_prior_attempt_spend(self):
        slot = self.ledger.slots[0]
        self.ledger = evaluation.append_slot_event(
            self.ledger, slot.slot_id, "attempted", attempt_id="prior-attempt",
            data={"sourceTimestamp": "2026-10-08T09:00:00Z"})
        prior_costs = {"eur": 2.0, "tokens": 5, "input_tokens": 3,
                       "output_tokens": 2, "retry_tokens": 0,
                       "wall_seconds": 3.0, "rss_bytes": 4096, "disk_bytes": 8192}
        self.ledger = evaluation.append_slot_event(
            self.ledger, slot.slot_id, "failed", attempt_id="prior-attempt",
            data={"sourceTimestamp": "2026-10-08T09:01:00Z", "completion": False,
                  "authorityCorrect": None, "costs": prior_costs,
                  "inputSha256": slot.fixture_sha256, "outputSha256": _sha("failed output")})
        too_low = capture.MeasuredCosts(
            {**dict(self.costs.values), "eur": 1.0}, "cost-source", _sha("cumulative"),
            "2026-10-08T10:00:00Z")
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "below previously recorded"):
            self._prepare(costs=too_low)
        self.assertEqual([], list(self.receipts.iterdir()))

    def test_incident_unrecoverable_and_two_infra_failures_stop_admission(self):
        for stop in (
            capture.StopState(True, False, 0, "state", _sha("s"), "2026-10-08T10:00:00Z"),
            capture.StopState(False, True, 0, "state", _sha("s"), "2026-10-08T10:00:00Z"),
            capture.StopState(False, False, 2, "state", _sha("s"), "2026-10-08T10:00:00Z"),
        ):
            with self.subTest(stop=stop):
                with self.assertRaises(capture.CaptureAdmissionError):
                    self._prepare(stop=stop)
        self.assertEqual([], list(self.receipts.iterdir()))

    def test_changed_registration_candidate_or_inputs_refuse(self):
        changed = copy.deepcopy(self.registration_data)
        changed["candidate"]["version"] += ".drift"
        self.registration_data = changed
        self._write_registration()
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "registration or ledger validation failed"):
            self._prepare()

    def test_dirty_checkout_and_changed_artifact_refuse(self):
        (self.candidate / "untracked.txt").write_text("drift\n", encoding="utf-8")
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "dirty"):
            self._prepare()
        (self.candidate / "untracked.txt").unlink()
        self.artifact.write_bytes(b"changed build artifact")
        with self.assertRaisesRegex(capture.CaptureAdmissionError, "candidate SHA-256"):
            self._prepare()

    def test_candidate_artifact_drift_during_verifier_call_is_caught(self):
        test = self

        class MutatingVerifier:
            def attest(self, **kwargs):
                test.artifact.write_bytes(b"changed during verification")
                return _SyntheticVerifier().attest(**kwargs)

        with self.assertRaisesRegex(capture.CaptureAdmissionError, "artifact changed during admission"):
            self._prepare(verifier=MutatingVerifier())
        self.assertEqual([], list(self.receipts.iterdir()))


if __name__ == "__main__":
    unittest.main()
