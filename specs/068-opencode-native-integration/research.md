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
provenance change additively. Accepted by the owner as D12 on 2026-11-03.

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

Observed by T002; see "T002 findings" below.

Rows to observe: dependency-free module load; transform order versus discovered
skills; override of a user `agent-braid` MCP entry; tool approval prompts for
plugin-registered MCP; Git install bytes, modes and size; `plugin update` and
`plugin remove` behaviour; command listing; behaviour with `--standalone`.

## T002 findings

Observed on 2026-11-03 by a track in disposable profiles with OpenCode 2.1.4 on
macOS arm64, using a local Git fixture (no network, no model call). Source of every
statement: [`evidence/opencode-host-matrix.json`](evidence/opencode-host-matrix.json)
(row ids in brackets). This section records observations; it changes no decision.
The one contradiction is flagged; all other items confirm or extend the findings
above.

| Item | Row | Result |
|---|---|---|
| R1 dependency-free module loads | 01 | Observed on 2.1.4. The default export must be an object with `id` and `setup` (or `effect`); a bare function or a missing `id` fails to load. Transforms may run more than once per load, unevenly and in varying order, so the entry must be idempotent. |
| R1 transform order vs discovered sources | 02 | See the contradiction below. |
| R2 Git install keeps modes, bytes, size (D3 gate) | 05 | Observed pass on a local bare repository (`git+file://`; the real `github:` transport and plugin-dist content are not exercised, 05b): executable bit, CRLF and binary bytes, and a 64 MiB file are preserved. Git attributes are honored (checkout, not archive), so the artifact keeps its root `* -text`. Symlinks are not installed. `github:` itself was not fetched (05b). |
| R2 update, remove, list | 06 | `remove` needs the exact source string and leaves the cache copy; `update` writes a new cache directory and keeps the old one; a running service needs `opencode reload`. |
| R2 `--standalone` | 08 | Private server, no background service; a one-shot `api` call returns before plugins load. |
| R3 override of a user `agent-braid` entry | 03 | `editor.set` silently overrides it, and `editor.get`/`list` show it first, so refusing is implementable. Compare semantic fields: the host normalizes entries. |
| R3 codemode default | 12 | Default `true` confirmed; the tool id is `agent-braid_<tool>` either way. Model-facing names need a model turn (12b, unobserved). |
| R3 approval prompts | 04 | Default rule sets contain `*` allow and no MCP-specific rule; a user permission rule can target the `<server>_<tool>` id. Prompts at call time are unobserved (04b). |
| R4 skill precedence | 02 | Partly confirmed: the discovered set beat the plugin-added skill, project `.opencode` beat five other discovered sources, home `.agents` beat home `.claude`, an explicit entry beat all. Project `.claude`/`.agents` and XDG positions are not in R4 and were not compared pairwise. |
| R5 commands | 07 | Flat names, exactly as registered. |
| R5 reload | 13 | A host reload exists (`opencode reload`, `experimental.mcp.connect/disconnect`, and `ctx.mcp.reload` by key name). R5 says no documented plugin API reloads; the operator-run reconnect and REQ-005 are unchanged. |
| R6 configuration files | 09, 11 | Six locations are read together; project files are taken at the Git root, not the working directory (global, project root, `.opencode`, each as `.json` then `.jsonc`); for a same-name key the `.opencode/opencode.jsonc` value won over the other five; array merging across files was NOT confirmed (one attempt: a project `plugins` entry did not load next to the global one), a tension with R6 left open; macOS global is `$XDG_CONFIG_HOME/opencode` or `~/.config/opencode`. `plugin add` writes the key `plugins` (singular `plugin` is also accepted). Linux unobserved (09b). |
| R6 comments and trailing commas | 09 | The host parses both; `plugin add` keeps comments. |
| R7 `_meta` session identifier | none | Not a T002 row; not observed (no model call). |
| D13 warning channel | 10 | None: no log/notice member; `console` reaches server stdout only; throwing disables the plugin. |

### Contradiction

**R4 / contract Skills (row 02, `contradicts-research`).** The research says the
transform refuses to replace an existing skill ID. In OpenCode 2.1.4 the skill
transform sees only built-in and plugin skills: `editor.get("analyze")` returns
nothing while a discovered `analyze` exists, and the discovered skill silently
replaces the plugin one. D2 and SC-004 stand (the user skill wins; `plugin doctor`
reports it), but the in-entry refusal is not a collision check. A later
`ctx.skill.list()` sees the resolved list. The coordinator should reword R4 and the
contract; no decision among D3, D7, D8, D13 or the dependency-free entry is
affected.
