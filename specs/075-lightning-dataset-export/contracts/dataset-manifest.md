# Contract: `braid-lightning-dataset-manifest/v0.1` (proposed)

Schema: `schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json`
(created by the lead; this file is the normative prose). Status: proposed.

## Files

An export directory contains exactly `manifest.json` and `records.jsonl`.
Lines are `trace_adapter.canonical_bytes(record)` followed by `\n`.

## Manifest fields

| Field | Type | Rule |
|---|---|---|
| `manifestVersion` | const `braid-lightning-dataset-manifest/v0.1` | required |
| `kind` | `supervised` \| `rollout` | required |
| `level` | `transition` \| `trajectory` | required |
| `generatedAt` | RFC 3339 UTC | excluded from `digest` |
| `seed` | integer ≥ 0 | balance choice seed |
| `balance` | `equal` \| `none` | E4; `rollout` kind only, `none` for `supervised` |
| `orderingKey` | const `["taskId","groupId","rolloutId","attemptId","turnIndex"]` | E3 |
| `redactionVersion` | string | from SPEC-074; one per dataset |
| `termsDecision` | `{path, sha256}` \| null | required non-null when any record has `source: host-model` |
| `canaryScan` | const `clean` | written only after the scan |
| `exclusions` | object reason → count | `no-consent`, `consent-none`, `unredacted`, `balance`, `overlong`, `retention-expired` |
| `retention` | object source run id → `{retentionDays, expiresAt}` | from SPEC-074; records past `expiresAt` are refused |
| `records` | array | one entry per JSONL line, in file order |
| `recordsSha256` | hex | SHA-256 of `records.jsonl` |
| `digest` | hex | SHA-256 of canonical manifest without `generatedAt` and `digest` |

Record entry: `recordId`, `sha256` (of its line), `taskId`, `groupId`,
`rolloutId`, `attemptId`, `turnRange` `[first,last]`, `consentLevel` (`redacted`),
`source` (`host-model` \| `fixture` \| `local-model`), `outcome`
(`success` \| `failure` \| `unknown`), `limits` (subset of
`text-level-merge`, `truncated`).

## Record shapes

- `supervised`: `{"recordId", "messages": [{"role", "content"}...]}`, plus
  `"outcome"` when `--outcome-field` is given (otherwise only records with
  `d4FirstAttempt` true); `tool` messages carry `toolCallId`; content is
  redacted text only.
- `rollout`: `{"recordId", "rolloutId", "attemptId", "turns": [...],
  "reward": {...}, "status"}`; reward is the SPEC-071 vector, unchanged.

## Refusal codes

`export-disabled` (configuration `export.enabled` is not `true`),
`terms-gate-missing`, `canary-detected`, `retention-expired`,
`output-not-empty`, `path-refused`, `no-records`, `invalid-argument`. Refusals echo no record content.

## Retention and purge

Exported files are outside SPEC-074 purge; the owner deletes them.
`agent-braid lightning purge` lists the manifests that cite a purged run.

## Upstream mapping

`rollout_adapter.trace_aggregator_level` → `level`;
`trajectory_max_prompt_length`/`trajectory_max_response_length` → character
bounds with limit `truncated`; token-ID prefix merge → only when all turns have
token IDs, else `text-level-merge`.
