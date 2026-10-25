# Portable MCP contract `agent-braid-tooling/v0.2`: delta against v0.1

Status: proposed contract for SPEC-060 (ADR 0031 Proposed). Key words SHALL,
SHOULD and MAY follow the Constitution. This document lists only what changes;
everything else in the [SPEC-040 interface](../../040-portable-mcp-surface/contracts/interface.md)
(transport, tools, envelope, resources, evidence chunks, cancellation, authority)
stays normative for v0.2 and is not repeated. Source labels refer to
[research.md](../research.md).

## 1. What the version identifies

| Identifier | v0.1 | v0.2 | Where it appears |
|---|---|---|---|
| Server surface contract | `agent-braid-tooling/v0.1` | `agent-braid-tooling/v0.2` | `schemaVersion` of the `agent-braid://capabilities` resource; this document |
| Envelope schema | `agent-braid-tooling/v0.1` | `agent-braid-tooling/v0.1` (unchanged, recommended scope) | `schemaVersion` of every tool envelope; tool `outputSchema` const; `provenance.schemaVersion`; `envelopeSchemaVersion` of the capabilities resource |
| Plugin envelope | `agent-braid-plugin/v0.2` | `agent-braid-plugin/v0.2` (unchanged) | plugin tool envelopes only |
| Package and `serverInfo.version` | `0.1.0a1` | proposed `0.1.0a2` (OD-3) | wheel metadata, `serverInfo.version` |

The recommended scope (call it scope B) versions the surface and keeps the
envelope stamp. Scope A would stamp `agent-braid-tooling/v0.2` on every envelope,
output schema and provenance block; it is recorded in the plan as OD-1 with these
effects: the plugin facade derives from the same core and embeds the core
provenance in its `agent-braid-plugin/v0.2` envelopes, so scope A would change the
plugin's tool output without a plugin schema bump unless the plugin pins the old
stamp; four test modules (`test_tooling_mcp`, `test_tooling_present`,
`test_tooling_presentation_acceptance`, `test_tooling_skills_acceptance`) pin the
literal v0.1 stamp, one of them as an equality on a live envelope; and the System One verifier
compares the envelope stamp to the module constant. Scope B changes none of them.
Implementation needs two constants (surface and envelope) where v0.1 had one.

## 2. Prompt table

Message text is identical in all rows of the same family. Texts are the v0.1
`_PROMPT_TEXT` values, reproduced here for the byte comparison in procedure_001.

| Name | Status | Replaced by | Removed in | v0.1 name |
|---|---|---|---|---|
| `analyze` | canonical | n/a | n/a | `agent-braid-analyze` |
| `plan` | canonical | n/a | n/a | `agent-braid-plan` |
| `evidence` | canonical | n/a | n/a | `agent-braid-evidence` |
| `agent-braid-analyze` | deprecated alias | `analyze` | `agent-braid-tooling/v0.3` | same |
| `agent-braid-plan` | deprecated alias | `plan` | `agent-braid-tooling/v0.3` | same |
| `agent-braid-evidence` | deprecated alias | `evidence` | `agent-braid-tooling/v0.3` | same |

Message texts (one `user` text message per prompt):

- `analyze` and `agent-braid-analyze`: "Analyze the supplied bounded AIM or Git work
  request. Explain conflicts, conditions, unknown coverage, evidence and limits. Do
  not infer execution authority."
- `plan` and `agent-braid-plan`: "Use Agent Braid analysis and preparation to inspect
  dependencies and the exact bounded plan. Explain what requires existing operator
  authorization. Never request or create a grant through a tool."
- `evidence` and `agent-braid-evidence`: "Retrieve only the referenced owned evidence.
  Reconstruct bytes from the manifest and chunk chain, verify every chunk and the
  complete SHA-256 and length before parsing or comparison."

### prompts/list

- Order: the three canonical names in the order analyze, plan, evidence, then the
  three aliases in the same order.
- Canonical `description`: the message text, as v0.1 did for its names.
- Alias `description`: `[Deprecated alias of `<canonical>`; removed in
  agent-braid-tooling/v0.3] ` followed by the message text.
- No `arguments` are declared; arguments remain accepted and bounded at 16 KiB as in v0.1.

### prompts/get

- Canonical: `description` "Read-only bounded workflow guidance", unchanged.
- Alias: `description` "Deprecated alias of `<canonical>`; removed in
  agent-braid-tooling/v0.3. Read-only bounded workflow guidance"; the message text
  equals the canonical text and carries no extra instruction, so a v0.1 consumer
  parsing the body sees unchanged bytes.
- Any other name: the v0.1 refusal ("Unknown prompt"), no side effect.
- Prompts perform no writes, issue no grant and are not telemetry operations (unchanged).

## 3. Capabilities resource

`agent-braid://capabilities` (and the plugin's per-workspace capabilities resource,
see section 5):

| Key | v0.1 | v0.2 |
|---|---|---|
| `schemaVersion` | `agent-braid-tooling/v0.1` | `agent-braid-tooling/v0.2` |
| `envelopeSchemaVersion` | absent | `agent-braid-tooling/v0.1` |
| `tools`, `resources`, `mode`, `limits` | as defined | unchanged |
| `prompts` | the three prefixed names | `["analyze", "plan", "evidence"]` (canonical only) |
| `deprecatedPrompts` | absent | three objects `{"name", "replacedBy", "removedIn"}` for the aliases, in table order |

A client that reads `prompts` sees only supported names; a client that lists
prompts through the protocol sees both sets.

## 4. Deprecated-alias exception (amends the SPEC-054 change-control rule)

SPEC-054 states: deprecated aliases SHALL NOT be published on a surface where they
would recreate a duplicate invocation. Publishing the aliases in v0.2 deliberately
recreates a duplicate invocation of the same prompt in hosts that list MCP prompts
(Claude Code lists both `/agent-braid:analyze (MCP)` and
`/agent-braid:agent-braid-analyze (MCP)`; Codex lists neither). The exception is
therefore limited as follows, and any condition failing means the alias SHALL NOT
be published:

1. **Scope.** Only the three portable-server prompt aliases named above. No alias
   for tools, resources, resource schemes, skills (plugin or legacy), the server
   key or the plugin server. The plugin still publishes no prompts.
2. **Reason.** A server named by a user-controlled host key already holds users'
   habits and scripts for the old names; the prompt text is advisory, read-only and
   identical, so the duplicate is cosmetic and cannot change any effect or authority.
3. **Window.** The aliases are published by the first release that carries v0.2 and
   by exactly one further release (N = 2 releases, OD-2). A release is a tagged
   package release of the portable server; plugin releases do not count because the
   plugin publishes no prompts. The window is counted in releases, not days.
4. **Marking.** Every alias carries the deprecation description of section 2, the
   `deprecatedPrompts` entry of section 3, and a release-note line.
5. **Removal criterion (all must hold).** (a) At least two releases carried the
   aliases with the deprecation marking. (b) The release notes of both named the
   removal contract. (c) The owner recorded a removal decision citing the new
   contract (`agent-braid-tooling/v0.3`, its own SPEC amendment and ADR change).
   (d) A repository search finds no reference to the alias names outside frozen
   evidence, the alias table, its tests and deprecation documentation. (e) The
   legacy skill install, host configuration and plugin surfaces do not reference
   the alias names (they do not at v0.2; this is rechecked).
6. **No usage criterion.** Prompt requests are not counted by SPEC-047 and this
   contract adds no counter, so non-use cannot be observed and is not a condition.
   The release-count rule bounds the exposure instead.
7. **No silent extension.** If the second window release has not shipped 180 days
   after the first, the owner SHALL record an explicit decision to remove, extend
   with a new count, or keep waiting; documentation then states the decision.
   Absent a decision the aliases remain, flagged as an overdue deprecation.

## 5. Plugin facade

The plugin server derives from the same core but SHALL:

- register no prompt handlers and advertise no prompts capability (unchanged);
- pop `prompts` and `deprecatedPrompts` from its capabilities resource and SHALL
  NOT emit `envelopeSchemaVersion`; its capabilities `schemaVersion` keeps the
  alpha.4 value so the resource bytes equal alpha.4;
- keep `agent-braid-plugin/v0.2` envelopes with the core provenance unchanged
  (scope B guarantees this; scope A would not without a pin).

## 6. Compatibility, migration and rollback

| Surface | Effect of v0.2 |
|---|---|
| Existing host configuration (SPEC-041/042 installer) | Unchanged: same server key, command, arguments; no reinstall needed |
| Claude Code display, default key `agent-braid` | Before: `/agent-braid:agent-braid-analyze (MCP)`. During the window: `/agent-braid:analyze (MCP)` plus the deprecated aliases. After v0.3: canonical only |
| Codex | Lists no MCP prompts before or after (O); unaffected |
| Tools, resources, evidence chunks, grants, telemetry, results | Unchanged |
| Legacy global skills `agent-braid-*` | Unchanged (no host namespace) |
| Native plugin | Unchanged; skills `analyze`, `plan`, `evidence` |

Migration: update the package and reconnect the host MCP; no configuration edit.
Rollback: reinstall the earlier package; the v0.1 server lists only the prefixed
names and refuses the unprefixed ones as unknown prompts; no stored state is
involved (the portable server has no registry; telemetry and result roots are
unchanged). Release notes SHALL list the new names, the aliases, their removal
contract and this rollback.

Host-key collision caveat: a Claude Code user with both the native plugin (skill
`/agent-braid:analyze`) and the portable server registered under the key
`agent-braid` (prompt `/agent-braid:analyze (MCP)`) sees two entries with the same
slash name, distinguished only by the `(MCP)` suffix. This is a consequence of the
unprefixed target and of the default key. Documentation SHALL advise either not to
install both surfaces or to register the portable server under another key; the
observation (T009) records whether Claude Code disambiguates them.

## 7. Verification hooks

Negative controls the implementation SHALL include: a changed canonical text; an
alias missing its marking; an alias listed under `prompts`; a plugin capabilities
resource containing a prompt key; a changed envelope stamp under scope B; an
unknown prompt name. Pinned v0.1 assertions are enumerated in the plan and changed
only for prompt and capabilities expectations.
