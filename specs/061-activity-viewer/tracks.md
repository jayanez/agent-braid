# VIS derived tracks

The VIS track is independent of the core, M4.x and HAR and never gates them. VIS.1
is this specification, delivered as VIS.1a and VIS.1b with a go/no-go checkpoint
(T035) between them. The later tracks are planned; each may be re-scoped or closed
as Deferred only by an owner decision recorded at a checkpoint, and each opens its
own specification, ADR review where needed, GitHub milestone and Project entries
when the owner starts it. Every track keeps the authority, minimization and
rendering rules of the [UI, security and privacy contract](contracts/ui-security-privacy.md)
and the `agent-braid-loom/v0.1` contract (or a versioned successor). A track that
adds a route, an origin or a credential needs its own boundary review.

| Track | Specification | Scope | Entry gate |
|---|---|---|---|
| VIS.1 | SPEC-061 | contract, adapters, loopback server, SSE, OTLP/JSON ingest for Claude Code and Codex, observational Claude Code HTTP hooks, replay, Three.js web viewer, frames, export, effort pack | ADR 0032 (and ADR 0033 for vendoring) |
| VIS.2 | SPEC-062 (planned) | Claude Code mod pane | T035 records keep for VIS.2; T030 and T032 receipts; mod API status reviewed |
| VIS.3 | SPEC-063 (planned) | Codex hooks and `notify`, Codex MCP App and a terminal UI | T035 records keep for VIS.3; T031 and T033 receipts |
| VIS.4 | SPEC-064 (planned) | other hosts (Cursor, OpenCode, Pi, VS Code) | T035 records keep for VIS.4; per-host research |

Decided in T001 (2026-11-01): SPEC-062 to SPEC-064 and their milestones are
written only after T035 records keep for the track. Until then each probe receipt
(T030–T033) adds its findings to the matching section below, so the later
specification starts from observed host behavior.

## VIS.2 — Claude Code mod pane (SPEC-062)

- Companion mod in `integrations/agent-braid-view/claude-mod/`, outside the plugin
  package scan. Observes `tool.call`, `agent.spawn`, `turn.*` and
  `session.measure` only: every handler passes the event on unchanged and returns
  no decision (ADR 0029 rejected enforcing `agent.spawn` mods). Sending events to
  the viewer needs a new ingest route with its own credential and `unverified`
  status, specified in SPEC-062.
- Pane: desktop draws `Svg` from `/frame.svg` (under the 131 072 character cap);
  terminal draws kitty graphics `Image` frames through shared memory and
  `$.ui.blit`, with `Raster` fallback.
- Host configuration stays printed by `view env` for the user to paste; the viewer
  never writes host configuration. Any installer would need an amended contract
  and its own ADR.
- Open questions: mod API stability (early access), frame rate budget, shared
  memory on macOS, `claude plugin validate` and `claude plugin test` coverage.

## VIS.3 — Codex MCP App and terminal UI (SPEC-063)

- `mcp-app/loom-app.html` served by a `view_mcp.py` tool `loom-open` (MCP import
  only inside `create_server`, extra `tooling`). The app iframe has a foreign
  `Origin` that the VIS.1 contract refuses, and inlining Three.js leaves the ADR
  0033 boundary: SPEC-063 needs its own boundary decision and, if it inlines
  vendored code, an ADR 0033 amendment.
- Codex hook shim and `notify` command that posts to the loopback server with the
  ingest token and always exits 0 with empty output; rollout JSONL tail
  (cumulative `token_count` to deltas); transcripts as observations without a
  compatibility class, with `shape-unpinned` until SPEC-053 pins their shape.
- `view_tui.py` curses UI: scrub, crossing filter, effort toggle, quit.
- Open questions: MCP Apps support per Codex build; app-server multi-client use
  alongside a live TUI.

## VIS.4 — Other hosts (SPEC-064)

- Research per host: MCP and MCP Apps support, OpenTelemetry export, hooks or
  JSONL logs. Fill rows of `contracts/surfaces-matrix.json` with receipts.
- Reuse the loopback viewer first; add host-native surfaces only where an observed
  API exists.

## Single-writer files

`docs/STATUS.md`, `ROADMAP.md`, `docs/development/SPEC_MILESTONE_INDEX.md` and
`docs/development/github-tracking.json` are edited only by the main VIS thread,
never by parallel track sessions.
