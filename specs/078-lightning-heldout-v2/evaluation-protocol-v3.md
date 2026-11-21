# SPEC-078 Amendment 1: evaluation protocol for A0' on v3-test

Status: owner decision 2026-11-21 (option 4). The v3 freeze (T014) binds this
file, the split, its builder and the shared fact generator by sha256 on a `develop` commit; it does not change
[evaluation-protocol.md](evaluation-protocol.md), which stays bound by the v2
freeze.

## What is measured

A0' is the analyze skill after the T012 kind-selection fix. It runs once on
the fresh `v3-test` split (100 prompts × 3 repetitions = 300 rollouts) on
`claude-code` with `claude-sonnet-5-5`, on the subscription route, at EUR 0.

## The split

`v3-test.json` is built by `scripts/spec078_build_v3.py` (seed 3078) with the
v2 class plan, fact generator and expectation rule, and with its own templates.
The templates are new wording, not derived from v2 prompts or traces; the
author had read three v2-test prompts and their traces during the Gate 1
review, so independence rests on the mechanical checks below. The builder
refuses a fact pattern used by a v2 split and any 8-word window shared with a
v2 split, a SPEC-069 prompt or the analyze skill. Gate 0 (references, the
literal follower and the null baselines of `scripts/spec078_gate0.py`) must
pass on it before any rollout.

## Acceptance and review

OD-1 and the zero-prompt review are those of
[evaluation-protocol.md](evaluation-protocol.md), computed by
`agent_braid/lightning_heldout_v2.analyse`. A 0/3 prompt is held until its
redacted transcripts are reviewed and classified as `model` (counts as a miss)
or `instrument` (invalidates the run and requires a new split version).
H-A0': A0' meets OD-1 on `v3-test`.

## Boundaries

- The split is scored once per candidate; a second non-resumed run is refused.
- `v3-test` is on the optimizer's denied paths, carries the held-out canary and
  is in the contamination fingerprints.
- The result is one host, model and split. It is not compared statistically
  with the Gate 1 result on `v2-test`, since the splits differ, and it is not
  H-G2 evidence.
- No LLM judge, no API key, no paid route; `executionAuthorization` stays false.
