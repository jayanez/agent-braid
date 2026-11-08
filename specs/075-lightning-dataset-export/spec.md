# SPEC-075: Lightning dataset export

**Milestone:** BL.5 — Lightning dataset export.

**Status:** draft. Depends on SPEC-074 (BL.4, trace consent and
`agent_braid/lightning_adapter.py`). Open decision OD-1 (host usage-terms
review) blocks any export of host-model output.

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

Design decisions (proposed, for owner review in T001):

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
  deterministic seeded choice; tasks with only one outcome are reported, not
  padded. Rationale: the SWE-Gym finding that unbalanced success-only data
  skews behaviour (research §2). `supervised` exports are not balanced: they
  include only records with `d4FirstAttempt` true, or every line carries an
  explicit `outcome` field. No claim is made that either choice benefits a
  model.
- **E5 — Terms gate.** Exporting host-model output requires an owner decision
  record naming provider, terms version or URL, review date and outcome. Without
  it the CLI refuses with `terms-gate-missing`. This is a legal question, not a
  scientific one.

Open decisions:

- **OD-1 — Host usage-terms review.** For each host provider (Anthropic for
  Claude Code; each OpenCode backend), may outputs be used to train or
  fine-tune models, including local open models? Owner decision; legal, not
  scientific. Until recorded, only fixtures and non-host content export.
- **OD-2 — Balance default.** Equal cap (proposed) versus ratio parameter.

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
merges a rollout into one record (E2).

**SC-004:** Given a three-turn rollout with and without token IDs, when exported
at both levels with kind `rollout`, then transition yields three records, trajectory yields one, and
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

**SC-013:** Given a fixture store with one record past retention, when export
runs, then that record is refused with `retention-expired`, the manifest
records retention per source, and a later `lightning purge` of the run lists
the manifest that cites it. Verification: procedure_013; T013.

## Scientific boundaries and compatibility

No hypothesis; datasets are artifacts, not evidence of model improvement.
Additive: new module, CLI subcommand and experimental schema; no existing
schema, contract or report changes. `executionAuthorization` stays false.

## Evidence and unresolved questions

Evidence is recorded per procedure under `evidence/`. Unresolved: OD-1, OD-2.
