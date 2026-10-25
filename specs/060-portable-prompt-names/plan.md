# SPEC-060 implementation plan

## Technical context and scope

Python standard library plus the pinned optional `mcp==2.3.0` SDK. Specification
only: nothing below is implemented by this change. Affected code when
implementation is authorized: `agent_braid/tooling_mcp.py` (`_PROMPT_TEXT`,
`list_prompts`, `get_prompt`, `capabilities`, a surface-version constant),
`agent_braid/plugin_mcp.py` (`WorkspaceService.capabilities` must strip the new
keys), the tests that pin prompt names or the v0.1 stamp, English tooling
documentation and the package version. Unaffected: tool definitions and results,
`agent_braid/tooling_install.py`, `agent_braid/tooling_hosts.py`,
`integrations/agent-braid/skills/` bytes, telemetry, registry, core, plugin
skills and every frozen evidence file.

## Constitution check before research

Article 14 requires inspectable evidence in interfaces; prompt names are not
evidence and change none. Article 15 requires effect metadata without vendor
coupling: no tool annotation changes. Article 16 asks for conservative versioning:
the new names are an additive, versioned contract and the removal is deferred to a
second versioned contract. Articles 19-20 keep the work practical and keep analysis
separate from execution: prompts stay read-only text with no grant path. Articles
23-24 forbid back-projecting accidental names as semantics. GOVERNANCE requires a
migration note and versioning impact for a public API change; both are in the
contract. The alias exception departs from the SPEC-054 policy (not a constitutional
MUST); ADR 0031 records it for review. No constitutional amendment is proposed.

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions: host behavior matches the SPEC-054
research; portable-server users exist (the installer defaults to the key
`agent-braid`); an alias window measured in releases is acceptable for an alpha
package; no usage signal for prompts is available.

| Alternative | Outcome |
|---|---|
| Rename the prompts in place inside `v0.1` | Rejected: SPEC-054 D3 froze v0.1; a rename breaks consumers without a version. |
| Publish unprefixed names only (no aliases) | Not selected by the owner (D3); smaller surface but breaks existing habits at once. Remains the fallback if the owner withdraws D3. |
| Keep aliases indefinitely | Rejected: permanent duplicate invocations; contradicts the SPEC-054 principle "one invocation surface per action". |
| Stamp v0.2 on every envelope (scope A) | Not recommended (OD-1): changes plugin-visible provenance and four test modules for no envelope change. |
| Calendar-based window (for example 90 days) | Rejected as primary: releases are owner-gated, so a calendar rule could expire with no release; kept only as the 180-day owner-decision trigger. |
| Hide aliases from `prompts/list` but still answer them | Considered: removes the visible duplicate but makes the alias undiscoverable and its deprecation unannounced. Offered as OD-4. |
| Per-host server key advice instead of a contract | Insufficient alone: the default key stays `agent-braid`. |

## Design and compatibility

1. **Surface versus envelope.** Add a surface constant `agent-braid-tooling/v0.2`
   used by `capabilities()` only; keep `SCHEMA_VERSION` (`v0.1`) for envelopes,
   output schemas and provenance. `capabilities()` also emits
   `envelopeSchemaVersion`.
2. **Prompt registry.** One ordered table of six entries (name, canonical, status,
   text) replaces `_PROMPT_TEXT`; both handlers derive from it, so canonical and
   alias text cannot drift.
3. **Aliases.** Marked per the contract; documented removal in v0.3.
4. **Plugin.** `WorkspaceService.capabilities` pops `prompts`, `deprecatedPrompts`
   and `envelopeSchemaVersion` and restores the alpha.4 `schemaVersion`; the plugin
   server still registers no prompt handlers. A test compares the resource and the
   envelopes with golden alpha.4 bytes.
5. **Pinned v0.1 assertions (enumerated, not exhaustive until T004 searches).**
   `tests/test_tooling_mcp.py` line 59 (live envelope: unchanged under scope B) and
   lines 503-505 (prompt set: changes to the six-name set);
   `tests/test_tooling_present.py`, `tests/test_tooling_presentation_acceptance.py`
   and `tests/test_tooling_skills_acceptance.py` use v0.1 as synthetic envelope
   input (unchanged under scope B). Scenario fixtures and frozen evidence under
   `specs/046-*/evidence/` keep their v0.1 literals and are never edited.
6. **Telemetry (SPEC-047).** The `mcp` operation enum, batch and store versions are
   unchanged; prompt requests were never counted and remain uncounted. A test
   confirms that listing and getting prompts, canonical or alias, records nothing.
7. **Legacy skills and installed hosts (SPEC-041/042).** Skill names and receipt
   paths are unchanged. Host configuration contains no prompt names (only server
   key, command and tool approvals of the form `mcp__<key>__*`), so previews and
   receipts are byte-identical; a test asserts that.
8. **Release.** Python package `0.1.0a1` to a proposed `0.1.0a2` (OD-3), which sets
   `serverInfo.version`. The native plugin vendors the same wheel, so its next
   build embeds the code; the plugin's observable behavior is unchanged
   (REQ-004), so no plugin release, plugin schema bump or tag is required by this
   specification. Building, tagging and publishing remain separate owner decisions.
   How portable users obtain the package (local wheel versus a public index) is not
   established by the repository record; the migration text must name the actual
   channel at release time.
9. **Documentation.** `docs/tooling/HOSTS.md`, `docs/tooling/INSTALL.md`,
   `docs/tooling/SKILLS.md` and `docs/tooling/NATIVE_PLUGINS.md` (collision
   caveat), the SPEC-040 interface (forward pointer to the v0.2 delta, history kept)
   and a forward pointer from the SPEC-054 policy row "MCP prompts, portable
   server" to this contract. SPEC-054's accepted files are not rewritten: the
   pointer lives in this spec and in the docs; if the owner wants an in-place
   pointer in SPEC-054, that is a separate reviewed edit (OD-6).

## Validation strategy

Requirement, scenario, procedure and task mapping is in `assurance.json` and
[validation-plan.md](validation-plan.md). Run
`python3 scripts/validate_change.py --base develop --profile quick` during
implementation and `--profile pr` once on the stable candidate. Native observation
(T009) is separate and never inferred from SDK-client tests. The implementation
must follow the repository's test-first discipline: each negative control in the
contract fails before the behavior exists.

## Constitution check after design

No effect, grant, execution path, analysis result or evidence boundary changes;
prompts stay advisory text. No vendor-specific semantics enter the core. The
departure from the SPEC-054 alias rule is explicit, bounded and owner-reviewable.

## Human review and unresolved decisions

Proposed by this specification; none is decided. Recommendation in brackets.

- **OD-1 Version-stamp scope.** [Scope B: version the surface, keep the envelope
  stamp.] Scope A stamps v0.2 everywhere; it forces a plugin pin (or a visible
  plugin provenance change), edits to four test modules and a System One verifier
  re-check, for no change in envelope shape.
- **OD-2 Window.** [N = 2 releases, then removal in v0.3, with the 180-day owner
  decision trigger.] Alternatives: N = 1 (shorter), N = 3 (gentler).
- **OD-3 Carrier version.** [Python package `0.1.0a2`; no plugin release required.]
- **OD-4 Alias visibility.** [Listed, marked deprecated.] Alternative: answer
  aliases but hide them from `prompts/list` (fewer duplicates, weaker discovery).
- **OD-5 Collision caveat.** [Document "do not register the portable server under
  the key `agent-braid` next to the native plugin" and observe in T009.] Alternative:
  change the installer default key, which alters SPEC-042 and is out of scope here.
- **OD-6 SPEC-054 pointer.** [Keep SPEC-054 files untouched; point from here.]
- **OD-7 Numbering.** SPEC-060 was chosen instead of the free number 055 because
  the milestone index note records 055 and 056 as historical working numbers in the
  #683 commit message; reusing 055 would reintroduce that ambiguity. ADR 0031 is the
  next free ADR (0029 is held by an unmerged branch). The owner may renumber.
- **OD-8 ADR adoption and implementation authority.** ADR 0031 stays Proposed;
  adoption, implementation (T002-T008), observation (T009) and release (T010) are
  separate owner decisions.

Remote GitHub issues, milestones and Project items are not created. The local
tracking source registers SPEC-060 and its tasks under the existing milestone #19;
publication follows the reviewed reconciliation workflow after merge.
