# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T008 (REQ-008 / SC-008 / procedure_008): the analyze skill's requests are drift-proof.

Every fenced ``json kind=<k> result=<classification> constraints=<c>`` block of the skill is sent through
``analyze-work`` and must be accepted with exactly the documented classification and constraints.
"""

from __future__ import annotations

import copy
import json
import re
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from agent_braid import tooling_mcp
from agent_braid.tooling_mcp import ToolingConfig, ToolingService

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "integrations/agent-braid/skills/agent-braid-analyze/SKILL.md"
BLOCK = re.compile(r"```json kind=(\w+) result=(\S+) constraints=(\S+)\n(.*?)```", re.S)
REPOSITORY_PLACEHOLDER = "<workspace root directory>"


def documented_examples(text: str) -> list[dict]:
    return [{"kind": kind, "result": result, "constraints": constraints.split(","), "request": json.loads(body)}
            for kind, result, constraints, body in BLOCK.findall(text)]


def git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


class GuidanceCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        base = Path(cls.temp.name)
        cls.source, results = base / "source", base / "results"
        cls.source.mkdir(), results.mkdir()
        git(cls.source, "init", "-q", "-b", "main")
        for name in ("one.txt", "two.txt"):
            (cls.source / name).write_text("base\n")
        git(cls.source, "add", "."), git(cls.source, "commit", "-q", "-m", "base")
        for branch, name in (("feature-one", "one.txt"), ("feature-two", "two.txt")):
            git(cls.source, "checkout", "-q", "-b", branch, "main")
            (cls.source / name).write_text(branch + "\n")
            git(cls.source, "commit", "-q", "-am", branch)
        git(cls.source, "checkout", "-q", "main")
        cls.service = ToolingService(ToolingConfig(cls.source, results))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def send(self, kind: str, request) -> dict:
        request = json.loads(json.dumps(request).replace(REPOSITORY_PLACEHOLDER, str(self.source)))
        return self.service.invoke("analyze-work", {"kind": kind, "request": request}, threading.Event())

    def problems(self, example: dict) -> list[str]:
        """Why the documented example does not give its documented result; empty when it does."""
        envelope = self.send(example["kind"], example["request"])
        if envelope["status"] != "ok":
            return [f"{example['kind']}: {envelope['status']}: {envelope['summary']}"]
        pairs = envelope["result"]["report"]["interactions"]
        found = [(p["classification"], sorted(p["constraints"])) for p in pairs]
        wanted = [(example["result"], sorted(example["constraints"]))]
        return [] if found == wanted else [f"{example['kind']}: documented {wanted}, got {found}"]


class SkillExampleTests(GuidanceCase):
    def setUp(self):
        self.examples = documented_examples(SKILL.read_text("utf-8"))

    def test_the_skill_documents_one_example_per_kind(self):
        self.assertEqual(sorted(e["kind"] for e in self.examples), ["aim", "git", "units"])

    def test_every_example_is_accepted_with_its_documented_result(self):
        for example in self.examples:
            self.assertEqual(self.problems(example), [], example["kind"])

    def test_no_example_carries_a_scheme_a_kind_cannot_take(self):
        by_kind = {e["kind"]: json.dumps(e["request"]) for e in self.examples}
        self.assertNotIn("repo://", by_kind["units"])
        self.assertIn("repo://workspace/", by_kind["aim"])

    def test_the_documented_coverage_rule_matches_the_report(self):
        aim = next(e for e in self.examples if e["kind"] == "aim")
        partial = copy.deepcopy(aim)
        for operation in partial["request"]["operations"]:
            operation["effects"]["coverage"]["status"] = "partial"
        # what the skill warns about: partial coverage turns the pair into unknown
        self.assertIn("('unknown',", self.problems(partial)[0])
        self.assertIn("complete", SKILL.read_text("utf-8"))

    # negative controls: the test must fail when the schema or the documented result drifts
    def test_a_renamed_required_field_fails(self):
        for example in self.examples:
            broken = copy.deepcopy(example)
            target = broken["request"]["operations"][0] if example["kind"] != "units" else broken["request"]["units"][0]
            key = {"aim": "instanceId", "git": "instanceId", "units": "id"}[example["kind"]]
            target["renamed"] = target.pop(key)
            self.assertTrue(self.problems(broken), example["kind"])

    def test_a_wrong_documented_result_fails(self):
        for example in self.examples:
            wrong = {**example, "result": "unknown"}
            self.assertTrue(self.problems(wrong), example["kind"])
            wrong = {**example, "constraints": ["serialize-unless-stronger-evidence"]}
            self.assertTrue(self.problems(wrong), example["kind"])

    def test_the_parser_ignores_unannotated_blocks(self):
        self.assertEqual(documented_examples("```json\n{}\n```"), [])


class ToolDescriptionTests(unittest.TestCase):
    def test_description_chooses_the_kind_and_and_states_the_coverage_rule(self):
        text = tooling_mcp._ANALYZE_WORK_SCHEMA_HELP
        for phrase in ("aim", "git", "units", "independent-candidate", "coverage complete if files are named"):
            self.assertIn(phrase, text)

    def test_git_source_refusal_states_the_commit_form(self):
        with self.assertRaises(Exception) as caught:
            tooling_mcp._require_git_structure({"repository": "r", "operations": [{"source": 1}, {"source": 2}]})
        self.assertIn('kind: "commit", revision', str(caught.exception.expected))


if __name__ == "__main__":
    unittest.main()
