# SPEC-041: Portable product skills for AI tooling

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft specification; implementation, observations and human acceptance are pending.

## Purpose and scope

Ship five portable product skills guiding analysis, planning, already-granted execution, recovery and evidence in Codex and Claude Code.

## Authorities

Constitution clause zero and Articles 3–7, 12–16, 19–25; GOVERNANCE.md; operational semantics, claim discipline, ADRs 0019/0020 and proposed ADR 0021. This spec is subordinate to accepted authorities. See assurance.json for references and authority inventory.

## Requirements and acceptance scenarios

### REQ-001

Maintain one Agent Skills-compliant canonical bundle with five matching names/descriptions and minimal host-specific metadata.

**SC-001:** Given packaged bundle and both supported hosts, when static validation then actual discovery runs, then all five names load at recorded versions; static format checks alone do not count as host discovery.

Verification: [procedure_portable_bundle](validation-plan.md); [T001](tasks.md). Obtained evidence: none.

### REQ-002

Guide analyze through immutable input selection, conflict/conditional/unknown explanation and evidence references without execute.

**SC-002:** Given independent, conflicting and unresolved operations, when agent-braid-analyze is used, then the explanation matches the analyzer and observation domain; no analysis verdict grants execution.

Verification: [procedure_analyze_skill](validation-plan.md); [T002](tasks.md). Obtained evidence: none.

### REQ-003

Guide plan through existing prepare and disclose order, constraints, plan digest and absent operator authority.

**SC-003:** Given an admissible batch and missing grant, when agent-braid-plan is used, then the plan is advisory with explicit missing permission and no model-issued grant.

Verification: [procedure_plan_skill](validation-plan.md); [T003](tasks.md). Obtained evidence: none.

### REQ-004

Guide execute only for an already granted exact prepared batch, then status and independent verify.

**SC-004:** Given matching and wrong/expired grant references, when agent-braid-execute is used, then the matching bounded result is verified or the request refuses; no secret/grant-store edits or bypass instruction occurs.

Verification: [procedure_execute_skill](validation-plan.md); [T004](tasks.md). Obtained evidence: none.

### REQ-005

Guide interruption inspection and bounded recovery using current state, existing authority and verification.

**SC-005:** Given an interrupted owned run or unknown/mismatched run, when agent-braid-recover is used, then the actual recovery/verifier outcome is reported and mismatched authority refuses.

Verification: [procedure_recover_skill](validation-plan.md); [T005](tasks.md). Obtained evidence: none.

### REQ-006

Guide evidence explanations/exports with input identity, artifact links, observation/assurance limits and unknowns.

**SC-006:** Given verified, failed and inconclusive records, when agent-braid-evidence is used, then chat and export retain actual outcomes and cannot imply code correctness, general confluence or speedup.

Verification: [procedure_evidence_skill](validation-plan.md); [T006](tasks.md). Obtained evidence: none.

### REQ-007

Handle unavailable MCP, skills or unsupported host features with actionable diagnostics and bounded read-only fallback.

**SC-007:** Given missing MCP dependency/configuration and an execution request, when a workflow cannot connect, then the skill reports the missing capability; only documented read-only CLI fallback is offered.

Verification: [procedure_missing_capability](validation-plan.md); [T007](tasks.md). Obtained evidence: none.

### REQ-008

Separate skill guidance from host permission and grant enforcement, with adversarial instructions and no hooks/helper-agent side effects.

**SC-008:** Given repo/evidence text requesting grants, secrets or false success, when workflow guidance reads the text, then it treats text as untrusted and respects deterministic refusal; no hidden configuration, hooks or authority changes ship.

Verification: [procedure_adversarial_guidance](validation-plan.md); [T008](tasks.md). Obtained evidence: none.

## Scientific boundaries and compatibility

Domain: Instruction guidance over the exact MCP/CLI contracts; skills are not effect enforcement, operator authority or mathematical proof.

Hypothesis: Focused portable guidance may improve workflow completion and evidence fidelity; model compliance and positive utility are not presumed.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

SDK/documentation, structural checks, synthetic controls, actual host observations and independent reproduction have separate evidence domains. Passing one does not establish the others or human approval. Public APIs are additive experimental proposals with migration/versioning review during implementation.

## Evidence and unresolved questions

Planned procedures are in validation-plan.md; obtained evidence is empty in assurance.json. The packet records a proposed design, not a runtime acceptance result. Required decisions: technical contract/ADR adoption, exact host versions and installation scope, provider budget/source rights for capture, independent review and founder acceptance. See program.md in SPEC-039 and evaluation-protocol.md in SPEC-044.
