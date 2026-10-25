# SPEC-052 host-verification disposition (T029)

**Date:** 2026-10-25. **Host:** Claude Code 2.1.292, macOS arm64. All observations use the engineering candidate loaded with `--plugin-dir`, a scratch analysis-only registry and no change to the installed plugin or user configuration. This is an agent-recorded summary of the evidence files; the founder's decision on R1 is separate. No task in `tasks.md` is ticked.

| Behavior | Outcome | Evidence | What it means for the gate |
|---|---|---|---|
| HV-1 plugin MCP tools in workflow agents | **pass** (analysis-only registration) | `hv-1.json` | MCP path is available; `execute`, `recover`, `verify`, `status` not visible. Runtime-enabled registration unobserved. |
| HV-2 plugin agent as `agentType` | **pass**, namespaced name only | `hv-2.json` | Bounds future design; the gate ships no plugin agent. R1 does not depend on it. |
| HV-3 nested call by plugin name | **pass** for resolution and a one-level refusal path | `hv-3.json` | `workflow('agent-braid:braid-gate', args)` works. A run with valid sources under a narrow allowlist is unobserved. |
| HV-4 resume and stalled-agent restart | **partial** | `hv-4.json` | Resume reuses completed agents and reruns the stopped one. Forced stall, duplicate MCP or prepare call and the admission-lock behaviour are unobserved. |
| HV-5 approval, modes and allowlist | **partial** | `hv-5.json` | Fail-safe under a strict allowlist, but literal rules do not match grouped or quoted-argument commands; wildcard tails do match. Interactive prompts, per-agent separation, launcher fallback rules, `mktemp` and `rm` rules unobserved. |

## Disposition

- **MCP path:** available (HV-1, HV-3). It is **not yet runnable under a narrow allowlist** (HV-5): before R1 the gate prompts must make every agent run each command ungrouped, and the recipe must either use wildcard tails over the fixed hardened prefix (wider than the REQ-016(b) text) or change the commands that carry quoted arguments. This needs a spec amendment and the founder's decision; it is recorded as an open finding, not accepted here.
- **Constrained-CLI fallback:** not needed while HV-1 passes. Whether the host can express the launcher-subcommand rules and `analyze-claude-transcripts` is unobserved (input to SPEC-053 REQ-009: no-go is not recorded, only unobserved).
- **Defect found by the HV-5 auto run and fixed separately:** the gate rejected the plugin's real `evidenceRefs` digest format (bare hex) and ended `inconclusive` on every real run. Fix and regression test are in the PR that fixes it; it is T030 groundwork, not a host-verification outcome.
- **Kill criterion:** not triggered. R1 on the MCP path remains open, blocked on the allowlist finding above and on a native run of the gate (T030) that has not yet completed.
- **Still open for R1:** the forced-stall run of the real gate (HV-4), the allowlist-compatible command set (HV-5) and T030/T031.
