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
  versioned local features and separately adjudicated, policy-blind
  assessed-usefulness labels, serialize versioned weights and
  perform local standard-library inference. No Laya/Jev or remote provider.
  - **SC-001:** A fixed artifact and feature vector produce deterministic
    proposal, abstention and model/version provenance.
  - **SC-002:** Changed weights, unknown features or missing provenance fail
    closed and do not create a certificate.
- **REQ-002 — valid evaluation.** Admit only consent-reviewed sessions mapped
  without guesswork to the M3 pair domain; register consecutive source windows,
  exclusions and the human utility rubric before labels. Split by repository
  and workflow family before training, annotate every holdout pair independently
  of policy scores, and compare with the rule-based M3 advisor.
  - **SC-003:** Report assessed-useful proposals, calibration when estimable,
    abstention, verifier workload and the prespecified cost boundary on an
    untouched holdout.
  - **SC-004:** Missing labels, reviewer disagreement, leakage, class imbalance,
    no-gain and inconclusive outcomes are reported without a success claim.
  - **SC-006:** A synthetic owned-flow capture reproduces session/pair admission
    and exclusion counts, records zero real pairs and never grants execution.
  - **SC-007:** A private prospective sidecar and filtered lab exporter preserve
    explicit base receipts, independent proposal ordering and full session/pair
    exclusion counts in synthetic rehearsal; content changes and incomplete
    remote registration or seal chains fail closed. No real-source claim follows.
- **REQ-003 — strict separation.** The deterministic SPEC-018 verifier remains
  the only source of bounded exchange status.
  - **SC-005:** A high model score without verifier agreement cannot yield
    verified-bounded or execution authorization.

## Scientific boundaries and compatibility

Scores are heuristic, not probabilities of semantic truth; any calibrated
probability concerns the stated human utility proxy in the sampled workload,
not semantic validity. Reviewer judgments do not measure observed time saved
or conflicts prevented. A learned model cannot
establish a braid relation, general confluence or runtime safety. Existing M2
and proposed M3 evidence contracts remain unchanged. No positive result is
assumed. The dataset, labels, feature version and splits must be reproducible.

## Evidence and unresolved questions

All model/evaluation evidence is empty pending M3.5 implementation. The
[source audit](source-audit.md) found no admitted session pairs in the inspected
public artifacts. The [annotation rubric](annotation-rubric.md) and revised
[workload protocol](workload-protocol.md) remain candidates for review before
label collection or training.
The [synthetic source instrument](instrumentation.md) exercises capture and
exclusion accounting only; its one admitted pair is not a real workload pair.
The proposed [sidecar and disposable lab decision](../../docs/adr/0018-private-source-sidecar-and-disposable-labs.md)
adds tooling for a future prospective window. Its synthetic tests and lab
snapshots do not constitute real pairs or permission to fit a predictor.
The founder selected real-workload utility prioritization as the target
direction on 2026-09-27 and approved only source feasibility work on
2026-09-28. A consented source, data provenance, privacy review, actual label
distribution and the final protocol still require review before training.
The [pretraining feasibility audit](feasibility-audit.md) identifies a
degenerate verifier-status target in the current valid corpus and two possible
routes to a useful comparison. Source discovery does not approve the model or
an improvement claim.
