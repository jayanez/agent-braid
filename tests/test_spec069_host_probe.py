# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T005: the host-probe test double and its summaries (no host, no model, no credential)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import spec069_host_probe as probe

DEFINITION = {"name": "analyze-work", "description": "d", "inputSchema": {
    "type": "object", "properties": {"kind": {"enum": ["aim", "git"]}, "request": {"oneOf": [{"type": "object"}, {"type": "array"}]},
                                     "workspaceId": {"type": "string"}},
    "required": ["kind", "request", "workspaceId"], "additionalProperties": False}}


def talk(messages: list[dict]) -> tuple[list[dict], list[dict]]:
    with tempfile.TemporaryDirectory() as temp:
        definition, record = Path(temp, "d.json"), Path(temp, "r.jsonl")
        definition.write_text(json.dumps(DEFINITION))
        done = subprocess.run([sys.executable, "-I", probe.__file__, "serve", str(definition), str(record)],
                              input="\n".join(json.dumps(m) for m in messages) + "\n", capture_output=True, text=True, timeout=30)
        assert done.returncode == 0, done.stderr
        return [json.loads(line) for line in done.stdout.splitlines()], probe.read_record(record)


class DoubleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.replies, self.rows = talk([
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "clientInfo": {"name": "x", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "analyze-work", "arguments": {"kind": "aim", "request": "{}", "workspaceId": "w"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "nope"}])

    def test_serves_the_definition_unchanged_and_echoes_the_protocol_version(self) -> None:
        self.assertEqual(self.replies[0]["result"]["protocolVersion"], "2025-03-26")
        self.assertEqual(self.replies[1]["result"]["tools"], [DEFINITION])
        self.assertEqual(self.replies[3]["error"]["code"], -32601)

    def test_summary_hashes_the_listing_and_keeps_the_calls(self) -> None:
        expected = probe.sha(probe.canonical(DEFINITION))
        info = probe.summarize_connection(self.rows, expected)
        self.assertTrue(info["toolsList"][0]["matchesDefinition"])
        self.assertEqual(info["initialize"]["clientInfo"]["name"], "x")
        self.assertEqual(len(info["toolsCalls"]), 1)
        self.assertFalse(probe.summarize_connection(self.rows, "0" * 64)["toolsList"][0]["matchesDefinition"])

    def test_stringified_request_is_reported_as_not_an_object_and_not_valid(self) -> None:
        verdict = probe.conformance({"kind": "aim", "request": "{}", "workspaceId": "w"}, DEFINITION["inputSchema"])
        self.assertFalse(verdict["requestIsObject"])
        self.assertEqual(verdict["requestType"], "str")
        good = probe.conformance({"kind": "aim", "request": {"units": []}, "workspaceId": "w"}, DEFINITION["inputSchema"])
        self.assertTrue(good["requestIsObject"] and good["validates"])


class ForwarderTests(unittest.TestCase):
    def test_keeps_names_and_hashes_never_bodies(self) -> None:
        schema = DEFINITION["inputSchema"]
        forwarder = probe.Forwarder("api.invalid", probe.sha(probe.canonical(schema)))
        body = json.dumps({"model": "m", "messages": [{"role": "user", "content": "SECRET-PROMPT"}],
                           "tools": [{"name": "ToolSearch"}, {"name": "mcp__probe__analyze-work", "description": "d", "input_schema": schema}]})
        forwarder.note(body.encode(), probe.sha(probe.canonical(schema)))
        entry = forwarder.requests[0]
        self.assertTrue(entry["analyzeWork"]["inputSchemaEqualsServed"])
        self.assertNotIn("SECRET-PROMPT", json.dumps(forwarder.requests))
        forwarder.note(json.dumps({"tools": [{"name": "mcp__probe__analyze-work", "input_schema": {"type": "object"}}]}).encode(),
                       probe.sha(probe.canonical(schema)))
        self.assertFalse(forwarder.requests[1]["analyzeWork"]["inputSchemaEqualsServed"])


class VerdictTests(unittest.TestCase):
    def run_of(self, **extra) -> dict:
        base = {"prompt": "aim", "listedByHost": True, "connection": {"toolsList": [{"toolCanonicalSha256": "a", "matchesDefinition": True}]},
                "calls": [], "hostError": None, "toolSearchCalledBeforeAnalyzeWork": False, "apiRequests": None}
        return {**base, **extra}

    def test_billing_error_is_not_a_model_answer(self) -> None:
        result = verdict = probe.verdict({"runs": [self.run_of(hostError="Credit balance is too low")]})
        self.assertFalse(verdict["modelAnswered"])
        self.assertEqual(result["hostErrors"], ["Credit balance is too low"])
        self.assertEqual(result["callsConformToDeclaredSchema"], "0/0")

    def test_loading_is_eager_only_when_the_first_api_request_carries_the_tool(self) -> None:
        eager = {"firstRequestHadAnalyzeWork": True, "firstRequestIndexWithAnalyzeWork": 0}
        late = {"firstRequestHadAnalyzeWork": False, "firstRequestIndexWithAnalyzeWork": 1}
        self.assertEqual(probe.verdict({"runs": [self.run_of(apiRequests=eager)]})["loading"], "eager")
        self.assertEqual(probe.verdict({"runs": [self.run_of(apiRequests=late)]})["loading"], "deferred")


if __name__ == "__main__":
    unittest.main()
