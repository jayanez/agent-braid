# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T011 (REQ-011 / SC-011 / procedure_011): the SPEC-069 documentation is backed by evidence.

The ``analyze-work`` request-kinds section of ``docs/tooling/NATIVE_PLUGINS.md`` (including the release-note draft)
must cite only files that exist, its links and anchors must resolve, and its measured numbers must equal the
committed evidence (T005 native probe, T010 held-out run, T009 replay). Negative controls show that a broken link,
a wrong number and a missing cited file are detected.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from agent_braid import analyze_work_schema

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/tooling/NATIVE_PLUGINS.md"
SPEC = ROOT / "specs/069-aim-request-authoring"
EVIDENCE = SPEC / "evidence"
START = "## `analyze-work` request kinds (SPEC-069, unreleased)"
LINK = re.compile(r"\]\(([^)\s]+)\)")
CITED = re.compile(r"`((?:tests|evidence|examples|scripts|schemas|agent_braid)/[^`\s]+)`")
HOSTS = {"Claude Code": "claude-code", "OpenCode": "opencode", "Codex": "codex"}
ROW = re.compile(r"^\| (Claude Code|OpenCode|Codex) \| (\d+)/(\d+) \((\d\.\d\d)–(\d\.\d\d)\) \| (\d+) \| ([^|]+) \|$", re.M)


def section(text: str) -> str:
    start = text.index(START)
    end = text.index("\n## ", start + len(START))
    return text[start:end]


def flat(text: str) -> str:
    """The prose with block-quote markers removed and whitespace collapsed, for phrase checks."""
    return " ".join(" ".join(re.sub(r"^> ?", "", line) for line in text.splitlines()).split())


def slug(heading: str) -> str:
    """GitHub heading anchor: lower case, punctuation other than '-' and '_' removed, spaces to '-'."""
    return re.sub(r"[^\w\- ]", "", heading.strip().lower()).replace(" ", "-")


def anchors(path: Path) -> set[str]:
    return {slug(m.group(1)) for m in re.finditer(r"^#{1,6} (.+)$", path.read_text(encoding="utf-8"), re.M)}


def broken_links(text: str, base: Path) -> list[str]:
    broken = []
    for target in LINK.findall(text):
        if target.startswith(("http://", "https://")):
            continue
        path, _, anchor = target.partition("#")
        resolved = (base.parent / path).resolve() if path else base
        if not resolved.exists():
            broken.append(target)
        elif anchor and resolved.suffix == ".md" and anchor not in anchors(resolved):
            broken.append(target)
    return broken


def missing_citations(text: str) -> list[str]:
    missing = []
    for cited in CITED.findall(text):
        base = SPEC if cited.startswith("evidence/") else ROOT
        if not list(base.glob(cited)):
            missing.append(cited)
    return missing


def held_out_rows(text: str) -> dict[str, tuple]:
    return {HOSTS[m[0]]: (int(m[1]), int(m[2]), float(m[3]), float(m[4]), int(m[5]), sorted(m[6].strip().split(", ")))
            for m in ROW.findall(text)}


def held_out_evidence() -> dict[str, tuple]:
    rows = {}
    for name in ("native-runs-t010-heldout-final.json", "native-runs-t010-heldout-final-codex.json"):
        for host, s in json.loads((EVIDENCE / name).read_text(encoding="utf-8"))["summary"]["hosts"].items():
            if s["verdict"] == "unobserved":
                continue
            low, high = s["firstAttemptInterval"]
            rows[host] = (s["firstAttemptTrials"], s["trials"], round(low, 2), round(high, 2),
                          s["firstAttemptPrompts"], sorted(s["firstAttemptPromptsMissed"]))
    return rows


class Spec069DocsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = section(DOC.read_text(encoding="utf-8"))
        cls.flat = flat(cls.text)

    def test_links_and_anchors_resolve(self):
        self.assertEqual(broken_links(DOC.read_text(encoding="utf-8"), DOC), [])

    def test_every_cited_file_exists(self):
        self.assertEqual(missing_citations(self.text), [])

    def test_documented_kinds_equal_the_served_enum(self):
        documented = [k for k in re.findall(r"^\| `(\w+)` \| ", self.text, re.M) if k != "kind"]
        self.assertEqual(tuple(documented), analyze_work_schema.KINDS)

    def test_held_out_table_equals_the_t010_evidence(self):
        rows = held_out_rows(self.text)
        self.assertEqual(rows, held_out_evidence())
        self.assertEqual(set(rows), set(HOSTS.values()))

    def test_retry_claim_and_d4_verdict_follow_the_evidence(self):
        for name in ("native-runs-t010-heldout-final.json", "native-runs-t010-heldout-final-codex.json"):
            summary = json.loads((EVIDENCE / name).read_text(encoding="utf-8"))["summary"]
            self.assertEqual(summary["overall"], "negative-result")
            for s in summary["hosts"].values():
                self.assertEqual(s["withinRetryTrials"], s["firstAttemptTrials"])
        self.assertIn("A refusal-guided retry added no valid trials", self.flat)
        self.assertIn("is **not met** on any host", self.flat)

    def test_probe_hosts_versions_and_loading_follow_procedure_005(self):
        native = json.loads((EVIDENCE / "procedure_005.json").read_text(encoding="utf-8"))["native"]
        self.assertTrue(native["passed"])
        loading = {"deferred": "Claude Code deferred the tool (ToolSearch first)",
                   "eager": "Codex loaded it eagerly",
                   "helper-before-call": "OpenCode loaded it eagerly after its `execute` helper"}
        self.assertEqual(set(native["arms"]), {"per-kind", "description-only"})
        for arm in native["arms"].values():
            for host in arm["hosts"].values():
                self.assertTrue(host["exposedToModel"])
                self.assertTrue(host["requestAlwaysObject"])
                self.assertTrue(host["servedBytesMatchFingerprint"])
                self.assertEqual({c["kind"] for c in host["callsAtServer"]}, {"aim", "units"})
                self.assertIn(loading[host["loading"]], self.flat)
        versions = "".join((EVIDENCE / name).read_text(encoding="utf-8")
                           for name in ("native-probe-schema-per-kind.json", "native-probe-schema-per-kind-codex.json"))
        for version in ("2.1.311 (Claude Code)", "codex-cli 0.167.0-alpha.4.1", "opencode v2.1.4"):
            self.assertIn(version, versions)
        for version in ("Claude Code 2.1.311", "Codex 0.167.0-alpha.4.1", "OpenCode 2.1.4"):
            self.assertIn(version, self.flat)

    def test_replay_counts_follow_procedure_009(self):
        outcome = json.loads((EVIDENCE / "procedure_009.json").read_text(encoding="utf-8"))["outcome"]
        self.assertIn("103 accepted stay accepted", outcome)
        self.assertIn("214 not accepted stay not accepted", outcome)
        self.assertIn("All 103 recorded `aim` requests", self.flat)
        self.assertIn("The 214 it refused are still refused", self.flat)

    def test_rollback_message_equals_the_compatibility_note(self):
        compatibility = (SPEC / "compatibility.md").read_text(encoding="utf-8")
        self.assertIn("`analyze-work refused: Unsupported analysis kind`", flat(compatibility))
        self.assertIn("`analyze-work refused: Unsupported analysis kind`", self.flat)
        self.assertIn("agent-braid--v0.1.0-alpha.7", self.text)

    def test_draft_states_that_nothing_is_published(self):
        self.assertIn("nothing has been published, tagged or versioned", self.flat)

    def test_negative_control_a_broken_link_is_detected(self):
        broken = self.text + "\n[x](../../specs/069-aim-request-authoring/missing.md) [y](SKILLS.md#no-such-heading)\n"
        self.assertEqual(broken_links(broken, DOC),
                         ["../../specs/069-aim-request-authoring/missing.md", "SKILLS.md#no-such-heading"])

    def test_negative_control_a_wrong_number_is_detected(self):
        wrong = self.text.replace("| Codex | 24/30 (0.63–0.90) | 7 |", "| Codex | 25/30 (0.63–0.90) | 7 |")
        self.assertNotEqual(wrong, self.text)
        self.assertNotEqual(held_out_rows(wrong), held_out_evidence())

    def test_negative_control_a_missing_cited_file_is_detected(self):
        self.assertEqual(missing_citations("`tests/test_spec069_absent.py` `evidence/procedure_099.json`"),
                         ["tests/test_spec069_absent.py", "evidence/procedure_099.json"])


if __name__ == "__main__":
    unittest.main()
