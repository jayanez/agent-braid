# Contract: `braid-lightning-attempt-result/v0.1`

`agent_braid/lightning_schema.py` owns `braid-lightning-rollout/v0.1` (exact keys
`schema`, `rolloutId`, `taskId`, `groupId`, `candidateSha256`, `inputSha256`,
`host`, `isTrain`, `timeoutSeconds`, `status`). SPEC-071 does not change it.
Everything BL.1 records about one attempt of a rollout lives in a separate
record, `braid-lightning-attempt-result/v0.1`, stored by the SPEC-070 store as a
new kind `result` (one JSON line per attempt in
`<plugin home>/lightning/runs/<run-id>/results.jsonl`), keyed by
`rolloutId` + `attemptId` and referencing the v0.1 rollout by `rolloutId`.
Exact keys; unknown keys refused.

| Key | Type | Meaning |
|---|---|---|
| `schema` | const `braid-lightning-attempt-result/v0.1` | — |
| `runId` | identifier | — |
| `rolloutId` | identifier | references the `braid-lightning-rollout/v0.1` record |
| `attemptId` | identifier | upstream analogue: attempt id; key with `rolloutId` |
| `promptSet` | enum `development`, `held-out` | — |
| `promptSetSha256` | 64 hex | must equal FREEZE for `held-out` |
| `hostVersion`, `model` | string or null | as reported by the host |
| `repetition` | integer ≥ 1 | — |
| `keySource` | string or null | host-reported; see REQ-004 for accepted values |
| `credentialPresent` | boolean | never the value |
| `stop` | null or a budget-stop name | — |
| `refusal` | null or a code from [refusals.md](refusals.md) | — |
| `startedAt`, `endedAt` | UTC RFC 3339 | — |
| `durationSeconds` | finite number ≥ 0 | — |
| `parsedAttempts` | list of content-free parsed attempts | per tool call: request envelope SHA-256, refusal code or null, and the `score_case` inputs (declared fields, verdict inputs), no prompt or response text |
| `transcriptSha256` | 64 hex | redacted transcript stored by hash only while trace consent is `none` |
| `rewardSha256` | 64 hex or null | hash of the reward record |
| `label` | enum `pipeline-only`, `host-run` | fake hosts are `pipeline-only` |
| `executionAuthorization` | const `false` | — |

Replay: the reward record is recomputed from `parsedAttempts` and must hash to
`rewardSha256`. Replay from the transcript itself requires SPEC-074 consent
`redacted`; without it only the transcript hash is checked.

Compatibility: `braid-lightning-rollout/v0.1` is unchanged; the new store kind
`result` is added to `lightning_store.KINDS`.
