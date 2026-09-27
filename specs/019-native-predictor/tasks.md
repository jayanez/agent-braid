# SPEC-019 deferred tasks

The founder chose workload utility prioritization after the
[feasibility audit](feasibility-audit.md). The detailed
[workload protocol](workload-protocol.md) and its actual data remain pending
before T001 can be completed. The bounded M3 experiment has founder review;
no model or M3.5 benefit is reported.

- [ ] T001 (REQ-001/002, SC-001..004): Review and freeze actual data, features,
  utility labels, family splits, baseline and thresholds before training.
- [ ] T002 (REQ-001, SC-001/002): Implement offline trainer and versioned
  local inference with negative controls.
- [ ] T003 (REQ-002, SC-003/004): Evaluate held-out calibration, abstention,
  useful proposals and cost against the rule baseline.
- [ ] T004 (REQ-003, SC-005): Confirm verifier and execution boundaries.
- [ ] T005 (REQ-001..003): Capture evidence and request M3.5 review.
