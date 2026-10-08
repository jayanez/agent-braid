# AI tooling research and decision register

**Retrieved:** 2026-10-08. **Claim level:** source-informed engineering proposal.
The owner selected Codex and Claude Code; no comparative vendor ranking or
runtime compatibility is established by this research.

Context7 resolved official Codex, Claude and MCP SDK documentation before API
queries. Agent Reach/Exa supplied discovery. Primary sources guide selection;
documentation and search snippets do not replace runtime observations.

| Source | Observed signal | Proposed response | Remaining verification |
|---|---|---|---|
| [Python SDK v2.3.0 release](https://github.com/modelcontextprotocol/python-sdk/releases/tag/v2.3.0) | Stable release October 2, including legacy fixes | Pin optional SDK extra | Installed behavior and dependency/license inventory |
| [Official SDK docs](https://py.sdk.modelcontextprotocol.io/) | stdio, typed tools, resources and prompts | Shared adapter over existing runtime | Exact pinned API and negative controls |
| [MCP 2026-07-28 release](https://blog.modelcontextprotocol.io/posts/2026-07-28/) | Discovery/per-request protocol evolution | Test new discovery and 2025-11-25 lifecycle | Actual host negotiation, no extensions assumed |
| [Agent Skills specification](https://agentskills.io/specification) | Portable SKILL.md format | Canonical five-skill bundle | Exact host discovery and instruction outcomes |
| [Agent Plugins](https://agent-plugins.org/) | Shared packaging direction, host differences | Minimal versioned wrappers | Valid manifest alone is not native support |
| [Codex stdio config source](https://github.com/openai/codex/blob/main/codex-rs/config/src/mcp_types.rs) | Local command/args/environment | Isolated executable, root-bound servers | Selected build, scope and config preservation |
| [Codex plugin source](https://github.com/openai/codex/blob/main/codex-rs/exec-server-protocol/src/protocol.rs) | Multiple manifest conventions | Shared bundle, tested metadata | Do not infer all Claude plugin features |
| [Codex skills docs](https://developers.openai.com/codex/skills) | Workflow guidance linked to tools | Portable skills plus live MCP evidence | Exact locations/dependencies for selected build |
| [Claude MCP docs](https://code.claude.com/docs/en/mcp) | Local/project/user scopes | Explicit scoped host adapter | Actual stdio discovery and interactive trust |
| [Claude skills docs](https://code.claude.com/docs/en/skills) | Host skill/plugin conventions | Minimal Claude wrapper | Bundle discovery, namespaces and unavailable features |

## Local design decision

Use program.md, capability-matrix.md and ADR 0021 as the shared portfolio. SPEC-040 supplies the contract, 041 guidance, 042 lifecycle, 043 presentation and 044 independent bounded evaluation. Keep the five future routes documentation-only.

## Why and alternatives

A shared typed core reduces duplicated host semantics; CLI remains the reproducible baseline. Skills-only wrappers lose standardized discovery; host-only implementations risk divergence. Hosted services and embedded UI expand the surface and are future routes.

### Decision rationale

Use the official SDK optionally and preserve core/legacy paths; extending the
handwritten server avoids dependencies but increases protocol maintenance.
Instructions guide workflows while the runtime enforces grants/effects.
No hooks, automatic permission changes or autonomous helpers are needed.
Reusable isolated user installation and explicit project scope both retain
per-server trusted roots. Host documentation cannot authorize editing real config.
Offline exports precede embedded MCP Apps, which need UI/security contracts.
CLI/MCP-only/integrated comparison records complete costs with no assumed speedup.

### Existing work

SPEC-021 has historical bounded stdio/host evidence. Reuse its contracts but do
not relabel that evidence as the new SDK, bundle or host version. SPEC-027
refinement remains relevant. SPEC-023 trace importing and expanded runtime
effects remain outside this first surface.

## Evidence needed

A coherent discoverable integration may make existing bounded capabilities useful to these hosts; user recognition and utility are not assumed.

Verify each proposed feature under the named validation procedures. Vendor documentation is source material, not host runtime evidence. Source rights, numeric budgets, exact versions and candidate review precede registered capture.

Before implementation/capture, adopt the exact experimental API/ADR; select and
freeze host/model/build identities; verify lifecycle ownership and dependency
provenance; register source rights and numeric provider/token/time/resource caps.
Obtain separate actual-host, clean-room, annotation and founder decisions.
Missing support or negative utility may narrow or reject adoption.

Recheck API/configuration details at implementation and after upgrades. This
dated register records a proposal; new versions need migration/control evidence.
