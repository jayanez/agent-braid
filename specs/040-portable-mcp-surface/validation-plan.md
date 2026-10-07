# SPEC-040: Prospective validation procedures

These procedures are plans. Future test modules/harnesses are not present in this source packet. No procedure below has obtained implementation evidence. A passed source validator checks structure only.

Record positive, refusal, unknown, failed, cancelled and unexecuted outcomes. Evidence must include full candidate and input hashes, command/tool trace, environment, output hashes, domain and limits. Human decisions remain separate.

## procedure_optional_sdk (REQ-001/SC-001)

Given core-only and tooling-extra installations; perform each launches supported commands. Assert core analysis works without the SDK; the new endpoint uses the pinned SDK and refuses missing dependency with actionable diagnosis. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-001.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_protocol_compatibility (REQ-002/SC-002)

Given SDK clients selecting each protocol and an existing legacy request; perform discovery and a tool call run. Assert declared schemas/capabilities work for both versions; legacy semantics are preserved and unsupported modes are explicit. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-002.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

## procedure_cli_parity (REQ-003/SC-003)

Given immutable valid and unsupported analysis requests; perform CLI and MCP consume identical inputs. Assert full results agree and unsafe/unknown requests refuse or remain unknown without execution authority. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-003.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

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

Given owned and missing evidence artifacts containing untrusted instructions; perform a resource/prompt is read. Assert only inventory-owned content is served with limits and no prompt or resource issues grants or writes. Include the success and refusal/unavailable counterpart; retain source/result-root integrity and exact typed output.

Prospective targets: `agent_braid/tooling_mcp.py (new); agent_braid/mcp_runtime.py (compatibility); agent_braid/cli.py; pyproject.toml; tests/test_tooling_mcp.py (new)`. Planned receipt: `evidence/sc-008.json`. Use a focused test/harness added with implementation and record its actual command; never execute an invented future command.

