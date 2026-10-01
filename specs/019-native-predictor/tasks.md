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
- [x] T006 (REQ-002, SC-006): Instrument an owned local flow with
  immutable base/operation events, stable IDs and provenance. Publish a
  deterministic synthetic capture and session/pair exclusion report, including
  invalid-base, unsupported-operation, invalid-anchor and missing-provenance
  cases. Record zero real admitted pairs; this demonstration cannot complete
  P019-01 or T001.
- [x] T008 (REQ-002, SC-007): Build a prospective local authoring sidecar,
  admission ledger and all-pairs adapter, plus exact-file filtered lab
  exporter and metadata-only remote seal validator. Exercise synthetic
  adversarial cases and document the two private lab and audit repositories.
  This completes tooling only: no real source window, admitted real pair,
  utility label or upstream completeness finding is asserted. The two
  read-only source deploy keys and lab Actions syncs were verified on actual
  runners on 2026-10-01; those operational results do not register a real
  source window or complete T001/P019-01.
- [ ] T007 (REQ-002, SC-003/004): In a later source-feasibility phase, audit
  existing session feeds only after owner permission, participant/data rights
  and privacy review. Kinetiq and SmartNotes are candidate owned-repository
  families from the 2026-09-29 structural screen; neither has an observed feed
  or eligible pair yet. First review the proposed local sidecar signals
  (`session-open`, actor `base-seen`, `insert-proposed`, `session-close`) against
  a real authoring boundary; verify shared-base independent intent from
  contemporaneous receipts and reconcile journal completeness with the source
  admission register. Version an adapter for all sessions, operations and
  unordered pairs with T008's prospective adapter rather than treating
  T006's exactly-two-operation synthetic CLI as a real feed. Preserve the
  separate repo-level feasibility records,
  fix a contiguous window only after all gates pass, enumerate all sessions
  and candidate pairs, report eligibility and exclusions by family, and reject
  Git-only histories that lack the shared-base event relation. SmartNotes
  patient and clinical payloads, Kinetiq athlete/customer data, and all
  private content stay excluded and outside this repository.
- [ ] T002 (REQ-001, SC-001/002): Implement offline trainer and versioned
  local inference with negative controls.
- [ ] T003 (REQ-002, SC-003/004): Evaluate held-out calibration when feasible,
  abstention, assessed-useful proposals, missing labels, reviewer disagreement
  and total analysis cost against the rule baseline.
- [ ] T004 (REQ-003, SC-005): Confirm verifier and execution boundaries.
- [ ] T005 (REQ-001..003): Capture evidence and request M3.5 review.
