# SPEC-061 quickstart

Updated 2026-11-05 (VIS.1d). The commands in the first block work today; the second
block is planned for VIS.1b and does not exist yet. The user guide is
[docs/tooling/VIEWER.md](../../docs/tooling/VIEWER.md).

```sh
# Start the viewer (loopback only); it prints a single-use link to open
agent-braid view serve

# Replay a recorded loom stream, or watch a run directory
agent-braid view serve --replay specs/061-activity-viewer/contracts/loom-event.example.jsonl
agent-braid view serve --watch /path/to/run-root

# Print a new single-use link for another browser while the viewer runs
agent-braid view open

# Print Claude Code hook settings to merge into ~/.claude/settings.json (writes nothing)
agent-braid view env --host claude --port <port printed by serve>

# Validate a loom file
agent-braid view validate session.loom.jsonl
```

What the page shows: a Now sentence and KPI tiles (running, waiting, may collide,
longest stated tool call), the live loom (one thread per Claude Code session and
subagent on a real time axis), a plan map per `analyze-work` report (operations in
dependency order and their classified pairs, with no time axis), collision and
duration panels, the details rail, playback, and an Explore 3D view of the same lanes.

Planned (VIS.1b, not available):

```sh
agent-braid view env --host codex
agent-braid view serve --record ~/agent-braid-recordings/with-braid.loom.jsonl --record-effort
agent-braid view export --from with-braid.loom.jsonl --to ~/agent-braid-exports/session-1
```

The server binds to loopback only and prints a one-time URL that the browser
exchanges for a session cookie; `view open` asks the running server, with an
owner-only token file, for another single-use code. Host hooks use a separate ingest
token read from an owner-only file at every call, so they need no environment
variable and work in the desktop app and IDE launches. The viewer is read-only and
writes no file other than its own tokens.
