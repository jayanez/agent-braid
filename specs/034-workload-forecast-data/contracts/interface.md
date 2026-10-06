# Proposed telemetry and causal-window contract v1

Feature-local draft, not a new public schema. Producer and consumer bind the
complete canonical record rather than trusting caller-provided digest strings.

Episode: `sourceRegisterDigest`, `episodeId`, `workloadFamily`, `baseTree`,
`manifestDigest`, `operationIds`, `resourceProfileDigest`, `clockReceipt`,
`phaseIntervals`, `completeWallNs`, `counters`, `outcomeReceiptDigest`.
Use integer nanoseconds for monotonic intervals. Phase sums include a declared
coordinator residual and do not double-count overlapping workers. Unavailable
RSS/CPU/scratch counters are null with explicit reasons, never synthetic zeros.

Window: `version`, `episodeGroup`, `resourceReceiptDigest`, `gridStart`, `stepNs`,
`cutoff`, `targetIds`, `units`, `values`, `observedMask`, `availableAt`,
`pastCovariates`, `knownFutureCovariates`, `partitionDigest`, `transformDigest`.
Canonical JSON contains finite numeric observed values or null/missing reasons;
no JSON NaN/Infinity, booleans-as-numbers or implicit unit conversion. Convert
missingness into backend arrays inside the adapter only under tested role rules.

Targets are regular numeric signals such as admitted queue depth or observed CPU
and aggregate latency, if actually available. Individual operation durations
remain event outcomes/operation-regression targets unless an explicitly reviewed
aggregation makes them a meaningful series. Counter resets, cumulative versus
rate values and interpolation rules must be explicit. Future outcomes, post-run
verifier verdicts and retrospective telemetry cannot enter cutoff-time inputs.

Validation refuses unknown revisions, late data, missing identity, non-monotonic
clocks, mixed units/cadence, oversized inputs, duplicate channels, invalid masks,
and unknown/stale resources. Purge overlap across history+horizon intervals and
keep entire episodes/workflow-resource groups together in declared partitions.
