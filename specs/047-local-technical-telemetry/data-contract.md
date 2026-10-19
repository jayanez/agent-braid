# Local telemetry data contract v1

The private store owns daily aggregate cells, local export deltas, batch deduplication entries and one crash-recoverable pending export. Cells contain exactly `day` (UTC date), `surface` (cli|mcp), `operation` (fixed covered tool/command or other), `outcome` (ok|refused|error|cancelled|unknown), `metric` (calls|duration|classification|missing-summary), `bucket` (fixed enum for its metric) and a positive bounded integer `count`. No event row or event order is retained. Durations use coarse millisecond bins (≤1, ≤10, ≤100, ≤1000, ≤10000, >10000); exact durations are discarded. Analyzer categories are independent-candidate, ordered, conflicting and unknown; arbitrary metadata is never traversed.

Schema `agent-braid-local-telemetry-batch/v1` contains exactly `schema`, `batchId` (fresh random UUID v4, no installation identity), `rows`. Strict allowlists and integer/date/count/input-size bounds apply before merge. Local exports drain only unexported local deltas in a transaction; imports are never exported, preventing transitive overlap. Each export is a disjoint measurement set even if date ranges overlap. The same batch ID with altered canonical JSON content refuses; insignificant whitespace and object-key order do not change the digest, while row order does. Source/destination deduplication entries last until all contained dates expire. Export retries recover the same pending batch. A local store rejects its own batch as a duplicate to avoid double counting local observations. Purge explicitly resets deduplication; merging old batches after purge can count them again.

Before acknowledging delivery, both a newly written export and an existing matching retry file are synchronized with `fsync`, followed by its parent directory. A file or directory sync failure retains the pending batch for another retry. Import and retry reads open the final path with no-follow/nonblocking flags and validate the opened regular file's size; retry destinations also retain private ownership/permission/hardlink checks. Import inputs need not be private or outside repositories. Parent paths must be owner-controlled: these checks do not protect against a hostile process rewriting ancestor directories under the same OS identity.

Retention keeps the current UTC date and previous 29 dates. Maintenance runs on enabled writes and management operations, never from a daemon. Inactive files can contain expired bytes until the next operation. Secure deletion and FULL auto-vacuum reclaim expired/purged cells at commit without a VACUUM transient database; external exports/backups are user-managed and cannot be revoked by local purge. Reports never imply complete measurement: process death before finalization and losses in other/terminated processes remain unknown; known collector failures are counted only in memory in the observing process.

Storage has a private 0700 directory, 0600 regular files, no symlink/hardlink destinations and no repository ancestors. SQLite uses DELETE journaling, bounded database pages and a process lock. The main database is limited to 4 MiB, leaving sufficient headroom for its bounded rollback journal and lock under the 10 MiB total ceiling. Refuse unsafe/corrupt/oversized storage; drop telemetry without changing product behavior. Export files are explicit private local artifacts outside repositories and the store, not automatic transmissions. See the implementation for the exact hard input/cell/batch limits.

## SQLite format and space rationale

The main file carries application ID ABT1 and user_version 1. Foreign nonempty SQLite databases refuse; an empty interrupted initialization can be initialized safely. Initialization commits independently of the first optional measurement, so a refused write leaves a valid empty store. Each connection enforces 4096-byte pages, at most 1024 pages, DELETE journaling, FULL auto-vacuum, secure_delete and in-memory temporary work. No VACUUM command or attached database is used. Reports sum local totals and imported totals; individual stored/exported cells are capped at 10^12, and a combined report cell can reach twice that value. Batch row limits bound its total arithmetic.

SQLite documents that [VACUUM can require twice the original size as additional free space](https://www.sqlite.org/lang_vacuum.html), while [FULL auto-vacuum truncates free pages at each commit](https://www.sqlite.org/pragma.html#pragma_auto_vacuum). Its [max_page_count pragma](https://www.sqlite.org/pragma.html#pragma_max_page_count) bounds main-file pages. These source facts inform the 4 MiB main-file plus rollback-journal/headroom design; they are not a native platform/storage acceptance result. Context7 resolution was attempted on 2026-10-16 and unavailable due to quota; the official SQLite documentation was used directly.

Imports are untrusted self-reported numeric aggregates. Structural validation and batch deduplication cannot authenticate their origin or prevent a sender from copying/re-identifying the same data into a different batch. Merge unchanged original batches only; there is no source-identity or semantic-overlap proof.
## Closed export enums and version impact

| Field | Allowed values |
|---|---|
| surface / operation | cli: analyze, analyze-git; mcp: analyze-work, analyze, prepare, status, execute, recover, verify, other |
| outcome | ok, refused, error, cancelled, unknown |
| metric / bucket | calls: all; duration: le-1ms, le-10ms, le-100ms, le-1000ms, le-10000ms, gt-10000ms; classification: independent-candidate, ordered, conflicting, unknown; missing-summary: unavailable |
| count | Strict positive integer at most 10^12; booleans/floats are invalid |
| day | Canonical YYYY-MM-DD UTC date within the retained 30-date window |
| batchId | Canonical lowercase hyphenated UUID v4, freshly generated per export |

Classification/missing-summary cells are allowed only for the covered analyzer operations. Zero classification counts have no stored cell; a missing-summary cell records unavailable measurement rather than an assumed zero. `ok` means successful interface completion under the existing envelope/exit contract; it does not mean execution authorization or a positive domain verdict.

Illustrative shape (the date/UUID are examples, not a reusable batch):

```json
{"schema":"agent-braid-local-telemetry-batch/v1","batchId":"12345678-1234-4234-8234-123456789abc","rows":[{"day":"2026-10-16","surface":"cli","operation":"analyze","outcome":"ok","metric":"calls","bucket":"all","count":1}]}
```

Duplicate object members and duplicate cell keys refuse. The batch digest uses canonical JSON with sorted object keys, compact separators and a final LF; row order remains significant. No fields beyond schema/batchId/rows and the seven declared cell members are allowed. A batch has at most 4096 cells and at most 1 MiB of input; at most 2048 unexpired batch identities are retained. Imported data is not relayed. Use the unchanged generated original rather than constructing or re-identifying data manually.

This v1 exchange and ABT1/user_version-1 store are new contracts; prior analyzer/MCP result schemas and legacy MCP remain unchanged. Installation receipt metadata is additive through the existing preview/digest lifecycle. There is no old product-telemetry database to migrate in this delivery. Future incompatible store/batch changes need an explicit version and migration decision; foreign nonempty databases are never silently converted.
