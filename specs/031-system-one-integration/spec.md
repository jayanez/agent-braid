# SPEC-031: Advisory integration across Agent Braid decision stages

## Purpose and scope

Expose native System 1 recommendations for every architectural stage through an explicit registry of capabilities. Only enabled, evidenced consumers are integrated; arbitrary host actions and runtime scope expansion are excluded.

Status: draft planning, human review pending (`assurance.json`: stage `draft`, human review `pending`; no obtained feature or utility acceptance). Task status as of 2026-11-26 (`tasks.md`): T001–T007 are checked for bounded engineering lots only (`evidence/technical-delivery.json`, 2026-10-07); T009–T011 are checked for bounded engineering lots only (2026-10-20 documentary reconciliation in `tasks.md`); T008 is open and SPEC-066 absorbs it as T303. Dependencies: SPEC-028 accepted contracts; implementation can use a rule backend while SPEC-030 research remains pending. Live learned use waits for SPEC-030 selection and SPEC-033 promotion.
Milestone: S1.3 — Advisory integration. See the [program](../028-system-one-core/program.md)
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

- **REQ-001 — Capability registry and scope.** Declare consumer, domain, evidence, fallback and authorization boundary for every proposed use.
  - **SC-001:** Given a request for an unsupported operation/tool/effect domain, when capability discovery or routing occurs, then it reports unavailable or advisory-only rather than claiming universal enhancement.
- **REQ-002 — Immutable context and semantic gates.** Preserve operation identities, resource versions, declared/observed effects and unresolved uncertainty.
  - **SC-002:** Given a candidate recommendation and stale resources or incomplete effects, when an analyzer or scheduler consumes it, then it revalidates supported premises and never turns unknown into verified commuting.
- **REQ-003 — Verifier-work prioritization.** Support advice to rank candidates and choose analysis depth within a matched budget.
  - **SC-003:** Given eligible SPEC-018 pairs or fixed-patch SPEC-012 analysis inputs, when System 1 prioritizes review, then the unchanged verifier determines outcomes and original keep-order remains the fallback.
- **REQ-004 — Execution and recovery boundary.** Predictions cannot issue operator grants, alter manifests, broaden execution language or bypass recovery verification.
  - **SC-004:** Given a malicious recommendation or repeated decision during recovery, when runtime policy consumes advisory data, then unauthorized allocation/publication is refused and grant/plan binding is unchanged.
- **REQ-005 — Portable transport and compatibility.** Expose versioned local CLI/library and optional read-only MCP advice, preserving current host protocols.
  - **SC-005:** Given a supported bounded request or unsupported protocol revision, when advice is transported, then schemas, timeout and errors stay precise; existing execution tools and authorization semantics remain unchanged.
- **REQ-006 — End-to-end utility and diagnostics.** Measure each enabled decision stage including advice, fallback, verifier and runtime overhead.
  - **SC-006:** Given shadow advice that disagrees with observed outcomes, when the evaluation report is produced, then disagreement and unknowns remain visible; no M4 closure or scientific assurance is inferred.

## Scientific boundaries and compatibility

Hypothesis H1: Prioritizing analysis work and selecting appropriate decision paths may save time without weakening verification; this is distinct from M4 parallel execution speedup.
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

## Current documentary reconciliation — 2026-10-20

[Corpus status](corpus-status.md) links the complete S1.x evidence history, obtained bounded results, proposed implementation tasks and remaining gates. Historical planning wording below/above is not a denial of later source research or an acceptance of its implementation. The master assurance remains historical/draft; no approval or activation is inferred.

## Non-functional requirements

These limits come from the proposed [integration contract](contracts/integration.md); no REQ defines a threshold of its own. They bind the transport and cost scenarios named, and the contract stays a proposal until reviewed.

- Ingress deadline: one monotonic ceiling of 5,000 ms per stage request, tightened to the request's `deadlineMs` and never reset on delegation (REQ-005).
- Input size: at most 1,048,576 raw and canonical bytes for the combined input, container depth 16, 1 to 64 operations or candidates per request; no truncation or partial operation set (REQ-005).
- Budget fields: `maxInputBytes` 1..1,048,576, `maxCandidates` 1..64 and `deadlineMs` 1..5,000, all integers excluding booleans (REQ-005).
- Resource profile: the pure stage library has no retries, background queue or caches; the transport has a bounded queue of one active and eight waiting calls (overflow returns `defer/overloaded`) and opens no network listener, source file, runtime store or extra process (REQ-004, REQ-005).
- Cost: queue, load, render, inference, fallback and verifier cost are measured per decision stage; advice cost is never omitted from the comparison (REQ-006).

Latency, memory and cost thresholds for promotion and fallback are not defined in this spec (OQ-6).

## Security and privacy

No security or privacy requirement is added by this refinement. The statements below are non-normative scope statements taken from [plan.md](plan.md) and [contracts/integration.md](contracts/integration.md); each is covered by an existing REQ only where its text says so.

- Advice is heuristic and `executionAuthorization` stays false. Recommendations cannot issue operator grants, alter manifests or bypass recovery verification (REQ-004).
- The design copies no reference weights or data, uses no `trust_remote_code`, adds no automatic network dependency and infers no hidden effect authority.
- The pure stage library calls no filesystem, network, subprocess, provider, model SDK, verifier, scheduler, runtime, grant store or recovery tool. The stdio transport opens no network listener, source file, runtime store or extra process (REQ-005).
- Registry discovery imports no dynamic package and neither installs nor launches anything (REQ-001).
- Private prompt text is omitted from traces by default; access and retention are explicit (REQ-006; [data-model.md](data-model.md)).
- Digest consistency detects change against trusted pins; it is not source authentication, and unauthenticated external packets are not an execution input (REQ-002).

## Terminology

Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md). Terms this spec uses:

- Capability: one separately registered advisory function; the registry declares its consumer, domain, evidence, fallback and authorization boundary (REQ-001).
- Advisory packet: the immutable result of advice; it carries no grant, certificate, verified or calibrated-probability field (REQ-004).
- Abstention and fallback: the capability reports unavailable or advisory-only, or the original keep-order applies (REQ-001, REQ-003).
- DecisionContext, DecisionQuestion, DecisionAnswer, DecisionTrace, ModelManifest, CalibrationManifest, PolicyManifest: the records in [data-model.md](data-model.md).

Values named in this spec:

- Logical primitive names: `boolean`, `choice`, `score` ([contracts/interface.md](contracts/interface.md)).
- Assurance `stage`: `draft` or `validated`; `human_review`: `pending`, `changes-requested` or `approved` ([SPEC_KIT.md](../../docs/development/SPEC_KIT.md)).
- Packet statuses and stage names are enumerated in [contracts/integration.md](contracts/integration.md); this spec adds none.

## Risks and assumptions

- Risk: advice is read as proof of effects, commutation or safety; the unchanged verifier decides outcomes and unknown is never turned into verified commuting (REQ-002, REQ-003).
- Risk: a stale or mismatched context or pin is accepted; digests are recomputed and a mismatch refuses advice (REQ-002).
- Risk: a forged or high-confidence recommendation escalates execution; runtime policy refuses unauthorized allocation or publication (REQ-004, T005).
- Risk: transport changes break host protocols or existing execution tools (REQ-005, T006).
- Risk: synthetic conformance or disagreeing shadow advice is counted as utility; negative and inconclusive results stay visible and no M4 closure is inferred (REQ-006, T008).
- Assumption: local context is trusted and the existing deterministic verifiers are unchanged; no workload corpus, training budget or device coverage is assumed (`assurance.json` assumptions; OQ-1 to OQ-3).
- Assumption: SPEC-028 accepted contracts are available; a rule backend suffices while SPEC-030 research is pending, and live learned use waits for SPEC-030 selection and SPEC-033 promotion (REQ-001; T001, T008).
- Assumption: SPEC-066 absorbs the open T008 as T303 (tasks.md note; T008).

## Exit criteria

Verification is complete when all of these hold:

- Each scenario SC-001 to SC-006 has named executable tests or an obtained research report in place of its prospective reference, with `evidence/sc-00x.json` binding candidate, input, command and environment hashes ([validation-plan.md](validation-plan.md); REQ-001 to REQ-006).
- Each task T001–T008 has its planned evidence report under `evidence/` (the planned-report set is T001–T008; evidence for T009–T011 is the 2026-10-20 addenda cited in `tasks.md`), and the final candidate passes the PR-profile change validation named in tasks.md.
- Integration parity and shadow utility results are captured, with disagreement and unknowns visible (T008; REQ-006).
- A human contract/protocol review is recorded (`human_review`; checklist CHK-008).
- A per-capability promotion or no-go decision is recorded (CHK-013; SPEC-033/T008).

Tests, procedures and feature evidence do not substitute for human review, scientific interpretation, source rights or promotion (tasks.md).

## Open questions

- OQ-1: What consented sources and eligible yield exist for fitting? Owner: owner. The owner decided on 2026-11-01 that S1.5b labels come from real runs and git-history replay, in registered plugin workspaces only; other repositories need express approval each time ([owner-review-20261101.md](../066-system-one-shadow/owner-review-20261101.md) R9–R10). Other sources are undecided (SPEC-029/T001; CHK-009).
- OQ-2: Which deployment hardware and device envelope apply? Owner: owner (CHK-011; [evaluation-protocol.md](../029-system-one-evaluation/evaluation-protocol.md)).
- OQ-3: Which paid-call and training budgets apply? Owner: owner.
- OQ-4: What rights apply to the base artifact the owner builds? Owner: owner. Decided 2026-11-01: native model only, own architecture, training and weights, with no third-party decision models or pretrained encoders, and ADR 0034 accepted as amended ([owner-review-20261101.md](../066-system-one-shadow/owner-review-20261101.md) R7–R8); rights to the owner's own artifact remain open.
- OQ-5: What is the per-capability promotion go/no-go? Owner: owner (CHK-013; SPEC-033/T008).
- OQ-6: What latency, memory and cost thresholds apply to promotion and fallback? Owner: owner; the contract limits above are transport bounds, not promotion thresholds (Non-functional requirements; REQ-006).
- OQ-7: When is remote delivery authorized? Owner: owner; tracked separately from feature acceptance.
