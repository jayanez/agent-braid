# Host event parser boundary

`agent_braid.tooling_host_events.parse_host_events` reads a completed, caller-
supplied JSONL stream and exit status. It does not start Codex or Claude Code,
select flags, authenticate, persist sessions, enforce a remote budget or attest
that an input came from a real host. Unit-test fixtures are explicitly synthetic
and are not host receipts.

The parser accepts Codex CLI `0.162.0` or newer and Claude Code `2.1.286` or
newer. The current planning observations named Codex `0.162.0-alpha.2` and
Claude `2.1.285`; the latter is deliberately refused for isolated comparison
because its `--bare` behavior is not sufficiently isolated. A compatible Claude
capture must use a new session and `--bare`; a resumed transcript may include
prior conversation history in its result totals. This module cannot verify those
launch conditions, so the report retains them as limits. A newer version is
accepted only for recognized event shapes; the report explicitly marks forward
compatibility unverified.

For Codex, the parser recognizes the documented `codex exec --json` JSONL
events and records `thread.started`, MCP tool-call items, `turn.completed` usage,
`turn.failed`, and `error`. Input, cached input, output and reasoning output
tokens remain separate and are bounded to signed 64-bit non-negative values.
The required sequence is one `thread.started`, one `turn.started`, zero or more
items, then one terminal turn/error event as the final line. Tool names are
deduplicated observations, not invocation counts. The CLI event source defines
typed MCP items and turn usage fields; the public CLI guide also describes JSONL
output.

For Claude Code, it recognizes the narrow headless stream shape used by this
integration: one leading `system`/`init`, optional assistant/user events, and one
terminal `result` as the final line. `expected_mcp_servers=None` means no
inventory expectation was supplied and leaves that scope explicitly unknown;
an empty tuple means the capture expects zero configured servers. When an
expectation is supplied, Claude init must include both the MCP inventory and
error fields, the inventory must match exactly, and every listed server must be
connected. Non-empty `mcp_server_errors` fails the observation even when a later
result says success. `total_cost_usd` is retained as the host's
estimated cost, never called an invoice or billed amount. A missing cost stays
unknown. Exact Claude CLI event schemas and fields are not fully specified by
the public CLI reference; the supported field set here is an integration
contract requiring confirmation against the selected real CLI version before
host compatibility can be claimed.

Both parsers reject malformed JSONL, duplicate keys, non-finite numbers,
truncation, excessive byte/line/event/depth bounds, unknown event types,
ambiguous terminal events, and malformed usage or tool evidence. A clean terminal
event alone does not override a nonzero exit code or initialization error. No
monetary Codex cost is inferred from token counts; no hard remote budget guarantee
is asserted. Negative process return codes are treated as signal termination:
SIGINT/SIGTERM map to cancellation, other signals to failure, and partial token
and cost totals are discarded as unknown. Unsupported ordering or missing stream
initialization refuses the input instead of reporting completion.
For Codex, a supplied expected server tuple checks each observed MCP call against
that set, including refusing all MCP calls when the expected set is empty. Codex
JSONL has no configured-server initialization inventory, so configured servers
that were never called remain unknown. With no expectation (`None`), both hosts
report the expected inventory scope as unknown. `observed_tools` lists unique
tool names and is not a count of invocations.

Documentation references:

- [Codex CLI `exec --json` source](https://github.com/openai/codex/blob/main/codex-rs/exec/src/exec_events.rs)
- [Codex CLI reference](https://developers.openai.com/codex/cli/reference)
- [Claude Code CLI reference](https://code.claude.com/docs/en/cli-reference)
- [Claude Code Agent SDK overview](https://code.claude.com/docs/en/agent-sdk/overview)

Claude execution-error results can reset usage and cost after a crash. The parser
therefore leaves their complete totals unknown, even when the result reports zero
or another numeric value. Budget-error `usage` can omit the response that crossed
the limit: token totals remain unknown while `total_cost_usd`, when present, stays
a separately labelled host estimate. Assistant message placeholders cannot repair
complete output, retry or subagent totals. These limits follow the official
[Claude cost-tracking documentation](https://code.claude.com/docs/en/agent-sdk/cost-tracking);
the parser still does not authenticate provider data or perform a capture.
