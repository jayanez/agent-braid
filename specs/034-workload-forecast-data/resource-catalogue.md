# Proposed local resource catalogue

Status: no resource profile registered or approved for this experiment.

Every profile records opaque ID, actual host/platform/CPU/memory observations,
runtime and isolation contract revisions, existing parallelism caps, resource
inventory revision, availability receipt and expiry, observation units, supported
counter/enforcement capabilities, and independent operator authority boundary.
The model cannot create or modify this catalogue.

Initial registry cardinality is one reviewed local host/resource profile. The
only supported action modes are existing serial and parallel preparation; actual
worker allocation still uses existing deterministic ready waves and isolated
owned scratch. A profile is a measured operating envelope, not a fabricated new
worker pool. Thread/memory observations alone do not certify enforceable capacity.

Additional local profiles may be separately registered as evaluation strata when
their execution contract and actual resource receipt are already reviewed. Remote
host dispatch, migration and automatic provisioning remain unavailable. If the
registered population cannot provide measured choice diversity, where benefit is
inconclusive. Unknown/stale/over-budget profiles refuse placement advice.

## Current synthetic implementation

The [resource/cache engineering tranche](resource-cache-controls-2026-10-15.md) implements a trusted, pinned catalogue and complete versioned profile metadata. The [synthetic fixture](fixtures/synthetic-resource-catalogue.json) contains one test-only profile; the real catalogue remains empty and unadmitted. No actual host/slot observation is inferred from that fixture or the prior FC.2 worker envelope. T005 and its applicable T001 review remain open.

## Owner-adopted admission stop (2026-10-16)

The [T005 disposition](t005-disposition.md) supersedes the earlier current-status sentence about continuing T005 admission work. T005 is cancelled/partial, not completed; its criterion stays unchecked. T001 remains open, the actual catalogue remains empty/unadmitted, and all T005-dependent consumers remain unsatisfied. The retained one-shot native control failed; no active grant, resource profile, new execution or replacement package follows.
