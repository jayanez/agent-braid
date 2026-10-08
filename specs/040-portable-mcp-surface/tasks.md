# Tasks

Stable task IDs are implementation obligations. Check only after the paired procedure produces candidate-bound evidence. Targets below may be future files; no product implementation is claimed.

- [ ] T001 (REQ-001/SC-001): Use mcp==2.3.0 as an isolated optional tooling extra, with core dependencies empty and stdio-only operation.
  Dependencies: none; consumed contract review. Targets: `pyproject.toml optional tooling extra; packaging controls`.
  Verification and planned evidence: `validation-plan.md::procedure_optional_sdk`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.

- [ ] T002 (REQ-002/SC-002): Support 2026-07-28 discovery and 2025-11-25 initialization through the SDK while preserving the legacy endpoint.
  Dependencies: T001. Targets: `agent_braid/tooling_mcp.py SDK lifecycle; protocol controls`.
  Verification and planned evidence: `validation-plan.md::procedure_protocol_compatibility`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.

- [ ] T003 (REQ-003/SC-003): Expose analyze-work for tagged AIM/Git/worktree requests and preserve analyze/prepare/status/execute/recover/verify result semantics.
  Dependencies: T001. Targets: `analysis.py and git_adapter.py delegation; CLI parity controls`.
  Verification and planned evidence: `validation-plan.md::procedure_cli_parity`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.

- [ ] T004 (REQ-004/SC-004): Declare bounded input/output schemas and a typed evidence envelope whose text and structuredContent agree.
  Dependencies: T001. Targets: `tooling_mcp.py schemas/envelope; data-model.md`.
  Verification and planned evidence: `validation-plan.md::procedure_schema_and_summary`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.

- [ ] T005 (REQ-005/SC-005): Bind canonical source/result/grant roots before launch and default to analysis-only advertised capabilities.
  Dependencies: T001. Targets: `tooling_mcp.py configured roots/mode; containment controls`.
  Verification and planned evidence: `validation-plan.md::procedure_root_and_mode`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.

- [ ] T006 (REQ-006/SC-006): Delegate execution/recovery to existing exact grants and policy checks; never expose grant issuance to a model.
  Dependencies: T001–T005. Targets: `mcp_runtime.RuntimeTools delegation; existing runtime_policy grant controls`.
  Verification and planned evidence: `validation-plan.md::procedure_grant_boundary`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.

- [ ] T007 (REQ-007/SC-007): Propagate timeout/cancellation and concurrency to existing point-of-use checks, locking and recoverable state.
  Dependencies: T001–T005. Targets: `tooling_mcp.py cancellation/concurrency bridge; interruption controls`.
  Verification and planned evidence: `validation-plan.md::procedure_cancellation_recovery`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.

- [ ] T008 (REQ-008/SC-008): Provide bounded capabilities/status/evidence manifests and digest/range chunk URIs with complete-result reconstruction controls, plus three read-only prompts without arbitrary file reads or automatic execution.
  Dependencies: T001–T005. Targets: `tooling_mcp.py resources/prompts; owned artifact inventory`.
  Verification and planned evidence: `validation-plan.md::procedure_resources_prompts`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.
