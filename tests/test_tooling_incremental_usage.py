# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic controls for bounded incremental usage observations."""
import json
import unittest
from unittest.mock import patch

from agent_braid import tooling_incremental_usage as incremental


def line(event):
    return json.dumps(event, separators=(",", ":")) + "\n"


def claude(*events):
    return "".join(line(event) for event in events)


def partial(event, *, uuid=None, parent_tool_use_id=None, timestamp=None):
    wrapper = {"type": "stream_event", "event": event}
    if uuid is not None:
        wrapper["uuid"] = uuid
    if parent_tool_use_id is not None:
        wrapper["parent_tool_use_id"] = parent_tool_use_id
    if timestamp is not None:
        wrapper["timestamp"] = timestamp
    return wrapper


class IncrementalUsageTests(unittest.TestCase):
    def test_claude_chunked_usage_replaces_output_snapshots_and_ignores_placeholder(self):
        observer = incremental.IncrementalUsageObserver("claude")
        stream = claude(
            {"type": "system", "subtype": "init"},
            partial({"type": "message_start", "message": {
                "id": "msg-1", "usage": {"input_tokens": 18, "cache_read_input_tokens": 7,
                                             "cache_creation_input_tokens": 3, "output_tokens": 0}}}, uuid="e1",
                    timestamp="2026-10-09T12:00:00Z"),
            {"type": "assistant", "message": {"id": "msg-1", "usage": {"output_tokens": 1}}},
            partial({"type": "message_delta", "usage": {"output_tokens": 4}}, uuid="e2"),
            partial({"type": "message_delta", "usage": {"output_tokens": 9}}, uuid="e3",
                    timestamp="2026-10-09T12:00:02Z"),
            partial({"type": "message_stop"}, uuid="e4"),
            {"type": "result", "timestamp": "2026-10-09T12:00:03Z", "subtype": "success", "usage": {
                "input_tokens": 21, "cache_read_input_tokens": 8,
                "cache_creation_input_tokens": 3, "output_tokens": 9}, "total_cost_usd": 0.002},
        )
        snapshots = []
        for start in range(0, len(stream), 7):
            snapshots.extend(observer.feed(stream[start:start + 7]))
        report = observer.finish()

        self.assertEqual([item.output_tokens for item in snapshots if item.message_id == "msg-1"],
                         [None, 4, 9, 9])
        self.assertEqual(len(report.messages), 1)
        message = report.messages[0]
        self.assertEqual(message.input_tokens, 18)
        self.assertEqual(message.cache_read_input_tokens, 7)
        self.assertEqual(message.cache_creation_input_tokens, 3)
        self.assertEqual(message.output_tokens, 9)
        self.assertEqual(message.source_timestamp, "2026-10-09T12:00:02Z")
        self.assertTrue(message.message_stopped)
        self.assertEqual(report.state, "completed")
        self.assertTrue(report.whole_run_usage_known)
        self.assertEqual(report.terminal_usage.input_tokens, 21)
        self.assertEqual(report.terminal_usage.output_tokens, 9)
        self.assertEqual(report.terminal_usage.source_timestamp, "2026-10-09T12:00:03Z")
        self.assertTrue(report.complete_cost_eligible)
        self.assertFalse(report.subagent_usage_known)
        self.assertFalse(report.retry_usage_known)

    def test_claude_deltas_are_not_added_and_stale_regression_preserves_partial(self):
        observer = incremental.IncrementalUsageObserver("claude")
        observer.feed(claude(
            {"type": "system", "subtype": "init"},
            partial({"type": "message_start", "message": {"id": "m", "usage": {"input_tokens": 2}}}),
            partial({"type": "message_delta", "usage": {"output_tokens": 8}}),
            partial({"type": "message_delta", "usage": {"output_tokens": 8}}),
        ))
        with self.assertRaisesRegex(incremental.IncrementalUsageError, "regressed"):
            observer.feed(line(partial({"type": "message_delta", "usage": {"output_tokens": 7}})))
        report = observer.finish()
        self.assertEqual(report.messages[0].output_tokens, 8)
        self.assertEqual(report.state, "failed")
        self.assertFalse(report.complete_cost_eligible)
        self.assertFalse(report.whole_run_usage_known)

    def test_stale_delta_after_message_stop_is_rejected(self):
        observer = incremental.IncrementalUsageObserver("claude")
        observer.feed(claude(
            {"type": "system", "subtype": "init"},
            partial({"type": "message_start", "message": {"id": "m", "usage": {}}}),
            partial({"type": "message_stop"}),
        ))
        with self.assertRaisesRegex(incremental.IncrementalUsageError, "stale Claude message_delta"):
            observer.feed(line(partial({"type": "message_delta", "usage": {"output_tokens": 1}})))
        report = observer.finish()
        self.assertTrue(report.messages[0].message_stopped)
        self.assertIsNone(report.messages[0].output_tokens)
        self.assertFalse(report.complete_cost_eligible)

    def test_codex_never_invents_in_flight_zero_and_only_terminal_usage_is_exposed(self):
        observer = incremental.IncrementalUsageObserver("codex")
        observer.feed(line({"type": "thread.started"}) + line({"type": "turn.started"}))
        in_flight = observer.snapshot()
        self.assertEqual(in_flight.state, "streaming")
        self.assertIsNone(in_flight.terminal_usage)
        self.assertFalse(in_flight.whole_run_usage_known)
        self.assertFalse(in_flight.complete_cost_eligible)
        observer.feed(line({"type": "turn.completed", "usage": {
            "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 3,
            "reasoning_output_tokens": 1}}))
        report = observer.finish()
        self.assertEqual(report.state, "completed")
        self.assertTrue(report.whole_run_usage_known)
        self.assertEqual(report.terminal_usage.input_tokens, 0)
        self.assertEqual(report.terminal_usage.output_tokens, 3)
        self.assertIsNone(report.terminal_usage.estimated_cost_usd)
        self.assertFalse(report.complete_cost_eligible)

    def test_codex_turn_failed_never_exposes_cost_eligibility(self):
        observer = incremental.IncrementalUsageObserver("codex")
        observer.feed(line({"type": "thread.started"}) + line({"type": "turn.started"}))
        observer.feed(line({"type": "turn.failed"}))
        report = observer.finish()
        self.assertEqual(report.state, "failed")
        self.assertTrue(report.terminal_received)
        self.assertFalse(report.whole_run_usage_known)
        self.assertFalse(report.complete_cost_eligible)

    def test_claude_error_terminal_zero_usage_and_budget_crossing_are_not_complete(self):
        cases = (
            {
                "subtype": "error_during_execution",
                "usage": {"input_tokens": 0, "output_tokens": 0},
                "total_cost_usd": 0.0,
                "modelUsage": {"fixture-model": {"inputTokens": 12, "outputTokens": 7}},
            },
            {
                "subtype": "error_max_budget_usd",
                "usage": {"input_tokens": 11, "output_tokens": 2},
                "total_cost_usd": 0.8,
                "modelUsage": {"fixture-model": {"inputTokens": 12, "outputTokens": 30}},
            },
        )
        for result in cases:
            observer = incremental.IncrementalUsageObserver("claude")
            observer.feed(claude(
                {"type": "system", "subtype": "init"},
                partial({"type": "message_start", "message": {
                    "id": "partial", "usage": {"input_tokens": 5, "cache_read_input_tokens": 2}}}),
                partial({"type": "message_stop"}),
                {"type": "result", **result},
            ))
            report = observer.finish()
            with self.subTest(subtype=result["subtype"]):
                self.assertEqual(report.state, "failed")
                self.assertTrue(report.terminal_received)
                self.assertFalse(report.whole_run_usage_known)
                self.assertFalse(report.complete_cost_eligible)
                self.assertEqual(report.messages[0].input_tokens, 5)
                self.assertEqual(report.terminal_usage.estimated_cost_usd, result["total_cost_usd"])
                self.assertEqual(report.terminal_usage.output_tokens, result["usage"]["output_tokens"])

        # error_max_budget_usd may omit the response that crossed the budget;
        # aggregate modelUsage is intentionally not substituted for usage.
        budget_observer = incremental.IncrementalUsageObserver("claude")
        budget_observer.feed(claude(
            {"type": "system", "subtype": "init"},
            {"type": "result", "subtype": "error_max_budget_usd", "usage": {},
             "modelUsage": {"fixture-model": {"outputTokens": 30}}, "total_cost_usd": 0.8},
        ))
        budget = budget_observer.finish()
        self.assertIsNone(budget.terminal_usage.output_tokens)
        self.assertFalse(budget.whole_run_usage_known)
        self.assertFalse(budget.complete_cost_eligible)

    def test_subagent_stream_events_are_not_attributed_to_main_session(self):
        observer = incremental.IncrementalUsageObserver("claude")
        observer.feed(claude(
            {"type": "system", "subtype": "init"},
            partial({"type": "message_start", "message": {
                "id": "sub", "usage": {"input_tokens": 999}}}, parent_tool_use_id="parent"),
            partial({"type": "message_start", "message": {
                "id": "main", "usage": {"input_tokens": 4}}}),
        ))
        report = observer.snapshot()
        self.assertEqual(tuple(item.message_id for item in report.messages), ("main",))
        self.assertEqual(report.messages[0].input_tokens, 4)
        self.assertFalse(report.subagent_usage_known)

    def test_duplicate_event_uuid_and_duplicate_message_id_fail_closed(self):
        cases = (
            claude(
                {"type": "system", "subtype": "init"},
                partial({"type": "message_start", "message": {"id": "m", "usage": {}}}, uuid="same"),
                partial({"type": "message_delta", "usage": {"output_tokens": 2}}, uuid="same"),
            ),
            claude(
                {"type": "system", "subtype": "init"},
                partial({"type": "message_start", "message": {"id": "m", "usage": {}}}),
                partial({"type": "message_stop"}),
                partial({"type": "message_start", "message": {"id": "m", "usage": {}}}),
            ),
        )
        expected = ("duplicate event uuid", "duplicate Claude message id")
        for stream, reason in zip(cases, expected):
            observer = incremental.IncrementalUsageObserver("claude")
            with self.subTest(reason=reason), self.assertRaisesRegex(incremental.IncrementalUsageError, reason):
                observer.feed(stream)
            self.assertFalse(observer.finish().complete_cost_eligible)

    def test_malformed_duplicate_nonfinite_and_depth_keep_prior_message_counts(self):
        prefix = claude(
            {"type": "system", "subtype": "init"},
            partial({"type": "message_start", "message": {"id": "m", "usage": {"input_tokens": 5}}}),
        )
        invalid_lines = (
            '{"type":"assistant","type":"assistant"}\n',
            '{"type":"stream_event","event":{"type":"message_delta","usage":{"output_tokens":NaN}}}\n',
            '{"type":"assistant","nested":' + "[" * 40 + "0" + "]" * 40 + "}\n",
        )
        expected = ("invalid JSONL event", "invalid JSONL event", "nesting limit")
        for invalid, reason in zip(invalid_lines, expected):
            observer = incremental.IncrementalUsageObserver("claude")
            observer.feed(prefix)
            with self.subTest(reason=reason), self.assertRaisesRegex(incremental.IncrementalUsageError, reason):
                observer.feed(invalid)
            report = observer.finish()
            self.assertEqual(report.messages[0].input_tokens, 5)
            self.assertFalse(report.complete_cost_eligible)

    def test_truncated_or_cancelled_stream_keeps_observed_counts_without_cost_eligibility(self):
        prefix = claude(
            {"type": "system", "subtype": "init"},
            partial({"type": "message_start", "message": {"id": "m", "usage": {"input_tokens": 12}}}),
            partial({"type": "message_delta", "usage": {"output_tokens": 6}}),
        )
        truncated = incremental.IncrementalUsageObserver("claude")
        truncated.feed(prefix + '{"type":"res')
        partial_report = truncated.finish()
        self.assertEqual(partial_report.state, "failed")
        self.assertEqual(partial_report.messages[0].output_tokens, 6)
        self.assertFalse(partial_report.complete_cost_eligible)

        cancelled = incremental.IncrementalUsageObserver("claude")
        cancelled.feed(prefix + line(partial({"type": "message_stop"})) + line({
            "type": "result", "subtype": "success", "usage": {"input_tokens": 14, "output_tokens": 6},
            "total_cost_usd": 0.003,
        }))
        cancelled_report = cancelled.finish(exit_code=130)
        self.assertEqual(cancelled_report.state, "cancelled")
        self.assertEqual(cancelled_report.messages[0].input_tokens, 12)
        self.assertEqual(cancelled_report.terminal_usage.input_tokens, 14)
        self.assertFalse(cancelled_report.whole_run_usage_known)
        self.assertFalse(cancelled_report.complete_cost_eligible)

    def test_resource_limits_reject_and_preserve_previous_messages(self):
        prefix = claude(
            {"type": "system", "subtype": "init"},
            partial({"type": "message_start", "message": {"id": "m", "usage": {"input_tokens": 2}}}),
        )
        line_limited = incremental.IncrementalUsageObserver("claude")
        line_limited.feed(prefix)
        with self.assertRaisesRegex(incremental.IncrementalUsageError, "line limit"):
            line_limited.feed(b"x" * (incremental.MAX_LINE_BYTES + 1))
        self.assertEqual(line_limited.finish().messages[0].input_tokens, 2)

        event_limited = incremental.IncrementalUsageObserver("claude")
        with patch.object(incremental, "MAX_EVENTS", 1):
            with self.assertRaisesRegex(incremental.IncrementalUsageError, "event count limit"):
                event_limited.feed(claude({"type": "system", "subtype": "init"}, {"type": "assistant"}))
        self.assertFalse(event_limited.finish().complete_cost_eligible)

        byte_limited = incremental.IncrementalUsageObserver("claude")
        byte_limited.feed(prefix)
        with patch.object(incremental, "MAX_STREAM_BYTES", len(prefix.encode()) + 1):
            with self.assertRaisesRegex(incremental.IncrementalUsageError, "stream byte limit"):
                byte_limited.feed(b" " * 10)
        self.assertEqual(byte_limited.finish().messages[0].input_tokens, 2)


if __name__ == "__main__":
    unittest.main()
