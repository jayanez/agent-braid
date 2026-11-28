# SPEC-091 evaluation protocol (draft skeleton): pilots, 2×2 factorial and gate B

Status: draft, not approved and not frozen. Bracketed values are open owner decisions of spec.md. Each real
run below has its own freeze (labels, items, builds, seed, this protocol's section) on a `develop` commit
and its own owner yes. No rollout precedes the simulation record (T007).

## Common to every run

- Host `claude-code`, model pinned, host CLI pinned with auto-update off, subscription route, EUR 0.
- Laboratory: the gate B profile with [OD-5] tools and pinned co-installed skills; `configDigest` recorded.
- Items: labelled `tool-necessary`, `tool-beneficial` or `tool-unnecessary` by [OD-2] before any rollout;
  near-miss items included; label record frozen by sha256. Spent v4 prompts only as [OD-1] allows.
- Observation: whether `analyze-work` was called in the rollout (transcript tool names); for calls,
  `validFirstAttempt` from the unchanged SPEC-069 scorer as a secondary measure. Missing results are
  reported and counted as non-calls. No LLM judge.
- Drift: SPEC-090 controls (versions per rollout, A/A anchors, seeded interleaved blocks, re-baseline).

## Noise pilot (T008)

Fresh development prompts; A/A pairs of the current build and two candidate arms. Outputs: within-prompt
correlation, candidate disagreement rate, A/A differences, each with an interval, in the SPEC-090 input
format. Descriptive.

## Development factorial (T009, H3)

2³ cells: product name (present, absent) × form (directive, question) × completeness sentence (present,
absent); [OD-6] prompts per cell. Per-cell invocation rates with exact intervals; descriptive; not a gate.

## 2×2 factorial (T011, T012; H1, H2)

Description (current, use-case-first) × hook (absent, present with the [OD-4] text). [OD-7] rollouts per
cell and metric; arms interleaved in seeded randomized blocks. Report per cell: recall on necessary and
beneficial items, false-positive rate on unnecessary and near-miss items, each with an exact bound; main
effects and the interaction with the test chosen by T007. Criterion to proceed to a held-out: [OD-9].

## Gate B held-out (T014, T015)

A fresh labelled set frozen and scored once, with a labelled development twin and the SPEC-090 tripwire.
Gate met when the recall lower bound is at least [OD-3] and the false-positive upper bound is at most
[OD-3], at α = SPEC-090 [OD-1].

## Stopping rules

- Each set is scored once; quota stops resume only with `--resume` on the same frozen bytes.
- A canary hit or a host or model change invalidates the session.
- Null, negative and invalidated results are valid outcomes and are recorded.
