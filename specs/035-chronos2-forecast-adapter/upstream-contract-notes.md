# Chronos-2 upstream inspection and limits

Inspected on 2026-10-07 using Context7 plus primary upstream source. Source and
model identities are in reference-sources.json; no weights were downloaded.

Candidate package: chronos-forecasting 2.3.2 at released source commit
`0aba28e9360b6355d5a919596c90b16c25939f02`. Observed main was a different commit;
do not silently install main. Candidate model: `amazon/chronos-2`, revision
`29ec3766d36d6f73f0696f85560a422f50e8498c`, model card Apache-2.0. Actual package
closure, checkpoint file hashes and license review remain 035/T001 gates.

Chronos-2 supports univariate/multivariate numeric targets, historical and
known-future covariates, quantile outputs and CPU/GPU execution. No installed
hardware parity, footprint, latency, calibration or Agent Braid utility follows.
The observed checkpoint config has context_length 8192, output_patch_size 16,
max_output_patches 64 and trained quantiles including p10/p50/p90.

Direct inspection of released pipeline.py resolves an ambiguity in generic docs:
predict_quantiles returns per-item tensors with axes target/horizon/quantile;
the second value is assigned from the 0.5 training quantile although named mean.
The local interface must call it median. Document examples for other Chronos
generations and generic batch/horizon/quantile snippets are not adapter contracts.

Input mapping, masks, categorical encoding and local loading must be checked
against the pinned preprocessing code before implementation. Do not assume that
an upstream automatic mask or warning prevents temporal leakage. Explicitly
withhold future targets and past-only covariate futures and validate availability
at the cutoff. Cross-learning is disabled unless a reviewed same-partition group
contract is registered. NaN conversion stays internal to tested backend mapping;
public JSON preserves null/mask/reason records instead.

Optional dependency ranges in upstream pyproject are not a reproducible lock.
Resolve and license-review the full deployment closure for the approved Python
3.12+ CPU environment during implementation. Model provisioning is separate
from help/import/core installation and cannot happen before artifact approval.
