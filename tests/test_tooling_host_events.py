# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic parser controls; these are not receipts from real host sessions."""
import json
import unittest

from agent_braid.tooling_host_events import HostEventError, parse_host_events


def lines(*events):
    return "".join(json.dumps(event, separators=(",", ":")) + "\n" for event in events)


class HostEventParserTests(unittest.TestCase):
    def test_codex_completed_mcp_tool_and_usage(self):
        report = parse_host_events("codex", lines(
            {"type": "thread.started", "thread_id": "synthetic"},
            {"type": "turn.started", "turn_id": "synthetic"},
            {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "fixture", "tool": "analyze", "status": "completed"}},
            {"type": "turn.completed", "usage": {"input_tokens": 100, "cached_input_tokens": 20, "output_tokens": 10, "reasoning_output_tokens": 3}},
        ), version="0.162.0-alpha.2", expected_mcp_servers=("fixture",))
        self.assertEqual(report.state, "completed")
        self.assertEqual(report.observed_tools, ("fixture/analyze",))
        self.assertEqual(report.input_tokens, 100)
        self.assertIsNone(report.estimated_cost_usd)

    def test_claude_init_cost_and_tool_observation(self):
        report = parse_host_events("claude", lines(
            {"type": "system", "subtype": "init", "model": "fixture-model", "mcp_servers": [{"name": "fixture", "status": "connected"}], "mcp_server_errors": []},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "mcp__fixture__analyze"}]}},
            {"type": "result", "subtype": "success", "usage": {"input_tokens": 10, "cache_read_input_tokens": 2, "output_tokens": 4}, "total_cost_usd": 0.001, "result": "synthetic"},
        ), version="2.1.286", expected_model="fixture-model", expected_mcp_servers=("fixture",))
        self.assertEqual(report.state, "completed")
        self.assertEqual(report.observed_tools, ("mcp__fixture__analyze",))
        self.assertEqual(report.estimated_cost_usd, 0.001)
        self.assertIn("not invoice", report.cost_basis)

    def test_execution_error_zero_totals_are_unknown_after_prior_usage(self):
        for count in (0, 17):
            with self.subTest(reported_count=count):
                report = parse_host_events("claude", lines(
                    {"type": "system", "subtype": "init", "model": "m", "mcp_servers": [], "mcp_server_errors": []},
                    {"type": "assistant", "message": {"usage": {"input_tokens": 17}, "content": []}},
                    {"type": "result", "subtype": "error_during_execution", "usage": {
                        "input_tokens": count, "cache_read_input_tokens": count, "output_tokens": count},
                     "total_cost_usd": 0 if count == 0 else 0.1},
                ), version="2.1.286", expected_mcp_servers=())
                self.assertEqual(report.state, "failed")
                for field in ("input_tokens", "cached_input_tokens", "output_tokens", "estimated_cost_usd", "cost_basis"):
                    self.assertIsNone(getattr(report, field))
                self.assertTrue(any("crash" in limit for limit in report.limits))

    def test_budget_error_keeps_host_cost_estimate_but_not_incomplete_usage(self):
        report = parse_host_events("claude", lines(
            {"type": "system", "subtype": "init", "model": "m", "mcp_servers": [], "mcp_server_errors": []},
            {"type": "result", "subtype": "error_max_budget_usd", "usage": {
                "input_tokens": 10, "cache_read_input_tokens": 2, "output_tokens": 4},
             "total_cost_usd": 0.2},
        ), version="2.1.286", expected_mcp_servers=())
        self.assertEqual(report.state, "failed")
        self.assertIsNone(report.input_tokens)
        self.assertIsNone(report.cached_input_tokens)
        self.assertIsNone(report.output_tokens)
        self.assertEqual(report.estimated_cost_usd, 0.2)
        self.assertIn("not invoice", report.cost_basis)
        self.assertTrue(any("budget-crossing" in limit for limit in report.limits))

    def test_claude_empty_mcp_expectation_and_mismatch_control(self):
        init = {"type": "system", "subtype": "init", "model": "m",
                "mcp_servers": [], "mcp_server_errors": []}
        result = {"type": "result", "subtype": "success", "usage": {}}
        empty = parse_host_events("claude", lines(init, result), version="2.1.286",
                                  expected_mcp_servers=())
        self.assertEqual(empty.state, "completed")
        unexpected = {"type": "system", "subtype": "init", "model": "m",
                      "mcp_servers": [{"name": "extra", "status": "connected"}],
                      "mcp_server_errors": []}
        mismatch = parse_host_events("claude", lines(unexpected, result), version="2.1.286",
                                     expected_mcp_servers=())
        self.assertEqual(mismatch.state, "failed")
        disconnected = {"type": "system", "subtype": "init", "model": "m",
                        "mcp_servers": [{"name": "wanted", "status": "failed"}],
                        "mcp_server_errors": []}
        status_mismatch = parse_host_events("claude", lines(disconnected, result), version="2.1.286",
                                            expected_mcp_servers=("wanted",))
        self.assertEqual(status_mismatch.state, "failed")

    def test_codex_refuses_observed_mcp_call_outside_expected_set(self):
        with self.assertRaisesRegex(HostEventError, "outside the expected set"):
            parse_host_events("codex", lines(
                {"type": "thread.started"}, {"type": "turn.started"},
                {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "extra", "tool": "read"}},
                {"type": "turn.completed", "usage": {}}),
                version="0.162.0-alpha.2", expected_mcp_servers=())

    def test_omitted_mcp_expectation_reports_unknown_scope(self):
        report = parse_host_events("codex", lines(
            {"type": "thread.started"}, {"type": "turn.started"},
            {"type": "turn.completed", "usage": {}}), version="0.162.0-alpha.2")
        self.assertEqual(report.state, "completed")
        self.assertTrue(any("Expected MCP server inventory was omitted" in item for item in report.limits))

    def test_old_claude_version_refuses_isolation_claim(self):
        with self.assertRaisesRegex(HostEventError, "before 2.1.286"):
            parse_host_events("claude", "{}\n", version="2.1.285")

    def test_mcp_init_error_wins_even_with_success_result(self):
        report = parse_host_events("claude", lines(
            {"type": "system", "subtype": "init", "model": "m", "mcp_servers": [], "mcp_server_errors": [{"name": "fixture", "error": "bad config"}]},
            {"type": "result", "subtype": "success", "usage": {}, "result": "apparently done"},
        ), version="2.1.286")
        self.assertEqual(report.state, "failed")
        self.assertEqual(report.error, "MCP server initialization error")

    def test_nonzero_exit_and_incomplete_stream_are_not_success(self):
        failed = parse_host_events("codex", lines(
            {"type": "thread.started"}, {"type": "turn.started"}, {"type": "turn.completed", "usage": {}}),
            version="0.162.0-alpha.2", exit_code=1)
        self.assertEqual(failed.state, "failed")
        cancelled = parse_host_events("claude", lines(
            {"type": "system", "subtype": "init", "model": "m", "mcp_servers": [], "mcp_server_errors": []}),
            version="2.1.286", exit_code=130)
        self.assertEqual(cancelled.state, "cancelled")
        with self.assertRaisesRegex(HostEventError, "truncated"):
            parse_host_events("codex", '{"type":"thread.started"}', version="0.162.0-alpha.2")

    def test_duplicate_keys_nonfinite_and_unknown_events_refuse(self):
        for stream in ('{"type":"thread.started","type":"turn.completed"}\n',
                       '{"type":"turn.completed","usage":{"input_tokens":NaN}}\n',
                       '{"type":"mystery"}\n'):
            with self.subTest(stream=stream), self.assertRaises(HostEventError):
                parse_host_events("codex", stream, version="0.162.0-alpha.2")

    def test_depth_nonfinite_and_overflowing_cost_are_bounded(self):
        deeply_nested = '{"type":"thread.started","x":' + "[" * 40 + "0" + "]" * 40 + "}\n"
        with self.assertRaisesRegex(HostEventError, "nesting limit"):
            parse_host_events("codex", deeply_nested, version="0.162.0-alpha.2")
        with self.assertRaises(HostEventError):
            parse_host_events("codex", '{"type":"thread.started","x":1e999}\n', version="0.162.0-alpha.2")
        huge_cost = '{"type":"system","subtype":"init","model":"m","mcp_servers":[],"mcp_server_errors":[]}\n' \
            '{"type":"result","subtype":"success","usage":{},"total_cost_usd":' + "9" * 5000 + "}\n"
        with self.assertRaises(HostEventError):
            parse_host_events("claude", huge_cost, version="2.1.286")

    def test_codex_requires_ordered_initialization_turn_and_last_terminal(self):
        completed = {"type": "turn.completed", "usage": {"input_tokens": 2}}
        with self.assertRaisesRegex(HostEventError, "start with thread.started"):
            parse_host_events("codex", lines(completed), version="0.162.0-alpha.2")
        with self.assertRaisesRegex(HostEventError, "final event"):
            parse_host_events("codex", lines(
                {"type": "thread.started"}, {"type": "turn.started"}, completed,
                {"type": "item.completed"}), version="0.162.0-alpha.2")
        positive = parse_host_events("codex", lines(
            {"type": "thread.started"}, {"type": "turn.started"},
            {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "f", "tool": "t"}},
            completed), version="0.162.0-alpha.2")
        self.assertEqual(positive.state, "completed")

    def test_claude_requires_init_first_and_result_last(self):
        init = {"type": "system", "subtype": "init", "model": "m", "mcp_servers": [], "mcp_server_errors": []}
        result = {"type": "result", "subtype": "success", "usage": {}}
        with self.assertRaisesRegex(HostEventError, "start with system/init"):
            parse_host_events("claude", lines(result, init), version="2.1.286")
        with self.assertRaisesRegex(HostEventError, "final event"):
            parse_host_events("claude", lines(init, result, {"type": "assistant"}), version="2.1.286")
        positive = parse_host_events("claude", lines(init, {"type": "assistant"}, result), version="2.1.286")
        self.assertEqual(positive.state, "completed")

    def test_usage_counters_are_bounded_signed_64_bit_values(self):
        stream = lines({"type": "thread.started"}, {"type": "turn.started"},
                       {"type": "turn.completed", "usage": {"input_tokens": 10**4000}})
        with self.assertRaisesRegex(HostEventError, "between 0 and"):
            parse_host_events("codex", stream, version="0.162.0-alpha.2")

    def test_signal_exit_discards_terminal_usage(self):
        report = parse_host_events("codex", lines(
            {"type": "thread.started"}, {"type": "turn.started"},
            {"type": "turn.completed", "usage": {"input_tokens": 10}}),
            version="0.162.0-alpha.2", exit_code=-2)
        self.assertEqual(report.state, "cancelled")
        self.assertIsNone(report.input_tokens)
        self.assertIsNone(report.estimated_cost_usd)
        failed = parse_host_events("claude", lines(
            {"type": "system", "subtype": "init", "model": "m", "mcp_servers": [], "mcp_server_errors": []}),
            version="2.1.286", exit_code=-9)
        self.assertEqual(failed.state, "failed")
        self.assertIsNone(failed.output_tokens)


if __name__ == "__main__":
    unittest.main()
