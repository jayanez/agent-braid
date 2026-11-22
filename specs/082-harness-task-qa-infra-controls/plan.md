# Implementation plan: SPEC-082 harness evaluation task QA and infrastructure controls

## Approach

- **This PR.** Spec, plan, tasks, validation plan and assurance record. No code, no
  schema, no task, no run.
- **Formats first.** After owner review, add versioned JSON schemas for the task
  record, corpus manifest, QA record and trial record, and one validator module. They
  extend, and do not replace, the SPEC-049 `harness_verification.Unit` partitions:
  `discovery` and `holdout` keep their meaning, and `private-holdout` is added.
- **Corpus from history.** Freeze the selection rule by hash, then inventory merged
  PRs read-only from local Git history (no network). A candidate is a merged PR whose
  change adds or edits a test that fails at the parent commit and passes at the merge
  commit. The SPEC-049 L1–L4 cases join as `synthetic` with their existing lineage
  ids and D1 rules. Lineage and partition are assigned before any candidate outcome.
- **QA is deterministic where it can be.** Oracle, no-op and exploit probes run
  locally with no model. Only the exploit agent needs a model; it waits for SPEC-084
  gates or an owner admission (OD-6). Until then a task is `qa-incomplete` and is not
  handed to SPEC-083 regression use.
- **Infra controls are record rules.** This spec defines the trial record, the closed
  infra-error taxonomy, the frozen classification rule, the run-id register and the
  summary bounds. SPEC-084 produces trial records; this spec validates them with
  synthetic fixtures only.
- **Private split.** Stored outside the repository (OD-3, ADR 0018 precedent); the
  public manifest carries hashes and counts. The validator scans the public tree and
  any optimizer context for private bytes and identity hashes, extending the
  SPEC-049 `check_context` rule. It cannot detect paraphrase.

## Constitutional check

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence; negative results valid | H1 (yield) is a hypothesis; a yield below 20 is a feasibility result |
| 9 | Experiments generate counterexamples | Exploit probes and the exploit agent are counterexample searches against each verifier; a passing exploit is a recorded result |
| 13 | Evidence method and domain explicit | Each task states origin, oracle kind, reviewer kind (human or model) and QA status |
| 14 | Evidence, not verdicts | Records expose hashes, configuration and infra counts; no verdict is computed here |
| 19 | Real, measurable problem | Tasks come from real regressions fixed in this repository |
| 20 | Analysis and execution separate | No execution; `executionAuthorization` false; runs belong to SPEC-084 |
| 23, 24 | Semantics before production | Formats and rules are reviewed before validators or tasks exist |

No MUST conflict found. One SHOULD deviation is proposed under OD-4 (one human and
one model reviewer instead of two human auditors); it needs owner acceptance.

## Affected files for the later code phase (named, not edited)

- New: `schemas/0.3.0-experimental/harness-task.schema.json`,
  `harness-corpus-manifest.schema.json`, `harness-task-qa.schema.json`,
  `harness-trial-record.schema.json`.
- New: `agent_braid/harness_task_corpus.py` (record, manifest, partition and private
  scan validation), `agent_braid/harness_trials.py` (trial record, infra taxonomy,
  run-id register, summary bounds).
- New: `scripts/har_corpus_inventory.py` (read-only Git history inventory),
  `scripts/har_task_qa.py` (oracle, no-op and exploit probes, local only).
- New tests: `tests/test_harness_task_corpus.py`, `tests/test_harness_trials.py`,
  `tests/test_har_task_qa.py`.
- Read, not changed: `agent_braid/harness_verification.py` (`PARTITIONS`,
  `selection_view`, `check_context`) unless the owner approves adding
  `private-holdout` there; frozen SPEC-049 records stay byte-identical.
- Spec data: `specs/082-harness-task-qa-infra-controls/corpus/` (public tasks and
  manifest) and `evidence/`.

## Phases

1. **P0 review.** Owner review (T001) and Codex review (T002).
2. **P1 formats.** Schemas and validators with negative controls (T003–T004).
3. **P2 corpus.** Selection rule freeze, inventory, lineage and partition, private
   store, task construction (T005–T008).
4. **P3 QA.** Oracle and no-op, exploit probes, exploit agent, reviews, contamination
   record (T009–T013).
5. **P4 infra controls.** Trial records, taxonomy and bounds on synthetic fixtures
   (T014–T015).
6. **P5 freeze and handoff.** Corpus freeze record to SPEC-083 and SPEC-084 (T016).

## Validation profile

- This PR: `python3 -m scripts.validate_spec_kit` and the `quick` profile per
  [VALIDATION_PROFILES.md](../../docs/development/VALIDATION_PROFILES.md); the CI
  `validate` aggregate on the PR head is the `pr` evidence.
- Code phase: targeted tests for the new modules, then `quick`; `pr` through CI.
  New schemas and `agent_braid/harness_*` paths may escalate to the full suite; use
  the escalation the path map reports.
- QA runs and reviews are separate evidence. A passing profile is not QA, not human
  review and not approval.

## Rollback

Documentation only: revert the PR. Code phase: the modules are additive and nothing
imports them outside their tests; revert removes them. The private store is deleted
by the owner; its hashes in the public manifest then refer to nothing, which the
manifest records as `withdrawn`.
