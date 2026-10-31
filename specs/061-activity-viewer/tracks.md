# VIS derived tracks

The VIS track is independent of the core, M4.x and HAR and never gates them. VIS.1
is this specification. The later tracks are planned, not discarded; each opens its
own specification, ADR review where needed, GitHub milestone and Project entries
when the owner starts it. Every track inherits the
[UI, security and privacy contract](contracts/ui-security-privacy.md) and the
`agent-braid-loom/v0.1` contract (or a versioned successor).

| Track | Specification | Scope | Entry gate |
|---|---|---|---|
| VIS.1 | SPEC-061 | contract, adapters, loopback server, SSE, OTLP/JSON and hook ingest for Claude Code and Codex, replay, Three.js web viewer, frames, export, effort pack | ADR 0032 (and ADR 0033 for vendoring) |
| VIS.2 | SPEC-062 (planned) | Claude Code mod pane and hook automation | VIS.1 merged; T030 and T032 receipts; mod API status reviewed |
| VIS.3 | SPEC-063 (planned) | Codex MCP App and a terminal UI | VIS.1 merged; T031 and T033 receipts |
| VIS.4 | SPEC-064 (planned) | other hosts (Cursor, OpenCode, Pi, VS Code) | VIS.1 merged; per-host research |

## VIS.2 — Claude Code mod pane (SPEC-062)

- Companion mod in `integrations/agent-braid-view/claude-mod/`, outside the plugin
  package scan. Subscribes to `tool.call`, `agent.spawn`, `turn.*` and
  `session.measure`, posts loom lines to `/loom`.
- Pane: desktop draws `Svg` from `/frame.svg` (under the 131 072 character cap);
  terminal draws kitty graphics `Image` frames through shared memory and
  `$.ui.blit`, with `Raster` fallback.
- `agent-braid view install --host claude --scope user` previews and applies HTTP
  hook and OpenTelemetry settings with a receipt (pattern of `tooling install`).
- Open questions: mod API stability (early access), frame rate budget, shared
  memory on macOS, `claude plugin validate` and `claude plugin test` coverage.

## VIS.3 — Codex MCP App and terminal UI (SPEC-063)

- `mcp-app/loom-app.html`: one self-contained file with inline Three.js,
  `connectDomains` limited to the loopback origin, served by a `view_mcp.py` tool
  `loom-open` (MCP import only inside `create_server`, extra `tooling`).
- Codex hook shim and `notify` posting to the loopback server; rollout JSONL tail
  (cumulative `token_count` to deltas); transcripts as class 0 with `shape-unpinned`
  until SPEC-053 pins their shape.
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
