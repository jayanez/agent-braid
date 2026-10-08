# Tasks

Stable task IDs are implementation obligations. Check only after the paired procedure produces candidate-bound evidence. Targets below may be future files; no product implementation is claimed.

- [ ] T001 (REQ-001/SC-001): Include versioned skills/host metadata in wheel/sdist and resolve them from installed resources with the optional tooling extra.
  Dependencies: none; consumed contract review. Targets: `pyproject.toml assets; installed package resource controls`.
  Verification and planned evidence: `validation-plan.md::procedure_installed_assets`; `evidence/sc-001.json` with actual commands and negative controls. Obtained: none.

- [ ] T002 (REQ-002/SC-002): Provide explicit serve/configure/install/doctor/update/uninstall commands with previewed destinations, effects, version and roots.
  Dependencies: T001. Targets: `agent_braid/cli.py tooling command group; lifecycle API`.
  Verification and planned evidence: `validation-plan.md::procedure_lifecycle_api`; `evidence/sc-002.json` with actual commands and negative controls. Obtained: none.

- [ ] T003 (REQ-003/SC-003): Support reusable user and opt-in project scope according to each host's actual conventions with per-server trusted roots.
  Dependencies: T001. Targets: `tooling_install.py host scope adapters and explicit root configuration`.
  Verification and planned evidence: `validation-plan.md::procedure_scope_and_roots`; `evidence/sc-003.json` with actual commands and negative controls. Obtained: none.

- [ ] T004 (REQ-004/SC-004): Apply configuration atomically with backups/ownership hashes and preserve unrelated keys, comments and skills.
  Dependencies: T001. Targets: `tooling_install.py atomic scoped apply/backup/receipt; preservation controls`.
  Verification and planned evidence: `validation-plan.md::procedure_configuration_preservation`; `evidence/sc-004.json` with actual commands and negative controls. Obtained: none.

- [ ] T005 (REQ-005/SC-005): Report doctor results separately for executable, dependency/assets, host/config/roots, protocol and runtime enablement.
  Dependencies: T001. Targets: `tooling_install.py read-only doctor; diagnostic status controls`.
  Verification and planned evidence: `validation-plan.md::procedure_doctor_status`; `evidence/sc-005.json` with actual commands and negative controls. Obtained: none.

- [ ] T006 (REQ-006/SC-006): Update only receipt-owned assets, verify compatibility/version and refuse unknown modifications.
  Dependencies: T001–T005. Targets: `tooling_install.py owned update; drift/collision controls`.
  Verification and planned evidence: `validation-plan.md::procedure_safe_update`; `evidence/sc-006.json` with actual commands and negative controls. Obtained: none.

- [ ] T007 (REQ-007/SC-007): Uninstall only matching owned entries and report residual shared/modified data.
  Dependencies: T001–T005. Targets: `tooling_install.py owned uninstall; residual/idempotency controls`.
  Verification and planned evidence: `validation-plan.md::procedure_safe_uninstall`; `evidence/sc-007.json` with actual commands and negative controls. Obtained: none.

- [ ] T008 (REQ-008/SC-008): Record license/provenance/transitive dependencies and reproduce package/lifecycle controls on supported platforms without cloud claims.
  Dependencies: T001–T005. Targets: `artifact hashes/license inventory; macOS/Linux package reproduction receipts`.
  Verification and planned evidence: `validation-plan.md::procedure_package_provenance`; `evidence/sc-008.json` with actual commands and negative controls. Obtained: none.

- [ ] T009 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Reconcile implementation evidence and run repository quick/PR gates.
  Dependencies: T001–T008. Targets: this spec's assurance.json, validation receipts and bounded candidate.
  Verification and planned evidence: run the explicit quick and stable PR profiles; bind actual results without implying actual-host observation, clean-room reproduction or approval.

- [ ] T010 (REQ-001,REQ-002,REQ-003,REQ-004,REQ-005,REQ-006,REQ-007,REQ-008/SC-001,SC-002,SC-003,SC-004,SC-005,SC-006,SC-007,SC-008): Freeze the bounded candidate, review findings and record the required human decision.
  Dependencies: T009 and feature-specific observation gates. Targets: frozen assurance, review record and SPEC-044 decision packet.
  Verification and planned evidence: candidate/evidence hashes, independent technical findings and actual decision; source validation and hashes are not approval.
