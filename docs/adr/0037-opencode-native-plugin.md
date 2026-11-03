# ADR 0037: OpenCode native plugin

- **Status:** Proposed. Adoption authorizes no implementation, observation,
  release, tag or `plugin-dist` publication by itself.
- **Date:** 2026-11-03
- **Articles:** 0, 5, 6, 12–16, 19, 20, 23–25
- **Specification:** [SPEC-068](../../specs/068-opencode-native-integration/spec.md)

## Context

M4.5 delivered native Codex and Claude Code plugins (ADR 0024) with the naming of
ADR 0030 and the portable prompt names of ADR 0031. SPEC-039 deferred OpenCode.
OpenCode 2.1 loads ES module plugins that register MCP servers, skills and
commands through transforms, installs them from npm or Git, and discovers skills
from `.claude/skills`, `.agents/skills`, its own directories and explicit
configuration, with the later source winning silently for the same ID.

## Decision proposal

Adopt the [OpenCode surface contract](../../specs/068-opencode-native-integration/contracts/opencode-surface.md)
and the [legacy profile contract](../../specs/068-opencode-native-integration/contracts/opencode-legacy-profile.md):

1. One dependency-free ES module in the shared `plugin-dist` directory registers
   the unchanged `agent-braid-plugin/v0.2` server as `agent-braid` (`local`,
   `codemode: false`, `protocol: legacy`), the six SPEC-054 skills and two
   prefixed commands. User-global scope.
2. ADR 0030 naming applies to OpenCode although OpenCode does not namespace plugin
   skills; collisions are diagnosed by `plugin doctor --host opencode` and never
   resolved by replacing a user's skill or server.
3. No hooks, no event subscriptions, no automatic MCP reload; grants stay outside
   every host surface (ADR 0024).
4. The SPEC-042 legacy route stays frozen for Codex and Claude Code and gains an
   `opencode` profile with a comment-preserving JSONC editor; it is the only path
   for the portable `agent-braid-tooling/v0.2` server and its prompts in OpenCode.

## Alternatives and consequences

A TypeScript entry with `@opencode/plugin` resolves a floating npm dependency at
install time; it is kept only as fallback. A separate OpenCode plugin directory
duplicates the runtime. An npm channel needs a new decision. Consequences:
OpenCode users get the same tools and skills as Codex and Claude Code users;
`package-inventory.json` and `provenance.json` of the shared directory change
additively; host behaviour is unclaimed until SPEC-068 REQ-002 and REQ-012 record
it. Rollback is `opencode plugin remove`.

## Compatibility and review

Additive. `agent-braid-plugin/v0.2`, `agent-braid-tooling/v0.2`, SPEC-047,
SPEC-066, ADR 0030 naming and Codex/Claude packages and receipts are unchanged.
No constitutional amendment is proposed. Adoption, implementation, native
observation and release remain separate owner decisions.
