# HAR.2 evaluation report

Status: deterministic cohort **infeasible** at
`ab2db0c45ab70c3689e39226897a5ddf2932126a` (2026-10-29). Native cohort
**pending**. No cohort was run and this report contains no outcome numbers.
SPEC-049/T005 stays open. Evidence: [evidence/t005.json](evidence/t005.json).

This report takes the "infeasible" path that the
[frozen protocol](evaluation-protocol.md) sets in advance (D6). D3 separately
says to record a feasibility result if native yield stays unknown, which is true
of the native cohort below. It is not an unsupported, inconclusive or negative result about the method. It
says only that the registered material cannot support an evaluation yet.

## Why the deterministic cohort cannot run

Four facts block it. Each is checked against the pinned inputs listed in the
evidence record:

1. **There are no executable case definitions.** [source-registration.md](source-registration.md)
   records 0 executable HAR case definitions and 0 registered or evaluated
   comparison units. The "up to 16" case definitions were only proposed and were
   never constructed.
2. **No case roster is frozen.** The T002 founder freeze
   ([decision record](evidence/registration/t002-founder-freeze-20261028.json))
   fixed the D1–D6 rules (summarized in D7). It froze no case roster and assigned no case to
   discovery or holdout. Source registration requires that roster before any
   outcome is evaluated. Calling `harness_evaluation.register` with no units
   refuses with `invalid-registration`.
3. **The A/B/C arms have no frozen identities.** No candidate hashes and no
   matched profile hash are registered for A (static base), B
   (checkpoint/context guidance) or C (contrastive refinement).
4. **Arm C has no real proposer.** Arm C must be the candidate that a
   `harness_refinement` round selects, or the base that round explicitly keeps.
   Today the only proposers are injected test doubles, so no real arm-C candidate
   exists.

Engineering note: the arms differ only in guidance text. The existing fixtures
for the offline runner (`harness_lab`, simulated containment) are fixed scripts
that do not read guidance. Without a model solver, A, B and C would give
identical fixture outcomes by construction. Writing arm-specific behavior into
fixtures would invent the effect being measured. Neither kind of output is a
result, and neither was produced. A meaningful comparison of guidance variants
therefore also needs a solver that reads guidance, and that means the native
branch (T004/T008).

Arm D (A–C plus scoped earlier experience) depends on the same roster and arm C.
It is therefore also infeasible. The T006 store being available does not change
that.

## Endpoints

None of the protocol's endpoints ("Outcomes and denominators") or of T005's
reporting items was computed. Each is infeasible for the deterministic cohort and
pending for the native cohort:

| Axis | Endpoint | Status |
|---|---|---|
| Continuity | Correct completion / registered and started units; correct interrupted recoveries; duplicate effects; repeated work; interventions; rework scope; checkpoint/handoff correctness | not computed |
| Coordination | Conflict precision/recall per class; false safe admissions; verified safe admissions and verification coverage; useful parallelism recovered; unnecessary serialization; serial-oracle agreement | not computed |
| Shared | Unknown/refused/failed/interrupted/ungraded counts; label/class coverage; task quality; declared/observed effect violations; complete costs and per-profile limits | not computed |
| T005 reporting | Paired per-stratum outcomes; correction/review effort; sensitivity to missing outcomes | not computed |

No costs were incurred beyond this offline inspection: no host, model, paid
route or native session was used. The T012 reconciliation therefore has no
attempts to reconcile.

## Native cohort

Pending. It is blocked on SPEC-049/T004 (native admission) and SPEC-048/T008
(qualified host). There is no native source, session or outcome, and none is
substituted with synthetic data.

## What would unblock the deterministic cohort

The founder must supply, in a decision record made before any outcome:

1. **A frozen case roster.** Constructed case definitions drawn from the
   registered lineages L1–L4 ([corpus.md](corpus.md)). Each case needs its
   lineage, task family, stratum, holdout partition, rubric and deterministic
   oracle. The roster must follow D1: L1 is never split, L3 stays unassigned
   until resolved, and L4 is held out only if a derived task qualifies.
2. **A/B/C arm identities.** Exact candidate hashes for A, B and C and the matched
   profile hash. Arm C must come from a recorded refinement round with a real
   proposer, either a selected candidate or an explicit keep-base.

Even with both, the D3 rule still applies. At most 4 independent lineages exist,
so a deterministic cohort stays descriptive only.

## Limits

This is an offline inspection and refusal check only. It runs no fixture, host,
model, native session, paid route or human annotation. It makes no inferential,
economic or promotion claim and does not authorize execution or promotion. The
pre-PR reviews were run by Claude subagents and are not independent Luna review.
