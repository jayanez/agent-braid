# ADR 0032: Read-only local activity viewer as an opt-in companion

- **Status:** proposed
- **Date:** 2026-10-31
- **Deciders:** Juan Antonio Yáñez García (owner)
- **Constitutional articles:** 0, 6, 11, 13, 14, 17, 18, 19, 20, 21, 22, 24
- **Specification:** [SPEC-061](../../specs/061-activity-viewer/spec.md) (track VIS.1)

## Context

Agent Braid computes pairwise classifications, compatibility classes, waves,
grants, ownership hazards and workflow-gate results, but exposes them only as JSON
artifacts and a static presentation (SPEC-043). Users of several Claude Code or
Codex agents cannot see what the agents do or what the coordination layer decided.
The hosts offer different surfaces: Claude Code exports OpenTelemetry, accepts HTTP
hooks and has an early-access mod API with panes; Codex exports OpenTelemetry, runs
command hooks and `notify`, and may render MCP Apps depending on the build; both
desktop clients are documented to show local web pages (unverified until host
verification). A Claude Code HTTP hook's response body is read like a command
hook's output, so a hook endpoint can take part in permission decisions.

ADR 0024 and ADR 0029 and the plugin package tests forbid hooks, mods, monitors,
agents and channels inside `integrations/agent-braid/`. The SPEC-047 telemetry
store collects only coarse aggregates, and the SPEC-057 never-collect list forbids
tokens, costs, exact durations, prompts and paths in telemetry about the SPEC-057
commands. The viewer writes no telemetry but holds several of these categories in
memory and, on explicit request, on disk; it records them as explicit deviations
rather than claiming the same minimization. Article 11 rejects visual metaphor
without semantics; Article 13 requires the compatibility class on analysis
results; Article 20 separates analysis from execution.

## Decision

1. Add an opt-in companion, the activity viewer, inside this repository:
   modules `agent_braid/view_*.py`, command group `agent-braid view`, and static
   assets under `integrations/agent-braid-view/`. It is never part of the
   `agent-braid` plugin package and never installed by it.
2. The viewer is read-only. It translates existing artifacts and allowlisted host
   telemetry into the versioned event contract `agent-braid-loom/v0.1`, where every
   event carries `executionAuthorization: false` and every crossing carries its
   compatibility class. No route or control has effects. Hook routes accept only
   observational events and answer with empty bodies, so the viewer never takes
   part in a host decision. Events are marked `rehashed`, `derived` or
   `unverified` by the viewer itself; replayed and host-reported events are
   unverified.
3. Network use is limited to one module (`view_serve.py`) that binds to loopback,
   separates a read credential (a one-time open code exchanged for a cookie) from
   an ingest credential (a bearer token in an owner-only file), keeps credentials
   out of URLs, logs and printed configuration, and refuses foreign `Host`,
   `Origin` and cross-site requests.
4. Effort data stays in process memory and is never written to the SPEC-047 store.
   A session is written to disk only when the user names a recording file, and
   effort is recorded only with a second explicit flag. Export reads such a file,
   is minimal by default, and includes effort only on request, labeled as host
   estimates with a non-claim statement. The categories held outside the
   never-collect list are listed in a deviation table for owner review.
5. Surfaces are selectable. VIS.1 implements the web viewer; Claude Code mod pane
   (VIS.2), Codex hooks, `notify`, MCP App and terminal UI (VIS.3) and other hosts
   (VIS.4) follow their own specifications. They keep this decision's authority,
   minimization and rendering rules; a new route, origin or credential needs its
   own boundary review.
6. The viewer never writes host configuration; it prints configuration for the
   user to paste into user-level settings.
7. Claim level (Article 17): inspiration. The braid picture is a structural analogy
   (Article 18) and a drawn swap or wave is never permission to interleave
   (Article 6).

## Alternatives considered

- **Mod, hooks or monitors inside the plugin package.** Rejected by ADR 0024/0029
  and the plugin tests; it would also make every plugin user carry the viewer.
- **Separate repository.** Rejected for now: the adapters depend on internal
  artifact shapes that change with the core; a companion in this repository keeps
  them tested together. It can be split later.
- **Hosted dashboard or remote collector.** Rejected: privacy, accounts, upload
  and cost.
- **Existing OpenTelemetry backends instead of a viewer.** Rejected for the
  coordination layer, which generic backends cannot show; adequate for generic
  token and cost views, which are not the viewer's purpose.
- **Persisting effort as telemetry.** Rejected: SPEC-047/057 boundaries.
- **Replay only.** Rejected by the owner: live ingest is part of VIS.1.

## Consequences

- Positive: the coordination layer becomes visible and inspectable down to the
  evidence hash; one stream unifies Braid artifacts, Claude Code and Codex.
- Negative: a local HTTP server and static web assets enter the repository; a new
  contract must be maintained; the vendored renderer needs ADR 0033.
- Uncertain: host telemetry shapes and the mod and MCP Apps surfaces may change;
  host verification receipts gate every documentation claim.
- Compatibility: additive; no existing contract or output changes.
- Security: loopback, separate read and ingest credentials, header checks, body,
  connection and timeout limits, CSP with trusted types, attribute allowlist,
  salted identifiers, no prompts, empty hook responses, exclusive file creation.
  Residual risk: exporters and hooks send full payloads to the loopback port
  before the viewer drops fields, and a process holding that port while the
  viewer is down receives them.
- Research: Q-VIS1 (does the braid shorten locating hazards) is an open question,
  not a hypothesis.

## Validation

SPEC-061 procedures 001–015, governance and plugin package regression tests, the
`activity-viewer` validation rule, and owner-run host verification receipts. The
decision is revisited at the SPEC-061 go/no-go checkpoint after the coordination
slice (artifact census and descriptive observation), if a host offers an official
visualization surface that makes the companion redundant, or if the boundary tests
cannot be kept.

## References

- [SPEC-061](../../specs/061-activity-viewer/spec.md)
- [UI, security and privacy contract](../../specs/061-activity-viewer/contracts/ui-security-privacy.md)
- [ADR 0024: native AI plugins](0024-native-ai-plugins.md)
- [ADR 0029: Claude dynamic workflows](0029-claude-dynamic-workflows.md)
- [Telemetry](../tooling/TELEMETRY.md)
