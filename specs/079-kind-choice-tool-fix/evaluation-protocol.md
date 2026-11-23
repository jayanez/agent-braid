# SPEC-079 evaluation protocol: fixed tool on held-out v4

Status: approved as written by the owner on 2026-11-23 ([record](https://github.com/jayanez/agent-braid/pull/1629#issuecomment-7116233460)). T007 freezes this file, the
split, its builder, the Gate 0 report and the pinned plugin commit by sha256 on a `develop` commit. No v4
rollout may start before that freeze and the owner's yes on 300 rollouts (T008), which is a separate
decision. Owner decisions OD-A to OD-E apply; the OD-E thresholds were approved as proposed on 2026-11-23
([record](https://github.com/jayanez/agent-braid/pull/1625#issuecomment-7116233134)).

## What is measured

One arm: the plugin at a pinned unreleased commit that contains the T001 refusal and the T002
descriptions (OD-D), with the analyze skill as shipped at that commit. It runs once on `v4-test`
(100 prompts × 3 repetitions = 300 rollouts) on `claude-code` with model `claude-sonnet-5-5`, on the
subscription route, at EUR 0 (OD-C). The SPEC-071 runner executes it over the SPEC-069 fixture
workspace. Each rollout is scored with the unchanged `scripts/spec069_scoring.py`.

## The split

`prompts/v4-test.json` is built by `scripts/spec079_build_v4.py` (seed 4079). Class plan: disjoint-parallel
20, overlap-write 15, dependency-order 15, read-only-shared 10, kind-choice-probe 20, analyze-tempting 10,
git-branch 10. Facts and expectations come from the SPEC-078 fact generator and footprint rule. The
templates are new. The builder refuses any fact pattern used by a SPEC-078 split, duplicate prompts, and
any 8-word normalized window shared with SPEC-069 prompts, SPEC-078 splits, the analyze skill or the
SPEC-079 tool texts. The authoring exposure is recorded in [research.md](research.md) R7.
[Gate 0](evidence/gate0-v4-report.json) passed with no rollouts: every reference and literal-follower
request is valid, and every null baseline misses OD-1.

## Gate (OD-B: SPEC-078 OD-1, unchanged)

1. A prompt passes when at least 2 of its 3 rollouts are `validFirstAttempt`.
2. The gate is met when the Wilson 95 % lower bound of the passing share is at least 0.80 (88/100) and
   every class has at least half of its prompts passing.
3. After the zero-prompt review, no prompt is 0/3.

`agent_braid/lightning_heldout_v2.analyse` computes items 1 to 3. A missing rollout result (runner
error, quota stop, timeout) counts as a failed rollout.

## Zero-prompt review

Each 0/3 prompt is held until the owner reviews its redacted transcripts. The owner classifies the prompt
as `model` (it counts as a miss) or `instrument` (its reference, expectation or wording is wrong). An
`instrument` finding invalidates the run. The split then needs a new version, Gate 0 and a new freeze,
and the invalidated run stays in the record. Disagreements are recorded verbatim (T009).

## Hypotheses (preregistered; none is a completion condition)

- **H1** — The share of attempts that use `kind: units` on the 20 kind-choice-probe prompts (60 rollouts)
  and on all 300 rollouts is below the v3-test rate of 19/300. This comparison is descriptive only: the
  prompts and class mix differ, so there is no paired test.
- **H2** — The arm meets the gate on `v4-test`.
- **H3** — Rollouts that call the `analyze` tool and never call `analyze-work` number fewer than 6 of 300.
  This is descriptive against v3-test, reported overall and for the analyze-tempting class.
- **H4** — The share of prompts passing on `validWithinRetry` (the first attempt, or one retry after a
  refusal; unchanged scorer) is at least the first-attempt passing share plus the prompts that the
  redirect rescued. This is secondary and descriptive. A refused `units` first attempt fails
  `validFirstAttempt` by construction, so the gate credits the fix only when the description already led
  to `aim`.

## Report (REQ-009)

The report gives per-prompt results; the passing share with its Wilson 95 % interval; the trial-level
first-attempt rate with a prompt-clustered standard error; per-class passing counts; the OD-1 verdict; the
`validWithinRetry` passing share (H4); `units` usage per class and overall (H1); the number of
`units-cannot-answer-independence` refusals and how many were followed by a valid `aim` retry; and the
`analyze`-only rollouts (H3). It also records canary hits, the host version, the model, the pinned plugin
commit and every frozen hash. Tool kinds come from transcript counts; no LLM judge is used.

## Stopping rules

- The split is scored once. A second non-resumed run on v4 is refused, and v4 is not reused for a second
  arm (REQ-010).
- A SPEC-071 quota stop ends the run. It resumes only with an explicit `--resume` on the same run
  directory and the same frozen bytes.
- A canary hit invalidates the run. It is recorded, not retried on v4.
- A missed gate, a null difference or an invalidated run is a valid outcome. It is recorded in spec.md,
  and the run is not repeated.

## Real-session shadow check (REQ-012, OD-E; thresholds approved 2026-11-23)

Before release (T010), the pinned build runs in the owner's real `claude-code` sessions. The window lasts
at least 14 days and covers at least 30 `analyze-work` calls. The check is read-only. It uses only local
telemetry cells and, from host transcripts, the tool names, the `kind` argument, the envelope status and
the refusal code. It reads no prompt or file content and spends no quota.

| Statistic | Definition | Pass |
| --- | --- | --- |
| S1 | `ok` share of `analyze-work` calls, Wilson 95 % | lower bound ≥ 0.70 |
| S2 | `units-cannot-answer-independence` refusals followed by an `aim` call in the same session | ≥ 80 % recovered |
| S3 | sessions that call `analyze` and never `analyze-work`, among sessions with any Agent Braid analysis call | ≤ 5 % |
| S4 | `analyze-work` `error` outcomes | 0 |

Fewer than 30 calls is `inconclusive`, and the release stays blocked. A failed or inconclusive check is
recorded and is not retried on the same window.

## Boundaries

- One host, model, split, tool build and skill. v4 results are not paired with v3-test.
- Frozen SPEC-069 and SPEC-078 files, the scorer and the earlier splits are read only.
- No LLM judge, API key or paid route. `executionAuthorization` stays false.
- The tool change ships only in the alpha after the result is recorded (OD-D).
