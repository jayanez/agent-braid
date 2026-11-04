# Contract v0.2 privacy review (gate G3, T052)

Review of the items R1 to R15 of the
[contract v0.2 amendment draft](contract-v0.2-amendment-draft.md), done on 2026-11-04
under the owner's G3 authorisation ("Sí, ambas (Recommended)", recorded in
[owner-decisions.md](owner-decisions.md#gate-answers-recorded-2026-11-04-second-session-verbatim))
and the accepted decisions OD-V4 (a) and OD-V5 (a). The reviewer is the implementing
agent; this record is a written verdict per item, not a founder approval, and the owner
can reopen any verdict. Evidence boundary: the verdicts are checked against the code and
tests of this change and the receipts named below, not against a running host.

Verdicts: **accepted** (published in v0.2 as stated), **accepted, enforced later** (the
rule is written in the contract and is implemented by the named task), **held** (the
condition is not yet met; nothing is published for it), **deferred** (not in v0.2).

## Outcome

`agent-braid-loom/v0.2` is published with `strand.update.toolDurationMs`,
`strand.update.waitingOn` and `strand.update.waitingBasis`, all optional
([schema](../contracts/loom-event.v0.2.schema.json),
[contract amendment](../contracts/ui-security-privacy.md#contract-v02-amendment-2026-11-04-t052)).
`axis.nowMs` and `axis.live` are snapshot members described in the contract and are
implemented by T060. `collision.observed` is deferred. No never-collect category is
added, no host payload name enters the allowlist, `executionAuthorization: false` and the
verification rules are unchanged, and v0.1 input stays valid.

## Verdicts

| Item | Subject | Verdict | Reason and where it is enforced |
|---|---|---|---|
| R1 | `axis.nowMs` basis | accepted | Same monotonic basis and class as `relMs` ("Sub-day relative time" row). Implemented by T060; this change only writes the rule. |
| R2 | no absolute time in `nowMs` | accepted | `nowMs` is a relative millisecond count from the server's monotonic start; no wall clock is read or sent, so it cannot correlate sessions. |
| R3 | `nowMs` not exported | accepted | It belongs to the snapshot, not to an event; recordings and exports store events only. No recorder or exporter exists yet; the rule is in the contract for when they do. |
| R4 | `waitingOn` identifier class | accepted | Validated as the existing identifier pattern (short id or `sha256:` digest); adapters salt it like every strand id. Tests: `ContractV02Tests` (`target is a path` is refused). |
| R5 | no tool name, input or output in `waitingOn` | accepted | The member holds one identifier and nothing else; `strand.update` stays a closed object, so an extra member is refused (`unknown member` test). |
| R6 | never parsed from message text | accepted, enforced later | The identifier pattern refuses free text. That no adapter derives it from a host string is an adapter rule for T061 and is written in the contract. |
| R7 | target must be a strand of the same session | accepted, enforced later | The validator refuses a strand waiting on itself (event-level). Whether the target exists is a stream-level fact: T061's adapter drops an unknown target with one `shape-unpinned` gap, as the contract now says. |
| R8 | duration is a number, not content | accepted | `toolDurationMs` is an integer 0 to 86,400,000; strings, floats, booleans, null, negatives and values over a day are refused by both the validator and the schema. No `tool_input`, `tool_response`, path or argument is read; the dropped-attribute inventory is unchanged. |
| R9 | `tool_use_id` pairing in memory only | accepted, enforced later | The contract carries no pairing identifier; any start-to-result pairing is in adapter memory (T062). The allowlist already salts `tool_use_id`. |
| R10 | retention tier | accepted | OD-V4 (a): memory only. Stricter than the draft's "buckets with `--include-effort`": the contract amendment says no recording or export carries it, with or without the effort flags. A replayed stream loses the member on load (`view_serve.replay_events`; test `test_a_v02_replay_loads_and_drops_tool_duration`). |
| R11 | a long duration hints at the kind of work | accepted | The residual inference (a build versus a read) is the same as for the existing "Exact durations" row; it is why the value stays out of every file. |
| R12 | no host payload name before the probe shows it | held, then met by T062 (2026-11-04) | Nothing is added to the allowlist in v0.2. The T030 receipt (`evidence/hv-t030-20261101.json`, Claude Code 2.1.292) already lists the member name `duration_ms` in `PostToolUse` payloads and none in `SubagentStop`, but did not record its JSON type. The T053 run of 2026-11-04 was `unobserved` (see `evidence/hv-t053-20261104.json`). T062 may pin `PostToolUse.duration_ms` only after the owner accepts the T030 name evidence or a rerun records the type; until then the viewer derives nothing and labels the interval between events as such. Update 2026-11-04 (T062): the owner accepted the T030 name evidence ("Aceptar T030"); `duration_ms` enters the hook allowlist for `PostToolUse` only, with a strict integer check (bool, float, string, negative and over a day are dropped with one `shape-unpinned` gap). Rationale: the name is observed on the same host version, the value is a number with no content, and retention stays memory only (R10). |
| R13 | collision: resource and strand ids only | deferred | Acceptable in principle (identifier and resource-id classes only). Not published: the draft requires the per-adapter observation boundary ("what touched means") to be written in the contract before merge, and that is T063's work against the ownership-receipt and ownership-notice adapters (OD-V5 (a)). |
| R14 | collision: no content, diff or absolute path | deferred | Same as R13; when added, paths stay limited to the existing relative `evidenceRef`. |
| R15 | collision: agent identities already visible | deferred | Same as R13; the lanes already show the two strands, so no new identity category arises. |

## Checklist for G3 (from the draft)

| # | Check | Result |
|---|---|---|
| 1 | each new member optional, bounded, typed; fail closed on malformed values | met (`ContractV02Tests.test_malformed_new_members_fail_closed_in_both`) |
| 2 | no host payload name added unless a probe shows it | met (R12 held; allowlist unchanged) |
| 3 | nothing stores or prints content, a path or an absolute time | met for v0.2 members |
| 4 | tool duration retention follows OD-V4 | met (R10; replay drop tested) |
| 5 | `executionAuthorization: false` and verification rules untouched | met (`EVENT_SPEC` unchanged except the version enum) |
| 6 | v0.1 replays still load; the viewer says which version it read | met (`view validate` prints a count per version; v0.1 corpus and example tests) |
| 7 | host behaviour recorded by probe, not assumed | met (T053 receipt records `unobserved`, not an assumed member) |

## Not covered

Any host actually emitting these members; the UI use of the fields (T060 to T064); the
observed-collision kind (T063); whether the T030 name evidence is enough to pin
`duration_ms` (owner decision, see R12).
