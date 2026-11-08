# SPEC-071: Research

The upstream analysis, literature review and program-level decisions are in
[SPEC-070 research](../070-braid-lightning-foundations/research.md). This file
records only decisions specific to BL.1.

- **Runner source.** Upstream v1.0.3 `agentlightning/controller/local_reconciler.py`
  (commit `bc3a9e80`) reconciles desired and running rollouts with local
  processes. Kept: one process per rollout, timeout, state transitions, bounded
  concurrency. Dropped: the Kubernetes reconciler, the gateway and the
  OpenAI-compatible proxy (no token IDs are available from hosted hosts).
- **Hooks source.** v1.0.3 `agentlightning/hooks.py` `RolloutHooks`; ported as
  plain callables without async.
- **Reward source.** v0.x `agentlightning/emitter/reward.py` (`emit_reward`,
  `RewardData`, commit `6db3c73d`) emits one float. Agent Braid keeps a vector
  (R1) because a scalar hides which criterion failed (Article 14).
- **Verifiable rewards.** GRPO and SWE-Gym style rewards are program-checked;
  an LLM judge is excluded because it can be gamed and is not reproducible.
- **Reward hacking threat model.** Known shortcuts: reading `.git` history or
  the scoring source, fetching answers over the network, reading held-out
  files. Controls: hidden `.git`, sandbox egress denial, canaries, FREEZE hash.
- **Paid route.** `scripts/spec069_native_runs.py` injects
  `ANTHROPIC_API_KEY` through `KEY_SPECS`; that is the paid route. The runner
  inverts the policy: such keys are refused, following
  `harness_host_claude.ENV_DENY` and `SUBSCRIPTION_KEY_SOURCES`.
- **Baseline to compare (`route-changed comparison`).** T010 baseline: claude-code and opencode each 16/30
  first-attempt successes on the development set, Wilson 95 % interval
  [0.361, 0.698]; verdict `misses` (negative result).
