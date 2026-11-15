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
| `redactionVersion` | string `[a-z0-9][a-z0-9./-]{0,127}` | identifies the SPEC-074 redactor that produced the content; one per dataset. SPEC-074 records carry no version field, so the builder defines it (T006): `spec074-redact/` plus the first 16 hex of the SHA-256 of the SPEC-074 redactor's pattern sources (each `flags:pattern`, one per line) and its salt size; it changes when a pattern or the salt size changes, does not cover the redactor's code, and holds no secret; SPEC-074 is not changed |
| `termsDecision` | `{path, sha256}` \| null | required non-null when any record has `source: host-model`; `path` is relative (no leading `/`, no `.` or `..` segment, no whitespace, at most 256 characters) |
| `canaryScan` | const `clean` | written only after the scan |
| `exclusions` | object reason → count, every reason present | `no-consent`, `consent-none`, `unredacted`, `content-missing`, `balance`, `overlong`, `retention-expired` |
| `balanceReport` | array of `{taskId, successes, failures, unknown, keptPerOutcome, dropped, singleOutcome}` | E4 per-task counts, one entry per task; `singleOutcome` implies `keptPerOutcome` 0; empty for `supervised` and `balance: none` |
| `retention` | object source run id → `{retentionDays, expiresAt}` | from SPEC-074; `expiresAt` is the UTC expiry date `YYYY-MM-DD` of the run; records past it are refused (T013; until then only fixture content can export, as the terms gate refuses all host-model output); one key per record `runId` |
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
result, or with conflicting results: fail closed). A writer refuses any
`host-model` unit that no valid owner terms decision covers with
`terms-gate-missing` before writing anything (T004, T008).
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
directory, else `output-not-empty`; a symbolic link as the output or its parent
is `path-refused`), then syncs the parent directory. The directory is `0700`
and both files `0600`. A refusal at any step leaves no output and no temporary
directory; a crash (for example a killed process) between the temporary
directory and the rename can leave a `.export-*` directory beside the output,
holding only that export's files, for the owner to delete. Both files are
canonical bytes plus a newline. The SPEC-074 adapter redacts the current `$HOME`
to `~` when it reads content, so the bytes reproduce for the same `$HOME` at
ingest and export, not across different ones.
`retention` gives each cited run the profile's `traces.retentionDays` and the UTC
date its run expires (`createdAt` + days); the refusal of expired records is
T013. `balance` defaults to `equal` for `rollout` and is always `none` for
`supervised` (`equal` there is `invalid-argument`; no ratio parameter, OD-2).

## Balance (T007)

`equal`: per task, attempts are grouped by outcome; each task keeps
`min(successes, failures)` attempts of each of `success` and `failure`, chosen
by the lowest SHA-256 of the canonical `[seed, taskId, runId, rolloutId]` (a
seeded, order-independent choice; a rollout has one attempt, so the key names
it without the salt-dependent pseudonym: the same data and seed give the same
selection, also after a re-ingest). Attempts are kept or dropped
whole, so at `transition` level every call of a kept attempt is kept. Dropped
model calls count as `exclusions.balance`. Attempts with outcome `unknown`
cannot be paired and are dropped. A task with only one of `success` and
`failure` keeps nothing, is reported with `singleOutcome` true and is never
padded. `balanceReport` lists every task in `taskId` order with its attempt
counts (`successes`, `failures`, `unknown`), `keptPerOutcome` and `dropped`
(attempts). The terms gate runs on every candidate before balance, so host-model
output that balance would drop is still refused.

`check_manifest` enforces the arithmetic: for every report row,
`keptPerOutcome` is `min(successes, failures)`, `singleOutcome` is true exactly
when one of the two counts is zero, `dropped` is `successes + failures + unknown
- 2 * keptPerOutcome`, and the dataset holds exactly `keptPerOutcome` distinct
attempts of each of `success` and `failure` for the task and none `unknown`;
every kept task is reported; a `rollout` export with `balance: equal` has a
non-empty report and with `balance: none` an empty one.

## Terms decision record (T008)

A non-fixture unit exports only under an owner terms decision record (E5,
OD-1). OD-1 is deferred: Agent Braid ships no record, and none says any
provider permits training. The record is a private regular file (owner only, no
group or other bits) of at most 16 KiB under `<plugin home>/lightning/terms/`,
both of whose directories (`lightning/`, `terms/`) must be private too; it is
opened without following a symbolic link and read bounded to 16 KiB plus one
byte, then checked on the open file descriptor. It is named for the
export by its relative path `terms/<name>.json` (`[A-Za-z0-9][A-Za-z0-9._-]*`).
Exact keys, no duplicates:

| Field | Rule |
|---|---|
| `schema` | const `braid-lightning-terms-decision/v0.1` |
| `provider` | the provider whose terms were reviewed; 1-256 characters without control characters |
| `host` | `claude-code` \| `opencode`: the host whose units it covers |
| `models` | non-empty list of distinct model ids (at most 64); a unit is covered only when its attempt's `attempt_start` model id is listed |
| `terms` | exactly one of `{version}` or `{url}` (`https://`) |
| `reviewedOn` | owner review date, `YYYY-MM-DD` |
| `validUntil` | last date the owner relies on the review, `YYYY-MM-DD` |
| `outcome` | `permits-training` \| `forbids-training` \| `undecided` |

The gate checks the record on the export's UTC day: it must parse, have
exactly these fields, satisfy `reviewedOn` ≤ day ≤ `validUntil` and have outcome
`permits-training`. Each non-fixture unit must then match the record's `host`
and one of its `models`; a unit with no recorded model, another host or another
model is not covered. Any failure refuses the whole export with
`terms-gate-missing` before anything is written, with a text that names no path
or field value. When at least one exported record is `host-model`, the manifest
`termsDecision` is `{path, sha256}` of the record bytes; a fixture-only export
cites none, and `check_manifest` refuses a cited `{path, sha256}` that is not
the record the gate read and verified. One record covers one host: units of two
hosts need two exports. `provider` is informational: binding is by `host` plus
exact model id only. The host and model come from the ingested trace data (the
rollout record and the attempt's `attempt_start` event) and are not
independently attested.

## Retention and purge

Exported files are outside SPEC-074 purge; the owner deletes them.
`agent-braid lightning purge` lists the manifests that cite a purged run.

## Upstream mapping

`rollout_adapter.trace_aggregator_level` → `level`;
`trajectory_max_prompt_length`/`trajectory_max_response_length` → character
bounds with limit `truncated`; token-ID prefix merge → only when all turns have
token IDs, else `text-level-merge`.
