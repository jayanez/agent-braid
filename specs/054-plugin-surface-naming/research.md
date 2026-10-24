# SPEC-054 research record

All sources were accessed on 2026-10-24. Quotes are verbatim and at most 15 words.
Labels: **N** normative (specification MUST/SHOULD, documented requirement or
validation code); **C** convention or guidance; **O** observed product behavior
(source code, live repositories or the owner's installed `0.1.0-alpha.3`).
"Inferred" marks conclusions not stated by a source. Context7 resolved the MCP
specification and Claude Code documentation and then reached its monthly quota;
the remaining items come from the primary pages or source files listed.

## Problem observation

- **O** Claude Code with plugin `0.1.0-alpha.3` on macOS lists the plugin MCP
  prompt as `/plugin:agent-braid:agent-braid:agent-braid-analyze (MCP)` and the
  skill as `/agent-braid:agent-braid-analyze`; tools appear as
  `mcp__plugin_agent-braid_agent-braid__analyze`.
- **O** Repository: `agent_braid/tooling_mcp.py` `_PROMPT_TEXT` defines three
  prompts reused by `agent_braid/plugin_mcp.py`; `scripts/build_native_plugin.py`
  sets plugin, marketplace and server key to `agent-braid`; skill bodies call
  tools, never prompts.

## MCP specification (current version 2026-07-28)

| # | Source | Quote | Label | Use |
|---|---|---|---|---|
| M1 | https://modelcontextprotocol.io/specification/versioning | "The current protocol version is 2026-07-28." | N | Version baseline |
| M2 | https://modelcontextprotocol.io/specification/2026-07-28/server/tools | "Tool names SHOULD be between 1 and 128 characters in length (inclusive)." | N | Length |
| M3 | same | "Tool names SHOULD be considered case-sensitive." | N | Case |
| M4 | same | allowed characters A–Z, a–z, 0–9, `_`, `-`, `.` (paraphrase of SHOULD rule) | N | Charset |
| M5 | same | "Tool names SHOULD be unique within a server." | N | Uniqueness |
| M6 | same | clients "SHOULD implement a disambiguation strategy such as prefixing tool names" | N | Hosts namespace tools; servers need no prefix |
| M7 | same | serverInfo `name` "SHOULD NOT be relied upon for disambiguation" | N | Server name is not a namespace |
| M8 | https://modelcontextprotocol.io/seps/986-specify-format-for-tool-names.md | SEP-986 status Final; adopted text differs from abstract (no `/`) | N | Do not use `/` |
| M9 | https://modelcontextprotocol.io/specification/2026-07-28/server/prompts | "Prompts are designed to be user-controlled" | C | Prompts are user surfaces like skills |
| M10 | same | "For example, as slash commands" | C | Explains Claude Code display |
| M11 | same | no character or length rules for prompt names (verified absence) | N | — |
| M12 | https://modelcontextprotocol.io/specification/2026-07-28/server/resources | "Custom URI schemes MUST be in accordance with RFC3986" | N | Current schemes conform |
| M13 | same | use `https://` "only when the client is able to fetch and load the resource directly" | N | Custom scheme is correct here |
| M14 | https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/schema/2026-07-28/schema.ts | `name`: "Intended for programmatic or logical use" | C | Identifier vs display |
| M15 | same | `title`: "Intended for UI and end-user contexts — optimized to be human-readable" | C | Optional titles |
| M16 | https://static.modelcontextprotocol.io/schemas/2025-12-11/server.schema.json | registry `name` "Server name in reverse-DNS format." | N | Only for a future registry listing |

## Agent Skills open standard

| # | Source | Quote | Label | Use |
|---|---|---|---|---|
| S1 | https://agentskills.io/specification (no date shown) | "Must be 1-64 characters" | N | Skill length |
| S2 | same | "Must not contain consecutive hyphens (`--`)" | N | Charset |
| S3 | same | "Must match the parent directory name" | N | Directory equals name |
| S4 | same | no prefix or namespacing guidance (verified absence) | — | Prefix is a host/vendor choice |
| S5 | https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices | "Cannot contain reserved words: \"anthropic\", \"claude\"" | N | Satisfied |
| S6 | same | "Consider using gerund form (verb + -ing) for Skill names." | C | Not adopted: names mirror tool verbs |
| S7 | same | avoid "Inconsistent patterns within your skill collection" | C | One pattern for all six skills |

## Claude Code

| # | Source | Quote | Label | Use |
|---|---|---|---|---|
| A1 | https://code.claude.com/docs/en/plugins-reference | "Use kebab-case. Every component is namespaced under it." | N | Plugin id is the namespace |
| A2 | same | `displayName` "isn't used for namespacing or lookup." | N | Display separate |
| A3 | https://code.claude.com/docs/en/skills | plugin skills use `/plugin-name:skill-name`; frontmatter `name` sets the last segment | N | Prefix is redundant |
| A4 | same | "Prefer a skill for new work, since skills also support supporting files" | C | Compares skills with `commands/`, not MCP prompts |
| A5 | https://code.claude.com/docs/en/mcp | "Claude Code lists each MCP prompt as `/servername:promptname (MCP)`." | N | Root cause of the long name |
| A6 | same | server "registers under the scoped name `plugin:<plugin-name>:<server-name>`." | N | Plugin server namespace |
| A7 | same | tool ids `mcp__plugin_<plugin-name>_<server-name>__<tool-name>` (paraphrase) | N | Tool-id stability |
| A8 | https://code.claude.com/docs/en/permissions | `__` or trailing `_` in a server name makes allow rules ambiguous (paraphrase) | N | Server-key constraint |
| A9 | https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools | "Must match the regex `^[a-zA-Z0-9_-]{1,128}$`." | N | Tool charset; dots not portable |
| A10 | same | "Use meaningful namespacing in tool names" | C | Satisfied by host qualification |
| A11 | https://www.anthropic.com/engineering/writing-tools-for-agents (2025-09-11) | prefix versus suffix namespacing had "non-trivial effects" | C | Rename only with evaluation evidence |

No fetched page states a preference between MCP prompts and skills (verified absence).

## OpenAI Codex and OpenAI tool guidance

| # | Source | Quote | Label | Use |
|---|---|---|---|---|
| X1 | https://developers.openai.com/codex/plugins/build | "Use a stable plugin `name` in kebab-case." | C | Plugin id |
| X2 | same | "Use `interface.displayName` for the marketplace title" | C | Display |
| X3 | github.com/openai/codex `codex-rs/core-plugin-common/src/plugin_id.rs` (HEAD 970111f6) | names allow "ASCII letters, digits, `.`, `_`, and `-`" | N | Plugin id charset |
| X4 | github.com/openai/codex `codex-rs/ext/skills/src/loader/environment.rs` | plugin skills named `{namespace}:{base_name}` (code paraphrase) | O | Same doubling as Claude Code (inferred) |
| X5 | github.com/openai/codex `codex-rs/core-plugins/src/loader.rs` | "skipping duplicate plugin MCP server name" | O | Generic server key would collide |
| X6 | github.com/openai/codex `codex-mcp/src/mcp/mod.rs`, `tools.rs` | non-alphanumeric, non-underscore characters become `_` (code paraphrase) | O | Host-specific tool ids |
| X7 | https://github.com/openai/codex/issues/5059 (open; updated 2026-09-27) | "Currently Codex only supports MCP's tools" | O | MCP prompts invisible in Codex |
| X8 | github.com/openai/openai-python `function_definition.py` | function names a-z, A-Z, 0-9, underscores and dashes, max 64 (paraphrase) | N | 64-character floor |
| X9 | https://developers.openai.com/apps-sdk/plan/tools | "A stable, action-oriented identifier." | C | Verb tool names |
| X10 | https://developers.openai.com/api/docs/guides/function-calling | "Use namespaces to group related tools by domain" | C | Satisfied by server key |

## NVIDIA and Vercel

| # | Source | Quote | Label | Use |
|---|---|---|---|---|
| V1 | https://docs.nvidia.com/nemo/agent-toolkit/1.8/build-workflows/mcp-client.html | tool references `<function_group_name>.<tool_name>`; examples use `__` (paraphrase) | C | Hosts qualify tools |
| V2 | github.com/NVIDIA/NeMo-Agent-Toolkit `docs/source/extend/third-party-plugins.md` | "Use one provider token consistently across the repository, distribution, import package" | C | One brand token |
| V3 | same | token should be "short, lowercase, and stable" | C | `agent-braid` retained |
| V4 | https://ai-sdk.dev/docs/ai-sdk-core/tools-and-tool-calling | tool keys are names; no naming rule stated (verified absence) | C | — |
| V5 | https://vercel.com/docs/agent-resources/vercel-mcp/tools (updated 2026-09-15) | snake_case verb-noun names such as `list_deployments` (observed) | C | Common but not required |
| V6 | https://raw.githubusercontent.com/vercel-labs/agent-skills/main/AGENTS.md | "Skill directory: `kebab-case`" | C | Skill case |

No NVIDIA NIM or agent-blueprint tool-naming guidance was found in one search.

## Precedent

| # | Source | Observation | Label |
|---|---|---|---|
| P1 | github.com/anthropics/claude-plugins-official `.claude-plugin/marketplace.json` (HEAD 58267944) | In github, linear, context7, vercel, sentry, stripe, figma and notion, the MCP server key equals the plugin name | O |
| P2 | same | Vercel and commit-commands use unprefixed skills; Sentry and Figma repeat the brand (`/sentry:sentry-debug-issue`) | O |
| P3 | github.com/modelcontextprotocol/servers root `AGENTS.md` | a tool "removed or renamed" is a major change (paraphrase) | C |
| P4 | same repository | reference tools are mostly snake_case; the `everything` server mandates kebab-case | O |

## Conclusions and hypothesis check

The preliminary hypothesis had two parts. The evidence supports one and
contradicts the other.

1. *Stop publishing MCP prompts from the plugin server* — supported (A5, X7, M9):
   prompts duplicate skills in Claude Code and are invisible in Codex. Adopted
   as D1.
2. *Drop redundant prefixes* — supported for skills (A3, X4, S4, P2), adopted as
   D2. Rejected for the server key: shortening `agent-braid` to a generic key
   would collide in Codex, which does not scope plugin server keys (X5), and
   would invalidate Claude permission rules (A7, A8); precedent keeps the key
   equal to the plugin name (P1).
3. Tool names: kebab-case verbs satisfy MCP (M2–M5), Claude (A9) and OpenAI (X8)
   rules. snake_case is more common (P4, V5) but not required, and renaming
   would break the SPEC-047 enum and permission rules (P3). Kept (D4).
4. Resource schemes conform (M12, M13). Kept.
5. Portable prompts keep their v0.1 names (D3). Inferred: in Claude Code a
   portable server registered under key `agent-braid` still shows
   `/agent-braid:agent-braid-analyze (MCP)`; this is the motivation for the
   future target names.

## Limits

Host behavior is taken from documentation and source code at the cited revisions
and may change. The Codex skill display form is inferred from source, not
observed. No native observation of a candidate built under this policy exists;
T009 obtains it.
