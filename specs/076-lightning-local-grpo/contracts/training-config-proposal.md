# Contract: `lightning.json` `training` section (proposed)

**Status:** proposed, deferred. Not part of `braid-lightning-config/v0.1`
([contract](../../070-braid-lightning-foundations/contracts/lightning-config.md));
a v0.1 validator refuses this key until a later configuration version adopts it.

## Proposed shape

```json
{
  "training": {
    "algorithm": "grpo",
    "rolloutLevelAdvantage": true,
    "lossMode": "per_rollout_mean",
    "aggregation": {"level": "trajectory", "maxPromptLength": 2048, "maxResponseLength": 8192},
    "groupSize": 8,
    "rewardFillValue": 0.0,
    "maxPpoUpdateTimes": null,
    "difficultyFilter": {"dropZeroVariance": true},
    "asyncRollout": {"enabled": false, "batchSize": null, "maxStaleness": 1},
    "rolloutTimeoutSeconds": 1800,
    "model": {"name": null, "servedBy": "vllm"},
    "gpuHourCap": null
  }
}
```

## Mapping from upstream `agentlightning/verl/config.yaml` (v1.0.3)

| Upstream key | Proposed key | Note |
|---|---|---|
| `algorithm.enable_rollout_level_advantage` | `rolloutLevelAdvantage` | default true |
| `actor_rollout_ref.actor.policy_loss.loss_mode` | `lossMode` | `per_rollout_mean` |
| `agentlightning.trace_aggregator.level` | `aggregation.level` | `transition` \| `trajectory` |
| `trace_aggregator.trajectory_max_prompt_length` | `aggregation.maxPromptLength` | |
| `trace_aggregator.trajectory_max_response_length` | `aggregation.maxResponseLength` | |
| `trace_aggregator.classify_trace_merge_mismatches` | — | debug only, dropped |
| `agentlightning.reward_fillna_value` | `rewardFillValue` | |
| `agentlightning.max_ppo_update_times` | `maxPpoUpdateTimes` | |
| `agentlightning.async_rollout.enabled` | `asyncRollout.enabled` | |
| `agentlightning.async_rollout.async_train_batch_size` | `asyncRollout.batchSize` | |
| `agentlightning.rollout_timeout_seconds` | `rolloutTimeoutSeconds` | |
| `agentlightning.agl_base_url`, `agl_key` | — | replaced by the local proxy and owner token |
| `agentlightning.local.*` | — | runner is always local |
| `agentlightning.k8s.*` | — | Kubernetes not ported |
| `agentlightning.hooks` | — | not ported |
| `data.filter_overlong_prompts` | covered by `aggregation` bounds | |
| `actor_rollout_ref.rollout.mode` | — | fixed async serving via vLLM |
| `hydra.*`, `defaults` | — | no Hydra (SPEC-070 F4) |
| verl `ppo_trainer` group size (`rollout.n`) | `groupSize` | |
| — | `difficultyFilter`, `asyncRollout.maxStaleness`, `gpuHourCap` | new |

Fixed values from configuration v0.1 (`budget.eurCap = 0`, human promotion,
`executionAuthorization = false`) still apply.
