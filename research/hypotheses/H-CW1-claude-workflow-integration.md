# H-CW1: Transcript read/write overlap adds a signal on Claude worktree workflows

**Identifier:** H-CW1. **Claim label:** hypothesis (a falsifiable proposition
with a stated domain). **Evidence status:** untested. Milestone M4.6, gate G0.

## Statement

In the domain below, a read/write overlap derived from Claude subagent
transcripts identifies at least one semantic integration failure that the `git
merge-tree` baselines, a naive path-overlap rule and Agent Braid commit-level
analysis (`analyze-git`) all miss, with the failure attributable to the flagged
pair (C1b); the overlap predicts reference failures with a precision that is at
least 0.3 and exceeds both the reference-failure prevalence and the naive
path-overlap precision (C2); the share of unknown writer-capable tool calls is
bounded (C3); and the probe stays quiet on designed negative controls (C4). A
pass of this hypothesis' test means feasibility not refuted on a small designed
sample, not that the probe is worth implementing.

At commit level the Braid primary flag equals "two agents changed a common path"
plus `unknown` labelling, so commit-level analysis is not claimed to detect more
than naive path overlap. Commit-level analysis identifying a failure that
merge-tree and naive overlap miss (C1a) is reported as a consistency check of the
commit-level gate only; it neither supports nor falsifies this hypothesis, and
zero hits are expected.

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

Under the frozen preregistration, on the first 10 eligible runs with probe data,
the hypothesis is falsified by any one of: no semantic reference failure that was
missed by both merge-tree baselines, the naive path-overlap arm and both Braid
flags, flagged by the probe and attributable to the flagged pair (C1b);
read/write-overlap precision below 0.3, or not above the reference-failure
prevalence or the naive path-overlap precision, with at least 3 probe-flagged
runs (C2); a pooled unknown writer-capable rate above 40%, where read-only
searches are reported separately (C3); or the probe flagging more than 1 of the
at least 3 negative-control runs (C4).

Order of evaluation: fewer than 10 eligible runs with probe data, or an unmet
design quota, is inconclusive; otherwise C1b, C3 and C4 are evaluated and any one
unmet is a fail, even with fewer than 3 probe-flagged runs; then fewer than 3
probe-flagged runs is inconclusive; then C2 is evaluated and unmet is a fail.
Fail therefore takes precedence over inconclusive once 10 eligible runs with
probe data exist. Inconclusive is not support. A negative or inconclusive result
is a valid, reportable outcome. The test has low power (the proposal publishes
the table), so a fail is weak evidence against the heuristic.

## Evidence status and links

- Obtained evidence: none. The preregistration is not frozen and no run exists.
- Preregistration (revision 2, 2026-10-24): [proposal](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md),
  [inputs](../../docs/experiments/claude-workflow-g0-inputs.json) and
  [decision vectors](../../docs/experiments/claude-workflow-g0-decision-vectors.json),
  checked by `scripts/validate_claude_workflow_g0_proposal.py`.
- Specification: [SPEC-053](../../specs/053-claude-transcript-trace-adapter/spec.md);
  consumer: SPEC-052 (read-only integration gate).
- Source and budget decision (signature superseded by revision 2, renewal required before freezing): [decision record](../../specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md).
- Related negative result: parallel runtime speedup NO-GO (SPEC-021 G4, SPEC-022,
  SPEC-038); H-CW1 makes no timing claim.
- Index: on this branch the identifier is not listed in the hypotheses README or
  RESEARCH.md; adding it is a separate change.
