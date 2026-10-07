# SPEC-035: Optional local Chronos-2 forecast adapter

## Purpose and scope

Implement an opt-in local numeric forecasting adapter for the Chronos-2 base checkpoint, producing inspectable p10/p50/p90 trajectories for admitted telemetry. Preserve a dependency-free Agent Braid core and an explicit offline model boundary. This feature integrates a third-party forecasting model; it does not alter the own decision-model experiment in SPEC-030.

Status: draft planning; human review pending. Milestone: **FC.1 — Forecast-guided parallelism experiment**.
Dependencies: SPEC-034 telemetry/window/resource contracts. Synthetic adapter work can proceed after interface review without real-workload admission; actual model download/loading needs the distinct artifact/budget gate.

See the [shared program](../034-workload-forecast-data/program.md) and its explicit launch, evaluation and promotion gates.

User scenarios: an operator wants an economic preparation recommendation; an analyst needs reproducible actual outcome and cost receipts; a maintainer needs precise refusal, fallback and deployment limits.

## Authorities

Constitution clause zero and Articles 2–7, 9, 12–16, 19–25; GOVERNANCE.md; ADRs 0013, 0014, 0019 and 0020; operational semantics; claim discipline; existing versioned runtime/grant/verification contracts. Feature-local ADR proposals require separate adoption and do not modify normative authority.

## Requirements and acceptance scenarios

### REQ-001 — Optional packaging and default behavior

Keep core dependencies empty and import/help/default CLI paths free of torch, transformers and model loading. Package the adapter as a named optional extra with a tested isolated wheel and a visible unavailable result when absent.

**SC-001:** Given an installation without optional ML packages, when the default CLI or forecast discovery runs, then core behavior is unchanged, no model import or download occurs and an explicit unsupported request refuses precisely.

### REQ-002 — Approved immutable model and dependency provenance

Require the approved package/checkpoint revisions, local file hashes, dependency lock, licenses and deployment budget before any model provisioning or evaluation. The inspected v2.3.2/base-checkpoint identities are candidates, not approvals.

**SC-002:** Given an unapproved manifest, mutable model reference or changed checkpoint file, when provisioning or loading is requested, then it refuses before network/download/load; only approved hashes in an isolated local installation are accepted.

### REQ-003 — Role-aware causal input mapping

Validate stable target/channel identities, equal cadence, context limits, masks and cutoff availability; keep past-only covariates out of future slots and allow future covariates only with cutoff-known provenance. Disable cross-learning between unrelated partitions.

**SC-003:** Given multiple targets, a past-only channel and an unknown future value, when inputs are translated for Chronos2Pipeline, then target order and masks are preserved, future outcomes never enter covariates and unsupported representations refuse without silent filling.

### REQ-004 — Quantile and point-output semantics

Normalize the pinned predict_quantiles output from per-item target/horizon/quantile tensors; verify shapes, finite output and ordered p10/p50/p90. Report the pinned second return value as median, despite its upstream mean variable name. Intervals have measured coverage, not guaranteed truth.

**SC-004:** Given reordered channels, crossed/nonfinite quantiles or the upstream mean-named median return, when a forecast envelope is emitted, then valid p50 is labeled median with units/horizon; malformed output refuses and nominal interval levels are not reported as calibrated coverage.

### REQ-005 — Bounded offline lifecycle and failure

Bound queue, memory, CPU threads, batch/context/horizon, wall time and cancellation in a separate worker; reject an unsupported enforcement profile. Measure startup, resident and failure costs. No cloud endpoint, credentials or background model service.

**SC-005:** Given a worker that hangs, crashes, exceeds budget or lacks memory enforcement, when the request deadline or shutdown occurs, then the owned process is stopped under its reviewed contract, resources are accounted for and advice refuses without executing a workload.

### REQ-006 — Causal reuse and request isolation

Reuse forecasts only under a key binding artifact, preprocessing, cutoff, full input/mask, partition, resource snapshot, capability and horizon. No shared mutable model state between simultaneous requests or test/development episodes.

**SC-006:** Given two similar requests with different masks or a new resource receipt, when a forecast cache or lifecycle reuse is attempted, then the cache misses or refuses appropriately and cached/uncached outputs meet declared numerical tolerance without hidden future inputs.

### REQ-007 — Conformance and complete adapter cost

Validate installed CPU behavior against pinned source and synthetic controls, then record local latency/memory and calibration status. Stubs prove contract behavior only; real checkpoint conformance does not establish workload benefit.

**SC-007:** Given a stub-passing adapter and an approved real CPU checkpoint run, when the conformance packet is produced, then stub and real results are distinguished, unsupported devices are unclaimed and loading/inference/fallback costs remain in later policy accounting.

## Scientific boundaries and compatibility

Hypothesis: An existing pretrained Chronos-2 model may produce useful forecasts on local telemetry without fine-tuning; prediction quality, latency and CPU economics remain unmeasured.

Domain: Bounded univariate/multivariate numeric histories and allowlisted covariates from SPEC-034, initially one request at a time on an explicitly measured CPU profile.

All four specs are draft planning records with human review pending. This packet
authorizes no workload collection, model download, fitting, benchmark execution,
paid service or live forecast-guided policy. Implementation may begin only after
the applicable technical contract review; real data, model loading, experiment
execution and promotion have distinct gates. No implementation task is complete.

The supported execution language remains 2–4 immutable ordinary-text A/M Git
patches in owned local scratch with the existing independent operator grant,
deterministic verifier and pinned tracked-tree observation. No source promotion,
repository code execution, remote runner, provisioning, cloud endpoint or changed
isolation boundary is introduced. Complete effects/dependencies, point-of-use
resource versions and enabledness are checked independently of advice. Scores
and forecast intervals are heuristic, not commutation or confluence evidence.

Chronos-2 zero-shot inference is the selected forecasting integration. Native
System 1 decision heads and SPEC-019 utility ranking retain their own targets,
sources and gates. No fine-tuning, continual learning or training on model/host
self-generated labels is in the initial experiment. A null, negative,
inconclusive or infeasible protocol outcome is valid. SPEC-021 G4 NO-GO, M4 open
status, M3/M3.5 scientific gates and historical evidence remain unchanged.

## Evidence and unresolved questions

Acceptance evidence: none. Upstream documentation/source inspection supports interface planning only. No model was installed/downloaded/evaluated and no new workload window was collected by drafting this record. Exact permissions, corpus yield, hardware enforcement, numerical budget and capability decisions remain visible implementation gates. Planned thresholds are review candidates; public benchmark rankings do not accept local utility.
