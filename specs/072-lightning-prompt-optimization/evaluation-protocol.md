# SPEC-072: Evaluation protocol (preregistration)

Status: draft. This file is frozen by sha256 (REQ-001) after owner review and
before any held-out rollout. Any later change is a deviation, recorded with a
reason, and the original hash stays in the record.

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
| A0 baseline | T010 baseline guidance (SPEC-071 seed) | none |
| A1 APO (secondary, descriptive) | best APO candidate | development score, P2 rule |
| A2 GEPA (primary, preregistered) | best GEPA candidate | development score, P2 rule |

## Data

- Development: `specs/069-aim-request-authoring/prompts/development.json`
  (optimizer-visible).
- Held-out: `specs/069-aim-request-authoring/prompts/held-out.json`, hash checked
  against `FREEZE.json` (never optimizer-visible).
- Required hosts, fixed in advance: `claude-code` and `opencode` (Codex is a
  declared SPEC-069 limit).
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

Units, per arm run with both required hosts:

- full development evaluation of one candidate = 10 prompts × 3 repetitions ×
  2 hosts = 60 rollouts;
- minibatch evaluation of one candidate = 5 prompts × 1 repetition × 2 hosts =
  10 rollouts;
- the seed (A0) development scores come from the SPEC-071 baseline run and are
  not charged to the arm.

Preregistered parameters, which override the configuration defaults:

| Parameter | Preregistered | Configuration default |
|---|---|---|
| `beamWidth` (APO) | 2 | 4 |
| `branchFactor` (APO) | 2 | 4 |
| `minibatch` | 5 prompts | — |
| `rounds` (APO) | 2 | 3 |
| `rounds` (GEPA) | 3 | 3 |

Resulting rollout counts:

| Arm | Search | Final full evaluation | Total | Optimizer calls |
|---|---|---|---|---|
| A1 APO | round 1: 1 parent × 2 children × 10 = 20; round 2: 2 parents × 2 children × 10 = 40 | best candidate 60 | 120 | 2 rounds × (≤ 2 critiques + ≤ 4 edits) ≤ 12 |
| A2 GEPA | 3 rounds × 1 child minibatch × 10 = 30 | the first accepted child 60 | ≤ 90 | 3 reflections |

In GEPA a second accepted child whose full evaluation would exceed 120 is not
evaluated: the run ends with a recorded `unit-cap` stop and the best fully
evaluated candidate. The configuration defaults (beam 4, branch 4) need
16 children × 10 = 160 rollouts in one APO round, which exceeds one
120-rollout arm budget, so this protocol overrides them. Reaching a cap is a
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
   (`claude-code`, `opencode`), A0 misses D4 on held-out and A2 (GEPA) meets
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

## Outcome statement

A null or negative result completes this protocol. It is reported with the
same detail as a positive result and does not justify changing the held-out
set, D4 or this protocol after the fact. Results describe the observed host
versions, models and prompt sets only.

## Proposed amendment A-1: hosts (draft, pending owner review)

Status: proposed 2026-11-13, not accepted. The sections above stay as written
until the owner accepts this amendment; it is not part of any freeze until then.

**Reason.** SPEC-071 OD-2: OpenCode reports no subscription credential source,
so every OpenCode rollout or optimizer call is refused as `route-unverified`
and the SPEC-071 baseline run `run-20261111T085405Z-a14514` (the A0 seed) has
`claude-code` only. Keeping `opencode` as a required host would make H1
`not assessable` by construction.

**Changes if accepted.**

1. Data: required hosts become `claude-code` only. `opencode` becomes a
   declared limit, like Codex (no verified subscription credential source;
   refusal code `route-unverified`).
2. Analysis plan item 3: "in every required host (`claude-code`, `opencode`)"
   reads "in the required host (`claude-code`)". The outcome describes Claude
   Code only and claims nothing for OpenCode.
3. Feasibility table, recomputed for one host (units: full evaluation =
   10 × 3 × 1 = 30 rollouts; minibatch = 5 × 1 × 1 = 5 rollouts). Upper bounds
   from `agent_braid.lightning_arm.estimate` with the preregistered
   parameters and caps of 120 rollouts and 40 optimizer calls:

   | Arm | Search | Full evaluations | Upper bound | Optimizer calls |
   |---|---|---|---|---|
   | A1 APO | round 1: 1 parent × 2 children × 5 = 10; round 2: 2 parents × 2 children × 5 = 20 | best candidate 30 | 60 | 1 × 3 + 2 × 3 = 9 |
   | A2 GEPA | 3 rounds × 1 child × 5 = 15 | every accepted child 30 (worst case 3 × 30 = 90) | 105 | 3 |

   Both arms stay inside the 120-rollout cap, so the GEPA `unit-cap` stop is no
   longer expected; it remains the rule if reached. Budgets, parameters,
   repetitions and stopping rules are unchanged.

**Unchanged.** A0 is the T010 baseline guidance at commit `8f63c606`
(SPEC-069 `BASELINE_COMMIT`, plugin arm `baseline`). Arms start from it
(`lightning run --source baseline`): the seed skill text is read from that
commit and candidate sub-runs use the `baseline` plugin, so a candidate
differs from A0 only in its skill text. The host model is pinned to
`claude-sonnet-5-5` (the T010 and A0 seed model). Re-scoring the A0 seed run
with the current `scripts/spec069_scoring.py` gives 16 of 30 first-attempt
successes and 21 of 30 schema-valid, identical to the recorded run.
