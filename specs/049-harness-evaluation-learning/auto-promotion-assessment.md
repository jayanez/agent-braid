# Automatic-promotion assessment (SPEC-049 T008)

Disposition: **deferred**. Automatic promotion stays disabled
(`agent_braid.harness_promotion.AUTOMATIC_PROMOTION` is `False`) and
`executionAuthorization` is false everywhere. This file assesses the optional policy in
`promotion-policy.md` and lists the rules SPEC-050 T009 may compile. It enables nothing.

T008 names `promotion-policy.md` and `tests/test_harness_promotion.py` as target files.
Both are pinned by hash in T006/T013 evidence, so this assessment and its controls live
in new files (this file and `tests/test_harness_auto_promotion_controls.py`) rather than
staling those records. `promotion-policy.md` is unchanged.

## Why deferred, not go-proposal

- The only cohort evidence is T005's deterministic synthetic-control run: plumbing
  only, descriptive-only under D3, arm C equal to keep-base by construction, no utility
  or cost claim, no native cohort (T004 and SPEC-048/T008 pending, T014 carries it).
- Every real T003 report still lists six pending endpoints (interventions, rework,
  interrupted-recovery, conflict-precision-recall, false-safe-admissions,
  useful-parallelism). The production policy below tolerates none, so current evidence
  abstains with `pending-endpoints`. That tolerance choice is the assessor's, not an owner
  decision; judging some endpoints irrelevant to task-local guidance is an owner decision
  that could move this toward `go-proposal`, and the positive control passes only under a
  control policy that tolerates all six.
- No held-out evidence exists for a claimed native profile, and numeric limits were not
  fixed before any native evaluation.

Not `disabled`, because the rules are concretely definable and the controls pass. If
T004/T014 never admit a native route, `deferred` is equivalent to `disabled` in practice;
revisit when T014 reports, or reopen the decision as `disabled` at T010 if no admissible
native route exists by then. Not `no-go`: the narrow class was not assessed against any
evidence that could contradict it, which is a gap, not a finding. A later `go-proposal`
would still need a separate ADR, candidate-bound review and a founder or operator
activation decision.

## Bounded eligibility (all must hold; first failing rule abstains)

Conformance vector: `assess` in `tests/test_harness_auto_promotion_controls.py`. This
table is the contract; T009 must implement it in `agent_braid/` and pass equivalent
vectors, not import from tests. Every stop signal (revoked set, conflicts, spend,
incident) is a required input: an omitted or malformed input abstains with
`invalid-input` before any rule, never passes.

| Order | Rule | Abstention reason |
| --- | --- | --- |
| 1 | The record is an undecided (`pending`) T013 record; human approved or rejected records are not re-assessed | `decision-not-pending` |
| 2 | Policy `fixedAt` is non-negative and earlier than the record's `decidedAt` | `limits-not-fixed-before-evaluation` |
| 3 | Change class is exactly `task-local-guidance-packaging` | `change-class-ineligible` |
| 4 | Changed layers are a non-empty subset of the closed allowlist (`guidance`, `context-packaging`); anything else, including authority, containment, hooks, scripts, settings and tools, is outside | `layer-not-allowed` |
| 5 | Candidate scope is the policy scope (`task-local`) and the profile scope is the registry scope | `scope-changed` |
| 6 | Declared effects are a subset of the policy effect bound | `effect-outside-bound` |
| 7 | Cohort is adopted by the policy and equals the profile cohort; the initial policy adopts `synthetic` only | `cohort-not-adopted` |
| 8 | Profile identity has all five keys and equals the current identity on each | `stale-identity` |
| 9 | None of the registration, evaluation, cost-report or extra evidence hashes is revoked | `evidence-revoked` |
| 10 | No conflicting evidence | `evidence-conflict` |
| 11 | There is at least one stratum and every stratum's C-vs-A verdict is `noninferior` | `regression-not-covered` |
| 12 | Pending endpoints are all tolerated by the policy (production: none) | `pending-endpoints` |
| 13 | Unsafe-admission, authority and effect counts are present, known and zero | `safety-violation` |
| 14 | No incident stop is open | `incident-stop` |
| 15 | Known spend is a non-negative integer within the budget cap | `budget-exhausted` |
| 16 | Independent acceptance (below) | `acceptance-*` |

Known limits of the rules as written:

- Candidate class, changed layers and scope are caller declarations. They are not bound
  to `candidateSha256`, so rules 3-5 bound the declared change, not the real one. T009
  must derive them from the hashed candidate manifest before any such rule counts as a
  safety bound.
- The T013 decision records the decision tick, not the evaluation tick, so rule 2 is
  weaker than "fixed before evaluation"; T009 should bind the evaluation tick.
- New tools, scripts, hooks, global settings, authority changes, paid routes and source
  promotion are outside the class (rules 3 and 4). Native promotion needs native evidence
  and a separately adopted policy; the synthetic adoption never covers it.

## Independent acceptance

An acceptance record names a checker of exactly `{kind: independent-check, id}` with a
non-empty id different from the proposer, a verdict of `accepted`, and the exact decision,
evaluation and candidate hashes. Missing, self-issued or malformed-checker, mismatched
(forged or stale) or non-accepting records abstain with `acceptance-missing`,
`acceptance-not-independent`, `acceptance-forged` or `acceptance-rejected`. Records prove
binding only, not authenticity of the checker; authenticity remains a caller check against
trusted records, as in T013.

## Stops

- Canary: size at least 1; any safety violation halts, a failure beyond the budget halts
  (zero in the control policy), an unknown observation halts, extra observations halt.
- Drift: `ProfileRegistry.resolve` serves nothing on any identity change; `begin` and
  `commit` refuse it.
- Revocation: `revoke_evidence` withdraws every decision citing the lesson and falls back
  to the newest prior profile with valid evidence, or nothing; a revoked citation also
  blocks a new `begin`.
- Rollback and incident: `rollback` restores the prior usable profile (journal reasons
  `drift-stop`, `canary-halt`, `incident-stop`); with none left the registry serves
  nothing, and a further stop fails visibly (`no-active-profile`). An unknown trigger fails
  with `invalid-trigger`.
- A rolled-back decision is withdrawn and cannot be begun again; restoring it needs a new
  human decision.

## What the controls do and do not show

They show that the rules are implementable against the existing human-decision records
and registry, and that each stop path fails closed. They qualify the controls only: they
use synthetic doubles, and the control module carries no authority. No automatic actor
can create a decision today. They do not show that any automatic transition is useful or
safe on native agent behavior. T009 must keep the engine disabled by default and must
not treat this assessment as adoption.
