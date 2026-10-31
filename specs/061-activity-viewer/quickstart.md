# SPEC-061 quickstart (planned behavior)

Nothing here works yet; this describes the planned VIS.1 commands.

```sh
# Replay the bundled example in a local browser
agent-braid view serve --replay examples/view/loom-replay.jsonl

# Watch a run directory and accept live host telemetry
agent-braid view serve --watch /path/to/run-root

# Record the session to an explicit new private file (effort only if asked)
agent-braid view serve --record ~/agent-braid-recordings/with-braid.loom.jsonl --record-effort

# Print host configuration to paste (writes nothing)
agent-braid view env --host claude
agent-braid view env --host codex

# Validate a loom file
agent-braid view validate session.loom.jsonl

# Export a recording without effort (default), or a comparative effort pack
agent-braid view export --from with-braid.loom.jsonl --to ~/agent-braid-exports/session-1
agent-braid view export --from with-braid.loom.jsonl --to ~/agent-braid-exports/pack-1 \
  --include-effort --baseline without-braid \
  --arm without-braid=without-braid.loom.jsonl --arm with-braid=with-braid.loom.jsonl \
  --arm-note "with-braid=same task and commit, run after the baseline"
```

The server binds to loopback only and prints a URL with a per-session token. It is
read-only, keeps effort data in memory and writes a file only when `--record` names
one.
