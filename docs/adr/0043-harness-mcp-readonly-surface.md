# ADR 0043: Read-only harness views over the plugin MCP facade

- **Status:** Proposed (draft, 2026-11-16). Not accepted; implements and publishes
  nothing. Accepted or rejected with the SPEC-077 T008 publication decision, which
  follows SPEC-049 T014 and the D7 ADR.
- **Date:** 2026-11-16
- **Deciders:** Juan Antonio Yáñez García (founder)
- **Constitutional articles:** 0, 5, 13, 14, 15, 19, 20, 23, 24
- **Specification:** [SPEC-077](../../specs/077-harness-mcp-readonly/spec.md)
  (milestone M4.8)

## Context

SPEC-049 T009 merged four read-only advisory views in the experimental
`agent-braid harness` CLI: `capabilities`, `registry-status`, `evaluation-summary`
and `evidence`. SPEC-049 SC-008 and T009 require any plugin/MCP extension to have a
versioned contract and its own review. SPEC-050 owner decision D3 kept access on the
CLI and placed MCP exposure under milestone M4.8. Decision D7 defers any activation
policy and ADR to SPEC-049 T014 results.

On 2026-11-16 the owner decided to draft the read-only MCP contract now and publish
it only after T014, and excluded native execution over MCP: the MCP server runs as
the operator user and cannot `sudo` the root-owned SPEC-065 launcher, a launch would
change the qualified environment hash and spend subscription quota, and host tool
approval is not an operator grant (ADR 0035).

Issue #1343 shows host models failing to author complex `analyze-work` requests
(HELD-04 fails every trial on every host). No CLI-vs-MCP baseline exists (SPEC-044
T005 never ran).

## Decision (proposed)

1. Expose exactly four plugin-owned MCP tools, `harness-capabilities`,
   `harness-registry-status`, `harness-evaluation-summary` and `harness-evidence`,
   under the result contract `agent-braid-harness-mcp/v0.1`
   ([contract](../../specs/077-harness-mcp-readonly/contracts/harness-mcp-readonly.md)).
2. Every result carries `executionAuthorization: false`; the tools have no effects
   and reach no launch, grant, promotion, activation or registry write.
3. Arguments are flat and trivial (`workspaceId`, one workspace-relative path, an
   optional hash); each tool description embeds its schema and one example.
4. Output is capped at 65,536 bytes and refused, not truncated, above it; refusals
   carry a JSON Pointer and never echo values (ADR 0038 refusal rules).
5. Host the tools on the native plugin facade, additively under
   `agent-braid-plugin/v0.2`. Leave the portable `agent-braid-tooling/v0.2` surface
   unchanged, so this decision needs no `agent-braid-tooling/v0.3` and does not
   couple with the alias removal of issue #771.
6. Publish only if SPEC-049 T014 has results, the D7 ADR does not close the harness
   as experimental, a held-out validity test passes in Claude Code, Codex and
   OpenCode, the Codex contract review is resolved and the owner accepts the
   candidate.

## Alternatives considered

- **Keep CLI only (D3 as is).** No new surface to maintain; host models keep
  shelling out. This remains the outcome if the gate fails.
- **Portable server as well.** Changes the fixed `v0.2` tool set and needs
  `agent-braid-tooling/v0.3`; bundle it with #771 once that issue's criteria hold.
- **Expose execution tools (`prepare`, launch).** Rejected: operator authority,
  environment-hash and quota reasons above; Article 20.
- **Pagination or truncation.** Rejected for v0.1: more arguments or silent loss.

## Consequences

- Positive: hosts can report what the harness records say without a shell, with the
  CLI's limits preserved and no authority added.
- Negative: four more tools to keep at parity with the CLI; installed verifiers and
  native evidence that count plugin tools change; SPEC-047 telemetry counts the
  tools as `other` until its operation enum is extended (SPEC-077 OD-4).
- Compatibility: additive; rollback is reinstalling the previous plugin release.
- Security: new trust boundary at the host-supplied path, closed by descriptor-walk
  resolution without links and uniform refusals.
- Research: engineering only; the validity hypothesis may be refuted (clause zero).

## Validation

Planned in SPEC-077 [validation-plan.md](../../specs/077-harness-mcp-readonly/validation-plan.md):
differential CLI parity, containment and bound tests with mutation controls, and the
held-out three-host validity run. None has run.
