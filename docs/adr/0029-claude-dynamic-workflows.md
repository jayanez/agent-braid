# ADR 0029: Claude-only dynamic workflows component in the native plugin

- **Status:** Proposed — awaiting founder adoption. This file is the PR3 adoption package for SPEC-052 T033–T036; it records no decision, adoption or approval.
- **Date:** 2026-10-25 (regenerated from the merged SPEC-052 text; the adoption date is recorded by the founder, not here)
- **Deciders:** Juan Antonio Yáñez García (`@jayanez`), for any adoption.
- **Amends (if adopted):** [ADR 0024 native AI plugins](0024-native-ai-plugins.md), only for a Claude-only `workflows/` component.
- **Constitutional articles:** 0, 5, 12, 15, 19, 20, 24.

## Context

ADR 0024 defines the native plugin as portable and Claude manifests, "the unchanged five product skills", a setup skill, a pinned runtime and the plugin MCP, and states that no installation or session hooks or provider prompts ship. Claude Code dynamic workflows (introduced in v2.1.154) are plain-JS scripts run by a host runtime; plugins may ship `workflows/*.js` invoked as `/<plugin>:<name>`. Workflows can spawn worktree agents, but the documentation describes no automatic merge and no conflict detection across them. SPEC-052 proposes one read-only integration gate workflow, `braid-gate`. Shipping any executable-looking `.js` component changes the package's component set and the wording of ADR 0024, even if no hook, agent definition or provider prompt is added.

The decision was handled as a feature-local proposal (`specs/052-claude-workflow-gate/adr-proposal.md`) until adoption; this canonical file is created only for the founder's adoption decision. The number 0029 was confirmed free on 2026-10-25 (existing files: 0028 and 0030, none numbered 0029; two files share 0024). It is not reserved: if another ADR takes it first, renumber before adoption.

## Decision

Allow the native plugin to ship a Claude-only `workflows/` component containing exactly the workflows named by an adopted spec, initially `braid-gate` (SPEC-052). The component:

- is built by `scripts/build_native_plugin.py` from `integrations/agent-braid/plugin/workflows/` into `plugin/workflows/`, appears in the byte-stable package inventory and is verified by package verification;
- is ignored by Codex; the portable manifest and MCP configuration are unchanged;
- leaves the five product skills and the setup skill byte-identical; a workflow is not a skill;
- keeps the plugin's other prohibitions: no installation or session hooks, no mods, no plugin agent definitions, no provider prompts beyond the workflow's schema-bound agent prompts, no global host configuration.

ADR 0024 is otherwise unchanged. Its sentence "No installation/session hooks or provider prompts ship" stays in force except that the `braid-gate` agent prompts, bound by schema, are not provider prompts shipped as skills or hooks. The only edit to ADR 0024 is a link to this ADR.

### Explicit no-go list

The component must not, in this ADR or any workflow it covers: spawn agents in parallel or with worktree isolation; edit files, merge, push, create refs, branches or worktrees; install or declare hooks (including SubagentStop or WorktreeCreate), mods or `agent.spawn` rewrites; call grant, execute, recover or runtime-mode tools or start the owned runtime; accept, forward or generate grants; widen MCP limits (4 active calls, 32 operations, 1 MiB, 360 s) or the four-operation replay and runtime bound; make speed, safety or semantic-correctness claims; reach the network; run Git commands outside one fixed hardened template (system and global configuration, hooks, fsmonitor, external merge drivers, content filters and network disabled); run against a registration with runtime enabled or without a host permission allowlist that limits its agents to the read-only plugin tools and the fixed hardened Git prefix per named subcommand; or ship a fan-out orchestrator. Any additional workflow needs its own spec and an amendment.

### Authority boundaries

Host approval of a workflow run, Desktop "Always" approval and auto mode are host conveniences, not Agent Braid authority (ADR 0021). Prompts computed by a workflow script are not user authority. The gate result always carries `executionAuthorization: false`. The operator issues grants outside any workflow with the existing grant policy command, and execution stays in the owned runtime with serial publication to a private result repository, never to source refs (ADR 0014, 0019, 0020). Analysis and execution remain separate products (Article 20); Article 12 is respected because gating rules are computed by script from schema-bound results, not left to prompts.

## Alternatives considered

1. **Documentation-only recipe** (users paste the steps): lowest authority impact and a valid fallback, but unversioned, not tested with the package and easy to drift. It is the outcome on rejection and the fallback if the host cannot support the workflow (SPEC-052 REQ-013).
2. **SubagentStop or WorktreeCreate hooks**: contradicts the no-hooks wording, fires on every subagent, is not scoped to a user's intent and is hard to bound; WorktreeRemove is documented as not firing for workflow agents, so hooks are also incomplete. Rejected.
3. **`agent.spawn` mod that denies or rewrites workflow agents**: would alter other plugins' and users' workflows. Rejected as enforcement overreach.
4. **Shipping a fan-out orchestrator**: replaces the user's orchestration, would require the specs/039 coordination contract and invites speed claims contradicted by recorded NO-GO results. Rejected; a pre-flight partitioning proposal would be a separate future spec (SPEC-057) with its own ADR.
5. **Transcript-based hooks now**: depends on SPEC-053 and gate G0; deferred.

## Consequences

- Codex ignores `workflows/`; Claude Code with workflows disabled by organization policy cannot run the gate and falls back to the recipe documentation.
- The package inventory gains a file and its hash; `docs/tooling/PLUGIN_PACKAGE_README.md` and any "five skills" wording must distinguish skills from the workflow component.
- `scripts/validate_change.py` classifies paths by pattern with all-match semantics, so a `.js` file under `integrations/agent-braid/**` is already sensitive through the existing `ai-tooling` rule; an explicit rule for the workflow artifact type (SPEC-052 T018) makes the type and its boundary text visible.
- Host behaviors unconfirmed in the documentation (plugin MCP tools in workflow agents, plugin agents as `agentType`, nested call by plugin name) bound the design; a failed required behavior triggers the declared fallback or a no-go rather than a weaker gate.
- Host version drift is possible (the workflow API is recent); the package records the observed version and the gate refuses unknown shapes.
- Packaging adds one executable-looking file to the supply-chain review surface; its source is small, schema-bound and statically checked.
- Until adoption the builder excludes `workflows/` by default (explicit engineering-only opt-in); at adoption the default flips (SPEC-052 T036).
- Adoption does not accept a release, bump the version, publish to plugin-dist or widen any accepted capability; R1 (expected `0.1.0-alpha.4`) is a separate founder decision.

- Host verification HV-1..HV-5 and native runs T030/T031 are recorded under `specs/052-claude-workflow-gate/evidence/`. HV-5 showed that literal exact rules do not match commands with quoted arguments, so the spec amendment of 2026-10-25 uses wildcard tails over the fixed hardened prefix per named subcommand, one command per Bash call, and `/tmp` as an allowed directory for the scratch cleanup. The founder's acceptance of that trade-off for R1 on the MCP path is recorded separately in the SPEC-052 folder and is not adoption of this ADR.

## Validation

- `python -m scripts.validate_spec_kit` and the change-aware validators pass, with the authority delta reviewed in an authority impact review that SPEC-052 T035 creates at adoption.
- Package tests assert the inventory, the Claude-only scope, the byte-identical skills and the absence of hooks, mods and agent definitions.
- Host behaviors HV-1..HV-5 are observed per SPEC-052 before any compatibility claim; the decision is revisited if a required behavior fails or the host workflow API changes shape.
- Rejection keeps the documentation recipe only and closes R1 as no-go.

## References

- [SPEC-052 ADR proposal](../../specs/052-claude-workflow-gate/adr-proposal.md), [spec](../../specs/052-claude-workflow-gate/spec.md), [tasks](../../specs/052-claude-workflow-gate/tasks.md)
- The authority impact review and the architecture decision record are created at adoption by SPEC-052 T034 and T035; they do not exist yet.
- [Host evidence](../../specs/052-claude-workflow-gate/evidence/hv-disposition.md)
- ADR 0014, 0019, 0020, 0021, 0024 (native AI plugins)
