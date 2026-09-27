# SPEC-019: Native specialized proposal predictor (M3.5 draft)

## Purpose and scope

After M3 has a reviewed deterministic exchange domain, investigate a small
native learned advisor for choosing which candidate exchanges deserve verifier
work. This is a separate M3.5 experiment, not an M3 exit dependency. No model
is trained or integrated by this draft.

## Authorities

Constitutional clause zero and Articles 2, 4, 6, 8–10, 13–14, 17–20, 23–25;
GOVERNANCE.md; accepted bounded ADR 0017; claim discipline. The verifier alone
determines bounded evidence. Prediction never authorizes execution.

## Requirements and acceptance scenarios

- **REQ-001 — native proposal only.** Train an offline linear ranker on
  versioned local features and separately adjudicated workload utility
  labels, serialize versioned weights and
  perform local standard-library inference. No Laya/Jev or remote provider.
  - **SC-001:** A fixed artifact and feature vector produce deterministic
    proposal, abstention and model/version provenance.
  - **SC-002:** Changed weights, unknown features or missing provenance fail
    closed and do not create a certificate.
- **REQ-002 — valid evaluation.** Split by workload family before training;
  compare with rule-based M3 advisor on untouched holdout data.
  - **SC-003:** Report calibration, abstention, useful proposals, verifier
    workload and cost with uncertainty and negative controls.
  - **SC-004:** Leakage, class imbalance and no-gain outcomes are reported,
    not hidden or converted into a success claim.
- **REQ-003 — strict separation.** The deterministic SPEC-018 verifier remains
  the only source of bounded exchange status.
  - **SC-005:** A high model score without verifier agreement cannot yield
    verified-bounded or execution authorization.

## Scientific boundaries and compatibility

Scores are heuristic, not probabilities of semantic truth unless calibrated
for a stated distribution, and never guarantees. A learned model cannot
establish a braid relation, general confluence or runtime safety. Existing M2
and proposed M3 evidence contracts remain unchanged. No positive result is
assumed. The dataset, labels, feature version and splits must be reproducible.

## Evidence and unresolved questions

All obtained evidence is empty pending M3.5 implementation.
Target distribution, useful-proposal threshold, calibration method and cost
budget require preregistration before training.
The founder selected real-workload utility prioritization as the target
direction on 2026-09-27. The detailed
[workload protocol](workload-protocol.md), data provenance, privacy review and
metric thresholds require review before training.
The [pretraining feasibility audit](feasibility-audit.md) identifies a
degenerate verifier-status target in the current valid corpus and two possible
routes to a useful comparison. Neither route is approved by this draft.
