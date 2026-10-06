# SPEC-033: Shadow validation, promotion, drift and rollback

## Purpose and scope

Operational engineering for opt-in shadow decisions, per-capability promotion, drift monitoring, rollback and bounded closure. No automatic online learning, external telemetry export, paid model calls or milestone closure.

Status: draft planning, human review pending. Dependencies: SPEC-029 registered evaluation and SPEC-031 consumers; advanced SPEC-032 features promote independently and may stay deferred.
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

## Evidence and unresolved questions

Source inspection is in the analysis manifest; planned validation is in
[validation-plan.md](validation-plan.md). Feature/model/workload acceptance evidence:
none. All obtained_evidence arrays are empty and human_review is pending. Passing
planning validators establishes artifact structure, not implementation or utility.
