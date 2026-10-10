<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# M3.5 technical readiness

**Historical observation:** 2026-10-05. The measurements below retain their
original date, code candidate and limits.

**Current status (2026-10-10):** synthetic-only trainer/inference T002/#182 and
verifier boundary T004/#184 are complete. Six software tasks T002/T004/T006/T008/
T009/T010 are closed. T001/#181, T007/#188, T003/#183, T005/#185, parent #180
and milestone 9 remain open. The synthetic package passed 115 focused controls
with zero skips/failures; the final provenance repair passed exact-head and
post-merge CI (885 tests, two skips) and all four integration-matrix configurations. These results do
not admit real pairs, adapt real feeds, establish protocol approval or close the
experiment. See the [delivery and alignment record](m35-project-alignment.md).

This non-normative operations note records technical checks against Agent Braid
commit `f1bc304827b26c2cc3e02d5488ff2f82daa5453d`. It supplements
[ADR 0018](../adr/0018-private-source-sidecar-and-disposable-labs.md), the
[source-readiness checklist](../../specs/019-native-predictor/checklists/owned-repo-source-readiness.md)
and the [prospective pilot runbook](../../specs/019-native-predictor/prospective-pilot.md).
It does not alter their approvals or frozen evidence. Current software task status is given in the dated addendum above; the historical observations below are unchanged.

## Executed software checks

The isolated environment used Python **3.13.11** on **macOS 26.6.2 ARM64**.
These are local observations; Linux reproduction is a separate execution.

| Check | Observed result | Evidence boundary |
| --- | --- | --- |
| Spec Kit preflight in a full independent clone | Passed | Structural validation; human and semantic review remain separate. |
| Four focused M3.5 test modules | **44 tests passed**, 3.131 seconds | Supplied synthetic fixtures, mocks and disposable Git repositories. |
| Synthetic capture and audit CLI reproduction | Capture and report matched the committed fixtures byte for byte | 18 events; six synthetic sessions and pairs; one admitted synthetic pair; five exclusions. |
| Additional all-pairs sidecar rehearsal | Four synthetic sessions, 22 events, four pairs examined and three structurally admitted | Three participants produced all three unordered pairs; the dependent-observation pair was excluded; empty and single-proposal sessions remained in the inventory. |

Both synthetic reports retained `realPairsAdmitted: 0` and
`executionAuthorization: false`. The three-participant rehearsal exercises
enumeration; it supplies no real family, utility label or training sample.
No software defect was reproduced by these checks.

The focused suite covers the hidden-proposal barrier, complete session/pair
accounting, invalid bases and anchors, unsupported operations, missing
provenance, dependent observations and unclosed sessions. Recovery checks cover
torn and completed-before-crash appends, orphaned staging and rejection of an
unrelated journal tail. Export and seal checks cover content-pin drift,
symlinks, filtered ancestry, changed identities, skipped days, decreasing
counts, premature submission and runnerless registration.

Run the same checks with an isolated Python 3.12+ environment from the
repository root:

```sh
python3 -m scripts.validate_spec_kit
python3 -m unittest \
  tests.test_m35_source_capture \
  tests.test_m35_source_window \
  tests.test_m35_lab_export \
  tests.test_m35_seal_validate -v

RUN_DIR=$(mktemp -d)
python3 -m scripts.instrument_m35_flow capture \
  examples/m35/m35-synthetic-sessions.json "$RUN_DIR/capture.jsonl"
python3 -m scripts.instrument_m35_flow audit "$RUN_DIR/capture.jsonl" \
  --output "$RUN_DIR/report.json"
cmp "$RUN_DIR/capture.jsonl" examples/m35/m35-synthetic-capture.jsonl
cmp "$RUN_DIR/report.json" examples/m35/m35-synthetic-report.json
```

Fresh paths are required: capture and report creation refuse to overwrite
existing files. The sidecar tests `test_three_actors_enumerate_every_unordered_pair`
and `test_exclusions_keep_full_sessions_and_primary_reasons` provide reusable
regressions for the supplementary rehearsal's accounting rules.

## Private lab and infrastructure audit

A read-only audit checked the two existing private labs. It inspected only
already-reviewed engineering documents and metadata. Exact paths, blob pins,
source and lab commit references, allowlist digests and run IDs remain in the
private operations evidence outside Git.

All **four** `lab/main` and `lab/develop` snapshots contained exactly their
**two** allowlisted documents plus `lab-snapshot.json`. Their exported bytes
matched the reviewed source blobs and snapshot SHA-256 values, and each
snapshot's allowlist digest matched its lab control manifest. Their ancestry
was checked as filtered snapshot history. No source application history,
session journal or unlisted file was present in those snapshot trees.

| Candidate | Snapshot integrity | Comparison with current source branches |
| --- | --- | --- |
| Kinetiq | Both stored snapshots verified | All reviewed file pins still match `main` and `develop`. |
| SmartNotes | Both stored snapshots verified | `main` pins still match; **one** allowlisted `develop` blob has changed. |

The changed SmartNotes blob was identified from metadata; its new content was
not inspected and its pin was not updated. The previous snapshot remains
verifiable, while a new export from that source branch must stop until the
changed engineering document receives review. A newer source commit with
unchanged allowed blobs is distinct from this content drift.

Each source still has a candidate read-only M3.5 deploy key. Each corresponding
lab has the expected Environment secret, no repository-level copy of that
secret, and a custom Environment policy admitting only `main`. Scheduled sync
is enabled. These configuration observations do not prove that a credential
will authenticate in a future run.

The latest **three runs per lab**, dated October 3–5, were completed with
GitHub's `failure` conclusion but had an empty runner name and no steps. The
latest runs' check annotations identified the billing gate. Their correct
execution classification is **infrastructure not executed**; they are not
failed exporter tests, completed syncs or experimental results.

The audit repository had two failed attempts: one without an executed runner
and one executed diagnostic that produced no successful seal. Neither is a
successful source-window registration. No workflow was dispatched, runner
registered, credential changed or private payload captured during this audit.

## Historical task disposition and human handoff — 2026-10-05

| Task | Technical work available now | Remaining prerequisite |
| --- | --- | --- |
| T006 and T008 | Existing capture, sidecar, export and seal tooling reproduced; focused regressions passed | Tooling completion does not admit a source. |
| T001 | Permission-record shape, registration checks, eligibility accounting and proposed protocol are prepared | Source rights/privacy decisions, actual prospective yield and scientific review of the full protocol and rubric. |
| T007 | The all-session/all-pair adapter and exclusion controls are prepared | Review of a real authoring boundary, participant receipts and an independent completeness control before opening a feed. |
| T002 and T003 | Their proposed inputs and evaluation rules are documented | An approved, eligible corpus, frozen labels and partitions; no trainer or held-out evaluation is authorized by preparation alone. |
| T004 | Current adapters consistently deny execution authorization | A future predictor candidate is needed to validate the score/verifier separation scenario. |
| T005 | Synthetic software results and infrastructure limitations are recorded here | Candidate-bound experimental evidence and M3.5 review after the preceding gates. |

The next source decision must provide, separately for each workflow:

1. A private owner/participant/data-rights/privacy and capture-permission record,
   including the reviewed retention and publication boundary.
2. A reviewed authoring process that emits actual base receipts and independent
   proposals, plus a completeness control covering bypasses, cancellations and
   every opened session.
3. One immutable 14-day UTC window and a successful metadata-only remote
   registration with an executed runner and steps at least **24 hours** before
   its start; then the complete daily/final seal chain.
4. Review of the full sampling, annotation, split, calibration and cost protocol
   before labels or training. The proposed five-family and label/class thresholds
   remain protocol candidates, not established statistical power.

The current record contains **zero admitted real pairs**. Kinetiq and
SmartNotes are two candidate workflows; they cannot by themselves satisfy the
proposed five-family protocol. Their Git histories and filtered decision
snapshots cannot establish independent shared-base intent.

Additional Linux capacity can reproduce synthetic software checks and shorten
their execution. A local Linux result or public synthetic Actions run cannot
replace the successful remote registration required for each real source,
clear rights/privacy decisions, establish upstream completeness or authorize
labels, training, exchange execution or a predictor-benefit claim. Preserve
the private audit repository and its source-specific gate when planning
future runner use.
