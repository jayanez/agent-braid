# SPEC-019 synthetic contract checks — 2026-10-09

The four contract-anchor tests for versioned inference, tamper refusal, synthetic held-out evaluation, negative/no-gain reporting, and verifier separation passed on candidate commit `06d7e85cff985e429f159132f6b383fa195c09cb` using Python 3.13.11.

Command: `python3.13 -m unittest tests.test_native_predictor_contract -v`

Output: `contract-tests.txt` (SHA-256 `fe05c6d63e9d96e68640f0e8b8ec890835e72238c7a64c1afba11c8b32c8b6d1`).

These are synthetic software controls only. The fixture is not an eligible real holdout, does not establish human usefulness, protocol approval, real-data training or calibration, and grants no execution authorization.
