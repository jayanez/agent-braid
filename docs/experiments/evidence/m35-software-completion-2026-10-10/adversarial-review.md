# Independent technical adversarial review

Model: Luna Latest (`gpt-6-luna`), effort medium. Two read-only reviewers did
not implement this increment. No source payloads or real labels were inspected.

The comprehensive reviewer inspected code at `0fd401d`/`4a400d4`, verified
all 15 focused input commitments and the raw output hash, and reran all 114
then-present focused controls (zero failures/skips). Scope: deterministic
trainer and calibration, artifact/request provenance, partition/duplicate
isolation, adapter census/cutoff and prospective rejection, reviewer record
consensus, budgets/unknown bounds, verifier separation and permutation control.
A forged scorer certificate/execution grant did not enter verifier results or
authorization. A documentation statement about pending verification was
corrected to identify required checks rather than presumed completed evidence.
No code finding blocked the synthetic T002/T004 scope.

The separate evaluator reviewer reran 50 evaluator/trainer controls and found
one P2 measurement defect: the optional preparation hook's canonical validation
was inside total time but outside all named phases. The fix counts it in
`preparationSeconds` and exposes `preparationValidationSeconds` as a diagnostic
subset, never an additional cost. The deterministic clock regression proves
8 units of hook work + 12 validation = 20 preparation = 20 total across four
rows. The reviewer reran that test plus the full evaluator suite (29 test
invocations, zero failures) and found no remaining material accounting issue.
Feature/artifact/policy/authorization contracts are unchanged; the report phase
addition and subset semantics are documented in the interface plan.

These reviews establish bounded software findings only. Caller-declared
synthetic origin, cohort metadata and reviewer IDs remain unauthenticated;
callbacks are trusted and not sandboxed. Real feed completeness, linked
resolution/exclusion semantics, blinded rendering, authenticated lineage,
real-cost protocol review, the experiment and human/founder approval remain
pending. No independent scientific validation or production benefit is claimed.
