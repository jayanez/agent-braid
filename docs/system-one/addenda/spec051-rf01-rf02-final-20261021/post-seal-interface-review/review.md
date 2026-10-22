# RF-T01/RF-T02 interface and evidence review

2026-10-21. Read-only review of the final local SPEC-051 candidate at
`/private/tmp/agent-braid-spec051-corrected-20261021`, baseline
`a6329c828011d1468fed3dfa4e98f5a8531167e2`.

## Result and scope

No P1/P2 findings identified in the three requested interface properties. A separate
Luna Latest (`gpt-6-luna`, reviewer role) static review reached the same result.
This is a bounded interface review, not whole-product release approval, an independent
experiment, clean-room reproduction, physical authentication or scientific acceptance.
No product imports, tests, mutations, suites, captures or historical diagnosis were run.
No candidate or sealed packet was edited. No product publication was performed.

## Requested properties

- **Snapshot authority.** `OperatorRegistry` freezes the supplied descriptors and sets.
  `resolve_authority` (owned_work_authority.py:224–252) requires the exact registry type,
  exact registered canonical descriptor, current supplied revocation set, root/scope,
  expected pins, consent/review references, validity window and allowed actions.
  `decision=admitted` alone cannot resolve authority. Python snapshot construction,
  current UTC, receipt truth, physical root checks and revocation freshness remain
  trusted operator-adapter obligations; a fabricated trusted caller is outside this seam.
  No authenticated registry loader or live consent route has been delivered.
- **Supplied history replay.** `validate_append` (owned_work_contracts.py:326–393)
  parses candidate and bounded historical records before accessing their fields,
  resolves the supplied snapshot anew, then replays every supplied event. It checks
  sequence, predecessor/digest, authority, record dates, frozen identity/source pins,
  origin uniqueness and outcome/supersession semantics. It returns immutable canonical
  state, semantic idempotence and explicit missing origins/outcomes for the frozen
  supplied population. Valid replay cannot prove that real history or population was
  not omitted by the trusted supplier, nor authenticate observation truth.
- **Late maturity.** The outcome guard (owned_work_contracts.py:275–285) requires
  `labelState=censored` and `censoring.state=right-censored` for terminals after the
  original fixed horizon; an already right-censored outcome cannot be amended into
  a mature original-lot label. Eligibility (387–389) selects only mature outcomes
  with a produced forecast, so these late outcomes remain excluded. Append-only origin
  uniqueness prevents rewriting the origin horizon or backfilling its predictors.
  This matches RF-DEC-002. The corresponding test source was read, not executed.

## Evidence readback

The sealed packet hash is
`7773a3607315e042dd7d5672ecdf41fba9b797c579fbdf363973b58562517ce9`.
All 68 candidate bindings, 50 lossless compressed representations and 18 archive
members matched their hashes and current source bytes. Archive, patch, completion,
final-readback and both durable mirrors matched the supplied seals.

Existing corrected quick/pr receipts each bind 2,932 inputs, include the same four
software/test source pins and report exit 0. Their bound logs contain 2,153 tests,
23 skips and OK; log hashes match the receipts and packet. Source-match and temporary
copy removal are recorded by the parent receipts. This review did not repeat all
2,932 baseline reads, patch application or either profile. Prior failed attempts,
metadata repair and the incomplete first hash check remain preserved in the packet;
this review does not reclassify them as passing.

Real source admission, trusted adapter/physical registry, secure store RF-T03,
observer RF-T04, real-population/oracle qualification, training/calibration,
human/scientific acceptance, promotion, activation and product publication remain
pending. The historical packet's pending-review field is preserved; this separate
record adds the bounded static review without rewriting that historical snapshot.
