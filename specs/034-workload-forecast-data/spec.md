# SPEC-034: Permissioned workload telemetry and prospective forecast data

## Purpose and scope

Define the numeric history, resource identities and sampling frame needed to ask whether forecasting helps Agent Braid choose when and where admitted parallel preparation is useful. Build permissioned metadata tooling and causal windows; do not presume that Git history, source snapshots or ordered events already constitute forecastable series.

Status: draft planning; human review pending. Milestone: **FC.1 — Forecast-guided parallelism experiment**.
Dependencies: Existing SPEC-020/021 contracts; reuse SPEC-022 phase accounting only after checking its actual implementation and evidence. No dependency on M3.5 training or successful System 1 neural research.

See the [shared program](../034-workload-forecast-data/program.md) and its explicit launch, evaluation and promotion gates.

User scenarios: an operator wants an economic preparation recommendation; an analyst needs reproducible actual outcome and cost receipts; a maintainer needs precise refusal, fallback and deployment limits.

## Authorities

Constitution clause zero and Articles 2–7, 9, 12–16, 19–25; GOVERNANCE.md; ADRs 0013, 0014, 0019 and 0020; operational semantics; claim discipline; existing versioned runtime/grant/verification contracts. Feature-local ADR proposals require separate adoption and do not modify normative authority.

## Requirements and acceptance scenarios

### REQ-001 — Source admission and prospective sampling

Register the exact owner-approved sources, purpose, rights/privacy decision, consecutive collection window, eligible population and exhaustive exclusion reasons before capture; never admit public repository history as consent for workload collection.

**SC-001:** Given a proposed source and a consecutive window, when admission is evaluated before collection, then approved owned metadata may enter the registered population; absent rights, incomplete enumeration or changed source identity refuses capture and remains visible.

### REQ-002 — Typed telemetry and full-cost provenance

Record units, clock/source identity, workload/resource group, observed counters, phase boundaries and independent run receipts; exclude prompts, code, secrets and arbitrary host content. Do not present overlapping phase sums as total wall time.

**SC-002:** Given a run with unavailable RSS, overlapping worker intervals and raw phase receipts, when telemetry is encoded and reconciled, then actual zero differs from unavailable data; complete wall time has a declared residual and worker overlap is not counted twice.

### REQ-003 — Causal regularization and missingness

Create explicitly versioned time-grid histories with units and availability times; use only values known by the decision cutoff. Preserve masks and event-time versus arrival-time distinctions; reject silent imputation, backfill and mixed frequencies.

**SC-003:** Given late-arriving values, missing bins and future outcome timestamps, when a decision history is compiled, then only cutoff-available data enters inputs, masks remain explicit and retrospective backfill cannot change a frozen decision receipt.

### REQ-004 — Chronological grouped partitions

Split at the workload-episode/resource-group level before fitting, normalization or policy tuning; purge overlapping context/horizon windows and lock a later holdout. Synthetic rehearsal and real permissioned workload receipts remain separate.

**SC-004:** Given overlapping windows from one episode and later test outcomes, when partitions and transforms are frozen, then no episode or future outcome crosses fit/tuning/holdout boundaries; synthetic coverage never becomes real-source evidence.

### REQ-005 — Eligible local resource catalogue

Bind an allowlisted resource profile to its host/execution-contract revision, availability receipt, numerical caps and freshness. Initial where advice concerns registered local capacity and already admitted worker slots; no remote dispatch, provisioning or invented capacity.

**SC-005:** Given an unknown host, stale capacity or resource with incomplete isolation metadata, when resource eligibility is checked, then the resource is unavailable for placement and serial fallback remains possible only under its existing admission rules.

### REQ-006 — Feasibility and complete yield reporting

Report every registered episode/window, admission/exclusion/missingness count and independent-group count before the experiment; inspect action/outcome variability only in the development pilot, keeping calibration/holdout outcome values sealed. An inadequate series or one-option population exits as infeasible without training or a benefit claim.

**SC-006:** Given a short, constant or heavily missing prospective history, when the readiness packet is prepared, then yield, excluded episodes and actionable coverage are reported and the experiment stays pending or records infeasibility instead of manufacturing a larger corpus.

## Scientific boundaries and compatibility

Hypothesis: A prospective numeric history may have sufficient coverage, variability and temporal predictability to support useful advice. Insufficient history or no actionable variation is an acceptable feasibility result.

Domain: Owned or separately permissioned Agent Braid workload episodes, with the initial execution population restricted to existing 2–4 immutable ordinary-text A/M Git batches on a reviewed local resource profile.

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
