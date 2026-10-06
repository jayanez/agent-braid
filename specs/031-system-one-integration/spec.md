# SPEC-031: Advisory integration across Agent Braid decision stages

## Purpose and scope

Expose native System 1 recommendations for every architectural stage through an explicit registry of capabilities. Only enabled, evidenced consumers are integrated; arbitrary host actions and runtime scope expansion are excluded.

Status: draft planning, human review pending. Dependencies: SPEC-028 accepted contracts; implementation can use a rule backend while SPEC-030 research remains pending. Live learned use waits for SPEC-030 selection and SPEC-033 promotion.
Milestone: S1.3 — Advisory integration. See the [program](../028-system-one-core/program.md)
and [source-backed analysis](../028-system-one-core/reference-analysis.md).

User scenarios: an analyzer operator requests bounded advice and inspectable reasons;
a host gets a precise abstention/fallback when input is unsupported; a maintainer
compares decision quality and complete cost without weakening semantic verification.

## Authorities

Constitution clause zero and Articles 2–7, 9, 12–16, 19–25; GOVERNANCE.md;
ADRs 0017, 0019, 0020; operational semantics; claim discipline; existing versioned
contracts. Proposed architecture choices stay feature-local until separately adopted.
No constitutional amendment, runtime authorization or scientific claim is implied.

## Requirements and acceptance scenarios

- **REQ-001 — Capability registry and scope.** Declare consumer, domain, evidence, fallback and authorization boundary for every proposed use.
  - **SC-001:** Given a request for an unsupported operation/tool/effect domain, when capability discovery or routing occurs, then it reports unavailable or advisory-only rather than claiming universal enhancement.
- **REQ-002 — Immutable context and semantic gates.** Preserve operation identities, resource versions, declared/observed effects and unresolved uncertainty.
  - **SC-002:** Given a candidate recommendation and stale resources or incomplete effects, when an analyzer or scheduler consumes it, then it revalidates supported premises and never turns unknown into verified commuting.
- **REQ-003 — Verifier-work prioritization.** Support advice to rank candidates and choose analysis depth within a matched budget.
  - **SC-003:** Given eligible SPEC-018 pairs or fixed-patch SPEC-012 analysis inputs, when System 1 prioritizes review, then the unchanged verifier determines outcomes and original keep-order remains the fallback.
- **REQ-004 — Execution and recovery boundary.** Predictions cannot issue operator grants, alter manifests, broaden execution language or bypass recovery verification.
  - **SC-004:** Given a malicious recommendation or repeated decision during recovery, when runtime policy consumes advisory data, then unauthorized allocation/publication is refused and grant/plan binding is unchanged.
- **REQ-005 — Portable transport and compatibility.** Expose versioned local CLI/library and optional read-only MCP advice, preserving current host protocols.
  - **SC-005:** Given a supported bounded request or unsupported protocol revision, when advice is transported, then schemas, timeout and errors stay precise; existing execution tools and authorization semantics remain unchanged.
- **REQ-006 — End-to-end utility and diagnostics.** Measure each enabled decision stage including advice, fallback, verifier and runtime overhead.
  - **SC-006:** Given shadow advice that disagrees with observed outcomes, when the evaluation report is produced, then disagreement and unknowns remain visible; no M4 closure or scientific assurance is inferred.

## Scientific boundaries and compatibility

Hypothesis H1: Prioritizing analysis work and selecting appropriate decision paths may save time without weakening verification; this is distinct from M4 parallel execution speedup.
Heuristic confidence is not a proof of effects, commutation, confluence, braid laws
or execution safety. Preserve SPEC-019 eligibility/label construct and SPEC-021 G4
NO-GO; this track cannot close M3.5 or M4. Legacy versions and default behavior remain
unchanged; planned APIs/extras are additive and need their own contract review.

## Clarifications and unresolved decisions

The user requests own analogous capabilities, no upstream package/model integration,
an unbiased comparison and complete Spec Kit implementation planning. Public repository
documents remain English; the user-facing explanation is Spanish. Starting with typed
Strands-like contracts does not preselect a decoder model. Unknowns that do not block
planning are explicit implementation gates: consented source/yield, available deployment
hardware, paid/training budgets, final base-model rights and per-capability promotion.
No dataset, hardware support or approval has been invented. Remote delivery authorization
is tracked separately from feature acceptance.

## Evidence and unresolved questions

Source inspection is in the analysis manifest; planned validation is in
[validation-plan.md](validation-plan.md). Feature/model/workload acceptance evidence:
none. All obtained_evidence arrays are empty and human_review is pending. Passing
planning validators establishes artifact structure, not implementation or utility.
