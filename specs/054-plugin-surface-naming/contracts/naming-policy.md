# Native plugin surface naming policy v1

Status: draft contract for SPEC-054. Key words SHALL, SHOULD and MAY follow the
Constitution. Source labels refer to [research.md](../research.md): **N** normative
source, **C** convention, **O** observed host behavior, **D** owner decision.

## Principles

1. **Brand once.** A host namespace already carries the plugin identifier.
   Names inside that namespace SHALL NOT repeat it (C: Claude Code and Codex
   qualify plugin components as `<plugin>:<component>`; D2).
2. **One invocation surface per action.** A user-facing workflow SHALL be
   offered once per host. Skills are that surface for the native plugin because
   they work in both hosts; MCP prompts do not reach Codex (O; D1).
3. **Stable programmatic identifiers.** Names consumed by permission rules,
   telemetry, receipts or frozen contracts SHALL change only through a new
   versioned contract with a migration note (N: GOVERNANCE; C: MCP reference
   servers treat a tool rename as a breaking change; D4).
4. **Display text is separate from identifiers.** Human-readable labels belong in
   `displayName`, `title` or descriptions, never in identifiers (N: MCP
   BaseMetadata `name` vs `title`).
5. **Portable lowest common denominator.** Identifiers SHALL use lowercase ASCII
   letters, digits and single hyphens, start with a letter and stay at most 64
   characters, which satisfies every cited host and specification limit (N).

## Surface rules

| Surface | Rule | Current value | Policy value | Basis |
|---|---|---|---|---|
| Plugin `name` (both manifests) | kebab-case brand token; stable | `agent-braid` | unchanged | N (Claude Code, Codex manifest rules), D |
| Marketplace and entry `name` | equal to the plugin name | `agent-braid` | unchanged | N, C |
| `displayName` / `interface.displayName` | product name with spaces | `Agent Braid` | unchanged | N |
| MCP server key (`mcp.json`, `.mcp.json`) | equal to the plugin name; no `__`, no trailing `_` | `agent-braid` | unchanged | C (official plugins), O (Codex does not scope plugin server keys; duplicates are skipped), N (Claude permission rules) |
| MCP `serverInfo.name` | distinct per server program | `agent-braid-plugin`, `agent-braid-tooling` | unchanged | N (not a namespace; display and logging only) |
| MCP `serverInfo.title` | MAY be added later (additive) | absent | absent in alpha.4 (D5) | N |
| MCP tool `name` | unprefixed lowercase verb or verb-noun in kebab-case; unique per server | 9 names | unchanged | N (MCP tool name SHOULD rules), D4 |
| MCP tool `title` | MAY be added later (additive) | absent | absent in alpha.4 (D5) | N |
| MCP prompts, plugin server | SHALL NOT be published | 3 prompts | none (`agent-braid-plugin/v0.2`) | D1 |
| MCP prompts, portable server | frozen in `agent-braid-tooling/v0.1` | `agent-braid-analyze`, `agent-braid-plan`, `agent-braid-evidence` | unchanged; future target `analyze`, `plan`, `evidence` | D3 |
| Resource URI scheme | RFC 3986 custom scheme owned by the product; workspace in the authority component | `agent-braid://`, `agent-braid-plugin://<workspaceId>/` | unchanged | N (custom schemes per RFC 3986) |
| Plugin skills | unprefixed action or noun; directory equals `name` | `agent-braid-analyze` … , `setup` | `analyze`, `plan`, `evidence`, `execute`, `recover`, `setup` | N (Agent Skills), D2 |
| Legacy global skills (receipt install) | keep the brand prefix, because no host namespace exists | `agent-braid-*` | unchanged | C, D3 |

## Resulting invocations

| Host | Before (`0.1.0-alpha.3`) | After (`0.1.0-alpha.4` target) |
|---|---|---|
| Claude Code skill | `/agent-braid:agent-braid-analyze` | `/agent-braid:analyze` |
| Claude Code MCP prompt | `/plugin:agent-braid:agent-braid:agent-braid-analyze (MCP)` | none |
| Claude Code tool id | `mcp__plugin_agent-braid_agent-braid__analyze` | unchanged |
| Codex skill | `agent-braid:agent-braid-analyze` (inferred from source) | `agent-braid:analyze` |
| Codex tool id | `mcp__agent_braid__analyze_work` (hyphens sanitized) | unchanged |

## Reference rules for text

Skill bodies and documentation SHALL reference tools by their bare MCP tool
name (for example `analyze-work`) and SHALL NOT embed a host-qualified tool id,
because Claude Code keeps hyphens and Codex replaces them with underscores (O).
References to sibling skills SHALL use the name valid in the packaging surface:
plugin builds substitute unprefixed names; legacy installs keep the prefixed
canonical names.

## Change control

- Adding display metadata (`title`, descriptions) is additive.
- Removing, adding or renaming a tool, prompt, skill, server key or resource
  scheme requires a new schema version for the affected server, release notes
  naming each change, and an evaluation of SPEC-047 enum impact.
- A tool rename changes the frozen SPEC-047 `mcp` operation enum and therefore
  requires a new telemetry batch/store version and migration decision before it
  can ship.
- Deprecated aliases SHALL NOT be published on a surface where they would
  recreate a duplicate invocation; the plugin migration therefore uses none.
