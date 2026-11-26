# SPEC-060: Portable MCP prompt names

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** draft (`assurance.json`: stage `draft`, human review `approved` by
[founder-review-20261027.json](founder-review-20261027.json), 2026-10-27, bound to
commit `f9329134`). T001-T010 are done; T009 closed with bounded scope (CLI and
loader observation, see [native observation](evidence/native-observation-0.1.0a2.md)).
The candidate is published as pre-release `v0.1.0-alpha.2`
([release record](evidence/release-0.1.0a2.md)). T011 (alias removal under
`agent-braid-tooling/v0.3`) is open and deferred. The approval covers the spec at
`f9329134`; this refinement is not yet reviewed.

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
[ADR 0030](../../docs/adr/0030-native-plugin-surface-naming.md) and accepted
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

| D4 | OD-1: scope B, version the surface only; `envelopeSchemaVersion` stays v0.1. |
| D5 | OD-2/OD-4: window of 2 releases; aliases listed and marked deprecated; removal in v0.3 after an owner decision and a repository search; 180-day re-decision trigger. |
| D6 | OD-3: carrier is Python package `0.1.0a2`; no plugin release and no plugin schema bump. |
| D7 | OD-5: document not registering the portable server under key `agent-braid` next to the plugin, observe it in T009, no code change. |
| D8 | ADR 0031 adopted and T002-T008 authorized; T009 observation and T010 release stay separate decisions. |

OD-6 (SPEC-054 files untouched) and OD-7 (number 060) stand as recommended. See
[plan.md](plan.md#human-review-and-unresolved-decisions).

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
(Alternative A, stamping v0.2 everywhere, was rejected under D4.)

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
releases, D5). Aliases are removed by a later contract version,
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
version and `serverInfo.version` (`0.1.0a2`, D6), the contract identifier, the
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

Obtained evidence is in `assurance.json` and [evidence/](evidence/); procedures
without obtained evidence are planned only, see [validation-plan.md](validation-plan.md).
Host behavior is taken from the SPEC-054 research and the sources in
[research.md](research.md). The native observation (T009) covers CLI and loader
listings in disposable profiles on macOS arm64; the T009 closure records the
slash-menu display as not observed. Owner screenshots of 2026-10-27 later recorded
it in [interactive-slash-result.md](evidence/interactive-slash-result.md): under the
key `agent-braid` the prompts show as `/agent-braid:analyze (MCP)` and the plugin
skills as `* /agent-braid:analyze`, distinguishable by the `(MCP)` suffix, the `*`
marker and the description, with no warning and no hidden entry; under
`portable-braid` there is no collision. T009, `assurance.json` and `tasks.md` do not
cite that record. Decisions
OD-1 to OD-8 are decided, see [plan.md](plan.md#human-review-and-unresolved-decisions).
Open questions: see [Open questions](#open-questions).

## Non-functional requirements

No performance or availability requirement applies in this spec. Operational and
quality constraints it states:

- Size limit: an oversized prompt argument map is refused as in v0.1 (REQ-001).
- Text integrity: alias and canonical text equal the v0.1 text byte for byte, derived
  from one ordered registry so they cannot drift (REQ-001, REQ-002; plan, Design 2).
- Compatibility: envelopes, output schemas, provenance, resource URIs, plugin bytes
  and host configuration previews stay byte-identical (REQ-003, REQ-004, REQ-005).
- Observability: prompt requests record no telemetry operation (REQ-005).
- Bounded window: aliases live two releases and are removed only by `v0.3` (REQ-007).
- Reversibility: reinstalling the earlier package restores the old behavior with
  configuration and result roots unchanged (REQ-006).

## Security and privacy

No security or privacy obligation applies: no grant or execution path changes, and
prompts remain read-only text (`assurance.json` execution contract). The refusal of
oversized arguments and of unknown names without side effect is stated in REQ-001.

## Terminology

Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md). Terms this
spec uses:

- Surface version: the contract version `agent-braid-tooling/v0.2` of the server
  surface (capabilities resource, prompt set, contract document), distinct from the
  envelope version (REQ-003).
- Envelope version: `agent-braid-tooling/v0.1`, the `schemaVersion` stamp of
  tool-result envelopes (REQ-003).
- Canonical prompt: an unprefixed prompt `analyze`, `plan` or `evidence` (REQ-001).
- Deprecated alias: an old prompt `agent-braid-analyze`, `agent-braid-plan` or
  `agent-braid-evidence`, kept for the window (REQ-002).
- Window: the first release that carries v0.2 plus one more release (REQ-007).
- Portable server: `agent-braid tooling serve`; plugin server: the native plugin's
  MCP server (REQ-004).

Values named in this spec:

- Prompt names: canonical `analyze`, `plan`, `evidence`; aliases
  `agent-braid-analyze`, `agent-braid-plan`, `agent-braid-evidence` (REQ-001,
  REQ-002).
- Contract versions: surface `agent-braid-tooling/v0.2`; envelope
  `agent-braid-tooling/v0.1`; alias removal `agent-braid-tooling/v0.3`; plugin
  `agent-braid-plugin/v0.2` (REQ-003, REQ-004, REQ-007).
- Capabilities keys: `prompts` (canonical names), `deprecatedPrompts` (aliases),
  `envelopeSchemaVersion` (REQ-002, REQ-003).

## Risks and assumptions

- Risk: the portable prompt `/agent-braid:analyze (MCP)` and the plugin skill
  `/agent-braid:analyze` can be confused under the default key; mitigated by
  documentation; distinguishable in the observed menu, no warning shown; the record
  is not bound to SC-010 (REQ-009, REQ-010, T009).
- Risk: removing the aliases breaks consumers not known to the repository
  (REQ-007, T011).
- Risk: the window never ends if no owner decision is taken; the 180-day trigger
  forces a decision by 2027-04-25 (REQ-007, T011).
- Risk: the plugin facade exposes the new capabilities keys (REQ-004, T005).
- Assumption: host behavior matches the SPEC-054 research of 2026-10-24 (REQ-010,
  T009).
- Assumption: portable-server users exist under the installer default key (REQ-006).
- Assumption: an alias window counted in releases is acceptable for an alpha package
  (REQ-007).
- Assumption: prompt use is not measurable, so non-use is no removal criterion
  (REQ-007).

## Exit criteria

Verification of the v0.2 candidate is complete when each of SC-001 to SC-011 has
obtained evidence bound in `assurance.json` or an owner-recorded bounded closure:
SC-001 to SC-006, SC-008 and SC-011 have bound evidence; SC-009 (T007) and SC-010
(T009, bounded closure) do not yet. SC-007 is verified only when T011 runs, which
needs two published window releases and an owner removal decision (T011, REQ-007).

## Open questions

- OQ-1: Does the owner decide by 2027-04-25 (180 days after the first release,
  [release record](evidence/release-0.1.0a2.md)) to remove the aliases under
  `v0.3` or to extend the window? Owner: founder (REQ-007, T011).
- OQ-2: Should [interactive-slash-result.md](evidence/interactive-slash-result.md)
  be bound to SC-010 and T009? Owner: founder (REQ-010).
- OQ-3: Should the obtained evidence be bound in `assurance.json`: for REQ-010,
  `evidence/interactive-slash-result.md` and
  `evidence/native-observation-0.1.0a2-addendum.md`; for REQ-009 (T007), for which no
  documentation diff or search record exists under `evidence/`? The record has
  `human_review` approved and the founder review `limits` bind acceptance to the
  frozen commit, so the edit may need a new owner review. Owner: founder (REQ-009,
  REQ-010).
