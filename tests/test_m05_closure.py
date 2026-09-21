# SPDX-License-Identifier: AGPL-3.0-only

import json
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from scripts.validate_m05_closure import (
    EVIDENCE,
    REPRODUCTION,
    REPRODUCTION_VERSION,
    REQUIRED_OBSERVATIONS,
    REPORT_ASSET,
    REPORT_PDF,
    REPORT_PPTX,
    validate_candidate,
    validate_candidate_unchanged,
    validate_closure,
    validate_distribution_boundary,
    validate_founder_review,
    validate_report_assets,
    validate_reproduction,
)
from scripts.run_m05_clean_room import _clean_environment


class M05ClosureTests(unittest.TestCase):
    def test_candidate_accepts_pending_but_closure_requires_approved_radar(self):
        with patch("scripts.validate_m05_closure.validate_candidate", return_value=[]), \
             patch("scripts.validate_m05_closure._approved_radar", return_value=False), \
             patch("scripts.validate_m05_closure.validate_reproduction"):
            self.assertTrue(any("not approved" in item for item in validate_closure()))

    def test_report_and_history_boundary_are_required(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "reports/assets").mkdir(parents=True)
            (root / "docs/releases").mkdir(parents=True)
            (root / REPORT_ASSET).write_bytes(b"png")
            (root / REPORT_PDF).write_bytes(
                b"%PDF-1.7\n" + b"/Type /Page\n" * 6
            )
            with zipfile.ZipFile(root / REPORT_PPTX, "w") as archive:
                for index in range(1, 7):
                    slide = "<slide><a:tbl></a:tbl></slide>" if index == 6 else "<slide/>"
                    archive.writestr(f"ppt/slides/slide{index}.xml", slide)
                    archive.writestr(
                        f"ppt/notesSlides/notesSlide{index}.xml", "<notes>Source</notes>",
                    )
                archive.writestr("ppt/slides/charts/chart1.xml", "<chart/>")
                archive.writestr("ppt/embeddings/chart-data.xlsx", b"workbook")
                archive.writestr(
                    "docProps/core.xml",
                    "Juan Antonio Yáñez García Agent Braid Open Tooling Outlook 2026",
                )
            (root / "docs/releases/RESEARCH_PREVIEW_PROPOSAL.md").write_text(
                "clean export historical Git objects does not rewrite history "
                "explicit authorization independent_validation: pending"
            )
            readiness = {
                "recordVersion": "0.1.0", "status": "prepared",
                "currentTreeRedistributable": True,
                "historicalReportStatus": "unresolved",
                "recommendedPublicationMode": "clean-export",
                "repositoryVisibilityChangeAuthorized": False,
                "historyRewriteAuthorized": False,
                "limits": ["bounded"],
            }
            (root / "docs/releases/research-preview-readiness.json").write_text(
                json.dumps(readiness)
            )
            self.assertEqual(validate_report_assets(root), [])
            self.assertEqual(validate_distribution_boundary(root), [])
            with zipfile.ZipFile(root / REPORT_PPTX, "w") as archive:
                archive.writestr("ppt/slides/slide1.xml", "<slide/>")
            self.assertTrue(validate_report_assets(root))
            readiness["historicalReportStatus"] = "cleared"
            (root / "docs/releases/research-preview-readiness.json").write_text(
                json.dumps(readiness)
            )
            self.assertTrue(validate_distribution_boundary(root))

    def _reproduction(self, content=b"candidate input"):
        checksum = hashlib.sha256(content).hexdigest()
        commit = "a" * 40
        tree = "b" * 40
        observations = []
        for identifier, suffix in REQUIRED_OBSERVATIONS:
            command = f"python {suffix}"
            if identifier == "whitespace":
                command = f"git diff-tree --check --root --no-commit-id -r {commit}"
            observations.append({
                "command": command, "exitCode": 0, "stdout": "", "stderr": "",
            })
        inputs = {
            REPORT_PPTX: checksum,
            REPORT_PDF: checksum,
            REPORT_ASSET: checksum,
        }
        return {
            "recordVersion": REPRODUCTION_VERSION,
            "capturedAt": "2026-09-18T12:00:00+00:00",
            "reviewedCommit": commit,
            "tree": tree,
            "platform": "test-platform",
            "python": "3.12.14",
            "git": "git version 2.50.1",
            "cleanRoom": {
                "freshClone": True, "freshEnvironment": True,
                "pipCacheDisabled": True, "initialStatus": "", "finalStatus": "",
            },
            "operator": {
                "automation": "Codex", "authorization": "Founder approval",
                "supervisor": "Founder", "independent": False,
            },
            "inputs": inputs,
            "observations": observations,
            "reportArtifacts": dict(inputs),
            "independentValidation": "pending",
            "limits": ["Internal evidence only."],
        }

    def test_reproduction_rejects_incompatible_or_stale_evidence(self):
        content = b"candidate input"
        record = self._reproduction(content)

        def git_result(command, **_kwargs):
            if "rev-parse" in command:
                return subprocess.CompletedProcess(command, 0, stdout=("b" * 40 + "\n").encode())
            return subprocess.CompletedProcess(command, 0, stdout=content)

        with tempfile.TemporaryDirectory() as temporary, \
             patch("scripts.validate_m05_closure.INPUTS", (
                 REPORT_PPTX, REPORT_PDF, REPORT_ASSET,
             )), patch("scripts.validate_m05_closure.load", return_value=record), \
             patch("scripts.validate_m05_closure.subprocess.run", side_effect=git_result):
            root = Path(temporary)
            self.assertEqual(validate_reproduction(root), record)
            record["capturedAt"] = "2026-09-18T12:00:00"
            with self.assertRaisesRegex(ValueError, "include a timezone"):
                validate_reproduction(root)
            record["capturedAt"] = "2026-09-18T12:00:00+00:00"
            record["git"] = "Git 2"
            with self.assertRaisesRegex(ValueError, "Git version"):
                validate_reproduction(root)
            record["git"] = "git version 2.50.1"
            record["python"] = "3.9.6"
            with self.assertRaisesRegex(ValueError, "Python 3.12"):
                validate_reproduction(root)
            record["python"] = "3.12.14"
            record["inputs"][REPORT_PDF] = "0" * 64
            with self.assertRaisesRegex(ValueError, "input mismatch"):
                validate_reproduction(root)
            record["inputs"][REPORT_PDF] = hashlib.sha256(content).hexdigest()
            record["observations"].pop()
            with self.assertRaisesRegex(ValueError, "incomplete or out of order"):
                validate_reproduction(root)

    def test_clean_room_environment_removes_python_and_git_overrides(self):
        environment = _clean_environment({
            "PATH": "/bin", "PYTHONPATH": "/unsafe", "GIT_DIR": "/unsafe",
            "GIT_CONFIG_GLOBAL": "/unsafe", "PIP_CACHE_DIR": "/unsafe",
        })
        self.assertEqual(environment["PATH"], "/bin")
        self.assertNotIn("PYTHONPATH", environment)
        self.assertNotIn("GIT_DIR", environment)
        self.assertEqual(environment["GIT_CONFIG_GLOBAL"], "/dev/null")
        self.assertEqual(environment["PIP_NO_CACHE_DIR"], "1")

    def test_post_freeze_changes_are_limited_to_decision_records(self):
        with patch(
            "scripts.validate_m05_closure.validate_closure_anchor",
            side_effect=ValueError("protected closure record changed"),
        ):
            failures = validate_candidate_unchanged(Path.cwd(), "a" * 40)
        self.assertTrue(any("protected closure record changed" in item for item in failures))

        with patch(
            "scripts.validate_m05_closure.validate_closure_anchor",
            return_value={"candidateCommit": "a" * 40},
        ):
            self.assertEqual(validate_candidate_unchanged(Path.cwd(), "a" * 40), [])

    def test_closure_requires_three_decisions_without_visibility_authorization(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            evidence_items = []
            for relative in (EVIDENCE, REPRODUCTION):
                evidence = root / relative
                evidence.parent.mkdir(parents=True, exist_ok=True)
                evidence.write_text("{}")
                evidence_items.append({
                    "path": relative, "sha256": hashlib.sha256(b"{}").hexdigest(),
                })
            review = {
                "recordVersion": "0.1.0", "feature": "M0.5", "reviewedCommit": "a" * 40,
                "reviewer": {"name": "Founder", "role": "founder"},
                "conflictsOfInterest": "Founder-led internal review.",
                "boundedReview": {"decision": "approved", "date": "2026-09-18", "rationale": "bounded"},
                "milestoneClosure": {"decision": "approved", "date": "2026-09-18", "rationale": "bounded"},
                "researchPreviewProposal": {"decision": "approved", "date": "2026-09-18", "rationale": "proposal only"},
                "independentValidation": "pending",
                "repositoryVisibilityChangeAuthorized": False,
                "evidence": evidence_items,
                "limits": ["bounded"],
            }
            with patch("scripts.validate_m05_closure.load", return_value=review):
                self.assertEqual(validate_founder_review(root, "a" * 40), [])
                review["researchPreviewProposal"]["decision"] = "pending"
                self.assertTrue(validate_founder_review(root, "a" * 40))
                review["researchPreviewProposal"]["decision"] = "approved"
                review["repositoryVisibilityChangeAuthorized"] = True
                self.assertTrue(validate_founder_review(root, "a" * 40))


if __name__ == "__main__":
    unittest.main()
