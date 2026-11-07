# Contract: `braid-lightning-reward/v0.1`

Computed by `agent_braid/lightning_reward.py` from one rollout's parsed attempts
and its prompt case. No model call. Exact keys.

| Key | Type | Source |
|---|---|---|
| `schema` | const `braid-lightning-reward/v0.1` | — |
| `rolloutId` | identifier | — |
| `schemaValid` | boolean | first attempt's request validates against the declared `analyze-work` schema (`agent_braid/analyze_work_schema.py`) |
| `d4FirstAttempt` | boolean | `score_case` first-attempt verdict |
| `d4WithinRetry` | boolean | `score_case` within-one-retry verdict |
| `attempts` | integer ≥ 0 | tool calls counted by `score_case` |
| `reasons` | list of strings | `score_case` failure reasons, bounded |
| `canaryHits` | integer ≥ 0 | canary tokens seen in tool calls or output |
| `scoringSha256` | 64 hex | must equal the FREEZE entry for `scripts/spec069_scoring.py` |
| `components` | subset of `schema`, `d4`, `canary` | from `reward.components` |
| `claim` | const `empirical-measurement` | Article 13: never a guarantee |

Rules:

- `canaryHits > 0` forces `d4FirstAttempt` and `d4WithinRetry` to false.
- A tool not called, or an empty declaration, is never valid (SPEC-069
  procedure_010 negative controls).
- Aggregation per host uses `summarize` and `wilson_interval`; any scalar used
  by an optimizer is declared in its run record (SPEC-072).
