# Agent Braid native plugin

Agent Braid inspects agent interactions, explains conflicts and carries bounded evidence forward. This local plugin includes its Python runtime, the existing tooling MCP implementation, five canonical product skills and a setup workflow. No Python, pip, uv or Node installation is required by the user. Git and a supported local Codex or Claude Code client remain prerequisites.

Install at user scope from the Agent Braid marketplace. Open setup (Claude Code: `/agent-braid:setup`; Codex: mention the `agent-braid:setup` skill), select repositories, inspect the private configuration/results destinations, apply the exact preview and reconnect MCP. Selection is per repository; global plugin availability is not unrestricted filesystem access. Analysis is the default. Execution requires explicit operator configuration and existing exact grants; setup never creates grants or starts provider sessions.

The host manages plugin updates and removal. Shared configuration and private results live outside its plugin cache and survive those operations. Use setup to unregister a workspace without deleting its source or evidence. Legacy manual installations can be migrated only using their matching ownership receipts.

This is a research-alpha engineering package. See provenance.json and package-inventory.json for the exact software/runtime identities and license inventory. Corresponding source is distributed alongside the marketplace under sources/. Byte verification is not native host acceptance or official directory approval. Official listing status must be checked independently.

Support: https://github.com/jayanez/agent-braid/issues

Software and executable materials: AGPL-3.0-only. Documentation and skill instructions: CC-BY-SA-4.0. Bundled Python and third-party packages retain their own included licenses. See LICENSE, LICENSES and provenance.json.

Invoke the product skills in Claude Code as `/agent-braid:analyze`, `/agent-braid:plan`, `/agent-braid:evidence`, `/agent-braid:execute`, `/agent-braid:recover` and `/agent-braid:setup`; in Codex mention the skill, for example `agent-braid:analyze`. Plugin skills are unprefixed because the host namespace already carries the plugin name. Skill text refers to tools by their bare MCP names (for example `analyze-work`); Claude Code keeps the hyphens in host tool ids and Codex rewrites them to underscores. Codex does not display MCP prompts and the plugin publishes none.
