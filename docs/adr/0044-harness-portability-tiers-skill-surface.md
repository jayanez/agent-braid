# ADR 0044: Harness portability tiers and a skill-first harness surface

- **Status:** Accepted on 2026-11-23 by the founder in the SPEC-080 T001 review
  (answer "Aceptar (Recomendado)";
  [record](../../specs/080-harness-skill-every-host/evidence/t001-owner-review.md)).
  Proposed on 2026-11-22. Acceptance authorizes no code, release or execution.
- **Date:** 2026-11-22
- **Deciders:** Juan Antonio Yáñez García (founder)
- **Constitutional articles:** 0, 5, 13, 14, 15, 19, 20, 23, 24
- **Specification:** [SPEC-080](../../specs/080-harness-skill-every-host/spec.md)

## Context

The experimental `agent-braid harness` CLI is part of the plugin's shared `launch` for
Claude Code, Codex and OpenCode. Nothing an agent can discover exposes it: the plugin
ships seven fixed skills and no harness MCP tool. ADR 0043 (read-only harness MCP) was
rejected on 2026-11-22 under SPEC-050 D7. OpenCode is missing from the harness host
registry. The owner wants the harness usable wherever Agent Braid is installed, Pi and
ThinkRail included.

The field has settled on a portable layer plus a native layer per host:

- **Portable layer:** Agent Skills, MCP and AGENTS.md, all under the AAIF.
- **Native layer per host:**
  - Claude Code and Codex: plugin manifests (Codex also reads Claude-compatible
    manifests).
  - OpenCode: npm plugins.
  - Pi and ThinkRail: Pi packages.

Evaluation platforms (Langfuse, Phoenix, promptfoo, LangSmith, Braintrust) expose
themselves to coding agents through skills and/or MCP. Minimalist hosts (Pi) treat
MCP as a cost to every session's context window and prefer skills plus CLI.

## Decision

1. **Portability tiers.** Agent Braid sorts every agent-facing artifact into one of
   two tiers.
   - **Portable:** Agent Skills, using only the fields `name`, `description`,
     `compatibility` and `metadata`; the plugin MCP server; repository instruction
     files.
   - **Host-native:** hooks, plugin manifests, commands, output styles, eval suites
     and installer profiles.

   Every new capability names its tier. A portable artifact must work unchanged in
   each supported host. A host-native one names the host it targets.
2. **Skill-first harness surface.** The harness reaches agents through one portable,
   read-only `harness` skill. The skill invokes only read commands of the plugin's
   `launch harness`: `capabilities`, `registry-status`, `evaluation-summary`,
   `evidence`, `inspect`, `validate`, `status` and `compare`. It never invokes
   `prepare` or any launch, grant, promotion or registry write. It states that the
   harness is experimental and that `executionAuthorization` is false.
3. **No new MCP tools for the harness.** ADR 0043 stays rejected. A future MCP surface
   needs a new ADR backed by measured validity in every host.
4. **Host registry.** The harness host registry covers every host the plugin installs
   into. Each host carries its qualification state; unqualified hosts are offline
   only. This decision adds OpenCode now. Pi and ThinkRail follow SPEC-081.

## Alternatives considered

- **CLI only, documented.** Smallest change, but agents still cannot discover the
  harness. Rejected as the end state; it remains the fallback if the skill fails its
  validity check.
- **MCP tools (ADR 0043).** Rejected under D7 on 2026-11-22. It also adds
  per-session context cost and needs held-out validity in three hosts, in light of
  #1343.
- **Host-native harness integrations per host.** More capable per host, but every
  host needs its own maintenance and the result is not portable.

## Consequences

- **Positive:**
  - One artifact reaches Claude Code, Codex, OpenCode and Pi/ThinkRail.
  - Context cost is paid only when the skill is invoked.
  - No new trust boundary: the skill runs the existing CLI.
- **Negative:**
  - The skill depends on the host model following instructions and on shell access.
  - Skill counts in the build and the plugin tests change from 7 to 8.
- **Compatibility:** additive. Rollback is reinstalling the previous plugin release.
- **Security:** the skill has to make the read-only boundary explicit. A host model
  could still run `prepare` by hand, as it can today, so the CLI's own limits remain
  the guard.
- **Research:** engineering only. Whether host models invoke and use the skill
  correctly is a hypothesis that SPEC-080 tests.

## Validation

SPEC-080 plans:
- a held-out prompt set, run in each host, to check that the skill is invoked and
  stays inside its commands;
- CLI parity;
- skill-count and portable-field checks in the plugin tests.

None has run.

## References

- [Harnessing benchmark (2026-11)](../strategy/HARNESSING_BENCHMARK.md) and
  [radar 2026-11-22](../../research/radar/2026-11-22-harnessing.json)
- [Agent Skills](https://agentskills.io),
  [AAIF porting guide](https://aaif.io/blog/how-to-move-a-skill-from-one-coding-agent-to-another)
- [ADR 0043](0043-harness-mcp-readonly-surface.md)
