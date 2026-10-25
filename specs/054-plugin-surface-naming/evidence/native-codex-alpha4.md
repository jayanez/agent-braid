# SPEC-054 T009b: Codex observation of the alpha.4 candidate

Observed on 2026-10-25 on macOS 27.0.1 arm64 with codex-cli 0.164.0 (npm, native binary
sha256 `d8990e3e…499cf`) and Node v22.20.0. The candidate is the T009a build from `develop`
`268a8179f4b7fe68bb18722d6bb122c309e29aa0` (inventory sha256
`12c9ab896a9d223e17b0ee52764e87ca54f7fdf5686cad7ee56e4c779ef4d6c5`, provenance
`2a123a46…63e0a`, both unchanged). The reproduction script came from a fresh clone of
`develop` `15d4ca63fcfe7236298f699f47666eb89ce54aa2`. Machine-readable record:
[native-codex-alpha4.json](native-codex-alpha4.json). All state used a disposable `HOME`,
`CODEX_HOME` and `AGENT_BRAID_HOME`; no sign-in, credential, model or provider session was
started and nothing was pushed to plugin-dist or tagged. This does not tick T009.

## Results

| Step | Outcome |
| --- | --- |
| `codex plugin marketplace add` (local directory), `marketplace list --json` | Passed: name `agent-braid`, source type local |
| `codex plugin list --available --json` | Passed: version `0.1.0-alpha.4`, install policy AVAILABLE, auth policy ON_USE. No skills, MCP servers, prompts or displayName in this JSON |
| `codex plugin add agent-braid@agent-braid` | Passed: enabled, cached at `plugins/cache/agent-braid/agent-braid/0.1.0-alpha.4` |
| Installed skills | analyze, evidence, execute, plan, recover, setup; no `agent-braid-*` anywhere in skills, `.mcp.json`, `mcp.json`, `plugin.json` |
| MCP manifests | Server key `agent-braid`; `plugin.json` version `0.1.0-alpha.4`, displayName "Agent Braid" |
| Installed `launch plugin doctor` | Passed: package verified, 7818 files |
| `codex mcp list --json` | One server `agent-braid` (no plugin prefix), stdio, `launch plugin serve`, auth `unsupported`; `[]` after removal |
| `codex plugin remove`, then add again | Passed: files gone, list empty; reinstall verified |
| Registry and results across remove and reinstall | Identical (registry `b106f0d7…`, results `e8134843…`) |
| `reproduce_native_plugin.py` (develop, bundled Python, Codex only, native-mac) | **Passed**, 17 commands |

## Qualified skill name

Observed in JSON: the Codex app-server `skills/list` call made by the reproduction script
returned six enabled skills named `agent-braid:analyze`, `:evidence`, `:execute`, `:plan`,
`:recover` and `:setup`. The same run showed one MCP server `agent-braid` (serverInfo
`agent-braid-plugin`) with the five tools and no prompts capability. The interactive
invocation of the skill was not observed.

## Findings

- `codex plugin list --json` exposes only version and policies; skills come from `skills/list`.
- The script limits PATH to git, sh, uname and dirname, so the npm launcher `codex.js` failed
  (`env: node: No such file or directory`). The passing run used the native binary from the
  same npm package. The script was not modified.
- Two early mistakes were mine: a hand-made 755 state directory and an invalid hand-made
  registry were refused by doctor. State created by `plugin setup` passed.

## Not observed

Interactive Codex skill use, sign-in and any model session; Linux; a published Git ref
(the marketplace was a local directory). The release build must be redone from the then-current
`develop` commit before publication.
