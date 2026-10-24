# SPEC-046: Tasks

Stable source IDs; task completion does not imply native/provider or founder acceptance.

- [x] T001 (REQ-001 / SC-001): Specification and architecture.
  Dependencies: none. Verification: procedure_001 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T002 (REQ-002 / SC-002): Self-contained runtime.
  Dependencies: T001. Verification: procedure_002 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T003 (REQ-003 / SC-003): User registry and MCP routing.
  Dependencies: T001. Verification: procedure_003 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T004 (REQ-004 / SC-004): Repository discovery.
  Dependencies: T003. Verification: procedure_004 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T005 (REQ-005 / SC-005): Onboarding wizard.
  Dependencies: T003, T004. Verification: procedure_005 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T006 (REQ-006 / SC-006): Codex plugin.
  Dependencies: T002, T005. Verification: procedure_006 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T007 (REQ-007 / SC-007): Claude Code plugin.
  Dependencies: T002, T005. Verification: procedure_007 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T008 (REQ-008 / SC-008): Lifecycle and migration.
  Dependencies: T003, T006, T007. Verification: procedure_008 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T009 (REQ-009 / SC-009): Distribution and technical acceptance.
  Dependencies: T002–T008. Verification: procedure_009 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T010 (REQ-010 / SC-010): Documentation and tracking.
  Dependencies: T001–T009. Verification: procedure_010 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T011 (REQ-011 / SC-011): OpenAI candidacy.
  Dependencies: T001, T002. Verification: procedure_011 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T012 (REQ-012 / SC-012): Anthropic candidacy.
  Dependencies: T001, T002. Verification: procedure_012 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [x] T013 (REQ-013 / SC-013): Shell installer.
  Dependencies: T002, T003. Verification: procedure_013 in validation-plan.md. Evidence: evidence/release-alpha2.json.

- [ ] T014 (REQ-011 / SC-011): OpenAI partner eligibility and external approval.
  Dependencies: T011, T009. Verify owner eligibility, obtain publication decision, submit via authorized portal and record provider disposition. Documentary preparation alone does not close this item.

- [ ] T015 (REQ-012 / SC-012): Anthropic executable/size exception and external approval.
  Dependencies: T012, T009. Resolve bundled-runtime restrictions via an authorized review route, obtain publication decision and record directory/official-marketplace dispositions separately. Do not replace bundled runtime with external prerequisites.

- [ ] T016 (REQ-003 / SC-003): Typed stale-registry refusal in the plugin MCP.
  Dependencies: T003. Add `RegistryStale` (a `RegistryError`) with the stable code `reconnect-required`. `PluginRouter.invoke` and `read_resource` must not degrade it to the generic "check workspace, arguments, registry and reconnect state" refusal: the summary names reconnecting the MCP and `plugin-status`, and the refusal keeps the requested `workspaceId` when it is registered. Verification: focused `tests/test_plugin_mcp.py` cases (specific refusal, `isError`, bootstrap tools still answer) via procedure_003 in validation-plan.md. Evidence: focused tests pass (`tests/test_plugin_registry.py`, `tests/test_plugin_mcp.py`, 33 tests with the bundled mcp==2.3.0 SDK, 2026-10-24); installed/native procedure_003 rerun and a recorded evidence file remain pending, so the task stays open.

- [ ] T017 (REQ-003 / SC-003): Effective-configuration comparison for reconnect detection.
  Dependencies: T016. Compare the snapshotted and current registry by effective configuration (telemetry consent and normalized workspace rows), not by raw document equality or order, so an idempotent `plugin setup --apply` does not mark reconnect. `plugin-status` adds path-free `baselineDigest` and `currentDigest`. Immutable roots and grants per connection are unchanged; a change in any registered workspace, grant or consent still requires reconnect. Verification: focused `tests/test_plugin_registry.py` and `tests/test_plugin_mcp.py` cases (no-op rewrite, reordered rows, added/removed/changed workspace, consent change) via procedure_003. Evidence: focused tests pass (`tests/test_plugin_registry.py`, `tests/test_plugin_mcp.py`, 33 tests with the bundled mcp==2.3.0 SDK, 2026-10-24); installed/native procedure_003 rerun and a recorded evidence file remain pending, so the task stays open.

- [ ] T018 (REQ-003 / SC-003): Distinguish reconnect-required refusals in local MCP telemetry.
  Dependencies: T016; SPEC-047/T003. Record the refusal cause (`reconnect-required` versus unknown workspace, full inventory, busy admission, malformed arguments) under surface `mcp` so stale-connection refusals are not counted as usage failures. First inspect the actual SPEC-047 collector; if a versioned category value is needed, specify it in `plan.md` before implementation and keep the data contract otherwise unchanged. Verification: focused plugin telemetry tests with consent `local` and `off` via procedure_003. Evidence: pending.

- [ ] T019 (REQ-010 / SC-010): Document multi-session registry changes and reconnect.
  Dependencies: T016–T018. Update `docs/tooling/NATIVE_PLUGINS.md` and `contracts/interface.md`: a setup apply from any session or the CLI invalidates already running connections; reconnect steps; the new refusal code and digests. State that T016–T019 are a bounded defect fix after the 2026-10-19 owner disposition and do not reopen T014/T015 candidacy, builds, size work or publication. Verification: documentation review and Spec Kit validation via procedure_010. Evidence: pending.

## Owner disposition — 2026-10-19

T014/T015 and the plugin product remain frozen. The owner deferred further
candidacy work and identified repository/package and executable size reduction
as a possible future refactoring process. This note authorizes documentation
only, not investigation, implementation, builds, migration, contact, submission
or publication. Both tasks remain open; the economic NO-GO remains unchanged.

For T015, the [current directory checklist](https://claude.com/docs/plugins/pre-submission-checklist)
requires a repository below 50 MiB archived and 256 MiB unpacked, fewer than
10,000 files and folders, and each plugin file below 5 MiB. These stop validation;
reviewer holds for executables, files above 256 KiB and more than 512 plugin files
do not waive those limits. The historical alpha.2 inventory records 390,788,156
file bytes and 7,737 files; no new build or size measurement was performed for
this disposition. No public size-exception procedure was established by the
2026-10-19 documentation review. The [official-marketplace route](https://code.claude.com/docs/en/plugins/publish#submit-to-anthropics-directory)
requires a separate partner discussion; its acceptance of this candidate remains
unknown. The existing own Git marketplace is a supported distribution route,
not Anthropic directory or official-marketplace approval and not T015 closure.

If the owner later resumes size-reduction work, first measure repository archive,
unpacked package, largest files, platform runtimes, dependencies and duplicated
content separately. Compare Python packaging reductions with a bounded Rust
prototype before choosing a migration. Rust is an unmeasured option, not an
adopted architecture or a guarantee of meeting the per-file or total limits.
Preserve the self-contained offline runtime, macOS arm64 and Linux x86_64,
versioned contracts, workspace/grant boundaries and evidence provenance. Do not
substitute external runtime prerequisites or evade directory limits through
pointers, links or deferred runtime downloads. Any later architectural decision,
implementation and acceptance require their applicable records and validation;
existing candidate-bound evidence does not transfer to a rewritten product.

## Remaining acceptance boundaries

T005/T006/T007 have actual agent-operated native macOS setup/product-skill
journeys, including bounded discovery, exact preview/apply, immutable binding
reconnection and two-workspace MCP analysis. Codex additionally observed explicit
cancellation before apply. The historical Claude login refusal was resolved by
native login before its successful journey. T008 has real native alpha.1 → alpha.2
updates and unchanged registry/result bytes for both hosts on macOS and emulated
Linux. T009 has the public distribution branch/tag, exact fresh clone inventory
and literal remote curl installation for both hosts on both observed platforms.
T010 updates the English installation and source tracking map. The prior
integrated audit returned `operations: []` with 15 linked tasks, independently
read back in the private Project. Final reconciliation is applied only from
merged clean sources; its empty post-audit and Project readback are retained
privately after integration.
See release-acceptance.md for exact observation boundaries.
T011/T012 completion is documentary preparation only; T014/T015 keep external
eligibility, contact/submission and approval independent. No provider submission
messages have been sent. Historical 108 attempts and human/scientific/final M4.5
gates remain unchanged.
