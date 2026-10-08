# SPEC-043: Evidence-oriented AI tooling developer journey

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft specification; implementation, observations and human acceptance are pending.

## Purpose and scope

Expose a complete guided developer journey with faithful chat explanations, interaction graph and offline evidence exports.

## Authorities

Constitution clause zero and Articles 3–7, 12–16, 19–25; GOVERNANCE.md; operational semantics, claim discipline, ADRs 0019/0020 and proposed ADR 0021. This spec is subordinate to accepted authorities. See assurance.json for references and authority inventory.

## Requirements and acceptance scenarios

### REQ-001

Provide a reproducible owned synthetic journey from install/discovery through analysis/plan/grant refusal/execute/verify/recovery/export.

**SC-001:** Given fresh owned roots and registered fixture instances, when either supported host follows the journey, then every step retains input/output/candidate receipts and synthetic versus actual-host domains stay explicit.

Verification: [procedure_full_journey](validation-plan.md); [T001](tasks.md). Obtained evidence: none.

### REQ-002

Explain decisions with input identity, conflicts/dependencies, conditional premises, unknowns, assurance and observation limits.

**SC-002:** Given all analyzer classification classes, when chat summaries are generated, then each statement agrees with typed results and unknown is not mislabeled independent.

Verification: [procedure_faithful_summary](validation-plan.md); [T002](tasks.md). Obtained evidence: none.

### REQ-003

Explain advisory order and exact missing authority before opt-in execution.

**SC-003:** Given a prepared plan with absent or invalid grant, when the developer requests execution, then the host explains refusal and operator scope without issuing a grant or treating host approval as sufficient.

Verification: [procedure_authority_journey](validation-plan.md); [T003](tasks.md). Obtained evidence: none.

### REQ-004

Display actual private-result/verifier state and interruption/recovery outcomes with evidence links.

**SC-004:** Given successful, failed, cancelled and recovered runs, when the result is presented, then unfinished states never appear successful and source promotion/code correctness is not implied.

Verification: [procedure_result_journey](validation-plan.md); [T004](tasks.md). Obtained evidence: none.

### REQ-005

Render an interaction graph with semantic labels, accessible legend and bounded node/edge input.

**SC-005:** Given conflict/dependency/conditional/unknown edges and malformed graphs, when graph generation runs, then labels and color-independent styles preserve semantics or malformed/oversize data refuse.

Verification: [procedure_interaction_graph](validation-plan.md); [T005](tasks.md). Obtained evidence: none.

### REQ-006

Export deterministic Markdown, SVG and standalone HTML from selected evidence with hashes and provenance.

**SC-006:** Given identical typed input and versioned formatter, when each export repeats, then bytes/order/IDs are stable and receipt binds source/output hashes plus limits.

Verification: [procedure_deterministic_export](validation-plan.md); [T006](tasks.md). Obtained evidence: none.

### REQ-007

Escape and bound untrusted source/evidence in every export without scripts, remote references or secret inclusion.

**SC-007:** Given HTML/SVG injection, unsafe URIs and overlarge content, when export validation runs, then active/remote content and arbitrary reads refuse or are inert escaped text; no network/telemetry occurs.

Verification: [procedure_export_security](validation-plan.md); [T007](tasks.md). Obtained evidence: none.

### REQ-008

Provide clear onboarding, diagnostics, raw-evidence access and unsupported-rendering explanations in both hosts.

**SC-008:** Given missing feature and image rendering unsupported by a host, when journey presentation is requested, then bounded fallback and actionable diagnosis are visible; no native embedded UI capability is invented.

Verification: [procedure_onboarding_fallback](validation-plan.md); [T008](tasks.md). Obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Presentation of existing bounded typed results and selected owned evidence; output generation does not expand runtime authority or observation.

Hypothesis: Clear evidence-oriented presentation may help developers understand system potential; comprehension and usability need observations.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

SDK/documentation, structural checks, synthetic controls, actual host observations and independent reproduction have separate evidence domains. Passing one does not establish the others or human approval. Public APIs are additive experimental proposals with migration/versioning review during implementation.

## Evidence and unresolved questions

Planned procedures are in validation-plan.md; obtained evidence is empty in assurance.json. The packet records a proposed design, not a runtime acceptance result. Required decisions: technical contract/ADR adoption, exact host versions and installation scope, provider budget/source rights for capture, independent review and founder acceptance. See program.md in SPEC-039 and evaluation-protocol.md in SPEC-044.
