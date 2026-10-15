# Selected-operation cost boundary v2

Version: `agent-braid-selected-flow-cost-v2`. This additive engineering contract
resolves the finite measurement stop event for the full-flow driver. It does not
rewrite `agent-braid-forecast-technical-cost-v1`, its historical receipts, the
Constitution, any FC.1 task criterion or an economic/adoption decision. The owner
requested contract resolution and implementation on 2026-10-15. Applying this
boundary to an actual VM/model run still requires the exact new package admission.

## Selected population and clock

One ready-artifact local synthetic **batch**, with two fixed Git fixtures:
independent patches and a dependency chain, two operations each. One root host
monotonic interval starts before owned output allocation and data preparation.
It includes the newly admitted owned VM/model collection and teardown, then all
six host policy arms, external grants, replay, verification, fixture cleanup,
durable product payload publication and its byte-for-byte readback.

The model collector performs three session calls H1/H5/H1: two actual backend
calls (cold H1 and resident H5), then a session-cache hit H1. It returns their
bound packets and its independently checked counter receipt. Both forecasts must
be valid and within cold 30 s/resident 1 s; cache output must match the cold
quantiles, with no third backend call. A fresh per-operation nonce and generated
window bind the collector to this invocation. Retained outputs cannot be supplied
as new inference. Validation of a nonce/digest alone is not source authentication;
the exact private collector must independently establish fresh execution.

The VM is stopped before host Git work. The H1 is consumed from this current
batch by the existing paired fixture harness; those reads are explicitly
**forecast consumption**, not additional inference. Model acquisition is shared
once per batch and excluded from individual arm times. Those arm ratios cannot
support speedup/utility. All six intended arms, refused/failed attempts and a
partially attempted roster remain inspectable through durable per-arm intent
and terminal snapshots. An intent without a terminal snapshot means
`started-outcome-unknown`, never definitely unattempted; fixture iteration never changes
operation effects, dependencies, grants or deterministic verification.

## Finite publication boundary

The product payload is an output of the selected operation. Its durable export,
readback and all confirmed owned cleanup occur before the stop event
`owned-cleanup-and-product-payload-readback`. The final metrology attestation
`operation.json` is then written outside that interval. This exclusion is explicit:
`payloadPublicationIncluded` records actual product readback;
`attestationPublicationIncluded=false` records the remaining apparatus cost.
No observer is added recursively to move that same final write outward.

The embedded v1 ledger keeps `publicationIncluded=false` and its final-receipt
publication gap. V2 never strips that gap, sets v1's flag true, or declares complete
costs by calling apparatus free. This resolves what the new bounded measurement
means; it does not satisfy a broader literal requirement by narrowing its scope.
T007 stays open until its applicable complete-cost criterion is actually accepted.
If that cannot be satisfied, report partial/infeasible; no completed checkbox.

## CPU, stages, preparation and unknowns

Retain all 17 v1 stage obligations and four CPU domains. The host phase enclosing
collection is not a replacement for guest model/engine phase measurements.
The collector's disjoint, persistent client/worker/services lifetime counters
remain separate from host coordinator/waited-helper-and-Git and guest-control diagnostics.
The outer waited-children delta is recorded when the platform supports it,
excludes guest/XPC CPU, and overlaps the inner collector helper counter; never
add those two host observations.
Do not translate guest clocks to host offsets without an observed mapping or add
VM-wide/host virtualization counters to their children. Partial intervals remain
gaps. Memory lifetime peaks and samples are never summed.

Reused setup is explicitly unallocated unless a bound source receipt and denominator
exist. Historical acquisition/build/export CPU not retained is permanently unknown;
measuring a new copy or build does not repair it. Host XPC, pre-cgroup bootstrap and
final attestation costs remain named gaps where unavailable. Baseline installed
OS/Docker and engineering retries stay separate; the contract invents no new
requirement to remeasure all OS history. A later provisioning procedure needs its
own exact admission and allocation, including failures.

Generic validation checks schema/bindings, not authenticity, effective enforcement
or observed disjointness. `fullDeploymentCostAccepted`, `economicCostAccepted`,
`utilityAccepted` and `executionAuthorization` remain false in every driver result.
Source/model loading, FC.1 registration/holdout/interpretation, ADR adoption and
promotion are separate gates. Default discovery never starts this harness.

## Procedure and stop rules

`forecast_fullflow.run_selected_flow` requires a separately trusted collector and
an independent fixture operator. The public `reproduce_forecast_fullflow` CLI
can only simulate model packets; it cannot load ML or start Docker/VMs. No arbitrary
command is taken from numeric inputs. Existing or symlinked output is refused
before collection. Failed/interrupted collection cannot confirm cleanup. Storage
failure retains already written files; failure to write the terminal attestation
propagates rather than returning success. Outside admission/supervision bounds
remain mandatory for a real collector and cannot be supplied by this library.

Offline controls cover changed nonce/window/provenance/call count, forged grants,
interruption, failed export, bounded output and the healthy six-arm case. A single
reviewed actual run may follow only a complete exact package and owner approval;
no empty-engine qualification, destructive fault, automatic retry, download,
paid fallback or limit increase is implied.
