# SPDX-License-Identifier: AGPL-3.0-only

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from research.lab.model import loads
from scripts import validate_m0_closure as validator


ROOT = Path(__file__).resolve().parents[1]


class M0ClosureTests(unittest.TestCase):
    def test_exit_matrix_traces_scientific_boundaries(self):
        text = (ROOT / "docs/releases/M0_EXIT_MATRIX.md").read_text()
        for marker in ("T1 independence", "T2 schedule equivalence", "CE1", "CE2",
                       "CE3", "CE4", "CE5", "S3", "Certificate verifier"):
            self.assertIn(marker, text)
        self.assertIn("General confluence", text)
        self.assertIn("Yang–Baxter", text)
        self.assertIn("adapter correctness remain open", text)

    def test_portable_workloads_cover_required_effects(self):
        schema = loads((ROOT / "schemas/0.2.0-draft/agent-interaction-metadata.schema.json").read_text())
        schema_validator = Draft202012Validator(schema)
        paths = [
            ROOT / "examples/workloads/code-agent-repository.json",
            ROOT / "examples/workloads/ci-deployment-controller.json",
        ]
        operations = []
        for path in paths:
            workload = loads(path.read_text())
            self.assertIsInstance(workload, list)
            self.assertGreaterEqual(len(workload), 2)
            for operation in workload:
                schema_validator.validate(operation)
                operations.append(operation)
        effects = {(effect["kind"], effect["resource"])
                   for operation in operations
                   for effect in operation["effects"]["declared"]}
        self.assertTrue(any(kind == "transform" and resource.endswith("#text")
                            for kind, resource in effects))
        self.assertTrue(any(kind == "call" and resource.startswith("tool://repository/")
                            for kind, resource in effects))
        self.assertTrue(any(kind == "write" and resource.startswith("api://")
                            for kind, resource in effects))
        self.assertTrue(any(kind == "deploy" and resource.startswith("deployment://")
                            for kind, resource in effects))

    def test_portable_workloads_preserve_identity_and_never_authorize(self):
        identifiers = set()
        for path in sorted((ROOT / "examples/workloads").glob("*.json")):
            for operation in loads(path.read_text()):
                self.assertNotIn(operation["instanceId"], identifiers)
                identifiers.add(operation["instanceId"])
                self.assertTrue(operation["attemptId"])
                self.assertRegex(operation["definition"]["digest"], r"^sha256:[0-9a-f]{64}$")
                self.assertRegex(operation["inputDigest"], r"^sha256:[0-9a-f]{64}$")
                self.assertIsInstance(operation["dependencies"], list)
                self.assertIsInstance(operation["readVersions"], dict)
                self.assertIn(operation["effects"]["coverage"]["status"], {"partial", "unknown"})
                self.assertNotIn("executionAuthorization", operation)
                for item in operation["evidence"]:
                    self.assertEqual(item["assuranceClass"], 0)
                    self.assertEqual(item["executionContract"], "non-executing-portable-example-m0")

    def _pilot_root(self):
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        pilot = root / validator.PILOT
        pilot.mkdir(parents=True)
        (root / "input.txt").write_text("frozen")
        evidence = {
            "python": "3.12.4",
            "candidate_commit": "a" * 40,
            "repository_dirty": False,
            "inputs": {"input.txt": validator.digest(root / "input.txt")},
            "interactive_codex": "not executed",
            "interactive_claude": "not executed",
        }
        evidence_path = pilot / "evidence.json"
        evidence_path.write_text(json.dumps(evidence))
        assurance = {
            "human_review": "pending",
            "requirements": [{"scenarios": [{"obtained_evidence": [{
                "sha256": validator.digest(evidence_path)
            }]}]}],
        }
        (pilot / "assurance.json").write_text(json.dumps(assurance))
        return temporary, root, evidence, assurance

    def _rewrite(self, root, evidence, assurance):
        evidence_path = root / validator.PILOT / "evidence.json"
        evidence_path.write_text(json.dumps(evidence))
        assurance["requirements"][0]["scenarios"][0]["obtained_evidence"][0]["sha256"] = validator.digest(evidence_path)
        (root / validator.PILOT / "assurance.json").write_text(json.dumps(assurance))

    def test_rejects_incompatible_python_and_unknown_commit(self):
        temporary, root, evidence, assurance = self._pilot_root()
        with temporary:
            evidence["python"] = "3.11.9"
            self._rewrite(root, evidence, assurance)
            with self.assertRaisesRegex(ValueError, "Python 3.12"):
                validator.validate_pilot(root)
            evidence["python"] = "3.12.4"
            evidence["candidate_commit"] = "not-a-commit"
            self._rewrite(root, evidence, assurance)
            with self.assertRaisesRegex(ValueError, "exact candidate commit"):
                validator.validate_pilot(root)

    def test_rejects_stale_input_and_evidence_digest(self):
        temporary, root, evidence, assurance = self._pilot_root()
        with temporary:
            (root / "input.txt").write_text("changed")
            with self.assertRaisesRegex(ValueError, "pilot input changed"):
                validator.validate_pilot(root)
            (root / "input.txt").write_text("frozen")
            assurance["requirements"][0]["scenarios"][0]["obtained_evidence"][0]["sha256"] = "0" * 64
            (root / validator.PILOT / "assurance.json").write_text(json.dumps(assurance))
            with self.assertRaisesRegex(ValueError, "does not bind"):
                validator.validate_pilot(root)

    def test_rejects_missing_agent_pair_and_commit_mismatch(self):
        temporary, root, evidence, assurance = self._pilot_root()
        with temporary:
            report_path = root / validator.REPORTS["codex"]
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "one review set"):
                validator.check(root)
            report = {
                "reportVersion": "0.1.0", "agent": "codex", "agentVersion": "test",
                "executedAt": "2026-09-17T00:00:00Z", "reviewedCommit": "b" * 40,
                "prompt": "bounded review", "unsupportedProof": "unverified",
                "automatedHumanSeparation": True, "scientificLimitsRetained": True,
                "contradictions": [], "pendingChecks": ["founder review"],
                "decision": "compatible",
            }
            with self.assertRaisesRegex(ValueError, "different candidate"):
                validator.validate_agent_report(report, "codex", "a" * 40)

    def test_rejects_agent_prompt_or_pending_check_divergence(self):
        temporary, root, evidence, assurance = self._pilot_root()
        with temporary:
            base = {
                "reportVersion": "0.1.0", "agent": "codex", "agentVersion": "test",
                "executedAt": "2026-09-17T00:00:00Z", "reviewedCommit": "a" * 40,
                "prompt": "same bounded prompt", "unsupportedProof": "unverified",
                "automatedHumanSeparation": True, "scientificLimitsRetained": True,
                "contradictions": [], "pendingChecks": ["T006"], "decision": "compatible",
            }
            for agent in ("codex", "claude"):
                report = deepcopy(base)
                report["agent"] = agent
                path = root / validator.REPORTS[agent]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps(report))
            validator.check(root)
            claude_path = root / validator.REPORTS["claude"]
            claude = json.loads(claude_path.read_text())
            claude["prompt"] = "different prompt"
            claude_path.write_text(json.dumps(claude))
            with self.assertRaisesRegex(ValueError, "same prompt"):
                validator.check(root)
            claude["prompt"] = base["prompt"]
            claude["pendingChecks"] = ["different"]
            claude_path.write_text(json.dumps(claude))
            with self.assertRaisesRegex(ValueError, "pendingChecks"):
                validator.check(root)

    def test_rejects_incomplete_review_and_closure_without_decision(self):
        temporary, root, evidence, assurance = self._pilot_root()
        with temporary:
            record = {
                "recordVersion": "0.1.0", "feature": "M0",
                "reviewedCommit": "a" * 40,
                "reviewer": {"name": "Founder", "role": "founder"},
                "conflictsOfInterest": "Founder and project author.",
                "scientificReview": {"decision": "pending", "date": "2026-09-17", "rationale": "pending"},
                "milestoneClosure": {"decision": "approved", "date": "2026-09-17", "rationale": "bounded"},
                "evidence": [{"path": "input.txt", "sha256": validator.digest(root / "input.txt")}],
                "limits": ["No production claim"],
            }
            with self.assertRaisesRegex(ValueError, "scientificReview"):
                validator.validate_review_record(record, root, "a" * 40)
            with self.assertRaisesRegex(ValueError, "both interactive agent reports"):
                validator.check(root, closure=True)


if __name__ == "__main__":
    unittest.main()
