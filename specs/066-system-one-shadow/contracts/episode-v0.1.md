# Contract: agent-braid-s1-episode/v0.1

One episode is a single JSON object on one line (UTF-8, canonical: sorted keys,
no insignificant whitespace, no NaN or infinity, no duplicate members). It is
written by the S1.5a shadow observer after a successful `analyze` or
`analyze-work` call. It never reaches an MCP envelope.

## Top level

| Field | Type | Rule |
|---|---|---|
| `schemaVersion` | string | Exactly `agent-braid-s1-episode/v0.1` |
| `episodeId` | string | Random UUID4, lowercase. Not derived from any input |
| `day` | string | UTC date, `YYYY-MM-DD` |
| `surface` | string | `mcp` |
| `operation` | string | `analyze` or `analyze-work` |
| `analysisKind` | string | `aim` or `git` |
| `analyzer` | object | `{version, ruleSet}`, copied from the report's `analyzer` without `name` |
| `operationCount` | integer | 1–64, from the report summary |
| `pairCount` | integer | 0–2016 |
| `pairsRecorded` | integer | 0–64; pairs beyond 64 are dropped deterministically in report order |
| `pairs` | array | `pairsRecorded` pair objects |
| `systemOne` | object | See below |
| `executionAuthorization` | boolean | Exactly `false` |

## Pair object

All values are derived from the System 2 report. Strings come only from closed
vocabularies.

| Field | Type | Rule |
|---|---|---|
| `system2` | string | `independent-candidate`, `ordered`, `conflicting` or `unknown` |
| `system2Determinate` | boolean | `false` only for `unknown` |
| `reasonCodes` | array of strings | Closed set: `dependency-order`, `shared-write`, `partial-coverage`, `external-effect`, `disjoint`, `shared-read-only`, `read-version` |
| `constraints` | array of strings | Copied from the report's closed constraint vocabulary |
| `coverage` | array of strings | Sorted subset of `complete`, `partial`, `unknown` |
| `sharedResourceCount` | integer | 0–4096 |
| `effectKinds` | object | `{left: [...], right: [...]}`. Sorted subsets of the analyzer's effect kinds. In the AIM path, effect kinds come from the operation records; when they are not derivable (Git path), the value is `null` |
| `dependency` | boolean | Whether the pair is ordered by an explicit dependency path |
| `observedOutcome` | null | Always `null` in v0.1; filled only by the S1.5b observer in a separate joined record |

Reason codes are mapped from the report's reason sentences by an exact,
versioned table. An unmapped sentence makes the observer record `skipped` with
reason `unmapped-reason`; the observer never stores free text.

## `systemOne` object

| Field | Type | Rule |
|---|---|---|
| `status` | string | `answered`, `abstained`, `refused` or `skipped` |
| `reason` | string or null | Closed set: `calibration-absent`, `identity-mismatch`, `budget-exceeded`, `unmapped-reason`, `store-unavailable`, `internal-error`, or `null` |
| `backendId` | string | For example `stdlib-rule-fixture-v1` |
| `manifestDigest` | string | 64 lowercase hex characters |
| `decisionPoint` | string | `DP-1` |
| `answers` | array or null | `null` unless `status` is `answered`; otherwise one item per recorded pair: `{choice, probabilities}` over `likely-independent`, `likely-conflicting`, `undetermined` |
| `elapsedMicros` | integer | 0–50,000; System One time only |

## Never present

Resource names, paths, instance or attempt identifiers, analysis identifiers,
input digests, repository names, prompts, reason sentences, host names and user
names. The validator refuses an episode containing any string that is outside
the closed vocabularies above, other than `episodeId`, `day`, `backendId` and
`manifestDigest`.
