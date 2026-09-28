# SPEC-019 deferred tasks

The founder chose workload utility prioritization after the
[feasibility audit](feasibility-audit.md) and approved a limited
[source screen](source-audit.md). The [workload protocol](workload-protocol.md),
[annotation rubric](annotation-rubric.md) and actual data remain pending before
T001 can be completed. The bounded M3 experiment has founder review; no model
or M3.5 benefit is reported.

- [ ] T001 (REQ-001/002, SC-001..004): Complete source permission and
  prospective session/pair yield audit; review and freeze the sampling frame,
  human utility rubric, policy-blind holdout annotation, class coverage,
  features, family splits, baseline, calibration, cost rules and thresholds
  before training. The limited public screen is recorded; a consented source
  and eligible pair yield are still missing.
- [ ] T002 (REQ-001, SC-001/002): Implement offline trainer and versioned
  local inference with negative controls.
- [ ] T003 (REQ-002, SC-003/004): Evaluate held-out calibration when feasible,
  abstention, assessed-useful proposals, missing labels, reviewer disagreement
  and total analysis cost against the rule baseline.
- [ ] T004 (REQ-003, SC-005): Confirm verifier and execution boundaries.
- [ ] T005 (REQ-001..003): Capture evidence and request M3.5 review.
