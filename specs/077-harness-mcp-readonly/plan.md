# Implementation plan: SPEC-077 read-only harness MCP surface

## Technical context and scope

- **Surface host.** The native plugin MCP facade (`agent_braid/plugin_mcp.py`,
  envelope `agent-braid-plugin/v0.2`), the server Claude Code, Codex and OpenCode load
  from the installed plugin. The portable `agent-braid-tooling` server is not touched
  (OD-1).
- **Views.** `agent_braid/harness_cli.py` functions `_capabilities`,
  `_registry_status`, `_evaluation_summary` and `_evidence` (SPEC-049 T009). The MCP
  tools call the same functions through one shared adapter; they do not reimplement
  parsing or verification.
- **Frozen files.** No change to `harness_containment_macos.py`, `harness_lab.py`,
  `harness_host_claude.py`, `harness_transport_claude.py`, `harness_quota.py` or
  `scripts/har_t00*_launch.sh`. None is imported by the planned adapter.
- **This PR.** Contract, plan, research, tasks, validation plan, assurance record,
  ADR 0043 (Proposed) and the Codex review packet. No code.

## Constitution check before research

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | Engineering, no scientific claim beyond evidence | H1 is a hypothesis; REQ-009 may refute it; negative outcome closes the spec |
| 5, 15 | Effects are first-class; tools carry effect semantics | Every tool declares `effect: none`; no write, lock, clock, network, subprocess (REQ-003) |
| 13, 14 | Evidence, not verdicts | Results are the CLI views with their `limits`; no blended score, no verdict added |
| 19 | Real, measurable problem | REQ-009 measures host validity on a held-out set before publication |
| 20 | Analysis and execution are separate | No execution, launch, grant or promotion tool; `executionAuthorization: false` |
| 23, 24 | Semantics before production | Contract and review precede code; publication gated on T014 and D7 |

No MUST conflict found. No SHOULD deviation recorded.

## Research, assumptions and alternatives

See [research.md](research.md): surface host and version (R1), argument design from
#1343 (R2), path resolution (R3), output bound (R4), telemetry (R5), validity test
(R6), native execution exclusion (R7). Not an empirical comparison; no data source
is fitted. The held-out validity run (REQ-009) is a measurement with a frozen set.

## Design and compatibility

- One adapter module (planned `agent_braid/harness_mcp.py`) maps each tool's
  arguments to the CLI view, resolves paths under the registered source root by
  descriptor walk (`O_NOFOLLOW` on every segment), serializes the result, enforces the
  65,536-byte cap and builds refusals per the contract.
- `plugin_mcp.tool_listing` gains the four plugin-owned definitions next to
  `plugin-status` and `workspaces`; `workspaceId` is required except for
  `harness-capabilities`.
- `harness capabilities` reports `pluginOrMcpSurface: "none"` until publication; the
  published build reports `"agent-braid-harness-mcp/v0.1"`. The module docstring and
  `HARNESSING.md` change only at publication (T009).
- Compatibility: additive tools under `agent-braid-plugin/v0.2` (OD-1). Installed
  verifiers that count plugin tools are updated in the same change. Rollback is a
  plugin reinstall; no stored state.

## Validation strategy

| REQ | SC | Test / procedure | Planned evidence |
|---|---|---|---|
| REQ-001 | SC-001 | validation-plan procedure_001 | `evidence/t001-owner-review.md` |
| REQ-002 | SC-002 | `tests/test_harness_mcp.py::test_tool_set_is_exact` | `evidence/t004.json` |
| REQ-003 | SC-003 | `tests/test_harness_mcp.py::test_no_effects_no_authority` | `evidence/t004.json` |
| REQ-004 | SC-004 | `tests/test_harness_mcp.py::test_flat_schema_in_description` | `evidence/t004.json` |
| REQ-005 | SC-005 | `tests/test_harness_mcp.py::test_workspace_path_containment` | `evidence/t004.json` |
| REQ-006 | SC-006 | `tests/test_harness_mcp.py::test_cli_parity` | `evidence/t004.json` |
| REQ-007 | SC-007 | `tests/test_harness_mcp.py::test_output_bound` | `evidence/t004.json` |
| REQ-008 | SC-008 | `tests/test_harness_mcp.py::test_refusal_pointer_and_redaction` | `evidence/t004.json` |
| REQ-009 | SC-009 | validation-plan procedure_007 (three hosts) | `evidence/heldout-*.json` |
| REQ-010 | SC-010 | validation-plan procedure_008 | `evidence/t008-publication.json` |
| REQ-011 | SC-011 | validation-plan procedure_010 | `evidence/t003.json` |
| REQ-012 | SC-012 | `tests/test_harness_mcp.py::test_result_has_no_submitted_values_or_host_paths` | `evidence/t004.json` |
| REQ-013 | SC-013 | `tests/test_harness_mcp.py::test_host_approval_grants_nothing` | `evidence/t004.json` |

Negative controls: each guard (link refusal, `..`, cap, pointer redaction, tool-set
exactness) has a test that fails when the guard is removed (mutation check recorded in
`evidence/t004.json`). Assurance snapshots: `current` while drafting; frozen before
owner review.

## Constitution check after design

Unchanged: no article conflict. The one new trust boundary (host-supplied path) is
closed by REQ-005. The surface adds no authority.

## Human review and unresolved decisions

OD-1 to OD-6 in [spec.md](spec.md#evidence-and-unresolved-questions). The Codex
contract review ([packet](review/codex-contract-20261116.md)) is independent model
review, not human review or approval.
