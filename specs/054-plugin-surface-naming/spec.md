# SPEC-054: Native plugin surface naming

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** specification; ADR 0030 accepted 2026-10-24; implementation tracks
T002-T008 and T010 delivered (see [tasks.md](tasks.md)); T001 owner review and T009
native observation pending; no release, tag or `plugin-dist` publication
authorized.

## Purpose and scope

The native plugin `0.1.0-alpha.3` (SPEC-046) shows long, repetitive invocations in
Claude Code, for example `/plugin:agent-braid:agent-braid:agent-braid-analyze (MCP)`.
The plugin name, the MCP server key and every prompt and skill name all repeat
`agent-braid`, and the plugin MCP server publishes three MCP prompts that
duplicate the packaged skills. Codex does not display MCP prompts at all.

This engineering specification defines one naming policy for every native plugin
surface in Codex and Claude Code: plugin identifier, marketplace entry, MCP server
key and server identity, MCP tools, MCP prompts, MCP resources and skills. It
also defines the migration from the published alpha releases and its effect on
the SPEC-047 telemetry data contract.

Exclusions: no change to the portable MCP server contract
`agent-braid-tooling/v0.1` (SPEC-040), the legacy receipt-owned skill install
(SPEC-041/042), the core analyzer, AIM, grants, runtime authority, the user
registry schema or the SPEC-047 data contract. No research protocol or
scientific claim is involved.

The normative naming rules are in [contracts/naming-policy.md](contracts/naming-policy.md).
Sources and their classification are in [research.md](research.md).

## Authorities

Constitution clause zero and Articles 14, 15, 16, 19, 20, 23 and 24;
[GOVERNANCE.md](../../GOVERNANCE.md) (public API or schema change requires a
migration note and versioning impact); ADR 0021, ADR 0024 and accepted
[ADR 0030](../../docs/adr/0030-native-plugin-surface-naming.md); SPEC-040
[interface](../040-portable-mcp-surface/contracts/interface.md); SPEC-046
[interface](../046-native-ai-plugins/contracts/interface.md); SPEC-047
[data contract](../047-local-technical-telemetry/data-contract.md).

## Owner decisions recorded

On 2026-10-24 the owner selected, for this specification:

| ID | Decision |
|---|---|
| D1 | The plugin MCP server stops publishing MCP prompts; skills are the plugin's only invocation surface. |
| D2 | Plugin skills drop the redundant `agent-braid-` prefix inside the plugin namespace. |
| D3 | The portable server keeps `agent-braid-tooling/v0.1` unchanged; unprefixed prompt names are recorded as the target of a future versioned contract. |
| D4 | MCP tool names stay unchanged; only display metadata may be added. |

These selections define the specification. They are not implementation approval,
release approval or ADR adoption.

## Requirements and acceptance scenarios

### REQ-001 — Naming policy and research record

Publish one naming policy covering all plugin surfaces on both hosts, with each
rule traced to a cited normative source, a convention or an owner decision.

**SC-001:** Given the research record and the naming-policy contract, when the
policy is reviewed against the cited MCP, Agent Skills, Claude Code and Codex
sources, then every rule names its source class (normative, convention, observed
or owner decision), no rule contradicts a cited normative requirement, and host
differences (tool-id sanitization, prompt support, server-key scoping) are explicit.

Verification: [procedure_001](validation-plan.md); T001.

### REQ-002 — Stable identifiers

Keep the plugin identifier, marketplace entry names, MCP server key and MCP tool
names unchanged.

**SC-002:** Given a built plugin candidate, when its Codex and Claude manifests,
both marketplaces, `mcp.json`, `.mcp.json` and the plugin MCP tool list are
inspected, then the plugin and marketplace names are `agent-braid`, the server
key is `agent-braid`, and the tool names are exactly `analyze-work`, `analyze`,
`prepare`, `status`, `execute`, `recover`, `verify`, `plugin-status` and
`workspaces` (subject to runtime enablement); a renamed key or tool fails the check.

Verification: [procedure_002](validation-plan.md); T002.

### REQ-003 — No MCP prompts from the plugin server

The plugin MCP server advertises no prompts capability and returns no prompts.

**SC-003:** Given a plugin MCP connection with two registered workspaces, when the
client initializes, lists prompts and requests `agent-braid-analyze`, then the
server capabilities omit prompts, the listing is empty or the method is not
supported, the request is refused without side effects, and per-workspace
`capabilities` resources no longer list prompts; tools and resources behave as
before.

Verification: [procedure_003](validation-plan.md); T003.

### REQ-004 — Unprefixed plugin skill names

Package the plugin skills as `analyze`, `plan`, `evidence`, `execute`, `recover`
and `setup`, with directory names equal to the `name` field and sibling-skill
references rewritten to the plugin names.

**SC-004:** Given the canonical skill sources and a built plugin, when the packaged
skills are inspected, then each directory equals its frontmatter `name`, every
name satisfies the Agent Skills name rules, the bodies equal the canonical bodies
except for the declared name and cross-reference substitutions, no `agent-braid-`
skill token remains in packaged skills, and the package inventory records the
canonical source hash and the substitution table.

Verification: [procedure_004](validation-plan.md); T004.

### REQ-005 — Legacy and portable surfaces unchanged

Keep the portable MCP server, its prompts and the receipt-owned global skill
install byte- and name-compatible.

**SC-005:** Given the portable server and a legacy receipt install, when prompts,
tools, capabilities and installed skill paths are listed, then they equal the
`agent-braid-tooling/v0.1` and SPEC-041/042 contracts, including the three
`agent-braid-*` prompts and the prefixed global skill directories.

Verification: [procedure_005](validation-plan.md); T005.

### REQ-006 — Versioned migration

Version the change as plugin MCP schema `agent-braid-plugin/v0.2` in plugin
`0.1.0-alpha.4`, with a documented migration and rollback and no aliases.

**SC-006:** Given an `0.1.0-alpha.3` installation with a v0.2 registry and
existing results, when the plugin is updated natively to the candidate on each
host, then the registry and results survive, the old prompt and prefixed plugin
skills are no longer listed, the new skills are listed, existing permission rules
for plugin tools keep matching, release notes name every removed and renamed
invocation, and reinstalling `0.1.0-alpha.3` restores the old names without
registry changes.

Verification: [procedure_006](validation-plan.md); T006, T009.

### REQ-007 — Telemetry contract unchanged

Preserve the SPEC-047 `mcp` operation enum and batch contract.

**SC-007:** Given telemetry `local` and the candidate plugin, when every delegated
tool and the removed prompt request are exercised, then recorded operations stay
within `analyze-work`, `analyze`, `prepare`, `status`, `execute`, `recover`,
`verify` and `other`, no prompt traffic is counted, and the batch schema and
store version are unchanged.

Verification: [procedure_007](validation-plan.md); T007.

### REQ-008 — Documentation and host-neutral references

Update English documentation and skill text so tool references do not assume one
host's qualified tool id.

**SC-008:** Given updated documentation and packaged skills, when they are searched
for invocation names and tool references, then installation docs show
`/agent-braid:<skill>` (Claude Code) and the Codex skill mention form, tool
references use bare MCP tool names, and no document claims Codex displays MCP
prompts.

Verification: [procedure_008](validation-plan.md); T008.

### REQ-009 — Native host observation

Observe the candidate in real Codex and Claude Code user profiles before release.

**SC-009:** Given a source-bound candidate installed natively at user scope, when
each host lists its skills and MCP prompts and runs the analyze skill on a
registered fixture, then the observed names match the policy and the outcome,
environment and limits are recorded separately from package checks.

Verification: [procedure_009](validation-plan.md); T009.

## Scientific boundaries and compatibility

Engineering only; no hypothesis. Naming does not change effects, authority,
analysis results or evidence. Public contract impact: plugin MCP schema
`agent-braid-plugin/v0.1` → `v0.2` (prompts removed; display titles deferred); plugin skill invocation names change in `0.1.0-alpha.4`. Unchanged:
plugin identifier, server key, tool names, resource URI schemes, user registry
`agent-braid-plugin-registry/v0.2`, `agent-braid-tooling/v0.1`, SPEC-041/042
legacy installs and the SPEC-047 v1 data contract. Any future tool rename
changes the frozen telemetry enum and requires a new batch/store contract
version and migration decision.

## Evidence and unresolved questions

Planned procedures are not obtained evidence; see [validation-plan.md](validation-plan.md)
and `assurance.json`. Open items needing owner approval are listed in
[plan.md](plan.md#human-review-and-unresolved-decisions). Host behavior was
established from documentation and source code, not from a native observation of
this candidate; T009 records that observation.
