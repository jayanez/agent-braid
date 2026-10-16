# SPEC-046: Native AI plugins

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** implementation authorized; acceptance pending.

## Purpose and scope

Install Agent Braid once per user in each local host, with its runtime and automatically discovered skills. Configure multiple explicitly selected repositories without Python setup. Deliver a Git marketplace and prepare both official candidacies; external approvals do not block engineering delivery. macOS arm64 and Linux x86_64 are targets, not unobserved compatibility claims.

## Authorities

Constitution clause zero and Articles 5–6, 12–16, 19–20, 23–25; GOVERNANCE; ADRs 0019/0020 and proposed 0021/0024; operational semantics.

## Requirements and acceptance scenarios

### REQ-001 — Specification and architecture

Describe native plugins, immutable workspace bindings, runtime provenance and scope boundaries.

**SC-001:** Given The approved scope, existing M4.5 authorities and five-skill contract, when specification, ADR and interface artifacts are analyzed, then requirements, tasks and procedures agree, old contracts remain unchanged and interactive/external gates are explicit.

Verification: [procedure_001](validation-plan.md); T001.

### REQ-002 — Self-contained runtime

Bundle relocatable CPython and hash-locked tooling dependencies for macOS arm64 and Linux x86_64.

**SC-002:** Given A clean source commit and the two pinned runtime archives, when the package is built, relocated to a path with spaces and launched without external Python or package managers, then both target runtimes start offline, hashes and license inventories are present, and corrupt archives or unsupported platforms refuse.

Verification: [procedure_002](validation-plan.md); T002.

### REQ-003 — User registry and MCP routing

Require explicit workspace IDs and preserve fixed roots, evidence isolation and existing grant checks.

**SC-003:** Given Two analysis-only registered workspaces and separate MCP connections, when each explicit ID analyzes a fixture and resources are read, then core report values are preserved; unknown IDs, arbitrary roots, foreign resource IDs, stale bindings and unauthorized execution are refused.

Verification: [procedure_003](validation-plan.md); T003.

### REQ-004 — Repository discovery

Suggest the current/registered repositories and scan only explicitly selected directories with bounded work and no symlink traversal.

**SC-004:** Given Current and registered repositories, an explicit project folder, a Git worktree and symlink aliases, when discovery runs with a depth/entry budget or cancellation, then canonical roots are deduplicated, worktrees recognized, symlinks excluded, work bounded and no registry written; empty/unreadable folders permit manual selection.

Verification: [procedure_004](validation-plan.md); T004.

### REQ-005 — Onboarding wizard

Preview and apply selected workspaces atomically, default to analysis and report required reconnection.

**SC-005:** Given An installed plugin and two repositories selected by the user, when setup previews, the user applies the exact digest and MCP reconnects, then one private registry transaction adds both in analysis mode; stale digests and concurrent changes refuse, cancellation before apply writes no registry, and reconnected status shows the selected IDs.

Verification: [procedure_005](validation-plan.md); T005.

### REQ-006 — Codex plugin

Generate a native Codex package with five canonical skills plus separate setup onboarding.

**SC-006:** Given A clean supported Codex user profile and source-bound marketplace, when the native manager installs the plugin and the local host loads its components, then five canonical product skills and setup onboarding are available with bundled stdio MCP; actual interactive skill use is recorded separately from CLI metadata inspection.

Verification: [procedure_006](validation-plan.md); T006.

### REQ-007 — Claude Code plugin

Generate equivalent Claude Code metadata and user-scoped marketplace distribution.

**SC-007:** Given A clean supported Claude Code user profile and the same marketplace sources, when strict validation, user install and local component loading run, then the six skills and bundled stdio MCP are available, without global skill copying or Python setup; actual interactive skill use is recorded separately.

Verification: [procedure_007](validation-plan.md); T007.

### REQ-008 — Lifecycle and migration

Use native plugin lifecycle and receipt-owned legacy removal while retaining modified/shared files and private results.

**SC-008:** Given Installed user plugins, existing private results and a legacy receipt with one edited skill, when native update/removal and explicit receipt migration are exercised, then configuration/results and unrelated or modified bytes survive; only matching receipt-owned entries are removed; a real version change is observed before update acceptance.

Verification: [procedure_008](validation-plan.md); T008.

### REQ-009 — Distribution and technical acceptance

Build versioned marketplace artifacts, provenance and licenses; record clean package and native host observations separately.

**SC-009:** Given A clean source commit, runtime/dependency locks and owner release decision, when a versioned distribution is built and reproduced in fresh host profiles, then provenance binds source, wheel, locks, runtime archives and corresponding sources; inventory verifies; both catalogs install; binaries live only in the distribution branch and publication is separately authorized.

Verification: [procedure_009](validation-plan.md); T009.

### REQ-010 — Documentation and tracking

Update English installation/README, additive M4.5 references and governed GitHub records.

**SC-010:** Given Existing historical M4.5 records and the new source artifacts, when English documentation and governed GitHub reconciliation are updated, then native installation/setup/lifecycle come first; only allowlisted new IDs and intended milestone metadata change; post-audit operations are empty and private Project membership/status is read back independently.

Verification: [procedure_010](validation-plan.md); T010.

### REQ-011 — OpenAI candidacy

Prepare listing, support/privacy/review material and identify partner eligibility for local MCP without claiming approval.

**SC-011:** Given OpenAI local-MCP publication requirements and the source-bound candidate, when listing, privacy/support, test cases and eligibility checklist are reviewed, then documentary material is complete and partner/account/publication dependencies are explicitly assigned to T014; preparation never claims provider approval.

Verification: [procedure_011](validation-plan.md); T011.

### REQ-012 — Anthropic candidacy

Prepare directory/official-marketplace material, identify binary/size restrictions and record external review separately.

**SC-012:** Given Anthropic directory and official-marketplace rules and the bundled candidate inventory, when listing/reviewer material and executable/size constraints are checked, then largest files and limits are recorded, directory and official-marketplace routes are distinct, and unresolved exceptions/account/publication approvals stay in T015.

Verification: [procedure_012](validation-plan.md); T012.

### REQ-013 — Shell installer

Offer a POSIX curl entrypoint that uses native user-scoped plugin managers, requires no Python or sudo, and never starts a provider session.

**SC-013:** Given Existing Git and one or both native host executables, when the shell installer is invoked explicitly, dry-run, with a pinned ref or with a missing selected host, then only native user plugin-manager operations run; all selected hosts preflight first; option order preserves the explicit ref; dry-run performs no install; no Python bootstrap, sudo or provider session occurs.

Verification: [procedure_013](validation-plan.md); T013.

## Scientific boundaries and compatibility

Engineering only. No new effect domain, grant issuance, provider launch, scientific claim, registered 108-slot amendment, historical acceptance or milestone closure. Official approval and public release remain separate founder/provider decisions.

## Evidence and unresolved questions

Planned procedures are not obtained evidence. See validation-plan.md and assurance.json. Native host observations, Linux controls, directory eligibility, technical review and founder acceptance must identify their actual environment and outcome.
