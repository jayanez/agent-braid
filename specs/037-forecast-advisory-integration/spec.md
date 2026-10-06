# SPEC-037: Bounded forecast advice, shadow integration and promotion

## Purpose and scope

Expose forecast-derived when/where recommendations as an opt-in consultative capability, integrate them with the existing bounded runtime and compatible typed System 1 consumers, and specify exact promotion/rollback gates. Preserve execution authority and all existing semantic evidence.

Status: draft planning; human review pending. Milestone: **FC.1 — Forecast-guided parallelism experiment**.
Dependencies: SPEC-034 resource/history receipts and SPEC-035 adapter controls. Rule-only advice engineering can precede a positive model result. Learned operational promotion requires SPEC-036 accepted utility for the exact capability; optional System 1 transport requires its independently accepted interface.

See the [shared program](../034-workload-forecast-data/program.md) and its explicit launch, evaluation and promotion gates.

User scenarios: an operator wants an economic preparation recommendation; an analyst needs reproducible actual outcome and cost receipts; a maintainer needs precise refusal, fallback and deployment limits.

## Authorities

Constitution clause zero and Articles 2–7, 9, 12–16, 19–25; GOVERNANCE.md; ADRs 0013, 0014, 0019 and 0020; operational semantics; claim discipline; existing versioned runtime/grant/verification contracts. Feature-local ADR proposals require separate adoption and do not modify normative authority.

## Requirements and acceptance scenarios

### REQ-001 — Separate typed forecast and advice contracts

Version forecast trajectories, units, horizon, model/data/resource provenance, status and uncertainty separately from discrete System 1 option distributions. Default forecasting is off; no schema widening by inserting unknown fields into legacy responses.

**SC-001:** Given a compatible client and an unsupported legacy response revision, when forecast discovery or advice is requested, then new opt-in envelopes are typed and unsupported versions refuse; existing default outputs and schemas retain their bytes/meaning.

### REQ-002 — Deterministic admissibility and placement limits

Rank only immutable options obtained from unchanged runtime constraints: supported serial/parallel preparation, existing ready waves and reviewed local capacity. Initial where support is one declared local profile; additional hosts/resources stay unavailable until separately contracted and measured.

**SC-002:** Given a faster predicted option with changed waves, unknown effects or a remote host, when the advisory mapper validates candidates, then it rejects the option and cannot invent waves, resources, migration or execution safety from prediction.

### REQ-003 — Fresh bindings and independent operator authority

Bind advice to exact manifest/input/resource/cutoff/artifact/policy receipts and expiry. Revalidate at point of use; a policy change requires its own matching existing operator grant supplied outside the forecast/model interface.

**SC-003:** Given stale advice, a forged grant or a chosen policy different from the authorized policy, when a host proposes consuming advice, then advice refuses or is recomputed, no grant is manufactured and recovery cannot reinterpret already committed execution choices.

### REQ-004 — Compatible System 1 feature bridge

Offer a versioned immutable forecast-summary input to an accepted System 1 capability as optional numeric context; keep categorical option confidence distinct from forecast interval coverage. Runtime-only advice remains possible while that consumer is deferred.

**SC-004:** Given a pending System 1 contract or interval presented as semantic confidence, when a bridge capability is requested, then unsupported transport defers precisely, interpretation errors refuse and native decision-model fitting is neither required nor silently expanded.

### REQ-005 — Shadow, fallback and complete trace

Record candidate/advice/reference action, resource group, refusal/disagreement and complete costs without changing shadow execution. Missing model, timeout, drift or wide uncertainty uses the reviewed non-model fallback; unknown/refused runtime inputs remain refused.

**SC-005:** Given shadow advice that disagrees with the reference or a timed-out model, when the host processes the request, then shadow executes only its independently authorized reference action, extra costs remain visible and no unobserved alternate outcome is presented as measured.

### REQ-006 — Exact-capability promotion, drift and rollback

Keep learned live selection disabled until a positive SPEC-036 utility decision, candidate-bound boundary validation and separate founder capability adoption. Restrict promotion by workload/resource/artifact/contract version; drift disables new advice and leaves in-flight runs under their original immutable contracts.

**SC-006:** Given an unaccepted subgroup, changed artifact or observed drift after promotion, when capability admission or rollback occurs, then unsupported requests fall back/refuse, future advice is disabled and active execution/recovery is not rewritten; milestone closure is a separate decision.

## Scientific boundaries and compatibility

Hypothesis: A separate typed forecast contract can inform economic recommendations without weakening deterministic analysis, grants, runtime recovery or semantic verification. Shadow observations alone do not establish deployment benefit.

Domain: Read-only recommendations over the current finite admissible serial/parallel preparation options and registered local resource profile; actual execution remains the existing separately authorized fixed-patch runtime.

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
