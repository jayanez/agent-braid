# Tasks

## Development status — 2026-10-08

Exact source rights and protocol are approved for bounded implementation and
preparation. See [implementation readiness](implementation-readiness.md) for the
scoped decision and current gates. Earlier proposal descriptions below retain
their design-time context; stable review, capture and whole-M4 acceptance remain pending.

T002 approval of the exact source/protocol permits bounded C08 implementation
and evaluation preparation under the user-authorized goal. It does not permit
registered capture. T004 requires a separately reviewed stable candidate and
manifest before exact capture authorization. Dependencies sequence work; they
do not change those boundaries.

- [ ] T001 (REQ-001/SC-001,SC-002): Freeze source rights and exact prospective frame.
  Dependencies: none. Targets: `source-rights-manifest.json; exact rights receipts; immutable source commits`.
  Verification and planned evidence: Identify rightsholders, provenance, exact M4 permission/retention terms, then retain the complete candidate/exclusion frame and assess current runtime limits. No source execution or substitution. Planned: `evidence/sc-001.json; evidence/sc-002.json`. Obtained: none.

- [ ] T002 (REQ-001,REQ-002,REQ-003/SC-001,SC-002,SC-003,SC-004,SC-005): Obtain exact protocol/source-rights review.
  Dependencies: T001. Targets: `protocol-review-packet.md; separate exact human decision record`.
  Verification and planned evidence: Review exact source/rights, task relevance, frame, current limits, denominator, order, costs, refusals, recovery, budgets and stops. An approved decision permits only the bounded C08 harness and evaluation-preparation work; no registered capture. Planned: `evidence/sc-007.json`. Obtained: nine written owner decisions, consolidated in the separate local `spec038-exact-source-protocol-decision-20261008.json` receipt; public evidence packaging and dependency admission remain pending.

- [ ] T003 (REQ-002,REQ-003/SC-003,SC-004,SC-005): Implement the narrow harness slice and prepare a candidate manifest.
  Dependencies: approved T002 and confirmed exact source feasibility. Targets: `one narrow runner; focused novel-invariant tests; successor plan.md, tasks.md and quickstart.md; candidate manifest`.
  Verification and planned evidence: Reuse current SPEC-020 runtime, grant, verifier and accounting. Refuse malformed/stale/unsafe authority and wrong trees. Run appropriate quick and PR validation for the stable candidate; do not capture registered results. Planned: candidate-bound controls and validation receipts. Obtained: none.

- [ ] T004 (REQ-002,REQ-005/SC-003,SC-007): Freeze and independently review the stable harness and manifest.
  Dependencies: T003. Targets: `frozen candidate; exact workload manifest; independent review record`.
  Verification and planned evidence: Review candidate/input hashes, supported operation scope, refusal/recovery, verifier and complete accounting. This is a separate boundary; it does not itself capture results. Planned: `evidence/sc-007.json`. Obtained: none.

- [ ] T005 (REQ-002,REQ-003/SC-003,SC-004,SC-005): Capture only under separate exact authorization.
  Dependencies: approved T004 and exact capture decision. Targets: `raw observation index; environment/candidate receipt; pair outcomes`.
  Verification and planned evidence: Run only the reviewed SPEC-021 policy coordinator in `--mode serial` and `--mode parallel`, using the frozen AB/BA orders, 4 warm-up pairs, 6 measured pairs, exact schedule, budgets, full total-wall phases, and fresh-process control. Preserve all slots, failures, refusals, recoveries and costs. No source-code/test/hook/network/provider execution. Planned: `evidence/sc-003.json` through `evidence/sc-005.json`. Obtained: none.

- [ ] T006 (REQ-003,REQ-004/SC-004,SC-005,SC-006): Reconcile all outcomes and interpret limits.
  Dependencies: T005 or a documented infeasible exit. Targets: `bounded result packet; denominator and source-integrity audit`.
  Verification and planned evidence: Report all intended, attempted, valid, invalid, failed, refused, recovered and unexecuted rows, plus full cost and unsupported yield. Negative, null, inconclusive and infeasible outcomes are valid. Planned: `evidence/sc-004.json` through `evidence/sc-006.json`. Obtained: none.

- [ ] T007 (REQ-004,REQ-005/SC-006,SC-008): Prepare independent review and the whole-M4 decision packet.
  Dependencies: T006. Targets: `bounded packet; SPEC-021 six-row reconciliation; separate founder decision`.
  Verification and planned evidence: Preserve the historical SPEC-021 G4 NO-GO, audit all six rows, and require a new explicit founder whole-M4 decision before changing milestone status. Planned: `evidence/sc-008.json`. Obtained: none.

These future tasks do not authorize concurrent agents, source execution,
registered capture, or milestone acceptance. Research completion does not
depend on a favorable utility result.
