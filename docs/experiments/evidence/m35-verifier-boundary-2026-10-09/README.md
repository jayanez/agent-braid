# M3.5 verifier boundary software evidence — 2026-10-09

This artifact records software-level evidence for SPEC-019 SC-005 from the
complete CI test suite. It does not establish real-source eligibility,
human-utility prediction, a real-data fit, holdout performance, production
behavior, human scientific approval, or founder acceptance.

- Tested PR head: `7316f97551e8345e43ae39c7b5eb0ffa6200c403`.
- Workflow: [Validate repository run 37858099799](https://github.com/jayanez/agent-braid/actions/runs/37858099799).
- Relevant job: [Complete Python test suite](https://github.com/jayanez/agent-braid/actions/runs/37858099799/job/113587349492), Ubuntu 24.04, Python 3.12.15.
- Command: `python3 -m unittest discover -s tests -v`.
- Outcome: 832 tests ran in 506.676 seconds; all passed, with two explicit skips.

The run includes these passing controls from
`tests/test_native_predictor_contract.py`:

- `NativePredictorContractTests.test_verifier_remains_sole_certificate_source`
- `NativePredictorContractTests.test_learned_score_remains_outside_verifier_and_authorization_boundary`

Both use an extreme predictor score and verify that scoring does not invoke
the deterministic verifier, produce a certificate or grant execution
authorization. The separate unchanged verifier remains the only source of
bounded status. These controls exercise synthetic fixtures and prove only
the tested software boundary.
