# Implementation plan

1. Adopt exact two schema bytes and closed contract; preserve original proposal
   with manifest SHA 46d078fcb373070e4a50c0ce29154b4dd6fef379073c0cea90f420d35d7fa787.
2. RF-T01: `owned_work_authority.py`: bounded parser, fixed-schema checking,
   immutable operator registry and resolved context; no physical source reads.
3. RF-T02: `owned_work_contracts.py`: frozen registration and pure append validator,
   immutable canonical event state, idempotence and complete missing-member report.
4. Meaningful positive chains/corrections and hostile raw/semantic controls,
   schema parity with dev-only jsonschema, source dependency/non-I/O checks.
5. Focused, quick during coherent implementation, pr once stable. Preserve all
   failed attempts. Evidence packaging is separate; no source capture/reproduction.

Single parent owns these files. No agent delegation or concurrent mutations.
Production depends only on stdlib. Exact schemas are embedded for pure installed
use without filesystem reads; tests bind embedded schemas to contract bytes.
Authority resolver precedes state validator. Errors carry fixed codes and field
paths, never echo untrusted input values. Supplied clocks and registry snapshots
remain caller-owned observations; no implicit wall-clock or source observation.
