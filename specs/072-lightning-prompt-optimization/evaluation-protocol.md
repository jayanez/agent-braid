# SPEC-072: Evaluation protocol (preregistration)

Status: draft. This file is frozen by sha256 (REQ-001) after owner review and
before any held-out rollout. Any later change is a deviation, recorded with a
reason, and the original hash stays in the record.

## Hypothesis

**H1.** An optimized `agent-braid-analyze` guidance (best APO or best GEPA
candidate, selected on the development set only) meets D4 on the frozen SPEC-069
held-out set in each required host where the T010 baseline missed D4.

D4 is the SPEC-069 criterion as implemented by the frozen
`scripts/spec069_scoring.py` (per host: at least 8 of 10 prompts valid on the
first attempt and 10 of 10 within one retry, pooled over repetitions as
`summarize` defines).

## Arms

| Arm | Candidate | Selection |
|---|---|---|
| A0 baseline | T010 baseline guidance (SPEC-071 seed) | none |
| A1 APO | best APO candidate | development score, P2 rule |
| A2 GEPA | best GEPA candidate | development score, P2 rule |

## Data

- Development: `specs/069-aim-request-authoring/prompts/development.json`
  (optimizer-visible).
- Held-out: `specs/069-aim-request-authoring/prompts/held-out.json`, hash checked
  against `FREEZE.json` (never optimizer-visible).
- Required hosts: per OD-2, default `claude-code` and `opencode`.
- Repetitions: 3 per prompt per host per arm (per OD-1).

## Budgets

| Item | Cap |
|---|---|
| development rollouts per arm | 120 (`budget.maxRollouts`) |
| optimizer calls per arm | 40 (`budget.maxOptimizerCalls`) |
| APO rounds | 3 |
| GEPA rounds | 3 |
| held-out runs per arm | 1 |
| extra cash | EUR 0 |

## Stopping rules

A run stops at the first of: a budget cap; a SPEC-071 quota stop; no
development improvement for 2 consecutive rounds; any contamination or
paid-route refusal. APO stops at 3 rounds because ProTeGi-style optimization
overfits after about 3 steps. A quota stop pauses; resumption continues the
same run with the same seeds.

## Contamination controls

- The optimizer never receives held-out prompts, ids, transcripts or rewards.
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
3. Decision rule: H1 is supported if, in every required host where A0 misses
   D4, at least one of A1 or A2 meets D4. Otherwise H1 is not supported.
   Interval overlap and the sign test are reported but do not change the rule.
4. Canary hits and schema validity are reported per arm; any canary hit in a
   held-out run invalidates that arm's result.
5. No other outcome measure, subset or host is used to claim support.

## Outcome statement

A null or negative result completes this protocol. It is reported with the
same detail as a positive result and does not justify changing the held-out
set, D4 or this protocol after the fact. Results describe the observed host
versions, models and prompt sets only.
