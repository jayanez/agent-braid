# Contract: OpenCode native surface

Status: proposed with [ADR 0037](../../../docs/adr/0037-opencode-native-plugin.md).
Additive. It changes no existing contract: `agent-braid-plugin/v0.2`, the
SPEC-054 naming policy, SPEC-047 telemetry and SPEC-066 System One are unchanged.

## Package

Location in the built marketplace: `plugins/agent-braid/` (shared with Codex and
Claude Code; the runtime is shipped once).

| File | Content |
|---|---|
| `package.json` | `{"name": "agent-braid", "version": <plugin version>, "type": "module", "private": true, "license": "AGPL-3.0-only", "exports": {".": "./opencode/index.js"}}`; no `dependencies` |
| `opencode/index.js` | ES module; default export is the plugin entry; generated at build from one tracked source |

Install string: `github:jayanez/agent-braid#<tag>::path:plugins/agent-braid`.
Scope: user-global only (D9).

## Entry behaviour

The entry performs exactly three registrations and nothing else: no network, no
file writes, no child processes other than the MCP server OpenCode starts, no
hooks, no event subscriptions.

Shape (T002 row 01): the default export is an object `{id, setup}`; a bare
function or an object without `id` fails to load. `setup` registers the three
transforms. The host may run the transforms more than once per load, unevenly and
in varying order, so every registration is idempotent and order independent. An
exception inside a transform disables the whole plugin (T002 row 10), so the entry
never throws to report a collision.

### MCP server

```js
editor.set("agent-braid", {
  type: "local",
  command: [`${root}/launch`, "plugin", "serve", "--plugin-root", root],
  codemode: false,
  protocol: "legacy",
})
```

- `root` is the plugin directory resolved from `import.meta.url`.
- The entry sets the server only when no `agent-braid` entry exists or the existing
  one is semantically equal on `type`, `command`, `codemode` and `protocol`; any
  other existing entry, including a disabled one or one with an environment, is left
  alone (D13). `editor.get("agent-braid")` returns the existing entry
  before `set` (T002 row 03), so the check is implementable. The host normalizes
  entries (for example adds `timeout`, reports `enabled:false` as `disabled:true`),
  so "exactly this value" is decided on semantic fields (`command[0]` and
  `--plugin-root`), never by whole-object equality. T002 row 10 found no
  write-free host warning channel (no log, notice or toast member on the server plugin
  context; `console` output reaches only the server process output), so the entry
  emits no host warning. The collision is reported by `plugin doctor --host
  opencode` as `server-collision` and by the setup command. The fix is the
  operator's: `plugin legacy` migration or an update of the foreign entry.
- Tool names are `agent-braid_<tool>`; tool set, schemas and results are those of
  `agent-braid-plugin/v0.2`, unchanged. The server publishes no prompts.

### Skills

Seven skills, IDs `analyze`, `plan`, `evidence`, `execute`, `recover`, `setup`, `telemetry-audit`, read
from the packaged `skills/<id>/SKILL.md` produced by the SPEC-054 build
substitution. No text is duplicated in JavaScript; the entry passes `{path, content}` with
the full `SKILL.md` content.

- The entry never removes or updates a skill it can see (a built-in or its own). It cannot see discovered skills: in the skill transform,
  `editor.get` returns null for user or project skills, and a discovered skill with
  the same ID silently wins over the plugin's skill; an explicit `skills`
  configuration entry wins over all discovered skills (T002 row 02). User and
  project collisions are therefore detected and reported by `plugin doctor --host
  opencode` (`collision`), the detector of record for REQ-004 and SC-004, not by
  the entry.
- Skills issue no grant and request no host permission beyond calling the MCP tools.

### Commands

| Command | Effect |
|---|---|
| `agent-braid-setup` | Prompts the current session with the packaged `setup` skill |
| `agent-braid-reconnect` | Prompts the session (`ctx.session.prompt`) with the operator steps (`opencode reload` or restart) for the `agent-braid` MCP server, because no write-free display channel exists (T002 row 10); performs no reload |

Command names keep the brand prefix because OpenCode commands share one flat
namespace with the user's own commands; names are listed exactly as registered,
with no plugin prefix (T002 row 07). The command `execute` and `session.prompt` shapes come from the OpenCode v2 documentation and stay unobserved until T010. Skills follow SPEC-054 (D2).

## Collision diagnosis

`agent-braid plugin doctor --host opencode [--project <dir>]` is read-only and
reports, for each of the six IDs, every definition found in the documented
discovery locations (`~/.claude/skills`, `~/.agents/skills`,
`~/.config/opencode/skills`, and for `--project` the `.claude/skills`,
`.agents/skills` and `.opencode/skills` directories from the directory up to the
filesystem root, not stopping at the Git root (T010 row 14), plus explicit
`skills` entries in the configuration files it can read; those configuration
files are still read only from the Git root down to the directory, since no
observation shows the host reading them above it).

| Finding | Meaning |
|---|---|
| `collision` | A non-plugin definition has one of the six IDs; output names the path that would win under the documented precedence |
| `duplicate-guidance` | Prefixed legacy skills (`agent-braid-*`) are also visible to OpenCode |
| `server-collision` | The configuration defines an `agent-braid` MCP entry that is not the plugin's |

Without `--host`, `plugin doctor` output is byte-identical to today.

## Reconnection

Registry changes keep `reconnectRequired: true` (SPEC-046 T016–T019). The plugin
never restarts or reloads the server; the operator does, following
`agent-braid-reconnect`.

## Session identifier

Request `_meta` (including the OpenCode session identifier) is never read, stored,
exported, logged or used for authorization. Envelopes and stores are byte-identical
with and without it.

## Host permissions

The entry writes no `permission` configuration for `agent-braid_*` tools; the
host's own approval rules and defaults apply. Their observed behaviour is a T002
row. Documentation may describe how an operator sets them, never as a grant.

## Authority

OpenCode permissions are host approvals, not Agent Braid grants. Execution still
requires an operator grant created outside every tool, skill, command and plugin
entry (ADR 0024).

## Negative controls

- Entry removes or updates a skill ID it can see, or replaces a foreign
  `agent-braid` server.
- `plugin doctor --host opencode` misses a user or project skill with one of the six
  IDs (the entry cannot detect it, T002 row 02).
- Entry throws from a transform (disables the whole plugin, T002 row 10).
- Entry performs network access, writes files or subscribes to events.
- `package.json` declares dependencies.
- Any stored artifact contains a `_meta` session identifier.
- Codex or Claude Code host-read files differ from a build without the OpenCode
  target (inventory and provenance differ only by added entries, D12).
