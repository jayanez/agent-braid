# SPEC-040: Validation procedures and obtained scope

These are the paired acceptance procedures. Experimental implementation modules and deterministic controls are present in the current candidate. Canonical records may retain reviewed partial local observations; a partial record does not satisfy a procedure unless all stated assertions and paired positive/refusal outcomes are evidenced. Canonical assurance remains draft with human review pending. A passed source validator checks structure only and does not complete these procedures.

Record positive, refusal, unknown, failed, cancelled and unexecuted outcomes. Evidence must include full candidate and input hashes, command/tool trace, environment, output hashes, domain and limits. Human decisions remain separate.

## procedure_optional_sdk (REQ-001/SC-001)

Given core-only and tooling-extra installations; perform each launches supported commands. Assert core analysis works without the SDK; the new endpoint uses the pinned SDK and refuses missing dependency with actionable diagnosis. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-001.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.


Historical partial observation, before the 2026-10-10 full bounded procedures: `evidence/partial-installed-e40c949.json` records installed-wheel core analysis success and the actionable missing-SDK serve refusal on exact e40. These observations cover only those paired clauses; the complete procedure remains unmet. The capability-only probe lists tools/resources/prompts and makes zero calls; separate protocol-mode evidence makes two read-only calls. A separate default installed-wheel resource observation confirms byte equality for five bundled skills and five supporting assets, but no native host load. The classic analysis example is not a cohort fixture.

## procedure_protocol_compatibility (REQ-002/SC-002)

Given SDK clients selecting each protocol and an existing legacy request; perform discovery and a tool call run. Assert declared schemas/capabilities work for both versions; legacy semantics are preserved and unsupported modes are explicit. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-002.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.


Historical partial observation, before the 2026-10-10 full bounded procedures: `evidence/partial-installed-e40c949.json` records two read-only calls on the new endpoint (`auto` selecting 2026-07-28 and `legacy` selecting 2025-11-25), plus a separately reviewed old-endpoint 2025-11-25 probe with six tools listed, out-of-root refusal, and valid synthetic Git analyze. Both probes matched their stated bounded results. The complete paired unsupported-mode/refusal matrix and all required scenarios remain unobserved; SC-002 remains unmet.

## procedure_cli_parity (REQ-003/SC-003)

Given immutable valid and unsupported analysis requests, including a result above 256 KiB; compare CLI and MCP on identical inputs. Reconstruct the complete result through digest-bound first/next chunk URIs before comparing core values. Assert parity for every byte/field and preserve refusal/unknown semantics without execution authority. Missing, corrupt or incomplete fragment chains cannot pass parity. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-003.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

Historical partial observation, before the 2026-10-10 full bounded procedures: the bound partial record includes semantic CLI/MCP report equality for one classic AIM input across two selected SDK modes, with execution authorization false. No >256 KiB result, digest-bound chunk reconstruction, Git/worktree parity, missing/corrupt chain control, or unsupported-request refusal matrix was exercised; SC-003 remains unmet.

## procedure_schema_and_summary (REQ-004/SC-004)

Given valid, malformed, deeply nested and overlarge input/output; perform request/result validation runs. Assert accepted outputs preserve complete result/provenance/limits and summaries agree; invalid/over-budget values refuse. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-004.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_root_and_mode (REQ-005/SC-005)

Given root escapes, symlinks, unknown runs and analysis mode; perform tools or resources are invoked. Assert out-of-root access refuses and runtime mutations are unavailable until explicit operator configuration. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-005.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_grant_boundary (REQ-006/SC-006)

Given valid, absent, stale, expired, reused, revoked or wrong-scope grants; perform execute/recover is requested. Assert only the exact existing authority admits bounded private effects; advice and host permission cannot create or expand grants. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-006.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_cancellation_recovery (REQ-007/SC-007)

Given cancelled execution, stale base and overlapping calls; perform a transition starts or recovery runs. Assert no unfinished success or duplicate effect is returned; existing private state can be inspected/reconciled and wrong authority refuses. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-007.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_resources_prompts (REQ-008/SC-008)

Given owned multi-chunk, empty, missing or stale artifacts and untrusted instructions; read the manifest and every first/next chunk URI. Assert deterministic repeat reads, bounded base64 bytes, exact offsets/lengths, correct EOF and complete digest reconstruction, including Unicode split across fragments and a partial last chunk. Refuse wrong digests, malformed/overflowing or out-of-range selectors, escapes and missing/corrupt chains; detect duplicate/overlapping/gapped replies before use. Only inventory-owned content is served and no resource or prompt issues grants, writes or reruns the operation. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-008.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.


Historical partial observation, before the 2026-10-10 full bounded procedures: `evidence/partial-installed-e40c949.json` records capability-resource and prompt inventory plus an oversized prompt-argument refusal and a succeeding follow-up list request. A separate installed-wheel observation loads five skills and five supporting assets from the default package resources and verifies source/wheel/installed byte equality. Neither observation tests artifact manifests/chunks, empty or stale resources, reconstruction, the required refusal matrix, or native host loading; SC-008 remains unmet.


2026-10-10 autonomous procedure update: obtained receipts `evidence/sc-*.json` retain actual paired controls, commands, source/input identities and limits. Earlier partial observations above are historical and have not been rebound. See `docs/tooling/AUTONOMOUS_COMPLETION.md` for remaining interventions.
