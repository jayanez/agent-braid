# SPDX-License-Identifier: AGPL-3.0-only
"""Focused checks for the portable product skill resource inventory."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_braid import tooling_assets


REPOSITORY = Path(__file__).resolve().parents[1]
SOURCE_SKILLS = REPOSITORY / "integrations/agent-braid/skills"


class ToolingAssetTests(unittest.TestCase):
    def test_source_checkout_inventory_is_ordered_hashed_and_bounded(self) -> None:
        bundle = tooling_assets.load_skill_bundle(source_checkout=True)

        self.assertEqual(tooling_assets.SKILL_BUNDLE_VERSION, bundle.version)
        self.assertEqual(tooling_assets.SKILL_NAMES, tuple(skill.name for skill in bundle.skills))
        self.assertEqual(5, len(bundle.skills))
        self.assertEqual(64, len(bundle.sha256))
        self.assertEqual(bundle.sha256, tooling_assets.load_skill_bundle(source_checkout=True).sha256)
        inventory = bundle.inventory()
        self.assertEqual(bundle.version, inventory["bundleVersion"])
        self.assertEqual(bundle.sha256, inventory["bundleSha256"])
        self.assertNotIn("content", inventory["skills"][0])

        aggregate = hashlib.sha256()
        aggregate.update(b"agent-braid-skill-bundle\0")
        aggregate.update(bundle.version.encode("ascii"))
        aggregate.update(b"\0")
        for skill in bundle.skills:
            source = SOURCE_SKILLS / skill.name / "SKILL.md"
            raw = source.read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), skill.sha256)
            self.assertEqual(len(raw), skill.size_bytes)
            self.assertEqual("CC-BY-SA-4.0", skill.license)
            aggregate.update(skill.name.encode("utf-8"))
            aggregate.update(b"\0")
            aggregate.update(bytes.fromhex(skill.sha256))
        self.assertEqual(aggregate.hexdigest(), bundle.sha256)

    def test_default_loader_uses_installed_package_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package_root = Path(temporary) / "agent_braid"
            resources_root = package_root / "tooling_assets" / "skills"
            resources_root.parent.mkdir(parents=True)
            shutil.copytree(SOURCE_SKILLS, resources_root)
            with patch.object(tooling_assets.resources, "files", return_value=package_root):
                bundle = tooling_assets.load_skill_bundle()
        self.assertEqual(tooling_assets.SKILL_NAMES, tuple(skill.name for skill in bundle.skills))

    def test_default_loader_does_not_fall_back_to_source_checkout(self) -> None:
        with patch.object(
            tooling_assets.resources,
            "files",
            side_effect=ModuleNotFoundError("package resources absent"),
        ):
            with self.assertRaises(tooling_assets.SkillBundleError):
                tooling_assets.load_skill_bundle()

    def test_loader_imports_without_loading_core_analyzer_or_runtime(self) -> None:
        code = (
            "import sys; import agent_braid.tooling_assets; "
            "assert not any(name in sys.modules for name in "
            "('agent_braid.analysis', 'agent_braid.git_runtime', 'agent_braid.mcp_runtime'))"
        )
        subprocess.run(
            [sys.executable, "-c", code],
            cwd=REPOSITORY,
            check=True,
            capture_output=True,
            text=True,
        )

    def test_partial_installed_bundle_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package_root = Path(temporary) / "agent_braid"
            resources_root = package_root / "tooling_assets" / "skills"
            resources_root.mkdir(parents=True)
            shutil.copytree(
                SOURCE_SKILLS / tooling_assets.SKILL_NAMES[0],
                resources_root / tooling_assets.SKILL_NAMES[0],
            )
            with patch.object(tooling_assets.resources, "files", return_value=package_root):
                with self.assertRaisesRegex(tooling_assets.SkillBundleError, "exactly five"):
                    tooling_assets.load_skill_bundle()

    def test_unexpected_skill_payload_refuses(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package_root = Path(temporary) / "agent_braid"
            resources_root = package_root / "tooling_assets" / "skills"
            resources_root.parent.mkdir(parents=True)
            shutil.copytree(SOURCE_SKILLS, resources_root)
            (resources_root / tooling_assets.SKILL_NAMES[0] / "hook.py").write_text("pass\n")
            with patch.object(tooling_assets.resources, "files", return_value=package_root):
                with self.assertRaisesRegex(tooling_assets.SkillBundleError, "only SKILL.md"):
                    tooling_assets.load_skill_bundle()

    def test_source_checkout_rejects_symlinked_skill_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "agent_braid"
            package.mkdir()
            (package / "tooling_assets.py").touch()
            (root / "pyproject.toml").write_text('[project]\nname = "agent-braid"\n')
            canonical = root / "integrations/agent-braid/skills"
            canonical.parent.mkdir(parents=True)
            shutil.copytree(SOURCE_SKILLS, canonical)
            outside = root / "outside"
            shutil.copytree(SOURCE_SKILLS / tooling_assets.SKILL_NAMES[0], outside)
            target = canonical / tooling_assets.SKILL_NAMES[0]
            shutil.rmtree(target)
            target.symlink_to(outside, target_is_directory=True)

            with patch.object(tooling_assets, "__file__", str(package / "tooling_assets.py")):
                with self.assertRaisesRegex(tooling_assets.SkillBundleError, "symbolic link"):
                    tooling_assets.load_skill_bundle(source_checkout=True)

    def test_frontmatter_identity_and_instruction_bounds(self) -> None:
        bundle = tooling_assets.load_skill_bundle(source_checkout=True)
        for skill in bundle.skills:
            self.assertLessEqual(skill.size_bytes, 32 * 1024)
            self.assertLess(len(skill.content.splitlines()), 500)
            self.assertTrue(skill.content.startswith("---\n"))
            self.assertIn(f"name: {skill.name}\n", skill.content.split("---", 2)[1])
            self.assertIn("license: CC-BY-SA-4.0\n", skill.content)

    def test_workflow_guidance_keeps_authority_and_failure_boundaries(self) -> None:
        bundle = tooling_assets.load_skill_bundle(source_checkout=True)
        by_name = {skill.name: skill.content.lower() for skill in bundle.skills}
        self.assertIn("read-only", by_name["agent-braid-analyze"])
        self.assertIn("unknown", by_name["agent-braid-analyze"])
        self.assertIn("never creates", by_name["agent-braid-plan"])
        self.assertIn("grant", by_name["agent-braid-plan"])
        self.assertIn("already granted", by_name["agent-braid-execute"])
        self.assertIn("cancelled", by_name["agent-braid-execute"])
        self.assertIn("verify", by_name["agent-braid-recover"])
        self.assertIn("unknown", by_name["agent-braid-recover"])
        self.assertIn("sha-256", by_name["agent-braid-evidence"])
        self.assertIn("confluence", by_name["agent-braid-evidence"])


if __name__ == "__main__":
    unittest.main()
