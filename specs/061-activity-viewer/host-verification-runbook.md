# SPEC-061 host verification runbook

Owner-run probes. Each needs the owner's authorization for that probe, runs on the
owner's machine with the owner's accounts, and writes one receipt
`evidence/hv-<task>-<yyyymmdd>.json` with: task, host and version, operating
system, command or steps, expected outcome, observed outcome (`verified`,
`not-matching`, `unobserved`), raw excerpts with secrets and content removed, and
limits. A receipt changes only the matching row of the surfaces matrix.

## T030 — Claude Code OpenTelemetry attribute names

1. Start `agent-braid view serve` and note the printed endpoint.
2. Run `agent-braid view env --host claude` and export the printed variables in a
   new shell (`CLAUDE_CODE_ENABLE_TELEMETRY=1`, OTLP HTTP/JSON exporter, endpoint).
3. Run one short Claude Code session that starts one subagent.
4. Read the dropped-attribute names inventory and the allowlisted names from
   `/snapshot` (names only, never values) and compare them with the allowlist.
   Expected: token, cost, model, agent and parent-agent identifiers.

## T031 — Codex OpenTelemetry export shape

1. Paste the `[otel]` block printed by `view env --host codex` into a test profile.
2. Run one short `codex exec` turn.
3. Read metric, log and attribute names from `/snapshot` (names only). Expected:
   token usage per turn. Pin the exact names in the allowlist through a reviewed
   change.

## T032 — Claude desktop browser pane loads the viewer

1. Start `view serve --replay examples/view/loom-replay.jsonl`.
2. Open the printed URL in the Claude desktop browser pane.
3. Record whether the scene, table view and evidence panel load with no CSP
   violation, no console error and no outbound request.

## T033 — Codex Desktop MCP Apps

1. Using a minimal MCP App fixture (no Agent Braid data), check whether the
   installed Codex Desktop renders an MCP App resource.
2. Record `verified` or `unobserved`. `unobserved` is a valid outcome and keeps
   VIS.3 on the browser fallback.
