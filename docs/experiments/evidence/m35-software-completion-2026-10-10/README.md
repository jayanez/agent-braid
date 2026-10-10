# M3.5 software completion evidence — 2026-10-10

This package covers synthetic trainer/inference T002 and verifier boundary
T004, plus software controls for the still-open evaluation/source tasks.
No real data, labels, trained workload model or scientific/founder acceptance
is claimed. The remaining experiment is bounded in
[software-completion.md](../../../../specs/019-native-predictor/software-completion.md).

The initial focused run executed 114 tests with zero skips/failures using
CPython 3.12.13 in an isolated pinned environment. Command:

```sh
.venv/bin/python -m unittest -v tests.test_native_predictor tests.test_native_predictor_training tests.test_native_predictor_evaluation tests.test_native_predictor_adapter tests.test_native_predictor_contract tests.test_predictor_readiness tests.test_m35_review_packet
```

`focused-increment.txt` is its raw output. The post-review timing fix passed 115 controls with zero skips/failures in
`focused-final.txt`; `focused-receipt.json` binds that run. The original 114-test
receipt is preserved as `focused-receipt-before-timing-fix.json`. Independent
Luna findings and corrections are recorded in `adversarial-review.md`.
Final clean-clone reproduction executed 115 controls with zero skips/failures
on commit `7321407bc6abc57117fab379e14eafcddf80dd63`; `reproduction.json`,
`focused-cleanroom-final.txt` and `global-gate-final.txt` record its input
commitments, focused output and passing global gate. The earlier 114-test
reproduction is retained as `reproduction-before-timing-fix.json`.
quick/PR and exact-head CI are repository reliability checks, not scientific
or human approval. Interrupted older runs remain historical non-passes.

The previous assurance record is preserved byte-for-byte in
`historical-assurance.json` and was validated against its historical commits
before replacement. `authority-refresh.json` names changes between that
candidate and current authorities. The new draft remains human-review pending.
`preparation-packet.json` commits the fixed current metadata documents only:
it permits no source access, capture, registration, annotation or training.


The first quick run in this increment was interrupted (exit 130) because the
independent timing review produced a code correction. It is not a pass. A new
quick run and one stable PR profile validate the corrected candidate; their
results and exact-head CI are disclosed in the PR, with full local logs retained
in the task artifact directory. No profile substitutes for human review.


CI run 38038949732 failed an evaluator test that incorrectly required the
median of a sum to equal the sum of independently summarized medians. The test
now verifies the additive timing identity per raw policy run and retains the
report-level phase-separation checks; production code is unchanged. Independent
Luna re-review ran the 28 evaluator tests successfully, and the corrected
focused suite ran 115 controls. The failed run remains a non-pass; exact-head
CI must run again before integration.
