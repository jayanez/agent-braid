# T05 — source-bound candidate released for scoped review

S1-DDP-T05-REVIEW-CANDIDATE-20261020; canonical SPEC-028/T011. [Original worker receipt](worker-candidate.json) records released ownership and stable-for-review status. This follows the [open refusal-latch finding](../t05-failure-latch-20261020/README.md) and its [admission/refusal supplement](../t05-failure-latch-20261020/admission-and-late-refusal.md). It is not final T05 delivery or acceptance.

| Candidate binding | SHA-256 |
|---|---|
| system_one_verified_selection.py |109a182c1762b55acdb2575488ab1b573ca15d3e5dec760fec30621c164a6935|
| test_system_one_verified_selection.py |f5c8dd0e48a74f338b813d1a56ba66c650beb94123add3735c356c179755313e|

The documentary conversation checked both actual candidate hashes and both log hashes. [Exact logs](log-capsules.json) record28 focused tests, zero failures/skips, exit0,9.780s; three directed mutations were detected by assertion failure: ignoring cancellation at final publication, failing to latch an externally caught hunk failure and accepting rehashed observed-source drift. RED mutation controls are expected detections, not failures of the unmutated focused suite. They do not establish exhaustive coverage. The logs state source bytes were never modified. No tests or implementation review were executed here.

This is a later source-bound28-test run, distinct from the earlier unbound28-test/11.226s log and the22-test passes predating new boundary checks. Preserve all revisions and their scope; do not sum overlapping attempts as independent evidence.

## Remaining variant and review status

The coordinator reports that checkpoint→_open at the64-row saturation boundary does not immediately latch refusal. Final close does refuse, so the reported variant does not bypass final acceptance, but the live-context failure behavior remains pending review/fix. Do not close T05-FIND-001 based on these focused passes. Exact corrected source/tests and finding disposition are still required.

The worker receipt reports scoped Luna Latest review active on T05 token/cancellation/handoff semantics. No completed Luna report, findings disposition, independent acceptance or human review is received here. T05 full profiles have not started at this receipt. The [packaging exception](../t05-whitespace-preservation-20261020.md) must be included in that review. T07 global review, T06 consumers, scientific/representative acceptance, training/calibration, admission/promotion and activation remain separate pending gates. No product source or tests are published by this documentary PR; their hashes refer to the coordinator candidate.
