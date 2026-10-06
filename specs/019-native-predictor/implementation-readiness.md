# SPEC-019 implementation readiness

**Status:** prospective work breakdown, 2026-10-05. No new source, label, fit or protocol approval is recorded. Existing T001/T007 and their reviewed restrictions remain controlling. T009/T010 make offline preparation actionable; they do not satisfy the real-data gates.

| Step | Task | Required output | Completion or stop condition |
|---|---|---|---|
| Source ownership and rights | T007 | Owner/participant/data-rights/privacy decision per family, before opening payloads | Absent permission leaves family excluded; patient, clinical, athlete/customer and private payloads remain outside this repository |
| Authoring-boundary feasibility | T007 | Contemporaneous immutable shared-base receipts, all sessions/pairs and primary exclusion ledger | Git history alone is insufficient; absent eligible pairs is a feasibility result |
| Protocol preparation | T001/T009 | Candidate source window, rubric, blinding/adjudication, split and class-coverage readiness report | No window extension or population change after labels; no approval inferred from machine checks |
| Scientific preregistration | T001 | Human-reviewed and frozen existing workload protocol/rubric with source admission | Five eligible families, train/calibration/three holdout split and declared label/class coverage remain required before fitting |
| Offline interfaces | T010 | Feature/artifact serialization, abstention and test doubles using synthetic inputs only | No fitted weights, calibration, real data or benefit claim; declare all fixtures synthetic |
| Trainer and inference | T002 | Actual trainer, fixed calibration and versioned inference tests/results | Real fit starts only after T001/T007 gates and frozen protocol; reject leakage or unavailable prediction-time features |
| Held-out evaluation | T003 | Known/unknown label bounds, disagreement, coverage and complete costs | Negative/inconclusive results are valid; do not tune on holdout |
| Consumer boundary | T004 | Unchanged deterministic verifier and authorization-denial controls | Predictor score never supplies a certificate or execution grant |
| Review | T005 | Candidate-bound evidence and human M3.5 decision | Tests, synthetic readiness and filtered lab sync cannot close real-source feasibility |

T009 targets a standard-library `scripts/check_predictor_readiness.py` that reads explicitly synthetic or metadata-only manifests, produces missing prerequisite reasons, and never opens a source or changes admission state. `tests/test_predictor_readiness.py` must cover missing rights, zero yield, family leakage, insufficient classes, unapproved rubric and hash drift. All real eligibility thresholds come from the existing proposed workload protocol; machine checks cannot grant approval.

T010 targets `agent_braid/native_predictor.py` and `tests/test_native_predictor.py` for feature extraction, versioned artifacts, deterministic ranking/ties and fail-closed abstention with hand-authored synthetic test doubles. Fitting weights or calibration, even to synthetic labels, remains outside this preparation task until the protocol gate permits the relevant experiment. No raw sensitive source content is committed.

Run proportional validation after implementation and bind actual evidence separately. The planned filenames/commands above are future targets; they do not exist or pass by virtue of this document.
