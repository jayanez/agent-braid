# SPEC-054 T009a: Claude Code observation of the alpha.4 candidate

Observed on 2026-10-24 on macOS 27.0.1 arm64 with Claude Code 2.1.292, uv 0.11.26
and a CPython 3.12.13 build environment. Source: `develop`
`268a8179f4b7fe68bb18722d6bb122c309e29aa0`, clean clone, `sourceDirty` false. The
machine-readable record is [native-claude-alpha4.json](native-claude-alpha4.json).
All state used a disposable `HOME`, `CLAUDE_CONFIG_DIR` and `AGENT_BRAID_HOME`
with an empty environment; no login, model or provider session was started and
nothing was pushed, tagged remotely or published. This does not tick T009.

## Candidate

| Artifact | SHA-256 |
| --- | --- |
| `plugins/agent-braid/package-inventory.json` | `12c9ab896a9d223e17b0ee52764e87ca54f7fdf5686cad7ee56e4c779ef4d6c5` |
| `plugins/agent-braid/provenance.json` | `2a123a466cc48743655b15064e2203cfb6154b1bbecb17e93eca8ef0d8763e0a` |
| `sources/agent-braid-0.1.0-alpha.4-source.tar.gz` | `497936f1e004627c56c13e0d99ed0a7df5259750502dc6a9307223a9ed683dfd` |

7818 inventory entries (392,442,760 bytes); 7824 files and 415,485,999 bytes in the
distribution tree including the root README. `skillNaming` records policy SPEC-054
with packaged names analyze, plan, evidence, execute, recover and setup.

## Results

| Step | Outcome |
| --- | --- |
| Build without `--allow-dirty` | Passed, after adding pip to the uv venv (it has none) |
| `plugin doctor` on the package | Passed: verified, 7818 files |
| MCP over the SDK client (auto and legacy) | Passed: no prompts capability, `list_prompts` is Method not found, five tools, `agent-braid-plugin/v0.2` |
| `reproduce_native_plugin.py` as committed | **Failed**: line 168 still calls `list_prompts` |
| Same script with that call replaced by a capability check (outside the repository) | Passed, 19 commands |
| Isolated update alpha.3 to alpha.4 | Passed: "updated from 0.1.0-alpha.3 to 0.1.0-alpha.4" |
| Registry and results bytes across update and rollback | Identical (registry `c7d0ce25…`, results `e8134843…`) |
| Installed skills | analyze, evidence, execute, plan, recover, setup; no `agent-braid-*` directory |
| Components | `validate --strict` passed; 1 MCP server; `mcp list` shows `plugin:agent-braid:agent-braid` Connected |
| Doctor with `.in_use/<pid>` marker; `plugin-status` | Verified; status ok |
| Rollback to alpha.3 from the tag | Passed on the second attempt (see below) |
| Local distribution commit `b1fdb84f…`, tag object `64fbfb29…`, fresh clone | Byte-identical to the build; 7818 of 7818 entries match |

## Findings

- The reproduction script needs a source fix before it can gate alpha.4.
- Rollback needed `plugin marketplace remove` then re-add of the tag, because the
  profile already declared a different (directory) source; NATIVE_PLUGINS.md does not say so.
- After an update Claude Code adds `.orphaned_at` and `.mcp.json` to the old version
  cache; `doctor` on that orphaned directory reports an inventory change.
- With a directory marketplace `claude mcp list` runs the server from the folder, not the cache.

## Not observed

Interactive `/agent-braid:analyze` or any Claude Code session, Codex (not installed),
Linux, and an update from a published alpha.4 over Git. The release build must be redone
from the then-current `develop` commit before any publication.
