<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Claude Code workflows: the braid-gate recipe (SPEC-052)

**Status: unreleased, optional and Claude-only; observed on one host version.** The
`braid-gate` workflow is specified in [SPEC-052](../../specs/052-claude-workflow-gate/spec.md)
and is not part of any published plugin version. Until the ADR 0024 amendment in
the feature-local [ADR proposal](../../specs/052-claude-workflow-gate/adr-proposal.md)
is adopted, a build that includes it is an engineering artifact only. No Claude
Code version 2.1.292 (macOS arm64) was used for the host verification and the
native runs summarized in [Host verification status](#host-verification-status);
the evidence files are under
[`specs/052-claude-workflow-gate/evidence/`](../../specs/052-claude-workflow-gate/evidence/).
Nothing here is a release, an approval or a compatibility claim: those are
separate founder decisions.

## What this is

Claude Code dynamic workflows can run several agents in isolated worktrees. According
to the host documentation, the runtime applies no automatic merge and no conflict
detection to them. The gate is designed as a final analysis step you add after
your own worktree agents have committed their work. It is intended to leave the
repository untouched; its only write is a temporary scratch directory (see the
allowlist section). Agent Braid ships no fan-out: your
workflow creates the agents; the gate only observes their committed results. It
does not replace orchestration (see the [ecosystem note](../strategy/ECOSYSTEM.md)).

Codex is expected to ignore the component (intended, not observed; REQ-011
verification is pending). The five product skills and the `setup` skill are
unchanged ([skills](SKILLS.md), [installation](NATIVE_PLUGINS.md)).

## Before you run it

1. Install the plugin and register the repository with `/agent-braid:setup`
   ([setup](NATIVE_PLUGINS.md#setup-and-repository-suggestions)). Use an
   **analysis-only** registration (the default). Reconnect MCP after any registry
   change.
2. Make sure each worktree agent **commits** its work. Uncommitted work is not
   observed.
3. Choose the explicit `workspaceId` from `plugin workspaces`. The gate never
   defaults to a registered workspace and never falls back to another one.
4. Set the host permission allowlist below. Prompts are not a control.

## Arguments

```json
{
  "base": "main",
  "sources": ["agent/a", "agent/b"],
  "workspaceId": "WORKSPACE_ID"
}
```

Only these three fields are accepted. Unknown or missing fields end `refused`
before any agent is spawned. `sources` holds one commit, branch or tag name per
worktree agent (at least two distinct, at most 32); worktree paths are never
accepted. Names are resolved to full commit identifiers and pinned. Contract
drafts: [arguments and result schemas](../../specs/052-claude-workflow-gate/contracts/README.md).

## Ending your workflow with the gate

Two ways. The nested call was observed to resolve and run (HV-3, one level, 2.1.292);
the direct slash path was not observed:

- **Direct.** After your workflow finishes, invoke `/agent-braid:braid-gate` with
  the arguments above. How the host passes structured arguments on the slash path
  was not observed.
- **Nested.** Call the gate as the last step of your own workflow script.
  Illustrative sketch, not a tested example:

  ```js
  // Observed in HV-3 (2.1.292): the namespaced name resolves and runs one level deep.
  const gate = await workflow('agent-braid:braid-gate', {
    base: 'main',
    sources: ['agent/a', 'agent/b'],
    workspaceId: 'WORKSPACE_ID',
  })
  ```

  The host documents nesting as one level, so the gate itself calls no workflow.
  If nested resolution fails and it is the only integration path, there is no
  gate; this recipe remains the fallback.

### Splitting sign-off into separate workflows

Keep three steps separate so no approval of one stands in for another:

1. **Produce:** your workflow runs the worktree agents and commits their results.
2. **Gate:** a separate run of `braid-gate` over the pinned commits. It returns
   evidence and nothing else.
3. **Operator step:** you read the envelope, then integrate manually or grant and
   execute outside any workflow (next section).

## What the gate returns

One schema-validated envelope. It carries `executionAuthorization: false` always,
the pinned base and source identifiers, the operation count, per-phase status,
the analyzer's file-level interactions with coverage, a pairwise `git merge-tree`
baseline computed in a temporary object directory, the agreement between analyzer
and baseline, the number of agents used (at most four), stale-reference findings,
an `assurance` block (class `0-heuristic`) and explicit limits. For 2 to 4
operations it may add replay evidence and a prepared batch reference.

Statuses are `refused`, `busy`, `inconclusive`, `hazards-found`, `ok-analyzed` and
`ok-certified`. None of them is an approval or a guarantee. An `advisoryOrder` is
`null` unless dependencies are declared, and the gate declares none; the order
used for preparation is the input order of `sources`, not a recommendation. A
moved or deleted reference makes the run `inconclusive`.

## What the gate does not return

- No read hazards and no transcript or tool-call analysis.
- No hunk-level merge reasoning: resources are files, coarser than hunk merging.
  Deletions, renames, binaries and symlinks are unknown effects with partial
  coverage.
- No result for uncommitted work.
- No claim of faster integration, order independence, conflict freedom or semantic
  correctness. Parallel runtime speedup results are recorded NO-GO (SPEC-021 G4,
  SPEC-022, SPEC-038), and the gate makes no speed or agent-count claim.
- By design, no edits, merges, refs, branches, pushes, hooks, grants or
  execution, and no network access. Merge results are ephemeral and never
  applied. This is intended behavior enforced by the script's checks, the agent
  prompts and the host permission allowlist below; the script cannot observe the
  allowlist, and the allowlist behavior was observed only partly (HV-5).
- Release number, the ADR 0024 amendment and founder release acceptance are all
  pending, and the host outcomes of HV-1 to HV-5 are a separate task. Nothing here
  is a release decision. The workflow ships only in an engineering build made with
  the explicit `--include-workflows` option; the default build excludes it.

## Authority: grant and execute outside the workflow

Host approval of a workflow run and auto mode are **not** Agent Braid authority
([ADR 0021](../adr/0021-codex-claude-tooling-integration.md)), and the gate never
issues, requests or accepts a grant. If you choose to use the owned runtime, you do
that yourself, outside the workflow, after inspecting the envelope and the exact
digest: `grant-policy-run`, then `execute-policy-run` and `verify-git-run`, as in
the [owned fixture tutorial](../../examples/runtime/README.md) and the
[journey](JOURNEY.md). Recovery is `recover-policy-run`, documented there. The
alternative is to integrate manually. A prepared batch is a rehearsal, not a
decision.

## Host permission allowlist (REQ-016)

The plugin MCP lists model-callable `execute`, `recover`, `verify` and `status`
tools when any registration has runtime enabled. The gate therefore:

- **Refuses** with `runtime-enabled-workspace` when any registered workspace has
  runtime enabled or a grant store, so use an analysis-only registration.
- **Refuses** with `unsafe-tool-surface` when the validate agent reports any of
  those four tools as visible (an agent-reported check, not enforcement).
- **Requires** you to set a host permission allowlist built from exact command
  templates. A prefix rule (the hardened `env ... git -C "<root>" -c ...` prefix, or
  any rule matching `git`) is **insufficient**: it also matches `update-ref`,
  `config`, `checkout`, `branch` and every other subcommand. Permit only:
  - the plugin tools `workspaces`, `analyze-work`, `analyze` and `prepare`;
  - one rule per permitted Git subcommand: the full hardened prefix followed by the
    subcommand and a trailing `*` for its remaining arguments (host observation, HV-5:
    exact rules do not match commands with quoted arguments; a trailing wildcard
    matches). The subcommands are `version`, `rev-parse`, `rev-list`, `cat-file`,
    `merge-base`, `for-each-ref`, `count-objects`, `hash-object`, and for the
    baseline `init` and `merge-tree` with the scratch environment prefix. The
    wildcard allows any arguments of that subcommand under the fixed prefix; the
    prefix itself stays fixed and read-only commands stay the only ones named;
  - the scratch creation command `mktemp -d /tmp/braid-gate.*`;
  - the cleanup command `rm -rf -- /tmp/braid-gate.*`. The host also needs the
    scratch parent as an allowed directory (for example `--add-dir /tmp`, HV-5
    follow-up): without it the host refuses the removal, the gate reports
    `refused` or `failed`, and a scratch that was not removed is a stated limit that
    caps the run at `ok-analyzed`, never `ok-certified`. The agent checks that the
    path has the form `/tmp/braid-gate.` plus eight alphanumeric characters
    before removal, and the script accepts only a scratch path of that form.

Every agent runs each command as its own separate Bash call: no shell variables,
command substitution, loops or grouping (the host refuses brace expansion and
cannot match such commands with a rule). Pipes between two allowed commands are
matched per command.

This is a known deviation from "read-only Git": the baseline writes only that
temporary directory, never the repository, and `merge-tree --write-tree` writes
objects into the scratch alternate, not into the repository. If the host cannot
express the last two rules narrowly, the baseline phase is unavailable (a recorded
no-go), not unhardened. Whether the host matches at subcommand level is part of
HV-5: exact rules did not match commands with quoted arguments, a trailing
wildcard did, and the host refuses `rm` outside the working directory unless the
parent is an allowed directory (`--add-dir /tmp`). The founder accepted this
trade-off for the MCP path on 2026-10-25
([decision](../../specs/052-claude-workflow-gate/founder-decision-20261025.md)).

On the constrained-CLI fallback, used only if MCP tools are not visible to workflow
agents (HV-1), the rule set may in addition allow only these explicit launcher
subcommands: `analyze-git`, `plan-git`, `verify-git` and `plugin workspaces` with
no further arguments. It must never match the launcher binary as a whole,
`grant-policy-run`, `execute-policy-run`, `recover-policy-run` or any other
subcommand. If the host cannot express this, the fallback is a recorded no-go
(or refuses with `mcp-unavailable`). Whether the host can express any of these
rules was not observed (HV-5). The refusal rule runs after the validate agent has
already run, so for that one agent the allowlist is the only control.

## Host verification status

Recorded on Claude Code 2.1.292 (macOS arm64), engineering candidate loaded with
`--plugin-dir`, installed plugin and user configuration untouched. Workflows were
introduced in v2.1.154; the planning documentation described v2.1.309. These are
observations of this gate on one host version, not compatibility claims.

| Id | Behavior | Outcome | Evidence |
| --- | --- | --- | --- |
| HV-1 | Plugin MCP tools usable inside workflow agents; exact tool names visible | pass (analysis-only registration); `execute`, `recover`, `verify`, `status` not visible; runtime-enabled registration not run | `hv-1.json` |
| HV-2 | Plugin agent definitions as `agentType` (the gate ships none) | pass with the namespaced name only (`<plugin>:<agent>`) | `hv-2.json` |
| HV-3 | Plugin workflow called by name from nested `workflow()`; direct slash path | nested call pass (one level); slash path not observed | `hv-3.json` |
| HV-4 | Resume after interruption: which agents rerun, no duplicate MCP caller or prepare | partial: completed agents are reused, the stopped phase reruns, no duplicate `analyze-work` or `prepare`; a genuine stalled-agent restart and the admission lock not observed | `hv-4.json`, `native-gate-runs.json` |
| HV-5 | Per-run approval, auto-mode prompts and the permission allowlist above | partial: allowlist findings above; interactive prompts, accept-edits mode, per-agent separation and the launcher fallback rules not observed | `hv-5.json` |
| T030 | Native runs over a known-answer fixture matrix | ok-certified, ok-analyzed, hazards-found, refusals as designed; every baseline pair equals a direct `git merge-tree`; refs and objects unchanged | `native-gate-runs.json` |
| T031 | Auto mode; workflows disabled | auto mode: same envelope, no denials; workflows disabled by a session-only setting: the gate cannot start (unavailable) | `auto-and-disabled.json` |

The disposition of these outcomes is in
[`hv-disposition.md`](../../specs/052-claude-workflow-gate/evidence/hv-disposition.md).
Not observed anywhere: manual interactive prompts, a managed organization policy,
uncommitted work in a worktree and hostile inherited `GIT_*` variables in a native
session.

Workflows can be disabled by user setting or organization policy; then the gate
cannot start and the result is unavailable, not clean.

## Limits and degradation

The plugin admits one MCP caller at a time. The gate adopts the stricter of the
MCP limits (4 active calls, 32 operations, 1 MiB, 360 s) and never raises them.
Busy, unregistered or over-limit conditions end `busy`, `refused` or
`inconclusive` with the specific condition, without retry loops and with earlier
phase results preserved. A skipped replay (more than four operations) is never a
pass.
