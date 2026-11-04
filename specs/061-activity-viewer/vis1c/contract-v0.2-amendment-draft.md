# Contract amendment draft: `agent-braid-loom/v0.2` (REQ-022, REQ-023)

**Status: draft for owner review (gate G3). Not accepted. Not applied.** The files
`contracts/loom-event.schema.json` and `contracts/ui-security-privacy.md` are not
edited by this change. On acceptance, T052 produces `loom-event.v0.2.schema.json`
(a new file; v0.1 stays valid and frozen), the matching amendment of
`ui-security-privacy.md`, and the validator and test changes below.

Owner decision D9 (2026-11-04) asked for `axis.nowMs`, `waitingOn` and tool
duration. All three are additive and optional; none carries content. Each passes the
privacy review below before any code is written.

## Compatibility rules

- v0.1 files and streams remain valid input; the viewer accepts v0.1 and v0.2.
- v0.2 adds optional members only. A v0.2 event that omits every new member is
  semantically a v0.1 event with a different `schemaVersion` string.
- The v0.1 schema is `additionalProperties: false` at the event level and inside each `data` object, so a v0.1-only
  validator refuses v0.2 events with new members. That is intended: a stale consumer
  must fail closed rather than ignore a field it does not understand. The viewer's
  `validate` command reports which version each event uses.
- The `executionAuthorization: false` constant, `source.verification` assignment by the
  viewer, and every assurance rule are unchanged.

## 1. `axis.nowMs` (snapshot, not an event)

| | |
|---|---|
| Location | the model/snapshot `axis` object (`view_model._time_axis` output) |
| Members | `nowMs` (integer, milliseconds, same monotonic basis as `relMs`, at least `maxMs`) and `live` (boolean) |
| Source | the viewer's monotonic clock started with the server, read when the snapshot is built; for replay `live = false` and `nowMs = maxMs` |
| Why | distinguishes "still running" from "lasted the whole time"; draws a real "now" marker; lets the UI grow an open lane in real time |
| Privacy review | R1: same basis and class as `relMs` ("Sub-day relative time" row of the deviation table); R2: carries no absolute time, so no clock correlation across sessions; R3: not exported by default (a recording stores events, not snapshots). Expected outcome: no new category. |
| Failure | absent in v0.1 snapshots; the UI falls back to the last event time and labels running state "(inferido)" |
| Tests | monotonic across snapshots in one session; replay `live=false`; never earlier than the last event; absent field handled |

## 2. `waitingOn` (event member)

| | |
|---|---|
| Location | optional member of `strand.update.data`, valid only when `state` is `waiting` |
| Value | one salted strand identifier (`HMAC-SHA256(sessionSalt, id)` truncated to 16 hex, the identifier class already allowed), or absent |
| Source | **not available from the Claude Code hooks pinned in T030** (they emit `PostToolUse` only and no "waiting for" signal). Sources that exist: scheduler and runtime adapters (a unit queued behind another), `ordered` crossings and wave order (prediction). A host that reports waiting would need its own probe. |
| Semantics | `waitingOn` from analysis or scheduler is "ordered by plan", not "observed waiting"; the field gets a sibling `waitingBasis` of `declared` or `observed`; the UI shows "esperando a X (según el plan)" or "(observado)". Hook-only sessions show state without a target. |
| Privacy review | R4: identifier class already permitted (salted, unlinkable across sessions); R5: no tool name, input or output; R6: must not be derivable from message text, so it is never parsed from a host string; R7: the target must be a known strand id of the same session, otherwise dropped with a `shape-unpinned` gap. Expected outcome: no new category. |
| Tests | refused when `state` is not `waiting`; refused when the target is unknown; not counted as clean; `declared` never drawn as `observed` |

## 3. Tool duration (event member)

| | |
|---|---|
| Location | optional `toolDurationMs` member of `strand.update.data` (the event that already carries `toolName`) |
| Value | integer, 0 to 86,400,000 ms; absent when the host does not report it |
| Sources, in order of preference | (a) OTLP `duration_ms` on a tool-result record: already on the canonical allowlist and already listed under "Exact durations" in the deviation table, but OTLP ingest is VIS.1b (T018, not built); (b) a duration member in the `PostToolUse` hook payload: **unverified**, needs the owner-run probe T053 (names of payload members only, never values, as T030 did); (c) none: derive nothing and label "intervalo entre eventos", never "duración" |
| Privacy review | R8: a duration is a number about a call, not its content; no `tool_input`, `tool_response`, path or argument is read (those names stay in the dropped-attribute inventory); R9: `tool_use_id` stays salted and is used only to pair a start with its result inside memory, never stored; R10: already inside the owner's "Exact durations" deviation (D4), so the tier is effort-like: memory only, omitted from default export, exported only as buckets with `--include-effort`; R11: a long duration can hint at what a tool did (a build versus a read); this is accepted for effort data and is why it is not in default exports; R12: no host payload member is added to the allowlist before T053 shows it exists. Decision OD-V4 sets replay retention. Expected outcome: no new never-collect category if retention stays as (a) in OD-V4; a wider retention needs an explicit owner decision. |
| Tests | member dropped when the host sends a string, negative or non-finite value; absent default export; unchanged dropped-attribute inventory; fixture with and without duration renders without inventing a value |

## 4. Observed collision (phase 4, separate review)

New event kind `collision.observed` (v0.2 only), not scheduled until the owner confirms
OD-V5.

| | |
|---|---|
| Data | `strandIds` (two salted ids), `resourceIds` (ids from the analysis resource table, no paths), `basis` (`ownership-receipt` or `ownership-notice`), optional `overlapFromMs` and `overlapToMs` |
| Source | existing ownership adapters (T013) first; hook-derived touches only after a separate probe and allowlist review (OD-V5 option b) |
| Rules | never emitted from a prediction; never counted with `crossing.classified: conflicting`; the viewer assigns `source.verification` as for every event; relative paths only via the existing `evidenceRef`; the UI shows no counter when the source is absent |
| Privacy review | R13: resource ids and strand ids only; R14: no file content, diff or absolute path; R15: the two agents' identities are already visible as lanes. Expected outcome: no new category, but the observation boundary (what "touched" means for each adapter) must be written in the contract before merge. |

## 5. Considered and refused

Goal or prompt text per agent, file path per tool call, tool input or output, absolute
timestamps, cost or token fields on `strand.update` (effort stays in `effort.sample`,
VIS.1b), a success outcome inferred from silence. These violate the never-retained
rules ("Never retained" list in `ui-security-privacy.md`) and are not proposals.

## Review checklist for G3 (owner or delegated reviewer)

1. Each new member is optional, bounded and typed; fail closed on malformed values.
2. The allowlist gains no host payload name unless T053 shows the name exists.
3. Nothing here stores or prints content, a path or an absolute time.
4. Retention and export of tool duration follow OD-V4 (default: memory only).
5. `executionAuthorization: false` and the verification rules are untouched.
6. v0.1 replays still load; the viewer says which version it read.
7. The spec's REQ-014 rule holds: host behaviour is recorded by probe, not assumed.

Evidence this draft does not provide: any host actually emitting these members; that
is T053 and the closure evidence.
