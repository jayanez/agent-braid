# SPEC-060: result of the interactive slash menu observation

Status: owner-provided evidence, recorded 2026-10-27. This record is evidence only. It does
not tick any task, does not authorize a release, a tag or a publication, and does not change
the frozen SPEC-060 files. It answers part of the question posed in
[interactive-slash-guide.md](interactive-slash-guide.md) and part C of
[native-observation-0.1.0a2-addendum.md](native-observation-0.1.0a2-addendum.md); those two
frozen files are not edited and still read as pending, so read them together with this record.

## Source

Three owner-provided screenshots of the interactive Claude Code slash menu, taken on
2026-10-27. The Claude Code version and operating system were not recorded by the owner. An
auto mode notice is visible in the captures.

| File | SHA-256 | Content |
| --- | --- | --- |
| `1.png` | `61b329330afb8631ec4079b7f3061c60846329b0a7452bdc01e74460a01b9917` | Native plugin `0.1.0-alpha.4` only: exactly six entries |
| `2.webp` | `57f8534174e599bb8ede1c4ac57e3a5a61e927286363bfa1f4c146782bdd3beb` | Case A, filter `/braid` |
| `3.webp` | `ad17aadfe49cc03beb2a09938e5fe990726b8f101b3c1a140d205286728c4ba0` | Case A, filter `/evidence` |
| `4.png` | `e9fcd10f5ef065050df2f7b36f813732b1bb9895abafa0760f6974b6cbf3c691` | Case B, filter `/` (generic list; no agent-braid entry among the first five) |
| `5.png`, `6.png` | `7074be915970a6165f61976d1c91487125c70f2f098ee5cf25b6590c93e96a18` | Case B, filter `/braid` (identical duplicate captures) |
| `7.png` | `8b7b6d747c02cba75c37729dcff2910a11f2426c9ed45738cb6d9f61d7346f18` | Case B, filter `/evidence` |

The screenshots themselves are not stored in the repository; the hashes identify the files
the owner holds.

## Observed

Plugin only (`1.png`): the menu showed exactly six entries, the plugin's unprefixed skills
(SPEC-054): `agent-braid:analyze`, `agent-braid:evidence`, `agent-braid:execute`,
`agent-braid:plan`, `agent-braid:recover`, `agent-braid:setup`. No MCP prompt entry from the
plugin appeared.

Case A (`2.webp`, `3.webp`): the portable server registered under the key `agent-braid`
beside the plugin `0.1.0-alpha.4`.

1. The portable prompts appear as `/agent-braid:analyze (MCP)`, `/agent-braid:plan (MCP)` and
   `/agent-braid:evidence (MCP)`. The deprecated aliases appear as
   `/agent-braid:agent-braid-analyze (MCP)`, `/agent-braid:agent-braid-plan (MCP)` and
   `/agent-braid:agent-braid-evidence (MCP)`.
2. The alias descriptions are visible in the menu and start with
   "[Deprecated alias of `analyze`; removed in agent-braid-tooling/v0.3]" (the same pattern
   for `plan` and `evidence`). The canonical prompt descriptions carry no such marker.
3. The six plugin skills appear on separate lines prefixed with `* ` and labelled
   `(agent-braid)` (the plugin source label), for example `* /agent-braid:evidence (evidence)
   - (agent-braid) Use when...`. A skill and a prompt therefore share the slash text
   `/agent-braid:analyze` (and `plan`, `evidence`) but are two distinct entries, told apart by
   the `(MCP)` suffix, the `*` marker and the description. No conflict warning was visible and
   no entry was hidden.
4. With the filter `braid`, the highlighted first entry is the deprecated alias
   `/agent-braid:agent-braid-analyze (MCP)`. With the filter `/evidence`, the highlighted first
   entry is the plugin skill.

Case B (`4.png` to `7.png`): the portable server registered under the key `portable-braid`
beside the plugin `0.1.0-alpha.4`. `claude mcp list` showed both
`plugin:agent-braid:agent-braid` and `portable-braid` as Connected.

1. With the filter `/braid`, the first (highlighted) entry is
   `/portable-braid:agent-braid-analyze (MCP)`, followed by
   `/portable-braid:agent-braid-plan (MCP)`; both descriptions start with
   "[Deprecated alias of `analyze`; removed in agent-braid-tooling/v0.3]" and the same text
   for `plan`.
2. With the filter `/evidence`, the first (highlighted) entry is the plugin skill
   `* /agent-braid:evidence (evidence) - (agent-braid) Use when explaining...`, then
   `/portable-braid:evidence (MCP)` (canonical, no deprecation marker) and
   `/portable-braid:agent-braid-evidence (MCP)` (with the deprecation marker).
3. The portable prompts are namespaced by the user-chosen key (`/portable-braid:<name> (MCP)`)
   and do not share slash text with the plugin skills (`/agent-braid:<skill>`). The aliases
   are not filtered out of the menu, and their deprecation text is visible.

## Not observed

- The portable server alone (no plugin).
- Whether any entry was executed or Intro was pressed: not recorded.
- The Claude Code version and operating system of the captures.

## Conclusion and effect on documentation

The slash-name collision exists only when the portable server uses the key `agent-braid`
beside the plugin. Then the skill and the prompt share the same slash text and are
disambiguated only by the `(MCP)` suffix, the `*` marker and the description; there is no
conflict warning and no entry is hidden, so nothing breaks. Under a distinct key (for example
`portable-braid`) the slash texts differ. The advice in `docs/tooling/INSTALL.md` and
`docs/tooling/NATIVE_PLUGINS.md` is therefore kept as a precaution and reworded: prefer a
distinct key. The deprecation marking of the aliases is confirmed visible in the real menu in
both cases. Part C of the addendum remains open only for the solo-portable case.
