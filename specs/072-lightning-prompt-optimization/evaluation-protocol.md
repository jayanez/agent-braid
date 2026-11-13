# SPEC-072: Evaluation protocol (preregistration)

Status: draft. This file is frozen by sha256 (REQ-001) after owner review and
before any held-out rollout. Any later change is a deviation, recorded with a
reason, and the original hash stays in the record.

## Amendment 1 (approved by the owner 2026-11-13)

Made before the freeze, so it is an amendment, not a deviation. The owner
approved it on 2026-11-13 (item 6 included) before any development rollout;
T009 freezes the amended file.

1. **A0 is the current guidance.** A0 is the `agent-braid-analyze` guidance on
   `develop` after the SPEC-069 T008 rewrite (#1314) packaged in the current
   plugin build (`spec069_native_runs` arm `final`), not the T010 guidance at
   `8f63c606` (arm `baseline`). The arms optimize this same text.
2. **New A0 development run.** A0's development scores (the seed vectors of
   both arms) come from a new SPEC-071 baseline run of the current guidance:
   development set, `claude-code`, 3 repetitions, model pinned to
   `claude-sonnet-5-5`, subscription route. The SPEC-071 T012 run
   `run-20261111T085405Z-a14514` (T010 guidance, 16/30) is context only and is
   not the seed.
3. **One required host.** The required host is `claude-code`. `opencode` is a
   declared limit: it reports no subscription credential source, so the
   SPEC-071 runner refuses it as `route-unverified` (SPEC-071 OD-2). Codex
   stays a declared SPEC-069 limit.
4. **Model pin.** Every rollout and optimizer call of A0, A1 and A2 pins
   `claude-sonnet-5-5` (`lightning run --model`, default for arms).
5. **Feasibility recomputed for one host** (table below), checked with
   `agent_braid.lightning_arm.estimate`.
6. **Exploratory arms E1 and E2 (descriptive only).** APO (E1) and GEPA (E2)
   are also run from the T010 guidance at `8f63c606` (arm `baseline` plugin
   build), seeded by the SPEC-071 T012 run `run-20261111T085405Z-a14514`, with
   the same settings, model pin, budgets per arm (120 rollouts, 40 optimizer
   calls) and stopping rules as A1 and A2. They run on the development set only,
   sequentially after A1 and A2. They do not count for H1, are not candidates
   for the held-out runs or the SPEC-049 pair, do not change A0, A1 or A2, and
   are reported in a separate descriptive table. This is fixed before any
   development rollout of any arm.

## Hypothesis

**H1.** The preregistered primary arm, the best GEPA candidate (A2), selected
on the development set only, meets D4 on the frozen SPEC-069 held-out set in
every required host where the baseline A0 misses D4 on that held-out set.
APO (A1) is a secondary arm, reported descriptively only; it cannot support
H1.

D4 is the SPEC-069 criterion as implemented by the frozen
`scripts/spec069_scoring.py` (per host: at least 8 of 10 prompts valid on the
first attempt and 10 of 10 within one retry, pooled over repetitions as
`summarize` defines).

## Arms

| Arm | Candidate | Selection |
|---|---|---|
| A0 baseline | current `develop` guidance (SPEC-069 T008 rewrite), current plugin build; new development run (Amendment 1) | none |
| A1 APO (secondary, descriptive) | best APO candidate | development score, P2 rule |
| A2 GEPA (primary, preregistered) | best GEPA candidate | development score, P2 rule |
| E1 APO, E2 GEPA (exploratory, development only; Amendment 1 item 6) | best candidate from the T010 guidance | development score, P2 rule; descriptive |

## Data

- Development: `specs/069-aim-request-authoring/prompts/development.json`
  (optimizer-visible).
- Held-out: `specs/069-aim-request-authoring/prompts/held-out.json`, hash checked
  against `FREEZE.json` (never optimizer-visible).
- Required host, fixed in advance: `claude-code` (Amendment 1). `opencode` is a
  declared limit (`route-unverified`, SPEC-071 OD-2); Codex is a declared
  SPEC-069 limit.
- Model: `claude-sonnet-5-5`, pinned for rollouts and optimizer calls.
- Repetitions: 3 per prompt per host per arm (OD-1 decided 2026-11-11: keep 10 × 3).

## Budgets

| Item | Cap |
|---|---|
| development rollouts per arm | 120 (`budget.maxRollouts`) |
| optimizer calls per arm | 40 (`budget.maxOptimizerCalls`) |
| APO rounds | 2 (feasibility table) |
| GEPA rounds | 3 |
| held-out runs per arm | 1 |
| extra cash | EUR 0 |

Budgets are per arm run: each arm (A1, A2) is a separate `agent-braid lightning
run` with its own `budget.maxRollouts` of 120 and `budget.maxOptimizerCalls` of
40. The held-out runs are separate runs and do not count against them.

### Feasibility table

Units, per arm run with the one required host (`claude-code`):

- full development evaluation of one candidate = 10 prompts × 3 repetitions ×
  1 host = 30 rollouts;
- minibatch evaluation of one candidate = 5 prompts × 1 repetition × 1 host =
  5 rollouts;
- the seed (A0) development scores come from the new A0 baseline run
  (30 rollouts, Amendment 1) and are not charged to the arm.

Preregistered parameters, which override the configuration defaults (applied
with `lightning init --beam-width --branch-factor --rounds --minibatch`):

| Parameter | Preregistered | Configuration default |
|---|---|---|
| `beamWidth` (APO) | 2 | 4 |
| `branchFactor` (APO) | 2 | 4 |
| `minibatch` | 5 prompts | 5 |
| `rounds` (APO) | 2 | 3 |
| `rounds` (GEPA) | 3 | 3 |

Resulting counts (`lightning_arm.estimate` upper bounds):

| Arm | Search | Final full evaluation | Total rollouts | Optimizer calls |
|---|---|---|---|---|
| A1 APO | round 1: 1 parent × 2 children × 5 = 10; round 2: 2 parents × 2 children × 5 = 20 | best candidate 30 | 60 | round 1: 1 × (1 critique + 2 edits) = 3; round 2: 2 × 3 = 6; ≤ 9 |
| A2 GEPA | 3 rounds × 1 child minibatch × 5 = 15 | 30 per accepted child: 30 if one child is accepted, ≤ 90 if all three | 45 to ≤ 105 | 3 reflections |

With A0 (30), one complete T009 development phase uses at most
30 + 60 + 105 = 195 rollouts and 12 optimizer calls, all within the
per-arm caps of 120 rollouts and 40 calls.

In GEPA an accepted child whose full evaluation would exceed 120 is not
evaluated: the run ends with a recorded `unit-cap` stop and the best fully
evaluated candidate (with one host this cannot happen within 3 rounds). The
configuration defaults (beam 4, branch 4, 3 rounds) bound APO at
(4 + 16 + 16) × 5 + 30 = 210 rollouts, which exceeds one 120-rollout arm
budget, so this protocol overrides them. Reaching a cap is a
recorded stop, not a deviation.

## Stopping rules

A run stops at the first of: a budget cap; a SPEC-071 quota stop; no
development improvement for 2 consecutive rounds; any contamination or
paid-route refusal. APO never exceeds 3 rounds (2 preregistered) because ProTeGi-style optimization
overfits after about 3 steps. A quota stop ends the run; the same run id,
with the same seeds, resumes only by an explicit
`agent-braid lightning run --resume <run-id>`.

## Contamination controls

- The optimizer never receives held-out prompts, ids, transcripts or rewards.
- Before BL.4 the optimizer reflects only on the content-free reward vector,
  `score_case` reasons, refusal codes and candidate text, never transcripts.
- Optimizer calls run in the SPEC-071 disposable profile and OS sandbox with no
  path to `held-out.json`, scoring sources or `.git`.
- Before every optimizer call the full input is hashed and scanned; a match
  refuses the call (`holdout-contamination`).
- SPEC-071 canaries stay active in rollouts.
- Held-out runs start only after `evidence/protocol-freeze.json` records this
  file's hash.

## Analysis plan

1. Per host and arm: D4 verdict from `summarize`; first-attempt and
   within-retry proportions with Wilson 95 % intervals (`wilson_interval`).
2. Paired comparison per host: for each held-out prompt, the count of
   first-attempt successes over repetitions in A1 and A2 versus A0; report the
   number of prompts improved, unchanged and worsened, and an exact two-sided
   sign test over improved versus worsened prompts.
3. Decision rule: H1 is supported if and only if, in every required host
   (`claude-code`; Amendment 1), A0 misses D4 on held-out and A2 (GEPA) meets
   D4. If A0 meets D4 in a required host, H1 is `not assessable` for that host
   and the overall outcome is `not assessable`, never supported. Otherwise H1
   is not supported. A1 (APO) results are descriptive and never change the
   outcome. Interval overlap and the sign test are reported but do not change
   the rule.
4. The outcome is also written as a SPEC-049 `Registration`/`EvaluationRecord`
   pair (A = A0, C = A2) for SPEC-073.
5. Canary hits and schema validity are reported per arm; any canary hit in a
   held-out run invalidates that arm's result.
6. No other outcome measure, subset or host is used to claim support.
7. Exploratory arms E1 and E2 (Amendment 1 item 6) are reported only as a
   descriptive development-set table (best candidate's development score
   against the T012 seed's), never in the decision rule.

## Outcome statement

A null or negative result completes this protocol. It is reported with the
same detail as a positive result and does not justify changing the held-out
set, D4 or this protocol after the fact. Results describe the observed host
versions, models and prompt sets only.
