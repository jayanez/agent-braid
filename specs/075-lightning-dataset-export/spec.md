# SPEC-075: Lightning dataset export

**Milestone:** BL.5 — Lightning dataset export.

**Status:** draft, converged 2026-11-16 (T012). Depends on SPEC-074 (BL.4,
trace consent and `agent_braid/lightning_adapter.py`). Owner decisions: T001
(2026-11-14) E1–E5 accepted, OD-2 equal 1:1; OD-3 (2026-11-16) Q1 A, Q2 A; OD-4
(2026-11-16) additive purge output. OD-1 (host usage-terms review) is deferred,
so the terms gate ships closed and no host-model output exports.

## Purpose and scope

Build reproducible datasets from consented, redacted Braid Lightning traces so
that a later, separately approved training step (SPEC-076, deferred) or an
external supervised fine-tuning job can consume them. This is engineering, not a
research protocol; no training runs here.

In scope:

- module `agent_braid/lightning_export.py` (standard library only);
- two dataset kinds: `supervised` (SFT chat `messages` JSONL) and `rollout`
  (per-rollout records with reward and attempt metadata);
- aggregation levels `transition` and `trajectory`, porting the concepts of the
  upstream v1 trace aggregator (`agentlightning/verl/rollout_adapter.py`);
- a dataset manifest with per-record hashes, source rollout, group and task IDs,
  consent level, redaction version and deterministic ordering, published as
  `schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json`;
- success/failure balancing per task for `rollout` exports;
- CLI `agent-braid lightning export`, refused with `export-disabled` unless the
  configuration has `export.enabled` set to `true`;
- source retention recorded in the manifest, with refusal of records past
  retention;
- a terms-of-use gate recorded before any host-model output is exported.

Exclusions:

- Any training, fine-tuning, gradient step, GPU code or model download
  (SPEC-076, deferred).
- Traces without recorded consent, or not passed through the SPEC-074
  redaction pipeline.
- Upload or publication of datasets anywhere; export writes local files only.
- Changes to consent, redaction or retention semantics (SPEC-074 owns them).
- Any claim that an exported dataset improves a model.

## Authorities

- [CONSTITUTION.md](../../CONSTITUTION.md), Articles 13–16, 19, 20, 23, 24.
- [Program](../070-braid-lightning-foundations/program.md) fixed boundaries.
- [SPEC-070](../070-braid-lightning-foundations/spec.md) store and
  [configuration contract](../070-braid-lightning-foundations/contracts/lightning-config.md).
- [Research](../070-braid-lightning-foundations/research.md) §3 decisions 1 and 5.
- ADR 0021 (EUR 0), ADR 0034 (System One advisory boundary), proposed
  ADRs 0039–0042 (SPEC-070 REQ-001).
- SPEC-034 to SPEC-037 "no fine-tuning" statements, scoped to forecasting.
- [contracts/dataset-manifest.md](contracts/dataset-manifest.md).

## Clarifications

Owner review, T001, 2026-11-14 ([record](reviews/owner-t001-20261114.md)):
E1, E2, E3 and E5 accepted as written; E4 accepted with OD-2 decided (equal cap
1:1 per task, no ratio parameter); OD-1 deferred. `human_review` stays
`pending`.

Design decisions:

- **E1 — Input boundary.** Export reads only records returned by
  `lightning_adapter` with consent `redacted` (the only content level SPEC-074
  defines; the vocabulary is `none` | `redacted`) and a recorded redaction
  version. Consent `none` yields no record; the reason `consent-none` is counted
  in the manifest, never silently dropped.
- **E2 — Prefix merging.** Trajectory aggregation merges consecutive turns
  by token-ID prefix only when every turn carries token IDs (never true for
  hosted Claude Code or OpenCode). Otherwise merging is text-level on the
  canonical message list, and the manifest declares the limit
  `text-level-merge` per record.
- **E3 — Ordering.** Records sort by `(taskId, groupId, rolloutId, attemptId,
  turnIndex)`; JSONL lines use `trace_adapter.canonical_bytes`. No timestamps or
  host paths enter dataset bytes; `generatedAt` is excluded from the manifest
  digest.
- **E4 — Balance.** Balancing applies to `rollout` (trajectory) exports only:
  per task, successes and failures are capped to equal counts (default) with a
  deterministic seeded choice: each task keeps `min(successes, failures)` records
  of each outcome (1:1; OD-2, no ratio parameter); tasks with only one outcome
  are reported, not padded. Rationale: the SWE-Gym finding that unbalanced success-only data
  skews behaviour (research §2). `supervised` exports are not balanced: they
  include only records with `d4FirstAttempt` true, or every line carries an
  explicit `outcome` field. No claim is made that either choice benefits a
  model.
- **E5 — Terms gate.** Exporting host-model output requires an owner decision
  record naming provider, terms version or URL, review date and outcome. Without
  it the CLI refuses with `terms-gate-missing`. This is a legal question, not a
  scientific one.

Decisions:

- **OD-1 — Host usage-terms review (open, deferred 2026-11-14).** For each host
  provider (Anthropic for Claude Code; each OpenCode backend), may outputs be
  used to train or fine-tune models, including local open models? Owner
  decision; legal, not scientific. No decision is recorded: BL.5 ships with the
  terms gate closed, so only fixtures and non-host content export. No terms
  decision record is committed and no provider is said to permit training; the
  gate's permitting branch is tested only with synthetic records in temporary
  directories that name no real provider.
- **OD-2 — Balance default (decided 2026-11-14).** Equal cap 1:1 per task (E4);
  no ratio parameter.
- **OD-3 — Canaries the SPEC-074 redactor lets through (decided 2026-11-16,
  [record](reviews/owner-t010-20261116.md)).** Q1 A: another user's home path
  (`/Users/<name>/`, `/home/<name>/`) anywhere in the final exported bytes aborts
  the export with `canary-detected` (export-side check; SPEC-074 unchanged). Q2 A:
  literal secrets not passed at ingest and secrets of unknown shape are a
  documented residual risk, not detected.
- **OD-4 — Additive `lightning purge` output (decided 2026-11-16).** The owner
  approved adding `citingDatasets` and `datasetsNote` to the output of the
  SPEC-074 `lightning purge` command, in `lightning_cli.py`, as REQ-013
  requires; SPEC-074's spec, store, adapter, redactor and config are
  unchanged.

## Requirements and acceptance scenarios

### REQ-001 — Owner review

Spec, plan, contract and manifest schema name are reviewed by the owner before
implementation.

**SC-001:** Given this specification, plan and contract, when the owner reviews
them against the program boundaries and Articles 13–16, then E1–E5 are accepted
or amended and OD-2 is decided. Verification: procedure_001; T001.

### REQ-002 — Consented, redacted input only

Export consumes only SPEC-074 adapter output with consent `redacted` and a
redaction version; everything else is excluded and counted by reason
(`consent-none` among them).

**SC-002:** Given a fixture store mixing consent `redacted`, consent `none`, unconsented
and unredacted traces, when export runs, then only the consented redacted traces
appear and the manifest counts each exclusion reason. Verification:
procedure_002; T003.

### REQ-003 — Supervised dataset

`supervised` writes one JSONL line per example: `{"messages": [...]}` with roles
`system|user|assistant|tool`, plus a record ID referencing the manifest. It
includes only records with `d4FirstAttempt` true, unless `--outcome-field` is
given, in which case every line carries an explicit `outcome` field.

**SC-003:** Given fixture trajectories, when exported as `supervised`, then
every line validates against the record shape in the contract and its hash
matches the manifest. Verification: procedure_003; T004.

### REQ-004 — Rollout dataset and aggregation levels

Kind `rollout` writes per-rollout records with reward vector, attempt and status.
`--level transition` yields one record per model call; `--level trajectory`
merges an attempt into one record (E2). A rollout has one attempt
(VALID_TRANSITIONS allows no retry), so this is one record per rollout; export
refuses with `source-invalid` a rollout with more than one attempt.

**SC-004:** Given a three-turn rollout with and without token IDs, when exported
at both levels with kind `rollout`, then transition yields three records, trajectory yields one (one per attempt), and
the text-level record carries `limits: ["text-level-merge"]`. Verification:
procedure_004; T005.

### REQ-005 — Manifest schema

The manifest validates against
`schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json`
(created by the lead) and carries per-record hashes, source IDs, consent level,
redaction version, ordering key, exclusion counts and limits.

**SC-005:** Given an exported dataset, when its manifest is validated, then it
passes; a manifest missing a record hash or redaction version fails.
Verification: procedure_005; T002, T006.

### REQ-006 — Determinism

Two exports of the same store, filters and seed are byte-identical (dataset and
manifest, excluding `generatedAt`).

**SC-006:** Given one fixture store, when exported twice, including once with
shuffled input order and a different working directory, then all bytes match.
Verification: procedure_006; T006.

### REQ-007 — Success/failure balance

For `rollout` exports only, records are balanced per task per E4 and imbalance
is reported; `supervised` exports are never balanced (E4).

**SC-007:** Given a task with 5 successes and 2 failures, when exported as
`rollout` with the default, then 2 of each are kept by a seeded choice, stable across reruns, and
the manifest reports the dropped counts. Verification: procedure_007; T007.

### REQ-008 — Terms-of-use gate

Host-model output exports only with a recorded owner terms decision (E5, OD-1).

**SC-008:** Given host-model traces, when export runs without a decision record,
then it refuses with `terms-gate-missing` and writes nothing; with a record whose
outcome permits training, it proceeds and the manifest references the record
hash. Verification: procedure_008; T008, T010.

### REQ-009 — CLI

`agent-braid lightning export --run <id>|--all --kind supervised|rollout
--level transition|trajectory --out <dir> [--seed N] [--balance equal|none]
[--outcome-field]` with bounded, value-free refusals; it refuses with
`export-disabled` unless the configuration has `export.enabled` set to
`true`.

**SC-009:** Given the CLI, when called with valid and invalid arguments, then it
exports or refuses with a fixed code; it refuses with `export-disabled` when
`export.enabled` is not `true`, and refuses an existing non-empty output
directory, symlinks and paths outside the plugin home or the given directory.
Verification: procedure_009; T009.

### REQ-010 — Canary corpus clean

Exported bytes are scanned against the SPEC-074 secret canary corpus before the
manifest is finalised; any hit aborts and removes partial output.

**SC-010:** Given a fixture with a planted canary that survived redaction, when
export runs, then it aborts with `canary-detected`, leaves no dataset file, and a
clean fixture exports with `canaryScan: "clean"`. Verification: procedure_010;
T010.

### REQ-011 — Boundaries

Export opens no socket, starts no process, loads no model and adds no runtime
dependency; it is never callable from the MCP server.

**SC-011:** Given the module, when tests run with sockets and subprocess
patched to fail and the MCP tool list is inspected, then export succeeds offline
and no MCP tool exposes it. Verification: procedure_011; T011.

### REQ-012 — Documentation and converge

Documentation states what datasets are, their limits and the terms gate; Spec
Kit artifacts converge.

**SC-012:** Given the final candidate, when `speckit-converge` and link checks
run, then requirements, tasks, procedures and evidence agree and no
undocumented claim remains. Verification: procedure_012; T012.

### REQ-013 — Source retention

The manifest records, per source run, the SPEC-074 retention bound
(`traces.retentionDays`) and the expiry date of each record's source; export
refuses with `retention-expired` any record whose source is past retention.
Documentation states that exported files are outside SPEC-074 purge and must
be deleted by the owner; `agent-braid lightning purge` lists the dataset
manifests that cite the purged run.

Exported files are outside SPEC-074 purge and must be deleted by the owner;
`lightning purge` lists them through the SPEC-075 export index (contract,
"Retention and purge"). The owner approved on 2026-11-16 the additive purge
output (`citingDatasets`, `datasetsNote`) in `lightning_cli.py`; SPEC-074's
spec, store, adapter, redactor and config are unchanged. The export refuses a
run from the exact expiry instant, one instant before the SPEC-074 sweep removes
it (fail closed).

**SC-013:** Given a fixture store with one record past retention, when export
runs, then that record is refused with `retention-expired`, the manifest
records retention per source, and a later `lightning purge` of the run lists
the manifest that cites it. Verification: procedure_013; T013.

## Scientific boundaries and compatibility

No hypothesis; datasets are artifacts, not evidence of model improvement. No
claim is made that a dataset, its balance or its record shape helps any model.
Additive: new module, CLI subcommand, experimental schema and a private export
index; the only change to an existing interface is the additive `lightning
purge` output (`citingDatasets`, `datasetsNote`, OD-4). `executionAuthorization`
stays false.

## Evidence and unresolved questions

Evidence is recorded per procedure under `evidence/`; procedure_001 is the T001
review record and procedure_012 the convergence. Unresolved: OD-1 (deferred; the
terms gate stays closed, no provider's terms are reviewed, no terms decision
record ships).

## Convergence findings (T012)

Read-only analysis of spec, plan, tasks, contract, schema and obtained evidence
at convergence (2026-11-16), over T001–T011 and T013 and their review rounds.
None blocks a requirement; each is stated so the owner's review sees it.

| ID | Finding | Effect |
|---|---|---|
| A1 | SPEC-074 records carry no redaction version, although E1 and the plan assumed one. | The builder defines `redactionVersion` as a digest of the SPEC-074 redactor's pattern sources and salt size (T006); it does not cover the redactor's code. SPEC-074 unchanged. |
| A2 | The frozen rollout reader notes `content-consent-required` both without consent and for an unlisted source. | The export reads the SPEC-074 gate's refusal itself to count `consent-none` and `no-consent` apart (T003). |
| A3 | OD-1 is deferred. | The terms gate (T004, T008) ships closed: every non-fixture unit refuses with `terms-gate-missing`; only `pipeline-only` fixture runs export; no record ships, no provider is described as permitted, and the permitting branch is tested only with synthetic temporary records. |
| A4 | A probe before T010 showed the SPEC-074 redactor lets through another user's home path, a literal secret not given at ingest, unknown-shape text and raw ids typed in content. | OD-3: Q1 A, any `/Users/<name>` or `/home/<name>` path (any case, inside longer paths too) refuses with `canary-detected`, fail closed, with false positives such as `/srv/home/x`; Q2 A, the rest is documented residual risk. The scan catches known shapes only. |
| A5 | The export's retention boundary is one instant stricter than the SPEC-074 sweep's, and a missing profile refuses although the sweep defaults to 30 days. | Kept on purpose (fail closed) and documented (T013). |
| A6 | REQ-013 needs `lightning purge` to list citing datasets. | One additive output change in `lightning_cli.py`, approved by the owner on 2026-11-16 (OD-4); the private export index (path, digest, runs) remains while a dataset exists and is pruned by a purge apply once it is gone. |
| A7 | REQ-004 said a trajectory merges a rollout; the state machine allows no retry. | Clarified to one record per attempt; a rollout with two attempts refuses with `source-invalid` (T005). |
| A8 | SC-009's "paths outside the plugin home or the given directory" was read as a canonical, symlink-free output inside an existing directory; exports are not confined to the plugin home, and `--level` is required as REQ-009 writes it. | Reported in #1391, not changed; a one-line change if the owner wants exports confined. |
| A9 | Several review rounds found test gaps that mutants exposed (for example a leaked `HOME` patch that broke another test module on CI, and the read-side permission check on the export index). | Fixed in the PRs and in T012; every patch is undone with `addCleanup`, and an isolation test compares global state (T011). |
| A10 | SPEC-074 behaviour (consent, redaction, pseudonyms, retention, purge) is assumed, not re-proven, by SPEC-075. | SPEC-075 evidence tests the export against the frozen SPEC-074 code only. |

Residual risks, plainly: the canary scan catches known shapes only; pattern-based
redaction cannot catch every secret or every piece of personal data; exported
files are outside purge and the owner must delete them; no dataset has been
built from real host output, and nothing here shows that any dataset or its
balance improves a model.
