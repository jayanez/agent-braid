# M4.5 issue drafts

Source drafts materialized under GITHUB_TRACKING.md as [Open milestone #19](https://github.com/jayanez/agent-braid/milestone/19) with six spec parents and 60 task subissues. See [administrative-registration.md](administrative-registration.md) for issue links and reconciliation evidence. All issues are open; the six parents are Review pending in the private Project and the tasks are Todo.

## Milestone

Title: M4.5 — AI tooling integrations for Codex and Claude Code

Description: See program.md acceptance criteria. Consumes existing M4 contracts; v1 Codex/Claude Code only. Actual host/evaluation and founder acceptance pending. No assumed M4 closure or new effects.

## SPEC-039 parent

Title: SPEC-039: AI tooling integration program

Labels: spec. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

<!-- agent-braid-spec-id: SPEC-039 -->

Source: specs/039-ai-tooling-program/spec.md. Scope, acceptance and limits are authoritative there; implementation tasks below are not approval.

### SPEC-039/T001

<!-- agent-braid-task-id: SPEC-039/T001 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T001 (REQ-001/SC-001): Separate current capability, planned integration, evidence and adoption in a versioned matrix for Codex and Claude Code.
  Dependencies: none; consumed contract review. Targets: `capability-matrix.md`.
  Verification and planned evidence: `validation-plan.md::procedure_capability_matrix`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.


### SPEC-039/T002

<!-- agent-braid-task-id: SPEC-039/T002 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T002 (REQ-002/SC-002): Keep M4.5 adjacent to M4 while preserving its separately governed bounded acceptance, historical G4 NO-GO and independent M3/M3.5 gates.
  Dependencies: T001. Targets: `program.md; historical M4 boundary audit`.
  Verification and planned evidence: `validation-plan.md::procedure_m4_boundary`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.


### SPEC-039/T003

<!-- agent-braid-task-id: SPEC-039/T003 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T003 (REQ-003/SC-003): Maintain six subordinate specs with stable requirement/scenario/task identities and complete evidence obligations.
  Dependencies: T001. Targets: `specs/039–044; analysis.md`.
  Verification and planned evidence: `validation-plan.md::procedure_traceability`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.


### SPEC-039/T004

<!-- agent-braid-task-id: SPEC-039/T004 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T004 (REQ-004/SC-004): Propose the portable architecture through ADR 0021 without rewriting constitutional or runtime authority.
  Dependencies: T001. Targets: `docs/adr/0021-codex-claude-tooling-integration.md`.
  Verification and planned evidence: `validation-plan.md::procedure_architecture_review`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.


### SPEC-039/T005

<!-- agent-braid-task-id: SPEC-039/T005 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T005 (REQ-005/SC-005): Record official-source research with retrieval date, chosen versions, alternatives and unverified host claims.
  Dependencies: T001. Targets: `research.md`.
  Verification and planned evidence: `validation-plan.md::procedure_research_provenance`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.


### SPEC-039/T006

<!-- agent-braid-task-id: SPEC-039/T006 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T006 (REQ-006/SC-006): Prepare one milestone, six parents and every task subissue under governed reviewed-source tracking.
  Dependencies: T001–T005. Targets: `issue-drafts.md; docs/development/github-tracking.json; tracking receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_tracking_scope`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.


### SPEC-039/T007

<!-- agent-braid-task-id: SPEC-039/T007 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T007 (REQ-007/SC-007): Document five future routes and explicitly defer Cursor, VS Code/Copilot, OpenCode and pi from v1.
  Dependencies: T001–T005. Targets: `program.md future routes`.
  Verification and planned evidence: `validation-plan.md::procedure_future_scope`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.


### SPEC-039/T008

<!-- agent-braid-task-id: SPEC-039/T008 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T008 (REQ-008/SC-008): Require candidate-bound technical review, actual host evidence and explicit founder acceptance before M4.5 closure.
  Dependencies: T001–T005. Targets: `SPEC-044 decision packet; future closure record`.
  Verification and planned evidence: `validation-plan.md::procedure_closure_boundary`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.


### SPEC-039/T009

<!-- agent-braid-task-id: SPEC-039/T009 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.


### SPEC-039/T010

<!-- agent-braid-task-id: SPEC-039/T010 -->

Parent: SPEC-039. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.


## SPEC-040 parent

Title: SPEC-040: Portable MCP tooling surface

Labels: spec. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

<!-- agent-braid-spec-id: SPEC-040 -->

Source: specs/040-portable-mcp-surface/spec.md. Scope, acceptance and limits are authoritative there; implementation tasks below are not approval.

### SPEC-040/T001

<!-- agent-braid-task-id: SPEC-040/T001 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T001 (REQ-001/SC-001): Use mcp==2.3.0 as an isolated optional tooling extra, with core dependencies empty and stdio-only operation.
  Dependencies: none; consumed contract review. Targets: `pyproject.toml optional tooling extra; packaging controls`.
  Verification and planned evidence: `validation-plan.md::procedure_optional_sdk`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.


### SPEC-040/T002

<!-- agent-braid-task-id: SPEC-040/T002 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T002 (REQ-002/SC-002): Support 2026-07-28 discovery and 2025-11-25 initialization through the SDK while preserving the legacy endpoint.
  Dependencies: T001. Targets: `agent_braid/tooling_mcp.py SDK lifecycle; protocol controls`.
  Verification and planned evidence: `validation-plan.md::procedure_protocol_compatibility`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.


### SPEC-040/T003

<!-- agent-braid-task-id: SPEC-040/T003 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T003 (REQ-003/SC-003): Expose analyze-work for tagged AIM/Git/worktree requests and preserve analyze/prepare/status/execute/recover/verify result semantics.
  Dependencies: T001. Targets: `analysis.py and git_adapter.py delegation; CLI parity controls`.
  Verification and planned evidence: `validation-plan.md::procedure_cli_parity`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.


### SPEC-040/T004

<!-- agent-braid-task-id: SPEC-040/T004 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T004 (REQ-004/SC-004): Declare bounded input/output schemas and a typed evidence envelope whose text and structuredContent agree.
  Dependencies: T001. Targets: `tooling_mcp.py schemas/envelope; data-model.md`.
  Verification and planned evidence: `validation-plan.md::procedure_schema_and_summary`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.


### SPEC-040/T005

<!-- agent-braid-task-id: SPEC-040/T005 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T005 (REQ-005/SC-005): Bind canonical source/result/grant roots before launch and default to analysis-only advertised capabilities.
  Dependencies: T001. Targets: `tooling_mcp.py configured roots/mode; containment controls`.
  Verification and planned evidence: `validation-plan.md::procedure_root_and_mode`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.


### SPEC-040/T006

<!-- agent-braid-task-id: SPEC-040/T006 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T006 (REQ-006/SC-006): Delegate execution/recovery to existing exact grants and policy checks; never expose grant issuance to a model.
  Dependencies: T001–T005. Targets: `mcp_runtime.RuntimeTools delegation; existing runtime_policy grant controls`.
  Verification and planned evidence: `validation-plan.md::procedure_grant_boundary`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.


### SPEC-040/T007

<!-- agent-braid-task-id: SPEC-040/T007 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T007 (REQ-007/SC-007): Propagate timeout/cancellation and concurrency to existing point-of-use checks, locking and recoverable state.
  Dependencies: T001–T005. Targets: `tooling_mcp.py cancellation/concurrency bridge; interruption controls`.
  Verification and planned evidence: `validation-plan.md::procedure_cancellation_recovery`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.


### SPEC-040/T008

<!-- agent-braid-task-id: SPEC-040/T008 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T008 (REQ-008/SC-008): Provide bounded capabilities/status/evidence manifests and digest/range chunk URIs with complete-result reconstruction controls, plus three read-only prompts without arbitrary file reads or automatic execution.
  Dependencies: T001–T005. Targets: `tooling_mcp.py resources/prompts; owned artifact inventory`.
  Verification and planned evidence: `validation-plan.md::procedure_resources_prompts`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.


### SPEC-040/T009

<!-- agent-braid-task-id: SPEC-040/T009 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.


### SPEC-040/T010

<!-- agent-braid-task-id: SPEC-040/T010 -->

Parent: SPEC-040. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.


## SPEC-041 parent

Title: SPEC-041: Portable product skills for AI tooling

Labels: spec. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

<!-- agent-braid-spec-id: SPEC-041 -->

Source: specs/041-ai-tooling-skills/spec.md. Scope, acceptance and limits are authoritative there; implementation tasks below are not approval.

### SPEC-041/T001

<!-- agent-braid-task-id: SPEC-041/T001 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T001 (REQ-001/SC-001): Maintain one Agent Skills-compliant canonical bundle with five matching names/descriptions and minimal host-specific metadata.
  Dependencies: none; consumed contract review. Targets: `integrations/agent-braid/skills; host metadata and bundle format controls`.
  Verification and planned evidence: `validation-plan.md::procedure_portable_bundle`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.


### SPEC-041/T002

<!-- agent-braid-task-id: SPEC-041/T002 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T002 (REQ-002/SC-002): Guide analyze through immutable input selection, conflict/conditional/unknown explanation and evidence references without execute.
  Dependencies: T001. Targets: `skills/agent-braid-analyze/SKILL.md; analyze journey controls`.
  Verification and planned evidence: `validation-plan.md::procedure_analyze_skill`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.


### SPEC-041/T003

<!-- agent-braid-task-id: SPEC-041/T003 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T003 (REQ-003/SC-003): Guide plan through existing prepare and disclose order, constraints, plan digest and absent operator authority.
  Dependencies: T001. Targets: `skills/agent-braid-plan/SKILL.md; plan journey controls`.
  Verification and planned evidence: `validation-plan.md::procedure_plan_skill`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.


### SPEC-041/T004

<!-- agent-braid-task-id: SPEC-041/T004 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T004 (REQ-004/SC-004): Guide execute only for an already granted exact prepared batch, then status and independent verify.
  Dependencies: T001. Targets: `skills/agent-braid-execute/SKILL.md; authority/refusal controls`.
  Verification and planned evidence: `validation-plan.md::procedure_execute_skill`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.


### SPEC-041/T005

<!-- agent-braid-task-id: SPEC-041/T005 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T005 (REQ-005/SC-005): Guide interruption inspection and bounded recovery using current state, existing authority and verification.
  Dependencies: T001. Targets: `skills/agent-braid-recover/SKILL.md; interruption controls`.
  Verification and planned evidence: `validation-plan.md::procedure_recover_skill`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.


### SPEC-041/T006

<!-- agent-braid-task-id: SPEC-041/T006 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T006 (REQ-006/SC-006): Guide evidence explanations/exports with input identity, artifact links, observation/assurance limits and unknowns.
  Dependencies: T001–T005. Targets: `skills/agent-braid-evidence/SKILL.md; evidence fidelity controls`.
  Verification and planned evidence: `validation-plan.md::procedure_evidence_skill`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.


### SPEC-041/T007

<!-- agent-braid-task-id: SPEC-041/T007 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T007 (REQ-007/SC-007): Handle unavailable MCP, skills or unsupported host features with actionable diagnostics and bounded read-only fallback.
  Dependencies: T001–T005. Targets: `skill references/diagnostics; unavailable MCP controls`.
  Verification and planned evidence: `validation-plan.md::procedure_missing_capability`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.


### SPEC-041/T008

<!-- agent-braid-task-id: SPEC-041/T008 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T008 (REQ-008/SC-008): Separate skill guidance from host permission and grant enforcement, with adversarial instructions and no hooks/helper-agent side effects.
  Dependencies: T001–T005. Targets: `bundle security review; adversarial source/evidence fixtures`.
  Verification and planned evidence: `validation-plan.md::procedure_adversarial_guidance`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.


### SPEC-041/T009

<!-- agent-braid-task-id: SPEC-041/T009 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.


### SPEC-041/T010

<!-- agent-braid-task-id: SPEC-041/T010 -->

Parent: SPEC-041. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.


## SPEC-042 parent

Title: SPEC-042: AI tooling packaging and lifecycle

Labels: spec. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

<!-- agent-braid-spec-id: SPEC-042 -->

Source: specs/042-ai-tooling-packaging/spec.md. Scope, acceptance and limits are authoritative there; implementation tasks below are not approval.

### SPEC-042/T001

<!-- agent-braid-task-id: SPEC-042/T001 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T001 (REQ-001/SC-001): Include versioned skills/host metadata in wheel/sdist and resolve them from installed resources with the optional tooling extra.
  Dependencies: none; consumed contract review. Targets: `pyproject.toml assets; installed package resource controls`.
  Verification and planned evidence: `validation-plan.md::procedure_installed_assets`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.


### SPEC-042/T002

<!-- agent-braid-task-id: SPEC-042/T002 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T002 (REQ-002/SC-002): Provide explicit serve/configure/install/doctor/update/uninstall commands with previewed destinations, effects, version and roots.
  Dependencies: T001. Targets: `agent_braid/cli.py tooling command group; lifecycle API`.
  Verification and planned evidence: `validation-plan.md::procedure_lifecycle_api`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.


### SPEC-042/T003

<!-- agent-braid-task-id: SPEC-042/T003 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T003 (REQ-003/SC-003): Support reusable user and opt-in project scope according to each host's actual conventions with per-server trusted roots.
  Dependencies: T001. Targets: `tooling_install.py host scope adapters and explicit root configuration`.
  Verification and planned evidence: `validation-plan.md::procedure_scope_and_roots`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.


### SPEC-042/T004

<!-- agent-braid-task-id: SPEC-042/T004 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T004 (REQ-004/SC-004): Apply configuration atomically with backups/ownership hashes and preserve unrelated keys, comments and skills.
  Dependencies: T001. Targets: `tooling_install.py atomic scoped apply/backup/receipt; preservation controls`.
  Verification and planned evidence: `validation-plan.md::procedure_configuration_preservation`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.


### SPEC-042/T005

<!-- agent-braid-task-id: SPEC-042/T005 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T005 (REQ-005/SC-005): Report doctor results separately for executable, dependency/assets, host/config/roots, protocol and runtime enablement.
  Dependencies: T001. Targets: `tooling_install.py read-only doctor; diagnostic status controls`.
  Verification and planned evidence: `validation-plan.md::procedure_doctor_status`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.


### SPEC-042/T006

<!-- agent-braid-task-id: SPEC-042/T006 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T006 (REQ-006/SC-006): Update only receipt-owned assets, verify compatibility/version and refuse unknown modifications.
  Dependencies: T001–T005. Targets: `tooling_install.py owned update; drift/collision controls`.
  Verification and planned evidence: `validation-plan.md::procedure_safe_update`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.


### SPEC-042/T007

<!-- agent-braid-task-id: SPEC-042/T007 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T007 (REQ-007/SC-007): Uninstall only matching owned entries and report residual shared/modified data.
  Dependencies: T001–T005. Targets: `tooling_install.py owned uninstall; residual/idempotency controls`.
  Verification and planned evidence: `validation-plan.md::procedure_safe_uninstall`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.


### SPEC-042/T008

<!-- agent-braid-task-id: SPEC-042/T008 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T008 (REQ-008/SC-008): Record license/provenance/transitive dependencies and reproduce package/lifecycle controls on supported platforms without cloud claims.
  Dependencies: T001–T005. Targets: `artifact hashes/license inventory; macOS/Linux package reproduction receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_package_provenance`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.


### SPEC-042/T009

<!-- agent-braid-task-id: SPEC-042/T009 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.


### SPEC-042/T010

<!-- agent-braid-task-id: SPEC-042/T010 -->

Parent: SPEC-042. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.


## SPEC-043 parent

Title: SPEC-043: Evidence-oriented AI tooling developer journey

Labels: spec. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

<!-- agent-braid-spec-id: SPEC-043 -->

Source: specs/043-ai-tooling-journey/spec.md. Scope, acceptance and limits are authoritative there; implementation tasks below are not approval.

### SPEC-043/T001

<!-- agent-braid-task-id: SPEC-043/T001 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T001 (REQ-001/SC-001): Provide a reproducible owned synthetic journey from install/discovery through analysis/plan/grant refusal/execute/verify/recovery/export.
  Dependencies: none; consumed contract review. Targets: `docs/tooling/JOURNEY.md; examples/tooling; full fixture workflow`.
  Verification and planned evidence: `validation-plan.md::procedure_full_journey`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.


### SPEC-043/T002

<!-- agent-braid-task-id: SPEC-043/T002 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T002 (REQ-002/SC-002): Explain decisions with input identity, conflicts/dependencies, conditional premises, unknowns, assurance and observation limits.
  Dependencies: T001. Targets: `tooling_present.py chat summary; classification fidelity controls`.
  Verification and planned evidence: `validation-plan.md::procedure_faithful_summary`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.


### SPEC-043/T003

<!-- agent-braid-task-id: SPEC-043/T003 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T003 (REQ-003/SC-003): Explain advisory order and exact missing authority before opt-in execution.
  Dependencies: T001. Targets: `plan/permission journey explanation; missing-grant fixtures`.
  Verification and planned evidence: `validation-plan.md::procedure_authority_journey`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.


### SPEC-043/T004

<!-- agent-braid-task-id: SPEC-043/T004 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T004 (REQ-004/SC-004): Display actual private-result/verifier state and interruption/recovery outcomes with evidence links.
  Dependencies: T001. Targets: `result/recovery explanation; verifier-state controls`.
  Verification and planned evidence: `validation-plan.md::procedure_result_journey`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.


### SPEC-043/T005

<!-- agent-braid-task-id: SPEC-043/T005 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T005 (REQ-005/SC-005): Render an interaction graph with semantic labels, accessible legend and bounded node/edge input.
  Dependencies: T001. Targets: `tooling_present.py graph model/legend; bounded graph controls`.
  Verification and planned evidence: `validation-plan.md::procedure_interaction_graph`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.


### SPEC-043/T006

<!-- agent-braid-task-id: SPEC-043/T006 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T006 (REQ-006/SC-006): Export deterministic Markdown, SVG and standalone HTML from selected evidence with hashes and provenance.
  Dependencies: T001–T005. Targets: `tooling_present.py Markdown/SVG/HTML; deterministic export receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_deterministic_export`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.


### SPEC-043/T007

<!-- agent-braid-task-id: SPEC-043/T007 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T007 (REQ-007/SC-007): Escape and bound untrusted source/evidence in every export without scripts, remote references or secret inclusion.
  Dependencies: T001–T005. Targets: `tooling_present.py escaping/URI/content limits; injection controls`.
  Verification and planned evidence: `validation-plan.md::procedure_export_security`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.


### SPEC-043/T008

<!-- agent-braid-task-id: SPEC-043/T008 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T008 (REQ-008/SC-008): Provide clear onboarding, diagnostics, raw-evidence access and unsupported-rendering explanations in both hosts.
  Dependencies: T001–T005. Targets: `docs/tooling onboarding/diagnostics; unsupported render fallback`.
  Verification and planned evidence: `validation-plan.md::procedure_onboarding_fallback`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.


### SPEC-043/T009

<!-- agent-braid-task-id: SPEC-043/T009 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.


### SPEC-043/T010

<!-- agent-braid-task-id: SPEC-043/T010 -->

Parent: SPEC-043. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.


## SPEC-044 parent

Title: SPEC-044: AI tooling evaluation and closure

Labels: spec. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

<!-- agent-braid-spec-id: SPEC-044 -->

Source: specs/044-ai-tooling-evaluation/spec.md. Scope, acceptance and limits are authoritative there; implementation tasks below are not approval.

### SPEC-044/T001

<!-- agent-braid-task-id: SPEC-044/T001 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T001 (REQ-001/SC-001): Preregister the exact candidate/input/host/model versions, source rights, mandatory included-subscription-only billingPolicy, all 108 attempts, frozen rubric, two abstract independent reviewer roles, approved human-evaluation deferral record and numerical caps for v3 technical capture; keep humanReviewers empty and require a later bound addendum for named identities/ratings.
  Dependencies: none; consumed contract review. Targets: `evaluation-protocol.md; registration.json; owner source/budget decisions`.
  Verification and planned evidence: `validation-plan.md::procedure_registration_gate`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.


### SPEC-044/T002

<!-- agent-braid-task-id: SPEC-044/T002 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T002 (REQ-002/SC-002): Obtain actual discovery, five-skill loading and complete basic journey receipts in both selected macOS arm64 hosts.
  Dependencies: T001. Targets: `actual Codex and Claude receipts; bundle and host inventory`.
  Verification and planned evidence: `validation-plan.md::procedure_actual_host_observation`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.


### SPEC-044/T003

<!-- agent-braid-task-id: SPEC-044/T003 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T003 (REQ-003/SC-003): Run parity, malformed/stale/unsafe/grant/cancellation/recovery and output-agreement controls with exact oracle outcomes.
  Dependencies: T001. Targets: `research/tooling_evaluation.py control runner; oracle parity/refusal fixtures`.
  Verification and planned evidence: `validation-plan.md::procedure_negative_controls`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.


### SPEC-044/T004

<!-- agent-braid-task-id: SPEC-044/T004 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T004 (REQ-004/SC-004): Reproduce installed-package/core/protocol controls on clean macOS arm64 and Linux x86_64 environments.
  Dependencies: T001. Targets: `separate clean macOS/Linux reproduction receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_clean_reproduction`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.


### SPEC-044/T005

<!-- agent-braid-task-id: SPEC-044/T005 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T005 (REQ-005/SC-005): Compare CLI, MCP-only and MCP-plus-skills on 108 registered attempts with counterbalanced order and no outcome-driven revisions.
  Dependencies: T001. Targets: `evaluation harness roster/order/session isolation; 108-slot outcome index`.
  Verification and planned evidence: `validation-plan.md::procedure_three_arm_comparison`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.


### SPEC-044/T006

<!-- agent-braid-task-id: SPEC-044/T006 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T006 (REQ-006/SC-006): Measure complete setup/provider/tool/runtime/export/user/reviewer costs with unavailable fields explicit and numerical stops enforced.
  Dependencies: T001–T005. Targets: `cost/time/token/RSS/disk fields and stop controls; accounting receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_complete_cost`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.


### SPEC-044/T007

<!-- agent-braid-task-id: SPEC-044/T007 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T007 (REQ-007/SC-007): Complete technical interpretation against the frozen rubric while human ratings/adjudication remain deferred; preserve all 108 outcomes and denominators, report labels pending, retain human costs as unavailable rather than zero, and prohibit positive utility conclusions until later human review and applicable cost reconciliation. T007 remains partially pending.
  Dependencies: technical T001–T006 and retained outcomes/cost availability. Targets: `technical interpretation/denominator report; later human scoring and adjudication addendum`.
  Verification and planned evidence: `validation-plan.md::procedure_interpretation`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.


### SPEC-044/T008

<!-- agent-braid-task-id: SPEC-044/T008 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T008 (REQ-008/SC-008): Prepare the technical decision packet from T001–T006 and technical T007, with human outcome evaluation explicitly pending; obtain independent technical review and preserve historical M4 limits.
  Dependencies: technical T001–T006, completed technical T007, applicable technical observations/reproduction and independent technical findings. Founder acceptance and closure remain pending. Targets: `technical candidate/evidence; independent review; decision packet with human phase pending`.
  Verification and planned evidence: `validation-plan.md::procedure_acceptance_decision`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.


### SPEC-044/T009

<!-- agent-braid-task-id: SPEC-044/T009 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: technical evidence T001–T006 and technical T007; deferred human ratings, T008 and T010 follow technical validation. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.


### SPEC-044/T010

<!-- agent-braid-task-id: SPEC-044/T010 -->

Parent: SPEC-044. Labels: task. State: open. Milestone: M4.5 — AI tooling integrations for Codex and Claude Code

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T008 technical packet readiness, T009 validation, applicable technical gates, later human addendum/ratings/adjudication, independent review and actual founder decision. Targets: frozen assurance, review record and final SPEC-044 closure record.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.
