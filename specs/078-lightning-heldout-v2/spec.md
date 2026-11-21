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
  guidance (2026-11-18); T001 narrowed the rule (PR jayanez/agent-braid#1445,
  merged as `08bbffa2`).
- **No power.** With 10 prompts the Wilson intervals of 24/30 (0.63–0.90) and
  25/30 (0.66–0.93) overlap almost entirely, and three repetitions of the same
  prompt add little independent information. The 2026-11-20 research report
  estimates that detecting a 10–15 point paired gain with McNemar's test needs
  about 77–107 prompts (its own calculation, not reproduced here).
- **Other failures are not instrument defects.** Re-scoring the stored BL.2
  rollouts and the SPEC-069 T010 evidence
  (`specs/069-aim-request-authoring/evidence/native-runs-t010-heldout-final*.json`;
  T002 commits a derived receipt for the BL.2 runs) showed that HELD-02 and HELD-06 failed because the
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
  (SPEC-073 owns promotion; the owner decides). SPEC-073 `build_record` requires
  SPEC-072 H1 `supported`, so a supported H-G2 cannot feed promotion without a
  SPEC-073 amendment or an explicit owner decision.
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
  too broad. T001 (merged) changed it to say the dependency alone orders the
  units and a `read` is declared only when the unit uses the other unit's file
  content. The
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
  acceptance statistics of REQ-008 replace D4 as the primary rule for v2; the
  count of prompts valid in all 3 repetitions (D4's first-attempt count, equal
  to pass^3 at first attempt) is reported as secondary.
- **P3 — One test pass per arm.** The test split is eyes-off: it is opened only by
  the held-out command after the protocol freeze, and each arm (A0; the Gate 2
  candidate if Gate 2 runs) is scored on it once. If an arm's result is
  invalidated (an `instrument` finding of REQ-006 or a canary hit), the set gets
  a new version, is re-frozen, and that arm runs once on the new version; the
  invalidated run stays in the record.

Owner decisions for the protocol (decided 2026-11-20 and 2026-11-21; the protocol freeze, T003,
records them):

- **OD-1 — A0 threshold.** A test prompt *passes* when at least 2 of its 3
  repetitions are valid at first attempt; A0 *meets* the threshold when the
  Wilson 95 % lower bound of the share of passing prompts is at least 0.80
  (at least 88/100; 87/100 gives 0.790), every class has at least half of its
  test prompts passing (added 2026-11-20: Gate 0 showed that a host following
  the old HELD-04 read rule, otherwise perfect, scores 90/100, lower bound
  0.826, and would pass on the share alone), and no prompt is 0/3 after the
  transcript review of REQ-006.
- **OD-2 — Split sizes.** Feedback 24, validation 40, test 100 prompts,
  3 repetitions on validation and test. Gate 1 costs 300 rollouts. The Gate 2
  ceiling is 1056 rollouts (OD-4).
- **OD-3 — Host and model.** `claude-code` with model pinned to
  `claude-sonnet-5-5`, subscription route, as in SPEC-072.
- **OD-4 — Gate 2 caps (decided 2026-11-21).** At most 4 rounds and at most
  400 characters changed per edit; the Gate 2 ceiling is 1056 rollouts plus 4
  reflection calls (`evaluation-protocol.md`). Every real run still needs the
  owner's yes on its rollout count.

## Requirements

- **REQ-001 — Guidance fix (prerequisite).** The analyze skill's dependency rule
  is narrowed as decided in D1, and a test pins it: the answer that follows the
  rule on HELD-04 scores valid through `analyze-work` and the scorer, and the
  answer the old rule produced does not.
- **REQ-002 — Held-out set v2.** A versioned set file holds three disjoint splits
  (`feedback`, `validation`, `test`) of cases in the SPEC-069 case format, each
  with a class label and a structured statement of the facts the prompt gives
  (units, files, effect kinds, dependencies, whether a unit uses another's file
  content, whether the user names every file). The class plan covers: disjoint
  writes; shared writes; deletes; dependency chains with content reads and
  chains without them (the expectation then has no `read`, not an optional one,
  so the old-rule answer fails); kind choice where `aim` is required although
  `units` is tempting; Git branches; and negative cases whose correct report
  contains `unknown`: units that name their fixture files but say other files
  may be touched (partial coverage), and `call`, `deploy`, `delete`,
  `transform` or `unknown` effects on named fixture paths. Every unit has at
  least one required effect on a fixture file, because the scorer refuses an
  empty declaration and any non-`repo://` resource. Each class appears in every
  split, and the `independent-candidate` share keeps every null baseline of
  REQ-005 below OD-1 on every split. Build checks: every path in `facts`
  appears verbatim in the prompt; effect kinds come from a fixed verb
  vocabulary; a content-use phrase appears exactly when a unit `uses` another's
  file. Each split has its own templates, and no 8-word normalized window of a
  validation or test prompt appears in a feedback prompt or in the skill. A
  check refuses exact and normalized-text overlap with both SPEC-069 sets.
- **REQ-003 — Reference solutions (Gate 0).** Every v2 case has a reference
  request, built by SPEC-078 code from its `facts` (including coverage), that
  `analyze-work` accepts and the scorer marks valid; a case without one blocks
  the freeze. Negative control: the complete-coverage variant of a partial
  case scores invalid.
- **REQ-004 — Guidance-literal check (Gate 0).** A deterministic follower builds,
  from each case's structured facts, the request that the analyze skill's rules
  prescribe when followed literally (kind choice, `repo://workspace/` resources,
  dependency and read rule, coverage rule). Every v2 case's follower request must
  be accepted and score valid. A pin test ties each rule the follower encodes to
  its sentence in the skill, so a guidance edit that changes a rule fails the
  check until the follower is updated.
- **REQ-005 — Null baselines (Gate 0).** These deterministic answers are scored
  once per case: no call (every case); an empty declaration (`aim` cases);
  correct effects with partial coverage, which is what kind `units` also gives
  (`aim` cases; must fail every `independent-candidate` case); over-declaration,
  a `read` of every file a dependency writes (chain cases; must fail every chain
  without a content read); a wrong base revision (Git cases). Each must fail on
  the classes listed, and none may meet the OD-1 threshold on any split.
- **REQ-006 — Zero-prompt review.** A test prompt that is 0/3 in any arm is not
  counted until its redacted transcripts (stored under SPEC-074 consent
  `redacted`, with retention covering the review; a T006 precondition) are
  reviewed and classified as `model` (counts as
  a miss) or `instrument` (the reference or expectation is wrong). An
  `instrument` finding invalidates that arm's result and requires a new set
  version; it is reported, never silently dropped.
- **REQ-007 — Protocol and freeze.** `evaluation-protocol.md` preregisters the
  splits' sha256, the class plan, OD-1 to OD-3, the analysis and stopping rules.
  The protocol, the three splits, the Gate 0 script, the v2 analysis module
  and the A0 skill bytes are frozen by hash on a `develop` commit before any rollout; every `v2-*` run
  refuses when any frozen hash differs (including the skill used by the `final`
  source) or no freeze exists.
- **REQ-008 — Gate 1: A0 on the test split.** After the freeze and the owner's
  yes for the stated rollout count, A0 (the shipped guidance including T001) runs
  once on the test split. The report gives the per-prompt results, the share of
  passing prompts with its Wilson 95 % interval, the trial-level first-attempt
  rate with a prompt-clustered standard error, the OD-1 verdict, the all-three
  count as a secondary figure, canary hits, and the run's host, model and
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
  paired per-prompt comparison of passing prompts against the Gate 1 A0 result,
  with the one-sided exact McNemar (sign) test on discordant prompts
  (candidate better, α = 0.05). No regression on v1 means the candidate passes
  at least as many v1 prompts as A0 run in the same pass. A canary hit invalidates the arm. A null or negative result
  is reported as the outcome.
- **REQ-012 — Boundaries.** No BL.2b code edits the scorer, the SPEC-069 sets or
  the shipped skill from optimizer output, calls promotion, `execute`, `recover`
  or grant paths, uses an API key, an LLM judge or a paid route, or adds a
  runtime dependency; `executionAuthorization` stays false; spend is EUR 0.

### Amendment 1 (owner decision 2026-11-21)

Gate 1 missed OD-1 on one guidance gap (`evidence/gate1-diagnosis.json`). The
owner chose to fix the skill by hand and measure it on a fresh split instead
of running Gate 2. REQ-010 and REQ-011 (T008, T009) are cancelled, not met, and
H-G2 is not tested. A narrowed optimizer scope would have been test-informed.

- **REQ-013 — Kind-selection fix.** The analyze skill states, in its
  kind-selection section, that a parallel or overlap question is never answered
  with `units` and that placeholder digests are expected for `aim`. Tests pin
  both sentences and the analyzer behaviour they describe.
- **REQ-014 — A0' on a fresh split.** A new `v3-test` split (100 prompts, the
  ten classes, new templates and seed, disjoint 8-word windows from v1, v2 and
  the skill, never built from v2 traces or prompts) passes Gate 0 before any
  rollout and is frozen with the fixed skill on a `develop` commit. The fixed
  skill runs once on it as A0' (300 rollouts, owner yes 2026-11-21), with the
  same OD-1 and zero-prompt review as Gate 1. H-A0': A0' meets OD-1 on v3-test.
  The result is one host, model and set; it is not compared statistically
  with A0 on v2-test, since the sets differ.
- The v2 freeze (`prompts/FREEZE.json`) and the Gate 1 evidence stay bound to
  the skill that was measured (`9ba3424c…`); the v3 freeze (T014) binds the
  fixed skill. v2 runs refuse the fixed skill by design.

## Success criteria

Each requirement has one acceptance scenario (SC-001 to SC-012) in
`assurance.json`, with its procedure in `validation-plan.md`. Milestone exit:
SC-001 to SC-008 and SC-012 obtained, plus SC-009 if A0 meets the threshold or
SC-010 and SC-011 if it misses (after Amendment 1: SC-013, SC-014 and SC-015). Any outcome, including a miss followed by a null
Gate 2, completes the protocol.

## Scientific boundaries

- **Hypotheses.** H-A0: the shipped guidance A0 meets the OD-1 threshold on the
  v2 test split. H-G2 (only if H-A0 is not supported): the Gate 2 candidate is
  better than A0 on the test split by the one-sided paired exact test at
  α = 0.05 without regressing on v1. Neither is a completion condition.
- **Observation contract.** One host, one model, one guidance byte string per arm,
  synthetic prompts written for this protocol, and the SPEC-069 scorer. Results
  say nothing about other hosts, models, real user requests or the semantic
  correctness of the analyzer beyond the scorer's rule.
- **Limits.** Prompts are written by the project from templates, not sampled from
  real use; class balance is a design choice; repetitions of one prompt are
  correlated, which the clustered standard error accounts for only
  approximately; the Wilson interval treats prompts as exchangeable; prompts of
  one template are clustered too, and splits use disjoint templates; the Gate 2
  test comparison pairs against A0 measured at Gate 1, so model drift between
  the two runs is not controlled.

## Compatibility

Additive. The scorer, the SPEC-069 sets and the SPEC-069/072 evidence are
unchanged; T001 froze their assurance records historical at `3299ade8`. The
T001 guidance change ships in the next alpha. New records use the SPEC-071
record schemas and a new set version `spec078-held-out-v2`.
