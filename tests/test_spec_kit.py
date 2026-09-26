# SPDX-License-Identifier: AGPL-3.0-only
"""Structural invariants, not interactive agent or human approval tests."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts.constitution_replica import sync
from scripts.validate_spec_kit import (
    ROOT, authorities, check, digest, freeze, snapshot, validate_portable_record,
    validate_record,
)


class SpecKitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="braid-guards-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "repo"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            ".git", ".venv", ".venv-speckit", "__pycache__"))
        shutil.copytree(ROOT / ".git", self.root / ".git")
        self.record = self.root / "specs/001-certificate-verifier-pilot/assurance.json"
        self.portable = (self.root / "docs/releases/public-export.json").is_file()

    def write_record(self, data):
        self.record.write_text(json.dumps(data))

    def validate_test_record(self):
        if self.portable:
            validate_portable_record(self.root, self.record, bind_manifest=False)
        else:
            validate_record(self.root, self.record)

    def test_current_tree_and_constitution_baseline(self):
        check(self.root)
        self.assertEqual(digest(self.root / "CONSTITUTION.md"),
                         "ff7196976a1736a639947c2ab26e8da157fef23c89ba9881312f2a36459964eb")

    def test_replica_absence_divergence_and_idempotence(self):
        replica = self.root / ".specify/memory/constitution.md"
        original = (self.root / "CONSTITUTION.md").read_bytes()
        replica.unlink()
        with self.assertRaises(ValueError):
            sync(self.root)
        self.assertFalse(replica.exists())
        sync(self.root, True)
        self.assertEqual(replica.read_bytes(), original)
        sync(self.root, True)
        self.assertEqual(replica.read_bytes(), original)
        replica.write_bytes(original + b"\nchanged")
        with self.assertRaises(ValueError):
            sync(self.root)
        self.assertEqual(replica.read_bytes(), original + b"\nchanged")

    def test_authority_change_does_not_approve_new_text(self):
        data = json.loads(self.record.read_text())
        authority = self.root / "CONSTITUTION.md"
        authority.write_bytes(authority.read_bytes() + b"\nProposed change\n")
        sync(self.root, True)
        self.validate_test_record()
        self.assertEqual(json.loads(self.record.read_text())["human_review"], "approved")
        snapshot(self.root, "specs/001-certificate-verifier-pilot")
        refreshed = json.loads(self.record.read_text())
        self.assertEqual(refreshed["human_review"], "pending")
        self.assertEqual(refreshed["authority_snapshot"]["mode"], "current")

    def test_new_authority_preserves_history_but_invalidates_current_work(self):
        (self.root / "docs/adr/9999-proposed.md").write_text("New authority candidate")
        self.validate_test_record()
        snapshot(self.root, "specs/001-certificate-verifier-pilot")
        (self.root / "docs/adr/9998-later.md").write_text("Later authority candidate")
        with self.assertRaisesRegex(ValueError, "current authority snapshot"):
            self.validate_test_record()

    def test_historical_snapshot_must_match_available_commit(self):
        if self.portable:
            self.skipTest("private historical commit objects are intentionally unavailable")
        data = json.loads(self.record.read_text())
        data["authority_snapshot"]["hashes"]["CONSTITUTION.md"] = "0" * 64
        self.write_record(data)
        with self.assertRaisesRegex(ValueError, "does not match its commit"):
            self.validate_test_record()
        data = json.loads((ROOT / "specs/001-certificate-verifier-pilot/assurance.json").read_text())
        data["authority_snapshot"]["commit"] = "f" * 40
        self.write_record(data)
        with self.assertRaisesRegex(ValueError, "Git history required"):
            validate_record(self.root, self.record)

    def test_approval_requires_frozen_snapshot_and_matching_review(self):
        data = json.loads(self.record.read_text())
        data["authority_snapshot"] = {
            "mode": "current", "commit": None,
            "hashes": authorities(self.root),
        }
        data["human_review"] = "approved"
        self.write_record(data)
        with self.assertRaisesRegex(ValueError, "Approval requires"):
            self.validate_test_record()

    def test_freeze_rejects_dirty_candidate(self):
        readme = self.root / "README.md"
        readme.write_bytes(readme.read_bytes() + b"\nUncommitted test change\n")
        with self.assertRaisesRegex(ValueError, "clean candidate"):
            freeze(self.root, "specs/005-git-worktree-adapter")

    def test_broken_reference_and_invalid_article(self):
        original = json.loads(self.record.read_text())
        for key, value in (("references", ["missing.md"]), ("articles", [26]),
                           ("references", ["../outside.md"])):
            with self.subTest(key=key, value=value):
                self.write_record({**original, key: value})
                with self.assertRaises(ValueError):
                    self.validate_test_record()

    def test_missing_evidence_is_not_a_validated_result(self):
        data = json.loads(self.record.read_text())
        data["stage"] = "validated"
        data["requirements"][0]["scenarios"][0]["obtained_evidence"] = []
        self.write_record(data)
        with self.assertRaisesRegex(ValueError, "evidence absent"):
            self.validate_test_record()
        data["stage"] = "draft"
        self.write_record(data)
        self.validate_test_record()

    def test_historical_evidence_stays_bound_while_current_evidence_detects_drift(self):
        target = self.root / "research/lab/certificates.py"
        original = target.read_bytes()
        target.write_bytes(original + b"\n# changed\n")
        self.validate_test_record()
        target.write_bytes(original)
        snapshot(self.root, "specs/001-certificate-verifier-pilot")
        target.write_bytes(original + b"\n# changed again\n")
        with self.assertRaisesRegex(ValueError, "Stale evidence input"):
            self.validate_test_record()

    def test_historical_files_can_leave_worktree_but_current_files_cannot(self):
        evidence = self.root / "specs/001-certificate-verifier-pilot/evidence.json"
        reference = self.root / "docs/adr/0005-evidence-contracts-and-bounded-laboratory.md"
        evidence.unlink()
        reference.unlink()
        self.validate_test_record()
        data = json.loads(self.record.read_text())
        data["evidence_snapshot"] = {"mode": "current", "commit": None}
        data["authority_snapshot"] = {
            "mode": "current", "commit": None,
            "hashes": authorities(self.root),
        }
        data["human_review"] = "pending"
        self.write_record(data)
        with self.assertRaises(ValueError):
            self.validate_test_record()

    def test_post_root_review_uses_bound_public_snapshot(self):
        if not self.portable:
            self.skipTest("post-root public supplement is not present")
        record = self.root / "specs/012-m2-git-replay-planner/assurance.json"
        review = self.root / "specs/012-m2-git-replay-planner/founder-review.json"
        review.write_text("not the reviewed bytes")
        validate_portable_record(self.root, record)

    def test_reviewed_private_candidate_uses_annotated_tag_without_exporting_dependency(self):
        if not self.portable:
            self.skipTest("public export manifest is not present")
        record = self.root / "specs/016-m2-partial-order-reduction/assurance.json"
        private_reference = "specs/015-m2-counterexample-reducer/spec.md"
        manifest = json.loads(
            (self.root / "docs/releases/public-export.json").read_text()
        )
        exported = {item["path"] for item in manifest["files"]}
        self.assertNotIn(private_reference, exported)
        validate_portable_record(self.root, record)

    def test_lightweight_tag_cannot_authorize_a_private_historical_record(self):
        if not self.portable:
            self.skipTest("public export manifest is not present")
        record = self.root / "specs/016-m2-partial-order-reduction/assurance.json"
        data = json.loads(record.read_text())
        commit = data["authority_snapshot"]["commit"]
        tag_ref = f"refs/tags/spec-016-reviewed-{commit[:7]}"
        subprocess.run(
            ["git", "-C", str(self.root), "update-ref", "-d", tag_ref],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.root), "update-ref", tag_ref, commit],
            check=True, capture_output=True,
        )
        with self.assertRaisesRegex(
                ValueError, "export manifest does not bind required file"):
            validate_portable_record(self.root, record)

    def test_each_integration_drift_and_override_drift(self):
        for relative in (".agents/skills/speckit-constitution/SKILL.md",
                         ".claude/skills/speckit-plan/SKILL.md",
                         ".specify/templates/overrides/guardrails.md"):
            target = self.root / relative
            original = target.read_bytes()
            target.write_bytes(original + b"\nchange\n")
            with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, "drift"):
                check(self.root)
            target.write_bytes(original)

    def test_incompatible_config_and_constitution_sync(self):
        state_path = self.root / ".specify/integration.json"
        original = state_path.read_bytes()
        state = json.loads(original)
        state["integration_settings"]["claude"]["script"] = "sh"
        state_path.write_text(json.dumps(state))
        with self.assertRaises(ValueError):
            check(self.root)
        state_path.write_bytes(original)
        preset = self.root / ".specify/presets/constitution-sync/preset.yml"
        preset.parent.mkdir(parents=True)
        preset.write_text("id: constitution-sync\n")
        with self.assertRaisesRegex(ValueError, "constitution-sync"):
            check(self.root)

    def test_missing_assurance_is_rejected(self):
        self.record.unlink()
        with self.assertRaises(ValueError):
            check(self.root)

    def test_missing_integration_and_legacy_shadow_are_rejected(self):
        skill = self.root / ".claude/skills/speckit-constitution/SKILL.md"
        original = skill.read_bytes()
        skill.unlink()
        with self.assertRaises(ValueError):
            check(self.root)
        skill.write_bytes(original)
        shadow = self.root / ".claude/commands/speckit.constitution.md"
        shadow.parent.mkdir()
        shadow.write_text("An unreviewed legacy command")
        with self.assertRaisesRegex(ValueError, "shadow"):
            check(self.root)

    def test_nonexistent_test_reference(self):
        data = json.loads(self.record.read_text())
        data["requirements"][0]["scenarios"][0]["test_name"] = "NoSuchTest.test_missing"
        self.write_record(data)
        with self.assertRaisesRegex(ValueError, "Test reference"):
            self.validate_test_record()


if __name__ == "__main__":
    unittest.main()
