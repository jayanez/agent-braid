# ADR 0046: Lightning evaluation design (best-arm selection, gates A and B, identified estimands)

- **Status:** Proposed — (2026-11-28). Not accepted, and it implements and runs nothing. The owner
  approved the corrected strategy on 2026-11-28 as a planning decision; that approval has no committed
  record yet, and SPEC-090 T001 and SPEC-091 T001 record it. The founder accepts or rejects this ADR in
  those reviews. Every numeric parameter other than those inherited from SPEC-078 OD-1 and the approved
  strategy (the 2-of-3 majority, 3 repetitions and the 0.80 threshold) is an open owner decision (OD) in
  those specifications, not a value fixed here.
- **Date:** 2026-11-28
- **Deciders:** Juan Antonio Yáñez García (founder)
- **Constitutional articles:** 0, 9, 12, 13, 14, 19, 20, 21, 23
- **Specifications:** [SPEC-090](../../specs/090-lightning-evaluation-v2/spec.md) (statistical machinery and gate A), [SPEC-091](../../specs/091-invocation-gate/spec.md) (gate B)
- **Relation to other ADRs:** builds on [ADR 0039](0039-braid-lightning-boundary.md) (unchanged) and [ADR 0040](0040-braid-lightning-mit-vendoring.md); [ADR 0042](0042-braid-lightning-local-weight-training.md) stays deferred. [ADR 0038](0038-analyze-work-request-contract.md) needs an amendment only if SPEC-091 changes tool `_meta` or MCP server instructions (SPEC-091 OD-10).

## Context

SPEC-079 T008 ran a frozen 100-prompt held-out set (v4, 3 repetitions, 300 rollouts) and passed 17 of
100 prompts against a gate of 88. The model called `analyze-work` in 53 of 300 rollouts, and 51 of
those 53 first requests were valid. No v4 prompt names the product; every v3 prompt does. The
[T008 diagnosis](../../specs/079-kind-choice-tool-fix/evidence/t008-diagnosis-and-strategy-review.md)
records that seven things changed between v3 and v4, so the missing product name is not isolated.

Two different endpoints were measured as one:

- **Authoring validity:** given a request that names the product, is the first `analyze-work` request valid?
- **Unprompted invocation:** without the product name, does the model reach for the tool at all?

They have different levers. An adversarial and counterfactual review of the earlier "Lightning evaluation
v2" plan found, in this repository:

- the optimizer mutates only the skill body (`agent_braid/lightning_resources.py`; `target.kind` is
  `('skill',)` in `agent_braid/lightning_config.py`) and its development set is fixed;
- the `analyze-work` definition sits near the ADR 0038 D12 cap (about 1,499 of 1,500 tokens);
- `parallel` above 1 is accepted by the configuration but the runner is sequential;
- the lab disables `Read`, `Grep`, `Glob` and `Bash` and installs one plugin, so recall and false
  positives there do not describe a session with competing tools and skills;
- an `instrument` finding invalidates a whole run under the SPEC-079 protocol and cannot replace single prompts.

It also found two statistical pieces unsound: with p a prompt's per-repetition probability of a valid
first attempt, the share of prompts with p below a threshold is not identifiable from a few repetitions (only moments up to degree n are, with n rollouts per item),
and five-case minibatches are underpowered: a two-sided exact McNemar test cannot reach 0.05 (smallest
p-value 0.0625), a one-sided exact sign test reaches 1/32 only when all five pairs are discordant in one
direction, and McNemar's n counts discordant pairs only.

## Decision (proposed)

1. **Two gates, two estimands.**
   - **Gate A (authoring validity).** Prompts that name the product. Unit: the prompt. Outcome: the prompt
     passes when at least 2 of its 3 repetitions are valid first attempts. The primary estimand is the
     share of prompts that pass (one binary result per prompt, treated as independent across prompts).
   - **Gate B (unprompted invocation).** Prompts that do not name the product. Every item MUST carry a label
     fixed before measurement (owner decision OD-B1, stated on 2026-11-27; it has no committed record
     yet, and SPEC-091 T001 records it): `tool-necessary` (the needed fact is
     not in the prompt, for example repository state), `tool-beneficial` (the product gives a verified,
     auditable artifact the prose answer does not), or `tool-unnecessary`. Recall is measured and bounded
     on the first two labels together; the false-positive rate is measured and bounded on
     `tool-unnecessary` items, including near-misses. The item, not the rollout, MUST be the unit of both bounds,
     because rollouts of one prompt are correlated (ANOVA ICC of per-prompt pass counts 0.81 on v4); the per-item outcome is an open decision
     (SPEC-091 OD-17). The two bounds MUST NOT be combined into one score.
2. **Identified estimands only.** Gate A MUST report:
   - an **exact one-sided Clopper–Pearson lower bound** on the share of passing prompts, at an α declared
     before measurement (the Wilson interval with z = 1.96 is a one-sided 97.5 % bound without a coverage
     guarantee and MUST NOT be the verdict statistic);
   - an **exact upper bound on the all-fail rate** E[(1−p)³], where p is a prompt's per-repetition probability of a valid first
     attempt. The 0/3 count is Binomial(n, θ), so the earlier rule "no prompt is 0/3" is already a test of
     this functional: at α = 0.05 and n = 100 it equals an all-fail threshold τ in [0.0295, 0.0466). Making
     τ explicit means the owner knowingly keeps or loosens that rule (SPEC-090 OD-2); thresholds at or above
     0.075 are excluded because they pass v3 (and from 0.0757 also v2) with the `units` defect present. Replaced prompts MUST count
     as 0/3 in the verdict. Each 0/3 prompt is still reviewed by the owner as `model` or `instrument`; `instrument`
     prompts are replaced from a reserve frozen before the run, within a preregistered cap. A share such as
     "prompts with p below c" (for a cutoff c) MUST NOT be reported as a gate quantity.
   - The class rule MUST be kept.
   The gate is conjunctive, so a false `met` stays at or below α by the intersection–union principle.
   Three repetitions are kept: with the measured within-prompt correlation (0.41 to 0.52) and a prompt cost
   of about 6 to 10 rollouts, the optimum is near 3 (own calculation from 2611.26592; the cost ratio is an
   assumption the noise pilot must measure).
3. **Paired selection on one fixed slice.** Candidate text artifacts MUST be compared on the same fixed slice
   of prompts, sized from a pilot (a 5-prompt slice is underpowered). Elimination pairs per-prompt valid
   rates averaged over repetitions; the final replacement test runs on a separate confirmation slice, on
   per-prompt majority pass (the gate A estimand), with Holm when several challengers reach it. Elimination MUST be synchronized (all surviving candidates see the same items per round). The
   incumbent MUST be kept unless a preregistered margin δ is met (an ε-good objective); the slice is sized for
   power at a target advantage Δ greater than δ (both open, SPEC-090 OD-3). The elimination rule is
   chosen by simulation over the 0.41 to 0.81 correlation range before the pilots, re-run with the pilot's
   parameters (SPEC-090 T019) before any selection or held-out run.
4. **Audit set.** An audit set of items (128 proposed; the size is an OD) MUST NOT be used for selection. The
   selected winner and its incumbent are each scored on it once and reported with an exact confidence
   interval, to expose the winner's curse; the audit result MUST NOT be an input to a choice.
5. **Drift controls.** The host CLI and model MUST be pinned with no auto-update; the host, model and plugin
   versions are recorded per rollout; A/A anchors (the same arm twice) run each session; arms are
   interleaved in randomized blocks; any host or model change triggers a re-baseline (the A/A pair and the twin rerun;
   sizing reruns if a pilot estimate leaves its interval). A frozen protocol pins the host and model: a
   different host or model refuses the run before any rollout without spending the split. Reports carry `configDigest`,
   per-rollout versions, the server-reported model identifier, tool-call counts and whether the skill was
   invoked.
6. **Gate 0 invocation tripwire.** Every Gate 0 of a split frozen under SPEC-090 or SPEC-091 MUST include an invocation-rate tripwire on a
   development twin of the held-out set (size: SPEC-090 OD-9, SPEC-091 OD-22), so a collapse such as T008's is seen before a held-out set is spent. The threshold is per
   gate: gate A uses its pilot's invocation rate of the shipped-build arm on product-naming prompts; gate B
   uses the rollout-level call rate of the arm under test on recall-labelled items in the 2×2 factorial
   (SPEC-091 REQ-015); each minus an owner margin.
7. **Architecture before text.** For invocation, deterministic levers MUST be measured before text is
   optimized: `anthropic/alwaysLoad` tool meta, MCP server instructions, a skill description that leads
   with the use case, a factual (non-imperative) `UserPromptSubmit` hook, and an explicit command. Each is
   an arm. Their effect on this host is unmeasured; external reports are leads (see Research). A build that
   changes the skill description, the server instructions, `_meta` or the hook MUST be certified on the same
   build: gate B met and, on that build, at least one of gate A met or SPEC-049 noninferiority to the
   shipped build on a fresh gate A split (SPEC-091 REQ-038).
8. **Reframing.** The track is **best-arm selection over text artifacts under host drift**, with a frozen
   closed-model policy. It is not reinforcement learning of weights. ADR 0039's "reward-driven
   optimization" wording is read in that sense; no weights are trained (ADR 0042 deferred).
9. **Vendored APO is legacy.** The APO code vendored under ADR 0040 comes from the `v0.x` branch of
   microsoft/agent-lightning, which has had no development since January 2026; agent-lightning v1.x is
   reinforcement learning for open-weight models. APO and GEPA stay available for the skill body under
   gate A, with the corrected selection of decision 3 replacing their current selection steps: GEPA
   accepts a child when its minibatch mean beats its parent's and then keeps a Pareto front
   (`agent_braid/lightning_gepa.py`); APO keeps a top-k beam by mean (`agent_braid/lightning_apo.py`).
10. **Thompson Sampling: evaluated, not adopted.** See Alternatives. It MUST NOT be used in any frozen gate.
11. **Boundaries unchanged.** EUR 0 on the subscription route (ADR 0021, ADR 0039 decision 2); no LLM
    judge as a reward source (ADR 0039 decision 5); promotion MUST stay human with SPEC-049 noninferiority;
    held-out sets MUST be hash-frozen and scored once; `executionAuthorization` MUST stay false; no weights.
    **ADR 0039 needs no amendment:** it does not address allocation, decision 5 already admits verifiable
    rewards, and decision 1 already covers tool descriptions. **ADR 0042 stays deferred.**

## Alternatives considered

- **300 prompts × 1 repetition for gate A.** Changes the estimand from majority pass to the mean pass
  probability E[p] without saying so, and is optimal only if authoring a prompt costs nothing. It would
  have passed v3 (272/300 = 0.907) while the per-prompt signal that exposed the deterministic `units`
  defect is lost. Rejected.
- **Keep the zero-0/3 rule as written.** It detected real defects in v2 and v3, and it is itself an
  all-fail test at τ in [0.0295, 0.0466) for α = 0.05 and n = 100. It is not discarded but restated as an
  explicit τ (SPEC-090 OD-2), so that keeping or loosening it is a recorded owner choice; without any such
  rule v2 and v3 would have passed (95 and 91) with the defect inside.
- **Share of prompts with p below a cutoff c as the second-stage gate.** Not identifiable from 3 repetitions
  (2609.09245, Thm 1). Rejected.
- **Thompson Sampling (including top-two) for allocation.** Evaluated and not adopted:
  - it changes how rollouts are allocated, while the bottleneck is the power of each comparison;
  - pools are 5 to 20 near-tied candidates that fail on the same hard prompts, so pairing on a fixed
    slice removes shared noise that adaptive allocation does not, and the required sample grows as 1/gap², for the true gap between candidates,
    under any allocation;
  - top-two Thompson Sampling pays off for wide, well-separated pools;
  - adaptively collected data biases arm means and can double false-positive and false-negative rates
    (1905.11397, 2103.12198; abstracts), so it is excluded from held-out and audit data.
  It may be reopened only for pools of dozens of variants, by simulation against synchronized halving.
- **SySRs, racing or Bayesian best-arm identification as the elimination rule.** Not chosen here: SySRs
  (2606.07726) was demonstrated on deterministic scores and not against racing or covariance-adaptive
  methods. SPEC-090 compares candidates by simulation and the owner picks (SPEC-090 OD-11).
- **A paid or API optimizer, or weight RL.** Rejected by ADR 0021 and ADR 0039; ADR 0042 stays deferred.
- **Optimize only text for invocation.** The skill and tool text cannot grow (the cap) and the optimizer
  cannot reach front matter today. Architecture levers are measured first; text optimization follows.

## Consequences

- **Positive:** the gates certify quantities the data identify; per-prompt defects stay visible; the
  selection bias is measured; a collapse is detected before a held-out set is spent.
- **Negative:** code is needed (paired selection, `target.kind` beyond `skill`, run metadata, optionally
  `parallel`); three repetitions keep the cost near the current one; gate B needs a realistic lab and a
  labelled item set that the repository does not have yet.
- **Compatibility:** SPEC-078 and SPEC-079 protocols and splits are frozen and unchanged. The new gate A
  rule applies only to splits frozen under SPEC-090 onward; it is not applied retroactively to v4.
- **Security and privacy:** a `UserPromptSubmit` hook adds context to every prompt and is a new
  authority and privacy surface; whether the plugin may ship one is an owner decision (SPEC-091 OD-11).
- **Research:** that architecture levers raise recall without raising false positives is a hypothesis
  (SPEC-091), not a result. Nothing here has run.

## Validation

SPEC-090 and SPEC-091 plan simulation tests with known-p candidates, by simulation over the 0.41 to 0.81
correlation range before the pilots, re-run with the pilot's parameters (SPEC-090 T019) before any
selection or held-out run: selection accuracy against n = 5, type I and II error of gate A, coverage of
the all-fail bound, and replay determinism of a journal. None has run.

Real-run order, the same in ADR 0046, SPEC-090 and SPEC-091: the gate A noise pilot (SPEC-090 T020) and,
independently and in either order, the gate B noise pilot (SPEC-091 T008) and development factorial
(SPEC-091 T009); then lever screening (SPEC-091 T018) and the 2×2 factorial (SPEC-091 T012); then gate B
selection (SPEC-091 T019) only when SPEC-091 OD-20 requires it, and the same-build gate A run
(SPEC-091 T023) whenever the arm under test changes the description, server instructions, `_meta` or the
hook; then SPEC-091 T021 and T015. SPEC-090 T022 and T017 depend only on SPEC-090 T016 and may run at any
point after it. SPEC-091 T016 may run at any point after its own freeze. Each run MUST be behind its own
freeze and owner yes record (SPEC-090 REQ-017, SPEC-090 REQ-045, SPEC-091 REQ-045).

## Research (leads, not facts)

Preprints are single-team and several were read as abstracts only; each is a lead until reproduced here:
2512.21326 (pairing alone gives about 2.25× in sample size; the "3 to 6×" needs averaging over repeated
runs too), 2606.07726 (SySRs), 2610.09239 (winner's curse; a 64-item audit removes the average bias with
RMSE near 6 points, 128 items about 4.5), 2611.26592 (repetition optimum), 2609.09245 and 2610.04135
(identifiability), 2610.05671 and 2611.22605 (generate-and-select at small budgets), 2606.30775
(contrastive rewrite), 2610.14216 and 2609.16268 (invocation; invocation-only rewards teach keyword
triggers), 2611.23266 (Skill Roulette: a registered report without results). The host documentation
(skills, MCP, hooks) is the source for the lever mechanics; `alwaysLoad` on a plugin-provided server is
untested on this host, and the host's tool-search ranking is undocumented.

## References

- [ADR 0039](0039-braid-lightning-boundary.md), [ADR 0040](0040-braid-lightning-mit-vendoring.md),
  [ADR 0042](0042-braid-lightning-local-weight-training.md), [ADR 0038](0038-analyze-work-request-contract.md),
  [ADR 0021](0021-codex-claude-tooling-integration.md)
- [T008 diagnosis and strategy review](../../specs/079-kind-choice-tool-fix/evidence/t008-diagnosis-and-strategy-review.md),
  [SPEC-079 evaluation protocol](../../specs/079-kind-choice-tool-fix/evaluation-protocol.md)
- [SPEC-090](../../specs/090-lightning-evaluation-v2/spec.md), [SPEC-091](../../specs/091-invocation-gate/spec.md)
