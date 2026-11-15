# Contract: `braid-lightning-dataset-manifest/v0.1` (proposed)

Schema: [`schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json`](../../../schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json)
(created by the lead in T002; this file is the normative prose; the schema and
this table agree, `tests/test_spec075_manifest_schema.py`). Status: reviewed at
T001 (2026-11-14; E1–E5 accepted, OD-2 decided).

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
| `balance` | `equal` \| `none` | E4; `equal` keeps `min(successes, failures)` of each outcome per task (1:1, OD-2); `rollout` kind only, `none` for `supervised` |
| `orderingKey` | const `["taskId","groupId","rolloutId","attemptId","turnIndex"]` | E3 |
| `redactionVersion` | string `[a-z0-9][a-z0-9./-]{0,127}` | identifies the SPEC-074 redactor that produced the content; one per dataset. SPEC-074 records carry no version field, so the builder defines it (T006): `spec074-redact/` plus the first 16 hex of the SHA-256 of the SPEC-074 redactor's pattern sources (each `flags:pattern`, one per line) and its salt size; it changes when a pattern changes and holds no secret; SPEC-074 is not changed |
| `termsDecision` | `{path, sha256}` \| null | required non-null when any record has `source: host-model`; `path` is relative (no leading `/`, no `.` or `..` segment, no whitespace, at most 256 characters) |
| `canaryScan` | const `clean` | written only after the scan |
| `exclusions` | object reason → count, every reason present | `no-consent`, `consent-none`, `unredacted`, `content-missing`, `balance`, `overlong`, `retention-expired` |
| `balanceReport` | array of `{taskId, successes, failures, unknown, keptPerOutcome, dropped, singleOutcome}` | E4 per-task counts, one entry per task; `singleOutcome` implies `keptPerOutcome` 0; empty for `supervised` and `balance: none` |
| `retention` | object source run id → `{retentionDays, expiresAt}` | from SPEC-074; `expiresAt` is the UTC expiry date `YYYY-MM-DD` of the run; records past it are refused; one key per record `runId` |
| `records` | array, at least one | one entry per JSONL line, in file order (an empty export refuses with `no-records`) |
| `recordsSha256` | hex | SHA-256 of `records.jsonl` |
| `digest` | hex | SHA-256 of canonical manifest without `generatedAt` and `digest` |

Record entry: `recordId` (`r-` plus the first 16 hex of the SHA-256 of the
canonical `{record, source}`, where `record` is the record without `recordId`
and `source` is `[runId, rolloutId, attemptId, turnRange]`, so identical texts
from two attempts get distinct ids; T004), `sha256` (of its line), `runId` (the source
run, keying `retention`), `taskId`, `groupId`, `rolloutId`, `attemptId` (the
SPEC-074 pseudonym `attempt-`, `turn-`, `strand-` or `episode-<hmac16>`, never
the raw id), `turnRange` `[first,last]` with first ≤ last, `consentLevel` (`redacted`),
`source` (`host-model` \| `fixture` \| `local-model`), `outcome`
(`success` \| `failure` \| `unknown`), `limits` (subset of
`text-level-merge`, `truncated`).

Exclusions are counted per model call (one adapter triplet). Reasons, first
match wins: `consent-none` (the SPEC-074 gate refuses with
`content-consent-required`: consent `none`, or no profile, or an unreadable or
invalid one, which SPEC-074 reads as `none`), `no-consent` (gate refusal
`source-not-consented`: consent `redacted` but the source is not listed in
`traces.sources`),
`unredacted` (not a `braid-lightning-triplet/v0.1` record with
`redaction.scanClean` true), `content-missing` (below).

Exclusion `content-missing` counts model calls with consent but no stored
content (for example a content line already swept), or without a prompt or
response to export; it was added when the schema was created (T002).

Checks the schema cannot express and the builder enforces: `recordsSha256`, each
record `sha256` and `digest` match the bytes they cover; `turnRange` first ≤
last; `limits` sorted; a `retention` key per record `runId`; unique
`balanceReport.taskId`; `singleOutcome` implies `keptPerOutcome` 0; a
`supervised` export has `exclusions.balance` 0; a host-model record is never
labelled `fixture`.

## Record shapes

- `supervised`: `{"recordId", "messages": [{"role", "content"}...]}`, plus
  `"outcome"` when `--outcome-field` is given (otherwise only records with
  `d4FirstAttempt` true); `tool` messages carry `toolCallId`; `assistant`
  messages carry the redacted `toolCalls` when the model called tools; content is
  redacted text only. A `transition` record is one model call (`user` prompt,
  `assistant` response); a `trajectory` record is the attempt's exported calls in
  order, with limit `text-level-merge` when it merges more than one. Rollout
  content holds no tool results, so rollouts yield no `tool` message.

Per-attempt fields, from content-free records: `outcome` is `success` when the
attempt's last reward event has component `d4` 1.0 (`d4FirstAttempt` true),
`failure` when 0.0, else `unknown`; `source` is `fixture` only when every
attempt result is labelled `pipeline-only`, else `host-model` (also without a
result, or with conflicting results: fail closed). While OD-1 is deferred, a
writer refuses any `host-model` unit with `terms-gate-missing` before writing
anything (T004); T008 replaces that refusal with the owner terms-decision check.
Writers accept only items that pass the consent and redaction filter
(`invalid-argument` otherwise). Units left out by the `d4FirstAttempt` filter are not exclusions and are
not counted in the manifest.
- `rollout`: `{"recordId", "rolloutId", "attemptId", "turns": [...],
  "reward": {...}, "status"}`; reward is the SPEC-071 vector, unchanged.
  Each turn is `{prompt, response, toolCalls}` (redacted text and tool calls of
  one model call); `reward` is the attempt's last reward event `{value,
  components, source, reason}` or null; `status` is the rollout's latest state
  (`queuing`, `running`, `succeeded`, `failed`). `transition` writes one record
  per model call, `trajectory` one per attempt with its exported calls in order
  (a rollout has one attempt; a rollout with more is refused `source-invalid`).
  A trajectory merges by token-ID prefix only when its calls are consecutive
  (no call excluded in between), every turn's prompt and response carry integer
  token IDs and each prompt starts with the previous prompt and response; otherwise, and always for hosted Claude Code or OpenCode
  (their triplets carry no token IDs), the merge is text-level and the entry
  declares `text-level-merge`. A one-call unit merges nothing. Token IDs never
  enter a record (T005).

## Refusal codes

`export-disabled` (configuration `export.enabled` is not `true`),
`terms-gate-missing`, `canary-detected`, `retention-expired`,
`output-not-empty`, `path-refused`, `no-records`, `invalid-argument`,
`invalid-record` (a written record outside its shape), `invalid-manifest` (a
builder check failed). Refusals echo no record content.

## Writing (T006)

`export_dataset` reads, filters and writes the records, runs the SPEC-074
post-redaction scan over the dataset bytes (`canary-detected` on a hit; the
canary corpus coverage is T010), builds the manifest, runs `check_manifest` and
writes `records.jsonl` then `manifest.json` into a private temporary directory
next to the output, renamed onto it (the output must not exist or be an empty
directory, else `output-not-empty`). A refusal at any step leaves no output and
no temporary directory. Both files are canonical bytes plus a newline.
`retention` gives each cited run the profile's `traces.retentionDays` and the UTC
date its run expires (`createdAt` + days); the refusal of expired records is
T013. Until T007, `balance` is `none` for both kinds (`equal` is refused with
`invalid-argument`).

## Retention and purge

Exported files are outside SPEC-074 purge; the owner deletes them.
`agent-braid lightning purge` lists the manifests that cite a purged run.

## Upstream mapping

`rollout_adapter.trace_aggregator_level` → `level`;
`trajectory_max_prompt_length`/`trajectory_max_response_length` → character
bounds with limit `truncated`; token-ID prefix merge → only when all turns have
token IDs, else `text-level-merge`.
