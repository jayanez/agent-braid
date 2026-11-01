# FC.1 milestone-level owner disposition: route (a), cancelled as infeasible (SPEC-034 to SPEC-037)

**Status: owner decision recorded 2026-10-31, route (a). Pending PR review and integration.**

On 2026-10-31 the owner (founder, jayanez) answered in the coordinator chat: "Cancelar por inviables" (cancel as infeasible), and chose a "Deferred" milestone for parking blocked work. The coordinator session relayed this answer to the drafting session by cross-session message. This is integrator-recorded provenance, not cryptographic authentication, and nothing beyond the quoted answer is inferred.

This file edits no task checkbox and no tracking file (`github-tracking.json`, `STATUS.md`, `ROADMAP.md`, `SPEC_MILESTONE_INDEX.md`); the tracking owner applies it after merge.
Modeled on [t005-disposition.md](t005-disposition.md) and the
[SPEC-045 T007 disposition](../045-local-forecasting-capabilities/t007-disposition.md).

## Situation

Milestone 18 (FC.1) holds issues #335 to #371 (37). Read from GitHub on 2026-10-31:
7 closed (#337, #339, #346, #347, #348, #349 completed synthetic software; #340
closed `not_planned`), and 30 open: 4 parents (#335, #344, #353, #363) plus 26
original tasks. This count includes all four parents; re-check at signing.

SPEC-034 T005 (#340) is cancelled-partial/infeasible by owner decision of
2026-10-16 ([t005-disposition.md](t005-disposition.md)). Its original criterion
stays unchecked ([tasks.md:25](tasks.md)) and every dependent stays unsatisfied.
The one approved native control failed under the unchanged 256 Git-request limit and
actual complete native bounds are unknown ([t005-disposition.md](t005-disposition.md),
[t005-disposition.md](t005-disposition.md) lines 7-9).

Direct dependents of T005: 034/T006 ([tasks.md:32](tasks.md)), 035/T006
([tasks 035:31](../035-chronos2-forecast-adapter/tasks.md)), 037/T003
([tasks 037:16](../037-forecast-advisory-integration/tasks.md)). Transitively this
blocks: 034/T007 and T008; 035/T007 and T008; 036/T001 (via 034/T007,
[tasks 036:6](../036-forecast-parallelism-experiment/tasks.md)), then 036/T002 to T009
(T003 also via 035/T007); 037/T002, T004 to T008. Not blocked by T005 itself:
034/T001, 034/T003 (needs separate source-window approval), 035/T001, 037/T001.
Even those lack a usable downstream path while T005 stays cancelled.

Exit clauses already in the specs:
- 036/T001 verification: "record a reviewed launch decision or infeasibility"
  ([tasks 036:7](../036-forecast-parallelism-experiment/tasks.md)).
- 036/T008 depends on "T007 or a recorded pre-launch infeasibility exit after T001"
  ([tasks 036:42](../036-forecast-parallelism-experiment/tasks.md)); an infeasible
  outcome is valid ([evaluation-protocol.md:151](../036-forecast-parallelism-experiment/evaluation-protocol.md),
  [spec 036 REQ-008](../036-forecast-parallelism-experiment/spec.md)).
- 037/T007 accepts "explicit no-go/defer" instead of positive utility
  ([tasks 037:36](../037-forecast-advisory-integration/tasks.md));
  research completion with an infeasible result can be recorded while promotion stays
  no-go ([promotion-proposal.md:23](../037-forecast-advisory-integration/promotion-proposal.md)),
  but implementation and founder-gate tasks are not to be closed without their
  actual evidence ([promotion-proposal.md:25](../037-forecast-advisory-integration/promotion-proposal.md)).
- 034/T007: absent usable data is infeasible, not permission to widen the workload
  domain ([tasks.md:38](tasks.md)).

## Route (a): cancel and exit as infeasible

Mechanism: signed pre-launch infeasibility record (036/T001 exit, then 036/T008 and
T009 on that outcome), then 037/T007 no-go and 037/T008 founder no-go; remaining
unlaunched tasks cancelled `not_planned` with hash-bound decision entries, as in the
precedents. Learned/forecast traffic stays shadow/off; SPEC-021 G4 NO-GO and M4
interpretation are unchanged; M3.5 stays separate.

**Open questions the founder must answer, because the current text does not settle
them:**
- Q1. 036/T001 and 037/T007 list dependencies (034/T007, 035/T001; 037/T006) that
  would be cancelled or unsatisfied. The T005 precedent keeps dependencies "unchanged
  and unsatisfied". Does the signed record explicitly authorize completing these
  exit tasks on the infeasibility basis without satisfying those dependencies?
- Q2. Are 035/T001 and 037/T001 (pure design reviews, no data) cancelled with the
  rest, or kept as standalone reviews outside FC.1? Drafted below as cancelled.
- Q3. Do the completed synthetic-software issues stay as is? Drafted: yes.
- Q4. Parents #335/#344/#353/#363 and milestone 18: drafted as open until a separate
  scope decision (precedent), not closed here.

## Route (b): reopen or amend SPEC-034 T005

Replaces the cancelled attempt with an explicit new decision. Reopens #340 (closed
`not_planned`) or opens a replacement under an amended criterion. Constraints
carried from the 2026-10-16 decision: it prohibited new executions and packages, and
allowed resumption only with an actual need and independently supported bounds; the
cancelled attempt must not be inherited as admission. So signing route (b) must
lift that prohibition in express words and name the new bounds.

T005 depends on T001 and T002 ([tasks.md:26](tasks.md)); T001 is still open, so the
review below comes first. SPEC-034 T001 would need
([tasks.md:5-7](tasks.md), [source-register.md:1-30](source-register.md)):
1. Exact source owners and permission receipts; repository visibility, code license
   and earlier lab-sync rights are insufficient.
2. Participant/privacy determination and metadata allowlist, with excluded content.
3. Target population and workload purpose; immutable workload/resource identities.
4. Consecutive source window, enumeration method, episode eligibility, clock and
   availability semantics, sampling grid, completeness check.
5. Storage/retention/redaction budget; revocation behavior; reviewed launch
   provenance as actually available (a hash is not a signature).
6. Local resource boundary review feeding T005: actual admitted slots, an
   independently supported complete native bound (the 256-request failure shows the
   old bound was inadequate), and a technical review. The offline correction from
   [t005-disposition.md](t005-disposition.md) is engineering evidence only.
7. Confirm whether amending T005's acceptance text needs an ADR under
   [GOVERNANCE.md](../../GOVERNANCE.md) (not verified in this draft).

Even after T001 and T005, FC.1 still needs at least (see the issue map for the full chain): capture hooks (034/T003) with a separate
source-window/operator approval, an approved prospective window (034/T006), yield
audit (034/T007), real Chronos-2 conformance and cost (035/T008, separate approved
provisioning and compute), the frozen registration (036/T001), and per-run operator
authority for the holdout (036/T007). None is authorized by this draft.

## Issue map (every FC.1 issue; route (b) column kept for the record, not selected)

Legend. Route (a): **DONE-A** completed on an infeasible/no-go basis, **CANCEL**
cancelled `not_planned`, **OPEN** stays open pending separate decision, **KEEP**
unchanged. Route (b): **REOPEN**, **NEXT** (first actionable review), **WAIT**
(stays open, blocked in dependency order), **KEEP**.

| Issue | Task | State now | Route (a) | Route (b) |
| --- | --- | --- | --- | --- |
| #335 | 034 parent | open | OPEN (Q4) | OPEN |
| #336 | 034/T001 | open | CANCEL | NEXT: source/privacy/resource review above |
| #337 | 034/T002 | closed | KEEP | KEEP |
| #338 | 034/T003 | open | CANCEL | WAIT (needs T001 plus separate operator approval) |
| #339 | 034/T004 | closed | KEEP | KEEP |
| #340 | 034/T005 | closed not_planned | KEEP (cancelled) | REOPEN or replace, after #336 |
| #341 | 034/T006 | open | CANCEL | WAIT (T003 T004 T005) |
| #342 | 034/T007 | open | CANCEL | WAIT (T006) |
| #343 | 034/T008 | open | CANCEL | WAIT (T007) |
| #344 | 035 parent | open | OPEN (Q4) | OPEN |
| #345 | 035/T001 | open | CANCEL (Q2) | NEXT (needs 034/T001 plus model/dependency/budget review) |
| #346 | 035/T002 | closed | KEEP | KEEP |
| #347 | 035/T003 | closed | KEEP | KEEP |
| #348 | 035/T004 | closed | KEEP | KEEP |
| #349 | 035/T005 | closed | KEEP | KEEP |
| #350 | 035/T006 | open | CANCEL | WAIT (needs 034/T005) |
| #351 | 035/T007 | open | CANCEL | WAIT (T006) |
| #352 | 035/T008 | open | CANCEL | WAIT (T007 plus approved compute) |
| #353 | 036 parent | open | OPEN (Q4) | OPEN |
| #354 | 036/T001 | open | DONE-A: infeasibility record (Q1) | WAIT (034/T007, 035/T001, exact source/compute review) |
| #355 | 036/T002 | open | CANCEL | WAIT (T001) |
| #356 | 036/T003 | open | CANCEL (offline engineering evidence retained, unchecked) | WAIT (T002, 035/T007) |
| #357 | 036/T004 | open | CANCEL | WAIT (T002, 037/T003) |
| #358 | 036/T005 | open | CANCEL | WAIT (T003 T004) |
| #359 | 036/T006 | open | CANCEL | WAIT (T005) |
| #360 | 036/T007 | open | CANCEL (never launched) | WAIT (T006, 034/T008, 035/T008, launch authority) |
| #361 | 036/T008 | open | DONE-A: pre-launch infeasible exit (Q1) | WAIT (T007 or later exit) |
| #362 | 036/T009 | open | DONE-A: founder interpretation of infeasible result | WAIT (T008) |
| #363 | 037 parent | open | OPEN (Q4) | OPEN |
| #364 | 037/T001 | open | CANCEL (Q2) | NEXT (034/T001, 035/T002 done) |
| #365 | 037/T002 | open | CANCEL | WAIT (T001, 035/T007) |
| #366 | 037/T003 | open | CANCEL | WAIT (034/T005, 035/T007) |
| #367 | 037/T004 | open | CANCEL (bridge stays deferred and unavailable) | WAIT (T003, SPEC-028/031 contract) |
| #368 | 037/T005 | open | CANCEL | WAIT (T002 T003) |
| #369 | 037/T006 | open | CANCEL | WAIT (T005) |
| #370 | 037/T007 | open | DONE-A: no-go/defer packet (Q1) | WAIT (T006, 036/T009) |
| #371 | 037/T008 | open | DONE-A: founder no-go record | WAIT (T007) |

Counts, route (a) if signed as drafted: 7 closed unchanged (six completed, #340
cancelled), 5 completed on an infeasible/no-go basis (#354, #361, #362, #370, #371;
original acceptance wording stays visible per the precedents), 21 cancelled, 4 parents
open. 7 + 5 + 21 + 4 = 37. Recount at signing.
Note: #361 was closed once before and shows as reopened; confirm its history at signing.
Route (b): no issue changes state except #340 reopen/replace; all others remain as
now, in dependency order.

## Tracking this would imply (for the tracking owner, after signing)

Route (a): decision record JSON, `task_cancellations` entries for each CANCEL row,
completion operations for each DONE-A row, milestone 18 description and counts;
parents and milestone stay open until the separate scope decision. Route (b):
decision record lifting the T005 prohibition, a `task_cancellations` change for
#340, new source and privacy review packet, no other change.

## Real-use evidence check (2026-10-31)

Per the owner's standing instruction (policy `docs/development/REAL_USE_EVIDENCE.md`, coordinator branch `docs/real-use-evidence-policy`, not yet in this tree), local sources were queried read-only before merge. Derived receipt only; no content, paths of private material or identities are committed. A receipt informs this decision; it grants nothing.

| Source | Observation |
| --- | --- |
| `~/.local/share/agent-braid/telemetry/metrics.sqlite3` | 66 aggregate cells over 3 days (2026-10-16, 10-24, 10-27): CLI/MCP calls of `analyze`, `analyze-git`, `analyze-work`, `execute`, with outcome, duration and classification buckets. Tables `batches`, `pending`, `losses` are empty. No workload series, resource counters, session/pair journals or forecast cells. (`agent-braid telemetry` CLI not runnable in this worktree under system Python 3.9; the file was read read-only with sqlite.) |
| `~/.local/share/agent-braid/evidence/{fc1,fc2}` | Engineering receipts (PR integration, CI logs, tracking audits, synthetic resource-cache and offline-profile repair, shadow/report PR logs, FC.2 selected-flow audits). No admitted source window or real workload series. |
| `~/.local/share/agent-braid/{coordination,identity,evidence/m45,...}` | M4.5 coordination and evidence, an account HMAC key; unrelated to a workload or forecast source. |
| `~/.local/state/agent-braid/forecast` | A locally cached Chronos checkpoint and a worker lease from the FC.2 synthetic conformance; no captured series. |
| `~/Library/Application Support/AgentBraid` | Plugin registry (3 workspaces) and result directories; no workload data. |
| `~/.claude/projects/**/*.jsonl` (2880 files), `~/.codex/sessions` (844 files) | Development transcripts. Keyword hits for forecast terms are discussions of building these specs, not captured workloads. No M3.5 shared-base session/pair feed and no SPEC-034 prospective window. Not mined for content. |

Result: no observation contradicts "no data path". No admitted or consented source window, no admitted resource profile and no eligible families or pairs were found. Limits: transcript content was not exhaustively read, and a transcript is not an authoring-boundary feed with rights, notice and completeness. If a source is later found, reopen under the criteria above.

## Adopted decision (2026-10-31)

- Route: **(a), cancel and exit as infeasible**. Route (b) was not selected.
- Q1 to Q4: not answered separately by the quoted answer. The issue map above is applied
  as drafted (Q1 exit basis for the five exit rows, Q2 design reviews cancelled, Q3
  synthetic software unchanged, Q4 parents handled below). The founder may amend any of
  these on PR review.
- Infeasibility exit and no-go record: this document is the recorded pre-launch
  infeasibility exit (036/T001, T008, T009) and the 037 no-go (037/T007, T008): no
  admissible source window, no admitted local resource profile (034/T005 cancelled), no
  executed holdout. Learned/forecast traffic stays shadow/off; SPEC-021 G4 NO-GO and M4
  interpretation are unchanged. No forecasting utility, source, model or promotion is accepted.
- Tracking mechanism: the repo supports only the hash-bound cancellation record
  (`not_planned`, criterion unchecked). The five exit rows (#354, #361, #362, #370, #371)
  therefore also get cancellation records stating their basis; no result artifact exists.
  Whether to use an evidence-backed completed override instead is the tracking owner's
  and founder's call on PR review.
- Parents #335/#344/#353/#363 and milestone 18: not decided by the quoted answer. The
  coordinator asked the tracking owner to close them after merge; the founder confirms on
  PR review. The "Deferred" milestone choice is recorded only as relayed; no issue is
  moved by this document.
- Hash-bound records: 26 files `tNNN-owner-disposition-2026-10-31.json` under
  `specs/034..037/evidence/` (`agent-braid-task-cancellation-v1`).
- Founder instruction reference: "Cancelar por inviables", coordinator chat, 2026-10-31.

This record is integrator-recorded provenance, not cryptographic authentication, as in
the cited precedents.
