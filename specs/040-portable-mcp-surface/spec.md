# SPEC-040: Portable MCP tooling surface

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft specification; experimental implementation and partial local observations exist, while full procedures and human acceptance remain pending.

## Purpose and scope

Add an optional official-SDK stdio interface over existing analysis and runtime contracts with typed results, discovery and bounded evidence access.

## Authorities

Constitution clause zero and Articles 3–7, 12–16, 19–25; GOVERNANCE.md; operational semantics, claim discipline, ADRs 0019/0020 and proposed ADR 0021. This spec is subordinate to accepted authorities. See assurance.json for references and authority inventory.

## Requirements and acceptance scenarios

### REQ-001

Use mcp==2.3.0 as an isolated optional tooling extra, with core dependencies empty and stdio-only operation.

**SC-001:** Given core-only and tooling-extra installations, when each launches supported commands, then core analysis works without the SDK; the new endpoint uses the pinned SDK and refuses missing dependency with actionable diagnosis.

Verification: [procedure_optional_sdk](validation-plan.md); [T001](tasks.md). Obtained evidence: partial installed-e40 controls are recorded in [the partial evidence record](evidence/partial-installed-e40c949.json); full procedure remains unmet.

### REQ-002

Support 2026-07-28 discovery and 2025-11-25 initialization through the SDK while preserving the legacy endpoint.

**SC-002:** Given SDK clients selecting each protocol and an existing legacy request, when discovery and a tool call run, then declared schemas/capabilities work for both versions; legacy semantics are preserved and unsupported modes are explicit.

Verification: [procedure_protocol_compatibility](validation-plan.md); [T002](tasks.md). Obtained evidence: the record includes two read-only analyze-work calls on the new endpoint, selecting 2026-07-28 and 2025-11-25, plus a separate old-endpoint 2025-11-25 probe with an out-of-root refusal and a valid synthetic Git analyze call. The full unsupported-mode/refusal matrix and all scenarios remain unobserved, so SC-002 remains unmet.

### REQ-003

Expose analyze-work for tagged AIM/Git/worktree requests and preserve analyze/prepare/status/execute/recover/verify result semantics.

**SC-003:** Given immutable valid and unsupported analysis requests, including a result above 256 KiB, when CLI and MCP consume identical inputs, then full inline or manifest/chunk-reconstructed core values agree with CLI; missing/corrupt fragments cannot pass parity, and unsafe/unknown requests refuse or remain unknown without execution authority.

Verification: [procedure_cli_parity](validation-plan.md); [T003](tasks.md). Obtained evidence: one classic AIM example produced semantic CLI/MCP report equality in both selected new-endpoint protocol modes, with execution authorization false. No large-result chunk reconstruction, Git/worktree parity, corrupt-chain refusal, or unsupported-request matrix is recorded; SC-003 remains unmet.

### REQ-004

Declare bounded input/output schemas and a typed evidence envelope whose text and structuredContent agree.

**SC-004:** Given valid, malformed, deeply nested and overlarge input/output, when request/result validation runs, then accepted outputs preserve complete result/provenance/limits and summaries agree; invalid/over-budget values refuse.

Verification: [procedure_schema_and_summary](validation-plan.md); [T004](tasks.md). Obtained evidence: none.

### REQ-005

Bind canonical source/result/grant roots before launch and default to analysis-only advertised capabilities.

**SC-005:** Given root escapes, symlinks, unknown runs and analysis mode, when tools or resources are invoked, then out-of-root access refuses and runtime mutations are unavailable until explicit operator configuration.

Verification: [procedure_root_and_mode](validation-plan.md); [T005](tasks.md). Obtained evidence: none.

### REQ-006

Delegate execution/recovery to existing exact grants and policy checks; never expose grant issuance to a model.

**SC-006:** Given valid, absent, stale, expired, reused, revoked or wrong-scope grants, when execute/recover is requested, then only the exact existing authority admits bounded private effects; advice and host permission cannot create or expand grants.

Verification: [procedure_grant_boundary](validation-plan.md); [T006](tasks.md). Obtained evidence: none.

### REQ-007

Propagate timeout/cancellation and concurrency to existing point-of-use checks, locking and recoverable state.

**SC-007:** Given cancelled execution, stale base and overlapping calls, when a transition starts or recovery runs, then no unfinished success or duplicate effect is returned; existing private state can be inspected/reconciled and wrong authority refuses.

Verification: [procedure_cancellation_recovery](validation-plan.md); [T007](tasks.md). Obtained evidence: none.

### REQ-008

Provide bounded capabilities/status/evidence resources and three read-only prompts without arbitrary file reads or automatic execution.

**SC-008:** Given owned multi-chunk, empty, missing or stale evidence artifacts, invalid digest/range selectors and untrusted instructions, when resources and prompts are read through the manifest and first/next chunk URIs, then only inventory-owned content is served within bounds; exact bytes and full hash reconstruct before use, invalid/incomplete chains refuse, and no prompt or resource issues grants or writes.

Verification: [procedure_resources_prompts](validation-plan.md); [T008](tasks.md). Obtained evidence: partial capability/prompt listing and oversized-argument refusal with successful follow-up, plus default installed-wheel loading of five skill resources and five supporting assets with source/wheel/installed byte equality, are recorded in [the partial evidence record](evidence/partial-installed-e40c949.json). Artifact manifest/chunk and refusal-chain assertions, native host loading, sdist/Linux, and legal compatibility remain unproven; the full procedure remains unmet.

## Scientific boundaries and compatibility

Domain: Local stdio requests from configured Codex/Claude consumers; existing finite AIM/Git/worktree analyzer and 2–4 ordinary-text A/M private Git runtime domains.

Hypothesis: A standard typed interface may improve discovery and interoperability; SDK conformance alone does not prove real-host support or semantic correctness.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

SDK/documentation, structural checks, synthetic controls, actual host observations and independent reproduction have separate evidence domains. Passing one does not establish the others or human approval. Public APIs are additive experimental proposals with migration/versioning review during implementation.

## Evidence and unresolved questions

Planned procedures are in validation-plan.md; the assurance record contains candidate-bound partial local observations for SC-001, SC-002, SC-003 and SC-008, including installed default-resource bytes but not native loading, but no complete scenario has been established by these records. This packet remains draft and does not establish runtime acceptance, native-host acceptance or human approval. Required decisions: technical contract/ADR adoption, exact host versions and installation scope, provider budget/source rights for capture, independent review and founder acceptance. See program.md in SPEC-039 and evaluation-protocol.md in SPEC-044.
