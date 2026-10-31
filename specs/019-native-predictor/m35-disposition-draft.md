# M3.5 (SPEC-019) cancellation-or-deferral decision draft

**Status: DRAFT for founder decision. UNSIGNED. No decision is adopted, inferred or
recorded by this file.** Nothing here edits a task checkbox, closes an issue, or
changes `docs/development/github-tracking.json`, `STATUS.md`, `ROADMAP.md` or
`SPEC_MILESTONE_INDEX.md`; tracking owners apply an adopted option only after the
decision fields below are signed. Evidence below supports only its stated domain: a
bounded, owner-only source screen. It does not show that no suitable source exists.

Modeled on [SPEC-034 T005](../034-workload-forecast-data/t005-disposition.md) and
[SPEC-045 T007](../045-local-forecasting-capabilities/t007-disposition.md), whose
hash-bound `task_cancellations` entries are in
[github-tracking.json](../../docs/development/github-tracking.json) (section
`task_cancellations`).

## Why a decision is needed

Synthetic software is complete (T002, T004, T006, T008, T009, T010 closed; issues #182,
#184, #186, #187, #222, #223). Four phases of one deferred real-workload experiment
remain open: T007/#188, T001/#181, T003/#183, T005/#185, under parent #180 and
milestone 9. The bounded review found zero eligible families and zero admitted pairs
([spec.md:69](spec.md), [source-audit.md:41](source-audit.md),
[source-audit.md:104](source-audit.md), [source-audit.md:128](source-audit.md)).
The repo states current infeasibility alone cannot close #180 or milestone 9
([software-completion.md:44](software-completion.md)), and
[source-audit.md:202](source-audit.md) requires reporting feasibility as
inconclusive, not as completion. Only an explicit owner decision can change that.

## Open tasks and unmet preconditions

| Task / issue | Definition | Unmet precondition (evidence) |
| --- | --- | --- |
| T007 / #188 source admission | [tasks.md:39](tasks.md) | Zero eligible families and pairs in the bounded owner-only review ([tasks.md:50](tasks.md), [software-completion.md:41](software-completion.md)); participant rights/notice, immutable feed, completeness and pair yield not established ([spec.md:83](spec.md), [tasks.md:45](tasks.md)); five distinct eligible families required ([software-completion.md:41](software-completion.md)); no capture window authorized. |
| T001 / #181 preregistration and annotation | [tasks.md:18](tasks.md) | Needs a consented source and eligible pair yield ([tasks.md:22-23](tasks.md)); protocol is a pending candidate ([workload-protocol.md:1-11](workload-protocol.md); it also requires stopping before annotation if the split is infeasible, [workload-protocol.md:41](workload-protocol.md), [workload-protocol.md:88](workload-protocol.md)); no viable cohort, no frozen protocol, no named reviewers/adjudicator, no registered 14-day window ([software-completion.md:42](software-completion.md)). Depends on T007 for the cohort. |
| T003 / #183 real fit and evaluation | [tasks.md:75](tasks.md) | Depends on T001; no eligible labels, real model or sealed holdout; needs 1 train + 1 calibration + 3 holdout families, at least 100 known labels, holdout at least 20 positive and 20 negative ([software-completion.md:43](software-completion.md), [workload-protocol.md:126-133](workload-protocol.md)). |
| T005 / #185 evidence and final decision | [tasks.md:79](tasks.md) | No valid real experiment to reproduce or review; human scientific review and founder decision on an actual result missing ([software-completion.md:44](software-completion.md)). A null or negative real result would be acceptable; none exists. |

Dependency chain: T007 -> T001 -> T003 -> T005. None has an independent path; no
precondition is expected to become true without new source rights, new participants
or a new reviewed protocol (all outside current authorization).

## Option A: cancel as infeasible

Owner-adopted cancelled-partial/infeasible disposition, GitHub
`state_reason=not_planned`, same mechanism as SPEC-045/T007 and SPEC-034/T005.

Statements the signed text would need to carry (founder to confirm each):
- Synthetic software evidence stays valid for its stated scope; no real source
  window, pair, label, fit or held-out result exists, and none is claimed.
- The bounded result (zero eligible families) is not a proof that no source exists;
  this is a discretionary stop, not a universal impossibility finding.
- It explicitly supersedes the sentence at
  [software-completion.md:44](software-completion.md) for these four tasks only.
- No replacement task, retry, discovery broadening, capture, label or training is
  authorized. Thresholds and exclusions are not relaxed.
- M4, System One, forecasting, model promotion and confirmatory cohorts stay out of
  scope, as in [software-completion.md](software-completion.md).

Tracking changes this would imply (to be done by the tracking owner, not here):
- Unchecked original checkboxes for T001, T003, T005, T007 stay unchecked.
- A decision record JSON plus `task_cancellations` entries for `SPEC-019/T001`,
  `SPEC-019/T003`, `SPEC-019/T005`, `SPEC-019/T007` with the decision hash, then
  the reviewed synchronizer plan.
- #181, #183, #185, #188 close with `state_reason=not_planned`; state basis
  annotation shows cancelled/partial, not completed.
- Counts after readback: 6 completed + 4 cancelled/partial of 10 tasks.
- Parent #180 and milestone 9 stay open until a separate scope decision (precedent:
  #335/milestone 18, #510/milestone 20). Milestone description would need updating.
- Dependency statements stay unchanged and unsatisfied; closure of an issue is not
  predecessor acceptance.

## Option B: defer with explicit reopen criteria

Tasks stay open and unchanged. The signed text adds a dated review point and the
criteria below. Criteria 1 to 4 come from existing re-entry conditions
([software-completion.md:41-44](software-completion.md), notice clause from
[spec.md:83](spec.md)); criterion 5 is a NEW proposed governance condition. Nothing here is new
science; the founder may tighten but should not loosen thresholds.

Proposed reopen criteria (all required before any work resumes):
1. Source-specific allowlist, rights/privacy and authoring-boundary review for a
   named source set, with participant notice where third parties are involved.
2. Five genuinely distinct eligible families demonstrated by a prospective journal
   feed with ledger/seals and human completeness audit.
3. Finalized and reviewed protocol: lineage/duplicate encoding, resolution
   vocabulary, blinded rendering, timing/bin rules; two named independent
   reviewers and an adjudicator.
4. A 14-day UTC midnight-start window registered at least 24h before start.
5. Founder (not another actor) names the reopen trigger and an owner.

Tracking changes this would imply:
- No GitHub state change; #180, #181, #183, #185, #188 and milestone 9 stay open.
- Milestone 9 description and `STATUS.md`/`ROADMAP.md` could add a "deferred" note
  and the review date (tracking owner's call).
- Because the tasks stay open, M3.5 never reaches closure by itself; the stalled
  milestone remains visible. Founder should accept that cost or set a sunset date
  at which the founder must re-decide; reaching it changes nothing by itself, and
  Option A would still need its own signed record, hash entries and readback.

## Comparison

| | A: cancel | B: defer |
| --- | --- | --- |
| Open issues after | #180 parent only (until scope decision) | #180, #181, #183, #185, #188 |
| Reversible | Yes, by a new reviewed task/decision; cancelled attempt is not inherited | Yes, trivially |
| What tracking shows | Cancelled/partial, infeasibility recorded | Open, with stated reopen criteria and review date |
| Milestone 9 closure | Possible after separate scope decision | Blocked indefinitely |
| New authority needed | Signed record, hash-bound entries | Signed criteria only |

## Decision fields (UNSIGNED)

- Selected option (A cancel / B defer / other): `______` **UNSIGNED**
- If B: review date `______`, sunset date or "none" `______` **UNSIGNED**
- If B: reopen criteria adopted as drafted / amended text `______` **UNSIGNED**
- Parent #180 and milestone 9 disposition (separate): `______` **UNSIGNED**
- Founder name: `______`  Date: `______`  Signature/instruction reference: `______` **UNSIGNED**

A signed record is integrator-recorded provenance, not cryptographic authentication,
as in the cited precedents.
