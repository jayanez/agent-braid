# SPEC-054 implementation plan

## Technical context and scope

Python standard library plus the bundled pinned `mcp==2.3.0` SDK. Affected
code when implementation is authorized: `agent_braid/plugin_mcp.py` (prompt
handlers, capabilities, schema constant), `scripts/build_native_plugin.py`
(skill packaging, version), plugin package inventory and its tests, English
plugin documentation and the SPEC-046 interface contract. Unaffected:
`agent_braid/tooling_mcp.py` behavior, `agent_braid/tooling_install.py`,
`integrations/agent-braid/skills/` bytes, telemetry, registry and core.

## Constitution check before research

Article 14 requires inspectable evidence in interfaces; names are not evidence
and change none. Article 15 requires effect metadata without vendor coupling:
the policy keeps tool semantics and annotations and treats host qualification as
host-specific. Article 16 asks for conservative versioning: every removal or
rename is versioned. Articles 19–20 keep the work practical and keep analysis
separate from execution; Articles 23–24 forbid back-projecting accidental names
as semantics. GOVERNANCE requires a migration note and versioning impact for a
public API change. No MUST contradiction or SHOULD deviation is proposed.

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions: host behavior matches the cited
documentation and source revisions; plugin users invoke skills, not MCP prompts,
in their normal workflows; alpha users accept renamed invocations announced in
release notes.

Alternatives considered:

| Alternative | Outcome |
|---|---|
| Shorter or generic server key (`braid`, `core`) | Rejected: collides across Codex plugins (X5) and breaks Claude permission rules (A7, A8). |
| Keep prompts and rename them unprefixed | Rejected by D1: still duplicates skills in Claude Code; invisible in Codex. |
| Deprecated alias skills or prompts for one release | Rejected: would recreate the duplicate invocations this policy removes. |
| Rename tools to snake_case | Rejected by D4: changes SPEC-040, SPEC-047 and permission contracts without evidence of agent benefit (A11). |
| Rename canonical skill sources and add the prefix in legacy installs | Rejected: changes frozen SPEC-041/042 receipt paths and canonical bytes. |
| Rename plugin skills at build time | Adopted: canonical sources and legacy installs stay byte-identical. |

## Design and compatibility

1. **Plugin MCP v0.2.** `plugin_mcp.create_server` registers no prompt handlers,
   so the SDK does not advertise the prompts capability. `WorkspaceService.capabilities`
   omits `prompts`. `SCHEMA` becomes `agent-braid-plugin/v0.2`; delegated
   envelopes carry it. The portable server (`tooling_mcp`) keeps its prompts and
   `agent-braid-tooling/v0.1`.
2. **Display metadata (optional).** If the pinned SDK accepts them, the plugin
   server MAY add `title` to its tool definitions and `serverInfo`. Tool names,
   input/output schemas and annotations stay unchanged. Titles are applied in the
   plugin facade only, so the portable listing stays byte-compatible.
3. **Skill packaging.** The builder maps `agent-braid-analyze → analyze`,
   `agent-braid-plan → plan`, `agent-braid-evidence → evidence`,
   `agent-braid-execute → execute`, `agent-braid-recover → recover`; `setup` is
   unchanged. It writes `skills/<new>/SKILL.md` with the frontmatter `name`
   replaced and backtick-quoted sibling references rewritten by the same table.
   The package inventory records each canonical source SHA-256, the packaged
   SHA-256 and the substitution table. A build fails if any `agent-braid-<skill>`
   token remains in a packaged skill or a name violates the Agent Skills rules.
4. **Version.** Plugin `0.1.0-alpha.4`. Release notes list the removed prompts
   and each renamed skill invocation for both hosts.
5. **Migration and rollback.** Native update replaces package files; the
   `agent-braid-plugin-registry/v0.2` registry and results are untouched, so no
   registry migration is needed. Tool ids and permission rules are unchanged.
   Rollback reinstalls `0.1.0-alpha.3` from its tag; it reads the same registry.
   Users must reconnect MCP after update, as today.
6. **Telemetry.** Prompt traffic was never counted (SPEC-040 interface). Tool
   names and the `mcp` enum are unchanged, so the SPEC-047 v1 batch and store
   contracts are unaffected. This plan records that a future tool rename would
   require a telemetry contract version.
7. **Documentation.** Update `docs/tooling/NATIVE_PLUGINS.md`,
   `docs/tooling/PLUGIN_PACKAGE_README.md` and the SPEC-046 interface contract
   (plugin interface v0.2). Keep `docs/tooling/SKILLS.md` for the legacy names
   and note the plugin mapping.

## Validation strategy

Requirement → scenario → procedure → task mapping is in `assurance.json` and
[validation-plan.md](validation-plan.md). Negative controls: a prefixed packaged
skill, a renamed server key or tool, a prompt request on the plugin server and a
changed portable prompt listing must each fail. Run
`python3 scripts/validate_change.py --base develop --profile quick` during
implementation and `--profile pr` once on the stable candidate. Native host
observation (T009) is separate and never inferred from package checks.

## Constitution check after design

No effect, grant, execution path, analysis result or evidence boundary changes.
Removing prompts removes advisory text only; skills retain the same guidance.
No vendor-specific semantics enter the core. No amendment is proposed.

## Human review and unresolved decisions

Decisions needing owner approval before or during implementation:

1. Adopt [ADR 0030](../../docs/adr/0030-native-plugin-surface-naming.md)
   (currently Proposed). It amends ADR 0024's "unchanged five product skills"
   decision for plugin packaging only.
2. Authorize implementation of T002–T008 on a feature branch.
3. Whether to add tool and server `title` metadata in alpha.4 (MAY; default
   proposed: add for the plugin server only).
4. Whether alpha.4 also bundles other pending plugin fixes, such as the SPEC-046
   T016–T019 stale-registry reconnect tasks proposed in an open PR.
5. Release: building, tagging `agent-braid--v0.1.0-alpha.4` and publishing to
   `plugin-dist` remain separate owner decisions after T009.
6. Timing of a future `agent-braid-tooling/v0.2` portable contract with the
   unprefixed prompt names and an alias window (D3); not scheduled here.
7. GitHub tracking: issues, milestone membership and Project entries for
   SPEC-054 are drafted locally only and need explicit approval to create.
