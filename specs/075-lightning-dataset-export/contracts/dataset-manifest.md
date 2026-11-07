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
| `kind` | `supervised` \| `trajectory` | required |
| `level` | `transition` \| `trajectory` | required |
| `generatedAt` | RFC 3339 UTC | excluded from `digest` |
| `seed` | integer ≥ 0 | balance choice seed |
| `balance` | `equal` \| `none` | E4 |
| `orderingKey` | const `["taskId","groupId","rolloutId","attemptId","turnIndex"]` | E3 |
| `redactionVersion` | string | from SPEC-074; one per dataset |
| `termsDecision` | `{path, sha256}` \| null | required non-null when any record has `source: host-model` |
| `canaryScan` | const `clean` | written only after the scan |
| `exclusions` | object reason → count | `no-consent`, `metadata-only`, `unredacted`, `balance`, `overlong` |
| `records` | array | one entry per JSONL line, in file order |
| `recordsSha256` | hex | SHA-256 of `records.jsonl` |
| `digest` | hex | SHA-256 of canonical manifest without `generatedAt` and `digest` |

Record entry: `recordId`, `sha256` (of its line), `taskId`, `groupId`,
`rolloutId`, `attemptId`, `turnRange` `[first,last]`, `consentLevel`,
`source` (`host-model` \| `fixture` \| `local-model`), `outcome`
(`success` \| `failure` \| `unknown`), `limits` (subset of
`text-level-merge`, `truncated`).

## Record shapes

- `supervised`: `{"recordId", "messages": [{"role", "content"}...]}`; `tool`
  messages carry `toolCallId`; content is redacted text only.
- `trajectory`: `{"recordId", "rolloutId", "attemptId", "turns": [...],
  "reward": {...}, "status"}`; reward is the SPEC-071 vector, unchanged.

## Refusal codes

`terms-gate-missing`, `canary-detected`, `output-not-empty`, `path-refused`,
`no-records`, `invalid-argument`. Refusals echo no record content.

## Upstream mapping

`rollout_adapter.trace_aggregator_level` → `level`;
`trajectory_max_prompt_length`/`trajectory_max_response_length` → character
bounds with limit `truncated`; token-ID prefix merge → only when all turns have
token IDs, else `text-level-merge`.
