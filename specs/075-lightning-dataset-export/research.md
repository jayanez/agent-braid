# SPEC-075: Research

Shared research: [070 research](../070-braid-lightning-foundations/research.md)
(upstream survey §1, literature §2, decisions §3). Spec-specific notes:

- **Upstream aggregation.** `agentlightning/verl/rollout_adapter.py` (v1.0.3,
  commit `bc3a9e80`) accepts `trace_aggregator_level` `transition|trajectory`;
  trajectory merges multi-turn prompts by token-ID prefix and bounds lengths
  (`trajectory_max_prompt_length`, `trajectory_max_response_length`). We port
  the concept, not the tensor code: hosted hosts expose no token IDs
  (decision 1), so text-level merge is the normal path with a declared limit.
- **Balance.** SWE-Gym reports better downstream results when trajectories
  are balanced across outcomes; we adopt per-task capping as a default, not a
  claim (E4).
- **Terms.** Decision 5: provider terms decide whether host outputs may train
  models. Recorded as OD-1; no engineering work substitutes it.
- **Alternatives rejected.** Parquet/Arrow output (adds dependencies);
  HF `datasets` format (dependency, network); random ordering (breaks
  byte-identical reruns).
