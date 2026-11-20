# SPEC-078: Lightning held-out re-evaluation

**Milestone:** BL.2b — Lightning held-out re-evaluation (GitHub milestone created
by the reviewed tracking reconciliation after merge).

**Status:** draft. `human_review` is pending. This specification grants no
execution authority and promotes nothing. Every real host run needs the owner's
explicit yes, given after the rollout count is stated.

## Purpose and scope

BL.2 ([SPEC-072](../072-lightning-prompt-optimization/spec.md)) gave a negative
result: on the SPEC-069 held-out set (10 prompts × 3 repetitions, `claude-code`)
A0 scored 25/30 at first attempt, APO 23/30 and GEPA 24/30, and every arm missed
D4. That result is not interpretable as evidence about the optimizers:

- **A broken item.** HELD-04 failed every trial of every arm on every host. The
  shipped analyze skill told each waiting unit to declare a `read` of the file
  the other unit writes, and the frozen scorer rejects that read for the last
  unit of the chain. D4 requires all 10 prompts valid within one retry, so no
  guidance that obeyed the skill could meet D4. The owner attributed this to the
  guidance (2026-11-18), and the rule was narrowed before this specification
  (T001).
- **No power.** With 10 prompts the Wilson intervals of 24/30 (0.63–0.90) and
  25/30 (0.66–0.93) overlap almost entirely, and three repetitions of the same
  prompt add little independent information. Detecting a 10–15 point paired gain
  with McNemar's test needs about 77–107 prompts.
- **Other failures are not instrument defects.** Re-scoring the stored BL.2 and
  SPEC-069 T010 rollouts showed that HELD-02 and HELD-06 failed because the
  model chose kind `units` (which always records partial coverage and so can
  never report `independent-candidate`) for a parallelism question, or did not
  call `analyze-work` at all. The guidance already prescribes `aim` there and
  the scorer is right. These failures motivate the kind-choice and negative
  prompts in the new set (REQ-002), not a scorer change.

This specification is a research protocol. It first repairs and audits the
measurement (Gate 0, no rollouts), then measures the unchanged baseline guidance
A0 on a fresh, preregistered, adequately powered held-out set v2 (Gate 1), and
optimizes the guidance only if A0 misses the preregistered threshold (Gate 2).
A0 meeting the threshold, or a null or negative Gate 2 result, completes the
protocol.

In scope:

- held-out set v2 with three disjoint, hash-frozen splits and its case schema;
- Gate 0 tooling: reference solutions, a guidance-literal follower, null
  baselines and the 0 % transcript-review rule;
- the preregistered evaluation protocol and its analysis (paired exact tests,
  Wilson intervals, prompt-clustered standard errors);
- Gate 1: one A0 pass over the test split;
- Gate 2, conditional: one arm of bounded add/delete/replace edits proposed by
  reflection over the validator's structured errors;
- publication of the set as a regression suite when A0 meets the threshold.

Exclusions:

- Any change to `scripts/spec069_scoring.py`, the SPEC-069 prompt sets, FREEZE or
  D4. The scorer is reused unchanged as the reward and validator.
- Promotion of a candidate or editing the shipped skill from Gate 2 output
  (SPEC-073 owns promotion; the owner decides).
- APO; weight-level training (SPEC-076; BL.6 stays deferred); System One;
  natural-language tooling such as Stanza (no reward or runtime value).
- Hosts other than `claude-code`, any paid route, any API key, any LLM judge,
  any non-standard-library runtime dependency.
- Claims beyond the observed host, model, guidance bytes and prompt set.

## Authorities

Constitution clause zero and Articles 9, 12, 13, 14, 19, 20, 21 and 23;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md) (EUR 0
spend); [ADR 0039](../../docs/adr/0039-braid-lightning-boundary.md) (Braid Lightning boundary). Precedents:
[SPEC-069](../069-aim-request-authoring/spec.md) (case format, scorer, D4),
[SPEC-071](../071-lightning-rollouts-reward/spec.md) (runner, reward, canaries,
quota stops), [SPEC-072](../072-lightning-prompt-optimization/spec.md) (BL.2
outcome; its `evaluation-protocol.md` is frozen and is not edited here),
[SPEC-073](../073-lightning-promotion/spec.md) (promotion boundary).
Operator guide: [LIGHTNING.md](../../docs/tooling/LIGHTNING.md).

## Clarifications

Owner decisions already taken (2026-11-18 and 2026-11-20):

- **D1 — HELD-04 is a guidance defect.** The analyze skill's dependency rule was
  too broad. It now says the dependency alone orders the units and a `read` is
  declared only when the unit uses the other unit's file content (T001). The
  alternative of accepting an optional `read` in the scorer, suggested by the
  2026-11-20 research report, was considered and **not adopted**: the scorer
  stays frozen and the guidance states the intended semantics.
- **D2 — A0 first.** Gate 2 runs only if A0 misses the threshold on the test
  split.
- **D3 — Out of scope:** Stanza and similar NLP tooling.
- **D4 — Program state.** BL.3 stays open until this specification has a result;
  BL.6 stays deferred.

Design decisions recorded here:

- **P1 — Fresh authoring.** v2 cases are written from a class plan and templates
  (REQ-002), never by editing or paraphrasing SPEC-069 held-out cases or their
  failures. The SPEC-069 v1 sets remain a no-regression control only.
- **P2 — Same scorer, new acceptance rule.** Validity of one trial is
  `score_case(...)["validFirstAttempt"]` from the unchanged SPEC-069 scorer. The
  acceptance statistics of REQ-008 replace D4 as the primary rule for v2; D4-style
  counts and pass^3 are reported as secondary.
- **P3 — One test pass per arm.** The test split is eyes-off: it is opened only by
  the held-out command after the protocol freeze, and each arm (A0; the Gate 2
  candidate if Gate 2 runs) is scored on it once.

Owner decisions for the protocol (decided 2026-11-20; the protocol freeze, T003,
records them):

- **OD-1 — A0 threshold.** A test prompt *passes* when at least 2 of its 3
  repetitions are valid at first attempt; A0 *meets* the threshold when the
  Wilson 95 % lower bound of the share of passing prompts is at least 0.80
  (about 87/100) and no prompt is 0/3 after the transcript review of REQ-006.
- **OD-2 — Split sizes.** Feedback 24, validation 40, test 100 prompts,
  3 repetitions on validation and test. Gate 1 costs 300 rollouts; Gate 2, if
  run, adds about 600–900.
- **OD-3 — Host and model.** `claude-code` with model pinned to
  `claude-sonnet-5-5`, subscription route, as in SPEC-072.

## Requirements

- **REQ-001 — Guidance fix (prerequisite).** The analyze skill's dependency rule
  is narrowed as decided in D1, and a test pins it: the answer that follows the
  rule on HELD-04 scores valid through `analyze-work` and the scorer, and the
  answer the old rule produced does not. The change ships in the next alpha.
- **REQ-002 — Held-out set v2.** A versioned set file holds three disjoint splits
  (`feedback`, `validation`, `test`) of cases in the SPEC-069 case format, each
  with a class label and a structured statement of the facts the prompt gives
  (units, files, effect kinds, dependencies, whether a unit uses another's file
  content, whether the user names every file). The class plan covers: disjoint
  writes; shared writes; deletes; dependency chains with and without content
  reads; kind choice where `aim` is required although `units` is tempting; Git
  branches; and negative cases whose correct report contains `unknown` (unnamed
  or possibly other files, external or destructive effects). Each class appears
  in every split. No v2 prompt text duplicates or paraphrases a SPEC-069 prompt;
  a check refuses exact and normalized-text overlap with both v1 sets.
- **REQ-003 — Reference solutions (Gate 0).** Every v2 case has a reference
  request that `analyze-work` accepts and the scorer marks valid; a case without
  one blocks the freeze.
- **REQ-004 — Guidance-literal check (Gate 0).** A deterministic follower builds,
  from each case's structured facts, the request that the analyze skill's rules
  prescribe when followed literally (kind choice, `repo://workspace/` resources,
  dependency and read rule, coverage rule). Every v2 case's follower request must
  be accepted and score valid. A pin test ties each rule the follower encodes to
  its sentence in the skill, so a guidance edit that changes a rule fails the
  check until the follower is updated.
- **REQ-005 — Null baselines (Gate 0).** These fixed answers are scored on every
  case: no call; an empty declaration; every unit as kind `units`; every pair
  `unknown` through partial coverage; over-declaration (a `read` of every file
  another unit writes). Each must fail on every case where it differs from the
  expectation, and no null baseline may meet the OD-1 threshold on any split.
- **REQ-006 — Zero-prompt review.** A test prompt that is 0/3 in any arm is not
  counted until its transcripts are reviewed and classified as `model` (counts as
  a miss) or `instrument` (the reference or expectation is wrong). An
  `instrument` finding invalidates that arm's result and requires a new set
  version; it is reported, never silently dropped.
- **REQ-007 — Protocol and freeze.** `evaluation-protocol.md` preregisters the
  splits' sha256, the class plan, OD-1 to OD-3, the analysis and stopping rules.
  It and the set are frozen by hash on a `develop` commit before any rollout; the
  held-out command refuses when either hash differs or no freeze exists.
- **REQ-008 — Gate 1: A0 on the test split.** After the freeze and the owner's
  yes for the stated rollout count, A0 (the shipped guidance including T001) runs
  once on the test split. The report gives the per-prompt results, the share of
  passing prompts with its Wilson 95 % interval, the trial-level first-attempt
  rate with a prompt-clustered standard error, the OD-1 verdict, D4-style counts
  and pass^3 as secondary figures, canary hits, and the run's host, model and
  guidance hashes.
- **REQ-009 — Regression suite.** If A0 meets the threshold, the set is published
  as a regression suite with one documented command that re-runs it on a model or
  host change, and Gate 2 is not opened.
- **REQ-010 — Gate 2: bounded edits (conditional).** Only if A0 misses: one arm
  proposes add, delete or replace edits on sections of the skill body by
  reflection over the scorer's structured reasons on the feedback split (no
  transcripts, no validation or test content). An edit is kept only if it
  strictly improves the validation score. Each round has a character budget, the
  front matter is fixed, the guidance has a length cap, rejected edits are kept
  in a buffer the reflector sees, and each kept candidate has a readable diff.
  Every rollout checks that the skill was loaded. Implementation uses the
  standard library only.
- **REQ-011 — Gate 2 evaluation (conditional).** The final Gate 2 candidate runs
  once on the test split and once on the SPEC-069 v1 held-out set. Primary: the
  paired per-prompt comparison against A0 with the exact McNemar (sign) test on
  discordant prompts. The candidate must not regress on v1 against A0 measured
  in the same pass. A canary hit invalidates the arm. A null or negative result
  is reported as the outcome.
- **REQ-012 — Boundaries.** No BL.2b code edits the scorer, the SPEC-069 sets or
  the shipped skill from optimizer output, calls promotion, `execute`, `recover`
  or grant paths, uses an API key, an LLM judge or a paid route, or adds a
  runtime dependency; `executionAuthorization` stays false; spend is EUR 0.

## Success criteria

Each requirement has one acceptance scenario (SC-001 to SC-012) in
`assurance.json`, with its procedure in `validation-plan.md`. Milestone exit:
SC-001 to SC-008 and SC-012 obtained, plus SC-009 if A0 meets the threshold or
SC-010 and SC-011 if it misses. Any outcome, including a miss followed by a null
Gate 2, completes the protocol.

## Scientific boundaries

- **Hypotheses.** H-A0: the shipped guidance A0 meets the OD-1 threshold on the
  v2 test split. H-G2 (only if H-A0 is not supported): the Gate 2 candidate is
  better than A0 on the test split by the paired exact test at α = 0.05 without
  regressing on v1. Neither is a completion condition.
- **Observation contract.** One host, one model, one guidance byte string per arm,
  synthetic prompts written for this protocol, and the SPEC-069 scorer. Results
  say nothing about other hosts, models, real user requests or the semantic
  correctness of the analyzer beyond the scorer's rule.
- **Limits.** Prompts are written by the project from templates, not sampled from
  real use; class balance is a design choice; repetitions of one prompt are
  correlated, which the clustered standard error accounts for only
  approximately; the Wilson interval treats prompts as exchangeable.

## Compatibility

Additive. The scorer, the SPEC-069 sets and the SPEC-072 records are unchanged.
The T001 guidance change ships in the next alpha. New records use the SPEC-071
record schemas and a new set version `spec078-held-out-v2`.
