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

**SC-001:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_001](validation-plan.md); T001.

### REQ-002 — Self-contained runtime

Bundle relocatable CPython and hash-locked tooling dependencies for macOS arm64 and Linux x86_64.

**SC-002:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_002](validation-plan.md); T002.

### REQ-003 — User registry and MCP routing

Require explicit workspace IDs and preserve fixed roots, evidence isolation and existing grant checks.

**SC-003:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_003](validation-plan.md); T003.

### REQ-004 — Repository discovery

Suggest the current/registered repositories and scan only explicitly selected directories with bounded work and no symlink traversal.

**SC-004:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_004](validation-plan.md); T004.

### REQ-005 — Onboarding wizard

Preview and apply selected workspaces atomically, default to analysis and report required reconnection.

**SC-005:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_005](validation-plan.md); T005.

### REQ-006 — Codex plugin

Generate a native Codex package with five canonical skills plus separate setup onboarding.

**SC-006:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_006](validation-plan.md); T006.

### REQ-007 — Claude Code plugin

Generate equivalent Claude Code metadata and user-scoped marketplace distribution.

**SC-007:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_007](validation-plan.md); T007.

### REQ-008 — Lifecycle and migration

Use native plugin lifecycle and receipt-owned legacy removal while retaining modified/shared files and private results.

**SC-008:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_008](validation-plan.md); T008.

### REQ-009 — Distribution and technical acceptance

Build versioned marketplace artifacts, provenance and licenses; record clean package and native host observations separately.

**SC-009:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_009](validation-plan.md); T009.

### REQ-010 — Documentation and tracking

Update English installation/README, additive M4.5 references and governed GitHub records.

**SC-010:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_010](validation-plan.md); T010.

### REQ-011 — OpenAI candidacy

Prepare listing, support/privacy/review material and identify partner eligibility for local MCP without claiming approval.

**SC-011:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_011](validation-plan.md); T011.

### REQ-012 — Anthropic candidacy

Prepare directory/official-marketplace material, identify binary/size restrictions and record external review separately.

**SC-012:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_012](validation-plan.md); T012.

### REQ-013 — Shell installer

Offer a POSIX curl entrypoint that uses native user-scoped plugin managers, requires no Python or sudo, and never starts a provider session.

**SC-013:** Given an isolated owned installation and paired failure controls, when the selected procedure runs, then its stated capability works or reports a bounded refusal/pending observation, preserves unrelated state and records actual outcomes.

Verification: [procedure_013](validation-plan.md); T013.

## Scientific boundaries and compatibility

Engineering only. No new effect domain, grant issuance, provider launch, scientific claim, registered 108-slot amendment, historical acceptance or milestone closure. Official approval and public release remain separate founder/provider decisions.

## Evidence and unresolved questions

Planned procedures are not obtained evidence. See validation-plan.md and assurance.json. Native host observations, Linux controls, directory eligibility, technical review and founder acceptance must identify their actual environment and outcome.
