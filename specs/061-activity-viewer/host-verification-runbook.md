# SPEC-061 host verification runbook

Owner-run probes. Each needs the owner's authorization for that probe, runs on the
owner's machine with the owner's accounts, and writes one receipt
`evidence/hv-<task>-<yyyymmdd>.json` with: task, host and version, operating
system, command or steps, expected outcome, observed outcome (`verified`,
`not-matching`, `unobserved`; `not-matching` sets the matrix status
`not-matching`), raw excerpts with secrets and content removed, and
limits. A receipt changes only the matching row of the surfaces matrix.

Outcomes apply at two levels. Each check in a receipt records `verified`,
`not-matching` or `unobserved`. A `not-matching` check on an expected field or
event, while the ingest path itself delivers data, narrows the allowlist and is
pinned through the reviewed change of the task that implements that path; it does
not change the matrix row. The receipt outcome and the matrix status follow the
ingest paths: only a `not-matching` transport or ingest path sets the row
`not-matching` and removes that path from VIS.1. A probe that observes no data
for its expected outcome records `unobserved`: if it will be rerun (for example
after a usage limit) the row stays `hv-pending` and the task stays open; a final
`unobserved` sets the row `unobserved`. For surface probes without an ingest path
(T032, T033) the receipt outcome follows the surface's load and render checks,
and any other check left `unobserved` is recorded in the receipt and the matrix
note.

These probes run before any viewer code exists. They use a throwaway
standard-library listener on loopback that records only the names of the fields it
receives and answers every request with an empty body; it is not committed.

## T030 — Claude Code OpenTelemetry attribute names and hook responses

1. Start the throwaway listener on a loopback port.
2. In a new shell, set `CLAUDE_CODE_ENABLE_TELEMETRY=1`, the OTLP HTTP/JSON
   exporter and the loopback endpoint with an authorization header; add
   observational HTTP hook entries (`SessionStart`, `SessionEnd`,
   `SubagentStart`, `SubagentStop`, `PostToolUse`) in a throwaway user-level
   settings profile.
3. Run one short Claude Code session that starts one subagent and uses one tool;
   confirm the tool call proceeds normally while the listener answers hooks with
   empty bodies, and again with the listener stopped.
4. Record the content type and the names (never values) at each OTLP level and in
   each hook payload. Expected: OTLP JSON with token, cost, model, agent and
   parent-agent identifiers; tool calls unaffected.

## T031 — Codex OpenTelemetry export shape

1. Put an `[otel]` block targeting the throwaway listener with JSON over HTTP into
   a test profile.
2. Run one short `codex exec` turn.
3. Record the content type and the metric, log and attribute names (names only).
   Expected: token usage per turn. Pin the exact names in the allowlist through a
   reviewed change.

## T032 — Claude desktop browser pane loads a loopback page

1. Serve a static fixture page (one module script, one import map, a WebGL2
   canvas) from the throwaway listener with the contract headers.
2. The owner opens it in the Claude desktop browser pane by hand; no agent drives
   the pane, because page text could enter a model's context.
3. Record whether the page loads with no CSP violation, no console error and no
   outbound request, and whether WebGL2 is available. The real viewer is opened
   again at the T035 checkpoint.

## T033 — Codex Desktop MCP Apps

1. Using a minimal MCP App fixture (no Agent Braid data), check whether the
   installed Codex Desktop renders an MCP App resource.
2. Record `verified` or `unobserved`. `unobserved` is a valid outcome and keeps
   VIS.3 on the browser fallback.
