# SPEC-036: Prospective forecast-guided parallelism utility experiment

## Purpose and scope

Test whether temporal forecasts improve the when/where economic choice among already admissible Agent Braid preparation options on its own permissioned workloads. Evaluate forecasting and downstream policy utility separately, against strong inexpensive baselines, with complete costs and valid negative/inconclusive exits.

Status: draft planning; human review pending. Milestone: **FC.1 — Forecast-guided parallelism experiment**.
Dependencies: SPEC-034 data readiness and SPEC-035 measured adapter; SPEC-037 constrained advice mapping for the policy arm. Existing SPEC-022 accounting can be reused only with candidate-bound validation. SPEC-019 labels and SPEC-030 model fitting are not prerequisites.

See the [shared program](../034-workload-forecast-data/program.md) and its explicit launch, evaluation and promotion gates.

User scenarios: an operator wants an economic preparation recommendation; an analyst needs reproducible actual outcome and cost receipts; a maintainer needs precise refusal, fallback and deployment limits.

## Authorities

Constitution clause zero and Articles 2–7, 9, 12–16, 19–25; GOVERNANCE.md; ADRs 0013, 0014, 0019 and 0020; operational semantics; claim discipline; existing versioned runtime/grant/verification contracts. Feature-local ADR proposals require separate adoption and do not modify normative authority.

## Requirements and acceptance scenarios

### REQ-001 — Prospective protocol and reviewed budget

Freeze sources, independent units, folds, target/horizon/cadence, candidate roster, resource groups, quality/coverage limits, action mapping and numerical budget before scoring the holdout. A changed protocol restarts with a new untouched holdout.

**SC-001:** Given a candidate protocol with inspected pilot results, when the evaluation registration is reviewed, then all tuning uses development data and a later untouched holdout is frozen; absent source, yield or compute approval produces infeasible/pending.

### REQ-002 — Mandatory low-cost baselines and comparable information

Compare persistence, an EWMA family and an operation-feature regression baseline with zero-shot Chronos-2; freeze any optional Toto 2.0 comparison before holdout access. Baselines receive the same cutoff-available information and deployment-cost accounting.

**SC-002:** Given a model roster and variable-duration operations, when methods are fitted/tuned on development data and evaluated, then operation regression is not mislabeled as temporal forecasting, all mandatory baselines run and optional methods or failures cannot be selected after seeing test results.

### REQ-003 — Forecast quality, uncertainty and actionable coverage

Report per-target/horizon/group MAE, scaled error only when its denominator is defined, quantile loss and nominal p10–p90 coverage/width. Register sparse/constant/unsupported groups and abstention. Temporal prediction metrics do not establish scheduling utility or semantic validity.

**SC-003:** Given constant series, missing forecasts and wide or miscalibrated intervals, when forecast metrics are calculated, then undefined metrics retain reasons, coverage and failures remain visible and no uncalibrated interval becomes a safety probability.

### REQ-004 — Constraint-admissible policy choice

Map numeric forecasts and operation descriptors to only existing admissible serial/parallel/resource options; retain deterministic ready/dependency/isolation/grant checks. The mapping and abstention threshold are frozen before holdout; future treatment timings are outcome labels only.

**SC-004:** Given a high-value forecast for a conflicting batch or unregistered resource, when the advisory action is selected, then it refuses that option and keeps existing fallback; no unknown effect becomes commuting and no unmeasured resource gains claimed placement benefit.

### REQ-005 — Paired complete-cost execution boundary

Measure advice plus loading, telemetry preparation, cache work, grants, replay, isolated preparation, independent verification, serialization and cleanup with an explicit residual; capture waiting/deferred cost if an admitted policy ever includes it. Use fresh private runs and fixed input trees; every attempted arm stays in the record.

**SC-005:** Given matched workload episodes and an inference timeout or invalid execution arm, when the registered comparison runs, then complete cost and outcomes for every attempted policy are retained; invalid pairs make their acceptance group inconclusive rather than disappearing from favorable complete cases.

### REQ-006 — Adversarial controls and historical separation

Include leakage, stale resource receipts, forged grants, missing/late targets, nonstationarity, dependency-chain negative controls, refusal, cancellation and recovery. Synthetic controls validate tooling only; SPEC-021 G4 NO-GO and previous SPEC-022 observations remain historical.

**SC-006:** Given forged high-confidence advice or historical timings copied into test inputs, when controls and provenance checks execute, then unauthorized actions are refused, copied evidence cannot establish a fresh result and predictor correctness never substitutes for verifier agreement.

### REQ-007 — Prespecified utility and statistical interpretation

Evaluate each preregistered workload/resource group against the strongest non-model policy chosen on development data and report the serial reference. Use episode-level independent units, complete coverage and declared uncertainty; repeated timings of one fixture do not create independent workloads.

**SC-007:** Given small group counts, one beneficial subgroup or unstable repeated timings, when the utility report and threshold decision are produced, then insufficient groups or invalid pairs stay inconclusive; subgroup selection and optional stopping cannot turn exploratory results into accepted benefit.

### REQ-008 — Supported, negative, inconclusive and infeasible decisions

Publish a candidate-bound decision packet with all raw identities, denominators, costs and limits. Finishing the protocol never requires positive benefit. A separate exact-capability founder decision controls adoption and cannot close M4 or M3.5.

**SC-008:** Given a complete experiment with no economic gain, when the experiment exit is reviewed, then the negative result completes the research protocol, Chronos remains unpromoted and all existing milestone/scientific gates remain unchanged.

## Scientific boundaries and compatibility

Hypothesis: H1: numeric telemetry is forecastable at useful horizons. H2: forecast-informed choices improve complete wall time against a validation-selected non-model policy at matched admission and verification. H1 does not imply H2; either may fail.

Domain: Later held-out permissioned workload episodes/resource profiles admitted by SPEC-034, using the unchanged SPEC-020/021 fixed-patch execution language and observation/verifier contracts.

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
