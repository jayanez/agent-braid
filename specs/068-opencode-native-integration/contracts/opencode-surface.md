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
- If an `agent-braid` server already exists and is not this exact value, the entry
  does not replace it (D13). The collision is reported by `plugin doctor --host
  opencode` as `server-collision`, by the setup command, and by a host-visible
  warning from the entry if T002 finds a documented channel that writes nothing
  (for example a log or notice API). The fix is the operator's: `plugin legacy`
  migration or an update of the foreign entry.
- Tool names are `agent-braid_<tool>`; tool set, schemas and results are those of
  `agent-braid-plugin/v0.2`, unchanged. The server publishes no prompts.

### Skills

Six skills, IDs `analyze`, `plan`, `evidence`, `execute`, `recover`, `setup`, read
from the packaged `skills/<id>/SKILL.md` produced by the SPEC-054 build
substitution. No text is duplicated in JavaScript; the entry passes `path` and the
file content.

- An existing skill with the same ID is never removed or updated by the entry.
- Skills issue no grant and request no host permission beyond calling the MCP tools.

### Commands

| Command | Effect |
|---|---|
| `agent-braid-setup` | Prompts the current session with the packaged `setup` skill |
| `agent-braid-reconnect` | Shows the operator steps to restart the `agent-braid` MCP server; performs no reload |

Command names keep the brand prefix because OpenCode commands share one flat
namespace with the user's own commands; skills follow SPEC-054 (D2).

## Collision diagnosis

`agent-braid plugin doctor --host opencode [--project <dir>]` is read-only and
reports, for each of the six IDs, every definition found in the documented
discovery locations (`~/.claude/skills`, `~/.agents/skills`,
`~/.config/opencode/skills`, and for `--project` the `.claude/skills`,
`.agents/skills` and `.opencode/skills` directories from the directory to the Git
root, plus explicit `skills` entries in the configuration files it can read).

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

- Entry replaces an existing skill ID or a foreign `agent-braid` server.
- Entry performs network access, writes files or subscribes to events.
- `package.json` declares dependencies.
- Any stored artifact contains a `_meta` session identifier.
- Codex or Claude Code host-read files differ from a build without the OpenCode
  target (inventory and provenance differ only by added entries, D12).
