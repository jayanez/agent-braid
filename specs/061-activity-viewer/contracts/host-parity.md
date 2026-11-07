<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Host parity contract (SPEC-061 VIS.1e, T076, REQ-029)

**Status:** draft contract, not adopted by a host adapter. It maps what Claude Code, Codex and
OpenCode emit to the existing `agent-braid-loom` events, and says per host which of those signals
are provided, absent or unknown. It does not change `agent-braid-loom/v0.1` (frozen) or v0.2, adds
no route, no allowlist entry and no code. Admitting a host source stays gated by an owner-run
probe (T077, T078) and a privacy review (T079); ingest is built at T080 and T081.

The machine-readable table is `hostParity` in [surfaces-matrix.json](surfaces-matrix.json);
`tests/test_view_host_parity.py` keeps the two in step. The loom events are those of
[loom-event.schema.json](loom-event.schema.json) (v0.1) and
[loom-event.v0.2.schema.json](loom-event.v0.2.schema.json); the privacy rules are those of
[ui-security-privacy.md](ui-security-privacy.md). Everything below is observational: every event
carries `executionAuthorization: false`, and a lane, bead, duration or label is not a guarantee,
not a safety ordering and not permission to run, schedule or interleave work.

## Host-neutral mapping

One host signal becomes at most one loom event. The viewer, not the host, stamps `at`, `source`
and the assurance block, as the Claude Code hook adapter does today.

| Capability | Loom event | Data written | Since |
|---|---|---|---|
| `session.open` | `strand.open` | `role: agent`, `parentStrandId: null`, label `<Host> session` | v0.1 |
| `session.close` | `strand.close` | the session strand; its open subagent strands close first | v0.1 |
| `subagent.open` | `strand.open` | `role: subagent`, `parentStrandId` = the session strand, label = the host's agent type else `<Host> subagent` | v0.1 |
| `subagent.close` | `strand.close` | the subagent strand | v0.1 |
| `tool.call` | `strand.update` | `state: running`, `toolName` (a bounded name, never an input or output) | v0.1 |
| `tool.duration` | `strand.update` | `toolDurationMs`, an integer from 0 to 86,400,000, only when the host states it | v0.2 |
| `waiting` | `strand.update` | `state: waiting`, with `waitingOn` and `waitingBasis` together | v0.2 |
| `turn.idle` | `strand.update` | `state: idle` (the lane is not closed) | v0.1 |
| `outcome` | `strand.close` | `outcome` `ok`, `failed` or `cancelled` when the host states it, else `unknown` | v0.1 |

Rules that hold for every host:

1. **Identifiers are hashed.** A host-native session or agent id never leaves the adapter: the
   strand id is a per-instance salted HMAC over the kind and the id. New adapters include the host
   name in the hashed input so equal ids from two hosts cannot meet; the existing Claude Code
   input is unchanged.
2. **A lane opens on the first event that names it** when the host sends no start signal
   (observed for Claude Code under `claude -p`). A lane that was closed stays closed; an event that
   would continue it is not shown as activity, and one `shape-unpinned` gap says so. A repeated end
   signal changes nothing.
3. **Labels only.** Session and subagent labels are the closed text of the loom contract. Prompts,
   messages, tool inputs and outputs, paths, working directories, transcripts, model text and
   account fields are never read. Each host allowlist records names, never values, in its probe
   receipt, and keeps only the fields the table needs.
4. **Decision events are refused.** Whatever a host can block, approve or rewrite (permission,
   pre-tool, prompt-submit and stop-style events, command hooks included) is refused with no
   stored effect, and every observational route answers with an empty body, so the viewer takes
   no part in a host decision and never blocks the host. A stop-style signal is therefore not a
   source of `turn.idle` unless a host offers one that is observational; that is decided per host
   at its probe and privacy review.
5. **Same input, same page.** Two hosts that deliver the same logical facts (two sessions, one
   subagent, one stated tool call) yield the same lanes, branches, beads and labels, except for
   the host name inside the default labels (SC-029, tested at T083). The host is carried in the
   event source and changes no lane, branch, bead or label rule.
6. **Durations are stated, not inferred.** `toolDurationMs` comes only from a host-stated tool
   duration. The time between two events, an API request duration or a total session time is never
   turned into a tool duration.
7. **A waiting signal needs a stated basis.** `waitingBasis` is `declared` (the host says it) or
   `observed` (the viewer saw a pending state); nothing else makes a lane wait.

## Absent, not zero

A capability whose value is `absent` or `unknown` for a host is shown for that host as not
provided: no empty lane, no bead count of 0, no duration label, no "0 waiting", no flat bar (a missing capability is never drawn as zero). A
count that depends on a missing capability is omitted and never shown as zero, in the page, in
`view stats` (T084) and in the usage telemetry counts. `unknown` means no probe has observed the
host either way, `absent` means a probe or this contract's policy rules the signal out; both
render the same on the page (not provided) and differ only in this table and in
`docs/tooling/VIEWER.md`. The page never turns `unknown` into `provided` or `absent` by
guessing from another host.

## Capability table

Values: `provided` (a receipt observed the host emitting a signal that maps to the capability),
`absent` (a receipt observed it missing, or a policy of this contract rules it out for every
admitted source), `unknown` (neither). Basis: `receipt`, `policy`, `derived` (the viewer derives
it from another event) or `none`.

| Capability | Claude Code | Codex | OpenCode |
|---|---|---|---|
| `session.open` | provided (derived from the first event; no HTTP `SessionStart` delivered) | provided (`codex.conversation_starts`, partial receipt) | unknown |
| `session.close` | provided (`SessionEnd`) | unknown | unknown |
| `subagent.open` | provided (`SubagentStart`, `agent_id`) | unknown | unknown |
| `subagent.close` | provided (`SubagentStop`) | unknown | unknown |
| `tool.call` | provided (`PostToolUse`, `tool_name`) | unknown | unknown |
| `tool.duration` | provided (`PostToolUse.duration_ms`) | unknown | unknown |
| `waiting` | absent (policy) | unknown | unknown |
| `turn.idle` | absent (policy: `Stop` is refused) | unknown | unknown |
| `outcome` | absent (hook payloads state none) | unknown | unknown |

Evidence per cell is in the matrix: Claude Code 2.1.292 under `claude -p` only
([hv-t030](../evidence/hv-t030-20261101.json)); Codex `codex-cli 0.166.0-alpha.5.1`, `codex exec`,
where no turn completed because of an account usage limit, so only transport and start names were
seen ([hv-t031](../evidence/hv-t031-20261101.json)); OpenCode has no probe. Names can change
between host versions, and a cell holds for the version and client of its receipt only. The
`tool.duration` name for Claude Code was observed at T030; its JSON type was accepted by owner
decision when T053 closed, and the T053 probe itself recorded `unobserved`.

Claude Code OpenTelemetry carries no agent id, so subagent attribution comes from hooks only;
Codex and OpenCode attribution is decided at their probes. Plan maps from `analyze-work` reports
and result-root discovery are already host-neutral and are not part of this table.

## Open items for later tasks

These are recorded here so nobody assumes them done; none is decided by this contract.

- **T077 (Codex probe) and T078 (OpenCode probe)** fill `unknown` cells from receipts: names of
  hooks, `notify` and `[otel]` events for session start and end, subagent, tool call and duration.
  A completed Codex turn is needed first (the T031 account limit).
- **T079 (privacy review, owner gate)** approves each host's field allowlist before any value is
  read. Until it passes, no Codex or OpenCode route may store a value.
- **T080 and T081 (ingest)** may need schema additions this contract does not make: an adapter
  name for OpenCode (the adapter list has `codex-notify` and `codex-hook` but none for OpenCode)
  and, if wanted, a host value other than `other`. Either is an additive amendment decided at
  those tasks, together with the route entry in the route table.
- **ADR 0037** (OpenCode native plugin) says the plugin has no hooks and no event subscriptions.
  T081 may let the plugin post to the viewer only if the probe finds no in-process alternative,
  and that needs its own decision; this contract assumes a viewer-side path.
- **Waiting and idle for Claude Code** are `absent` for the five admitted events. Admitting a
  notification-style event needs its own probe and privacy review and would change those cells.
