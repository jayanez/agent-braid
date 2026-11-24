# SPDX-License-Identifier: AGPL-3.0-only
"""Focused checks for the portable product skill resource inventory."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_braid import analysis, tooling_assets


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
            frontmatter = skill.content.split("---", 2)[1]
            self.assertIn(f"name: {skill.name}\n", frontmatter)
            # SPEC-080 OD-2: the license is metadata.license, never a top-level field.
            self.assertIn("\nmetadata:\n  license: CC-BY-SA-4.0\n", frontmatter)
            self.assertNotRegex(frontmatter, r"(?m)^license:")
            self.assertEqual(
                {"name", "description", "metadata"},
                set(re.findall(r"(?m)^([a-z-]+):", frontmatter)),
            )

    def test_inventory_license_reads_metadata_license(self) -> None:
        inventory = tooling_assets.load_skill_bundle(source_checkout=True).inventory()
        self.assertEqual(["CC-BY-SA-4.0"] * 5, [entry["license"] for entry in inventory["skills"]])

    def _load_mutated(self, mutate):
        """Load an installed-layout copy whose analyze skill frontmatter is ``mutate``d."""
        with tempfile.TemporaryDirectory() as temporary:
            package_root = Path(temporary) / "agent_braid"
            resources_root = package_root / "tooling_assets" / "skills"
            resources_root.parent.mkdir(parents=True)
            shutil.copytree(SOURCE_SKILLS, resources_root)
            path = resources_root / "agent-braid-analyze" / "SKILL.md"
            head, separator, body = path.read_text("utf-8").partition("\n---\n")
            mutated = mutate(head)
            self.assertNotEqual(head, mutated, "the mutation must change the frontmatter")
            path.write_text(mutated + separator + body, "utf-8")
            with patch.object(tooling_assets.resources, "files", return_value=package_root):
                return tooling_assets.load_skill_bundle()

    def test_frontmatter_guards_refuse_with_a_mutation_control_each(self) -> None:
        # SPEC-080 T014 (REQ-005 / SC-005). Each guard has a passing control that differs
        # from the refused fixture only in the guarded property.
        metadata = "\nmetadata:\n  license: CC-BY-SA-4.0"
        cases = {
            "top-level license": (
                lambda head: head.replace(metadata, metadata + "\ncompatibility: CC-BY-SA-4.0"),
                lambda head: head.replace(metadata, metadata + "\nlicense: CC-BY-SA-4.0"),
                "metadata.license, not top level",
            ),
            "missing metadata.license": (
                lambda head: head.replace(metadata, metadata + "\n  owner: agent-braid"),
                lambda head: head.replace(metadata, "\nmetadata:\n  owner: agent-braid"),
                "metadata.license is missing",
            ),
            "missing metadata map": (
                lambda head: head.replace(metadata, metadata + "\n  owner: agent-braid"),
                lambda head: head.replace(metadata, ""),
                "requires name, description and metadata",
            ),
            "unknown top-level key": (
                lambda head: head.replace(metadata, metadata + "\ncompatibility: Requires a shell."),
                lambda head: head.replace(metadata, metadata + "\nallowed-tools: Bash"),
                "unsupported skill frontmatter field allowed-tools",
            ),
            "wrong metadata.license": (
                lambda head: head.replace(metadata, metadata + "\n  owner: agent-braid"),
                lambda head: head.replace(metadata, "\nmetadata:\n  license: MIT"),
                "license must be CC-BY-SA-4.0",
            ),
            "metadata entry outside the map": (
                lambda head: head.replace(metadata, metadata + "\n  owner: agent-braid"),
                lambda head: head.replace(metadata, metadata + "\ncompatibility: x\n  owner: agent-braid"),
                "outside the metadata map",
            ),
            "duplicate metadata key": (
                lambda head: head.replace(metadata, metadata + "\n  owner: agent-braid"),
                lambda head: head.replace(metadata, metadata + "\n  license: CC-BY-SA-4.0"),
                "duplicate skill metadata field license",
            ),
            "nested metadata value": (
                lambda head: head.replace(metadata, metadata + "\n  owner: agent-braid"),
                lambda head: head.replace(metadata, metadata + "\n    nested: x"),
                "unsupported skill frontmatter line",
            ),
        }
        for label, (control, mutation, message) in cases.items():
            with self.subTest(label):
                bundle = self._load_mutated(control)
                self.assertEqual("CC-BY-SA-4.0", bundle.skills[0].license)
                with self.assertRaisesRegex(tooling_assets.SkillBundleError, re.escape(message)):
                    self._load_mutated(mutation)

    def test_parse_skill_frontmatter_returns_the_four_agent_skills_fields(self) -> None:
        parsed = tooling_assets.parse_skill_frontmatter(
            "---\nname: harness\ndescription: Read the harness.\ncompatibility: Requires a shell.\n"
            "metadata:\n  license: CC-BY-SA-4.0\n  owner: agent-braid\n---\nbody\n",
            "harness",
        )
        self.assertEqual("harness", parsed.name)
        self.assertEqual("Read the harness.", parsed.description)
        self.assertEqual("Requires a shell.", parsed.compatibility)
        self.assertEqual((("license", "CC-BY-SA-4.0"), ("owner", "agent-braid")), parsed.metadata)
        self.assertEqual("CC-BY-SA-4.0", parsed.license)

    def test_analyze_skill_examples_are_checked_by_the_drift_test(self) -> None:
        # Issue #1080 / SPEC-069 T008: the examples are validated and analysed in tests/test_spec069_guidance.py.
        content = (SOURCE_SKILLS / "agent-braid-analyze" / "SKILL.md").read_text("utf-8")
        self.assertEqual(3, len(re.findall(r"```json kind=\w+ result=\S+ constraints=\S+\n", content)))
        self.assertEqual(3, len(re.findall(r"```json", content)))

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
