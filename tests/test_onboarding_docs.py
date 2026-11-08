# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-043 T008 technical counterpart: the onboarding guide names only things that exist.

Documentation check only. It does not observe a host and does not satisfy the T008 reopen criteria.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "tooling" / "ONBOARDING.md"
LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def help_text(*args):
    done = subprocess.run([sys.executable, "-m", "agent_braid", *args, "--help"], cwd=ROOT,
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    return done.stdout


class OnboardingGuide(unittest.TestCase):
    def setUp(self):
        self.text = GUIDE.read_text(encoding="utf-8")

    def test_relative_links_resolve(self):
        for target in LINK.findall(self.text):
            if "://" in target:
                continue
            self.assertTrue((GUIDE.parent / target.split("#")[0]).exists(), target)

    def test_journey_script_exists_and_is_documented_correctly(self):
        self.assertIn("examples/journey/run_journey.py --output", self.text)
        self.assertTrue((ROOT / "examples" / "journey" / "run_journey.py").is_file())
        out = subprocess.run([sys.executable, str(ROOT / "examples/journey/run_journey.py"), "--help"],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("--output", out.stdout)

    def test_documented_cli_subcommands_and_options_exist(self):
        present = help_text("tooling", "present")
        for option in ("--format", "--export-directory", "--evidence-ref", "text", "json", "graph"):
            self.assertRegex(present, rf"(?<![\w-]){re.escape(option)}(?![\w-])")
            self.assertIn(option, self.text)
        self.assertIn("doctor", help_text("tooling"))
        plugin = help_text("plugin")
        for sub in ("doctor", "workspaces", "setup"):
            self.assertIn(sub, plugin)
        for option in ("--apply", "--preview-digest"):
            for command in (("plugin", "setup"), ("tooling", "install")):
                self.assertRegex(help_text(*command), rf"(?<![\w-]){option}(?![\w-])")
            self.assertIn(option, self.text)

    def test_documented_tools_and_skills_exist(self):
        for tool in ("plugin-status", "workspaces"):
            self.assertIn(f"`{tool}`", self.text)
            self.assertIn(f"'{tool}'", (ROOT / "agent_braid" / "plugin_mcp.py").read_text(encoding="utf-8"))
        for skill in ("setup", "analyze", "plan", "evidence", "telemetry-audit"):
            self.assertIn(f"`{skill}`", self.text)
            found = [ROOT / "integrations" / "agent-braid" / "plugin" / skill / "SKILL.md",
                     ROOT / "integrations" / "agent-braid" / "skills" / f"agent-braid-{skill}" / "SKILL.md"]
            self.assertTrue(any(path.is_file() for path in found), skill)

    def test_states_it_is_not_host_observation(self):
        self.assertIn("not actual-host observation", self.text)
        self.assertIn("reopen criteria", self.text)


if __name__ == "__main__":
    unittest.main()
