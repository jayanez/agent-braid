# GitHub tracking history

Dated, per-milestone and per-task records moved verbatim from
[GITHUB_TRACKING.md](GITHUB_TRACKING.md), which keeps the procedure. These are
historical observations of the stated dates, not current instructions; the current
state is in [github-tracking.json](github-tracking.json).

## Task overrides and cancellations

Moved from the *Source of truth and stable IDs* section.

  `SPEC-004/T005` retains an unchecked checkbox in the frozen public export.
  Its documented override cites the two same-commit agent reports bound by
  `specs/004-m0-closure/founder-review.json` and the approved M0 closure;
  this reconciles historical tracking without changing the published source
  record or making a new review decision.
  `SPEC-011` T001–T007 are checked against [merged PR #3](https://github.com/jayanez/agent-braid/pull/3);
  T008 and human review remain open.

  SPEC-045/T007's [adopted disposition](../../specs/045-local-forecasting-capabilities/t007-disposition.md)
  retains seven completed FC.2 tasks and one cancelled/partial task. Issue/Project
  readback is separate; a generic Project Done value is administrative.
  SPEC-034/T005's [adopted disposition](../../specs/034-workload-forecast-data/t005-disposition.md)
  adds one FC.1 cancellation while retaining six completed and 26 open original
  tasks after reconciliation. Its original criterion remains unchecked and its
  dependencies remain unsatisfied; parent and milestone states stay open.

  The [Deferred triage of 2026-11-26](deferred-triage-20261126.md) (frozen record,
  SHA-256 `ce21e5d6f0e24d3e4dba3be0c0426e6ac734537d3a90f5fb4a0ab6dba85c938c`)
  cancels ten more tasks as not planned: SPEC-033 T001, T005, T007 and SPEC-077
  T001, T003–T007, T009. Each has its own decision file in
  [deferred-triage-20261126-cancellations](deferred-triage-20261126-cancellations/)
  that cites the record, because a cancellation binding is one JSON file per task.
  SPEC-077's parent closes as `not_planned` through the spec-level `state_reason`
  (ADR 0043 is Rejected). SPEC-041/T008 is rescued into M4.5 through a
  `task_milestone_overrides` entry and M4.5 is reopened for it (owner, 2026-11-26).

## Historical milestone aliases

Moved from *Milestone names and identity*.

The naming migration preserves these historical aliases:

| GitHub number | Previous title | Canonical title |
|---|---|---|
| 1 | M0 | M0 — Operational foundations |
| 2 | M0.5 | M0.5 — Open strategy and preview preparation |
| 3 | M1 | M1 — Observable interaction analyzer |
| 4 | M2 | M2 — Confluence lab and scheduler |
| 5 | M3 | M3 — Braid semantics |
| 6 | M4 | M4 — Agent Braid runtime |
| 7 | Public research preview | PUB.1 — Public research preview |
| 8 | Cross-cutting governance | GOV.1 — Governance and adoption |
| 9 | M3.5 | M3.5 — Native proposal predictor |
| 10 | Platform evidence adapters | ADP.1 — Recorded-trace adapters |
| 11 | Workload evidence laboratory | LAB.1 — Effectful workload lab |
| 12 | Formal interaction research | RES.1 — Formal interaction research |
| 13 | S1.0 — Contracts | S1.0 — Decision contracts |
| 14 | S1.1 — Evidence | S1.1 — Decision evaluation |
| 15 | S1.2 — Native model | S1.2 — Native decision model |
| 16 | S1.3 — Integration | S1.3 — Advisory integration |
| 17 | S1.4 — Product and promotion | S1.4 — Product capabilities and promotion |

## M3.5 software closure and experimental exception — 2026-10-10

M3.5 has six closed software tasks (T002, T004, T006, T008, T009, T010).
The four open tasks (T007, T001, T003, T005) are the source-admission,
preregistration/annotation, fit/evaluation and evidence/review phases of the
[deferred experiment](../../specs/019-native-predictor/software-completion.md).
SPEC-019/#180 and milestone 9 remain explicitly open for that experiment.
No source or scientific gate is closed by synthetic software or technical review.

The private Project was inspected through the owner's existing authenticated
browser session on 2026-10-10: all eleven records were present, the six closed
tasks were **Done**, and the four experimental tasks were **Todo**. The parent
was corrected from **Todo** to the configured **Review pending**. This is a
bounded UI observation, separate from repository issue reconciliation; no token
permissions were expanded. See the [alignment record](m35-project-alignment.md)
for the final source/remote audit and documentation boundary.

## Unpublished SPEC-047/M4.5 extension

The local telemetry delivery prepares one SPEC-047 parent and T001–T010, plus SPEC-044/T017/T018, assigned to existing milestone #19. [Local drafts](../../specs/047-local-technical-telemetry/issue-drafts.md) have stable markers and derived source states. SPEC-044/T004 incorporates a previously approved bounded documentary closure with [pinned provenance](../../specs/044-ai-tooling-evaluation/t004-bounded-closure-reconciliation.json); no reproduction or fresh acceptance is inferred. Local source preparation does not update remote issues or Project state.

After separately authorized review/integration, scope the audit to milestone 19 and allowlist only the exact missing new records: SPEC-047, SPEC-047/T001 through SPEC-047/T010, SPEC-044/T017 and SPEC-044/T018. Confirm actual inventory first; the allowlist must omit IDs that already exist. Preserve the digest-bound audit/apply/readback procedure and require no pending scoped operations after eventual publication. Private Project verification stays separate. No audit/apply or remote write is authorized by these drafts.

The [exact milestone #19 description draft](../../specs/047-local-technical-telemetry/milestone-description-draft.md) is local and unpublished. Existing synchronizer title/state/issue audit does not cover description drift; eventual publication needs its own reviewed guarded update and readback, without broadening the current no-write scope.

## VIS.1 activity viewer extension

SPEC-061 declares the new track milestone `VIS.1 — Activity viewer`, one open
parent and T001–T039 in the source inventory, and adds SPEC-061 to Project
**Review pending**. Nothing is published by the specification change. After merge
to `develop`, from a clean checkout of `develop`, scope the audit to the new
milestone, review the plan (one milestone, one parent, 39 task issues and their
sub-issue links), apply it with the reviewed digest, record the assigned number in
`milestone_numbers`, and re-audit until no operation remains. Then set the parent
to **Review pending** in [Project 6](https://github.com/users/jayanez/projects/6)
and check the *Specs and tasks*, *By milestone* and *By status* views. VIS.1a and
VIS.1b are deliveries inside this one milestone (the tracking source assigns one
milestone per specification). VIS.2–VIS.4
get milestones only when their specifications exist.

Published 2026-11-01: milestone #25 (registered by PR #808), parent SPEC-061 as
issue #810 in **Review pending**, and 39 task issues linked as its sub-issues; the
scoped re-audit planned no operations. After the T001 owner review was accepted on
2026-11-01, SPEC-061 left `project_review_pending` and the parent moved to **Todo**,
as for SPEC-060.

## S1.5 System One shadow activation

SPEC-066 declares the track milestone `S1.5 — System One shadow activation`, one
open parent and its task inventory, and adds SPEC-066 to Project **Review pending**.
The milestone was created on GitHub on 2026-11-01 as #26 and registered in
`milestone_numbers`. After the registering change merges to `develop`, from a clean
checkout of `develop`, scope the audit to #26 with `--new-record-key` for SPEC-066
and each missing `SPEC-066/Txxx`, review the plan (one parent, its task issues and
sub-issue links, and closed states for completed tasks), apply it with the
reviewed digest, and re-audit until no operation remains. Then set the parent to
**Review pending** in [Project 6](https://github.com/users/jayanez/projects/6).

Fifteen open Deferred task issues move to #26 by owner decision R6 (OD-5) through
the top-level `task_milestone_overrides` member of `github-tracking.json` (SPEC-066
T003): SPEC-029 T001-T009 (#285-#293), SPEC-031 T008 (#311) and SPEC-033 T002,
T003, T004, T006 and T008 (#323-#325, #327, #329). The member's rules are in the procedure ([GITHUB_TRACKING.md](GITHUB_TRACKING.md)).

The same member also pins 45 closed System One task issues (SPEC-028, SPEC-029
T010 onward, SPEC-031, SPEC-032 and SPEC-033) to the closed historical milestone
they already sit in on GitHub, by the owner default approved 2026-11-01, so the
scoped Deferred audit no longer fails with `selected issue ... moved from registered
milestone #24`.

Procedure after the override change merges to `develop`, from a clean checkout of
`develop`. Both scoped audits fail closed while the 15 issues still sit in Deferred
(#26 reports `selected issue ... moved from registered milestone #26`, #24 reports
them as out of scope), and a full-scope apply would also carry unrelated drift from
other tracks. So move exactly the 15 issues with `gh issue edit <number> --milestone
'S1.5 — System One shadow activation'` and read each back, then run the scoped audit
for #26 (with `--new-record-key` for any SPEC-066 record not yet published) and for
#24, review each plan, apply it with its reviewed digest, and re-audit both until no
operation remains. Publish the SPEC-066 records into #26 before this change merges,
or only after the manual move, because the scoped #26 audit fails closed in between.
Update the #26 and #24 descriptions to the source text by hand, as the procedure
says, and read them back. Deferred keeps its reopen condition: SPEC-029
T001 source permissions granted and admitted real groups greater than zero
(third-party sources), or SPEC-066 REQ-101 admission (the owner's own sources).

Published 2026-11-02: milestone #26 (registered by PR #897), parent SPEC-066 as
issue #900 in **Review pending**, its task issues linked as sub-issues, and the 15
absorbed issues moved from Deferred after PR #940; the scoped #26 re-audit planned no
operation and both milestone descriptions match the source. The scoped Deferred #24
audit still stops on `SPEC-041/T002`, a closed task sitting in M4.5; that belongs to
the SPEC-041 owner, not S1.5.
