# Proposed preregistration: M4.6 gate G0, Claude workflow integration evidence

**Status:** Proposed and not frozen. Nothing in this document authorizes a
workflow run, a concurrent agent, a spend, a push or a remote issue. Freezing is
an explicit founder act (see "Freezing"). The exact machine-readable inputs are in
[claude-workflow-g0-inputs.json](claude-workflow-g0-inputs.json); the checker is
`scripts/validate_claude_workflow_g0_proposal.py`.

**Milestone:** M4.6, Claude Code dynamic workflows. **Hypothesis:**
[H-CW1](../../research/hypotheses/H-CW1-claude-workflow-integration.md).
**Owner of the gate:** [SPEC-053](../../specs/053-claude-transcript-trace-adapter/spec.md).

## Decision requested

Accept, amend or reject one preregistered feasibility experiment (gate G0). If
the founder freezes it, the founder runs at least 10 eligible ad-hoc Claude
workflows on an owner-controlled repository, and the recorded results decide
whether transcript-derived read/write hazards are worth implementing (SPEC-053
implementation requirements and the transcript part of the gate in SPEC-052).
G0 is an existence-and-usefulness screen on a small, designed sample. It is not
an effectiveness estimate, a benchmark, a safety proof or a speed claim.

## Question and claim labels

Does Agent Braid evidence (commit-level `analyze-git`, and read/write overlap
derived from Claude subagent transcripts) identify integration failures that
`git merge-tree` baselines do not, with usable precision and an acceptable share
of unknown results?

- Hypothesis (H-CW1): yes, in the stated domain. Untested.
- Heuristic: shared reads and writes across agents predict integration
  failures. Not a soundness claim; transcripts record what an agent asked a tool
  to do, not an independently observed effect.
- Analogy only: no braid or commutation claim is made by G0.
- Negative results are valid. Parallel runtime speedup is already a recorded
  NO-GO (SPEC-021 G4, SPEC-022, SPEC-038); G0 makes no timing claim.

## Population, sampling frame, eligibility

- **Target population:** Claude Code dynamic workflows in which 3 or 4 agents
  run in isolated Git worktrees on overlapping tasks in one repository, each
  agent committing its result.
- **Source and permissions:** one repository controlled by the founder, named in
  the run manifest at freezing (not named here; the repository binding is a
  required pre-freeze field). The founder's own Claude sessions, on the
  founder's existing subscription. Provider-terms review for using one's own
  transcripts as local analysis input is recorded in the
  [source and budget decision](../../specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md),
  currently pending the founder's signature. No third-party repository, user or
  transcript is in scope.
- **Sampling frame:** runs designed by the founder before launch, not sampled
  from history. Each run is an ad-hoc workflow with 3 or 4 agents, `isolation:
  'worktree'`, and a task set written with a stated overlap rationale. Among the
  first 10 eligible runs, taken in the run ordinal fixed in the manifest before
  launch, at least 7 carry a designed file or shared-symbol overlap and at least
  3 carry a cross-file contract dependency without a shared file (so that
  read/write hazards, not just write/write overlap, can occur). Each design
  property is recorded in the manifest before launch and is never assigned or
  changed after an outcome is seen. The founder reports how each task set was
  designed; designed overlap is a stated limit on generalization and makes the
  reference-failure prevalence high by construction (see C2).
- **Run budget:** at least 10 eligible runs; at most 14 may be started so that
  ineligible runs can be replaced. No run may be dropped or replaced after
  seeing its reference outcome except for the ineligibility reasons below, which
  are decided mechanically before the reference outcome is computed.
- **Eligibility (all required):** every agent commits at least one commit
  different from the base; the base tree passes the project tests; each agent
  branch passes the project tests alone; the workflow completes without
  intervention that edits agent branches; transcripts for all agents are
  available for the probe. A run without them is reported as `probe-unavailable`:
  it is counted, contributes to the Git arms and to C1a only, and is not part of
  the 10-run minimum or of the denominators of C1b, C2 and C3 (a run counts
  toward those only when it carries probe data).
- **Exclusions, reported with counts:** `agent-did-not-commit` (an agent whose
  branch equals the base: the known silent false negative of `analyze-git`, so
  it is excluded and counted, never scored as independent),
  `base-tests-fail`, `branch-tests-fail-alone`, `flaky-final-tests` (the final
  test command gives different results in two executions), `workflow-aborted`,
  `quota-exhausted`, `manual-edit-of-agent-branch`.

## Procedure per run

1. **Manifest first.** Before launch the founder records and hashes: run id,
   base commit, task list with overlap rationale, the serial merge order (the
   agent ordinal order, fixed here and never chosen after seeing results), the
   test command, agent count, tool versions (Git, Claude Code, Agent Braid commit
   and plugin version, `clash` if present).
2. **Run.** The founder starts and approves the workflow in a Claude Code
   session on the existing subscription. The workflow only creates agents and
   returns their branches; it performs no merge. Agents must commit.
3. **Collect.** Branch head commits and the subagent transcript files are read
   in place, read-only. The transcript layout is documented by the host but is
   confirmed by the founder on the first run and recorded in the manifest.
4. **Predict before reference.** Every arm computes its prediction and the
   prediction file is hashed before any reference outcome exists. This prevents
   policy-dependent labelling.
5. **Reference outcome.** In a throwaway clone at the base commit, merge the
   agent branches in the preregistered order with ordinary Git merges. Outcomes:
   `textual-conflict` (a merge step conflicts), `semantic-failure` (every merge
   is clean but the project tests fail in both of two executions on the final
   tree), `clean` (clean merges and passing tests). A run is a reference failure
   when it is `textual-conflict` or `semantic-failure`.
6. **Record aggregates** (see Retention) and keep raw material private.

## Arms

| Arm | Prediction for a run |
|---|---|
| `merge-tree-pairwise` | Failure if `git merge-tree --write-tree` of any agent pair against the base conflicts. |
| `merge-tree-chained` | Failure if folding the agents in the preregistered order with `merge-tree --write-tree` conflicts at any step. |
| `naive-path-overlap` | Failure if any two agents changed a common path (`diff --name-only --no-renames`). |
| `clash` | Failure if `clash` reports a conflict across the worktrees; `not-installed` is a valid recorded state. Optional; installation is the founder's own decision. |
| `braid-analyze-git` | Primary flag: any pair labelled `conflicting` or `ordered`. Inclusive flag (secondary): additionally any pair that is `unknown`. Also records `plan-git`/`verify-git` eligibility when the run has at most 4 operations. |
| `transcript-probe` | Flag if any ordered agent pair (i, j) has a path that i read and j wrote with i never writing it. Counts only, see below. |

`merge-tree-pairwise` and `merge-tree-chained` together form the merge-tree
baseline. A failure is "missed by merge-tree" only when both variants predicted a
clean run.

## Transcript read/write probe

The probe reads each subagent transcript locally and in memory, classifies tool
calls (`Read`; `Edit`, `Write`, `NotebookEdit` as write; `Bash`; `Grep` and
`Glob`; tool names starting `mcp__`; other), normalizes file paths to
repository-relative paths using the worktree root from the manifest, and counts
read/write overlaps. It retains only integer counts: per agent and per tool
class, and per run the number of ordered agent pairs and distinct paths with a
read/write overlap. Paths, file contents, prompts and tool outputs are never
written to any retained artifact. Failed tool calls count as calls and as
unknown, never as effects. Paths outside the worktree are counted separately and
never matched. The probe is a small stdlib script whose bytes are pinned before
freezing; it is a measurement tool for G0 and not the SPEC-053 mapper.

## Metrics (per arm unless stated)

1. Hits and misses against the reference: the run-level confusion counts
   (true/false positive/negative), reported with the textual and semantic
   failure classes separately.
2. Unknown rate. Primary (criterion C3): the pooled share of subagent tool calls
   the probe classifies as unknown (`Bash`, `Grep`, `Glob`, MCP and other,
   including failed calls). Secondary, always reported: the share of
   `analyze-git` operations with an `unknown` effect or partial coverage, and
   the share of agent pairs labelled `unknown`.
3. Replay-ineligible rate: the share of runs in which `plan-git`/`verify-git`
   cannot certify the batch (more than 4 operations, any unknown effect, partial
   coverage, or refusal).
4. Share of runs with more than 4 agents. Designed runs have 3 or 4 agents by
   construction, so this is read from a descriptive census of the founder's
   existing worktree workflows (agent counts only) taken at freezing; it is
   not a pass criterion.
5. `Bash` share of subagent tool calls.
6. Precision of read/write overlap as a predictor of reference failure:
   flagged runs with a reference failure divided by flagged runs (unit: the run;
   pairs inside a run are not independent). Also reported for every other arm
   (the naive path-overlap precision is the comparison used by C2), with recall
   and a Wilson 95% interval as description, not inference.
7. Analysis cost: wall time of each arm; subscription usage of each workflow run
   when exposed by the host (unavailable is recorded as unavailable, not zero).
8. Reference-failure prevalence: reference-failure runs divided by eligible runs
   with probe data. It is a pre-registered reported denominator, stated before
   C2 is evaluated, and C2 is compared against it.

## Preregistered success thresholds and decision

A reference failure is *missed by an arm* when that arm predicted a clean run for
it. The criteria below are fixed before any data exist.

- **C1a (commit-level evidence; informs R1 only and unlocks nothing):** at least
  1 reference failure that both merge-tree baselines missed and that the Braid
  primary flag (`braid-analyze-git`) identified. Report how many of those runs
  the naive path-overlap arm also flagged. C1a is descriptive evidence about the
  commit-level gate release R1. It is not an input to `g0-pass` or `g0-fail`, and
  it never unblocks the transcript adapter (SPEC-053 PR5) or gate v2 (PR6).
- **C1b (transcript-dependent; the only C1 criterion that gates the transcript
  requirements):** at least 1 reference failure that was missed by both
  merge-tree baselines, by the naive path-overlap arm and by `braid-analyze-git`
  under both its primary flag and its inclusive flag, and that the transcript
  probe flagged. Only a failure that transcript read/write evidence alone
  identified counts.
- **C2:** read/write-overlap precision of at least 0.3, which must also be
  strictly greater than the reference-failure prevalence (metric 8) and strictly
  greater than the naive path-overlap precision, evaluated only when at least 3
  eligible runs with probe data are flagged by the probe. If the naive arm flags
  no run its precision is undefined; that comparison is then recorded as not
  applicable and the other two conditions still bind. Because designed overlap
  makes prevalence high by construction, C2 is a floor against a probe that
  flags nearly every run and not evidence that the probe is useful.
- **C3:** unknown rate (primary definition above) of at most 40%.

**Order of evaluation.** The rule is applied in this order and stops at the first
outcome:

1. Fewer than 10 eligible runs with probe data: `g0-inconclusive`.
2. Evaluate C1b and C3 on those runs. If either is unmet: `g0-fail`. This holds
   even when fewer than 3 runs are flagged by the probe; with no probe-flagged
   run C1b is unmet.
3. Fewer than 3 runs flagged by the probe: `g0-inconclusive`.
4. Evaluate C2. If unmet: `g0-fail`.
5. Otherwise `g0-pass`, which requires C1b, C2 and C3 together.

So `g0-fail` takes precedence over `g0-inconclusive` once 10 eligible runs with
probe data exist, and `g0-inconclusive` never passes: the transcript requirements
stay blocked and a further attempt is a new proposal, never an amendment of this
one after seeing data.

**Kill outcome on `g0-fail`:** adoption track AT-2026-006 moves to
watch or rejected; SPEC-053 is closed as not adopted; M4.6 closes with R1 only.
A pass unblocks the planning of SPEC-053 and the transcript part of SPEC-052; it
does not adopt anything and does not prove the gate prevents conflicts.

## Retention and privacy

Retained in the repository after a run, only after founder review: the manifest
without task prose that names private content, hashes of branch heads, the
prediction file hash, per-arm run-level labels, the probe's integer counts and
the aggregate metrics. Not retained or published: transcripts, prompts, file
contents, diffs, repository file paths, merge-tree output and workflow journals.
The founder keeps raw material locally and may delete it after reporting. This
`aggregate-only` rule is the G0 measurement rule and is stricter than the product
mapper's: the mapper retains allowlisted metadata (repository-relative paths, base
object ids, a transcript digest) and counts, under its own label
`allowlisted-metadata-and-counts` (SPEC-053 contracts). The G0 probe retains no
path or path hash.

## Cost and authority

The founder runs the workflows on the existing Claude subscription with included
quota. Additional spend is EUR 0 ([budget](../tooling/BUDGET.md)); API
credentials, purchased credits, overage and auto-recharge are not used, and the
founder stops on quota exhaustion. Running the workflows is not delegated to a
coding agent in this delivery. Each workflow run needs the host's own per-run
approval. Concurrent agents inside a workflow are used only because the founder
freezes this proposal; no command or skill authorizes them (AGENTS.md).
Agent Braid analysis is read-only (Article 20): no grant is issued and no owned
runtime execution happens in G0.

## Freezing

This proposal becomes the preregistration only when the founder records a
separate decision that binds the exact bytes of this file and of the inputs JSON,
and fills the pre-freeze bindings listed under `requiredBeforeFreeze` in the
inputs file. Until then `frozen` is false and no run counts toward G0. Changing a
threshold, the order rule, an eligibility rule or an arm after the first run
starts requires a new proposal and invalidates earlier runs for G0.

## Limits

Ten or more designed runs on one repository cannot establish prevalence,
generalization, a false-negative rate for the gate or the safety of any
integration. A single hit can satisfy C1a or C1b and is an existence observation; C2 only
guards against a probe that flags nearly every run.
Transcripts are an agent's recorded intent; `Bash`-driven effects are invisible
to the probe. Host, model and Claude Code versions drift between runs and are
recorded, not controlled. The merge-tree baselines are stronger than file-level
overlap on textual conflicts and weaker on semantic ones, so the arms answer
different questions. Passing deterministic checks of this document proves only
its structure.
