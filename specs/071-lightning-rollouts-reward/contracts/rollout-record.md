# Contract: `braid-lightning-rollout/v0.1`

One JSON line per rollout in `<plugin home>/lightning/runs/<run-id>/rollouts.jsonl`
(SPEC-070 store). Exact keys; unknown keys refused.

| Key | Type | Meaning |
|---|---|---|
| `schema` | const `braid-lightning-rollout/v0.1` | — |
| `runId`, `rolloutId`, `attemptId` | identifier | upstream analogue: rollout and attempt ids |
| `groupId` | identifier | prompt × candidate group (upstream `group_id`) |
| `taskId` | string | prompt case id (`DEV-01`, `HO-01`, …) |
| `promptSet` | enum `development`, `held-out` | — |
| `promptSetSha256` | 64 hex | must equal FREEZE for `held-out` |
| `candidateSha256` | 64 hex | guidance text under test |
| `host` | enum `claude-code`, `opencode` | — |
| `hostVersion`, `model` | string or null | as reported by the host |
| `repetition` | integer ≥ 1 | — |
| `state` | enum SPEC-070 rollout states | — |
| `keySource` | string or null | host-reported; must be in `SUBSCRIPTION_KEY_SOURCES` |
| `credentialPresent` | boolean | never the value |
| `stop` | null or a budget-stop name | — |
| `refusal` | null or a code from [refusals.md](refusals.md) | — |
| `startedAt`, `endedAt` | UTC RFC 3339 | — |
| `durationSeconds` | finite number ≥ 0 | — |
| `transcriptSha256` | 64 hex | redacted transcript stored by hash only while trace consent is `none` |
| `rewardSha256` | 64 hex or null | hash of the reward record |
| `label` | enum `pipeline-only`, `host-run` | fake hosts are `pipeline-only` |
| `executionAuthorization` | const `false` | — |

Replay: the reward record is recomputed from the stored transcript and must
hash to `rewardSha256`.
