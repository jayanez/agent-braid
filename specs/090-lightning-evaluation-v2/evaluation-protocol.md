# SPEC-090 evaluation protocol (draft skeleton): gate A and paired selection

Status: draft, not approved and not frozen. Every bracketed value is an open owner decision of spec.md and
stays open until T001. T016 completes this file and freezes it by sha256 on a `develop` commit. No real
rollout may start before that freeze, the committed simulation record (T004 to T007, T019) and the owner's
yes (T017), which is a separate decision.

## Simulation stage (no quota)

Before any real run, `scripts/spec090_simulate.py` records, with seeds:

1. **Gate A errors (H3).** Type I error at the 0.80 boundary and power at chosen alternatives for each α of
   [OD-1], with the class rule.
2. **All-fail coverage (H2).** Coverage of the exact upper bound over a grid of θ, and the detection rate of a
   deterministic defect affecting 2 to 3 % of prompts, for each τ of [OD-2].
3. **Clustering.** Items 1 and 2 are repeated in a template-clustered scenario (prompts of one class share
   a latent effect on p, the per-repetition probability of a valid first attempt) over a grid of
   between-class variances; the success criterion is the [OD-15] tolerance.
4. **Selection (H1).** Known-p candidate pools of size [OD-7] with within-prompt correlation from 0.41 to
   0.81, then the noise-pilot value: rate of picking an ε-good candidate for each rule and test of [OD-11]
   against top-k on n = 5 independent means; sizing uses [OD-3] δ and Δ.
5. **Replay.** A journal replayed twice yields identical decisions and hashes.

A simulation result that contradicts H1, H2 or H3 is recorded and blocks the real stage until the design
changes.

## Gate A (real stage, after T016)

- Split: a fresh split of [OD-13] prompts that name the product, with a reserve of [OD-8] and a
  development twin of [OD-9]; leakage checks against SPEC-069, v2, v3 and v4 (REQ-024).
- Host `claude-code`, model pinned, host CLI pinned with auto-update off, subscription route, EUR 0.
- Three repetitions per prompt (REQ-007). Missing results count as failed repetitions.
- Gate 0: references valid, null baselines below the gate, invocation tripwire on the twin at [OD-9].
- Gate met when all hold:
  1. exact one-sided Clopper–Pearson lower bound of the passing share at α = [OD-1] is at least 0.80;
  2. exact upper bound of the all-fail rate at α = [OD-1] is at most τ = [OD-2];
  3. every class has at least half its prompts passing;
  4. no 0/3 prompt is unreviewed; `instrument` prompts replaced within the cap [OD-8].

## Selection (development use)

Candidates are compared on one fixed slice sized from the gate A noise pilot of [OD-14] by the plan.md
formula with [OD-3] (δ and Δ) and [OD-4],
synchronized rounds, the rule and test of [OD-11], the incumbent kept unless the margin is met, and the
winner reported on the audit set of [OD-5].

## Report

Per-prompt results; both exact bounds; per-class counts; the verdict (`met`, `missed`, `held`,
`invalidated`); replacements; `configDigest`; per-rollout versions; tool-call and skill-invoked counts;
A/A anchor results; every frozen hash. No LLM judge.

## Stopping rules

- A split is scored once; v2, v3 and v4 are never used as gate A held-out splits.
- A quota stop ends the run; it resumes only with `--resume` on the same frozen bytes.
- A host or model change refuses the session and requires a re-baseline.
- A canary hit invalidates the run. A missed gate or an invalidated run is a valid outcome.
