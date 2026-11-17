# SPDX-License-Identifier: AGPL-3.0-only
"""Codex adapter against the shapes observed natively (codex-cli 0.169.0-alpha.11.1, 2026-11-17).

The fixture repeats the observed event sequence of
``specs/048-harness-variant-laboratory/evidence/codex-capture/capture-20261117T221002Z.json``
with synthetic values (the record holds key names and value types only). Offline, scripted
double only; native dispatch stays refused.
"""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from agent_braid import harness_host_codex as codex
from tests.test_harness_host_codex import host, line, run, terminal

CAPTURE = (Path(__file__).resolve().parents[1] / "specs/048-harness-variant-laboratory/evidence"
           / "codex-capture/capture-20261117T221002Z.json")
CAPTURE_SHA256 = "aa12a2eee6a9e9061f76b0558cd3d6fe89e8fa816f57195eaa3dd48519aa2105"
USAGE = {"input_tokens": 9000, "cached_input_tokens": 0, "cache_write_input_tokens": 0,
         "output_tokens": 40, "reasoning_output_tokens": 12}
COMMAND = {"id": "item_1", "type": "command_execution", "command": "/bin/zsh -lc ls",
           "aggregated_output": "", "exit_code": None, "status": "in_progress"}
OBSERVED = (
    line(type="thread.started", thread_id="t-observed"),
    line(type="turn.started"),
    line(type="item.completed", item={"id": "item_0", "type": "agent_message", "text": "Listing."}),
    line(type="item.started", item=COMMAND),
    line(type="item.completed", item={**COMMAND, "aggregated_output": "README.txt\nnotes.txt\n",
                                      "exit_code": 0, "status": "completed"}),
    line(type="item.completed", item={"id": "item_2", "type": "agent_message", "text": "2"}),
    line(type="turn.completed", usage=USAGE),
)
# Labels the adapter handles explicitly (normalized or deliberately ignored).
HANDLED = {"thread.started", "turn.started", "turn.completed", "turn.failed", "error",
           "item.started", "item.updated"} | {
    f"item.{phase}/{kind}" for phase in ("started", "updated", "completed")
    for kind in ("agent_message", "command_execution", "file_change", "mcp_tool_call",
                 "web_search", "reasoning", "todo_list")}


class ObservedShapeTests(unittest.TestCase):
    def test_observed_sequence_normalizes_completely(self):
        result = run(host(OBSERVED))
        data = result.observation.to_dict()
        self.assertEqual(terminal(result), "completed")
        self.assertEqual([e["kind"] for e in data["events"]],
                         ["start", "message", "tool", "effect", "message", "terminal"])
        self.assertEqual([e["text"] for e in data["events"] if e["kind"] == "message"],
                         ["Listing.", "2"])  # the final answer is the last message
        tool = next(e for e in data["events"] if e["kind"] == "tool")
        self.assertEqual((tool["tool"], tool["exitCode"]), ("command_execution", 0))
        self.assertEqual(dict(result.usage), USAGE)  # both new usage keys are kept
        self.assertEqual(result.ignored_events, 2)  # turn.started + item.started
        self.assertEqual(data["loss"]["transportErrors"], [])
        self.assertNotIn(b"README.txt", result.observation.canonical_bytes)  # output never exported

    def test_capture_record_is_pinned_and_fits_the_adapter(self):
        raw = CAPTURE.read_bytes()
        self.assertEqual(sha256(raw).hexdigest(), CAPTURE_SHA256)
        record = json.loads(raw)
        self.assertEqual(record["binary"]["version"], "codex-cli 0.169.0-alpha.11.1")
        self.assertFalse(record["executionAuthorization"])
        self.assertFalse(record["nativeDispatchQualified"])
        self.assertEqual(len(record["runs"]), 2)
        for observed in record["runs"]:
            self.assertEqual(observed["exit"], 0)
            self.assertEqual(observed["unparsedLines"], 0)
            self.assertLessEqual(set(observed["events"]), HANDLED)
            fit = observed["adapterFit"]
            self.assertEqual(fit["errors"], [])
            self.assertNotIn("unknown", fit["kinds"])
            self.assertEqual(fit["hostTerminal"], "completed")
            self.assertEqual(set(fit["usageKeys"]), set(USAGE))

    def test_native_dispatch_stays_unqualified(self):
        self.assertIs(codex.NATIVE_DISPATCH_QUALIFIED, False)


if __name__ == "__main__":
    unittest.main()
