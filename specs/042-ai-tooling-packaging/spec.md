# SPEC-042: AI tooling packaging and lifecycle

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft specification; implementation, observations and human acceptance are pending.

## Purpose and scope

Create reproducible installed assets and explicit global/project lifecycle commands for the two supported local hosts.

## Authorities

Constitution clause zero and Articles 3–7, 12–16, 19–25; GOVERNANCE.md; operational semantics, claim discipline, ADRs 0019/0020 and proposed ADR 0021. This spec is subordinate to accepted authorities. See assurance.json for references and authority inventory.

## Requirements and acceptance scenarios

### REQ-001

Include versioned skills/host metadata in wheel/sdist and resolve them from installed resources with the optional tooling extra.

**SC-001:** Given relocated isolated installation and core-only environment, when assets and entry points are resolved, then no checkout-relative paths are required and core-only analysis remains usable.

Verification: [procedure_installed_assets](validation-plan.md); [T001](tasks.md). Obtained evidence: none.

### REQ-002

Provide explicit serve/configure/install/doctor/update/uninstall commands with previewed destinations, effects, version and roots.

**SC-002:** Given a user-selected lifecycle operation, when preview and selected apply run, then only named effects occur, stdout protocol is clean and unselected configuration/provider work is absent.

Verification: [procedure_lifecycle_api](validation-plan.md); [T002](tasks.md). Obtained evidence: none.

### REQ-003

Support reusable user and opt-in project scope according to each host's actual conventions with per-server trusted roots.

**SC-003:** Given two repositories, host scopes and nondefault CODEX_HOME, when configuration is generated or selected, then both scopes are explicit and reusable assets cannot silently widen server access.

Verification: [procedure_scope_and_roots](validation-plan.md); [T003](tasks.md). Obtained evidence: none.

### REQ-004

Apply configuration atomically with backups/ownership hashes and preserve unrelated keys, comments and skills.

**SC-004:** Given existing unrelated configuration, collision or concurrent edit, when installation applies, then owned entries change idempotently or refuse on drift; unrelated bytes remain intact where promised.

Verification: [procedure_configuration_preservation](validation-plan.md); [T004](tasks.md). Obtained evidence: none.

### REQ-005

Report doctor results separately for executable, dependency/assets, host/config/roots, protocol and runtime enablement.

**SC-005:** Given missing SDK/host/auth, invalid root and healthy protocol peer, when doctor runs, then unavailable and pending checks remain distinct; no execute, grant or paid host session is launched.

Verification: [procedure_doctor_status](validation-plan.md); [T005](tasks.md). Obtained evidence: none.

### REQ-006

Update only receipt-owned assets, verify compatibility/version and refuse unknown modifications.

**SC-006:** Given older owned bundle and locally edited files, when update is requested, then unchanged owned entries update with receipt; edits/collisions refuse with a concrete diff.

Verification: [procedure_safe_update](validation-plan.md); [T006](tasks.md). Obtained evidence: none.

### REQ-007

Uninstall only matching owned entries and report residual shared/modified data.

**SC-007:** Given owned, shared and changed configuration/skills, when uninstall runs twice, then owned entries remove idempotently while unrelated/modified data is preserved and reported.

Verification: [procedure_safe_uninstall](validation-plan.md); [T007](tasks.md). Obtained evidence: none.

### REQ-008

Record license/provenance/transitive dependencies and reproduce package/lifecycle controls on supported platforms without cloud claims.

**SC-008:** Given built artifacts and macOS/Linux control environments, when inventory and clean reproduction run, then hashes, licenses and actual environment results are recorded; remote/cloud installation remains separately required.

Verification: [procedure_package_provenance](validation-plan.md); [T008](tasks.md). Obtained evidence: none.

## Scientific boundaries and compatibility

Domain: User-owned isolated package environment and receipt-owned configuration/skill files; startup binds exact repositories and result roots.

Hypothesis: Predictable installation and diagnosis may lower adoption effort; reusable installation does not imply universal repository access.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

SDK/documentation, structural checks, synthetic controls, actual host observations and independent reproduction have separate evidence domains. Passing one does not establish the others or human approval. Public APIs are additive experimental proposals with migration/versioning review during implementation.

## Evidence and unresolved questions

Planned procedures are in validation-plan.md; obtained evidence is empty in assurance.json. The packet records a proposed design, not a runtime acceptance result. Required decisions: technical contract/ADR adoption, exact host versions and installation scope, provider budget/source rights for capture, independent review and founder acceptance. See program.md in SPEC-039 and evaluation-protocol.md in SPEC-044.
