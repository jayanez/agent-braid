# Resource and cache engineering controls (2026-10-15)

This is the synthetic implementation tranche of SPEC-034/T005 and SPEC-035/T006.
It is additive to the [original-task retrospective](../035-chronos2-forecast-adapter/retrospective-2026-10-15.md).
The original criteria and checkboxes are preserved. Both tasks remain **open**:
T005 still needs its applicable T001 review and an actually admitted local profile;
T006 retains that explicit T005 predecessor. Passing these controls is not a
resource admission, real workload experiment, complete-cost result or promotion.

## Resource registration and point-of-use checks

`agent_braid.forecast_resources.ResourceCatalogue` is configured by trusted host
code, outside a forecast/advice request. Its root pin, expected opaque host/clock IDs,
runtime/isolation/inventory revisions and external admission verifier are not
request-supplied allowlisting claims. A matching self-computed hash is integrity,
not authority. The implementation reads no host data and creates no capacity.

A catalogue has zero or one profile. The **real catalogue is empty/unadmitted**.
The [one-profile fixture](fixtures/synthetic-resource-catalogue.json) is test-only,
`sourceKind: synthetic`, fixed-clock numerical data; its platform, CPUs, memory,
receipt hashes and slots are fabricated simulation inputs, never host observations.
No real profile is registered by shipping that fixture.

A profile binds its v2 resource record to complete metadata through
`profileRevision = digest(metadata)`. Metadata names runtime and inventory
revisions, platform observation units, the isolation revision/receipt, explicit
supported controls and a versioned availability receipt. The availability receipt
binds source/profile/host/inventory identity, clock epoch identity, explicit
monotonic-nanosecond units, observed/expiry times and numerical
observations/caps. Canonical hashes cover all of these bytes. Changed metadata,
revisions, bounds or freshness therefore change the resource digest carried by
the window and cache key. Version-1 synthetic records retain compatibility;
permissioned v1 records refuse because they cannot bind the complete metadata.

`resolve` checks the configured host/revisions, known profile ID, current supplied
runtime clock, mode, worker count and operation/patch/scratch budgets. Unknown,
stale, future, malformed, over-budget or unsupported profiles refuse. The returned
eligibility receipt names the checked time, requested budgets, profile/root/resource
digests and copied metadata. It always has `executionAuthorization: false`.
Logical CPU count and memory observations do not derive worker capacity or quotas.
The profile's explicit caps still need independent admission and enforcement.

For permissioned resources, `validate_resource` accepts only the exact configured
`ResourceCatalogue` verifier type, not a callback returning true or a subclass
with a bypassed check. It finds the exact pinned record and validates its complete
context, then calls the externally configured verifier with a defensive copy of
the **full profile and availability receipt on every use**. The existing advice
validator already calls this gate. A positive callback receiving only a raw
resource can no longer bypass metadata review. External verifier errors refuse
without exposing private error content. Current session/MCP real-source paths
remain unadmitted; this does not wire an active permissioned consumer.

A permissioned profile declaring parallel must have CPU and memory enforcement
support backed by its reviewed isolation/availability receipts and the external
verifier. This conservative feature admission minimum cannot be removed through
`required_controls`; that configuration can only add requirements. Flags alone
are never proof that controls exist or limits were applied. The synthetic fixture
can simulate unsupported hard limits without authorizing parallel work. Serial
may use explicit unsupported-hard-limit metadata only through its separately
configured **serial-only** profile and full external admission. An invalid profile
is not silently rewritten as serial. These are preparation-resource checks, not
admission of the distinct Chronos worker/image/VM or a change to runtime grants.

## Causal cache and cancellation

The bounded, in-process, caller-owned cache continues to hash the full canonical
request plus the complete artifact manifest identity. That includes cutoff,
values/masks/availability, covariates, target ordering/units, preprocessing and
partition identity, resource receipt, backend, alpha and horizon. Runtime and
isolation/capability revisions enter through the bound resource metadata; model
capability/profile/lock revisions enter through its manifest. There is no
caller-selected compatibility override. Implementation code and its fixed
capabilities cannot change inside a session; caches are not persisted or shared
with a new process/package. Each session owns its copied entries and LRU bound.

On a hit, the stored packet is validated against the current window/horizon and
Chronos artifact before any fresh envelope can relabel values. The new envelope
and cache receipt measure the current lookup/validation wall interval and retain
the original forecast digest separately; unknown model CPU/RSS counters stay
null with reasons. Stub timing controls do not become real Chronos/Docker costs.

Cancellation/deadline checks cover entry, lookup (hit or miss), validated cached
output, backend completion and cache commit. A cancelled/timed-out lookup cannot
start the backend; a cancelled completion cannot be stored. If interruption
arrives during commit, that entry is discarded and no successful cache receipt
is emitted. Previous diagnostic hits are cleared for the new accepted attempt.
Terminal backend results never warm the cache. Other valid cached results retain
the normal bounded LRU semantics. There is one active request, no extra queue,
automatic retry, model load or background service.

## Executed evidence and review

The task-local partial receipts [T005](evidence/t005.json) and
[T006](../035-chronos2-forecast-adapter/evidence/t006.json) bind production, fixture,
test and raw-output hashes. The focused tests use baseline math and a numerical
Chronos-shaped stub; the injected permissioned verifiers are protocol controls,
not real admission. No model, VM, container or real source collection runs.

The [guard mutation procedure](evidence/resource-cache-controls-2026-10-15/mutation_check.py)
changes source **only in a child process's memory**, never in checkout files.
It tests both permissive and over-restrictive mutations against named negative
and healthy controls. Its [report](evidence/resource-cache-controls-2026-10-15/mutation-report.json)
records every attempt and survivor. Earlier red cancellation, expiry and authority
controls are retained; these are code-regression checks, not repeated one-shot
qualification packages. Final technical review provenance and limitations are
recorded in the [review record](evidence/resource-cache-controls-2026-10-15/review.json).
Historical assurance, authority snapshots, exact approved packages and actual-model
observations retain their original bytes and scopes.

## Remaining admission work

T005 cannot close until the applicable T001 technical/resource phase and a real
local resource's exact identity, observations, supported/applied controls,
availability/expiry and independent authority have an admitted receipt. There
are no actual slots or silently fabricated observations in this delivery. A
concrete acquisition/qualification procedure would need its reviewed exact scope
before any approval request; no such execution is authorized by this document.
T006's software controls can be obtained now, but its T005 predecessor remains
open. T001's real-source/privacy phase, FC.1 registration/launch/interpretation,
complete cost and promotion gates remain independent. FC.2/T007's owner-adopted
cancellation does not cancel either task or SPEC-035/T008.

## Subsequent owner disposition (2026-10-16)

The open-state statements above describe this dated 2026-10-15 tranche. The [adopted T005 disposition](t005-disposition.md) subsequently cancels its remaining admission work as not_planned, with the original criterion unchecked. SPEC-035/T006 and all T005-dependent acceptance remain pending. Integration and remote readback are separate; this historical engineering receipt is not rewritten as admission or completion.
