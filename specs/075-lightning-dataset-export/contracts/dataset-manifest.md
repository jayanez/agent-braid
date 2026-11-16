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
| `retention` | object source run id → `{retentionDays, expiresAt}` | from SPEC-074; `expiresAt` is the UTC date `YYYY-MM-DD` of the instant the run expires (`createdAt` + `retentionDays` days); records past it are excluded and counted as `retention-expired`; one key per cited `runId` |
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

`export_dataset` reads, filters and writes the records, builds the manifest,
runs `check_manifest`, scans the final dataset and manifest bytes (T010, below)
and
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
date its run expires (`createdAt` + days); expired records are excluded (T013,
below). `balance` defaults to `equal` for `rollout` and is always `none` for
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

## CLI (T009)

```
agent-braid lightning export (--run RUN_ID ... | --all) --kind supervised|rollout
  --level transition|trajectory --out DIR [--seed N] [--balance equal|none]
  [--outcome-field] [--terms-decision terms/NAME.json] [--dry-run] [--home DIR]
```

The command refuses with `export-disabled` unless the profile's `export.enabled`
is `true`, which only a previewed `lightning init --export` sets; no profile,
an unreadable or invalid one, and any environment variable leave it disabled.
This is decided before the other arguments are parsed. The command parses its
own arguments: any argument error (unknown or abbreviated flag, bad choice or
integer, missing required flag, both `--run` and `--all`) is `invalid-argument`
with a fixed text that echoes no value, never the parser's message. `--help`
states that export is off by default and that no provider's terms have been
reviewed (OD-1). `--run`
repeats; `--all` takes every run in the store. `--level` is required (the
profile's `export.level` is not used as a default). `--terms-decision` names the
T008 record; the command reads it, never creates or modifies the `terms/`
directory or a record, and never prints a record's contents. `--dry-run` runs every check and
builds the manifest but writes nothing. `--out` must be a canonical path (no
symbolic link in any component, no `..`; on macOS `/tmp` and `/var` are
symbolic links, so use `/private/tmp` or a directory under the home) inside an
existing directory, and must
not exist or be an empty directory (`path-refused`, `output-not-empty`); the
check runs before the store is read. Success prints one JSON object of counts,
hashes and fixed fields (`status`, `kind`, `level`, `balance`, `seed`, `records`,
`exclusions`, `balanceReport`, `termsDecision`, `redactionVersion`,
`recordsSha256`, `digest`, `files`, `executionAuthorization: false`), never the
record entries, content, attempt pseudonyms, rollout ids or the output path;
task ids appear in `balanceReport` by design. A refusal prints `lightning refused (<code>):
<fixed text>` on stderr and exits 2; an unexpected error prints code `other` and
the text `Export refused`; an interrupt prints code `interrupted` and exits 130
(the temporary directory is removed, T006). There are no other flags.

## Canary scan (T010, OD-3)

After balance, the writers and `check_manifest`, and before the temporary
directory is created, `scan` reads the final `records.jsonl` bytes plus the
`manifest.json` bytes. It looks at the whole text, each field of each line, and
each two neighbouring fields joined (a value split across two fields), each with
its decoded views (URL decoding, `\uXXXX` escapes, base64 runs), as SPEC-074's
post-scan does. A hit on a SPEC-074 class (token shapes, bearer header, private
key block, e-mail address, the current `$HOME` read through `Path.home()` at
export time) or on another user's home path refuses the whole export with
`canary-detected`, and nothing is written (owner decision OD-3 Q1 A; no
redaction in the export). A home path is `/Users/` or `/home/`, in any letter
case, followed by a name segment of one or more characters other than
whitespace, `/`, `\`, quotes, `<`, `>`, `,`, `;`, `:` and `|` (a trailing `/` is
not needed), anywhere in the bytes, inside longer paths too. So
`/home/runner/work`, `/Users/Shared/x`, `/home/x`, `/mnt/c/Users/alice/f`,
`/System/Volumes/Data/Users/alice`, `/Volumes/D/home/bob`, `/Users/_svc/x`,
`/Users/.hidden`, `/Users/Ünal/x` and `/USERS/x` block, as do, fail closed,
`/srv/home/x`, `~/home/x` and URL paths such as `/api/users/42`; CI and shared
directories block too, unless the path is the current `$HOME`, which SPEC-074
turns into `~` when content is read. `/Users`, `/home/` alone and `/homework/x`
do not. Documented limits: a Windows path (`C:\Users\x\`) and a doubly escaped
`\/Users\/x` are not matched. The current home is redacted to `~` when the
adapter reads content, so a hit there means it escaped
redaction. The scan catches known shapes only. As the SPEC-074 privacy review
says, pattern-based redaction cannot catch every secret shape or every piece of
personal data (for example names in free text). Not detected (OD-3 Q2 A,
documented residual risk): a literal secret not given to the store at ingest,
free text of unknown shape, a raw attempt id typed inside content (content, not
the id field, which is always a pseudonym), and encodings nested twice or
more. `canaryScan: "clean"` therefore means "no hit for these classes",
not "free of secrets".

## Retention and purge (T013)

The retention bound is the profile's `traces.retentionDays` (1-90); a profile
without a valid bound, and a missing profile, refuse the export with
`retention-expired` (the SPEC-074 sweep would default to 30 days; refusing is
the intended fail-closed choice). A run expires at the instant `createdAt +
retentionDays` days. This is stricter than the SPEC-074 sweep, on purpose: the
export refuses the run from that exact instant, while the sweep removes it one
instant later (`createdAt < now - retentionDays` days). The export compares that instant with `now` in epoch
seconds (injectable in tests; the wall clock otherwise), so the host time zone
plays no part; `expiresAt` in the manifest is the UTC date of that instant, for
reading. A record whose run has expired (`now` at or after the instant) is
excluded and counted under `exclusions.retention-expired`; when every record is
expired the export refuses with `retention-expired` and writes nothing. The
terms gate still sees expired records first.

Exported files are outside SPEC-074 purge: purge never deletes a dataset, and
the owner deletes it. Each real export (not a dry run) first writes a private
index entry `<plugin home>/lightning/exports/<digest>-<hash>.json` (`0600`, in a
`0700` directory) holding `{schema, out, digest, runIds}`: the output path, the
manifest digest and the cited runs, no content. It is written atomically (a
temporary file in the same directory, then a rename) and removed if the dataset
write fails. `agent-braid lightning purge` (preview and apply, `--run-id` or `--all`)
then adds `citingDatasets`: each indexed dataset whose `manifest.json` still
exists, still matches its digest and cites a purged run, as `{manifest, digest,
citesRuns}`, plus a note that purge does not delete them. The listing is outside
the purge preview digest, so an export between preview and apply does not make
the preview stale. Deleted, moved, changed or forged entries are not listed (an
entry's `out` must be an absolute canonical path, without symbolic links, whose
`manifest.json` is a regular file and matches the digest). Purge apply removes
the index entries of datasets that are gone or changed; it never removes or
writes a dataset file, and a preview removes nothing. Residue: an entry, with
its absolute output path and run ids, stays in the index while its dataset
exists, also after the runs it cites are purged; it goes when the owner deletes
the dataset and a later purge apply runs. The `citingDatasets` and
`datasetsNote` purge output is one additive change in `lightning_cli.py`,
approved by the owner on 2026-11-16; SPEC-074's spec, store, adapter, redactor
and config are unchanged.

## Upstream mapping

`rollout_adapter.trace_aggregator_level` → `level`;
`trajectory_max_prompt_length`/`trajectory_max_response_length` → character
bounds with limit `truncated`; token-ID prefix merge → only when all turns have
token IDs, else `text-level-merge`.
