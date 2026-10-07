# SPEC-036: Proposed records

All records are feature-local draft contracts with immutable version, digest and provenance; no public runtime schema is changed.

| Record | Identity and important fields | Rejection/interpretation boundary |
|---|---|---|
| WorkloadEpisode | source register, base/patch/manifest digest, workflow family, resource profile, monotonic/UTC receipts | Rights and eligibility checked before capture; repeated timings share one episode identity |
| TelemetryWindow | grid/cutoff/available-at, target units/order, numeric values plus explicit missingness, source receipt and partition | No unknown-as-zero, late backfill, mixed cadence or future outcome input |
| ResourceReceipt | registry/profile/execution-contract digest, admitted caps, observed availability, receipt time and expiry | One reviewed local profile initially; no claimed remote capacity or automatic provisioning |
| ForecastEnvelope | request/window/artifact/preprocessing digests, target/horizon/quantile axes, p10/p50/p90, median, status/reasons, timing/memory | Finite typed output; nominal interval versus measured coverage stays explicit |
| AdvisoryDecision | immutable candidate set, reference/selected option, input/resource/artifact/cutoff bindings, expiry, heuristic evidenceClass, executionAuthorization false | No grant issuance, unsafe option, modified wave or manifest; actual host grant is independent |
| EvaluationReceipt | episode/arm/order/group/fold, cutoff decision, raw actual outcomes, full-wall/CPU/memory costs and unavailable reasons | All attempts retained; shadow has no observed counterfactual; historical/synthetic/real domains separate |
| CapabilityDecision | candidate/model/resource/population/mode, utility decision, boundary evidence, numerical caps, drift and rollback | No whole-M4 or scientific closure; in-flight immutable execution contracts are preserved |

Raw private telemetry and detailed host identifiers remain outside the public repository. Public evidence packages contain approved aggregate metadata and hashes; hashes are provenance, not signatures or permission. A private source receipt cannot be validated by publishing a synthetic substitute.
