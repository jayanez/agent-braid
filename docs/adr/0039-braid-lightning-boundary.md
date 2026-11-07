# ADR 0039: Braid Lightning optimization boundary

- **Status:** proposed (2026-11-08), for owner review with SPEC-070 T001
- **Date:** 2026-11-08
- **Deciders:** Juan Antonio Yáñez García (owner)
- **Constitutional articles:** 0, 12, 13, 14, 19, 20, 23, 25
- **Specification:** [SPEC-070](../../specs/070-braid-lightning-foundations/spec.md) (track BL), program in [program.md](../../specs/070-braid-lightning-foundations/program.md)

## Context

The ROADMAP keeps "specific model/runtime integrations" as a deferred decision
that needs an ADR. The owner asked on 2026-11-08 for a reinforcement-learning
layer adapted from microsoft/agent-lightning. The research record
([research.md](../../specs/070-braid-lightning-foundations/research.md)) shows
that hosted Claude Code and OpenCode expose neither weights nor token IDs, so
weight-level RL on them is impossible; reward-driven optimization of Agent
Braid's own guidance is feasible with verifiable rewards. ADR 0021 caps extra
cash spend at EUR 0; SPEC-049 keeps promotion human; Article 20 separates
analysis from execution; ADR 0034 forbids third-party decision models in System
One.

## Decision

1. **What Braid Lightning is.** An off-by-default laboratory that evaluates and
   proposes versions of text artifacts Agent Braid owns (skills, tool
   descriptions, request templates) from recorded rollouts and verifiable
   rewards. Its outputs are candidates and evidence, never actions.
2. **Model route.** Host CLIs in headless mode on the owner's subscription are
   the only route, both for rollouts and for the optimizer model. Any
   `*_API_KEY` or provider-switch variable in a rollout environment is refused.
   Extra cash spend is EUR 0.
3. **Authority.** `executionAuthorization` is false in every output; no
   Braid Lightning code calls `execute`, `recover`, grants or delegated runtime
   tools; the MCP server never starts a run; runs start only from the
   `agent-braid lightning` CLI.
4. **Promotion.** Human only, through the HAR profile registry (SPEC-073).
   Automatic promotion is not offered.
5. **Rewards.** Verifiable components first (schema validity, D4 criteria,
   canaries). Rewards are empirical measurements and are never labelled
   guarantees or equivalence classes (Article 13). LLM judges are not reward
   sources.
6. **Scope of earlier statements.** The "no fine-tuning" statements of SPEC-034
   to SPEC-037 concern forecasting models and remain in force there. Prompt
   optimization is not fine-tuning. Weight training is covered only by ADR 0042
   (deferred).
7. **System One.** Braid Lightning may read System One episodes as a trace
   source. It never supplies a decision model, weights or advice to System One;
   ADR 0034 is unchanged.

## Alternatives

- *Paid API optimizer:* faster, but breaks ADR 0021. Rejected by owner decision L1.
- *Weight RL now (verl, GPUs):* the literature's strongest results, but needs a
  local open model, CUDA and hundreds to thousands of GPU-hours. Deferred (L3).
- *No layer; manual guidance edits:* status quo; SPEC-069 T010 shows manual
  guidance missed D4.

## Consequences

- A new experimental CLI and a registry opt-in key; no change to existing outputs.
- Subscription quota (five-hour and weekly windows) becomes the binding budget.
- Every candidate and decision is replayable from hashes (Article 14).
- A null optimization result is a legitimate outcome of SPEC-072.
