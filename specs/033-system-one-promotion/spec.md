# SPEC-033: Shadow validation, promotion, drift and rollback

## Purpose and scope

Operational engineering for opt-in shadow decisions, per-capability promotion, drift monitoring, rollback and bounded closure. No automatic online learning, external telemetry export, paid model calls or milestone closure.

Status: draft planning, human review pending (`assurance.json`: stage `draft`, `human_review` pending). T001–T008 are open; T009 (bounded documentary lot) is done. Dependencies: SPEC-029 registered evaluation and SPEC-031 consumers; advanced SPEC-032 features promote independently and may stay deferred.
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

- **REQ-001 — Opt-in shadow and privacy.** Capture bounded decision metadata without changing behavior or exporting private source content by default.
  - **SC-001:** Given System 1 shadow enabled on a permissioned workload, when advice is recorded, then legacy plan/execution outputs remain identical and content retention follows the registered source policy.
- **REQ-002 — Promotion gates.** Promote only exact capability/model/policy artifacts with reviewed risk, calibration, cost and evidence coverage.
  - **SC-002:** Given a candidate passing unit checks but lacking workload evidence or approval, when promotion is requested, then it stays pending with explicit missing gates; a result from another language/task is not substituted.
- **REQ-003 — Drift and abstention.** Monitor input-domain, label/coverage and calibration drift without treating unlabeled scores as truth.
  - **SC-003:** Given unsupported groups, changed distributions or delayed labels, when monitoring detects a boundary breach, then the affected capability falls back and label-dependent metrics remain unknown until labels arrive.
- **REQ-004 — Rollback and immutable release.** Support atomic return to deterministic/no-advisor behavior and tamper-proof artifact identity checks.
  - **SC-004:** Given a replaced artifact or operator rollback, when the next request resolves its pinned manifest, then no mixed model/calibration pair is served and in-flight behavior follows its original sealed identity.
- **REQ-005 — Budgeted fallback.** Bound every fallback chain including System 2 and verifier costs; no infinite escalation loop.
  - **SC-005:** Given backend unavailable, OOM or deadline exhausted, when fallback is attempted, then a finite declared chain defers safely and reports total cost without unauthorized remote/paid calls.
- **REQ-006 — Closure discipline.** Close engineering and research protocols separately from utility, hardware support or mathematical claims.
  - **SC-006:** Given negative utility or pending real-host evidence, when the closure packet is reviewed, then open gates stay open, M4 NO-GO remains unchanged and no model confidence is presented as semantic proof.

## Scientific boundaries and compatibility

Hypothesis H1: Total cost can improve at matched verified outcomes for selected workloads. No universal improvement, production readiness or formal claim is presumed.
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

SPEC-033 defines no latency, memory or cost threshold (see [Open questions](#open-questions), OQ-6). Operational and quality constraints this spec states:

- Bounded fallback: every fallback chain is finite and its total cost, including System 2 and verifier, is reported (REQ-005).
- Atomic return: rollback to deterministic/no-advisor behavior is atomic, and the next request resolves its pinned manifest (REQ-004).
- Immutable identity: backend, request, capability, policy and calibration identities are immutable, and no mixed model/calibration pair is served (REQ-004).
- Bounded storage: shadow capture stores bounded decision metadata (REQ-001, T002).
- Unchanged behavior: shadow mode leaves legacy plan and execution outputs identical (REQ-001).
- Runtime: Python 3.12+, standard library for the core, the optional ML package isolated from core import paths (plan.md; no REQ covers it).

## Security and privacy

- Private source content is not exported by default, and content retention follows the registered source policy: see REQ-001.
- Remote or paid service calls require authorization: see REQ-005.
- Artifact identity is checked against tampering: see REQ-004.
- No security or privacy obligation beyond these three REQs is normative. The plan also states: no `trust_remote_code`, no automatic network dependency, no copied reference weights or data, and no hidden effect-authority inference. Per the owner decision in [owner-decisions-20261126.md](evidence/owner-decisions-20261126.md), these and the exclusions in Purpose and scope (online learning, external telemetry export, paid model calls, milestone closure) are scope statements, not requirements.

## Terminology

Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md). Terms this spec uses:

- Shadow mode: opt-in recording of System 1 advice that does not affect planning or execution (REQ-001).
- Capability: one separately registered advisory function; promotion is decided per capability (REQ-002).
- Promotion: the recorded decision that an exact capability/model/policy artifact set may be used; it stays pending while a gate is missing (REQ-002).
- Drift: a change in input domain, label/coverage or calibration (REQ-003).
- Abstention and fallback: the capability defers to deterministic or no-advisor behavior (REQ-003, REQ-005).
- Manifest: the immutable record binding model, tokenizer, head, adapter, backend, calibration or policy identities (REQ-004; [data-model.md](data-model.md)).
- DecisionContext, DecisionQuestion, DecisionAnswer, DecisionTrace: the records in [data-model.md](data-model.md).
- Closure packet: the exact-candidate packet reviewed at closure (REQ-006, T007).

Values named in this spec:

- Logical primitive names: `boolean`, `choice`, `score` ([contracts/interface.md](contracts/interface.md)).
- Assurance `stage`: `draft` or `validated`; `human_review`: `pending`, `changes-requested` or `approved` ([SPEC_KIT.md](../../docs/development/SPEC_KIT.md)).
- Promotion state named in SC-002: `pending`.

## Risks and assumptions

- Risk: a candidate that passes unit checks is promoted without workload evidence; promotion stays pending with the missing gates named (REQ-002).
- Risk: unlabeled scores are read as truth; label-dependent metrics stay unknown until labels arrive (REQ-003).
- Risk: a replaced artifact serves a mixed model/calibration pair (REQ-004).
- Risk: a fallback chain loops or escalates without a bound (REQ-005, T005).
- Risk: sparse groups, proxy labels or conformance fixtures are counted as product utility; research.md keeps them separate and the pilot records full cost and null/negative outcomes (REQ-006, T006).
- Assumption: local context is trusted and the existing deterministic verifiers are unchanged; no workload corpus, training budget or device coverage is assumed (`assurance.json` assumptions; OQ-1 to OQ-3).
- Assumption: SPEC-066 absorbs the open T002, T003, T004, T006 and T008 and carries them as T203 and T401–T403 (tasks.md note; T002, T003, T004, T006, T008).

## Exit criteria

Verification is complete when all of these hold:

- Each scenario SC-001 to SC-006 has named executable tests or an obtained research report in place of its prospective reference, with `evidence/sc-00x.json` binding candidate, input, command and environment hashes (validation-plan.md; REQ-001 to REQ-006).
- Each task T001–T008 has its planned evidence report under `evidence/`, and the final candidate verification `scripts/validate_change.py --base develop --profile pr` passes (tasks.md).
- The closure packet separates software passing, utility or no-gain, host/hardware coverage and pending independent review (T007; REQ-006).
- A human contract/protocol review is recorded (`human_review`; checklist CHK-008).
- A per-capability promotion or no-go decision is recorded by the owner (T008; REQ-002).

Tests, procedures and feature evidence do not substitute for human review, scientific interpretation, source rights or promotion (tasks.md).

## Open questions

- OQ-1: What consented sources and eligible yield exist for fitting? Owner: owner. The owner decided on 2026-11-01 that S1.5b labels come from real runs and git-history replay, in registered plugin workspaces only; other repositories need express approval each time ([owner-review-20261101.md](../066-system-one-shadow/owner-review-20261101.md) R9–R10). Other sources are undecided (SPEC-029/T001; T006).
- OQ-2: Which deployment hardware and device envelope apply? Owner: owner (checklist CHK-011; [evaluation-protocol.md](../029-system-one-evaluation/evaluation-protocol.md)).
- OQ-3: Which paid-call and training budgets apply? Owner: owner (REQ-005).
- OQ-4: What rights apply to the base artifact the owner builds? Owner: owner. Decided 2026-11-01: native model only, own architecture, training and weights, with no third-party decision models or pretrained encoders, and ADR 0034 accepted as amended ([owner-review-20261101.md](../066-system-one-shadow/owner-review-20261101.md) R7–R8); rights to the owner's own artifact remain open.
- OQ-5: What is the per-capability promotion go/no-go? Owner: owner (T008; REQ-002).
- OQ-6: What latency, memory and cost thresholds apply to promotion and fallback? Owner: owner; none is defined in SPEC-033 (Non-functional requirements; T001). SPEC-066 sets a 50 ms wall-time budget per shadow call, which covers the absorbed T002 only ([SPEC-066](../066-system-one-shadow/spec.md)).
- OQ-7: When is remote delivery authorized? Owner: owner; tracked separately from feature acceptance.
