# SPEC-025 tasks

T001-T006 are technically complete within the bounded delivery recorded in
`evidence/technical-delivery.json`. T007 remains pending final stable PR validation,
candidate freeze and specific independent proof review. Checkmarks describe technical
protocol delivery, never scientific proof acceptance or human/founder approval.
Finite validation, feasibility and proof review retain separate outputs; negative
or inconclusive findings may complete their documented protocol.

- [x] T001 (REQ-001/SC-001): Write exact candidate statements and premise/source inventory
  - Dependencies: none.
  - Targets: `research/proofs/` T1/T2 candidate statements/premise mapping; feature proof-status inventory.
  - Commands: planned PremiseInventoryReview in quickstart; compare source hashes and named authority statements.
  - Evidence: carriers/quantifiers/equivalences, complete premise inventory, exact source bindings, open gaps and claim labels; no accepted proof yet.
- [x] T002 (REQ-002/SC-002, REQ-002/SC-003): Implement the source-bound finite continuation checker
  - Dependencies: T001; review new experimental research request/report interface and versioning impact.
  - Targets: `research/contextual_lab/` parser/checker/evidence/CLI, new experimental contracts, `tests/test_contextual_lab.py`.
  - Commands: planned SC-002/SC-003 tests and CLI check/verify from quickstart.
  - Evidence: prefix replay, suffix/observation binding, enabledness/results/versions traces, cap accounting, minimized witnesses and tamper rejection.
- [x] T003 (REQ-003/SC-004): Freeze and execute omitted-premise and trace controls
  - Dependencies: T002; freeze corpus/suffix manifest before execution.
  - Targets: `examples/contextual-lab/`, control tests, feature finite-evidence directory.
  - Commands: planned `ContextualControlsTests.test_omitted_premises_and_event_order` and manifest checker.
  - Evidence: per-control outcomes, missing/inconclusive coverage and exact chronology witnesses; only bounded claims.
- [x] T004 (REQ-004/SC-005): Prepare anchored proof and independent executable-mapping cross-check
  - Dependencies: T001, T003.
  - Targets: `research/proofs/` anchored candidate proof and mapping, `scripts/crosscheck_contextual_proof_mapping.py`, mapping tests.
  - Commands: planned AnchoredProofReview, SC-005 mapping test and quickstart cross-check command.
  - Evidence: set-union/flattening derivation, closure/residual/intent premises, far/adjacent/involutive relations, exact source hashes and excluded-model controls.
- [x] T005 (REQ-006/SC-007): Assess proof review and optional tool value for a named gap
  - Dependencies: T001, T004.
  - Targets: feature proof/tool assessment and proposed ADR only if concrete adoption value survives.
  - Commands: planned ProofAndToolDecisionReview; primary documentation review only, no automatic download/install.
  - Evidence: handwritten/mechanized alternatives, trusted-base/mapping/cost/license assessment, no-tool/infeasible option; ADR/founder gate remains before adoption.
- [x] T006 (REQ-005/SC-006): Audit CoAgent artifact availability, rights and semantic comparison readiness
  - Dependencies: T001; independent of bounded checker implementation after premise inventory.
  - Targets: feature CoAgent feasibility report mapped to `AT-2026-005-coagent-comparator`; no change to adopted disposition without review.
  - Commands: planned CoAgentFeasibilityReview; read primary pinned sources/artifact/license metadata, no automatic third-party execution.
  - Evidence: immutable refs, availability/license matrix, state/effect/observation/execution mapping, gaps and abstention; executable comparator requires a separate authorized isolated protocol.
- [ ] T007 (REQ-006/SC-007): Reproduce bounded results and submit source-bound proof review packet
  - Dependencies: T003, T004, T005, T006.
  - Targets: feature reproduction/report/review packet and assurance; `research/proofs/` status records.
  - Commands: planned clean-clone repetition, quick and stable PR profiles; snapshot/freeze clean candidate; specific independent proof review.
  - Evidence: raw finite results and exact commands, separate proof reviewer findings/status, unresolved gaps, scientific limits and explicit human/founder status; no theorem until warranted.

## Obtained technical evidence and pending gates

- SC-001: source-bound `premise-inventory.json` and anchored candidate document; candidate statements and open mapping obligations only.
- SC-002/SC-003: reviewed experimental contract, unchanged-interpreter checker, 20 focused tests and two byte-identical CLI check/verify repetitions.
- SC-004: pinned manifest/expected controls retain omitted premises, raw chronology and inconclusive coverage.
- SC-005: independent finite oracle checks 32 orders and exchange relations; Luna technical mapping review has no remaining actionable finding. Specific proof acceptance is pending.
- SC-006: CoAgent primary-source feasibility assessment records unavailable executable rights/revision and semantic mismatch, without third-party execution.
- SC-007: no-tool/handwritten-first assessment and internal clean clone packet obtained; final stable PR profile, candidate freeze and specific independent proof review remain pending.

Exact paths, SHA-256 bindings, executed command outputs and scenario/test mapping
are in `evidence/technical-delivery.json` and `evidence/internal-clean-clone.json`.
The repetition shares maintainer, host and an existing isolated Python environment;
it is not independent external reproduction. Human/founder approval and accepted
proof status remain pending. Historical premise-inventory status fields retain their
original capture boundary; current obtained finite evidence is recorded separately.
