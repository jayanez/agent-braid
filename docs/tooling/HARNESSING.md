# Experimental harness CLI

Status: experimental, read-only advisory views (SPEC-049 T009). Ordinary-use
activation awaits the SPEC-049 T007 human promotion or no-go decisions. Nothing
here is native, activates a profile, promotes a candidate or grants anything.

The `agent-braid harness` command group (`python -m agent_braid harness ...`)
exposes the offline Braid Harness laboratory. Every command prints one JSON
object on stdout with `executionAuthorization: false`:

- exit 0: `{"status": "ok", ...}`;
- exit 2: `{"status": "refused", "reason": "<fixed-code>"}` for invalid,
  unverifiable, unreadable or oversized input. Argument-usage errors also exit 2,
  but print usage on stderr and nothing on stdout.

Any other exit is an internal bug; it is not converted into a refusal.

## Advisory views (SPEC-049 T009)

These four commands only read. They write nothing, hold no lock, and read no
clock, host, model or network. The parse and verify rules come from the T003
(`harness_evaluation`) and T013 (`harness_promotion`) modules.

### `capabilities`

Takes no input. Lists every `harness` command with its effect. Only `prepare`
has one: it creates one new private candidate directory. The output also states
`experimental: true`, the T007 activation status, `automaticPromotion: false`,
`pluginOrMcpSurface: "none"` and `globalHostInstructions: "untouched"`.

### `registry-status REGISTRY`

Reads a T013 profile registry file, at most 1 MiB, regular and not a symlink.
It is decoded with `ProfileRegistry.from_bytes`, so it must be the exact
canonical bytes. Its journal is replayed and its decision hashes are checked.
The output has:

- the registry `sha256` and `scope`;
- `active`: the active decision hash and its profile, or `null`;
- `pending`, `previous` and `revokedEvidence`;
- one row per recorded decision: decision, actor, decided cohort, `decidedAt`;
- a journal summary: entries, last event, last tick.

Common refusals: `input-unreadable`, `input-too-large`, `invalid-json`,
`non-canonical`, `invalid-registry`, `decision-hash-mismatch`.

An active profile is advisory configuration, never a grant. Actor, identity,
effects and safety counts are self-asserted; records prove binding, not
authenticity. The view does not resolve a profile against a current identity.
`begin`, `commit`, `rollback` and revocation stay library calls under a human
decision.

### `evaluation-summary REPORT [--sha256 HASH]`

Reads a T003 evaluation report, at most 1 MiB. A given `--sha256` is checked
against the raw bytes first. The report must then be canonical JSON with format
`braid-harness-evaluation-report/v0.1`, `executionAuthorization: false`, a known
cohort, full-hash registration and cost-report identities, and the summarized
keys with non-negative integer counts. Nested values are copied as decoded. The
output has:

- the report hash, `registrationSha256`, cohort, `costReportSha256`, the
  pending endpoints and the row count;
- per stratum: units, lineages, per-arm outcome counts and rates with the
  missing-outcome sensitivity bounds;
- per comparison: pairs, the worse-pair upper bound and the noninferiority
  status and verdict.

With `--sha256`, a matching trusted hash reports `authenticity: "hash-matched"`;
a mismatch refuses `record-drift`. Without it, `authenticity` is `"unverified"`.
Other refusals: `invalid-json`, `non-canonical`, `invalid-evaluation`,
`invalid-hash`.

The report is self-asserted. Strata, rows and verdicts are not re-derived from a
registration, T011 verdict records or T012 costs; the CLI has no codec for
those inputs. No promotion follows from any verdict.

### `evidence SPEC_DIR`

Inventories `SPEC_DIR/evidence/` against `SPEC_DIR/tasks.md`. `SPEC_DIR` and
`evidence/` must be real directories. The walk goes by directory descriptor, so
no path is looked up twice, and accepts regular files only. Its bounds are 256
files, 1,024 listed entries (files and directories), `evidence/` plus three
nested subdirectory levels, and 1 MiB per file. Refusals:

- `input-unreadable`: a missing directory or `tasks.md`, a symlink or a
  special file;
- `too-many-entries`, `too-deep` or `input-too-large`: a bound is exceeded;
- `invalid-tasks`: `tasks.md` is not UTF-8.

The output has:

- each file's path, size, SHA-256, whether it is a JSON object
  (`jsonObject`), and its top-level `task` and `executionAuthorization` when
  present;
- each `- [ ]` or `- [x]` task line, with whether `evidence/<task>.json`
  exists;
- `anomalies`: a checked task without evidence, or a file claiming
  `executionAuthorization: true`.

Hashes bind bytes. File contents, claims and checkbox state are not verified.

## Laboratory commands (SPEC-048)

`inspect`, `validate`, `compare`, `status` and `recover-inspect` are read-only
views of laboratory records and attempt journals. `prepare` imports one verified
candidate into a new private directory, and that is its only effect. Admission,
reservation, dispatch and reconciliation remain with the separately reviewed
operator contract.

## Limits and what is not provided

- Nothing native: no host, model, provider, route or paid call.
- No activation and no promotion. `AUTOMATIC_PROMOTION` is false. Human
  decisions are SPEC-049 T007, and the automatic-policy assessment is T008.
- No grants, no edits to global host instructions, no plugin and no MCP
  surface. A plugin or MCP extension of these views needs its own versioned
  contract and review first (SPEC-049 T009; spec SC-008).
- The SPEC-049 record shapes are still the draft proposals in
  `specs/049-harness-evaluation-learning/contracts/interface.md`. These views
  read the shapes the T003 and T013 modules emit, and may change when those
  contracts are versioned.
