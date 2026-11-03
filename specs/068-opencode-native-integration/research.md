# SPEC-068: Research

Engineering research only. Sources are the OpenCode 2.1.2 documentation (Context7
`/anomalyco/opencode/v2.1.2`, read on 2026-11-03), the OpenCode 2.1.4 CLI help
observed during `speckit-clarify`, and the repository at the branch base. Every
host fact below is documented, not observed; REQ-002 (T002) observes it in a
disposable profile, and a contradiction returns the affected decision to the owner.

## R1 — Plugin shape

**Finding (documented).** An OpenCode plugin is an ES module package:
`package.json` with `"type": "module"` and an `exports["."]` server entry. The entry
receives a context with transforms: `ctx.mcp.transform` (`editor.set/update/remove`),
`ctx.skill.transform` (`editor.add/get/update/remove/list`) and
`ctx.command.transform` (`editor.add` with an `execute` callback). Plugins manage
MCP servers only through transforms. Documented examples depend on the
`@opencode/plugin` npm package.

**Decision.** The OpenCode package is one plain JavaScript module (`opencode/index.js`,
no TypeScript build, no npm dependency) that only calls those three transforms.
All behaviour stays in the Python runtime behind `./launch`.

**Alternatives.** TypeScript with `@opencode/plugin`: rejected for this
specification because `plugin add` would resolve a floating npm dependency at
install time, outside the runtime lock and provenance. Kept as fallback if T002
shows that a dependency-free module does not load.

**Limit.** Whether a dependency-free module loads, and in which order plugin
transforms run relative to discovered sources, is a REQ-002 row.

## R2 — Git distribution

**Finding (documented).** `opencode plugin add` accepts npm specs and Git sources,
including `github:owner/repo#ref::path:subdir`. It writes only the global
configuration (observed in 2.1.4 help).

**Decision.** Install string: `github:jayanez/agent-braid#<tag>::path:plugins/agent-braid`
on the existing `plugin-dist` artifact (D3). The OpenCode entry lives in the same
plugin directory as the Codex and Claude manifests, so the bundled runtime is
shipped once.

**Alternatives.** A separate `plugins/agent-braid-opencode` directory: doubles the
runtime size and breaks the single-runtime provenance; rejected. npm: requires a
new owner decision (D3).

**Consequence for SC-010.** Adding files to the shared directory changes
`package-inventory.json` and `provenance.json`. "Byte-identical Codex/Claude
artifacts" is therefore measured on the files those hosts read (their manifests,
`mcp.json`, `.mcp.json`, `launch`, `skills/`, `runtime/`), while inventory and
provenance change additively. Recorded as OD-9 for owner confirmation.

**Limit.** Preservation of executable bits, bytes and size by the Git install is the
D3 gate in T002.

## R3 — MCP registration

**Finding (documented and clarified).** Local server entry: `type: "local"`,
`command` array, optional `environment`, `enabled`, `timeout`, `codemode`
(default `true`), `protocol` (`legacy` default). Tools appear as `<server>_<tool>`.

**Decision.** `editor.set("agent-braid", {type: "local", command: [<root>/launch,
"plugin", "serve", "--plugin-root", <root>], codemode: false, protocol: "legacy"})`
with `<root>` resolved from `import.meta.url`. D7, D8.

**Limit.** Whether the user's own `agent-braid` entry in `opencode.json(c)` is
overridden by the transform is a REQ-002 row; the contract forbids silent
replacement (see R5).

## R4 — Skills discovery and precedence

**Finding (documented).** Sources, lower to higher precedence: built-in;
`.claude/skills` (global, then ancestors to cwd); `.agents/skills`;
`~/.config/opencode/skills`; project `.opencode/skills`; explicit `skills` config
entries. The later source wins for the same ID, without a warning.

**Consequences.**

1. Legacy Claude Code and Codex installs (`agent-braid-analyze`, … in
   `~/.claude/skills` and `~/.agents/skills`, per `Selection.paths`) are also
   visible in OpenCode. IDs differ from the unprefixed plugin skills, so there
   is no collision, but the guidance appears twice. `plugin doctor` reports it as
   `duplicate-guidance`, not as a collision.
2. Any user or project skill named `analyze`, `plan`, `evidence`, `execute`,
   `recover` or `setup` in those locations is a collision (D2).

**Decision.** Collision detection is a read-only scan by `plugin doctor --host
opencode [--project <dir>]` over the documented locations, plus a refusal in the
transform to replace an existing skill ID (see contract). The scan is deterministic
Python and unit-testable with fixture trees.

**Limit.** Where plugin-added skills sit in that order is a REQ-002 row.

## R5 — Commands, setup and reconnection

**Finding (documented).** `ctx.command.transform` adds commands whose executor can
prompt the session. No documented plugin API reloads an MCP server; `opencode mcp`
exists as a CLI group.

**Decision.** Two commands: `agent-braid-setup` (prompts the session with the
packaged `setup` skill) and `agent-braid-reconnect` (prints the operator steps for
restarting the MCP server; it performs no reload). `reconnect-required` semantics
are unchanged (REQ-005).

**Alternative.** Automatic reload from the plugin on registry change: rejected by
REQ-005 and ADR 0024.

## R6 — Legacy profile configuration

**Finding (repository).** `tooling_install.py` edits host JSON with `_members`,
built on `json.JSONDecoder.raw_decode`: it preserves untouched bytes but rejects
comments and trailing commas. Host branches are binary (`codex` / `claude`), and
`asset_provenance` pins `hosts == ["codex", "claude"]`.

**Finding (documented).** OpenCode reads `opencode.json` and `opencode.jsonc` at
`~/.config/opencode/` and in the project (root and `.opencode/`); servers live under
the key `mcp`, not `mcpServers`; arrays from several files are combined.

**Decision.** Add a JSONC span scanner (comments, trailing commas, string-aware)
that returns the same member spans as `_members`, used only by the `opencode` host;
the Codex TOML and Claude JSON paths stay byte-for-byte as they are. Host dispatch
becomes a small per-host table instead of growing two-way conditionals. The
`hosts.json` asset manifest gains `opencode`; this is an additive change of the
`agent-braid-host-assets/v0.1` value, recorded in the contract.

**Alternatives.** A third-party JSONC library: adds a dependency to the frozen
route; rejected. Rewriting the file through a parser: loses comments; rejected
by SC-008.

## R7 — Session identifier

**Finding (documented).** OpenCode sends a per-call session identifier in request
`_meta`. `plugin_mcp.py` does not read `_meta`.

**Decision.** No code path reads `_meta`; a regression test sends a session
identifier and compares envelopes and stores byte for byte (REQ-009).

## Open items for T002

Rows to observe: dependency-free module load; transform order versus discovered
skills; override of a user `agent-braid` MCP entry; tool approval prompts for
plugin-registered MCP; Git install bytes, modes and size; `plugin update` and
`plugin remove` behaviour; command listing; behaviour with `--standalone`.
