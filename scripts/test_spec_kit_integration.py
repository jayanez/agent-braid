#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned-tool integration tests in temporary repositories; no model sessions."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml

from spec_kit import ROOT, generate
from validate_spec_kit import check


class IntegrationTests(unittest.TestCase):
    def test_solo_and_dual_regeneration(self):
        for installed, active in ((["codex"], "codex"), (["claude"], "claude"),
                                  (["codex", "claude"], "codex"),
                                  (["codex", "claude"], "claude")):
            with self.subTest(installed=installed, active=active), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp) / "repo"
                subprocess.run(
                    ["git", "clone", "--quiet", "--no-local", str(ROOT), str(root)],
                    check=True,
                )
                # A local clone copies branch tips, but not the source clone's
                # remote-tracking refs. Historical assurance commits may be
                # reachable only through those refs (as in Actions checkout).
                # Keep them reachable in the disposable clone without network
                # access or rewriting the reviewed evidence.
                inherited = subprocess.run(
                    ["git", "-C", str(ROOT), "for-each-ref", "--format=%(refname)",
                     "refs/remotes/origin"],
                    capture_output=True, text=True, check=True,
                ).stdout.splitlines()
                refspecs = [
                    f"+{ref}:refs/remotes/source-origin/{ref.removeprefix('refs/remotes/origin/')}"
                    for ref in inherited if ref != "refs/remotes/origin/HEAD"
                ]
                if refspecs:
                    subprocess.run(
                        ["git", "-C", str(root), "fetch", "--quiet", "--no-tags",
                         str(ROOT), *refspecs],
                        check=True,
                    )
                for integration in (".agents", ".claude"):
                    shutil.rmtree(root / integration, ignore_errors=True)
                shutil.copytree(
                    ROOT,
                    root,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(
                        ".git", ".venv", ".venv-speckit", "__pycache__",
                        ".agents", ".claude",
                    ),
                )
                canonical = (root / "CONSTITUTION.md").read_bytes()
                generate(root, installed=installed, active=active)
                check(root, require_both=len(installed) == 2)
                self.assertEqual(generate(root, check=True), [])
                self.assertEqual((root / "CONSTITUTION.md").read_bytes(), canonical)
                self.assertEqual(json.loads((root / ".specify/integration.json").read_text())[
                    "default_integration"], active)
                for agent in installed:
                    folder = ".agents" if agent == "codex" else ".claude"
                    skill = root / folder / "skills/speckit-constitution/SKILL.md"
                    text = skill.read_text()
                    self.assertIn("Do not modify", text)
                    self.assertNotIn("Write the completed constitution", text)
                    self.assertIn("python3 -m scripts.validate_spec_kit", text)
                    for artifact in (root / folder / "skills").glob("*/SKILL.md"):
                        content = artifact.read_text()
                        metadata = yaml.safe_load(content.split("---", 2)[1])
                        self.assertEqual(metadata["name"], artifact.parent.name)
                        self.assertIsInstance(metadata["description"], str)
                        self.assertNotIn("{SCRIPT}", content)
                        self.assertNotIn(".specify/scripts/validate_spec_kit.py", content)
                if len(installed) == 2:
                    # Shared policy/command bodies are byte-identical after native metadata.
                    for name in (root / ".agents/skills").iterdir():
                        codex = (name / "SKILL.md").read_text().split("## Agent Braid shared gates", 1)[1]
                        claude = (root / ".claude/skills" / name.name / "SKILL.md").read_text().split(
                            "## Agent Braid shared gates", 1)[1]
                        self.assertEqual(codex, claude)
                # A raw upstream switch can overwrite guards; detect before regeneration.
                cli = Path(sys.executable).parent / ("specify.exe" if os.name == "nt" else "specify")
                other = installed[-1]
                subprocess.run([str(cli), "integration", "use", other], cwd=root,
                               capture_output=True, text=True, check=True)
                with self.assertRaises(ValueError):
                    check(root, require_both=len(installed) == 2)
                generate(root)
                check(root, require_both=len(installed) == 2)
                self.assertEqual(json.loads((root / ".specify/integration.json").read_text())[
                    "default_integration"], other)
                # Exercise actual helpers and template resolution, not just wording.
                helper = root / ".specify/scripts/python"
                env = dict(os.environ, SPECIFY_INIT_DIR=str(root))
                env.pop("SPECIFY_FEATURE_DIRECTORY", None)
                result = subprocess.run([sys.executable, str(helper / "create_new_feature.py"),
                                         "--json", "--short-name", "guardrail-probe", "Probe shared guards"],
                                        cwd=root, env=env, capture_output=True, text=True, check=True)
                feature = json.loads(result.stdout)
                spec = Path(feature["SPEC_FILE"])
                self.assertEqual(spec.read_bytes(), (root / ".specify/templates/overrides/spec-template.md").read_bytes())
                subprocess.run([sys.executable, str(helper / "setup_plan.py"), "--json"],
                               cwd=root, env=env, capture_output=True, text=True, check=True)
                self.assertEqual((spec.parent / "plan.md").read_bytes(),
                                 (root / ".specify/templates/overrides/plan-template.md").read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
