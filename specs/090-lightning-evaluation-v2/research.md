# Research: SPEC-090

Sources are labelled as in the [T008 diagnosis](../079-kind-choice-tool-fix/evidence/t008-diagnosis-and-strategy-review.md):
**repo**, **paper** (read), **abstract** (abstract only), **own calculation**. Preprint claims are leads.

## R1 — Why exact bounds

Decision: exact Clopper–Pearson. The current gate uses Wilson with z = 1.96, which is a one-sided 97.5 %
bound with no coverage guarantee; an exact bound is preregisterable (own calculation, diagnosis §3.2).
Alternative: Wilson at z = 1.645 (rejected: still no guarantee). Limit: exactness holds for the binomial
model, not for template clustering, which REQ-033 simulates.

## R2 — All-fail bound replaces "no prompt is 0/3"

Decision: bound θ = E[(1−p)³], with p a prompt's per-repetition probability of a valid first attempt.
The 0/3 count is binomial in θ when prompts are independent and
repetitions are independent given p (own derivation). With n rollouts per item only moments up to degree n
are identified (2609.09245, paper; 2610.04135, minimax barrier), so θ is identified and a share of prompts
below a threshold is not. The earlier rule "no prompt is 0/3" is therefore already an all-fail test: at
α = 0.05 and n = 100 it equals τ in [0.0295, 0.0466). OD-2 makes τ explicit; values at or above 0.075 pass
v3 (two 0/3 prompts, bound 0.0616) and values at or above 0.0757 also pass v2 (three, bound 0.0757), each
with the `units` defect present. The rule did not fail on noise: the v2 and v3 0/3 prompts were deterministic
`units` choices reviewed as `model` and 25 to 100 times more frequent than independence predicts (repo).
Exact 95 % upper bounds for 0 to 4 zero-prompts in 100: 0.0295, 0.0466, 0.0616, 0.0757, 0.0892 (own
calculation).

## R3 — Three repetitions

Decision: keep 3. Extra rollouts of one prompt saturate at 1/ρ effective samples; with a per-prompt cost the
optimum is n* = √((c_p/c_r)(1−ρ)/ρ) (2611.26592, paper). With ρ = 0.41 to 0.52 and c_p/c_r of 6 to 10, n*
is near 3 (own calculation). Limit: the cost ratio is an assumption; the gate A noise pilot (REQ-032) measures ρ.
Alternative: 300 × 1 (rejected: changes the estimand to E[p]; would have passed v3 at 272/300 while losing
the per-prompt signal).

## R4 — Paired selection on a fixed slice

Decision: pair. Pairing alone gives about 2.25× in sample size; the "3 to 6×" figure needs averaging over
repeated runs too (2512.21326, paper). Five-case minibatches support no test (own calculation). SySRs
(2606.07726, paper) was shown on deterministic scores without comparison to racing or covariance-adaptive
best-arm identification (2306.02630), so the rule is chosen by simulation (OD-11). Near ties need samples
growing as 1/gap² (gap: the true difference between candidates) under any allocation.

## R5 — Audit set

Decision: an audit set never used for selection. The winner's curse is real at small validation sizes: GEPA
with 16 validation items reported +38.8 against +19.2 held out, from an instrumented follow-up, not the
preregistered part (2610.09239, paper). A 64-item audit gives RMSE near 6 points, 128 near 4.5 (same source).

## R6 — Thompson Sampling not adopted

Recorded in ADR 0046. Adaptive data bias arm means and can double false-positive and false-negative rates
(1905.11397, 2103.12198, abstracts); the pools are small and near-tied.

## R7 — Optimizer provenance

The vendored APO comes from agent-lightning's `v0.x` branch, without development since January 2026; v1.x
is open-weight RL (upstream repository). At budgets of a few hundred rollouts, generate-and-select is
competitive (2610.05671, 2611.22605, abstracts). GEPA and APO stay for the skill body with corrected
selection (REQ-019).

## R8 — Sequential gate (OD-12)

A sequential prompt-level gate with a prefixed random order is estimated to need 35 to 45 % fewer prompts
(review, lead, not verified here). Not adopted by default.
