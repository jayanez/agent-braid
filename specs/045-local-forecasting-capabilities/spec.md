# SPEC-045: Local forecasting capabilities and synthetic acceptance

## Purpose and scope

Milestone: **FC.2 — Local forecasting capabilities**. Implement the user-approved local forecasting flow using owned synthetic signals and fixed-patch fixtures, API/CLI/read-only MCP, cheap baselines and an optional local Chronos-2 CPU worker. Existing FC.1 research tasks remain individually tracked; synthetic receipts do not replace their source, experiment or adoption gates.

## Authorities

Constitution clause zero and Articles 2–7, 9, 12–14, 19–25; GOVERNANCE.md; operational semantics; ADRs 0013/0014/0019/0020; SPEC-034–037 interfaces. This feature-local design adopts no canonical ADR or constitutional change.

## Requirements and acceptance scenarios

### REQ-001 — Synthetic source and causal contracts

Only registered synthetic numeric receipts enter engineering; preserve units, availability, missingness and purged episode splits.

**SC-001:** Given a bound synthetic request and its negative control, when the corresponding boundary is exercised, then A late or malformed signal is excluded/refused without changing frozen input identities.

### REQ-002 — Independent local forecasting lifecycle

Lazy optional CPU inference has exact artifact approval, one active request, zero queue and verified owned-container limits.

**SC-002:** Given a bound synthetic request and its negative control, when the corresponding boundary is exercised, then Absent approval, drift, timeout or cancellation refuses before load/returns a accounted terminal result.

### REQ-003 — Finite advice and unchanged authority

Advice ranks only verified existing serial/parallel choices; shadow and rollback retain reference execution and independent grants.

**SC-003:** Given a bound synthetic request and its negative control, when the corresponding boundary is exercised, then A forged grant, altered candidate or expired receipt cannot cause dispatch.

### REQ-004 — Local API CLI and MCP parity

Versioned local numeric API/CLI/MCP expose capabilities, predict, advice and inspect with no grants, arbitrary paths or repository reads.

**SC-004:** Given a bound synthetic request and its negative control, when the corresponding boundary is exercised, then Unsupported input or missing backend returns precise refusal while default help/import load no ML.

### REQ-005 — Complete synthetic measurements and evidence

Preserve all registered synthetic episodes, arms and failures; reconcile complete cost; store/export only owned finite numeric receipts.

**SC-005:** Given a bound synthetic request and its negative control, when the corresponding boundary is exercised, then An invalid paired arm stays visible and cannot support favorable complete-case acceptance.

### REQ-006 — Bounded installed capability delivery

Bind wheel, synthetic reproduction, actual Chronos CPU conformance/costs, review and unresolved gates to a clean candidate.

**SC-006:** Given a bound synthetic request and its negative control, when the corresponding boundary is exercised, then Missing actual model conformance leaves that task pending while the rest of engineering evidence remains usable.

## Scientific boundaries and compatibility

Synthetic simulation, authentic measurement on synthetic workloads and permissioned real-workload evidence have distinct provenance. Forecasts are heuristic and executionAuthorization=false. Core dependencies remain empty, existing schemas/default behavior/grants/verifiers/waves remain authoritative, and System 1 bridging is explicitly unavailable until separately accepted. Native model fitting, distributed placement, new execution languages, automatic promotion and paid services are outside this delivery. Historical SPEC-021 G4 NO-GO remains unchanged.

## Evidence and unresolved questions

The owner authorized this implementation plan on 2026-10-13. Technical synthetic boundary review is recorded separately. Exact dependency/artifact approval precedes checkpoint provisioning/loading; source/privacy and real holdout registration remain FC.1 gates. No human or founder approval is inferred from hashes, issue state or technical/model reviews.
