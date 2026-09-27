# SPEC-018: Bounded structured exchange

## Purpose and scope

M3 tests a nontrivial overlapping pure structured-edit class with explicit
residuals. This is a consultative experiment, not a Git integration engine or
execution runtime. SPEC-019 contains the separate M3.5 predictor.

## Authorities

Constitutional clause zero and Articles 2–4, 6–10, 13–14, 17–20, 23–25;
GOVERNANCE.md; proposed ADR 0017; operational semantics and claim discipline.
Positive experiments cannot approve the ADR or milestone closure.

## Requirements and acceptance scenarios

- **REQ-001 — typed residual exchange.** Define anchored-sequence-v1 with
  immutable base anchors, fresh IDs and canonical sibling order.
  - **SC-001:** Same-anchor inserts yield the same final sequence in either
    order while physical indices are recomputed from the prefix state.
  - **SC-002:** Unknown or nested anchors, duplicate IDs and deletes are
    rejected rather than certified.
- **REQ-002 — explicit braid paths.** Define left-to-right adjacent crossings
  s0;s1;s0 and s1;s0;s1 for three inserts.
  - **SC-003:** Both paths end with reversed logical order and the same named
    final-sequence observation; chronological traces remain present.
- **REQ-003 — reproducible finite evidence.** Version request and evidence,
  regenerate all paths in the verifier, and fail closed on omission or tampering.
  - **SC-004:** Complete valid records verify within the named domain.
  - **SC-005:** Changed hashes, steps, paths or authorization bit are
    inconclusive; the producer verdict is not trusted.
- **REQ-004 — finite protocol.** Enumerate base sizes 0–3, 2–4 inserts, every
  root/base-anchor assignment and all operation orders.
  - **SC-006:** Report counts, same-anchor positives and false-certificate
    count, plus serial and path-disjoint comparisons without requiring speedup.
  - **SC-007:** Serialize both pair terminal sequences in an isolated Git object
    store and report tree IDs as a witness, without claiming an M2 certificate.

## Scientific boundaries and compatibility

Observation is only the ordered ID/value sequence after pure replay. Raw traces
are retained but excluded from equivalence. This establishes neither general
OT, contextual equivalence, arbitrary edit confluence, parallel safety, Git
patch equivalence nor a Yang–Baxter theorem. Producer and verifier share the
replay implementation. M2 AIM/Git contracts remain unchanged. All outputs say
executionAuthorization: false.

## Evidence and unresolved questions

Tests, corpus output and clean-room checks are planned in assurance.json.
Formal proof review, runtime transfer, real workloads, ADR acceptance and
founder M3 closure remain separate.
