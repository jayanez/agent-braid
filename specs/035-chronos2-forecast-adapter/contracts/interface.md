# Proposed local Chronos-2 adapter contract v1

Separate feature-local numeric interface; no legacy System 1 or runtime schema
is widened. `capabilities()` exposes approved manifest, installed adapter/device,
target/mask/covariate support and reviewed numerical limits without loading a model.
`forecast(request, deadline, cancellation)` returns a typed ForecastEnvelope;
`close()` stops only owned idle state and never evicts an in-use request.

Request includes exact TelemetryWindow and ResourceReceipt digests, stable target
order/units, context length, horizon, quantile levels, transform/cutoff/partition
identity and artifact manifest. Only cutoff-known future covariates are allowed;
past-only channels have no observed future slot. Default cross-learning is off
and group identities cannot mix fit/tuning/holdout episodes.

Proposed initial limits, subject to 035/T001 and 036/T001 review: 1 MiB canonical
JSON; one active request, zero waiting queue, one-item batch, at most eight target
and eight covariate channels; context 128 bins; horizons 1/5/10 bins; levels
[0.1, 0.5, 0.9]; CPU reference, one library CPU thread, 2 GiB model-worker RSS
ceiling, 1 s resident-request deadline and separate 30 s cold-start ceiling.
These are review candidates, not approved installed capabilities. Unsupported
enforcement refuses real loading/evaluation. No automatic GPU switch or cap increase.

Pinned checkpoint supports context 8192 and output horizon 64*16=1024; these are
upstream ceilings, not a grant to use them. Reject an over-envelope request before
calling the backend; never rely on upstream default truncation. Role-specific
missing-target and covariate behavior must be source-verified and tested.

Pinned `predict_quantiles` returns lists: each quantile tensor is
`(n_targets, horizon, n_quantiles)` and its second tensor is
`(n_targets, horizon)`. Despite the name `mean`, v2.3.2 returns the median.
Emit `median`/p50, never an inferred arithmetic mean. Outputs bind units,
target order, horizon timestamps and observed numerical tolerance. Nonfinite,
crossed or wrong-shape quantiles refuse; interval calibration stays absent until
evaluated on the declared population.

Statuses: forecast/refused/unavailable/timed-out/cancelled. Every status includes
precise reasons and costs; `evidenceClass` is heuristic and
`executionAuthorization` is false. Approved loading uses a local safetensors
checkpoint, offline flags, local-files-only and no remote/custom code. The model
worker receives no credentials, source repositories, cloud URLs or operator grants.
