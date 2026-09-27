# SPDX-License-Identifier: AGPL-3.0-only
"""Negative controls for candidate-bound M2 closure provenance."""

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import validate_m2_closure as closure
from scripts.run_m2_clean_room import _environment, _redact, _remote_ref, _run


class M2ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="m2-closure-test-")
        self.root = Path(self.temporary.name)
        paths = {
            closure.RETEST, closure.RETEST_INPUTS, closure.RETEST_DECISION,
            closure.RETEST_REVIEW,
            "docs/experiments/M2_REAL_CORPUS_RETEST_RESULT.md",
            "docs/experiments/evidence/m2-real-corpus-performance-attempt-1-batch.json",
            "docs/experiments/evidence/m2-real-corpus-performance-attempt-1-result.json",
            "specs/016-m2-partial-order-reduction/founder-review.json",
            "specs/013-m2-real-workload/m2-corpus-manifest.json",
            "specs/013-m2-real-workload/m2-corpus-selection.json",
            "agent_braid/git_integration_prototype.py", "agent_braid/git_process.py",
            "scripts/benchmark_m2_parallel_preparation.py",
            "scripts/docker/t013/Dockerfile", "scripts/docker/t013/apt-packages.lock",
            "scripts/docker/t013/constraints-t013.txt", "requirements-dev.txt",
            "requirements-speckit.txt",
        }
        for relative in paths:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(closure.ROOT / relative, target)
        radar = self.root / closure.RADAR
        radar.parent.mkdir(parents=True)
        radar.write_text(json.dumps({"review": {
            "kind": "milestone", "milestones": ["M2"],
            "reviewer": "Test Founder",
            "decision": "approved", "decisionRecord": closure.RADAR_REVIEW,
        }}))
        decision = self.root / closure.RADAR_REVIEW
        decision.parent.mkdir(parents=True)
        decision.write_text("# Bounded M2 radar decision\n\n"
                            "**Founder decision:** approved\n"
                            "**Founder reviewer:** Test Founder\n")

    def tearDown(self):
        self.temporary.cleanup()

    def test_source_evidence_requires_exact_registered_inputs_and_radar(self):
        result = closure.validate_source_evidence(self.root)
        self.assertEqual(result["retest"], "two-registered-30-pair-batches")
        self.assertFalse(result["executionAuthorization"])
        radar = json.loads((self.root / closure.RADAR).read_text())
        radar["review"]["decision"] = "pending"
        (self.root / closure.RADAR).write_text(json.dumps(radar))
        with self.assertRaisesRegex(ValueError, "radar"):
            closure.validate_source_evidence(self.root)

    def test_source_evidence_rejects_conflicting_radar_review(self):
        (self.root / closure.RADAR_REVIEW).write_text(
            "**Founder decision:** pending\n**Founder reviewer:** Test Founder\n")
        with self.assertRaisesRegex(ValueError, "radar decision record contradicts"):
            closure.validate_source_evidence(self.root)

    def test_rejects_changed_retest_manifest_or_incomplete_batch(self):
        manifest = self.root / "specs/013-m2-real-workload/m2-corpus-manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "manifest"):
            closure.validate_source_evidence(self.root)
        shutil.copy2(closure.ROOT / "specs/013-m2-real-workload/m2-corpus-manifest.json", manifest)
        record = json.loads((self.root / closure.RETEST).read_text())
        record["batches"][0]["rawPairs"].pop()
        (self.root / closure.RETEST).write_text(json.dumps(record))
        reviewed = json.loads((self.root / closure.RETEST_REVIEW).read_text())
        checksum = next(item["sha256AtReviewedCommit"]
                        for item in reviewed["reviewedArtifacts"]
                        if item["path"] == closure.RETEST)
        real_digest = closure._digest
        with patch.object(closure, "_digest", side_effect=lambda root, path: (
                checksum if path == closure.RETEST else real_digest(root, path))):
            with self.assertRaisesRegex(ValueError, "batch"):
                closure.validate_source_evidence(self.root)

    def test_rejects_reconstructed_retest_evidence_even_with_same_metrics(self):
        path = self.root / closure.RETEST
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "founder-reviewed bytes"):
            closure.validate_source_evidence(self.root)

    def test_clean_room_inventory_covers_four_exit_criteria_and_negative_controls(self):
        observed = {name for name, _ in closure.REQUIRED_OBSERVATIONS}
        self.assertEqual(set(closure.EXIT_CRITERIA), {
            "immutableFixtureReplay", "boundedPreparationGain",
            "fixedObservationContract", "safeEffectDefaults",
        })
        self.assertIn("radar", observed)
        self.assertIn("scientific-controls", observed)
        self.assertIn("reachable-objects", observed)
        self.assertIn("tests/test_git_partial_order.py", closure.INPUTS)
        self.assertIn(closure.RADAR, closure.INPUTS)
        self.assertIn(closure.ADVERSARIAL_REVIEW, closure.INPUTS)

    def test_clean_room_environment_drops_host_overrides(self):
        env = _environment({
            "PATH": "/usr/bin", "HTTPS_PROXY": "https://user:secret@proxy.invalid",
            "PIP_INDEX_URL": "https://user:secret@index.invalid/simple",
            "PYTHONPATH": "/host/code", "PYTHONHOME": "/host/python",
            "GIT_DIR": "/host/.git", "GIT_WORK_TREE": "/host/work",
        })
        self.assertEqual(env["PATH"], "/usr/bin")
        for key in ("PYTHONPATH", "PYTHONHOME", "GIT_DIR", "GIT_WORK_TREE",
                    "HTTPS_PROXY", "PIP_INDEX_URL"):
            self.assertNotIn(key, env)
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], os.devnull)

    def test_clean_room_record_redacts_temporary_paths(self):
        raw = f"command {self.root}/venv/bin/python; output {self.root}/tmp/build"
        redacted = _redact(raw, self.root)
        self.assertNotIn(str(self.root), redacted)
        self.assertIn("${CLEAN_ROOM}/venv/bin/python", redacted)
        self.assertEqual(closure.observation_id([
            "${CLEAN_ROOM}/venv/bin/python", "scripts/validate_m2_closure.py", "inputs"
        ]), "m2-inputs")
        command = [str(self.root / "venv/bin/python"), "scripts/validate_m2_closure.py", "inputs"]
        with patch("scripts.run_m2_clean_room.subprocess.run", return_value=Mock(
                returncode=0,
                stdout=f"used {self.root}/tmp/build",
                stderr=f"warning {self.root}/repository")):
            observation = _run(command, self.root, {}, self.root)
        self.assertEqual(observation["command"][0], "${CLEAN_ROOM}/venv/bin/python")
        self.assertEqual(observation["stdout"], "used ${CLEAN_ROOM}/tmp/build")
        self.assertEqual(observation["stderr"], "warning ${CLEAN_ROOM}/repository")

    def test_candidate_gate_rejects_implementation_after_freeze(self):
        with patch.object(closure, "validate_closure_anchor",
                          side_effect=ValueError("protected closure record changed")):
            with self.assertRaisesRegex(ValueError, "protected closure"):
                closure.validate_candidate_unchanged(self.root, "a" * 40)
        with patch.object(closure, "validate_closure_anchor", return_value={
                "changedPaths": ["agent_braid/git_replay.py"]}):
            with self.assertRaisesRegex(ValueError, "post-freeze implementation"):
                closure.validate_candidate_unchanged(self.root, "a" * 40)

    def test_observation_inventory_rejects_prefix_and_extra_args(self):
        python = "/tmp/cleanroom/venv/bin/python"
        self.assertEqual(closure.observation_id([
            python, "scripts/validate_m2_closure.py", "inputs"]), "m2-inputs")
        self.assertIsNone(closure.observation_id([
            "arbitrary", python, "scripts/validate_m2_closure.py", "inputs"]))
        self.assertIsNone(closure.observation_id([
            python, "scripts/validate_m2_closure.py", "inputs", "--skip-check"]))

    def test_published_ref_resolution_requires_exact_branch_identity(self):
        published = "refs/heads/work/m2-candidate"
        with patch("scripts.run_m2_clean_room._git",
                   return_value="a" * 40 + "\t" + published):
            self.assertEqual(_remote_ref(self.root, published, {}), "a" * 40)
        with patch("scripts.run_m2_clean_room._git",
                   return_value="a" * 40 + "\trefs/heads/other"):
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                _remote_ref(self.root, published, {})
        with patch("scripts.run_m2_clean_room._git", return_value=""):
            with self.assertRaisesRegex(ValueError, "unavailable"):
                _remote_ref(self.root, published, {})
        with patch("scripts.run_m2_clean_room._git",
                   return_value="a" * 40 + "\t" + published + "\n" +
                                "b" * 40 + "\t" + published):
            with self.assertRaisesRegex(ValueError, "ambiguous"):
                _remote_ref(self.root, published, {})

    def test_closure_does_not_accept_pending_founder_decisions(self):
        review = {
            "recordVersion": "0.1.0", "feature": "M2", "reviewedCommit": "a" * 40,
            "reviewer": {"name": "Founder", "role": "founder"},
            "conflictsOfInterest": "founder and maintainer",
            "scientificReview": {"decision": "approved", "date": "2026-09-27", "rationale": "bounded"},
            "milestoneClosure": {"decision": "pending", "date": "", "rationale": ""},
            "independentValidation": "pending", "evidence": [], "limits": ["bounded"],
        }
        path = self.root / "specs/017-m2-closure/founder-review.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, "milestoneClosure"):
            closure.validate_founder_review(self.root, "a" * 40)


if __name__ == "__main__":
    unittest.main()
