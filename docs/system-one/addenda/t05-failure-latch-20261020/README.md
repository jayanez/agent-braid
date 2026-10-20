# T05-FIND-001 — irreversible technical refusal, correction in progress

Canonical task SPEC-028/T011 (DDP-T05). [Original finding receipt](finding.json), recorded2026-10-20T07:17:51.592183Z: coordinator/worker self-inspection, not completed independent review. A trusted consumer could catch a live phase/checkpoint exception for deadline/work exhaustion and then publish an earlier answered producer snapshot. Required correction: latch technical refusal irreversibly before final publication, while leaving any already sealed final result immutable. This is a material boundary finding, not authority to execute or accept the system.

The coordinator reports a fix in progress, with deterministic tests for phase expiry, cleanup overrun, raw-byte limits and rehashed observation drift. No final corrected source hashes or review disposition have been received here. The [earlier context/digest direction](../t05-context-and-digest-seams-20261020.md) remains design intent rather than obtained conformance.

## Preserve the separate test attempts

[Exact log capsules](focused-log-capsules.json) retain each original UTF-8 log and SHA-256; reconstruct bytes from text without trimming. At incorporation, the logs show:

| Attempt | Obtained log result | Boundaries |
|---|---|---|
| First |22 tests, two failures,9.418s|Coordinator attributes mutable aliasing in a builder fixture; reports deepcopy repair without semantic relaxation. This is reported diagnosis, not an independent review.|
| Second |22 tests, zero failures/skips,9.639s|Predates new boundary checks; does not establish the subsequent latch correction.|
| Third, newly present when read |28 tests, zero failures/skips,11.226s|Later completed log observation only; no source-bound final receipt or finding-resolution evidence yet.|

These are overlapping revision runs, not independent experimental populations. The documentary conversation preserved and parsed logs; it did not execute tests or independently verify the diagnosis/fix. Do not convert the22-pass observation into proof of the new boundaries or use the later28-pass log alone to close T05-FIND-001. Next evidence must bind corrected source/tests, the latch invariant and independent findings disposition explicitly.

The coordinator reports earlier T02/T03/T04 source pins unchanged. Luna Latest review and T05 full quick/PR profiles remain pending at this handoff. This finding is independent of the older failed DDP-T01 profile and the later passing component profiles; each retains its actual candidate and outcome. No new model/study, scientific/human acceptance, admission/promotion, T06 consumer or activation is supplied. EUR0/executionAuthorization=false remain the stated boundary.
