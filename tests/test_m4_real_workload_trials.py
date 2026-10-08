# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic-only safety and denominator controls for SPEC-038 trial engine."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
import uuid
from unittest.mock import patch

from agent_braid import m4_real_workload_trials as trials
from agent_braid import git_runtime, runtime_policy
from agent_braid import m4_real_workload as workload
from scripts import measure_m4_real_workload as measure
from scripts import verify_m4_real_workload as fresh_verify


def _raw(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def _accounting():
    ticks = iter(range(1, 10000))
    from agent_braid.utility_accounting import UtilityAccounting
    accounting = UtilityAccounting(monotonic=lambda: next(ticks) / 1000,
                                   parent_cpu=lambda: 0.0, child_attribution_valid=False,
                                   lifetime_rss=lambda: 0)
    accounting.start()
    with accounting.activate_git_budget_registry():
        for name in trials.PHASES:
            with accounting.phase(name):
                pass
    return accounting.finish(outcome="success")


class RealWorkloadTrialTests(unittest.TestCase):
    def setUp(self):
        self.candidate = "a" * 40
        schedule = trials.build_schedule()
        self.manifest = {
            "recordVersion": "synthetic-test-only",
            "candidateCommit": self.candidate,
            "captureAuthorization": False,
            "expectedFinalTrees": {"AB": "1" * 40, "BA": "2" * 40},
            "harnessInputHashes": {"synthetic_fixture.py": "3" * 64},
            "slots": [],
        }
        for slot in schedule["slots"]:
            self.manifest["slots"].append({
                **deepcopy(slot), "runPath": "/private/test/" + slot["slotId"],
                "grantPath": "/private/test/" + slot["slotId"] + ".grants",
                "expectedFinalTree": self.manifest["expectedFinalTrees"][slot["operationOrder"]],
            })
        self.manifest_raw = _raw(self.manifest)
        self.manifest_sha = hashlib.sha256(self.manifest_raw).hexdigest()
        self.manifest["manifestSha256"] = self.manifest_sha  # validator-enriched raw-file digest
        now = datetime.now(timezone.utc)
        self.review_raw = _raw({
            "recordVersion": "m4-real-workload-harness-review-v1", "decision": "approved",
            "reviewedCandidateCommit": self.candidate,
            "reviewedManifestSha256": self.manifest_sha,
            "reviewedAt": (now - timedelta(minutes=20)).isoformat(),
        })
        self.capture_raw = _raw({
            "recordVersion": "m4-real-workload-capture-authorization-v1", "decision": "approved",
            "reviewedCandidateCommit": self.candidate,
            "reviewedManifestSha256": self.manifest_sha,
            "reviewedReviewSha256": hashlib.sha256(self.review_raw).hexdigest(),
            "authorizedAt": (now - timedelta(minutes=10)).isoformat(),
            "registeredCaptureAuthorized": True,
        })

    def validator(self, raw):
        return {**json.loads(raw), "manifestSha256": hashlib.sha256(raw).hexdigest()}

    def authority_verifier(self, kind, raw, candidate, manifest_sha):
        expected = {
            "stable-harness-manifest-review": self.review_raw,
            "capture-authorization": self.capture_raw,
        }
        return (raw == expected[kind] and candidate == self.candidate
                and manifest_sha == self.manifest_sha)

    def call(self, *, callback_factory=None, authority=None, manifest=None, clock=None):
        return trials.run_trials(
            manifest_raw=self.manifest_raw,
            manifest=self.manifest if manifest is None else manifest,
            manifest_validator=self.validator,
            review_raw=self.review_raw,
            capture_authorization_raw=self.capture_raw,
            authority_verifier=self.authority_verifier if authority is None else authority,
            identity_check=lambda: True,
            callback_factory=callback_factory or (lambda _manifest: (lambda _slot: None, {"synthetic": True})),
            monotonic_ns=clock or (lambda: 100),
        )

    def test_protocol_schedule_is_frozen_and_contains_twenty_unique_slots(self):
        schedule = trials.build_schedule()
        self.assertEqual([row["pairId"] for row in schedule["pairs"]],
                         ["W-AB-1", "W-AB-2", "W-BA-1", "W-BA-2", "M-AB-2",
                          "M-BA-2", "M-BA-3", "M-AB-1", "M-AB-3", "M-BA-1"])
        self.assertEqual(len(schedule["slots"]), 20)
        self.assertEqual(len({row["slotId"] for row in schedule["slots"]}), 20)
        self.assertEqual(sum(row["pairKind"] == "warmup" for row in schedule["pairs"]), 4)
        self.assertEqual(sum(row["pairKind"] == "measured" for row in schedule["pairs"]), 6)

    def test_exact_gate_runs_before_any_callback_or_fixture_preparation(self):
        events = []
        def verifier(kind, raw, candidate, manifest_sha):
            events.append("authority:" + kind)
            return self.authority_verifier(kind, raw, candidate, manifest_sha)
        def factory(_manifest):
            events.append("factory")
            return lambda _slot: {"status": "inconclusive"}, {"synthetic": True}
        # A valid gate reaches the factory only after both independent decisions.
        result = self.call(authority=verifier, callback_factory=factory,
                           clock=iter([100, 100 + trials.DISPATCH_BUDGET_NS]).__next__)
        self.assertEqual(events, ["authority:stable-harness-manifest-review",
                                  "authority:capture-authorization", "factory"])
        self.assertEqual(result["denominator"]["unexecutedPairs"], 10)

    def test_truthy_but_non_boolean_authority_response_is_rejected_before_factory(self):
        created = []
        with self.assertRaisesRegex(trials.InvalidRealWorkload, "authenticated stable-harness"):
            self.call(authority=lambda *_: 1,
                      callback_factory=lambda _: (created.append(True), None))
        self.assertEqual(created, [])

    def test_review_must_bind_raw_manifest_and_capture_must_bind_review(self):
        bad_review = json.loads(self.review_raw)
        bad_review["reviewedManifestSha256"] = "0" * 64
        review_raw = _raw(bad_review)
        capture = json.loads(self.capture_raw)
        capture["reviewedReviewSha256"] = hashlib.sha256(review_raw).hexdigest()
        with self.assertRaisesRegex(trials.InvalidRealWorkload, "exact candidate and manifest"):
            trials.validate_review_and_capture_authority(
                manifest=self.manifest, manifest_raw=self.manifest_raw,
                review_raw=review_raw, capture_raw=_raw(capture),
                authority_verifier=lambda *_: True)

    def test_review_after_capture_and_capture_after_action_are_rejected(self):
        capture = json.loads(self.capture_raw)
        capture["authorizedAt"] = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        with self.assertRaisesRegex(trials.InvalidRealWorkload, "predate this action in order"):
            trials.validate_review_and_capture_authority(
                manifest=self.manifest, manifest_raw=self.manifest_raw,
                review_raw=self.review_raw, capture_raw=_raw(capture),
                authority_verifier=lambda *_: True)

    def test_all_twenty_slots_remain_when_dispatch_budget_expires(self):
        events = []
        def factory(_manifest):
            events.append("factory")
            return lambda _slot: events.append("callback"), {"synthetic": True}
        ticks = iter([100, 100 + trials.DISPATCH_BUDGET_NS])
        result = self.call(callback_factory=factory, clock=lambda: next(ticks))
        self.assertEqual(len(result["slots"]), 20)
        self.assertTrue(all(row["status"] == "unexecuted" for row in result["slots"]))
        self.assertEqual(result["denominator"]["intendedPairs"], 10)
        self.assertEqual(result["denominator"]["unexecutedPairs"], 10)
        self.assertEqual(events, ["factory"])

    def test_unknown_treatment_failure_stops_dispatch_and_preserves_remaining_slots(self):
        calls = []
        def factory(_manifest):
            def callback(_slot):
                calls.append(True)
                raise RuntimeError("synthetic uncertainty")
            return callback, {"synthetic": True}
        result = self.call(callback_factory=factory)
        self.assertEqual(len(result["slots"]), 20)
        self.assertEqual(result["slots"][0]["status"], "invalid")
        self.assertTrue(all(row["status"] == "unexecuted" for row in result["slots"][1:]))
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["denominator"]["invalidPairs"], 1)
        self.assertEqual(result["denominator"]["unexecutedPairs"], 10)

    def test_same_slot_recovery_requires_consumed_bound_resume_grant_and_never_becomes_valid(self):
        slot = deepcopy(self.manifest["slots"][0])
        request = {"repository": "/synthetic/source", "expectedFinalTree": slot["expectedFinalTree"]}
        plan = {"runtimeManifest": {"request": request, "runDirectory": slot["runPath"],
                                    "manifestDigest": "manifest-digest"},
                "planDigest": "plan-digest"}
        original_grant_id, resume_grant_id = str(uuid.uuid4()), str(uuid.uuid4())
        interrupted_accounting = _accounting()
        interrupted_accounting.update(complete=False, outcome="failure",
                                     errors=["synthetic interrupted treatment"])
        original = {"recordVersion": "agent-braid-m4-real-workload-treatment-v1",
                    "status": "interrupted", "accounting": interrupted_accounting,
                    "operational": {"status": "interrupted", "slotId": slot["slotId"],
                                    "mode": slot["mode"], "plan": plan,
                                    "grantId": original_grant_id,
                                    "sourceIntegrityAtFailure": "unchanged"}}
        report = {"dispatch": "performed", "grantId": resume_grant_id,
                  "runtime": {"status": "completed", "manifestDigest": "manifest-digest",
                              "runDirectory": slot["runPath"],
                              "resultTree": slot["expectedFinalTree"]}}
        inspection = {"dispatch": "not-dispatched", "executionAuthorization": False,
                      "planDigest": "plan-digest",
                      "runtime": {"status": "verified-completed", "manifestDigest": "manifest-digest",
                                  "runDirectory": slot["runPath"],
                                  "resultTree": slot["expectedFinalTree"]}}
        sample = {"recordVersion": trials.RECOVERY_VERSION, "status": "recovered",
                  "originalTreatment": original,
                  "recovery": {"plan": plan, "grantStore": slot["grantPath"],
                               "grantId": resume_grant_id, "report": report,
                               "finalInspection": inspection, "accounting": _accounting()}}
        verified_plan = {"runtimeManifest": plan["runtimeManifest"], "planDigest": "plan-digest",
                         "policy": {"revision": runtime_policy.POLICY}}

        def read_grant(_root, identifier):
            action = "execute" if identifier == original_grant_id else "resume"
            return {"grantId": identifier, "action": action, "state": "consumed",
                    "planDigest": ("plan-digest" if identifier in {original_grant_id, resume_grant_id} else "wrong-plan"),
                    "manifestDigest": "manifest-digest",
                    "runDirectory": slot["runPath"]}

        with patch.object(trials.runtime_policy, "verify_policy_plan", return_value=verified_plan), \
             patch.object(trials.runtime_policy, "_store", return_value=Path("/synthetic/grants")), \
             patch.object(trials.runtime_policy, "_read_grant", side_effect=read_grant), \
             patch("agent_braid.m4_real_workload.runtime_inputs_for_slot",
                   return_value={"runtimeRequest": request, "expectedFinalTree": slot["expectedFinalTree"]}):
            disposition, reason = trials._sample_disposition(
                sample, slot, slot["expectedFinalTree"], self.manifest)
            self.assertEqual(disposition, "recovered", reason)
            bad = deepcopy(sample)
            bad["recovery"]["grantId"] = str(uuid.uuid4())
            with self.assertRaisesRegex(trials.InvalidRealWorkload, "consumed same-plan"):
                trials._validate_recovered_sample(bad, slot, slot["expectedFinalTree"], self.manifest)

            result = self.call(callback_factory=lambda _manifest: (lambda _slot: sample, {"synthetic": True}))
        self.assertEqual(result["slots"][0]["status"], "recovered")
        self.assertEqual(result["stopReason"], "recovery-observed")
        self.assertTrue(all(row["status"] == "unexecuted" for row in result["slots"][1:]))
        self.assertEqual(result["denominator"]["recoveredPairs"], 1)
        self.assertEqual(result["denominator"]["validMeasuredPairs"], 0)

    def test_owned_synthetic_interruption_resume_and_readonly_inspection_ingest_same_slot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            repo = root / "source"
            repo.mkdir()

            def git(*args):
                env = os.environ.copy()
                env["GIT_CONFIG_NOSYSTEM"] = "1"
                env["GIT_CONFIG_GLOBAL"] = os.devnull
                return subprocess.run(["git", "-C", str(repo), *args], env=env,
                                      capture_output=True, check=True).stdout.decode().strip()

            git("init", "-q", "-b", "main")
            git("config", "user.name", "Synthetic recovery test")
            git("config", "user.email", "recovery@example.invalid")
            for name in ("a.txt", "b.txt"):
                (repo / name).write_text("base\n")
            git("add", ".")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD")
            commits = {}
            for identifier in ("a", "b"):
                git("checkout", "-qb", "op-" + identifier, base)
                (repo / (identifier + ".txt")).write_text(identifier + "\n")
                git("add", identifier + ".txt")
                git("commit", "-qm", "operation " + identifier)
                commits[identifier] = git("rev-parse", "HEAD")
            git("checkout", "-q", "--detach", base)
            for identifier in ("a", "b"):
                (repo / (identifier + ".txt")).write_text(identifier + "\n")
            git("add", ".")
            expected_tree = git("write-tree")
            git("reset", "--hard", "-q", base)
            operations = [{"instanceId": name, "attemptId": name + "-resume-attempt",
                           "source": {"kind": "commit", "revision": commits[name]},
                           "dependencies": [], "uncertainPaths": [],
                           "declaredWrites": [name + ".txt"]} for name in ("a", "b")]
            replay_operations = [{k: v for k, v in item.items() if k != "declaredWrites"}
                                 for item in operations]
            runtime_request = {"gitRuntimeRequestVersion": git_runtime.VERSION,
                               "repository": str(repo), "baseRevision": base,
                               "expectedFinalTree": expected_tree, "order": ["a", "b"],
                               "operations": operations}
            replay_request = {"gitAnalysisRequestVersion": "0.1.0-alpha",
                              "repository": str(repo), "baseRevision": base,
                              "operations": replay_operations}
            slot = {**trials.build_schedule()["slots"][0],
                    "runPath": str(root / "recovered-run"),
                    "grantPath": str(root / "recovered-grants")}
            source_receipt = workload.source_fingerprint(repo)
            cancel = threading.Event()
            original_git = git_runtime._git
            original_execute = runtime_policy.execute_policy_run
            executing = {"value": False}

            def interrupt_after_apply(*args, **kwargs):
                result = original_git(*args, **kwargs)
                if (executing["value"] and Path(args[0]) == Path(slot["runPath"]) / "result.git"
                        and "apply" in args[3:]):
                    cancel.set()
                return result

            def execute_then_interrupt(*args, **kwargs):
                executing["value"] = True
                return original_execute(*args, **kwargs)

            with patch.object(git_runtime, "_git", side_effect=interrupt_after_apply), \
                 patch.object(runtime_policy, "execute_policy_run", side_effect=execute_then_interrupt):
                interrupted = trials.run_treatment(
                    slot, input_factory=lambda: {"runtimeRequest": runtime_request,
                                                 "replayRequest": replay_request,
                                                 "expectedFinalTree": expected_tree},
                    source_repository=repo, source_fingerprint=source_receipt,
                    source_integrity_check=workload.source_fingerprint,
                    cancel_event=cancel)
            self.assertEqual(interrupted["status"], "interrupted", interrupted)
            self.assertTrue(trials._valid_retained_accounting(interrupted["accounting"]),
                            {k: interrupted["accounting"].get(k) for k in ("complete", "outcome", "errors")})
            original_plan = interrupted["operational"]["plan"]
            original_grant_id = interrupted["operational"]["grantId"]
            resume_grant = runtime_policy.issue_operator_grant(
                original_plan, slot["grantPath"], acknowledge=original_plan["planDigest"],
                action="resume")
            recovery_report = runtime_policy.recover_policy_run(
                original_plan, slot["grantPath"], resume_grant["grantId"], action="resume")
            final_inspection = runtime_policy.inspect_policy_run(original_plan, slot["grantPath"])
            self.assertEqual(final_inspection.get("dispatch"), "not-dispatched", final_inspection)
            self.assertIs(final_inspection.get("executionAuthorization"), False, final_inspection)
            self.assertEqual(final_inspection.get("runtime", {}).get("status"), "verified-completed", final_inspection)
            self.assertEqual(final_inspection.get("runtime", {}).get("resultTree"), expected_tree, final_inspection)
            recovered = {"recordVersion": trials.RECOVERY_VERSION, "status": "recovered",
                         "originalTreatment": interrupted,
                         "recovery": {"plan": original_plan, "grantStore": slot["grantPath"],
                                      "grantId": resume_grant["grantId"], "report": recovery_report,
                                      "finalInspection": final_inspection, "accounting": _accounting()}}
            recovered_manifest = {"sourceRepository": str(repo), "slots": [slot]}
            with patch.object(workload, "runtime_inputs_for_slot",
                              return_value={"runtimeRequest": runtime_request,
                                            "expectedFinalTree": expected_tree}):
                disposition, reason = trials._sample_disposition(
                    recovered, slot, expected_tree, recovered_manifest)
            self.assertEqual(disposition, "recovered", reason)
            self.assertNotEqual(original_grant_id, resume_grant["grantId"])
            self.assertEqual(recovery_report["runtime"]["status"], "completed")
            self.assertEqual(final_inspection["runtime"]["status"], "verified-completed")

            verification_slots = []
            for frozen in trials.build_schedule()["slots"]:
                if frozen["slotId"] == slot["slotId"]:
                    descriptor = {**frozen, "runPath": slot["runPath"],
                                  "grantPath": slot["grantPath"], "expectedFinalTree": expected_tree}
                else:
                    descriptor = {**frozen,
                                  "runPath": str(root / ("run-" + frozen["slotId"])),
                                  "grantPath": str(root / ("grant-" + frozen["slotId"])),
                                  "expectedFinalTree": expected_tree}
                verification_slots.append(descriptor)
            verification_manifest = {
                "candidateCommit": "d" * 40, "sourceRepository": str(repo),
                "sourceFingerprint": source_receipt,
                "harnessInputHashes": {"synthetic-owned-fixture": "e" * 64},
                "expectedFinalTrees": {"AB": expected_tree, "BA": expected_tree},
                "slots": verification_slots,
            }
            manifest_bytes = _raw(verification_manifest)
            record = {"recordVersion": trials.RECORD_VERSION,
                      "candidateCommit": verification_manifest["candidateCommit"],
                      "manifestSha256": hashlib.sha256(manifest_bytes).hexdigest(),
                      "slots": [],
                      "denominator": {"intendedPairs": 10, "warmupPairs": 4, "measuredPairs": 6,
                                      "validMeasuredPairs": 0, "invalidPairs": 1,
                                      "failedPairs": 0, "refusedPairs": 0,
                                      "interruptedPairs": 0, "recoveredPairs": 1,
                                      "unexecutedPairs": 10, "attemptedTreatments": 1}}
            for descriptor in verification_slots:
                row = {**descriptor, "status": "unexecuted", "reason": "not dispatched after recovery",
                       "sample": None}
                if descriptor["slotId"] == slot["slotId"]:
                    row.update(status="recovered", reason="same-slot recovery retained", sample=recovered)
                record["slots"].append(row)
            with patch.object(fresh_verify.source, "source_fingerprint", return_value=source_receipt), \
                 patch.object(fresh_verify, "_candidate_identity", return_value=True), \
                 patch.object(workload, "runtime_inputs_for_slot",
                              return_value={"runtimeRequest": runtime_request,
                                            "expectedFinalTree": expected_tree}):
                fresh_report = fresh_verify._verify_validated_record(
                    verification_manifest, manifest_bytes, _raw(record))
            recovered_row = next(row for row in fresh_report["slots"] if row["slotId"] == slot["slotId"])
            self.assertEqual(fresh_report["status"], "verified")
            self.assertEqual(recovered_row["disposition"], "recovered")
            self.assertTrue(recovered_row["independentVerification"])
            self.assertEqual(recovered_row["resultTree"], expected_tree)

    def test_complete_synthetic_rows_keep_six_measured_ratios_and_all_warmups(self):
        accounting = _accounting()
        calls = []
        def factory(manifest):
            def callback(slot):
                calls.append(slot["slotId"])
                tree = manifest["expectedFinalTrees"][slot["operationOrder"]]
                grant = str(uuid.uuid5(uuid.NAMESPACE_URL, slot["slotId"]))
                digest = "sha256:" + hashlib.sha256(slot["slotId"].encode()).hexdigest()
                return {"status": "completed", "accounting": accounting,
                        "operational": {"slotId": slot["slotId"], "mode": slot["mode"],
                                        "resultTree": tree, "immutableSourceUnchanged": True,
                                        "grantId": grant, "plan": {"planDigest": digest}}}
            return callback, {"synthetic": True}
        result = self.call(callback_factory=factory)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(len(calls), 20)
        self.assertEqual(result["denominator"]["validMeasuredPairs"], 6)
        self.assertEqual(len(result["measuredRatios"]), 6)
        self.assertEqual(result["medianMeasuredRatio"], 1.0)

    def test_phase_accounting_rejects_residual_double_count(self):
        accounting = _accounting()
        self.assertTrue(trials._valid_accounting(accounting))
        altered = deepcopy(accounting)
        altered["residualWallNs"] += 1
        self.assertFalse(trials._valid_accounting(altered))

    def test_owned_synthetic_git_treatments_retain_outputs_for_fresh_readonly_inspection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            repo = root / "source"
            repo.mkdir()

            def git(*args):
                env = os.environ.copy()
                env["GIT_CONFIG_NOSYSTEM"] = "1"
                env["GIT_CONFIG_GLOBAL"] = os.devnull
                return subprocess.run(["git", "-C", str(repo), *args], env=env,
                                      capture_output=True, check=True).stdout.decode().strip()

            git("init", "-q", "-b", "main")
            git("config", "user.name", "Synthetic runtime test")
            git("config", "user.email", "synthetic@example.invalid")
            for name in ("a.txt", "b.txt"):
                (repo / name).write_text("base\n")
            git("add", ".")
            git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD")
            commits = {}
            for identifier in ("a", "b"):
                git("checkout", "-qb", "op-" + identifier, base)
                (repo / (identifier + ".txt")).write_text(identifier + "\n")
                git("add", identifier + ".txt")
                git("commit", "-qm", "operation " + identifier)
                commits[identifier] = git("rev-parse", "HEAD")
            git("checkout", "-q", "--detach", base)
            for identifier in ("a", "b"):
                (repo / (identifier + ".txt")).write_text(identifier + "\n")
            git("add", ".")
            expected_tree = git("write-tree")
            git("reset", "--hard", "-q", base)

            operations = [
                {"instanceId": name, "attemptId": name + "-attempt",
                 "source": {"kind": "commit", "revision": commits[name]},
                 "dependencies": [], "uncertainPaths": [], "declaredWrites": [name + ".txt"]}
                for name in ("a", "b")
            ]
            replay_operations = [{k: v for k, v in item.items() if k != "declaredWrites"}
                                 for item in operations]
            repository_fingerprint = trials._source_fingerprint(repo)
            plans = []
            for mode, order in (("serial", ["a", "b"]), ("parallel", ["b", "a"])):
                request = {"gitRuntimeRequestVersion": git_runtime.VERSION,
                           "repository": str(repo), "baseRevision": base,
                           "expectedFinalTree": expected_tree, "order": order,
                           "operations": operations}
                replay_request = {"gitAnalysisRequestVersion": "0.1.0-alpha",
                                  "repository": str(repo), "baseRevision": base,
                                  "operations": replay_operations}
                slot = {"slotId": "synthetic-" + mode, "mode": mode,
                        "runPath": str(root / ("run-" + mode)),
                        "grantPath": str(root / ("grant-" + mode))}
                sample = trials.run_treatment(
                    slot, input_factory=lambda r=request, q=replay_request: {
                        "runtimeRequest": r, "replayRequest": q,
                        "expectedFinalTree": expected_tree},
                    source_repository=repo, source_fingerprint=repository_fingerprint)
                self.assertEqual(sample["status"], "completed", sample)
                self.assertTrue(Path(slot["runPath"]).is_dir())
                self.assertTrue(Path(slot["grantPath"]).is_dir())
                self.assertTrue(trials._valid_accounting(sample["accounting"]))
                self.assertEqual(trials._sample_disposition(sample, slot, expected_tree)[0], "valid")
                plans.append({"plan": sample["operational"]["plan"],
                              "grantPath": slot["grantPath"], "runPath": slot["runPath"],
                              "expected": expected_tree})

            plans_path = root / "fresh-input.json"
            plans_path.write_text(json.dumps(plans))
            readonly_check = """import json,sys
from pathlib import Path
from agent_braid import runtime_policy
items=json.loads(Path(sys.argv[1]).read_text())
for item in items:
    result=runtime_policy.inspect_policy_run(item['plan'],item['grantPath'])
    runtime=result['runtime']
    assert runtime['status']=='verified-completed'
    assert runtime['resultTree']==item['expected']
print('verified',len(items))
"""
            checked = subprocess.run([sys.executable, "-c", readonly_check, str(plans_path)],
                                     cwd=Path(__file__).resolve().parents[1],
                                     capture_output=True, text=True, timeout=120)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertEqual(checked.stdout.strip(), "verified 2")

            altered_state = Path(plans[1]["runPath"]) / "state.json"
            altered_state.write_text("{}\n")
            tamper_check = """import json,sys
from pathlib import Path
from agent_braid import runtime_policy
item=json.loads(Path(sys.argv[1]).read_text())[1]
try:
    runtime_policy.inspect_policy_run(item['plan'],item['grantPath'])
except Exception:
    print('rejected')
else:
    raise SystemExit('tampered result was accepted')
"""
            rejected = subprocess.run([sys.executable, "-c", tamper_check, str(plans_path)],
                                      cwd=Path(__file__).resolve().parents[1],
                                      capture_output=True, text=True, timeout=120)
            self.assertEqual(rejected.returncode, 0, rejected.stderr)
            self.assertEqual(rejected.stdout.strip(), "rejected")

    def test_fresh_verifier_checks_all_twenty_slot_dispositions_and_rejects_tree_mismatch(self):
        schedule = trials.build_schedule()
        source_path = Path(tempfile.mkdtemp(prefix="m4-verify-source-"))
        manifest = {"candidateCommit": "5" * 40, "sourceRepository": str(source_path),
                    "sourceFingerprint": {"synthetic": "owned"},
                    "harnessInputHashes": {"synthetic_fixture.py": "6" * 64},
                    "expectedFinalTrees": {"AB": "7" * 40, "BA": "8" * 40}, "slots": []}
        for slot in schedule["slots"]:
            manifest["slots"].append({**deepcopy(slot),
                                      "runPath": "/tmp/synthetic/" + slot["slotId"],
                                      "grantPath": "/tmp/synthetic/" + slot["slotId"] + ".grants",
                                      "expectedFinalTree": manifest["expectedFinalTrees"][slot["operationOrder"]]})
        manifest_raw = b"synthetic exact manifest bytes"
        manifest_sha = hashlib.sha256(manifest_raw).hexdigest()
        record = {"recordVersion": trials.RECORD_VERSION, "candidateCommit": manifest["candidateCommit"],
                  "manifestSha256": manifest_sha, "slots": [],
                  "denominator": {"intendedPairs": 10, "warmupPairs": 4, "measuredPairs": 6,
                                  "validMeasuredPairs": 1, "invalidPairs": 0,
                                  "failedPairs": 0, "refusedPairs": 0,
                                  "interruptedPairs": 0, "recoveredPairs": 0,
                                  "unexecutedPairs": 8, "attemptedTreatments": 4}}
        expected_by_id = {}
        for slot in manifest["slots"]:
            expected_tree = manifest["expectedFinalTrees"][slot["operationOrder"]]
            expected_by_id[slot["slotId"]] = expected_tree
            row = {**deepcopy(slot), "status": "unexecuted", "reason": "synthetic test denominator", "sample": None}
            if slot["pairId"] in {"W-AB-1", "M-AB-1"}:
                plan = {"policy": {"revision": ("owned-operator-grant-v1" if slot["mode"] == "serial"
                                                  else "parallel-owned-operator-grant-v1")},
                        "runtimeManifest": {"request": {"synthetic": slot["slotId"]},
                                           "runDirectory": slot["runPath"]}}
                row.update(status="valid", sample={"status": "completed", "operational": {
                    "plan": plan, "slotId": slot["slotId"], "mode": slot["mode"]}})
            record["slots"].append(row)
        record_raw = _raw(record)

        def fake_inputs(_manifest, slot):
            return {"runtimeRequest": {"synthetic": slot["slotId"]},
                    "expectedFinalTree": expected_by_id[slot["slotId"]]}

        def inspector(plan, _grant):
            slot_id = plan["runtimeManifest"]["request"]["synthetic"]
            tree = expected_by_id[slot_id]
            return {"runtime": {"status": "verified-completed", "resultTree": tree}}

        with patch.object(fresh_verify.source, "source_fingerprint", return_value=manifest["sourceFingerprint"]), \
             patch.object(fresh_verify, "_candidate_identity", return_value=True), \
             patch.object(fresh_verify.source, "runtime_inputs_for_slot", side_effect=fake_inputs), \
             patch.object(fresh_verify.runtime_policy, "inspect_policy_run", side_effect=inspector):
            report = fresh_verify._verify_validated_record(manifest, manifest_raw, record_raw)
        self.assertEqual(report["status"], "verified")
        self.assertEqual(report["inspectedSlots"], 20)
        self.assertEqual(sum(row["disposition"] == "unexecuted" for row in report["slots"]), 16)
        self.assertTrue(next(row for row in report["pairTreeComparisons"]
                             if row["pairId"] == "W-AB-1")["treesMatch"])

        def wrong_tree(plan, _grant):
            result = inspector(plan, _grant)
            result["runtime"]["resultTree"] = "9" * 40
            return result

        with patch.object(fresh_verify.source, "source_fingerprint", return_value=manifest["sourceFingerprint"]), \
             patch.object(fresh_verify, "_candidate_identity", return_value=True), \
             patch.object(fresh_verify.source, "runtime_inputs_for_slot", side_effect=fake_inputs), \
             patch.object(fresh_verify.runtime_policy, "inspect_policy_run", side_effect=wrong_tree):
            rejected = fresh_verify._verify_validated_record(manifest, manifest_raw, record_raw)
        self.assertEqual(rejected["status"], "inconclusive")
        bad = [row for row in rejected["slots"] if row["disposition"] == "invalid"]
        self.assertEqual(len(bad), 4)
        self.assertEqual(rejected["capturedDenominator"]["validMeasuredPairs"], 1)
        self.assertEqual(rejected["postVerificationDenominator"]["validMeasuredPairs"], 0)
        self.assertEqual(len(rejected["verificationChangedSlots"]), 4)

        partial_failure = deepcopy(record)
        for row in partial_failure["slots"]:
            row.update(status="unexecuted", reason="not dispatched after first treatment failure", sample=None)
        partial_failure["slots"][0].update(status="invalid", reason="synthetic first treatment failure")
        partial_failure["denominator"] = {
            "intendedPairs": 10, "warmupPairs": 4, "measuredPairs": 6,
            "validMeasuredPairs": 0, "invalidPairs": 1,
            "failedPairs": 0, "refusedPairs": 0, "interruptedPairs": 0, "recoveredPairs": 0,
            "unexecutedPairs": 10,
            "attemptedTreatments": 1,
        }
        partial_raw = _raw(partial_failure)
        with patch.object(fresh_verify.source, "source_fingerprint", return_value=manifest["sourceFingerprint"]), \
             patch.object(fresh_verify, "_candidate_identity", return_value=True), \
             patch.object(fresh_verify.source, "runtime_inputs_for_slot", side_effect=fake_inputs), \
             patch.object(fresh_verify.runtime_policy, "inspect_policy_run", side_effect=AssertionError("no completed sample")):
            partial_report = fresh_verify._verify_validated_record(manifest, manifest_raw, partial_raw)
        self.assertEqual(partial_report["status"], "verified")
        self.assertEqual(partial_report["inspectedSlots"], 20)
        self.assertEqual(partial_report["capturedDenominator"]["invalidPairs"], 1)
        self.assertEqual(partial_report["capturedDenominator"]["unexecutedPairs"], 10)
        self.assertEqual(partial_report["postVerificationDenominator"]["invalidPairs"], 1)
        self.assertEqual(partial_report["postVerificationDenominator"]["unexecutedPairs"], 10)

        unexpected_manifest = deepcopy(manifest)
        unexpected_record = deepcopy(partial_failure)
        retained_root = Path(tempfile.mkdtemp(prefix="m4-unexpected-unexecuted-artifact-"))
        run_artifact, grant_artifact = retained_root / "unexpected-run", retained_root / "unexpected-grant"
        run_artifact.mkdir()
        grant_artifact.mkdir()
        unexpected_slot = unexpected_manifest["slots"][1]
        unexpected_slot["runPath"], unexpected_slot["grantPath"] = str(run_artifact), str(grant_artifact)
        unexpected_row = unexpected_record["slots"][1]
        unexpected_row["runPath"], unexpected_row["grantPath"] = str(run_artifact), str(grant_artifact)
        with patch.object(fresh_verify.source, "source_fingerprint", return_value=manifest["sourceFingerprint"]), \
             patch.object(fresh_verify, "_candidate_identity", return_value=True), \
             patch.object(fresh_verify.source, "runtime_inputs_for_slot", side_effect=fake_inputs), \
             patch.object(fresh_verify.runtime_policy, "inspect_policy_run", side_effect=AssertionError("no completed sample")):
            unexpected_report = fresh_verify._verify_validated_record(
                unexpected_manifest, manifest_raw, _raw(unexpected_record))
        self.assertEqual(unexpected_report["status"], "inconclusive")
        changed = {row["slotId"]: row for row in unexpected_report["verificationChangedSlots"]}
        self.assertEqual(changed[unexpected_row["slotId"]]["capturedDisposition"], "unexecuted")
        self.assertEqual(changed[unexpected_row["slotId"]]["freshDisposition"], "invalid")

    def test_cli_capture_path_is_refused(self):
        result = subprocess.run([sys.executable, str(trials.Path(__file__).resolve().parents[1] /
                                                       "scripts/measure_m4_real_workload.py")],
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)["registeredCaptureAuthorized"], False)

    def test_fresh_verifier_failure_preserves_owned_run_and_grant_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root = root / "synthetic-source"
            common_root = root / "synthetic-common"
            source_root.mkdir()
            common_root.mkdir()
            run_path, grant_path = root / "run-owned", root / "grant-owned"
            run_path.mkdir(mode=0o700)
            grant_path.mkdir(mode=0o700)
            (run_path / "result.json").write_text("synthetic retained result\n")
            (grant_path / "grant.json").write_text("synthetic retained grant\n")
            manifest = {
                "candidateCommit": "a" * 40,
                "sourceRepository": str(source_root),
                "sourceFingerprint": {"commonDirectory": str(common_root)},
                "slots": [{"runPath": str(run_path), "grantPath": str(grant_path)}],
            }
            manifest_raw = b"synthetic manifest bytes"
            manifest_path = root / "manifest.json"
            review_path, capture_path = root / "review.json", root / "capture.json"
            manifest_path.write_bytes(manifest_raw)
            review_path.write_bytes(b"synthetic review")
            capture_path.write_bytes(b"synthetic capture authorization")
            output_path = root / "trial-record.json"
            fake_record = {"recordVersion": trials.RECORD_VERSION,
                           "candidateCommit": manifest["candidateCommit"], "slots": []}

            with patch.object(measure.source, "validate_manifest", return_value=manifest), \
                 patch.object(measure.trials, "run_trials", return_value=fake_record), \
                 patch.object(measure.subprocess, "run", return_value=type("Process", (), {
                     "returncode": 2, "stdout": "", "stderr": "synthetic verifier disagreement"})()):
                with self.assertRaisesRegex(RuntimeError, "evidence retained"):
                    measure.run_registered_capture(
                        manifest_path=manifest_path, review_path=review_path,
                        capture_authorization_path=capture_path, output_path=output_path,
                        authority_verifier=lambda *_args: True)

            self.assertTrue(run_path.is_dir())
            self.assertTrue((run_path / "result.json").is_file())
            self.assertTrue(grant_path.is_dir())
            self.assertTrue((grant_path / "grant.json").is_file())
            observer = json.loads(output_path.with_name(output_path.name + ".observer.json").read_text())
            self.assertIsNone(observer["freshVerification"]["status"])
            self.assertEqual(observer["freshVerification"]["processReturnCode"], 2)
            self.assertTrue(observer["finalArtifactCleanup"]["skipped"])
            self.assertIn("retain run/grant evidence", observer["finalArtifactCleanup"]["skipReason"])
            self.assertTrue(output_path.with_name(output_path.name + ".observer-tail.json").is_file())

    def test_verified_but_incomplete_capture_still_retains_treatment_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root, common_root = root / "source", root / "common"
            source_root.mkdir()
            common_root.mkdir()
            run_path, grant_path = root / "run", root / "grant"
            run_path.mkdir(mode=0o700)
            grant_path.mkdir(mode=0o700)
            (run_path / "retained.txt").write_text("review evidence\n")
            (grant_path / "retained.txt").write_text("review grant\n")
            manifest = {"candidateCommit": "b" * 40, "sourceRepository": str(source_root),
                        "sourceFingerprint": {"commonDirectory": str(common_root)},
                        "slots": [{"runPath": str(run_path), "grantPath": str(grant_path)}]}
            manifest_path, review_path, capture_path = (root / "manifest.json", root / "review.json",
                                                        root / "capture-auth.json")
            manifest_path.write_bytes(b"synthetic manifest")
            review_path.write_bytes(b"synthetic review")
            capture_path.write_bytes(b"synthetic capture")
            output_path = root / "capture.json"
            fake_record = {"recordVersion": trials.RECORD_VERSION,
                           "candidateCommit": manifest["candidateCommit"], "slots": [],
                           "status": "incomplete"}

            def verified_process(command, **_kwargs):
                verification_path = Path(command[command.index("--output") + 1])
                verification_path.write_text(_raw({"status": "verified"}).decode())
                return type("Process", (), {"returncode": 0, "stdout": "verified", "stderr": ""})()

            with patch.object(measure.source, "validate_manifest", return_value=manifest), \
                 patch.object(measure.trials, "run_trials", return_value=fake_record), \
                 patch.object(measure.subprocess, "run", side_effect=verified_process), \
                 patch.object(measure, "_git", return_value="git version synthetic"):
                captured = measure.run_registered_capture(
                    manifest_path=manifest_path, review_path=review_path,
                    capture_authorization_path=capture_path, output_path=output_path,
                    authority_verifier=lambda *_args: True)

            self.assertTrue(run_path.is_dir())
            self.assertTrue(grant_path.is_dir())
            self.assertEqual(captured["environmentObservation"]["git"]["version"], "git version synthetic")
            self.assertTrue(captured["environmentObservation"]["python"]["version"])
            self.assertTrue(captured["environmentObservation"]["operatingSystem"]["platform"])
            self.assertIsNone(captured["gitCommandCounterBoundary"]["candidateIdentityGitCommandCount"]["value"])
            self.assertIsNone(captured["gitCommandCounterBoundary"]["sourceIntegrityGitCommandCount"]["value"])
            observer = json.loads(output_path.with_name(output_path.name + ".observer.json").read_text())
            self.assertEqual(observer["freshVerification"]["status"], "verified")
            self.assertTrue(observer["finalArtifactCleanup"]["skipped"])
            self.assertIn("incomplete", observer["finalArtifactCleanup"]["skipReason"])

    def test_capture_output_inside_git_common_storage_is_refused_before_runner(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_root, common_root = root / "source", root / "common"
            source_root.mkdir()
            common_root.mkdir()
            manifest_path, review_path, capture_path = (root / "manifest.json", root / "review.json",
                                                        root / "capture-auth.json")
            manifest_path.write_bytes(b"synthetic manifest")
            review_path.write_bytes(b"synthetic review")
            capture_path.write_bytes(b"synthetic capture")
            manifest = {"candidateCommit": "c" * 40, "sourceRepository": str(source_root),
                        "sourceFingerprint": {"commonDirectory": str(common_root)}, "slots": []}
            output = common_root / "must-not-write.json"
            with patch.object(measure.source, "validate_manifest", return_value=manifest), \
                 patch.object(measure.trials, "run_trials") as runner:
                with self.assertRaisesRegex(ValueError, "candidate, source, or Git common"):
                    measure.run_registered_capture(
                        manifest_path=manifest_path, review_path=review_path,
                        capture_authorization_path=capture_path, output_path=output,
                        authority_verifier=lambda *_args: True)
                runner.assert_not_called()
            self.assertFalse(output.exists())
            self.assertEqual(list(common_root.iterdir()), [])
            with self.assertRaisesRegex(ValueError, "source, and Git common"):
                fresh_verify._fresh_output(common_root / "fresh-verifier.json", manifest)
            self.assertEqual(list(common_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
