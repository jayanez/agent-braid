# Owned-repository source readiness review

**Status: pending.** This checklist assesses whether a source can enter an
event audit. It grants no access, capture, corpus, model training or execution.

## Preparation completed

- [x] The initial screen was limited to architecture, schemas, specifications
  and engineering documents.
- [x] Kinetiq excludes video, keypoints, biometrics, athlete and customer
  material. SmartNotes excludes patients, `PA-NNNN`, clinical activity, STT,
  audio and transcripts.
- [x] Commits, diffs, Issues and processing traces are not treated as
  independent shared-base insertion events.
- [x] The opt-in local sidecar, full-session admission ledger, all-pair
  structural adapter and synthetic adversarial tests are prepared.
- [x] Separate private Kinetiq and SmartNotes labs contain only reviewed,
  exact-file `lab/main` and `lab/develop` snapshots, without source history.
  Changed Git blobs block the next sync until reviewed.
- [x] A separate private audit repository contains the metadata-only
  registration and seal workflow. A synthetic dispatch was attempted.

## Gates still open for each source and workflow

- [ ] Record the source owner, authorized participants, optional capture
  permission, rights and privacy decision before opening any real record.
- [ ] Install the source-reading GitHub App with only `Contents:read` on the
  selected source repositories, then verify both lab syncs on actual runners.
- [ ] Obtain one successful audit registration run with a runner and steps,
  at least 24 hours before each separate, fixed 14-day UTC window. The
  synthetic dispatch on 2026-09-30 did not start a runner and is not a seal.
- [ ] Reconcile the complete sidecar admission register against each source
  workflow's independent completeness control, including bypasses.
- [ ] Freeze sampling and enumerate every session and unordered candidate
  pair with primary exclusion reasons; validate against
  `anchored-sequence-v1` without reconstruction or trimming.
- [ ] Review actual yield, source provenance and the safe aggregate before
  calling any pair real or publishing results. Keep local journal content
  outside GitHub and apply the reviewed retention rule.

## Current result

The repository-level screen found **zero observed real sessions and zero
eligible pairs** in each source. These are screening counts, not a measured
yield from a prospective window. No real journal has been opened. P019-01
and T001 remain open; no calibration or training is authorized.
