# SPEC-028: Native typed advisory decision foundation

## Purpose and scope

Engineering foundation for a local, non-generative, typed decision API with a deterministic reference backend. This milestone does not ship a pretrained general-purpose model.

Status: draft planning, human review pending. Dependencies: None; preserve SPEC-018/019/020/021 boundaries.
Milestone: S1.0 — Contracts. See the [program](../028-system-one-core/program.md)
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

- **REQ-001 — Typed decisions.** Requests support boolean, one-of-N choice and ordered-rubric score with explicit option IDs and question IDs.
  - **SC-001:** Given a valid request and a pinned backend, when each primitive is evaluated, then boolean P(true), choice distribution and score expected value are returned with stable identities; no generated text or arbitrary numeric regression.
- **REQ-002 — Strict validation and budgets.** Reject malformed, unknown-version, non-finite and ambiguous inputs before backend allocation; do not silently truncate state or options.
  - **SC-002:** Given duplicate IDs, NaN, bool-as-number, empty rubrics or over-budget input, when validation runs, then an explicit refusal identifies the boundary and the backend is never called.
- **REQ-003 — Decision provenance and confidence.** Report full distributions, raw concentration, top probability and calibration status separately, bound to immutable state, questions, backend and policy.
  - **SC-003:** Given uncalibrated logits or a changed artifact, when a response is constructed, then calibratedProbability is absent unless supported and response digests bind all decision inputs.
- **REQ-004 — No authority escalation.** Decision results are advisory and cannot mint certificates, grants, verified statuses or execution permission.
  - **SC-004:** Given a confidence of 1.0 and a forged verified field, when a consumer inspects the response, then executionAuthorization remains false and existing semantic verification is still required.
- **REQ-005 — Portable backend and default behavior.** The legacy analyzer and runtime work without ML packages, networks or System 1 configuration.
  - **SC-005:** Given an offline base install with System 1 disabled, when legacy commands run, then their outputs and failure behavior remain unchanged and optional backend imports are not attempted.
- **REQ-006 — Request isolation.** Keep request-local token offsets, state and caches isolated; bound admission and deterministic tie behavior.
  - **SC-006:** Given two interleaved requests with different options, when backend calls are overlapped or cancelled, then responses retain the correct request identities; ties use declared stable option-ID ordering.

## Scientific boundaries and compatibility

Hypothesis H1: A common contract can accommodate rules, linear advisors, decoder pointer heads and encoder heads without coupling the semantic core to ML.
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
