# SPDX-License-Identifier: AGPL-3.0-only
"""Controls for the read-only observational native receipt extractor (synthetic transcripts only)."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

_SCRIPT = (Path(__file__).resolve().parents[1] / "specs" / "041-ai-tooling-skills" / "evidence"
           / "extract_observational_receipts.py")
_spec = importlib.util.spec_from_file_location("extract_observational_receipts", _SCRIPT)
extract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(extract)

SECRET = "PRIVATE-PROMPT-AND-PROJECT-NAME"
CACHE = "/home/x/.claude/plugins/cache/agent-braid/agent-braid/0.1.0-alpha.4/skills/"


def _msg(kind, ts, content, **extra):
    return {"type": kind, "timestamp": ts, "sessionId": "sess-1", "message": {"content": content}, **extra}


def _transcript():
    envelope = lambda status: json.dumps({"status": status, "provenance": {"candidateVersion": "0.1.0a1"},
                                          "summary": SECRET})
    return [
        {"type": "attachment", "timestamp": "2026-10-01T00:00:00Z", "sessionId": "sess-1",
         "attachment": {"type": "skill_listing",
                        "content": "- agent-braid:analyze: x\n- agent-braid:plan: y\n- other:skill: z"}},
        _msg("user", "2026-10-01T00:00:01Z", [{"type": "text", "text": SECRET}]),
        _msg("assistant", "2026-10-01T00:00:02Z", [
            {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "agent-braid:analyze", "args": SECRET}}]),
        _msg("user", "2026-10-01T00:00:03Z", [{"type": "tool_result", "tool_use_id": "t1", "content": "Launching"}]),
        _msg("user", "2026-10-01T00:00:03Z", [{"type": "text",
             "text": f"Base directory for this skill: {CACHE}analyze\n\nbody"}], isMeta=True, sourceToolUseID="t1"),
        _msg("assistant", "2026-10-01T00:00:04Z", [
            {"type": "tool_use", "id": "t2", "name": "mcp__plugin_agent-braid_agent-braid__analyze", "input": {"p": SECRET}},
            {"type": "tool_use", "id": "t3", "name": "mcp__plugin_agent-braid_agent-braid__prepare", "input": {}}]),
        _msg("user", "2026-10-01T00:00:05Z", [
            {"type": "tool_result", "tool_use_id": "t2", "is_error": True, "content": envelope("refused")},
            {"type": "tool_result", "tool_use_id": "t3", "content": [{"type": "text", "text": envelope("ok")}]}]),
        _msg("assistant", "2026-10-01T00:00:06Z", [  # duplicate id from a resumed copy is counted once
            {"type": "tool_use", "id": "t2", "name": "mcp__plugin_agent-braid_agent-braid__analyze", "input": {}}]),
        _msg("assistant", "2026-10-01T00:00:07Z", [
            {"type": "tool_use", "id": "t9", "name": "Skill", "input": {"skill": "other:skill"}}]),
    ]


class ObservationalReceiptTests(unittest.TestCase):
    def _build(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        (root / "claude" / "proj").mkdir(parents=True)
        with (root / "claude" / "proj" / "a.jsonl").open("w") as handle:
            handle.write("\n".join(json.dumps(r) for r in _transcript()) + "\nnot json\n")
        # a resumed copy repeats history: calls, loads and listings must still count once
        (root / "claude" / "proj" / "b.jsonl").write_text(
            "\n".join(json.dumps(r) for r in _transcript()) + "\n")
        (root / "codex").mkdir()
        return extract.build(root / "claude", root / "codex", root / "home")

    def test_levels_outcomes_and_versions(self):
        receipts, journey = self._build()
        claude = receipts["hosts"][0]
        self.assertEqual(claude["c1Discovery"]["skillsListedInContext"]["plan"]["state"], "observed")
        self.assertEqual(claude["c1Discovery"]["skillsListedInContext"]["execute"]["state"], "not-observed")
        loaded = claude["c2InstructionsLoaded"]["analyze"]
        self.assertEqual(loaded["count"], 1)
        self.assertEqual(claude["c1Discovery"]["skillsListedInContext"]["plan"]["sessions"], 1)
        self.assertEqual(loaded["versions"], {"0.1.0-alpha.4": 1})
        self.assertEqual(len(next(iter(loaded["loadedContentSha256"]))), 64)
        used = claude["c3ObservedUse"]
        self.assertEqual(used["skills"]["analyze"]["count"], 1)
        self.assertEqual(used["skills"]["analyze"]["versions"], {"0.1.0-alpha.4": 1})
        self.assertEqual(used["mcpTools"]["analyze"]["outcomes"], {"refused": 1})
        self.assertEqual(used["mcpTools"]["analyze"]["count"], 1)
        self.assertEqual(used["mcpTools"]["prepare"]["outcomes"], {"ok": 1})
        self.assertEqual(used["mcpTools"]["prepare"]["versions"], {"0.1.0a1": 1})
        self.assertEqual([e["item"] for e in journey["journeys"][0]["events"]],
                         ["skill:analyze", "mcp:analyze", "mcp:prepare"])

    def test_no_private_content_is_emitted(self):
        receipts, journey = self._build()
        dump = json.dumps([receipts, journey])
        self.assertNotIn(SECRET, dump)
        self.assertNotIn("sess-1", dump)
        self.assertNotIn("/home/x", dump)

    def test_missing_roots_yield_not_observed(self):
        receipts, _ = extract.build(Path("/nonexistent/a"), Path("/nonexistent/b"), Path("/nonexistent/h"))
        self.assertEqual(receipts["hosts"][0]["transcriptFilesScanned"], 0)
        self.assertEqual(receipts["localStores"]["evidenceStore"], {"state": "absent"})
        self.assertEqual(receipts["localStores"]["pluginWorkspaceRegistry"], {"state": "absent"})
        self.assertEqual(receipts["hosts"][1]["c3ObservedUse"]["state"], "not-observed")


if __name__ == "__main__":
    unittest.main()
