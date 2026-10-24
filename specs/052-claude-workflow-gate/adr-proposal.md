# ADR proposal: Claude-only workflows component in the native plugin

- **Status:** proposed; not adopted. Drafted 2026-10-23 for milestone M4.6 after founder direction to handle the decision as a feature-local proposal.
- **Decider:** Juan Antonio Yáñez García, for any future adoption.
- **Amends (if adopted):** [ADR 0024 native AI plugins](../../docs/adr/0024-native-ai-plugins.md).
- **Constitutional articles:** 0, 5, 12, 15, 19, 20, 24.
- **Canonical identity:** none. No ADR number is reserved; the canonical `docs/adr` file is created only at founder adoption (precedent: the SPEC-048 proposal).

## Context

ADR 0024 defines the native plugin as portable and Claude manifests, "the unchanged five product skills", a setup skill, a pinned runtime and the plugin MCP, and states that no installation or session hooks or provider prompts ship. Claude Code dynamic workflows (introduced in v2.1.154) are plain-JS scripts run by a host runtime; plugins may ship `workflows/*.js` invoked as `/<plugin>:<name>`. Workflows can spawn worktree agents, but the documentation describes no automatic merge and no conflict detection across them. SPEC-052 proposes one read-only integration gate workflow. Shipping any executable-looking `.js` component is a change to the package's component set and to the wording of ADR 0024, even if no hook, agent definition or provider prompt is added.

## Decision proposal

Allow the native plugin to ship a Claude-only `workflows/` component containing exactly the workflows named by an adopted spec, initially `braid-gate` (SPEC-052). The component:

- is built by `scripts/build_native_plugin.py` from `integrations/agent-braid/plugin/workflows/` into `plugin/workflows/`, appears in the byte-stable package inventory and is verified by package verification;
- is ignored by Codex; the portable manifest and MCP configuration are unchanged;
- leaves the five product skills and the setup skill byte-identical; a workflow is not a skill;
- keeps the plugin's other prohibitions: no installation or session hooks, no mods, no plugin agent definitions, no provider prompts beyond the workflow's schema-bound agent prompts, no global host configuration.

## Explicit no-go list

The component must not, in this ADR or any workflow it covers: spawn agents in parallel or with worktree isolation; edit files, merge, push, create refs, branches or worktrees; install or declare hooks (including SubagentStop or WorktreeCreate), mods or `agent.spawn` rewrites; call grant, execute, recover or runtime-mode tools or start the owned runtime; accept, forward or generate grants; widen MCP limits (4 active calls, 32 operations, 1 MiB, 360 s) or the four-operation replay and runtime bound; make speed, safety or semantic-correctness claims; reach the network; run Git commands outside one fixed hardened template (system and global configuration, hooks, fsmonitor, external merge drivers, content filters and network disabled); run against a registration with runtime enabled or without a host permission allowlist that limits its agents to the read-only plugin tools and fixed read-only Git commands; or ship a fan-out orchestrator. Any additional workflow needs its own spec and an amendment.

## Authority boundaries

Host approval of a workflow run, Desktop "Always" approval and auto mode are host conveniences, not Agent Braid authority (ADR 0021). Prompts computed by a workflow script are not user authority. The gate result always carries `executionAuthorization: false`. The operator issues grants outside any workflow with the existing grant policy command, and execution stays in the owned runtime with serial publication to a private result repository, never to source refs (ADR 0014, 0019, 0020). Analysis and execution remain separate products (Article 20); Article 12 is respected because gating rules are computed by script from schema-bound results, not left to prompts.

## Alternatives considered

1. **Documentation-only recipe** (users paste the steps): lowest authority impact and a valid fallback, but unversioned, not tested with the package and easy to drift; kept as the fallback if the host cannot support the workflow (SPEC-052 REQ-013).
2. **SubagentStop or WorktreeCreate hooks**: contradicts the no-hooks wording, fires on every subagent, is not scoped to a user's intent and is hard to bound; rejected. WorktreeRemove is documented as not firing for workflow agents, so hooks are also incomplete.
3. **`agent.spawn` mod that denies or rewrites workflow agents**: would alter other plugins' and users' workflows; rejected as enforcement overreach.
4. **Shipping a fan-out orchestrator**: replaces the user's orchestration, contradicts the ecosystem position, would require the specs/039 coordination contract and invites speed claims contradicted by recorded NO-GO results; rejected. A pre-flight partitioning proposal would be a separate future spec (SPEC-054) with its own ADR.
5. **Transcript-based hooks now**: depends on SPEC-053 and gate G0; deferred.

## Consequences

- Codex ignores `workflows/`; Claude Code with workflows disabled by organization policy cannot run the gate and falls back to the recipe documentation.
- The package inventory gains a file and its hash; `docs/tooling/PLUGIN_PACKAGE_README.md` and any "five skills" wording must distinguish skills from the workflow component.
- `scripts/validate_change.py` classifies paths by pattern and matching is all-match, so a `.js` file under `integrations/agent-braid/**` is already sensitive through the existing `ai-tooling` rule; an explicit rule for the workflow artifact type (T018) makes the type and its boundary text (host verification, release acceptance) visible rather than rescuing an unknown path.
- Host behaviors unconfirmed in the documentation (plugin MCP tools in workflow agents, plugin agents as `agentType`, nested call by plugin name) bound the design; a failed required behavior triggers the declared fallback or a no-go rather than a weaker gate.
- Host version drift is possible (the workflow API is recent); the package records the observed version and the gate refuses unknown shapes.
- Packaging increases the supply-chain review surface by one executable-looking file; its source is small, schema-bound and statically checked.

## Adoption procedure

At founder adoption only: create the canonical `docs/adr` file with the next available number at that time and amend or supersede the ADR 0024 wording through that file; re-snapshot affected current assurance records (specs 047, 048 and 051 and any other record whose authority inventory includes `docs/adr`) with fresh review and report changed hashes; produce `authority-impact-review.json` for the change (as SPEC-048 does); update `PLUGIN_PACKAGE_README`, the package inventory and `validate_change` rules; reconcile the milestone index; obtain independent review. Until then nothing in `docs/adr` changes, no number is reserved (two files already share 0024 and the highest is 0028, so the next free number is confirmed at adoption), and the plugin ships no workflow: the package builder excludes `workflows/` by default and includes it only with an explicit engineering-only opt-in until adoption, and the default flips at adoption.

Decisions recorded on 2026-10-23 as planning decisions, not adoption or approval (see the [SPEC-052 clarifications](spec.md#clarifications) and [program](program.md)): the unreleased packaging increment (PR2) may merge before adoption provided no version bump, plugin-dist publication or release occurs; R1 ships the commit-level gate alone, expected as `0.1.0-alpha.4`, independent of G0. What remains open and is not decided here: adoption, amendment or rejection of this proposal; the R1 number and any plugin-dist publication, each a separate founder decision.
