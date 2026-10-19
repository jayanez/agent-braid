<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# D10 and ADR documentary reconciliation — 2026-10-17

Baseline: `938523a8c3d7e2c3fd5a506d41c27f91c8e7c0e7`. This is a separate local documentary follow-up prepared for its own freeze;
the predecessor frozen candidate and its external sealed admission packet remain
unchanged. The exact successor commit is recorded in the external admission update. It supplies no new owner approval or admission.

## D10 byte correspondence

The immutable [owner-decision JSON](owner-decisions-20261016.json) still binds
original D10 SHA-256 `55a1b4ffe4e8d24e37a7ac0759665533c75739f4b5b313b4573191bd211645ff`.
Those original bytes are now available canonically at
[the historical D10 snapshot](historical/owner-acceptance-disposition-20261016.md).
The snapshot was copied from the sealed dossier and checked against the unchanged
historical decision checksum; no old Git object or reference was imported. An
identical [archived decision JSON](historical/owner-decisions-20261016.json)
preserves the original snapshot's relative reference context.

The [machine-readable mapping](documentary-reconciliation-938523a-20261017.json)
records the original, frozen-candidate and corrected current document hashes.
The frozen-candidate document had two ADR-numbering/provenance edits relative
to the original. This follow-up corrects its remaining canonical-effect
reference to ADR 0024 and links the preserved original bytes and mapping.
The historical JSON checksum is not replaced with a later rendering's checksum.

D10 continues to acknowledge bounded C/D engineering and defer acceptance.
Neither the editorial mapping nor the local passing profiles extend that
acknowledgment to the reconstructed candidate or confer independent review.

## ADR identity

The telemetry proposal is [ADR 0024](../../docs/adr/0024-local-technical-telemetry.md),
which remains proposed with architectural adoption pending. The original
telemetry ADR 0023 bytes remain in the
[historical proposal](historical/adr-0023-local-technical-telemetry.md). Current
[ADR 0023](../../docs/adr/0023-second-history-correction-equivalence.md) concerns
the second history correction. Neither ADR file nor any authority hash changed.

## Dated-record interpretation

The dated [2026-10-16 admission preparation](admission-preparation-20261016.md)
and [canonical decision prose](owner-decisions-20261016.md) retain their original
C/D observations. Their statements about historical snapshots and missing source
modules describe that earlier lot. For the later candidate, the active assurance
is current/draft and the original assurance is archived; #509 source modules
are already present on e474320e; the
[reconciliation validation report](reconciliation-validation.md) records the
later passing engineering profile. These facts do not supply native/process
authentication, candidate admission, independent review or acceptance. This
addendum resolves those dated references without rewriting their observations.

## Preserved boundaries and verification

All existing tracked files except the D10 rendering retain their exact baseline
bytes. The original assurance, owner decisions, evidence, both ADRs, all task
files and T004 records are unchanged. Task counts remain 65 checked / 26 open;
T017/T018/T010 remain open, assurance stays draft with human review pending,
and pilot **NO-GO** remains in force. T004 retains its historical bounded
closure and exclusions; no reproduction or review was repeated.

Verification for this documentary lot checks the original/current hash mapping,
all unchanged tracked files, the original packet seal, task/ADR states, local
link targets, whitespace and the active SPEC-046 draft structure. The retained
1,888-test PR profile covers the frozen engineering lot, not a fresh full run
after these prose changes. No new full suite, scientific experiment, agent,
host/provider execution, registration, publication, push or merge is performed.
No task or admission gate is closed.
