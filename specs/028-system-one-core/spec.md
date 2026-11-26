# SPEC-028: Native typed advisory decision foundation

## Purpose and scope

Engineering foundation for a local, non-generative, typed decision API with a deterministic reference backend. This milestone does not ship a pretrained general-purpose model.

Status: `assurance.json` stage `validated` for bounded synthetic software checks, `human_review` pending. Task status as of 2026-11-26 (`tasks.md`): T001–T008 are checked for the bounded engineering lot (`evidence/technical-delivery.json`, 2026-10-07); T009–T011 are checked for bounded engineering lots only (2026-10-20 documentary reconciliation in `tasks.md`). Dependencies: None; preserve SPEC-018/019/020/021 boundaries.
Milestone: S1.0 — Decision contracts. See the [program](../028-system-one-core/program.md)
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

Open questions: see [Open questions](#open-questions).

## Evidence and unresolved questions

Source inspection is in the analysis manifest; planned validation is in
[validation-plan.md](validation-plan.md). Feature/model/workload acceptance evidence:
none. Each scenario's obtained_evidence holds one synthetic software check; human_review is pending. Passing
planning validators establishes artifact structure, not implementation or utility.

## Current documentary reconciliation — 2026-10-20

[Corpus status](corpus-status.md) links the complete S1.x evidence history, obtained bounded results, proposed implementation tasks and remaining gates. Historical planning wording below/above is not a denial of later source research or an acceptance of its implementation. The master assurance remains historical/draft; no approval or activation is inferred.

## Non-functional requirements

SPEC-028 defines no promotion threshold for latency, memory or cost (see [Open questions](#open-questions), OQ-4). The limits below are stated in the sources; those in [contracts/decision-api.md](contracts/decision-api.md) are a draft envelope and those in [contracts/stdlib-v1.md](contracts/stdlib-v1.md) a provisional profile, both feature-local and not adopted authority:

- Input bounds: 1 MiB canonical JSON (raw bytes checked before parsing), 1 to 32 questions, 2 to 32 options per choice or score, at most 64 UTF-8 bytes per identifier, nesting depth 16 (REQ-002; decision-api.md; stdlib-v1.md).
- Budgets: the caller supplies integer ceilings `maxInputBytes`, `maxQuestions`, `maxOptions`, `maxTokens` and `deadlineMs` (at most 5,000 ms); booleans are not numeric budgets and there are no implicit defaults (REQ-002; stdlib-v1.md).
- Admission and deadline: one active neural evaluation, queue bound 8, request deadline 5 s, zero retries by default; admission, queue time, model load, tokenization and compute all count toward the deadline (REQ-006; decision-api.md).
- Numeric: distributions are finite, nonnegative and sum to 1 within 1e-6; head, softmax and calibration run in fp32 or stronger (REQ-001, REQ-003; decision-api.md).
- Determinism: ties use stable option-ID ordering (REQ-006; decision-api.md).
- Hard compute deadlines need a killable worker boundary; a Python thread timeout cannot stop GPU work. Backend memory and token caps must be frozen per device before use (decision-api.md; no REQ covers it).
- Runtime: Python 3.12+, standard library for the core, the optional ML package isolated from core import paths (plan.md; REQ-005 covers only the no-ML default path).

## Security and privacy

- Advice cannot mint certificates, grants, verified statuses or execution permission; `executionAuthorization` remains false: see REQ-004.
- Malformed, unknown-version, non-finite and ambiguous input is rejected before backend allocation: see REQ-002.
- Legacy behavior needs no ML package, network or System 1 configuration: see REQ-005.
- Private text is omitted from decision traces by default; access and retention are explicit ([data-model.md](data-model.md)).
- No security or privacy obligation beyond REQ-002, REQ-004 and REQ-005 is normative. The plan and contract also state: no `trust_remote_code`, no automatic network dependency, no copied reference weights or data, no hidden effect-authority inference, no external inference endpoint configured by default, and no caller-controlled field that invokes code, imports, reads files or selects a URL (plan.md; decision-api.md; stdlib-v1.md). Per the owner decision in [owner-decisions-20261126.md](evidence/owner-decisions-20261126.md), these are scope statements, not requirements.

## Terminology

Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md). Terms this spec uses:

- Primitive: one typed decision kind: `boolean`, `choice` or `score` (REQ-001; [contracts/decision-api.md](contracts/decision-api.md)).
- Backend: an implementation of the typed backend protocol (`capabilities()`, `evaluate(request, deadline, cancellation)`, `close()`); the first is a deterministic rule backend (plan.md; decision-api.md).
- Raw concentration and top probability: uncalibrated readouts reported separately from `calibratedProbability`, which is present only when calibration supports it (REQ-003).
- Abstain, defer, refuse: response `status` values besides `answered`; none authorizes execution (REQ-004; decision-api.md).
- Advisory: a heuristic recommendation with `evidenceClass: heuristic` and `executionAuthorization: false` (REQ-004).
- DecisionContext, DecisionQuestion, DecisionAnswer, ModelManifest, CalibrationManifest, PolicyManifest, DecisionTrace: the records in [data-model.md](data-model.md).

Values named in this spec:

- Response `status`: `answered`, `abstain`, `defer`, `refused` (decision-api.md).
- `calibrationStatus`: `absent`, `fitted`, `validated`, `stale` (decision-api.md).
- Question `type`: `boolean`, `choice`, `score`; `contractVersion` of the reference profile: `decision-stdlib-v1` (decision-api.md; stdlib-v1.md).
- Assurance `stage`: `draft` or `validated`; `human_review`: `pending`, `changes-requested` or `approved` ([SPEC_KIT.md](../../docs/development/SPEC_KIT.md)).

## Risks and assumptions

- Risk: invalid input reaches a backend or is silently truncated; validation runs first and refuses (REQ-002, T002).
- Risk: confidence is read as proof of effects, commutation or execution safety; advice stays heuristic with authorization false (REQ-003, REQ-004, T004, T005).
- Risk: calibration is population-specific and a rule-derived row looks calibrated; calibratedProbability stays absent unless supported (REQ-003, T004; decision-api.md).
- Risk: overlapping or cancelled requests mix state or emit late advice (REQ-006, T006).
- Risk: the new capability changes legacy behavior or imports optional packages by default (REQ-005, T003, T007).
- Risk: adding inference may increase total decision cost and narrowing may lose the correct label (analysis.md, known tradeoffs; no task measures it here).
- Risk: request-level timeouts need killable worker boundaries for a hard resource guarantee (analysis.md; decision-api.md; REQ-006 covers bounded admission only).
- Assumption: local context is trusted and existing deterministic verifiers are unchanged; no workload corpus, training budget or device coverage is assumed (`assurance.json` assumptions; OQ-1 to OQ-3).
- Assumption: the reference profile has no neural backend; synthetic conformance results are not real utility ([stdlib-v1.md](contracts/stdlib-v1.md); research.md).

## Exit criteria

Verification is complete when all of these hold:

- Each scenario SC-001 to SC-006 has named executable tests with `evidence/sc-00x.json`-style candidate, input, command and environment hashes in `assurance.json` (validation-plan.md; REQ-001 to REQ-006). Obtained today: one synthetic software check per scenario.
- Each task T001–T008 has its candidate-bound report under `evidence/`, and the final candidate verification `scripts/validate_change.py --base develop --profile pr` passes (tasks.md).
- A human contract/protocol review is recorded (`human_review`; checklist CHK-008), which is still pending.

Tests, procedures and feature evidence do not substitute for human review, scientific interpretation, source rights or promotion (tasks.md).

## Open questions

- OQ-1: What consented sources and eligible yield exist for fitting? Owner: owner; tracked in SPEC-029/T001 (Clarifications; CHK-009).
- OQ-2: Which deployment hardware and device envelope apply? Owner: owner (Clarifications; CHK-011).
- OQ-3: Which paid-call and training budgets apply? Owner: owner (Clarifications).
- OQ-4: What latency, memory and cost thresholds govern promotion? Owner: owner; the limits under Non-functional requirements are draft envelope values, not thresholds (CHK-011).
- OQ-5: Which final base-model rights apply to the artifact the owner builds? Owner: owner (Clarifications).
- OQ-6: When is remote delivery authorized? Owner: owner; tracked separately from feature acceptance (Clarifications).
- OQ-7: What is the per-capability promotion decision? Owner: owner; decided in SPEC-033/T008 (CHK-013).
- OQ-8: When is the human contract/protocol review recorded? Owner: owner (CHK-008; `assurance.json` `human_review`).
