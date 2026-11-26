# SPEC-032: CPU, multilingual and structured decision capabilities

## Purpose and scope

Independently implement useful product patterns observed in Laya: CPU optimization, multilingual routing, schema-derived questions, large-catalogue retrieval, batching, lifecycle control and telemetry hooks. Defer browser automation, vision, email parsing, multiple language SDKs and framework-specific adapters until demand and evidence justify separate specs.

Status: draft planning, human review pending (`assurance.json`: stage `draft`, `human_review` pending). T001, T003, T004, T007 and T008 are checked for engineering evidence on the selected subset only (declared-metadata routing, schema compiler, hooks and packaging), as recorded in the tasks.md section "Obtained selected engineering evidence (2026-10-07)" and the `obtained:` fields of those tasks, which name `evidence/technical-delivery.json`; this is not feature, model or workload acceptance. T002, T005 and T006 are open and deferred ([product-decisions.md](product-decisions.md)). Dependencies: SPEC-028/029 contracts and evaluation; learned extensions require SPEC-030 selection. No advanced feature is an MVP prerequisite.
Milestone: S1.4 — Product capabilities and promotion. See the [program](../028-system-one-core/program.md)
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

Open questions: see [Open questions](#open-questions).

## Evidence and unresolved questions

Source inspection is in the analysis manifest; planned validation is in
[validation-plan.md](validation-plan.md). Feature/model/workload acceptance evidence:
none. All obtained_evidence arrays are empty and human_review is pending. Passing
planning validators establishes artifact structure, not implementation or utility.

## Current documentary reconciliation — 2026-10-20

[Corpus status](corpus-status.md) links the complete S1.x evidence history, obtained bounded results, proposed implementation tasks and remaining gates. Historical planning wording below/above is not a denial of later source research or an acceptance of its implementation. The master assurance remains historical/draft; no approval or activation is inferred.

## Non-functional requirements

SPEC-032 defines no latency, memory or cost threshold for promotion (see [Open questions](#open-questions), OQ-6). Constraints the sources state:

- Runtime: Python 3.12+, standard library for the core, optional ML package isolated (plan.md; no REQ covers it).
- Bounded schema compilation: input at most 1,048,576 bytes, container depth 16, at most 256 schema-node visits, 1 to 32 questions, 5,000 ms monotonic deadline (REQ-003; [contracts/product.md](contracts/product.md), T004).
- Bounded routing: `deadlineMs` is an integer from 1 to 5,000 and unsupported input defers (REQ-002; contracts/product.md, T003).
- Bounded hooks: at most 64 records of at most 1,024 canonical bytes each, a 5,000 ms cooperative ceiling, no background worker (REQ-006; contracts/product.md, T007).
- Reference core admission: one active and eight waiting requests; this is not neural serving support, and no REQ covers it (T006 deferred; [product-decisions.md](product-decisions.md)).
- Work bounds, not memory bounds: the contract bounds work, not OS peak RSS, and claims no hard CPU termination (contracts/product.md).
- Immutable identities: backend, request, capability, policy and calibration identities stay immutable (plan.md, Design and compatibility; no REQ covers it).
- Measurement: backend claims report probability or decision changes, cold and warm latency and peak RSS, with no blanket speed claims (REQ-001, T002 deferred).

## Security and privacy

- Hook observers cannot mutate sealed inputs or grant authority, and the observation buffer holds no prompts, descriptions, answers, operation or resource IDs or filesystem paths: see REQ-006 and [contracts/product.md](contracts/product.md).
- Private text is omitted by default; access and retention are explicit ([data-model.md](data-model.md); no REQ covers it).
- Advice stays heuristic with `executionAuthorization` false (plan.md, Constitution check after design; contracts/product.md).
- No security or privacy obligation beyond REQ-006 is normative. The plan also states: no `trust_remote_code`, no automatic network dependency, no copied reference weights or data, and no hidden effect-authority inference. Per the owner decision in [owner-decisions-20261126.md](evidence/owner-decisions-20261126.md), these and the deferrals in Purpose and scope (browser automation, vision, email parsing, multiple language SDKs, framework-specific adapters) are scope statements, not requirements.

## Terminology

Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md). Terms this spec uses:

- Extension: one independently selected or deferred capability among export/quantization, language and task routing, schema compiler, catalogue retrieval, batching and lifecycle, and hooks and packaging (REQ-001 to REQ-006; [product-decisions.md](product-decisions.md)).
- Declared-metadata routing: matching caller-declared language and task labels against a fixed installed registry, with no text inspection or confidence (REQ-002; [contracts/product.md](contracts/product.md)).
- Schema compiler: the pure function that turns a bounded schema into typed questions with stable schema pointers (REQ-003).
- Shortlist and tournament: retrieval or pairwise narrowing of a large catalogue, where finalist probability is conditional (REQ-004).
- Observation buffer: the data-only, bounded, pullable metadata store used instead of callbacks (REQ-006).
- DecisionContext, DecisionQuestion, DecisionAnswer, ModelManifest, CalibrationManifest, PolicyManifest, DecisionTrace: the records in [data-model.md](data-model.md).

Values named in this spec:

- Question primitives: `boolean`, `choice`, `score` (contracts/product.md).
- Extension disposition: `Selected`, `Deferred` ([product-decisions.md](product-decisions.md), T001).
- Routing status: `matched`, `unavailable`, `refused`, `defer` (contracts/product.md).
- Evidence class: `heuristic`.
- Assurance `stage`: `draft` or `validated`; `human_review`: `pending`, `changes-requested` or `approved` ([SPEC_KIT.md](../../docs/development/SPEC_KIT.md)).

## Risks and assumptions

- Risk: an export changes tokenizer or logits, or uses an unsupported operator (REQ-001, T002).
- Risk: language confidence is read as proof of in-domain input, or caller-declared en/es labels are read as language understanding (REQ-002, T003; product-decisions.md).
- Risk: a schema with refs, cycles or unrestricted strings is compiled with a changed meaning (REQ-003, T004).
- Risk: a pruned correct option or a finalist probability is read as whole-catalogue confidence (REQ-004, T005).
- Risk: unload during inference, cancellation or overload makes a request read another state or lose its model (REQ-005, T006).
- Risk: a hook mutates inputs or stalls, or an installed wheel lacks an advertised backend (REQ-006, T007).
- Risk: synthetic conformance fixtures are counted as source yield or product utility; research.md keeps them separate (T008).
- Assumption: local context is trusted and the existing deterministic verifiers are unchanged; no workload corpus, training budget or device coverage is assumed (`assurance.json` assumptions; OQ-1 to OQ-3).
- Assumption: the selected branches (T003, T004, T007) need no model selection, and deferred branches T002, T005 and T006 stay pending with their reconsideration conditions (plan.md, Optional branch ordering; product-decisions.md).
- Assumption: the CPU/device matrix is CPython 3.12+ standard library on the existing owned POSIX filesystem domain, with Linux and macOS evidence planned separately (product-decisions.md, T001).

## Exit criteria

Verification is complete when all of these hold:

- Each scenario SC-001 to SC-006 has named executable tests or an obtained research report in place of its prospective reference, with `evidence/sc-00x.json` binding candidate, input, command and environment hashes (validation-plan.md; REQ-001 to REQ-006). Deferred scenarios stay draft with empty obtained evidence.
- The selected tasks T001, T003, T004, T007 and T008 are bound to `evidence/technical-delivery.json` and its focused controls, Luna review, profile and offline-wheel records; the per-task `tNNN.json` and per-scenario `sc-00x.json` reports named in tasks.md and validation-plan.md are planned and do not exist yet. The final candidate verification `scripts/validate_change.py --base develop --profile pr` passes (tasks.md).
- T008 records a per-feature selected, deferred or evaluated disposition with actual evidence and remaining gates; a packet for a subset does not accept the whole spec or promote anything (tasks.md; plan.md).
- A human contract/protocol review is recorded (`human_review`; checklist CHK-008).
- Source permission, annotation, device envelope, acceptance evidence and per-capability promotion are recorded where a branch needs them (checklist CHK-009 to CHK-013).

Tests, procedures and feature evidence do not substitute for human review, scientific interpretation, source rights or promotion (tasks.md).

## Open questions

These restate the unresolved decisions of [Clarifications and unresolved decisions](#clarifications-and-unresolved-decisions) with their sources.

- OQ-1: What consented sources and eligible yield exist for fitting? The owner decided on 2026-11-01 that S1.5b labels come from real runs and git-history replay, in registered plugin workspaces only; other repositories need express approval each time ([owner-review-20261101.md](../066-system-one-shadow/owner-review-20261101.md) R9–R10). Other sources are undecided (checklist CHK-009; [evaluation protocol](../029-system-one-evaluation/evaluation-protocol.md)).
- OQ-2: Which deployment hardware and device envelope apply? (checklist CHK-011; evaluation protocol).
- OQ-3: Which paid-call and training budgets apply? (Clarifications and unresolved decisions).
- OQ-4: What rights apply to the base artifact? Decided 2026-11-01: native model only, own architecture, training and weights, with no third-party decision models or pretrained encoders, and ADR 0034 accepted as amended (owner-review-20261101.md R7–R8). Clarifications names final base-model rights as an open gate.
- OQ-5: What is the per-capability promotion go/no-go? (checklist CHK-013; SPEC-033/T008).
- OQ-6: What latency, memory and cost thresholds apply to promotion? None is defined in SPEC-032 (Non-functional requirements; T001).
- OQ-7: When is remote delivery authorized? Tracked separately from feature acceptance (Clarifications and unresolved decisions).
