# ADR 0031: Portable MCP prompt names

- **Status:** Accepted on 2026-10-25 by the founder (conversation decision).
  Adoption authorizes implementation tasks T002-T008 of SPEC-060 only; native
  observation (T009), release (T010), tagging and any package publication remain
  separate founder decisions.
- **Date:** 2026-10-25
- **Articles:** 0, 14-16, 19, 20, 23, 24
- **Specification:** [SPEC-060](../../specs/060-portable-prompt-names/spec.md)

## Context

[ADR 0030](0030-native-plugin-surface-naming.md) removed the plugin MCP prompts and
unprefixed the plugin skills, and kept the portable contract
`agent-braid-tooling/v0.1` and its prompts `agent-braid-analyze`, `agent-braid-plan`
and `agent-braid-evidence` unchanged, naming `analyze`, `plan` and `evidence` as the
target of a future versioned contract. Claude Code lists a server's prompts as
`/<server key>:<prompt> (MCP)`; with the installer's default key `agent-braid` the
portable prompts display as `/agent-braid:agent-braid-analyze (MCP)`. Codex does not
display MCP prompts. Prompt traffic is not measured by SPEC-047.

## Decision

1. Publish `agent-braid-tooling/v0.2`, a versioned surface contract in which the
   portable server lists the prompts `analyze`, `plan` and `evidence` with the v0.1
   message text.
2. Keep `agent-braid-analyze`, `agent-braid-plan` and `agent-braid-evidence` as
   deprecated aliases, marked in their descriptions and in a `deprecatedPrompts`
   capabilities entry, for a window of N = 2 releases, then remove them in
   `agent-braid-tooling/v0.3` after an owner decision and a repository check. The
   window is counted in releases, with an owner decision required if 180 days pass
   without the second release.
3. Record an explicit, bounded exception to ADR 0030's rule that deprecated aliases
   are not published where they recreate a duplicate invocation: it covers only the
   three portable-server prompt aliases; the plugin keeps no prompts and no alias
   exists for tools, skills, resources or the server key.
4. Version the surface, not the envelope (recommended scope B): the capabilities
   resource reports `agent-braid-tooling/v0.2` and
   `envelopeSchemaVersion` `agent-braid-tooling/v0.1`; tool envelopes, output
   schemas, provenance, resource URIs, the plugin facade and the System One verifier
   stay as they are. Scope A (stamp v0.2 everywhere) is an alternative recorded for
   the owner.
5. Change nothing in SPEC-047 (prompts are not counted, enums unchanged), in the
   receipt-owned legacy skills (SPEC-041/042) or in installed host configuration.
6. Carry the change in the next Python package release (`0.1.0a2`); no plugin
   schema bump or plugin release is required.

## Alternatives and consequences

Renaming inside v0.1 breaks the frozen contract. Unprefixed names without aliases
shorten the surface but break existing invocations at once. Indefinite aliases keep a
permanent duplicate. A calendar-only window can expire without a release. Scope A
changes plugin-visible provenance and four test modules for no envelope change.
Consequences: during the window Claude Code lists six prompts for a portable server
(three canonical, three deprecated); a user with both the native plugin and the
portable server under the key `agent-braid` sees the slash name
`/agent-braid:analyze` twice (skill and `(MCP)` prompt), which the documentation
must address and a native observation must characterise; rollback is a package
reinstall with no stored state; the portable server gains a second named version
identifier to maintain.

## Compatibility and review

Public contract change: new portable surface contract v0.2 (additive names, retained
aliases, two capabilities keys). Unchanged: tool names and schemas, envelope v0.1,
resource URIs, plugin `agent-braid-plugin/v0.2`, registry v0.2, SPEC-047 v1,
SPEC-040/041/042/046/054 accepted files and all frozen evidence. No constitutional
amendment is proposed. The decisions OD-1 to OD-8 (all decided) are recorded in the
[plan](../../specs/060-portable-prompt-names/plan.md#human-review-and-unresolved-decisions).
