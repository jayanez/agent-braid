# SPEC-078: Evaluation protocol (preregistration)

Status: draft for owner review (T003). T005 freezes this file by sha256 on a
`develop` commit, together with the three v2 splits, the Gate 0 script and the
A0 skill bytes, before any rollout. Any later change is a deviation, recorded
with a reason, and the frozen hash stays in the record.

## Questions

- **H-A0.** Does the shipped analyze guidance (A0) meet OD-1 on the v2 test
  split?
- **H-G2** (only if H-A0 is not supported). Does the Gate 2 candidate beat A0 on
  the v2 test split without regressing on the SPEC-069 v1 held-out set?

Neither is a completion condition. A supported, unsupported or invalidated
result completes the protocol.

## Fixed inputs

| Input | Value |
| --- | --- |
| Set | `specs/078-lightning-heldout-v2/prompts/{feedback,validation,test}.json` (24 / 40 / 100 cases, ten classes in every split), built by `scripts/spec078_build_set.py` |
| Scorer | `scripts/spec069_scoring.py`, unchanged; a trial is valid when `score_case(...)["validFirstAttempt"]` is true |
| Fixture | `scripts/spec069_fixture_workspace.py`, unchanged |
| Gate 0 | `scripts/spec078_gate0.py` passes on the frozen bytes |
| A0 | `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md` at the freeze commit (includes the HELD-04 rule fix #1445 and the coverage sentence fix #1461), packaged by the runner's `final` source |
| Host and model | `claude-code`, model pinned to `claude-sonnet-5-5`, subscription route only (OD-3) |
| Repetitions | 3 on validation and test; 1 on feedback |

## OD-1 (acceptance rule for an arm on a split)

1. A prompt **passes** when at least 2 of its 3 repetitions are valid at first
   attempt.
2. The arm **meets OD-1** when all of these hold:
   - the Wilson 95 % lower bound of the share of passing prompts is at least
     0.80 (on test: at least 88/100);
   - every class has at least half of its prompts passing;
   - no prompt is 0/3 after the review in step 3.
3. **Zero-prompt review.** A prompt that is 0/3 is held until its redacted
   transcripts are reviewed and classified as `model` (it counts as a miss) or
   `instrument` (its reference or expectation is wrong). The review reads only
   that prompt's transcripts. An `instrument` finding invalidates the arm's run
   on that split; the set gets a new version, Gate 0 runs again, the protocol
   is re-frozen, and the arm runs once on the new version. The invalidated run
   stays in the record.

`agent_braid/lightning_heldout_v2.analyse` implements items 1 to 3 (Gate 0 uses
the same `meets_share_and_classes` for items 1 and 2); the module is bound by the
freeze. Refusals are listed in [contracts/refusals.md](contracts/refusals.md).

## Gate 1: A0 on the test split

- **Preconditions:** the freeze exists and matches; Gate 0 passes on the frozen
  bytes; SPEC-074 content consent is `redacted`, with a retention window that
  covers the zero-prompt review; the owner said yes to 300 rollouts.
- **Run:** A0 once on `v2-test`, 100 prompts × 3 repetitions.
- **Report:** per-prompt results; passing share with its Wilson 95 % interval;
  the trial-level first-attempt rate with a prompt-clustered standard error;
  per-class passing counts; the OD-1 verdict; the count of prompts valid in all
  three repetitions (secondary); canary hits; host version, model and every
  frozen hash.
- **Outcome:** if A0 meets OD-1, H-A0 is supported and Gate 2 stays closed;
  the set becomes the regression suite (T007). Otherwise Gate 2 opens.

## Gate 2: bounded edits (only if A0 misses)

Caps: owner decision 2026-11-21, at most 4 rounds and at most 400 characters changed per edit, for a ceiling of 1056 rollouts. Every real run still needs the owner's yes on its rollout count.

- **Seed.** A0. A0 is also run once on `v2-validation` (40 × 3 = 120 rollouts);
  that score is the first incumbent.
- **Round.** Each round runs as follows:
  1. The incumbent runs on `v2-feedback` (24 × 1 rollouts).
  2. One reflection call receives the incumbent's body, the scorer's
     structured reasons for its failed feedback trials, and the buffer of
     rejected edits. It receives no transcripts, and no validation or test
     content. It returns one edit: add, delete or replace on one section of
     the skill body.
  3. The edited candidate runs on `v2-validation` (40 × 3).
  4. The edit is **kept** only if the candidate has strictly more passing
     validation prompts than the incumbent. Otherwise it goes to the rejected
     buffer.
- **Edit limits.** At most 400 characters changed per round. The
  front matter is fixed. The body may not exceed A0's length by more than
  **15 %**. Every kept candidate has a readable diff against A0.
- **Stopping.** The arm stops at the first of:
  - 4 rounds;
  - 3 consecutive rejected edits;
  - a SPEC-071 quota stop, which ends the run; it resumes only by an explicit
    `--resume`;
  - a canary hit, which invalidates the arm.
- **Final evaluation.** The last kept candidate runs once on `v2-test`
  (100 × 3). The same candidate and A0 then run, in the same pass, on the
  SPEC-069 v1 held-out set (2 × 10 × 3). If no edit was kept, Gate 2 reports a
  null result and runs no test or v1 rollouts.
- **H-G2.**
  - **Primary:** a one-sided exact McNemar (sign) test on test prompts whose
    pass status differs between the candidate and the Gate 1 A0 result
    (candidate better, α = 0.05).
  - **No regression:** on v1, the candidate passes at least as many prompts as
    A0 does in the same pass.
  - The candidate's OD-1 verdict on test is reported as secondary.
- **Promotion** is out of scope. The candidate is reported by hash and diff
  only (SPEC-073).

### Gate 2 budget at the decided caps

| Item | Rollouts |
| --- | --- |
| A0 on validation | 120 |
| Per round: feedback 24 + validation 120 | 144 × 4 = 576 |
| Final candidate on test | 300 |
| v1 control, candidate and A0 | 60 |
| **Total (upper bound)** | **1056**, plus at most 4 reflection calls |

## Contamination and integrity

- Only `v2-feedback` ever reaches a reflection call. Validation and test
  prompts, their ids, and the SPEC-069 held-out set are on the optimizer's
  denied paths. The SPEC-072 contamination scan is extended to v2 validation
  and test fingerprints (T005).
- Every `v2-*` run refuses when any frozen hash differs: the protocol, a split,
  the Gate 0 script, the v2 analysis module, or the skill used by the `final`
  source. An A0 run refuses a prebuilt plugin. A candidate is scored on
  `v2-test` once: a second, non-resumed run of the same candidate is refused.
- Every rollout checks that the skill was loaded. A rollout without it counts
  as invalid and is reported.
- No LLM judge. No API key. No paid route. `executionAuthorization` stays
  false. Extra spend is EUR 0.

## Analysis definitions

- **Wilson interval:** `spec069_scoring.wilson_interval`, z = 1.96.
- **Prompt-clustered standard error** of the trial-level rate: with
  per-prompt rates r_i over n prompts, SE = sd(r_i) / sqrt(n).
- **Exact sign test:** the binomial tail on the discordant prompts with
  p = 0.5.
- **Reported, never gating:** D4-style counts and the per-class table.

## Outcome statement (filled after the runs)

- Gate 1: H-A0 supported, not supported, or invalidated.
- Gate 2: not run, null, H-G2 supported, or not supported.

Each outcome is written with its numbers, the run ids and the frozen hashes.
Protocol adherence is reported separately from the result.
