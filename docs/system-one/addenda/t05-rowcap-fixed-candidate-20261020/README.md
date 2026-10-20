# T05-FIND-002 — corrected candidate, scoped recheck pending

S1-T05-ROWCAP-FIX-CANDIDATE-20261020; canonical task SPEC-028/T011. The coordinator's T05-FIND-002 is an alias of the corpus's T05-REVIEW-P2-001, the row64 variant associated with T05-FIND-001. Preserve both identifiers. This follows [Luna's pre-fix review](../t05-luna-row64-review-20261020/README.md), not a rewrite of its reviewed hashes.

The [exact fixed-candidate receipt](fixed-candidate.json) reports ownership released for scoped recheck, not final delivery. The documentary conversation compared both source/test hashes against the actual implementation candidate and both [original logs](log-capsules.json) against receipt hashes, without rerunning tests or reviewing correctness.

| Bound candidate | SHA-256 |
|---|---|
| Selection source |8971650c51082938281ecb62e40e23adab4202bb20971b1eb23e1ef7d78c339c|
| Selection tests |d14d2ec1637b944eab96a6c9938b1758c8343e390fae208d55e615c9089e0b56|

The focused log records28tests, zero failures/errors/skips, exit0,9.848s. Two new directed mutations are each detected by one assertion failure and zero errors: swallowing automatic-checkpoint row refusal without latching, and failing to reserve the actual cleanup row. RED mutation results are expected detection controls, not failures of the unmutated suite. The log states source bytes were never modified. These overlap earlier test attempts and are not independent experiments or exhaustive coverage.

The coordinator reports limiting operational rows to63, latching across the full checkpoint path, and a public-API regression for immediate live refusal, cleared semantic bodies, immutable earlier producer snapshot, blocked subsequent semantic operations and a real cleanup row64. The logs provide focused evidence on the candidate above; the same Luna reviewer is still checking the fix. No completed reviewer disposition was received at this observation, so T05-FIND-002/T05-REVIEW-P2-001 remains pending closure. T05-FIND-001's related boundary is not silently declared fully closed by these passes.

New complete quick/PR profiles have not started at this receipt. Prior T02/T03/T04 packet, contracts and historical test outcomes are preserved. No product code is published by this documentary update, no task/parent/milestone is closed and no human/scientific/representative/admission/promotion/activation approval is implied. Next evidence must bind Luna's targeted disposition to these exact fixed hashes, then stable-profile inputs and actual results.
