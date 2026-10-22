# SPEC-051 RF-T01/RF-T02 local implementation result

Bounded software implementation obtained on M3 Pro, EUR 0. Baseline `a6329c828011d1468fed3dfa4e98f5a8531167e2`.
No capture, actual source admission, secure store, observer, model, forecasting
accuracy, human/scientific approval, activation or product publication obtained.

## Implemented

- Adopted separate SPEC-051 and ADR 0026 for local pure implementation, preserving
  the two proposal schema bytes and RF-DEC-001/002. Public integration/review pending.
- `owned_work_authority`: bounded raw/parser/schema validation and immutable trusted
  operator snapshot comparison. Wire flags/callback True do not mint authority.
- `owned_work_contracts`: exact raw/schema/digest and causal state validation;
  supplied history replay, immutable append result, duplicate idempotence, one origin,
  exact correction, source/clock/family/oracle bindings, T0, unknown values,
  intervals, spans, missing supplied population and fixed-horizon censoring.
- Stdlib-only production imports, no I/O/model/collector/grants/default registration.

## Actual software checks

42 focused tests passed, zero failures/errors/skips, 0.135 seconds. Earlier focused
attempt1: 35 tests with two errors, caused by reading untrusted history before schema
admission. Fixed by parsing history before field access; regressions pass. Attempt2:
35 passed; final extended controls: 42 passed. Counts overlap, not independent samples.
Six targeted mutants were detected: five assertion detections and one runtime-error
detection after deleting the oracle guard. The helper exited 1 because its final
expectation incorrectly required assertion-only detection. All attempts and that
disposition are preserved; no mutant changed product files and no rerun hid it.

First full profiles failed: each ran 2,153 tests with seven errors and 23 skips.
The seven events were three metadata causes: missing local SPEC-051 tracking entry,
unqualified new scenario test names, and stale CURRENT draft-047 authority inventory
after adding ADR 0026. Those exact metadata defects were corrected; no pure source
module changed. Only the new authority hash was added to active draft047, preserving
all requirements, evidence, pending review and historical records. Tracking051 is
OPEN; no remote object was created/closed. See integration-repair.md and raw receipts.
The initial wrappers then stalled inside OS read on an existing 285 KiB receipt during
final hash checks; stopped only those own wrappers/monitor, supervisor exit -15.
The old hash read is incomplete, never declared passed; the OS cause remains unknown.
A fresh independent /private/tmp clone at the SAME baseline read that exact historical
file and matched its baseline hash. Preflight passed before restoring the byte-exact
pure implementation and correcting metadata. Six affected methods passed separately.

Corrected-candidate quick/pr receipts (earlier failures preserved):

```json
{
  "quick": {
    "exitCode": 0,
    "unitBatches": [
      {
        "tests": 2153,
        "seconds": 2198.039
      }
    ],
    "skippedByBatch": [
      23
    ],
    "profileSeconds": 2424.9525901250017,
    "logSha256": "5e631ae8b497f0736d57e48b44f5fe4b0b399153a45c44809246f194c0528926",
    "sourceInputsStillMatch": true
  },
  "pr": {
    "exitCode": 0,
    "unitBatches": [
      {
        "tests": 2153,
        "seconds": 2198.943
      }
    ],
    "skippedByBatch": [
      23
    ],
    "profileSeconds": 2426.2510924579983,
    "logSha256": "94c300cfdbec8fb3d527655f9e6f5997a59f7790fd6b2159c8a8489fae44be7c",
    "sourceInputsStillMatch": true
  }
}
```

All 2932 corrected tested inputs still matched at packaging; 2915
baseline files remained byte-exact, with only 2 justified metadata exceptions
bound in metadata-repair.json. Four pure implementation/test files stayed byte-exact
through the correction. quick escalated to sensitive per the normal planner.
Profiles used independent equivalent local copies and the existing Python 3.12 env
with child PATH pinned. These are engineering checks, not source capture/reproduction.

## Limits and continuation

The fixed-schema interpreter is tested against sampled dev-validator controls; it
is not a general JSON Schema implementation or a proof of language equivalence.
UTC admission accepts Z timestamps with seconds and up to six fractional digits;
integer fields require JSON integer tokens rather than float representations.
Span IDs are unique; repeated stage labels are reconciled by interval union.

Registry/attestation constructors are a trusted Python host boundary. These modules
cannot authenticate consent, physical roots/links, revocation freshness, artifact
truth or complete registration. A secure operator adapter and RF-T03 must supply
those facts; no loader/source verifier fallback is shipped. Caps here count event
bytes, not a physical store's journals/maps/annexes. N03's physical check and N17
storage/N18 observer remain pending; N19 reports supplied members only. No source
or method admission follows from constructing fixtures or parsing records.

The scalar target binds a supplied trusted operational command/log attestation;
it never yields semantic or human gold. Late completion cannot uncensor its original
forecast horizon. SPEC-045 synthetic contracts, SPEC-047 identity-free aggregates,
typed-v1 domain, defaults, historical packets and closed v1 remain unchanged.
No independent review of this new code is claimed; coordinator self-review only.

Local T001–T003 implementation and checks obtained. T004 profile portion obtained;
documentary reconciliation/publication is tracked separately. RF-T03/RF-T04 and
real source/privacy/population/oracle admission require their next assignment.
Training/calibration, human/scientific review, promotion and activation remain pending.

Evidence: [packet](evidence/rf01-rf02/packet.json), historical and bound to commit
`f03796066d14d152dc1df3ba417546650b7405e4`; it is not rewritten. Later review
repairs and their hashes are recorded in [review-repair.md](review-repair.md). The external source archive and
baseline patch are private reproducibility materials, not publication approval.
