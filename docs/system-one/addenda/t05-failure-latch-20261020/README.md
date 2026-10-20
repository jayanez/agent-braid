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

## Subsequent admission and late-refusal directions

The coordinator reports a targeted T05 wire-admission rule: reject a zero Git object ID in task.goal as invalid-envelope. [Frozen verified-plan contract](../../../../specs/028-system-one-core/contracts/verified-plan-v1.md), VP-REQ-01 lines15/32, restricts zero-G absence to retained change-preimage/file-addition semantics; task.goal is not that exception. Contract bytes were read directly. This is the coordinator's wire-compliance direction, pending an actual negative test and final source-bound receipt; generic T03/IR semantics and the frozen contract remain unchanged.

For late technical refusal, preserve pins already established and use null only for identities never established; clear selected plans and semantic evidence. This is an additional implementation direction, not a completed fix or observed output. The source remains worker-owned; final focused hashes and Luna review are pending.

The coordinator also reports diff-check detecting a blank final line in historical shared-worktrees.log. This documentary conversation confirmed its bytes end in a blank line and exactly match the already packaged source capsule: SHA-256 `2e52c3b29b3ded0242b07e3eb53ae966e024e8e2a89d5a96f00a3181e17ff4a8`. The original evidence is retained unchanged; no whitespace is trimmed or hidden. [Documentary source capsules](../first-batch-final-package-20261020/documentary-source-capsules.json) preserve the exact text using JSON encoding. This is an evidence-formatting observation, separate from the new branch's staged-whitespace checks and the earlier profiles' obtained outcomes; no failed check is reclassified as a pass.
