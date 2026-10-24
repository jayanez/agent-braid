# ADR 0030: Native plugin surface naming

- **Status:** Accepted on 2026-10-24 by the founder (conversation decision in the
  SPEC-054 pull request). Adoption authorizes implementation tracks T002–T008
  only; native observation, release, tag and `plugin-dist` publication remain
  separate founder decisions.
- **Date:** 2026-10-24
- **Articles:** 0, 14–16, 19, 20, 23, 24
- **Specification:** [SPEC-054](../../specs/054-plugin-surface-naming/spec.md)

## Context

Plugin `0.1.0-alpha.3` repeats `agent-braid` in the plugin name, the MCP server
key and every prompt and skill name. Claude Code qualifies plugin skills as
`/<plugin>:<skill>` and plugin MCP prompts as `/plugin:<plugin>:<server>:<prompt>`,
which produces `/plugin:agent-braid:agent-braid:agent-braid-analyze (MCP)`.
Codex qualifies plugin skills the same way, does not scope plugin MCP server
keys and does not support MCP prompts. The three plugin MCP prompts duplicate
skills that already carry the same guidance.

## Decision proposal

Adopt the [naming policy](../../specs/054-plugin-surface-naming/contracts/naming-policy.md):

1. Keep `agent-braid` as plugin identifier, marketplace entry and MCP server key.
2. The plugin MCP server publishes no prompts (`agent-braid-plugin/v0.2`).
3. Plugin skills drop the brand prefix inside the plugin namespace: `analyze`,
   `plan`, `evidence`, `execute`, `recover`, `setup`. Renaming happens at build
   time; canonical sources and legacy global installs keep prefixed names.
4. Keep all MCP tool names and resource URI schemes; display titles are deferred (additive, no schema bump).
5. Keep the portable `agent-braid-tooling/v0.1` contract, including its prompts;
   unprefixed prompt names are the target of a future versioned contract.
6. Any future tool rename requires a new SPEC-047 telemetry contract version.

This narrows ADR 0024's "unchanged five product skills" decision: skill bodies
remain the canonical guidance, but plugin packaging changes their names and
sibling references through a recorded substitution table.

## Alternatives and consequences

A generic or shorter server key collides across Codex plugins and breaks Claude
permission rules. Keeping unprefixed prompts still duplicates skills. Alias
skills or prompts recreate duplicates. A snake_case tool rename changes three
frozen contracts without evidence of agent benefit. Consequences: alpha users
see renamed skill invocations and lose MCP prompt commands in alpha.4, announced
in release notes; tool ids, permission rules, registry and telemetry are
unchanged; rollback to alpha.3 is a reinstall.

## Compatibility and review

Public contract change: plugin MCP schema v0.1 → v0.2 and plugin skill names in
`0.1.0-alpha.4`. SPEC-040, SPEC-041/042, SPEC-047 and historical evidence remain
unchanged. No constitutional amendment is proposed. Adoption, implementation,
native observation and release remain separate owner decisions.
