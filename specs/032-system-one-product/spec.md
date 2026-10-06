# SPEC-032: CPU, multilingual and structured decision capabilities

## Purpose and scope

Independently implement useful product patterns observed in Laya: CPU optimization, multilingual routing, schema-derived questions, large-catalogue retrieval, batching, lifecycle control and telemetry hooks. Defer browser automation, vision, email parsing, multiple language SDKs and framework-specific adapters until demand and evidence justify separate specs.

Status: draft planning, human review pending. Dependencies: SPEC-028/029 contracts and evaluation; learned extensions require SPEC-030 selection. No advanced feature is an MVP prerequisite.
Milestone: S1.4 — Product and promotion. See the [program](../028-system-one-core/program.md)
and [source-backed analysis](../028-system-one-core/reference-analysis.md).

User scenarios: an analyzer operator requests bounded advice and inspectable reasons;
a host gets a precise abstention/fallback when input is unsupported; a maintainer
compares decision quality and complete cost without weakening semantic verification.

## Authorities

Constitution clause zero and Articles 2–7, 9, 12–16, 19–25; GOVERNANCE.md;
ADRs 0017, 0019, 0020; operational semantics; claim discipline; existing versioned
contracts. Proposed architecture choices stay feature-local until separately adopted.
No constitutional amendment, runtime authorization or scientific claim is implied.

## Requirements and acceptance scenarios

- **REQ-001 — CPU and optimized backend parity.** Provide only measured, artifact-bound CPU/export/quantized backend support with exact capability reporting.
  - **SC-001:** Given an export with changed tokenizer, logits or unsupported operator, when backend selection runs, then parity failures disable it and the unoptimized supported path remains available.
- **REQ-002 — Language and task routing.** Validate English/Spanish and declared language/task groups before routing; confidence alone cannot identify out-of-domain input.
  - **SC-002:** Given non-English, uncertain language, code-mix or unknown task, when routing occurs, then unsupported input defers or uses an explicitly validated backend and calibration group.
- **REQ-003 — Schema compiler limits.** Compile bounded boolean, enum and ordinal fields into typed questions with stable schema pointers.
  - **SC-003:** Given local refs, nullable enums, cycles or unrestricted strings, when schema compilation occurs, then supported meanings are preserved and unsupported generation/ref recursion is refused precisely.
- **REQ-004 — Large-catalogue probability semantics.** Expose retrieval/tournament selection and recall loss; finalist probability is conditional, never whole-catalogue confidence.
  - **SC-004:** Given the correct option is pruned or finalists change, when a narrowed decision is evaluated, then dropped options and subset identity are logged; shortlist recall and full-catalogue baseline are measured.
- **REQ-005 — Batching and lifecycle safety.** Bound token-aware batching, queue admission and idle unloading without evicting in-use models.
  - **SC-005:** Given concurrent batches, reload, cancellation and memory pressure, when serving lifecycle runs, then no request reads another state or loses its model; overload refuses within the declared deadline.
- **REQ-006 — Observability and packaging.** Offer bounded read-only hooks and offline wheel validation; optional backends are actually packaged.
  - **SC-006:** Given a hook mutates inputs, stalls or an installed wheel lacks a backend, when the packaged consumer runs, then mutation is rejected, timeout stays bounded and backend capabilities match installed contents.

## Scientific boundaries and compatibility

Hypothesis H1: Specialized compact models and input-aware routing may improve deployment economics; retrieval and tournament narrowing may harm recall or calibration and must be evaluated.
Heuristic confidence is not a proof of effects, commutation, confluence, braid laws
or execution safety. Preserve SPEC-019 eligibility/label construct and SPEC-021 G4
NO-GO; this track cannot close M3.5 or M4. Legacy versions and default behavior remain
unchanged; planned APIs/extras are additive and need their own contract review.

## Clarifications and unresolved decisions

The user requests own analogous capabilities, no upstream package/model integration,
an unbiased comparison and complete Spec Kit implementation planning. Public repository
documents remain English; the user-facing explanation is Spanish. Starting with typed
Strands-like contracts does not preselect a decoder model. Unknowns that do not block
planning are explicit implementation gates: consented source/yield, available deployment
hardware, paid/training budgets, final base-model rights and per-capability promotion.
No dataset, hardware support or approval has been invented. Remote delivery authorization
is tracked separately from feature acceptance.

## Evidence and unresolved questions

Source inspection is in the analysis manifest; planned validation is in
[validation-plan.md](validation-plan.md). Feature/model/workload acceptance evidence:
none. All obtained_evidence arrays are empty and human_review is pending. Passing
planning validators establishes artifact structure, not implementation or utility.
