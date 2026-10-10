# SPEC-019 synthetic-code adversarial review — 2026-10-09

## Scope and method

Independent read-only adversarial review by Luna Latest (`gpt-6-luna`, medium)
of the SPEC-019 trainer, evaluator, adapter, contract tests and their claims.
The reviewer did not implement the candidate, inspect private source payloads,
run a real-data experiment, or modify the worktree. This is a software review;
it is not scientific acceptance, human label review, or founder approval.

The review found no confirmed synthetic-code defect that invalidates the
tested controls. The 91-test focused set passed in the review environment.
The reviewer confirmed coverage for family/session/duplicate-group split
separation, holdout-label exclusion from fitting/scoring inputs, budget and
ranking behavior, abstentions, unknown-label metric bounds, and the boundary
that keeps model scores advisory and execution unauthorized.

## Findings that still block real-data use

- The adapter refuses prospective sources because independently verified
  registration, rights, completeness and admission checks are absent.
- The adapter has no approved resolution-event taxonomy for excluding a pair
  resolved at or before the selected cutoff. Add a regression where such a
  resolution precedes the second proposal and ensure the pair is excluded or
  ingestion fails closed before any real-source use.
- The evaluator accepts in-process Python callbacks. Closures and global state
  are not isolated, so the implementation alone cannot prove holdout labels
  stayed sealed. Real evaluation needs a trusted execution boundary and
  evidence bound to the exact inventory and artifact.
- The synthetic records do not authenticate reviewer identity, independence,
  annotation context, source rights or feed completeness. The exact blind
  display and source-bound label package remain protocol gates.

These are real-source and protocol blockers, not observed failures of the
synthetic-only result. They keep real capture, training, evaluation, T001,
T003, T005 and T007 open. The founder's owner-only source decision remains in
force; this review authorizes no source discovery, capture or label access.

## Follow-up regression review

Luna Latest separately reviewed the follow-up test
`test_unreviewed_resolution_before_second_proposal_fails_closed`. It confirms
the test inserts a structurally resealed `proposal-resolved` event between the
first and second proposals, then verifies the adapter rejects the complete
input. The refusal is caused by the unrecognized event kind, so the test proves
fail-closed behavior only; it does not implement or approve resolution
semantics. It does not cover how a future reviewed taxonomy should distinguish
events before versus after the cutoff. No false positive was found in the test
construction.

## Reviewed file commitments

| File | SHA-256 |
| --- | --- |
| `agent_braid/native_predictor_adapter.py` | `ecaa6c037e1af6f02e737f61cadcc2a88f44e4f7161ed52625da66123b7fd43c` |
| `agent_braid/native_predictor_evaluation.py` | `c60beb495cd358e1ba6629d456bc6250ae7242b989d5fa738a6eff8c12b2082e` |
| `agent_braid/native_predictor_training.py` | `5c77eb3c134ed8bdb8f1a6f7ab5a46b3fda62014282d7da0211863e7d3b2d8a3` |
| `tests/test_native_predictor_adapter.py` | `d41741dd233a797be8161662b3bad0ba974ac567e3736b57663a88cd410058fc` |
| `tests/test_native_predictor_evaluation.py` | `097da1b7a064eab64c5deb598de4a61479da09c1b9c83a3af7577253a71cd93d` |
| `tests/test_native_predictor_training.py` | `a7023106c9f57e8ab961e6874c43316dc813eb17015b936b8f1e5a320127c392` |
| `tests/test_native_predictor_contract.py` | `2faf226c56d633e4229160303511bd5a17de2a47979438272bfcc4372becc4e4` |
