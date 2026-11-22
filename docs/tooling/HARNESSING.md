# Experimental harness CLI

Status: experimental, read-only advisory views (SPEC-049 T009). Ordinary-use
activation awaits the SPEC-049 T007 human promotion or no-go decisions. Nothing
here is native, activates a profile, promotes a candidate or grants anything.

![Braid Harness laboratory: admission, prepare, simulated fixture runner, hash-chained journal, observations, verifiers and an evaluation report; the native backend gate refuses until qualified and human promotion is not delivered](../assets/agent-braid-harness.svg)

Track state (2026-11-02, HAR.1 and SPEC-065 updated 2026-11-21): HAR.1 (SPEC-048)
has 15 of 15 tasks done; T008 closed on 2026-11-20 with the native Claude profile
qualified with limits in the laboratory and Codex refused. HAR.2
(SPEC-049) has 8 of 13 tasks done; the native pilot, cohorts, human promotion
decisions and per-axis publication remain open. Native Claude containment
(SPEC-065, ADR 0035) is qualified on one machine from 2026-11-17 until
2026-12-17T22:19:29Z and approved by the owner on 2026-11-21 with documented
limits; it authorizes no execution. Assurance profiles (SPEC-067) were approved by the owner on 2026-11-22 with documented limits; they are advisory and authorize nothing.
The HAR.2 native cohort (SPEC-049 T014) was inconclusive, so under SPEC-050 D7 the harness
stays experimental: nothing is promoted or activated, and the read-only harness MCP
surface (SPEC-077) is not published. HAR.3 adaptation (SPEC-050) is planning only. Extra
cash spend stays at EUR 0.

## Availability per host (2026-11-22)

| Surface | Claude Code | Codex | OpenCode | Pi / ThinkRail |
|---|---|---|---|---|
| This CLI, through the plugin's `launch` (`launch harness ...`) | yes | yes | yes | not installable yet (SPEC-081) |
| Harness skill an agent can discover | planned (SPEC-080) | planned (SPEC-080) | planned (SPEC-080) | planned (SPEC-081) |
| Harness MCP tool | no (ADR 0043 rejected) | no | no | no |
| Native harness sessions | laboratory only (SPEC-065), run by the owner | refused | none | none |
| Harness telemetry | after the next release (#1405) | same | same | — |

Today an agent uses the harness only when told to run the plugin `launch` from a
shell. Planned work, still documentation only:

- SPEC-080: a read-only skill in every host
  ([ADR 0044](../adr/0044-harness-portability-tiers-skill-surface.md));
- SPEC-081: Pi and ThinkRail;
- HAR.4 (SPEC-082 to SPEC-086): cross-host evaluation through Harbor containers with a
  macOS shadow ([ADR 0045](../adr/0045-hybrid-harness-evaluation-substrate.md)),
  regression gates, promotion pointers and OTel telemetry.

The [harnessing benchmark](../strategy/HARNESSING_BENCHMARK.md) explains the choices.

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

Every `harness` command accepts `--telemetry local` (default off) to count the
call in the local telemetry store by subcommand name, outcome and coarse
duration only; see [local telemetry](TELEMETRY.md).

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

## Experimental lifecycle library (SPEC-050 T011)

`agent_braid.harness_lifecycle` is an offline Python library, not a command. It
adds no CLI, plugin or MCP surface. It is disabled by default: nothing exists
until a human calls `install(root, opt_in=True, ...)` for one task-local scope.
Only `claude` is a supported host, because it is the only host with an observed
build; `codex` and unknown hosts are refused.

Everything it writes stays inside `ROOT/.braid-harness-lifecycle`, with
directories 0700 and files 0600, plus two kinds of short-lived working
directories in `ROOT`: one for staging an install and one for removal. Every
result has `executionAuthorization: false`, and `activate` always refuses.
Ordinary use stays unavailable, because the SPEC-049 T008 disposition is
deferred and the T009 production policy abstains with `pending-endpoints`.

- `migrate` stages a verified, admitted component profile only as the next
  linked version of the current one. `rollback` restores the prior profile only
  if its stored bytes still match the recorded hash. Every profile has a
  caller-fixed expiry tick.
- `check_drift` compares the source, host, model, tool and policy identity
  with the installed one. Any difference blocks migration and canaries until a
  human calls `requalify` with an evidence hash. That rebinds only the
  installation: a promotion decision made under the old identity stays stale in
  the registry.
- `begin_canary` and `observe_canary` run the T009 canary against the persisted
  T013 registry. `incident_stop` halts the installation and rolls the registry
  back, and only a human `clear_incident` lifts the halt. `revoke` withdraws
  registry decisions that cite the evidence and, if a caller-held T008 store is
  given, propagates the revocation through it.
- `retain` keeps a private record until a retention tick the caller must give;
  there is no default duration. Records are deleted only when a human calls
  `purge`. Nothing is exported.
- `uninstall` refuses unknown or linked content, then removes the whole
  installation and returns a hash receipt. `recover` finishes an interrupted
  install, uninstall or purge and deletes temporary or unreferenced files.
  `residue` lists anything left behind.

Limits:

- Operators, identities, retention ticks and evidence hashes are
  caller-asserted.
- Writes are serialized by a POSIX lock. A same-user process swapping
  directories between a check and a write is outside the threat model.
- Racing installs on one root are not handled.
- Human workflow usability, native hosts and any activation have not been
  observed.
