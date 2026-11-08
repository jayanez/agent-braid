# Contract: `braid-lightning-config/v0.1`

Canonical file: `<plugin home>/lightning/lightning.json` (private, 0600).
Machine schema: `schemas/0.3.0-experimental/lightning-config.schema.json`.
Validator: `agent_braid/lightning_config.py`. Both refuse unknown keys at every
level. Defaults below are what `agent-braid lightning init` proposes.

| Section / key | Type and bound | Default | Upstream analogue |
|---|---|---|---|
| `schema` | const `braid-lightning-config/v0.1` | — | — |
| `target.kind` | enum `skill` | `skill` | `actor_rollout_ref.model.path` (component of interest) |
| `target.path` | repository-relative path, no `..` | `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md` | — |
| `target.lab` | enum `spec069` | `spec069` | `examples/*` |
| `data.train` | repository-relative path | `specs/069-aim-request-authoring/prompts/development.json` | `train_dataset` |
| `data.holdout` | repository-relative path | `specs/069-aim-request-authoring/prompts/held-out.json` | `val_dataset` |
| `data.freezeSha256` | 64 lowercase hex or `null` | `null` (set by SPEC-072 preregistration) | — |
| `rollout.hosts` | non-empty unique subset of `claude-code`, `opencode` (SPEC-069 driver host names) | `["claude-code", "opencode"]` | `local.agent_class` |
| `rollout.repetitions` | integer 1–5 | 3 | — |
| `rollout.maxTurns` | integer 1–50 | 12 | — |
| `rollout.timeoutSeconds` | integer 30–3600 | 300 | `rollout_timeout_seconds` |
| `rollout.parallel` | integer 1–4 | 1 | `n_runners` |
| `algorithm.name` | enum `gepa`, `apo`, `baseline` | `gepa` | `algorithm` |
| `algorithm.beamWidth` | integer 1–8 | 4 | APO `beam_width` |
| `algorithm.branchFactor` | integer 1–8 | 4 | APO `branch_factor` |
| `algorithm.rounds` | integer 1–10 | 3 | APO `beam_rounds` |
| `algorithm.minibatch` | integer 1–32 | 5 | APO `gradient_batch_size` |
| `optimizer.host` | enum `claude-code`, `opencode` | `claude-code` | APO `gradient_model` |
| `optimizer.route` | const `subscription` | — | — |
| `reward.components` | non-empty unique subset of `schema`, `d4`, `canary` | all three | `RewardData` |
| `reward.gate` | enum `d4-holdout` | `d4-holdout` | — |
| `budget.maxRollouts` | integer 1–2000 | 120 | `max_rollouts` |
| `budget.maxOptimizerCalls` | integer 0–500 | 40 | — |
| `budget.eurCap` | const 0 | — | — |
| `traces.sources` | unique subset of `rollout`, `host-transcript`, `loom`, `system-one` | `["rollout"]` | `tracer` |
| `traces.contentConsent` | enum `none`, `redacted` | `none` | — |
| `traces.retentionDays` | integer 1–90 | 30 | — |
| `export.enabled` | boolean | `false` | — |
| `export.level` | enum `transition`, `trajectory` | `trajectory` | `trace_aggregator.level` |
| `promotion.mode` | const `human` | — | — |
| `promotion.executionAuthorization` | const `false` | — | — |

Refusal codes (closed vocabulary): `config-shape`, `config-unknown-key`,
`config-missing-key`, `config-type`, `config-range`, `config-enum`,
`config-constant`, `config-path`, `config-duplicate`, `config-digest`,
`config-changed`.

`traces.contentConsent = "redacted"` is accepted by the schema but has no effect
until SPEC-074 delivers the consent contract; until then the store refuses
content-bearing fields whatever this value says.
