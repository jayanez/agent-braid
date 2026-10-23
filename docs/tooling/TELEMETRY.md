> **Candidate boundary:** The commands and behavior documented here describe the telemetry source change reconstructed on rewritten develop `e474320eb763c33846665a0870677977b47d7a06`. They do not record an installation or native-host observation on this new candidate. Historical evidence remains bound to `4f0a6bf40779` / `b3809cbbaa0a`; current candidate validation and admission are pending. Pilot **NO-GO**.

<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Local technical telemetry

The [canonical owner decisions](../../specs/046-local-technical-telemetry/owner-decisions-20261016.md) keep the pilot **NO-GO** and T017/T018/T010 open. They grant no host/provider launch or collection consent and do not change the preview/digest installation flow or default-off telemetry.

**Status:** SPEC-047 source integration candidate; [existing b2cf Luna review](../../specs/047-local-technical-telemetry/integration-review.md) completed. Integration-delta review/validation, native admission and final acceptance remain separate. Telemetry is **off by default**, uses only local storage and has no upload service, daemon or additional provider cost.

## Choose consent

For one analysis, choose `--telemetry local`. Omit it or use `--telemetry off` to collect nothing. No environment variable, skill or report command enables collection.

```sh
agent-braid analyze /absolute/input.json --format text --telemetry local
agent-braid analyze-git /absolute/git-request.json \
  --provenance-output /absolute/private/provenance.json --telemetry local
```

The new portable MCP service accepts `agent-braid tooling serve --source-root /absolute/repository --result-root /absolute/private/results --telemetry local`. To persist that choice in its host configuration, add `--telemetry local` to `tooling configure|install|update`, inspect the preview and repeat the exact selection with its digest to apply. Preview and installation do not start collection. Consent belongs to that configured server process; direct CLI analyses still require their own flag. Repeat the flag on updates to retain local consent; the default selection is off. Use a previewed update with `--telemetry off` to disable future server collection. Restart the configured server separately when authorized; this documentation does not launch it.

The native plugin persists its consent with a previewed `plugin setup --telemetry local|off` and records its delegated workspace calls as surface `mcp`; see [native plugins](NATIVE_PLUGINS.md#local-telemetry-consent). `tooling doctor` reports requested and statically configured modes from the selected server arguments, retention and no-upload policy without reading or creating metrics. `telemetry status` describes storage and default consent; it cannot infer modes of other running processes. Skills only guide existing tools and never activate telemetry or collect metrics themselves. The legacy `agent_braid.mcp_runtime` endpoint is outside coverage.

## What is retained

The store at `~/.local/share/agent-braid/telemetry/` contains SQLite daily counters and coarse duration histograms for portable MCP tool invocations and CLI `analyze` / `analyze-git`. CLI timing begins after argument parsing and covers dispatched input reading, analysis and output; MCP timing covers the service invocation through its envelope. Exact durations exclude the final store write, whose added cost is measured separately. `ok` means interface completion, not execution authorization or a positive domain verdict. Protocol/schema refusals that never reach the service invocation are outside coverage. It counts reliability outcomes (ok/refused/error/cancelled/unknown) and only the four analyzer summary categories: independent-candidate, ordered, conflicting, unknown. Missing/incomplete summaries, including results returned by artifact reference, are counted as unavailable. Internal calls are not counted again. Discovery, prompts, resources, parsing errors before CLI dispatch, forecasts and external hosts are outside coverage.

No requests, full results, exceptions, code, prompts/responses, paths, URLs, names, commits, credentials or repository/user/team identifiers or hashes enter the store. Durations become fixed bins: ≤1, ≤10, ≤100, ≤1000, ≤10000 and >10000 ms; exact durations and individual event order are discarded. Daily aggregates can still reveal activity patterns and do not guarantee anonymity.

Storage uses private 0700/0600 permissions and refuses symlink/hardlink, repository, public, corrupt, oversized or busy destinations. It is intended for owner-controlled local POSIX filesystems (macOS/Linux); it refuses telemetry on unsupported systems while leaving analysis results intact. The main SQLite file is capped at 4 MiB with headroom for its DELETE rollback journal and lock under a 10 MiB total. FULL auto-vacuum and secure deletion reclaim free pages on commit without creating a VACUUM transient database. Each of the local-total, unexported-delta and imported tables has at most 4096 cells; at most 2048 unexpired batch IDs are retained. Capacity failures drop optional measurements and never change the product response.

The current UTC date and previous 29 dates are retained. Enabled writes and management commands expire data; no background process deletes inactive files exactly at their anniversary. Existing expired rows are securely deleted on the next successful operation. Collector faults leave product outputs, permissions, MCP envelopes and exit codes intact. Known failures are available only in the observing process's memory; a later CLI process reports its own count, not a recovered lifetime total. Crashes before finalization and other-process losses remain unknown. The store lock waits at most 250 ms; this can add latency under contention. SQLite also has a 250 ms busy timeout, and stalled filesystem calls have no separate hard deadline.

## Inspect and exchange aggregates manually

```sh
agent-braid telemetry status --format json
agent-braid telemetry report
agent-braid telemetry report --format json
agent-braid telemetry export /absolute/private/telemetry-batch.json --format json
agent-braid telemetry merge /absolute/private/received-batch.json --format json
agent-braid telemetry purge --format json
```

Create/select a private parent directory outside repositories for export. Export creates a private local file; it never sends it anywhere. Only incremental, previously unexported local cells are drained. Two batches may cover the same date but contain disjoint measurement sets. Imports contribute to reports and are never re-exported, avoiding transitive overlap. Copy a batch unchanged to another local store for explicit merge. Strict schema, finite integer bounds, fixed enums, valid dates, row and 1 MiB input limits apply. Imported aggregates are self-reported; these checks cannot authenticate their origin or detect copies deliberately assigned a different ID. Unknown fields and duplicate JSON members refuse (exit 2 with a fixed diagnosis); successful management commands return 0.

A fresh random UUID v4 identifies each batch; there is no persistent installation identifier. Reimporting an unchanged batch is a no-op; the same ID with altered data refuses. Local exports are remembered so importing your own export cannot double-count it. A failed write retains the same pending batch for retry; retry to a valid new file, or the same file if it contains the complete matching bytes. Resolve/remove a partial user-owned output explicitly before retry. A pending batch is discarded whole when its oldest date expires, and its discarded call count is reported; delivery before a failed acknowledgement can remain unknown. This may discard newer export deltas in that batch; the report's retained local totals remain separate.

Each retry synchronizes the matching file itself and its parent directory before clearing the pending export. A synchronization failure preserves the pending batch. Import and retry reads validate the opened regular file with no-follow/nonblocking flags, so a final-path replacement by a symlink or special file is refused. Imported inputs need not be private or outside repositories. When required secure-opening flags are unavailable, management commands return the fixed refusal diagnosis; export checks directory-sync support before draining a batch. Failed export-writer initialization closes the descriptor and retains the pending batch for retry. Keep parent directories under owner control; protection against a hostile process rewriting ancestor paths under the same OS identity is outside this storage domain. Merge deduplication compares canonical JSON content: whitespace/object-key order is insignificant, while row order remains significant.

Uninstall removes receipt-owned integration assets and keeps metrics. `purge` securely clears local cells, pending exports and deduplication and truncates its free pages; it leaves an empty private store. Stop/disable separately authorized active collectors first if you need it to remain empty. Purge resets deduplication, so importing old batches afterwards can count them again. Exported files, filesystem snapshots and backups are user-managed and are not removed or revoked by purge. Unexpired batch IDs are retained until their last contained date expires; expired imports refuse.

## Evidence boundary

These are product diagnostics. They are not complete native process receipts, complete-cost accounting, experimental rows, learned-model inputs, anonymity certification or scientific results. SPEC-034–037/045 keep their own consent/admission contracts. SPEC-044 keeps native inventory/loading/use, 108 attempts, CLI baseline, human evaluation and founder acceptance separate. The prior SPEC-044/T004 closure remains bound to `482fbcc`; [new-candidate admission](../../specs/044-ai-tooling-evaluation/candidate-admission-matrix.md) remains pending.

See [SPEC-047](../../specs/047-local-technical-telemetry/spec.md), [data contract](../../specs/047-local-technical-telemetry/data-contract.md), [validation plan](../../specs/047-local-technical-telemetry/validation-plan.md) and [M4.5 alignment](M45_ALIGNMENT.md).

The [synthetic overhead procedure](../../specs/046-local-technical-telemetry/measure_overhead.py) measures warm CLI/MCP calls with alternating off/local modes. [Recorded measurements](../../specs/046-local-technical-telemetry/evidence/review-overhead-final.json) are descriptive for one local synthetic fixture, not a production or native-host latency guarantee.
