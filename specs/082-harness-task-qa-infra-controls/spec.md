# SPEC-082: Harness evaluation task QA and infrastructure controls

**Milestone:** HAR.4 — Harness evaluation platform (new milestone).

**Status:** draft. Documentation only; nothing is implemented, built or run by this
specification's first PR. It implements owner decision F6 of the
[harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md) (2026-11-22).
`executionAuthorization` is false for every record it defines.

## Purpose and scope

SPEC-049 T014 (15 units, one lineage) closed inconclusive under D3. The benchmark
found four gaps: too few lineages, no task QA, infra errors mixed with agent
failures, unrecorded run configuration. This spec defines formats and procedures
for them; SPEC-083 consumes the corpus and SPEC-084 executes trials on it.

Engineering only; no claim about any harness candidate. That this repository's
history yields at least 20 QA-passing tasks is hypothesis H1; a low yield is a valid
feasibility result.

In scope:

- a corpus of 20–50 real-failure tasks from this repository's history (merged-PR
  regression fixes, SPEC-049 lineages L1–L4), with public and private held-out splits;
- per-task QA in the Terminal-Bench 2.0 style: oracle passes, exploits fail, two
  reviewers;
- infrastructure controls: infra errors apart from agent outcomes, pinned and
  recorded configuration, fresh run ids; a contamination record.

Exclusions (each a MUST NOT):

- MUST NOT run any agent, model, container or harness session in the first PR; the
  exploit agent runs only under SPEC-084 or an owner admission (OD-6).
- MUST NOT compute or report a harness verdict; statistics belong to SPEC-083.
- MUST NOT relabel repository-history or synthetic tasks as native user sessions.
- MUST NOT place private held-out task bytes in the public repository or its history.
- MUST NOT change a frozen SPEC-049 record, the D1–D3 rules, or the T005 roster.
- MUST NOT grant, promote, activate or authorize execution.

## Requirements and acceptance scenarios

**REQ-001 Owner review.** The owner reviews this spec and plan before any code.

- **SC-001:** Given this spec, plan and tasks, when the owner reviews them, then OD-1
  to OD-7 are decided or deferred in a dated record.

**REQ-002 Task record format.** Each task has a versioned record: id, origin
(`repository-history` or `synthetic`), lineage, stratum (closed vocabulary, OD-2),
family, source provenance (PR number, pre-fix and fix commits, merge date), rights
basis, initial-state commit, task statement, oracle (fail-to-pass and pass-to-pass
tests), reference-solution hash, resource budget, canary id, partition, QA status
and the SHA-256 of each file. Unknown keys refuse.

- **SC-002:** Given a record missing a field, carrying an unknown key or a wrong
  hash, when it is validated, then it refuses with a reason code and a JSON Pointer.

**REQ-003 Selection rule before construction.** The rule that admits a candidate
from history is frozen by hash before any task is built. Every candidate, exclusion
and its reason, and the observed yield are recorded.

- **SC-003:** Given the frozen rule and the merged-PR history, when the inventory
  runs, then every inspected PR is listed as candidate or excluded with a reason, and
  the rule hash predates the first task record.

**REQ-004 Lineage and partition.** Tasks that share a fixing PR, a spec feature, a
test fixture base or an unresolved relation share a lineage (OD-2). Partitions
(`discovery`, `holdout`, `private-holdout`) are assigned by lineage, stratified,
with a recorded seed, before any candidate outcome exists. SPEC-049 D1 holds: L1 is
never split, L3 stays unassigned until resolved, L4 is held out only if it qualifies.

- **SC-004:** Given a manifest, when a lineage spans two partitions, L1 is split, L3
  is assigned, or a partition changes after any outcome record, then validation
  refuses.

**REQ-005 Private held-out split.** Private task bytes live outside the public
repository (OD-3); the public manifest holds only their hashes, counts and strata.
No optimizer context, prompt or library receives them. Their outcomes reach a
promotion decision only in aggregate, and each use is counted.

- **SC-005:** Given the public tree and an optimizer context, when they are
  scanned, then no private task byte or identity hash appears, and the use count
  matches the recorded evaluations.

**REQ-006 Oracle passes and no-op fails.** The reference solution applied to the
initial state passes the verifier in 3 of 3 fresh runs; the unchanged initial state
fails it. A flaky or failing oracle rejects the task.

- **SC-006:** Given a task, when the oracle and no-op checks run, then the oracle
  passes 3/3, the no-op fails, and any other result sets QA status `rejected`.

**REQ-007 Exploits fail.** The verifier restores protected test files and grades
outcomes, not paths. Deterministic probes (delete or weaken tests, hard-code
outputs, edit the verifier, forge a score file) and an exploit agent told to pass
without solving must all fail. A passing exploit rejects the task until it is
repaired and QA reruns.

- **SC-007:** Given a task, when each probe and the exploit agent run, then every
  one fails, and a planted weak verifier is caught by at least one probe.

**REQ-008 Two reviewers.** Each task has two independent review records (statement
clarity, solvability, no solution leak, oracle checks outcome, rights). Disagreement
needs an adjudication record (OD-4); a majority is not a consensus.

- **SC-008:** Given a task, when it is marked `qa-passed`, then two distinct review
  records exist, each labeled human or model, and any disagreement has an
  adjudication.

**REQ-009 Infrastructure errors kept separate.** A trial outcome is one of `pass`,
`fail`, `infra-error` (closed subclasses: setup, provider, quota-stop, runtime-crash,
verifier-crash, config-drift) or `not-attempted`. Classification follows a rule
frozen before data. An infra error never counts as 0 or as a pass; it leaves the
agent-outcome denominator, is reported with its count, and bounds the rate both ways.
An agent that exceeds its registered time budget is a `fail`. Reruns use fresh run
ids and are all kept; the job validity threshold is OD-5.

- **SC-009:** Given a synthetic job with injected infra errors, when trial records
  are summarized, then infra errors are counted apart, excluded from the agent
  denominator, shown in the bounds, and over the threshold the job is `invalid`.

**REQ-010 Pinned and recorded configuration.** Each trial records requested and
observed model id, reasoning effort, host and agent versions, CPU, memory, disk,
timeout, network policy and image digest when used. A mismatch is `config-drift`.

- **SC-010:** Given a trial whose observed model or effort differs from the request,
  or whose resource fields are missing, when it is validated, then it is
  `config-drift` or refused, never `pass` or `fail`.

**REQ-011 Fresh run ids, no cache reuse.** Each trial has a new run id from a
register, a fresh workspace and no reused result, session or cache (the SWE-bench
`run_id` hazard).

- **SC-011:** Given a trial whose run id is already registered, or a result whose
  bytes match an earlier run's, when it is recorded, then it refuses.

**REQ-012 Contamination record.** Each task carries a canary id and records its
public source date against each model's stated knowledge cutoff. Reports say the
canary is a detection aid and not a guarantee; no task is called contamination-free.

- **SC-012:** Given the corpus report, when it is reviewed, then each task shows
  canary, source date and cutoff relation, and the limitation text is present.

**REQ-013 No authority and handoff.** The frozen corpus manifest is handed to
SPEC-083 and SPEC-084 by hash. No record here authorizes execution.

- **SC-013:** Given the freeze record, when it is inspected, then it lists hashes,
  counts per partition, stratum and lineage, QA status per task, and
  `executionAuthorization: false`.

## Owner decisions (open)

- **OD-1 Corpus size.** 20, 30 or 50 candidates. Recommended: build about 30 and
  freeze whatever passes QA in 20–50; below 20 is a feasibility result.
- **OD-2 Lineage and stratum rules.** (a) one PR = one lineage; (b) conservative
  merge by shared PR, spec, fixture base or unresolved relation. Strata: SPEC-049
  `continuity` and `coordination`, plus `repair` for single-change fixes. Recommended:
  (b) and the three strata, never pooled.
- **OD-3 Private split storage.** (a) local private store outside the repository,
  hashes committed, as in ADR 0018; (b) encrypted file in the repository; (c) no
  private split. Recommended: (a).
- **OD-4 Second reviewer.** Options were (a) two humans; (b) owner plus an
  independent model review labeled as model; (c) owner only. Decided on 2026-11-23
  (T001): (d) cross adversarial review. Claude and Codex review each task blind, then
  critique each other's report. The owner adjudicates every disagreement. This is
  recorded as a deviation from Terminal-Bench 2.0's two human auditors.
- **OD-5 Infra policy.** Recommended: at most 2 reruns per trial; a job is `invalid`
  when infra errors exceed 10 % of trials or a task loses all trials.
- **OD-6 Exploit-agent venue.** (a) SPEC-084 after its gates; (b) an owner-admitted
  local run; (c) skip, so tasks stay `qa-incomplete`. Recommended: (a), else (c).
- **OD-7 Split proportions.** Recommended by lineage: 40 % discovery, 40 % holdout,
  20 % private-holdout.

## Non-goals

Statistics or verdicts (SPEC-083); trials, containers, Harbor (SPEC-084); promotion
pointers (SPEC-085); telemetry (SPEC-086); native cohorts; automatic promotion.

## Risks

- Yield: few merged PRs may have a clean fail-to-pass test; H1 may fail.
- One repository couples tasks; inference counts lineages, not tasks.
- History is public, so models may have seen fixes; the private split limits
  optimizer leakage only. Repeated held-out use still leaks through selection.
- A model reviewer may share blind spots with the agents under test.
- Post hoc infra classification; the rule is frozen before data.

## Dependencies

SPEC-049 (D1–D3, T005 roster, `harness_verification` partitions); SPEC-083 and
SPEC-084 consume the corpus; ADR 0045 (proposed); ADR 0018 (private data outside
Git history). None blocks drafting.

## References

- [Harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md) (F6),
  [ADR 0045](../../docs/adr/0045-hybrid-harness-evaluation-substrate.md),
  [ADR 0018](../../docs/adr/0018-private-source-sidecar-and-disposable-labs.md)
- [SPEC-049](../049-harness-evaluation-learning/spec.md) and its
  [evaluation protocol](../049-harness-evaluation-learning/evaluation-protocol.md)
- [Terminal-Bench 2.0](https://arxiv.org/html/2601.11868v1),
  [SWE-bench evaluation guide](https://github.com/SWE-bench/SWE-bench/blob/main/docs/guides/evaluation.md),
  [Demystifying evals](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents),
  [infrastructure noise](https://www.anthropic.com/research/infrastructure-noise)
