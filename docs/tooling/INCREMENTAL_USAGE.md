# Incremental host usage observations

`agent_braid.tooling_incremental_usage.IncrementalUsageObserver` accepts
caller-supplied UTF-8 JSONL chunks. It buffers at most one bounded incomplete
line and emits frozen snapshots only after a full line has been parsed. It
does not launch a host, authenticate a stream, inspect credentials, or alter the
capture or supervisor contract.

For Claude Code, the observer reads the raw `message_start`, `message_delta`,
and `message_stop` values inside `stream_event` records. Each message snapshot
retains the source message ID and source timestamp when supplied. Input, cache
read, and cache creation counters come from that message's `message_start`;
output comes from `message_delta`. A later output counter replaces the earlier
snapshot for the same message, so repeated cumulative updates are never added.
Assistant-message `usage.output_tokens` is ignored because it can be a
placeholder. Nested events carrying a non-null `parent_tool_use_id` are not
assigned to the main session.

Codex usage is exposed only from `turn.completed`; in-flight state keeps all
terminal counters unknown rather than inventing zeroes. A Claude `result` or
Codex `turn.completed` can expose the fields in that host's terminal usage
object. The observer never derives a terminal aggregate by summing per-message
snapshots. Omitted counters remain `None` even when a terminal event is present.
This module covers the existing CLI JSONL streams only. Codex App Server's
`thread/tokenUsage/updated` is a separate cumulative response-scope event and
does not expose retry completeness; it requires a separate source-scoped
adapter before it can be observed here.

`whole_run_usage_known` means a successful process ended with a successful
terminal record and a host-reported terminal usage object. It is a source scope,
not proof that every retry or subagent was individually captured or attributed;
those flags remain false in this observer. Claude's `complete_cost_eligible`
requires that same successful terminal path and a finite non-negative
`total_cost_usd` reported by the result. This is only the host estimate, not an
invoice or an authenticated accounting record. Codex does not expose a cost
field here, so cost stays unknown.

Unsuccessful Claude results remain partial even when they contain zero-valued
usage or cost fields. In particular, `error_during_execution` can report zero
usage after a process failure, and `error_max_budget_usd` can omit the response
that crossed the budget while its `modelUsage` or cost fields include aggregate
values. The observer retains the selected `usage` and cost fields for diagnosis,
but does not treat error terminals or `modelUsage` as complete run accounting.

Malformed JSON, duplicate object keys or event UUIDs, duplicate message IDs,
stale/regressing deltas, out-of-order events, invalid counters, non-finite
numbers, truncation, cancellation, and resource-limit violations fail closed.
Any message snapshots and terminal values already observed remain available in
the final report, but failed, truncated, or cancelled streams cannot qualify
for complete-cost eligibility. Synthetic unit fixtures exercise these
boundaries; this module does not provide live capture evidence.
