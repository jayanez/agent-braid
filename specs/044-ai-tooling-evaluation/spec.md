# SPEC-044: AI tooling evaluation and closure

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft specification; implementation, observations and human acceptance are pending.

## Purpose and scope

Register and execute candidate-bound deterministic controls, clean reproduction, actual Codex/Claude journeys and a complete-cost three-arm comparison.

## Authorities

Constitution clause zero and Articles 3–7, 12–16, 19–25; GOVERNANCE.md; operational semantics, claim discipline, ADRs 0019/0020 and proposed ADR 0021. This spec is subordinate to accepted authorities. See assurance.json for references and authority inventory.

## Requirements and acceptance scenarios

### REQ-001

Preregister exact population, source rights, candidate/input/host/model versions, all attempts, rubric and numerical caps before capture.

**SC-001:** Given unapproved paid capture or a drifted/missing registration, when capture admission runs, then unapproved costs/rights/versions refuse; owned deterministic controls remain a separately identified engineering path.

Verification: [procedure_registration_gate](validation-plan.md); [T001](tasks.md). Obtained evidence: none.

### REQ-002

Obtain actual discovery, five-skill loading and complete basic journey receipts in both selected macOS arm64 hosts.

**SC-002:** Given a real host and a mock protocol client, when host support is assessed, then only real host receipts satisfy host acceptance, with exact build/model/bundle and interactive blocks reported.

Verification: [procedure_actual_host_observation](validation-plan.md); [T002](tasks.md). Obtained evidence: none.

### REQ-003

Run parity, malformed/stale/unsafe/grant/cancellation/recovery and output-agreement controls with exact oracle outcomes.

**SC-003:** Given all mandatory positive/negative control cases, when deterministic validation runs, then zero unauthorized effects, false successes or authority exposures occur; every attempted failure remains recorded.

Verification: [procedure_negative_controls](validation-plan.md); [T003](tasks.md). Obtained evidence: none.

### REQ-004

Reproduce installed-package/core/protocol controls on clean macOS arm64 and Linux x86_64 environments.

**SC-004:** Given separate clean environments and frozen artifacts, when reproduction runs, then candidate/environment/commands/results are bound; Linux protocol results do not claim real-host adoption.

Verification: [procedure_clean_reproduction](validation-plan.md); [T004](tasks.md). Obtained evidence: none.

### REQ-005

Compare CLI, MCP-only and MCP-plus-skills on 108 registered attempts with counterbalanced order and no outcome-driven revisions.

**SC-005:** Given the three-arm fixture roster and isolated sessions, when all slots are processed, then completion, interventions and fidelity are compared with full denominators, failures and carryover disclosed.

Verification: [procedure_three_arm_comparison](validation-plan.md); [T005](tasks.md). Obtained evidence: none.

### REQ-006

Measure complete setup/provider/tool/runtime/export/user/reviewer costs with unavailable fields explicit and numerical stops enforced.

**SC-006:** Given missing tokens, overlapping phases, exceeded budget and provider failure, when cost accounting and admission run, then unknown differs from zero, wall totals are not double-counted and exceeded/blocked attempts stop without silent retry.

Verification: [procedure_complete_cost](validation-plan.md); [T006](tasks.md). Obtained evidence: none.

### REQ-007

Apply frozen human rubric and descriptive thresholds, report disagreements/missing labels and preserve legitimate negative results.

**SC-007:** Given 16/18 completion threshold, a host failure or unresolved scoring, when the report is interpreted, then per-host denominators and uncertainty remain visible; safety failures block acceptance and no general causal speedup claim is inferred.

Verification: [procedure_interpretation](validation-plan.md); [T007](tasks.md). Obtained evidence: none.

### REQ-008

Freeze candidate/evidence, obtain independent technical review and explicit founder scope/closure decision with historical M4 limits.

**SC-008:** Given a bounded completed or inconclusive report, when the decision packet is assembled, then implementation/protocol/human gates are separated; M4.5 acceptance cannot reverse M4 G4 NO-GO or close M4.

Verification: [procedure_acceptance_decision](validation-plan.md); [T008](tasks.md). Obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Exact local host/model builds on macOS arm64 and owned registered fixture population; Linux x86_64 core/protocol reproduction is a separate domain.

Hypothesis: MCP plus skills may improve completion, interventions or evidence fidelity over CLI/MCP-only. Negative, null and infeasible outcomes are valid.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

SDK/documentation, structural checks, synthetic controls, actual host observations and independent reproduction have separate evidence domains. Passing one does not establish the others or human approval. Public APIs are additive experimental proposals with migration/versioning review during implementation.

## Evidence and unresolved questions

Planned procedures are in validation-plan.md; obtained evidence is empty in assurance.json. The packet records a proposed design, not a runtime acceptance result. Required decisions: technical contract/ADR adoption, exact host versions and installation scope, provider budget/source rights for capture, independent review and founder acceptance. See program.md in SPEC-039 and evaluation-protocol.md in SPEC-044.
