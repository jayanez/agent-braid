# SPEC-060: Portable MCP prompt names

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** specification only; [ADR 0031](../../docs/adr/0031-portable-prompt-names.md)
is Proposed; no implementation, release, tag or publication is authorized.
The owner selected the direction on 2026-10-25 (see Owner decisions); this
document makes it reviewable and records the decisions it still needs.

## Purpose and scope

SPEC-054 fixed the native plugin's long names and left the portable MCP server
(`agent-braid tooling serve`, contract `agent-braid-tooling/v0.1`, SPEC-040)
untouched. The portable server still publishes the prompts `agent-braid-analyze`,
`agent-braid-plan` and `agent-braid-evidence`. In Claude Code, a server registered
under the key `agent-braid` (the default key of `tooling install`) lists them as
`/agent-braid:agent-braid-analyze (MCP)`, which repeats the brand inside its own
namespace. SPEC-054 recorded the unprefixed names `analyze`, `plan` and `evidence`
as the target of a future versioned contract.

This specification defines that contract, `agent-braid-tooling/v0.2`:

1. the portable server publishes the unprefixed prompts `analyze`, `plan` and
   `evidence`;
2. the three old `agent-braid-*` prompt names remain as deprecated aliases for a
   bounded window, which is an explicit, narrow exception to the SPEC-054 rule
   that aliases SHALL NOT recreate a duplicate invocation;
3. it fixes exactly what the version change covers, the effect on tests,
   telemetry, installed hosts and the plugin facade, migration and rollback, the
   removal criterion and the release impact.

Exclusions: no change to tool names, tool schemas, tool-result envelopes (under
the recommended scope, see REQ-003), resource URIs, the plugin server (which
still publishes no prompts), the plugin skills, the receipt-owned legacy skill
install (SPEC-041/042), the SPEC-047 data contract, the registry schemas or any
frozen evidence. No research protocol or scientific claim is involved.

The normative delta is in [contracts/interface-delta.md](contracts/interface-delta.md).
Reused and new sources are in [research.md](research.md).

## Authorities

Constitution clause zero and Articles 14, 15, 16, 19, 20, 23 and 24;
[GOVERNANCE.md](../../GOVERNANCE.md) (public API or schema change requires a
migration note and versioning impact); ADR 0021, ADR 0024, accepted
[ADR 0030](../../docs/adr/0030-native-plugin-surface-naming.md) and proposed
[ADR 0031](../../docs/adr/0031-portable-prompt-names.md); SPEC-040
[interface](../040-portable-mcp-surface/contracts/interface.md); SPEC-054
[naming policy](../054-plugin-surface-naming/contracts/naming-policy.md);
SPEC-047 [data contract](../047-local-technical-telemetry/data-contract.md).

## Owner decisions recorded

| ID | Decision (2026-10-25) |
|---|---|
| D1 | Address the portable prompt names with a new versioned portable contract, `agent-braid-tooling/v0.2`. |
| D2 | v0.2 publishes the unprefixed prompt names `analyze`, `plan`, `evidence`. |
| D3 | v0.2 also keeps the old `agent-braid-*` names as deprecated aliases for a bounded window. |

These define the specification. They are not ADR adoption, implementation
approval or release approval. The numeric window, the version-stamp scope and
the other points marked OD in [plan.md](plan.md#human-review-and-unresolved-decisions)
are proposals for the owner.

## Requirements and acceptance scenarios

### REQ-001 — Unprefixed canonical prompts

The v0.2 portable server lists and serves the prompts `analyze`, `plan` and
`evidence`. Their message text equals the v0.1 text of the corresponding
`agent-braid-*` prompt byte for byte.

**SC-001:** Given a v0.2 server and an SDK client, when the client lists prompts
and requests `analyze`, `plan` and `evidence`, then all three are listed, each
result carries exactly the v0.1 message text of its predecessor, an unknown name
is refused with no side effect, and an oversized argument map is refused as in v0.1.

Verification: [procedure_001](validation-plan.md); T002.

### REQ-002 — Bounded deprecated aliases

The old names `agent-braid-analyze`, `agent-braid-plan` and `agent-braid-evidence`
remain requestable and listed as deprecated aliases of the canonical prompts during
a defined window, and only there. The alias message text equals the canonical text;
only the list description and the result description state the deprecation, the
canonical replacement and the contract version that removes the alias. The policy
exception is defined in the contract: it applies to the portable server's prompts
only, never to the plugin server, tools, skills or resources, and never extends
silently.

**SC-002:** Given a v0.2 server, when prompts are listed and each alias is
requested, then the listing orders canonical names before aliases, every alias
description starts with the deprecation marker and names its replacement, each alias
returns the canonical message text, and the capabilities resource lists the aliases
under `deprecatedPrompts` and not under `prompts`.

Verification: [procedure_002](validation-plan.md); T003.

### REQ-003 — Scope of the version change

The contract version `agent-braid-tooling/v0.2` identifies the server surface
(capabilities resource, prompt set, contract document). The tool-result envelope
schema, its `schemaVersion` stamp (`agent-braid-tooling/v0.1`), the tool output
schemas, the provenance block and the resource URIs are unchanged. The capabilities
resource reports both identifiers so a client can tell the surface from the envelope.
(Alternative A, stamping v0.2 everywhere, is recorded as OD-1 with its effects.)

**SC-003:** Given a v0.2 server, when every tool is invoked and every resource is
read, then envelopes, output schemas and provenance equal the v0.1 server's
byte-for-byte on identical inputs, and the capabilities resource reports
`schemaVersion` `agent-braid-tooling/v0.2` and `envelopeSchemaVersion`
`agent-braid-tooling/v0.1`.

Verification: [procedure_003](validation-plan.md); T004.

### REQ-004 — Plugin facade unchanged

The plugin MCP server still advertises no prompts capability and returns no prompts.
Its tool envelopes (`agent-braid-plugin/v0.2`, including the nested core provenance),
its per-workspace capabilities resource and its tool, resource and permission names
are byte-identical to the alpha.4 behavior, although it derives from the same core.

**SC-004:** Given a plugin connection with two registered workspaces, when it
initializes, lists prompts, requests a canonical name and an alias, reads each
`capabilities` resource and invokes each tool on identical inputs, then the prompts
capability is absent, both requests are refused without side effects, the
capabilities resources contain neither `prompts` nor `deprecatedPrompts` nor
`envelopeSchemaVersion`, and every other output equals the alpha.4 output.

Verification: [procedure_004](validation-plan.md); T005.

### REQ-005 — Dependent contracts unchanged

Keep unchanged: the tool names, including the nine plugin tool names; the SPEC-047
`mcp` operation enum, batch and store contracts (prompts are not counted); the
receipt-owned legacy global skill install and its `agent-braid-*` skill names; the
host configuration written by `tooling configure|install|update` (server key,
command and arguments); and the System One verifier that checks the envelope stamp.

**SC-005:** Given the existing suites for telemetry, legacy install, host
configuration, the plugin and the System One verifier, when they run against the
v0.2 candidate with only the intentional prompt and capabilities assertions
changed, then they pass, a prompt request records no telemetry operation, and a
previewed host configuration is byte-identical to the v0.1 preview.

Verification: [procedure_005](validation-plan.md); T004, T006.

### REQ-006 — Migration and rollback for registered portable servers

A user who registered the portable server needs no configuration change to adopt
v0.2, keeps working invocations of the old names during the window, and can roll
back by reinstalling the earlier package. The documentation states the Claude Code
display forms before and during the window, that Codex does not display MCP
prompts, and the host-key collision caveat of REQ-010.

**SC-006:** Given a host configuration written by the v0.1 installer, when the
package is updated to the candidate and the host reconnects, then the same
configuration starts the v0.2 server, both names resolve, and after reinstalling
the earlier package the old names resolve and the new names are refused, with the
host configuration and any result roots unchanged.

Verification: [procedure_006](validation-plan.md); T008.

### REQ-007 — Window and removal criterion

The window is the first release that carries v0.2 plus one more release (N = 2
releases, an OD-2 proposal). Aliases are removed by a later contract version,
`agent-braid-tooling/v0.3`, only when every criterion in the contract holds; the
window never extends silently, and usage is not a criterion because prompt traffic
is not measured.

**SC-007:** Given the contract, when the removal criterion is read against a
proposed removal, then a missing release count, release note, owner decision or
repository-reference check blocks the removal, and the document states that
non-use is unmeasured.

Verification: [procedure_007](validation-plan.md); T011.

### REQ-008 — Release and versioning impact

Name the carrier and the effects without authorizing a release: the Python package
version and `serverInfo.version` (proposed `0.1.0a2`), the contract identifier, the
absence of a required plugin release or plugin schema change, and the release notes
content (new names, alias window, removal contract, rollback).

**SC-008:** Given the release-readiness record, when it is reviewed, then it names
the package version, the contract versions, the exact list of changed and unchanged
surfaces, the migration and rollback notes, and states that no release, tag or
publication was performed or authorized.

Verification: [procedure_008](validation-plan.md); T008, T010.

### REQ-009 — Documentation

English documentation shows the new names as the primary invocation, marks the old
names deprecated, links the contract and the removal criterion, and amends the
SPEC-054 naming-policy rule on deprecated aliases by pointer, without rewriting
SPEC-054's accepted files.

**SC-009:** Given updated documentation, when it is searched for prompt names,
then the unprefixed names appear as primary, every `agent-braid-*` prompt mention is
marked deprecated or historical, and no document claims Codex displays MCP prompts
or that the plugin publishes prompts.

Verification: [procedure_009](validation-plan.md); T007.

### REQ-010 — Host observation and the key-collision caveat

Observe the v0.2 portable server in a real Claude Code profile (and record that
Codex lists no prompts) before any release, including the case where both the
native plugin and the portable server are installed.

**SC-010:** Given the source-bound candidate registered as a portable server under
the default key and, separately, alongside the native plugin, when Claude Code lists
slash commands, then the observed names match the contract table, the observation
records whether the portable prompt `/agent-braid:analyze (MCP)` and the plugin
skill `/agent-braid:analyze` can be confused, and the outcome, environment and
limits are recorded separately from package checks.

Verification: [procedure_010](validation-plan.md); T009.

### REQ-011 — Frozen evidence untouched

No frozen historical evidence, closed receipt, accepted review or SPEC-040/046/054
artifact is rewritten. The prompt names inside them remain true for their candidates.

**SC-011:** Given the final change set, when paths are compared with the frozen
inventory, then no file under a frozen evidence path, no SPEC-054 file and no
accepted ADR is modified, and the v0.1 contract text remains available as history.

Verification: [procedure_011](validation-plan.md); T010.

## Scientific boundaries and compatibility

Engineering only; no hypothesis. Names do not change effects, authority, analysis
results or evidence. Public contract impact: new `agent-braid-tooling/v0.2`
surface contract (additive prompt names; aliases retained; capabilities resource
gains `envelopeSchemaVersion` and `deprecatedPrompts` and a new `schemaVersion`
value). Unchanged under the recommendation: tool envelope schema `v0.1`, tool names,
resource URIs, plugin `agent-braid-plugin/v0.2`, registry v0.2, SPEC-047 v1,
SPEC-041/042 installs. A later `v0.3` removes the aliases.

## Evidence and unresolved questions

Planned procedures are not obtained evidence; see [validation-plan.md](validation-plan.md)
and `assurance.json`. Host behavior is taken from the SPEC-054 research and the
sources in [research.md](research.md); the display of the new names and of a
portable/plugin collision has not been observed (T009). Open decisions are listed
in [plan.md](plan.md#human-review-and-unresolved-decisions).
