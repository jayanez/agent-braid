# SPEC-076: Research

Shared research: [070 research](../070-braid-lightning-foundations/research.md).
Spec-specific notes (upstream v1.0.3, commit `bc3a9e80`, read only):

- **Proxy.** `agentlightning/server/proxy.py` injects `return_token_ids` and
  `logprobs`, keeps a pause state (503 with retry reason, in-flight counter) and
  retries upstream on retryable status. Ported concepts only, onto `view_serve`.
- **Trainer defaults.** `agentlightning/verl/config.yaml`:
  `algorithm.enable_rollout_level_advantage: true`,
  `actor.policy_loss.loss_mode: per_rollout_mean`,
  `trace_aggregator.level: trajectory`, `max_ppo_update_times: null`,
  `async_rollout.enabled: false`, `rollout.mode: async`.
- **Advantage and loss.** `rollout_level_advantage.py`, `per_rollout_loss.py`:
  one advantage per rollout, loss averaged per rollout so long trajectories do
  not dominate.
- **Setup.** `scripts/setup_verl.sh` installs pinned verl/vLLM/torch; we keep
  that pinning in an optional extra, isolated environment only.
- **Async.** `docs/35-asynchronous-training*` describes overlapping rollout and
  training with bounded staleness.
- **Difficulty filtering.** Groups with identical rewards give zero advantage
  (advantage collapse); filter them (literature §2).
- **Alternatives rejected.** Kubernetes runner (complexity, no cluster);
  hosted fine-tuning APIs (cash spend, no token IDs); PPO with critic (memory).
- **Budget.** Published GRPO coding-agent runs report hundreds to thousands of
  GPU-hours; recorded as an estimate range, not a plan.
