# Release notes: Python package 0.1.0a2 (portable surface `agent-braid-tooling/v0.2`)

**Status: prepared, not released.** Nothing described here has been tagged,
built for distribution, uploaded or published. These notes are the text the
owner would review before a separate release decision (SPEC-060 T008 is
"prepare only"). The native plugin is not released and keeps `0.1.0-alpha.4`.

## What changes for a user of the portable server

The portable MCP server (`agent-braid tooling serve`, `python -m agent_braid.tooling_mcp`)
now publishes its three prompts under unprefixed names. Hosts that namespace MCP
prompts by server key (Claude Code) otherwise show the key twice, for example
`/agent-braid:agent-braid-analyze (MCP)`.

| New (canonical) name | Deprecated alias (same text) |
|---|---|
| `analyze` | `agent-braid-analyze` |
| `plan` | `agent-braid-plan` |
| `evidence` | `agent-braid-evidence` |

- `prompts/list` returns the three canonical names, then the three aliases. Each
  alias description starts with `[Deprecated alias of <canonical>; removed in
  agent-braid-tooling/v0.3]`.
- `prompts/get` returns the identical message text for a canonical name and its
  alias; the alias result description names the replacement.
- The `agent-braid://capabilities` resource reports `schemaVersion`
  `agent-braid-tooling/v0.2`, `envelopeSchemaVersion` `agent-braid-tooling/v0.1`,
  `prompts` (canonical names only) and `deprecatedPrompts` (name, `replacedBy`,
  `removedIn`).
- Unchanged: tool names and schemas, tool envelopes and provenance (still stamped
  `agent-braid-tooling/v0.1`), resources, evidence chunks, grants, telemetry
  (prompt requests are not counted), the legacy `agent-braid-*` skill install,
  and the host configuration written by the installer.
- `serverInfo.version`, the wheel metadata and `agent_braid.__version__` are
  `0.1.0a2`.

Codex lists no MCP prompts, so it is unaffected. The native plugin publishes no
prompts and its output is unchanged apart from the core `candidateVersion` string
in provenance, which follows the package version.

## Deprecation and removal contract

The aliases are a bounded exception to the SPEC-054 rule against duplicate
invocations (SPEC-060 `contracts/interface-delta.md` section 4):

- They are published by this release and by exactly one further portable-server
  release (a window of two releases, counted in releases, not days).
- They are removed only by a new contract, `agent-braid-tooling/v0.3`, and only
  after all of these hold: two releases carried them marked as deprecated; the
  release notes of both named the removal contract; the owner recorded a removal
  decision; a repository search finds no reference to the alias names outside
  frozen evidence, the alias table, its tests and the deprecation documentation;
  and the legacy skill install, host configuration and plugin do not reference
  them.
- Prompt use is not measured (SPEC-047 does not count prompt requests), so
  non-use cannot be a removal condition.
- If the second window release has not shipped 180 days after this one, the owner
  must record a decision to remove, extend or keep waiting. Without a decision the
  aliases stay and are flagged as an overdue deprecation.

Nothing in this release removes any name.

## Known caveat: server-key collision

Claude Code namespaces prompts by the MCP server key. Registering the portable
server under the key `agent-braid` next to the native plugin of the same name
makes two `/agent-braid:analyze` entries possible. SPEC-060 documents not
registering the portable server under that key beside the plugin; whether the two
entries are distinguishable in Claude Code is a pending native observation (T009)
and is not claimed here.

## Migration and rollback

- **Upgrade:** install the new package. An existing host configuration written by
  the earlier package needs no reinstall: the server key, command and arguments
  are the same, and `tooling install --operation update` plans no change. Clients
  that request the old prompt names keep working through the aliases.
- **Rollback:** reinstall the earlier package (`0.1.0a1`). The host configuration
  and receipt are untouched by both directions, the old names resolve again, and
  the unprefixed names are refused with `Unknown prompt`. There is no data
  migration.
- Both directions were exercised only against a synthetic earlier roster in owned
  temporary fixtures (`tests/test_spec060_release.py`); no published earlier wheel
  was installed.

## Verifying an installed package

`scripts/verify_installed_tooling.py` verifies contract v0.1 and package `0.1.0a1`
and is deliberately unchanged (its hash is pinned in frozen evidence).
`scripts/verify_installed_tooling_v2.py` verifies contract v0.2 and package
`0.1.0a2`. See `docs/tooling/INSTALLED_VERIFIERS.md`.

## Not done

No tag, no wheel or sdist for distribution, no upload, no GitHub release, no
plugin build or release, no native-host observation (T009), no owner release
decision. See `evidence/release-readiness.md` for the exact verification status.
