# H-CW1: Braid evidence adds to merge-tree on Claude worktree workflows

**Identifier:** H-CW1. **Claim label:** hypothesis (a falsifiable proposition
with a stated domain). **Evidence status:** untested. Milestone M4.6, gate G0.

## Statement

In the domain below, a read/write overlap derived from Claude subagent
transcripts identifies at least one integration failure that the `git
merge-tree` baselines, a naive path-overlap rule and Agent Braid commit-level
analysis (`analyze-git`) all miss (C1b); the overlap predicts reference failures
with a precision that is at least 0.3 and exceeds both the reference-failure
prevalence and the naive path-overlap precision (C2); and the share of tool calls
that stay unknown is bounded (C3). Commit-level analysis identifying a failure
that merge-tree misses (C1a) is reported as evidence about the commit-level gate
only; it neither supports nor falsifies this hypothesis.

## Domain

Ad-hoc Claude Code dynamic workflows in which 3 or 4 agents work in isolated Git
worktrees, on tasks with designed overlap, in one owner-controlled repository;
each agent commits; the reference outcome is a serial merge in a preregistered
order followed by the project tests. Nothing outside this domain is claimed:
not other hosts, workflows with more than 4 agents, other repositories, runtime
speed, or the safety of any integration. Transcripts record what an agent asked a
tool to do, not an independently observed effect, so any positive result is a
heuristic about prediction, not a proof of commutation.

## Falsification condition

Under the frozen preregistration, on at least 10 eligible runs with probe data,
the hypothesis is falsified by any one of: no reference failure missed by both
merge-tree baselines, the naive path-overlap arm and both Braid flags and flagged
by the probe (C1b); read/write-overlap precision below 0.3, or not above the
reference-failure prevalence or the naive path-overlap precision, with at least 3
probe-flagged runs (C2); or a pooled unknown rate above 40% (C3).

Order of evaluation: fewer than 10 eligible runs with probe data is inconclusive;
otherwise C1b and C3 are evaluated and either one unmet is a fail, even with
fewer than 3 probe-flagged runs; then fewer than 3 probe-flagged runs is
inconclusive; then C2 is evaluated and unmet is a fail. Fail therefore takes
precedence over inconclusive once 10 eligible runs with probe data exist.
Inconclusive is not support. A negative or inconclusive result is a valid,
reportable outcome.

## Evidence status and links

- Obtained evidence: none. The preregistration is not frozen and no run exists.
- Preregistration: [proposal](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md)
  and [inputs](../../docs/experiments/claude-workflow-g0-inputs.json), checked by
  `scripts/validate_claude_workflow_g0_proposal.py`.
- Specification: [SPEC-053](../../specs/053-claude-transcript-trace-adapter/spec.md);
  consumer: SPEC-052 (read-only integration gate).
- Source and budget draft: [decision record](../../specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md).
- Related negative result: parallel runtime speedup NO-GO (SPEC-021 G4, SPEC-022,
  SPEC-038); H-CW1 makes no timing claim.
- Index: the identifier is not yet listed in the hypotheses README or RESEARCH.md;
  adding it is a separate change.
