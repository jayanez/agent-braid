# SPEC-078: v2 run refusals

Refusal codes a `v2-*` run (`lightning run --prompt-set v2-feedback|v2-validation|v2-test`) or the optimizer
contamination scan can raise, in addition to the SPEC-071 codes in
[`specs/071-lightning-rollouts-reward/contracts/refusals.md`](../../071-lightning-rollouts-reward/contracts/refusals.md).
Every refusal happens before a run directory is created, except `holdout-contamination` (before an optimizer call).

| Code | Meaning | Effect |
| --- | --- | --- |
| `protocol-not-frozen` | `prompts/FREEZE.json` is missing or is not a SPEC-078 freeze record | run not started |
| `protocol-hash-mismatch` | the protocol, the Gate 0 script or `agent_braid/lightning_heldout_v2.py` differs from the freeze | run not started |
| `holdout-hash-mismatch` | a v2 split differs from the freeze | run not started |
| `skill-hash-mismatch` | an A0 run would not measure the frozen skill (edited skill, prebuilt plugin, or another target path) | run not started |
| `test-already-scored` | the same candidate already has a `v2-test` run in this store; resume that run instead | run not started |
| `holdout-fingerprint-stale` | `prompts/fingerprints.json` does not match the frozen validation and test splits | optimizer call or run refused |
| `config-enum` | another arm than `final`, a partial split (`case_ids`), or repetitions other than 1 (feedback) or 3 (validation, test) | run not started |
| `holdout-contamination` | an optimizer input contains a v2 validation or test id or 8-word window | optimizer call refused |
