> Unpublished local draft payloads derived from specs/052-claude-workflow-gate/spec.md, tasks.md and assurance.json at the planning candidate. Source links target the eventual integrated develop branch and do not claim the files are already there. No external tracking operation is authorized by this file.

# Unpublished issue drafts

Milestone: **M4.6 — Claude Code dynamic workflows** (not yet created; number unassigned). Publication: forbidden in this delivery. No remote issue, milestone, description or Project write, audit/apply or merge was performed. Labels: `spec` for the parent, `task` for each task. Project Review pending: SPEC-052 (draft flag only). Records: 1 spec parent and 47 task issues, all proposed open.

Task issues keep the "Blocked by" and "Founder:" markers of tasks.md; a blocked or founder task is tracking state only and authorizes nothing.

## SPEC-052

Proposed state: open. Parent: none. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `spec`. Project Review: pending (draft flag).

<!-- agent-braid-spec-id: SPEC-052 -->

Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)

Requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014, REQ-015, REQ-016.

Issue state is a bounded tracking record, not a scientific or founder approval.

## SPEC-052/T001

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T001 -->

## Task

Write and review the argument and result contracts. Dependencies: spec.md clarifications of 2026-10-23. Target files: contracts/braid-gate-args.schema.json; contracts/braid-gate-result.schema.json; contracts/README.md. Acceptance: Both schemas are JSON Schema draft 2020-12, reject unknown fields, fix `executionAuthorization` to the constant false, require the canonical limits and the Article 13 `assurance` block, and map each field to a requirement. Verification: planned schema-validity and sample-envelope tests in T007. Planned evidence: the contracts directory bytes bound by the authority snapshot; obtained: none (drafted, not reviewed).

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-001 SC-001 REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T002

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T002 -->

## Task

Founder: accept, amend or reject this planning packet (plan, research, quickstart, validation plan, tasks, contracts, ADR proposal) for PR1. Dependencies: T001; independent read-only analysis (speckit-analyze) of the packet. Target files: none (decision recorded in the PR). Acceptance: A recorded disposition; acceptance of the packet is not ADR adoption, implementation approval or release approval. Verification: not applicable (human decision). Planned evidence: the PR review record; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-009 SC-009 REQ-013 SC-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T003

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T003 -->

## Task

Refresh the current authority snapshot of `assurance.json` after the planning files exist and run the structural validators. Dependencies: T001. Target files: assurance.json. Acceptance: `python3 -m scripts.validate_spec_kit snapshot specs/052-claude-workflow-gate` and `python3 -m scripts.validate_spec_kit` pass; `human_review` stays pending; `obtained_evidence` stays empty; changed authority hashes are reported, never silently refreshed. Verification: the two commands. Planned evidence: command transcripts in the PR; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T004

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T004 -->

## Task

Write the failing static test of the workflow source. Dependencies: T001. Target files: tests/test_claude_workflow_gate.py. Acceptance: A Node-free structural check over `integrations/agent-braid/plugin/workflows/braid-gate.js` asserts: an SPDX `AGPL-3.0-only` header; `export const meta` is the first statement and a pure literal with `name` braid-gate, a description and `phases` whose titles equal the `phase()` titles; no `import()`; no `Date.now`, `Math.random` or argless `new Date`; no `isolation` option; no `parallel(` or `pipeline(` and no loop spawning agents over `sources`; at most four `agent(` call sites, each with a `schema`; no `workflow(` call; no `agentType`; no `model` or `effort` option on any `agent(` call (agents inherit the session model); no call-site or prompt text naming grant, execute, recover, status, verify or runtime-mode tools; agent prompts built only from validated identifiers and constants. Include mutation controls that must fail the check (add a parallel wrapper, add isolation, add a fifth agent, add a `model` or `effort` option). Verification: the new test fails before the source exists. Planned evidence: specs/052-claude-workflow-gate/evidence/t004.json with source hash, test names, exits and limits; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-008 SC-008 REQ-001 SC-001 REQ-003 SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T005

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T005 -->

## Task

Write the fixture repository builder and the known-answer corpus. Dependencies: T001. Target files: tests/claude_workflow_gate_helpers.py; tests/test_claude_workflow_gate.py. Acceptance: Deterministic temporary repositories with one base and branches for: disjoint files, same file different hunks, same hunk, delete versus modify, rename, binary change, symlink change, untouched pair, a branch equal to the base, a branch not descending from the base, 2, 4, 5, 32 and 33 operations. Each pair carries a stated file-level truth label written before any tool output is read. Records the Git version; a Git without `merge-tree --write-tree` is an unavailable observation, not a pass. Verification: builder self-tests. Planned evidence: specs/052-claude-workflow-gate/evidence/t005.json with corpus manifest and Git version; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-002 SC-002 REQ-006 SC-006 REQ-015 SC-015
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T006

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T006 -->

## Task

Write failing argument-validation and degradation tests. Dependencies: T004 T005. Target files: tests/test_claude_workflow_gate.py. Acceptance: Fixture args (valid, missing base, missing workspaceId, unknown field, wrong types, empty sources, sources not an array, one source, duplicate source, identifier with revision syntax) each end `refused` with zero `agent()` calls; simulated busy admission lock, unregistered workspace, exceeded limits and timeout map to `busy`, `refused` or `inconclusive` with no retry and no second workspace; a `workspaces` fixture with runtime enabled and a planted grant store (on the explicit workspace and, separately, on another registered workspace) ends `refused` with `runtime-enabled-workspace` and no `analyze-work` call; a validate result listing `execute`, `recover`, `verify` or `status` among the visible plugin tools ends `refused` with `unsafe-tool-surface`. The script is executed with mocked `agent`, `phase`, `log` and `args` globals in a pinned JavaScript runtime whose version is recorded; a missing runtime is reported as an unavailable observation and the structural checks of T004 still run. Verification: tests fail before T008 to T014. Planned evidence: specs/052-claude-workflow-gate/evidence/t006.json with runtime version or the statement that none was available; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-001 SC-001 REQ-010 SC-010 REQ-002 SC-002 REQ-016 SC-016
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T007

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T007 -->

## Task

Write failing envelope-schema tests. Dependencies: T001. Target files: tests/test_claude_workflow_gate.py. Acceptance: Sample envelopes for every status validate against `contracts/braid-gate-result.schema.json`; extra fields, `executionAuthorization` other than false, a missing canonical limit, a reordered phase list and a certified status without a certificate are rejected; the limits content is identical across statuses; `jsonschema` is used only from the isolated development environment. Verification: tests pass against the schema alone and gate the later report phase. Planned evidence: specs/052-claude-workflow-gate/evidence/t007.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T008

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T008 -->

## Task

Implement the workflow skeleton: header, literal meta, argument validation and the refusal and report builders. Dependencies: T004 T006 T007. Target files: integrations/agent-braid/plugin/workflows/braid-gate.js. Acceptance: SPDX AGPL-3.0-only header; literal `meta` (name braid-gate, description, five phases); only `base`, `sources`, `workspaceId` accepted; every invalid input returns a schema-valid `refused` envelope before any agent is spawned; the canonical limits, the `assurance` block (class `0-heuristic`) and `executionAuthorization: false` are constants in the script; gating decisions are computed by script code from schema-bound results (Article 12). Verification: T004, T006 and T007 tests for the skeleton cases. Planned evidence: specs/052-claude-workflow-gate/evidence/t008.json with source hash and test results; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-001 SC-001 REQ-009 SC-009 REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T009

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T009 -->

## Task

Implement the validate phase. Dependencies: T008. Target files: integrations/agent-braid/plugin/workflows/braid-gate.js. Acceptance: One agent runs the fixed hardened read-only Git command template (REQ-006; T011 defines it once) and calls the read-only bootstrap tool `workspaces` once (no admission lock); it resolves `base` and each source to 40-hex identifiers, checks ancestry and presence in the registered repository, returns the registered `sourceRoot`, `resultRoot`, runtime mode and grant-store presence of every registered workspace, the repository root reported by Git and the plugin tool names visible to it, all under a strict schema; the script applies the rules (equal-to-base, duplicate after resolution, not a descendant, fewer than two sources, more than 32 operations, `workspace-not-registered`, `workspace-root-mismatch` against the registered `sourceRoot`, `runtime-enabled-workspace` when any registered workspace has runtime enabled or a grant store, `unsafe-tool-surface`; on the constrained-CLI fallback the registry rows come from `plugin workspaces` and are unobtainable only as `mcp-unavailable`) and refuses naming the input and the rule, never selecting another workspace; uncommitted work is stated as not observed. The equal-to-base case is a blocking-defect control. Verification: the T005 corpus through a harness that replaces the agent with the same read-only Git commands. Planned evidence: specs/052-claude-workflow-gate/evidence/t009.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-002 SC-002 REQ-016 SC-016 REQ-006 SC-006
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T010

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T010 -->

## Task

Implement the analyze phase. Dependencies: T009. Target files: integrations/agent-braid/plugin/workflows/braid-gate.js. Acceptance: Exactly one agent calls the registered workspace's MCP `analyze-work` with `kind: git` and commit sources over the pinned identifiers (`analyze-git` is a CLI command and appears only on the fallback path), never a worktree or path source; it returns the report reference, coverage, interaction classes and unknown effects without rewriting them; a busy admission lock, an unavailable MCP tool or a limit error ends the run as `busy`, `refused` or `inconclusive` with the verbatim message and no retry. If MCP tools are absent the script refuses with `mcp-unavailable`; the bundled-CLI path exists only if T029 records an acceptable outcome (Blocked by T029 for that path). Verification: harness with a recorded analyzer fixture; later native observation in T030. Planned evidence: specs/052-claude-workflow-gate/evidence/t010.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-003 SC-003 REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T011

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T011 -->

## Task

Implement the baseline phase. Dependencies: T009. Target files: integrations/agent-braid/plugin/workflows/braid-gate.js. Acceptance: The script defines one fixed hardened Git template as constants (system and global configuration disabled via `GIT_CONFIG_NOSYSTEM` and `GIT_CONFIG_GLOBAL`, `GIT_TERMINAL_PROMPT=0`, `-c core.hooksPath=/dev/null`, fsmonitor disabled, external merge drivers and content filters disabled, no network), following docs/architecture/PARALLEL_INTEGRATION.md and the precedents `GIT_CONFIG_NOSYSTEM` in agent_braid/git_replay.py and `-c core.hooksPath=/dev/null` in agent_braid/git_runtime.py, and every phase's Git command uses it; a command that cannot be hardened is a stated limit and its phase is unavailable or inconclusive, not run unhardened. One agent runs, for every pair, `git merge-tree --write-tree --merge-base=<base>` with a temporary `GIT_OBJECT_DIRECTORY` that uses the repository store as an alternate, and the chained fold in the chosen order that yields `expectedFinalTree`; all merge results are ephemeral and never applied to a ref, worktree or the repository store; reports conflicted paths or the error per pair, and records refs and `git count-objects -v` before and after as `true`, `false` or `not-observed`; a Git without the option yields `baseline unavailable`, never clean. The baseline is reported beside the analyzer verdict and never merged into it. Verification: T005 corpus; compare per-pair outcomes with direct `git merge-tree` runs and compare object counts, unreachable objects and refs before and after; a hardening test with a fixture repository whose configuration and attributes carry a sentinel hook, fsmonitor command, merge driver and filter that must not run. Planned evidence: specs/052-claude-workflow-gate/evidence/t011.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-006 SC-006
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T012

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T012 -->

## Task

Implement the finalize phase: replay certificate, prepared batch and end-of-run reference check. Dependencies: T010 T011. Target files: integrations/agent-braid/plugin/workflows/braid-gate.js. Acceptance: One agent, within the single-MCP-caller discipline, obtains replay evidence and the advisory plan from the plugin MCP `analyze` tool with a script-derived runtime request only for 2 to 4 operations whose analysis allows it (the MCP has no `plan-git`/`verify-git`; those CLI commands exist only on the constrained fallback), and skips with `operation-limit-4` or another stated reason otherwise (a skip is never a pass); calls the plugin `prepare` tool once, serial mode only, only with complete coverage, no conflicting or unknown pair and a clean baseline, with full 40-hex identifiers, `order` (input order, not a recommendation), `declaredWrites` equal to the observed paths, empty `uncertainPaths`, `expectedFinalTree` and a `runDirectory` name under the registered `resultRoot`, all derived by the script from schema-bound results (`prepare` does not allocate the directory); where `expectedFinalTree` cannot be derived deterministically the batch is `not-prepared` with `expected-tree-unavailable`; the agent never calls grant, execute, recover, status or verify tools or the runtime-mode tools, which is enforced by the REQ-016 refusal and the host allowlist and not by the prompt alone; the same agent re-resolves base and sources and the script reports moved or deleted references in `staleRefs` with status `inconclusive`. Verification: harness over the 2, 4 and 5 operation fixtures; negative tests with runtime enabled and a planted grant (T006); transcript inspection of tool names. Planned evidence: specs/052-claude-workflow-gate/evidence/t012.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-004 SC-004 REQ-005 SC-005 REQ-016 SC-016 REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T013

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T013 -->

## Task

Implement the report phase. Dependencies: T012. Target files: integrations/agent-braid/plugin/workflows/braid-gate.js. Acceptance: The script (no agent) classifies each pair as `both-clean`, `both-conflicting`, `analyzer-stricter`, `baseline-stricter`, `analyzer-unknown`, `baseline-unavailable` or `not-comparable`, flags every `independent-candidate` versus baseline-conflict pair as a counterexample, computes the overall status by fixed rules, sets `advisoryOrder` to `null` unless dependencies are declared (the gate declares none), counts agents (0 for refused arguments, 4 for a run that completed all agent phases), attaches the `assurance` block, validates the envelope before returning it and uses only permitted claim wording. Verification: T007 schema tests and the T005 truth table. Planned evidence: specs/052-claude-workflow-gate/evidence/t013.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-007 SC-007 REQ-015 SC-015 REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T014

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T014 -->

## Task

Complete the degradation mapping and partial-output preservation. Dependencies: T010 T011 T012. Target files: integrations/agent-braid/plugin/workflows/braid-gate.js. Acceptance: A failed or timed-out phase keeps earlier phase outputs in the envelope, marks later phases `not-run`, never fabricates a clean verdict, never retries (the host may restart a stalled agent, which the script cannot suppress: MCP calls stay read-only and idempotent, `prepare` is requested at most once, a busy refusal that may stem from the gate's own earlier attempt maps to `inconclusive`, and `agentsUsed` is a lower bound) and never widens limits or selects another workspace; the 1 MiB, 32-operation, four-active-call and 360 s limits are adopted as the stricter bound, not raised. Verification: T006 degradation tests pass. Planned evidence: specs/052-claude-workflow-gate/evidence/t014.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T015

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T015 -->

## Task

Write the failing packaging tests. Dependencies: T004. Target files: tests/test_plugin_package.py. Acceptance: Tests assert that assembling with the opt-in copies `integrations/agent-braid/plugin/workflows/` to `plugin/workflows/` with a byte-stable inventory entry; two builds from one clean commit have identical inventories; verification rejects a missing, altered or extra workflow file; the Claude manifest declares no `workflows` override (default discovery) and the portable manifest, `mcp.json`, `.mcp.json` and the six existing skill files are byte-identical to the baseline; the package contains no `hooks`, `mods`, `agents` or `monitors` entries; the version string is unchanged; the default build (no opt-in) excludes `workflows/` and passes package verification, the explicit opt-in build includes it and is marked engineering-only (pre-adoption guard), and both are asserted. Verification: tests fail before T016. Planned evidence: specs/052-claude-workflow-gate/evidence/t015.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-011 SC-011 REQ-008 SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T016

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T016 -->

## Task

Copy the workflow directory in the plugin builder. Dependencies: T008 T015. Target files: scripts/build_native_plugin.py. Acceptance: `assemble()` copies the workflows directory after the setup skill copy using the same tree-copy discipline only when an explicit opt-in is given (default: excluded until ADR adoption; the opt-in output is marked engineering-only and shares the unchanged version string, so it is never a releasable identity), adds nothing else, leaves the frozen Git runners untouched, and does not change `VERSION` (the bump is R1, T038). Verification: T015 tests; `python3 -m scripts.validate_change --base develop --profile quick`. Planned evidence: specs/052-claude-workflow-gate/evidence/t016.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-011 SC-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T017

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T017 -->

## Task

Write failing validation-profile tests for the new artifact type. Dependencies: T004. Target files: tests/test_validation_profiles.py. Acceptance: A path under `integrations/agent-braid/plugin/workflows/`, the workflow test file and `docs/tooling/CLAUDE_WORKFLOWS.md` classify under a named domain, are sensitive, select the full tests and carry a boundary that names host verification and release acceptance; no path is classified as unknown. Verification: the test fails before T018. Planned evidence: specs/052-claude-workflow-gate/evidence/t017.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-011 SC-011 REQ-008 SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T018

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T018 -->

## Task

Add the explicit validation rule. Dependencies: T017. Target files: scripts/validate_change.py. Acceptance: A dedicated rule is added next to the `ai-tooling` rule (matching is not first-match, so the existing rule already makes these paths sensitive; the new rule makes the artifact type explicit and carries its own boundary text). Verification: T017 tests and the existing profile tests. Planned evidence: specs/052-claude-workflow-gate/evidence/t018.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-011 SC-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T019

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T019 -->

## Task

Write the recipe. Dependencies: T008; the host status of each behavior stays "unverified" until T032. Target files: docs/tooling/CLAUDE_WORKFLOWS.md. Acceptance: Shows how to end a user's workflow with the gate directly and through nested `workflow()` (nesting is one level, so the gate itself never nests), how to split sign-off into separate workflows, what the result contains and does not contain, how the operator issues a grant and executes outside the workflow, every unconfirmed host behavior marked unverified, the observed Claude Code versions (none yet), and no speed, safety or semantic-correctness claim. States the host permission allowlist required by REQ-016 (plugin tools `workspaces`, `analyze-work`, `analyze`, `prepare`; fixed read-only Git prefixes; on the fallback only the explicit launcher subcommands `analyze-git`, `plan-git`, `verify-git` and `plugin workspaces`) and that a runtime-enabled registration is refused, so the operator uses an analysis-only one. Marked unreleased and dependent on ADR adoption; builds that include the workflow before adoption are engineering-only. Verification: link and anchor check; each example command runs in the fixture repository or is marked unverified. Planned evidence: specs/052-claude-workflow-gate/evidence/t019.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-012 SC-012 REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T020

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T020 -->

## Task

Update the surrounding documentation to distinguish skills from the workflow component. Dependencies: T019. Target files: docs/tooling/NATIVE_PLUGINS.md; docs/tooling/PLUGIN_PACKAGE_README.md; docs/tooling/PLUGIN_PRIVACY.md; docs/tooling/plugin-submissions/README.md. Acceptance: Each file states that the gate is an optional Claude-only component, that Codex ignores it, that the five product skills and the setup skill are unchanged, that the gate reaches the network nowhere, writes no source state and issues no grant, and that it is unreleased; the privacy text states what the gate agents read (Git metadata and analyzer results) and that nothing is uploaded. Verification: documentation review and the claim-discipline checklist. Planned evidence: specs/052-claude-workflow-gate/evidence/t020.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-011 SC-011 REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T021

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T021 -->

## Task

Run the known-answer comparison of the analyzer against the merge-tree baseline. Dependencies: T011 T013. Target files: specs/052-claude-workflow-gate/evidence/corpus-comparison.json. Acceptance: A complete classification table with denominators, each counterexample listed with commit identifiers or "none observed in this corpus"; every pair also carries a naive path-overlap column and an analyzer `conflicting` pair counts as added detection only where naive overlap missed it (expected none); H1 is not claimed beyond the corpus and H2 is a packaging statement, not a detection claim; a counterexample blocks conservativeness wording and is not by itself a protocol failure. Verification: the corpus run through the analyzer and direct merge-tree. Planned evidence: the corpus-comparison file with Git and analyzer versions; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-015 SC-015
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T022

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T022 -->

## Task

Close PR2: quick profile, one pr profile on a stable candidate, independent review and merge decision. Dependencies: T004 to T021. Target files: none beyond earlier tasks. Acceptance: Both profiles pass or the failure is reported; no version bump, release or publication is part of PR2, and the default build still excludes `workflows/` (the opt-in is the pre-adoption guard of T015/T016); the executed checks are listed separately from the pending host, human and founder checks. Founder: decides whether PR2 may merge before ADR adoption (allowed by the 2026-10-23 clarification only while no version bump, plugin-dist publication or release occurs). Verification: `python3 -m scripts.validate_change --base develop --profile pr`. Planned evidence: specs/052-claude-workflow-gate/evidence/t022.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-011 SC-011 REQ-008 SC-008 REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T023

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T023 -->

## Task

Founder: choose the Claude Code host and version for verification and install the built candidate package locally. Dependencies: T022 (an engineering candidate built outside the checkout; an `--allow-dirty` artifact is never a releasable identity). Target files: evidence/host-prerequisites.json. Acceptance: Records Claude Code version, platform, workflows setting, plugin version and source commit; EUR 0 additional spend on the existing subscription (docs/tooling/BUDGET.md); no paid API, credits or upgrades. Verification: not applicable (operator action). Planned evidence: the prerequisites file; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-013 SC-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T024

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T024 -->

## Task

HV-1, plugin MCP tools inside workflow agents. Blocked by T023. Dependencies: T023. Target files: evidence/hv-1.json plus transcript. Acceptance: Records pass, fail or unobserved with Claude Code version, whether `workspaces` and `analyze-work` are visible and callable from a workflow agent, and the exact tool names exposed to the agent for an analysis-only registration and for a runtime-enabled one; if `execute`, `recover`, `verify` or `status` are visible and the host cannot deny them, the outcome is recorded as fail for the REQ-016 control. Negative outcomes are valid. Verification: native probe run; transcript saved. Planned evidence: evidence/hv-1.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-013 SC-013 REQ-003 SC-003 REQ-016 SC-016
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T025

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T025 -->

## Task

HV-2, plugin agent definitions as `agentType`. Blocked by T023. Dependencies: T023. Target files: evidence/hv-2.json. Acceptance: Records the outcome and version; the gate ships no plugin agent, so this outcome only bounds future design and R1 does not depend on it. Verification: native probe run. Planned evidence: evidence/hv-2.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-013 SC-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T026

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T026 -->

## Task

HV-3, nested call of the plugin workflow by name from `workflow()`. Blocked by T023. Dependencies: T023. Target files: evidence/hv-3.json. Acceptance: Records whether `workflow('agent-braid:braid-gate', args)` or the equivalent plugin-namespaced name resolves and returns one structured result, and the direct slash invocation path separately. Verification: native probe run. Planned evidence: evidence/hv-3.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-013 SC-013 REQ-001 SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T027

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T027 -->

## Task

HV-4, resume after interruption and automatic restart of a stalled agent. Blocked by T023. Dependencies: T023. Target files: evidence/hv-4.json. Acceptance: Records which gate agents rerun after a stop and relaunch, and whether any second MCP caller or duplicate prepare call occurred; forces a stall of the analyze and finalize agents (for example a long-running read) and records whether the host restarts them ("attempt 2 (stalled)"), how many restarts, whether the restarted attempt calls the MCP again, whether the admission lock refuses it, and what `agentsUsed` and the envelope report; negative and unobserved outcomes are valid. Verification: native probe run. Planned evidence: evidence/hv-4.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-013 SC-013 REQ-010 SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T028

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T028 -->

## Task

HV-5, per-run approval and auto-mode prompts. Blocked by T023. Dependencies: T023. Target files: evidence/hv-5.json. Acceptance: Records what prompt appears in manual, accept-edits and auto modes and under `claude -p`, what Bash and MCP permissions the gate agents need, the exact permission allowlist rules used and whether the host can express them, and confirms that approval of the run is treated as no Agent Braid authority. Defines and records "Bash constrained to the launcher" for the fallback: an explicit rule set, in force for the session because subagents use the session's permission rules, that allows only the fixed read-only Git prefixes plus the explicit launcher subcommands `analyze-git`, `plan-git`, `verify-git` and the argument-less `plugin workspaces` (the registry read the fallback uses for the REQ-016(e) checks), and no rule matching the launcher binary as a whole, `grant-policy-run`, `execute-policy-run`, `recover-policy-run` or any other launcher subcommand; records whether the host can express an exact no-argument rule for `plugin workspaces` and, as an input to SPEC-053 REQ-009 only, whether it could also express the one additional subcommand `analyze-claude-transcripts` that gate v2 would need (planning amendment approved by the founder on 2026-10-24); per-agent separation is recorded as available or not. Verification: native probe run. Planned evidence: evidence/hv-5.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-013 SC-013 REQ-009 SC-009 REQ-016 SC-016
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T029

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T029 -->

## Task

Record the host-verification disposition and apply the declared fallback or kill criterion. Blocked by T024 T026 T028. Dependencies: T024 T026 T028. Target files: evidence/hv-disposition.md. Acceptance: Each of five behaviors has a recorded pass, fail or unobserved outcome with version. If HV-1 fails, the bundled-CLI fallback is allowed only if the Bash permission can be constrained as defined in T028 (explicit launcher subcommands alongside the Git read prefixes, never the launcher binary as a whole); otherwise R1 is no-go for the CLI path and only the documentation recipe ships. A host that cannot express that constraint (including per agent, when needed) is recorded as a no-go input for SPEC-053 REQ-009; on the fallback the registry rules are computed from `plugin workspaces` rows and the fallback refuses with `mcp-unavailable` when they cannot be obtained (REQ-016(e)). If HV-3 fails and nesting is the only integration path, there is no R1 gate. R1 depends only on HV-1, HV-3 for the nested path, and HV-5. Verification: not applicable (record). Planned evidence: evidence/hv-disposition.md; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-013 SC-013 REQ-003 SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T030

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T030 -->

## Task

Run the gate natively over the fixture matrix. Blocked by T029 with a passing required behavior. Dependencies: T029. Target files: evidence/native-gate-runs.json plus transcripts. Acceptance: Fixture runs with 2, 4 and 5 operations, independent edits, conflicting edits, a deletion and the equal-to-base case; the MCP transcript contains no grant, execute, recover, verify or status call; with a deliberately runtime-enabled scratch registration the gate refuses (`runtime-enabled-workspace`); a hardening run with sentinel hook, fsmonitor, merge driver and filter leaves no marker; refs, worktrees and working-tree status are identical before and after; object counts and unreachable objects are unchanged; per-pair outcomes match direct merge-tree runs. Verification: native runs with saved transcripts. Planned evidence: evidence/native-gate-runs.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-002 SC-002 REQ-003 SC-003 REQ-004 SC-004 REQ-005 SC-005 REQ-006 SC-006 REQ-008 SC-008 REQ-016 SC-016
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T031

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T031 -->

## Task

Run the gate in an auto-mode session and under organization-disabled workflows. Blocked by T029. Dependencies: T029. Target files: evidence/auto-and-disabled.json. Acceptance: The auto-mode run yields the same envelope and no operator action is taken; with `disableWorkflows` the workflow cannot start and the result is recorded as unavailable rather than failed or clean. Verification: native runs. Planned evidence: evidence/auto-and-disabled.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-009 SC-009 REQ-010 SC-010 REQ-005 SC-005
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T032

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T032 -->

## Task

Update the recipe with the recorded host outcomes and versions. Blocked by T029 T030. Dependencies: T029 T030. Target files: docs/tooling/CLAUDE_WORKFLOWS.md. Acceptance: Every behavior shows its recorded outcome and Claude Code version or stays marked unverified; no unobserved host is claimed compatible. Verification: documentation review. Planned evidence: specs/052-claude-workflow-gate/evidence/t032.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-012 SC-012 REQ-013 SC-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T033

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T033 -->

## Task

Founder: adopt, amend or reject the ADR proposal. Dependencies: T022; T029 recommended before deciding. Target files: none (decision recorded in the PR). Acceptance: A recorded decision on adding a Claude-only `workflows/` component to the native plugin, including the no-go list in `adr-proposal.md`; rejection keeps the documentation recipe only and closes R1 as no-go. Verification: not applicable (human decision). Planned evidence: the PR review record; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-009 SC-009 REQ-011 SC-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T034

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T034 -->

## Task

Create the canonical ADR file. Blocked by T033 (adoption). Dependencies: T033. Target files: docs/adr/ (new file from 0000-template.md at the next free number at that time; the highest existing number today is 0028, and two files already share 0024, so confirm the next free number then); docs/adr/0024-native-ai-plugins.md (cross-reference links only). Acceptance: The ADR carries the proposal's decision, no-go list, authority boundaries and alternatives; the only edit to ADR 0024 is a link to the new ADR; no number is reserved before adoption. Verification: `python3 -m scripts.validate_spec_kit`. Planned evidence: specs/052-claude-workflow-gate/evidence/t034.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-011 SC-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T035

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T035 -->

## Task

Re-snapshot the affected current assurance records and write the authority impact review. Blocked by T034. Dependencies: T034. Target files: specs/047-local-technical-telemetry/assurance.json; specs/048-harness-variant-laboratory/assurance.json; specs/051-owned-work-evaluation/assurance.json; specs/052-claude-workflow-gate/assurance.json; specs/052-claude-workflow-gate/authority-impact-review.json; any other current record whose authority inventory includes docs/adr. Acceptance: Changed hashes are reported, human review resets to pending, no prior historical binding is rewritten, and the review record follows the specs/048 `authority-impact-review.json` shape. Verification: `python3 -m scripts.validate_spec_kit snapshot <feature>` per record, then the full validator. Planned evidence: authority-impact-review.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-009 SC-009 REQ-007 SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T036

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T036 -->

## Task

Reconcile README, inventory wording, validation rules and the milestone index; obtain independent review; decide PR3 merge. Blocked by T035. Dependencies: T035. Target files: docs/tooling/PLUGIN_PACKAGE_README.md; docs/development/SPEC_MILESTONE_INDEX.md; scripts/validate_change.py; scripts/build_native_plugin.py; tests/test_plugin_package.py; docs/tooling/CLAUDE_WORKFLOWS.md. Acceptance: The builder default flips to include `workflows/` (the pre-adoption opt-in guard is removed or inverted) with the package tests asserting the new default; any remaining "five skills" wording distinguishes skills from the workflow component; the milestone index matches the tracking configuration; the independent review is scoped to the authority delta. Verification: pr profile. Planned evidence: specs/052-claude-workflow-gate/evidence/t036.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-011 SC-011 REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T037

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T037 -->

## Task

Founder: go or no-go for R1 and the version number (expected 0.1.0-alpha.4). Blocked by T029 T030 T036. Dependencies: T029 T030 T036. Target files: none. Acceptance: A recorded decision independent of G0; no-go if a required host behavior failed without an acceptable fallback. Verification: not applicable (human decision). Planned evidence: the decision record; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-014 SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T038

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T038 -->

## Task

Bump the plugin version everywhere it is declared, tests first. Blocked by T037. Dependencies: T037. Target files: scripts/build_native_plugin.py; docs/tooling/NATIVE_PLUGINS.md; tests/test_plugin_package.py. Acceptance: Every occurrence of 0.1.0-alpha.3 outside historical records changes to the chosen version, found by `grep -rn "0.1.0-alpha.3"`; historical evidence and prior acceptance records are untouched. Verification: package tests. Planned evidence: specs/052-claude-workflow-gate/evidence/t038.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-014 SC-014 REQ-011 SC-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T039

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T039 -->

## Task

Build the candidate from a clean commit and reproduce it. Blocked by T038. Dependencies: T038. Target files: evidence/release-candidate.json. Acceptance: Records the clean source commit, package and inventory hashes, the default build (which includes the workflow only after T036), two builds with identical bytes, and a fresh-checkout reproduction; the plugin-dist checkout is not modified. Verification: `python3 scripts/build_native_plugin.py` into a new directory outside the checkout, then package verification. Planned evidence: evidence/release-candidate.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-014 SC-014 REQ-011 SC-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T040

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T040 -->

## Task

Observe native install, the gate over the fixture matrix, update from the previous alpha and uninstall; write the release acceptance. Blocked by T039. Dependencies: T039. Target files: specs/052-claude-workflow-gate/release-acceptance.md; evidence/release-alpha4.json. Acceptance: Modeled on specs/046-native-ai-plugins/release-acceptance.md; each supported host and platform has an observed or "not observed" entry; unobserved platforms carry no compatibility claim; registry and result bytes retained through update and uninstall. Verification: native runs with saved transcripts. Planned evidence: the two files; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-014 SC-014 REQ-011 SC-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T041

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T041 -->

## Task

Founder: accept, amend or reject the release acceptance. Blocked by T040. Dependencies: T040. Target files: none. Acceptance: A recorded decision that does not itself publish anything. Verification: not applicable (human decision). Planned evidence: the decision record; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-014 SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T042

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T042 -->

## Task

Founder: publish the accepted package to plugin-dist as one scoped, owner-authorized operation and record the receipt. Blocked by T041. Dependencies: T041. Target files: specs/052-claude-workflow-gate/delivery/publication.json. Acceptance: The scope (repository, branch, exact files, commit) is stated before the write; the receipt records the remote result and read-back; nothing beyond that scope is written; this task is not performed in the delivery that created this packet. Verification: remote read-back after the authorized write. Planned evidence: delivery/publication.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-014 SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T043

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T043 -->

## Task

Founder: authorize or defer remote tracking publication (milestone, spec and task issues, Project) for M4.6. Dependencies: PR1 merged. Target files: none (drafts: issue-drafts.md; tracking-drafts.json; milestone-description-draft.md). Acceptance: A recorded decision; the drafts forbid publication in the delivery that created them; the Project Review pending flags stay drafts until published. Verification: `python3 scripts/sync_github_tracking.py source`, then a reviewed audit before any apply. Planned evidence: the decision record; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T044

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T044 -->

## Task

Run the radar milestone review for M4.6. Blocked by T042 or a recorded R1 no-go; and by the SPEC-053 and G0 disposition. Dependencies: T029; SPEC-053 disposition. Target files: research/adoption/ review record for M4.6 (path decided by the radar process). Acceptance: Review states what was and was not observed, includes negative outcomes, and makes no speed claim. Verification: `python3 research/validate_research_radar.py`. Planned evidence: the review record; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-009 SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T045

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T045 -->

## Task

Obtain the technical review of the SPEC-052 deliverables. Blocked by T040 or a recorded R1 no-go. Dependencies: T044. Target files: specs/052-claude-workflow-gate/technical-review.md. Acceptance: Independent review of the implemented scope against the requirements, with pending items separate; reviewer identity and scope recorded. Verification: not applicable (review). Planned evidence: technical-review.md; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-009 SC-009 REQ-014 SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T046

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T046 -->

## Task

Founder: close the SPEC-052 part of M4.6. Blocked by T045 and the SPEC-053 and G0 closure items in program.md. Dependencies: T045. Target files: specs/052-claude-workflow-gate/founder-review.json. Acceptance: Each requirement is implemented or explicitly dispositioned; host-verification outcomes and each release acceptance are recorded; a negative or inconclusive host result is a valid closure input. Verification: not applicable (human decision). Planned evidence: founder-review.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-009 SC-009 REQ-013 SC-013 REQ-014 SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-052/T047

Proposed state: open. Parent: SPEC-052. Milestone: M4.6 — Claude Code dynamic workflows (unassigned number). Labels: `task`.

<!-- agent-braid-task-id: SPEC-052/T047 -->

## Task

Adapt the gate implementation to host restarts and untrusted echoed text. Blocked by: PR #672 rebase (the gate implementation branch must be rebased onto this packet first; no gate code is written in the specification packet). Dependencies: T006 T007 T010 T012 T014. Target files: integrations/agent-braid/plugin/workflows/braid-gate.js; tests/test_claude_workflow_gate.py; specs/052-claude-workflow-gate/contracts/braid-gate-result.schema.json. Acceptance: Harness tests with a simulated host restart (the same phase result delivered twice; a busy admission-lock refusal after the first attempt of the same phase completed) show a schema-valid envelope, a busy result attributable to the gate's own earlier attempt reported as `inconclusive`, `prepare` requested at most once by the script and no script retry; an agent result that fails the strict schema is not trusted; after the validate phase later prompts embed only the 40-hex identifiers the script resolved; a ref name carrying instruction-like text within the arguments pattern never reaches a later prompt; the result schema constrains the echoed name fields (`request.base`, `request.sources[]`, `refusal.input`) to the arguments pattern and marks `refusal.message` and `phases[].detail` as untrusted text in their descriptions (a schema change coordinated with the PR #672 tests). Verification: the T006 and T007 test classes extended; the real host is observed in T027. Planned evidence: specs/052-claude-workflow-gate/evidence/t047.json; obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/052-claude-workflow-gate/assurance.json)
- Trace: REQ-010 SC-010 REQ-007 SC-007 REQ-008 SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.
