# SPEC-060 T009 evidence: native observation of portable server 0.1.0a2

Observed on 2026-10-27 on macOS 27.0.1 arm64 with Claude Code 2.1.292, codex-cli 0.164.0
(npm, Node v22.20.0), uv 0.11.26, a CPython 3.12.13 build environment and a CPython 3.13.11
install environment. Source: `develop` `06d0313df1c4d836edb77059fe69203542c91e86`, clean
clone, no uncommitted change after the build. Machine-readable record:
[native-observation-0.1.0a2.json](native-observation-0.1.0a2.json).
All state used a disposable `HOME`, `CLAUDE_CONFIG_DIR` / `CODEX_HOME` and
`AGENT_BRAID_HOME` under a private directory outside any repository, with an emptied
credential environment. No login, no model or provider session was started and nothing was
pushed, tagged or published. This record is evidence only: it does not tick T009 (the owner
confirms scope first) and is not a release decision.

## Candidate

| Item | Value |
| --- | --- |
| Wheel | `agent_braid-0.1.0a2-py3-none-any.whl` |
| SHA-256 | `bd282e618078920b0577f0f68eb9bf95f8b5494f4b432ab2fc409a7d94632f16` |
| Build | `python -m build --wheel` in a 3.12 venv (isolated build; the only downloads were build tooling) |
| Install | disposable CPython 3.13.11 venv, `agent_braid-0.1.0a2-py3-none-any.whl[tooling]` (`mcp==2.3.0`) |
| Native plugin (collision case) | alpha.4 local directory marketplace from the SPEC-054 observation; inventory `12c9ab89…d6c5`, provenance `2a123a46…63e0a`, both identical to that record; not rebuilt |

## (a) SDK client against the installed portable server

Server `agent-braid-tooling` 0.1.0a2, started with `agent_braid.cli tooling serve`.
Capabilities: prompts, resources, tools.

- `list_prompts` order: `analyze`, `plan`, `evidence`, `agent-braid-analyze`,
  `agent-braid-plan`, `agent-braid-evidence`.
- The three `agent-braid-*` descriptions start with `[Deprecated alias of ...; removed in
  agent-braid-tooling/v0.3]`; the canonical ones do not.
- `get_prompt` returns text identical to the canonical prompt for each alias (157, 195 and
  182 characters). The alias `description` reads "Deprecated alias of `X`; removed in
  agent-braid-tooling/v0.3. ...". An unknown name returns "Unknown prompt".
- The `agent-braid://capabilities` resource reports `schemaVersion` `agent-braid-tooling/v0.2`,
  `envelopeSchemaVersion` `agent-braid-tooling/v0.1`, `prompts` `[analyze, plan, evidence]`
  and three `deprecatedPrompts` entries (`removedIn` v0.3, `replacedBy` the canonical name).
- Tools: `analyze-work`, `analyze`, `prepare`.

## (b) Claude Code 2.1.292

Method: `claude mcp add/list/get`, `claude plugin install/list/details`, and the `system`
`init` record of `claude -p --output-format stream-json --verbose "/cost"`. `/cost` is a local
command: the run reports `num_turns` 0, no API time and `apiKeySource` `none`, so no model
session occurred. The init record carries `slash_commands`, `mcp_servers`, `tools` and `skills`.

| State | `claude mcp list` | Agent Braid entries in the slash-command registry |
| --- | --- | --- |
| Portable alone, key `portable-braid` | `portable-braid` Connected | `mcp__portable-braid__analyze`, `__plan`, `__evidence`, `__agent-braid-analyze`, `__agent-braid-plan`, `__agent-braid-evidence` (6); tools `analyze-work`, `analyze`, `prepare`; no skills |
| Native plugin alone | `plugin:agent-braid:agent-braid` Connected after `plugin setup` (Failed before it) | `agent-braid:analyze`, `:evidence`, `:execute`, `:plan`, `:recover`, `:setup` (skills); no MCP prompt |
| Native plugin plus portable under `portable-braid` | both Connected | the 6 plugin skills and the 6 `mcp__portable-braid__*` prompts; 61 commands, no duplicate name |
| Native plugin plus portable under key `agent-braid` (collision) | `plugin:agent-braid:agent-braid` and `agent-braid` both Connected | the 6 plugin skills and the 6 `mcp__agent-braid__*` prompts; 61 commands, no duplicate name |

`claude plugin details agent-braid` lists six skills and one MCP server and no prompt. The
plugin server is named `plugin:agent-braid:agent-braid`, the user server `agent-braid`; Claude Code
accepted both and did not warn about the shared name.

## (c) Codex CLI 0.164.0

`codex mcp add portable-braid`, `mcp list --json` and `mcp get --json` show one stdio server;
`codex mcp` has only `list`, `get`, `add`, `remove`, `login`, `logout`, no prompt command. The
`app-server` request `mcpServerStatus/list` connected to the server and returned its `serverInfo`
(`agent-braid-tooling` 0.1.0a2), the three tools and the `agent-braid://capabilities` resource.
The entry has no prompts field (keys: `authStatus`, `httpOrigin`, `name`, `pluginId`,
`resourceTemplates`, `resources`, `runtimeStatus`, `serverCapabilities`, `serverInfo`,
`toolListMeta`, `tools`, `toolsError`), although `serverCapabilities` repeats the server's
`prompts` capability. The generated `ClientRequest` schema has 106 methods, five about MCP
(`config/mcpServer/reload`, `mcpServer/oauth/login`, `mcpServer/resource/read`,
`mcpServer/tool/call`, `mcpServerStatus/list`) and none named `prompt*`. Observed: Codex
0.164.0 lists no MCP prompts for this server.

## (d) Installed verifiers

Offline wheelhouse: the 28 wheels of `mcp-2.3.0-cp313-macos-arm64.lock.txt`, fetched with
`pip download --require-hashes`; the verifier checked roster and digests against the manifest.

| Verifier | Result |
| --- | --- |
| `scripts/verify_installed_tooling_v2.py` (sha256 `4799d7dc…fc3cca`), `--execute-installed`, CPython 3.13.11 | **passed**; 28 packages; SDK modes auto and legacy matched; receipt sha256 `b9438037…ff656`; no grant, no runtime dispatch, no provider session |
| `scripts/verify_installed_tooling.py` (sha256 `e88e0307…1ce431`, unchanged) | **blocked**, exit 2, reason "candidate distribution identity mismatch" (the pinned version is 0.1.0a1) |

## Findings

- The v0.2 roster, deprecation marking and capability data are observed as specified, through
  the SDK client, Claude Code's own loader and Codex's app-server.
- Claude Code registers MCP prompts internally as `mcp__<key>__<name>`. Under the key
  `agent-braid` the registry therefore holds `mcp__agent-braid__analyze` beside the skill
  `agent-braid:analyze`: distinct strings, no duplicate. How the interactive slash menu prints
  them (INSTALL.md says `/agent-braid:analyze (MCP)` for the unprefixed prompt) was not
  observed, so the collision warning in `docs/tooling/INSTALL.md` is neither confirmed nor
  refuted here. Aliases appear in the registry with their `agent-braid-` names.
- The native plugin server is reported `failed` in the `-p` init record in every state, while
  `claude mcp list` reports it Connected; the debug log shows no connection attempt for it in
  print mode. The cause was not determined and nothing here depends on it.
- The native plugin refused to start until its `AGENT_BRAID_HOME` was mode 700 and `plugin
  setup` had registered a fixture repository (as in the SPEC-054 record).
- The plugin build bundles core 0.1.0a1 and publishes no prompts; unchanged by 0.1.0a2.

## Limits (not observed)

- Interactive slash-menu use (typing `/`, selecting or running a prompt) and any model
  session; only the registry in the init record and CLI listings were read.
- Claude Code or Codex sign-in; Codex plugin install for this candidate.
- Linux.
- A published or tagged package: the wheel was built locally and never uploaded.
- The native plugin was reused from the alpha.4 observation, not rebuilt.
- Observation by the owner in a real profile, which remains the owner's call for T009.
