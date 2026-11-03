# Contract: legacy `tooling install --host opencode` profile

Status: proposed with [ADR 0037](../../../docs/adr/0037-opencode-native-plugin.md).
Adds one host to the SPEC-042 receipt-owned lifecycle. The `codex` and `claude`
profiles, their receipts, previews and refusal diagnostics are unchanged byte for
byte. The route is the frozen fallback for platforms without a bundled runtime and
for source users (D4).

## Paths

| Scope | Configuration | Skills | Receipt |
|---|---|---|---|
| `user` | `$XDG_CONFIG_HOME/opencode/opencode.jsonc` if it exists, else `opencode.json` there, else create `opencode.json` (`XDG_CONFIG_HOME` defaults to `~/.config`) | `$XDG_CONFIG_HOME/opencode/skills/` | `$XDG_CONFIG_HOME/opencode/agent-braid-receipts/<name>.json` |
| `project` | `<source>/opencode.jsonc` if it exists, else `<source>/opencode.json`, else create `opencode.json` | `<source>/.opencode/skills/` | `<source>/.opencode/agent-braid-receipts/<name>.json` |

With `--destination <dir>`, the paths are `<dir>/opencode.json`, `<dir>/skills/`
and `<dir>/receipts/<name>.json`, as for the other hosts.

If both `opencode.json` and `opencode.jsonc` exist in the same scope, preview
refuses with `ambiguous_configuration` and names both paths.

## Owned entry

```jsonc
"mcp": {
  "<name>": {
    "type": "local",
    "command": ["<python>", "-m", "agent_braid", "tooling", "serve", ...],
    "codemode": false
  }
}
```

- `<name>` defaults to `agent-braid-tooling` for this host only (OD-10), so the
  legacy server never shares the native plugin's `agent-braid` key (SPEC-060 OD-5);
  the `codex` and `claude` default stays `agent-braid`. Tools appear as
  `agent-braid-tooling_<tool>` and prompts as `agent-braid-tooling:<prompt>`
  commands (D10).
- `protocol` is omitted (host default `legacy`, D8).
- Skills: the canonical prefixed skills (`agent-braid-analyze`, …), as for the
  other legacy hosts.

## Host permissions

The profile writes no `permission` configuration for `<name>_*` tools; the
host's approval rules apply, as recorded by T002.

## Editing rules

- A JSONC span scanner accepts `//` and `/* */` comments and trailing commas,
  respects strings, and returns member spans; only the owned member's span is
  written. All other bytes, including comments and formatting, are preserved.
- Creating `mcp` appends one member to the root object; removing the last owned
  entry leaves an empty `mcp` object only if the profile created `mcp`, recorded in
  the receipt.
- Writes are atomic with directory sync, under the existing scope lock, with the
  existing preview digest and rollback.

## Lifecycle

`preview`, `apply`, repeat (idempotent, no change), `update`, `uninstall` and
`doctor` behave as for the other hosts. `doctor` checks `opencode` on `PATH`,
the owned entry and owned skills.

## Refusals

| Code | Condition |
|---|---|
| `ambiguous_configuration` | `opencode.json` and `opencode.jsonc` both exist in the scope |
| `invalid_configuration` | JSONC does not parse, root is not an object, or `mcp` is not an object |
| `unowned_collision` | `mcp.<name>` or an owned skill exists without a matching receipt |
| `changed_digest` | The configuration or an owned skill changed since preview or since the receipt |
| existing lifecycle codes | Unchanged |

Refusal diagnostics use a new scope label `opencode_jsonc_server_entry`; existing
labels are unchanged.

## Asset manifest

`integrations/agent-braid/hosts.json` gains `"opencode"` in `hosts`; the schema
value `agent-braid-host-assets/v0.1` is unchanged because the field is a list of
supported hosts. `asset_provenance` accepts the new list.

## Negative controls

- Comment, foreign server or foreign key changed after apply or uninstall.
- Repeat apply produces a write.
- Unowned `mcp.<name>` or skill overwritten.
- Failed write leaves a partial file (no rollback).
- Codex or Claude preview, receipt or diagnostic bytes change.
