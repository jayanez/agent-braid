# SPEC-029: Prospective corpus and unbiased decision evaluation

## Purpose and scope

Research protocol and tooling for permissioned, representative decision data and paired comparisons. Synthetic conformance cases are never counted as real workload utility.

Status: draft planning, human review pending (`assurance.json`: stage `draft`, `human_review` pending). T001–T009 are open; T010–T027 are done as bounded documentary or engineering lots only ([tasks.md](tasks.md)). Dependencies: SPEC-028 contracts; SPEC-019 source feasibility is reusable only inside its original eligible population.
Milestone: S1.1 — Decision evaluation. See the [program](../028-system-one-core/program.md)
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

- **REQ-001 — Source rights and feasibility.** Register source ownership, consent, privacy, immutable sampling windows, eligibility and yield before fitting.
  - **SC-001:** Given a source with unknown rights or zero eligible pairs, when the pre-fit gate runs, then training remains blocked and exclusions, missing sources and feasibility outcome are reported.
- **REQ-002 — Independent labels and grouping.** Freeze rubric, label construct and independent adjudication before method scores; group correlated repositories, sessions and workflow families.
  - **SC-002:** Given related traces and unresolved reviewer labels, when partitions and labels are sealed, then no group crosses train/calibration/threshold/test splits and every admitted holdout item has an annotation attempt.
- **REQ-003 — Fair baselines and common budgets.** Compare rule/keep-order, majority, linear SPEC-019 where eligible, generative System 2, native decoder and native encoder on the same admitted items.
  - **SC-003:** Given candidate methods with different latency or coverage, when paired evaluation executes, then budget-matched results include all refusals, absent labels and end-to-end fallback cost; invalid methods are marked ineligible.
- **REQ-004 — Calibration and selective risk.** Estimate top-label calibration, Brier, NLL, ordinal MAE and risk-coverage per declared group; freeze thresholds outside test.
  - **SC-004:** Given small strata, absent classes and calibration leakage, when metrics are computed, then unsupported estimates are descriptive or unavailable and thresholds are never selected on test results.
- **REQ-005 — Counterexamples and contamination.** Include negation, instruction flip, label permutation, unseen options, multilingual/code-mix, overflow and prompt-injection slices.
  - **SC-005:** Given train/test near duplicates or reversed instructions, when the contamination and sensitivity audit runs, then leakage blocks claims; failures remain in reports rather than being removed to improve scores.
- **REQ-006 — Total cost and reproducibility.** Record input identities, seeds, hardware, cold/warm state, memory, deadlines and all decision-chain costs.
  - **SC-006:** Given a completed or infeasible experiment, when the report is generated, then paired uncertainty, subgroup counts, missingness and negative outcomes are reproducible without a universal speedup claim.

## Scientific boundaries and compatibility

Hypothesis H1: At matched risk and verifier budgets a native System 1 can reduce total decision cost in at least one declared workload; a null or negative result completes the protocol.
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

SPEC-029 defines no latency, memory or cost threshold (see [Open questions](#open-questions), OQ-4). The constraints below are stated in the sources; the figures from [evaluation-protocol.md](evaluation-protocol.md) are draft targets, not requirements, and are frozen at pre-fit review (T005, T008):

- Reproducibility: input identities, seeds, hardware, cold/warm state, memory, deadlines and every decision-chain cost are recorded (REQ-006).
- Fixed splits: the planned partition is train 60%, calibration 15%, threshold selection 10% and untouched test 15%, with a stable seed and hash manifest; group isolation takes precedence over the percentages (REQ-002; evaluation-protocol.md).
- Draft feasibility floors: 200 calibration items per eligible type/cardinality group and 100 labeled accepted test items per capability stratum; they are not a power analysis (REQ-004; evaluation-protocol.md).
- Draft promotion target: accepted error at most 5%, with a one-sided 95% precision lower bound of at least 0.95 (REQ-004; evaluation-protocol.md).
- Draft utility hypothesis: at least 10% lower median total cost than the best eligible non-neural baseline at matched risk and coverage; paired cluster bootstrap with 10,000 resamples and a fixed seed (REQ-003, REQ-006; evaluation-protocol.md).
- Runtime: Python 3.12+, standard library for the core, the optional ML package isolated from core import paths (plan.md; no REQ covers it).

## Security and privacy

- Source ownership, consent and privacy are registered before fitting, and unknown rights keep training blocked: see REQ-001.
- Private text is omitted from decision traces by default; access and retention are explicit ([data-model.md](data-model.md)). The pre-fit gate in REQ-001 covers retention of source content only for registered sources.
- No security or privacy obligation beyond REQ-001 is normative. The plan and protocol also state: no `trust_remote_code`, no automatic network dependency, no copied reference weights or data, no hidden effect-authority inference, no paid teacher or System 2 runs until a budget is explicit, and SPEC-019 source windows and private seals stay private. Per the owner decision in [owner-decisions-20261126.md](evidence/owner-decisions-20261126.md), these are scope statements, not requirements.

## Terminology

Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md). Terms this spec uses:

- Decision family: one separately evaluated kind of decision: exchange assessed-usefulness proxy, effect-review prioritization, analyzer selection, model/tool recommendation or response adequacy ([research.md](research.md)).
- Source register: the record of source ownership, consent, privacy, sampling window, eligibility and yield (REQ-001).
- Group: a set of correlated repositories, sessions or workflow families kept in one partition (REQ-002).
- Partition: one of the four disjoint group splits: train, calibration, threshold selection, untouched test (REQ-002).
- Blind holdout: admitted test items labeled before method rankings are seen (REQ-002).
- Paired evaluation: comparison of all candidate methods on the same admitted items at matched budgets (REQ-003).
- Selective risk: error among accepted decisions at a declared coverage (REQ-004).
- Abstention and fallback: the method defers to the deterministic or no-advisor path; both count in cost and coverage (REQ-003, REQ-006).
- Conformance case: a synthetic engineering case; never counted as real workload utility (REQ-005; Purpose and scope).
- Infeasibility report: the candidate-bound report that closes the investigation when T008 records NO-GO (T009).
- DecisionContext, DecisionQuestion, DecisionAnswer, ModelManifest, CalibrationManifest, PolicyManifest, DecisionTrace: the records in [data-model.md](data-model.md).

Values named in this spec:

- Candidate methods (REQ-003): rule/keep-order, majority, linear SPEC-019 where eligible, generative System 2, native decoder, native encoder.
- Logical primitive names: `boolean`, `choice`, `score` ([contracts/interface.md](contracts/interface.md)).
- Assurance `stage`: `draft` or `validated`; `human_review`: `pending`, `changes-requested` or `approved` ([SPEC_KIT.md](../../docs/development/SPEC_KIT.md)).

## Risks and assumptions

- Risk: a source with unknown rights or zero eligible pairs is fitted anyway; the pre-fit gate keeps training blocked (REQ-001, T001, T008).
- Risk: correlated sessions leak across splits or reviewers see method rankings first (REQ-002, T002, T003).
- Risk: methods with different latency or coverage are compared unfairly; refusals, absent labels and fallback cost are included (REQ-003, T007).
- Risk: thresholds are selected on test results, or sparse strata give unsupported estimates (REQ-004, T006).
- Risk: near duplicates or reversed instructions inflate scores; failures stay in reports (REQ-005, T003, T004).
- Risk: synthetic conformance cases are read as real utility or as source yield (REQ-006; research.md).
- Assumption: local context is trusted and the existing deterministic verifiers are unchanged; no workload corpus, training budget or device coverage is assumed (`assurance.json` assumptions; OQ-1 to OQ-3).
- Assumption: SPEC-066 absorbs the open T001–T009 for the owned population, with its amended label rubric replacing two-blind-reviewer labelling (tasks.md note of 2026-11-01; [SPEC-066](../066-system-one-shadow/spec.md)).

## Exit criteria

Verification is complete when all of these hold:

- Each scenario SC-001 to SC-006 has named executable tests or an obtained research report in place of its prospective reference, with `evidence/sc-00x.json` binding candidate, input, command and environment hashes (validation-plan.md; REQ-001 to REQ-006).
- Each task T001–T009 has its planned evidence report under `evidence/`, and the final candidate verification `scripts/validate_change.py --base develop --profile pr` passes (tasks.md).
- T009 records either the registered comparison or the candidate-bound infeasibility report; a null, negative or infeasible result completes the protocol (T009; Scientific boundaries).
- A human contract/protocol review is recorded (`human_review`; checklist CHK-008).

Tests, procedures and feature evidence do not substitute for human review, scientific interpretation, source rights or promotion (tasks.md).

## Open questions

- OQ-1: What consented sources and eligible yield exist for fitting? Owner: owner. The owner decided on 2026-11-01 that S1.5b labels come from real runs and git-history replay, in registered plugin workspaces only ([owner-review-20261101.md](../066-system-one-shadow/owner-review-20261101.md) R9–R10); other sources are undecided (T001, T008; CHK-009).
- OQ-2: Which deployment hardware and device envelope apply? Owner: owner (T005; CHK-011; evaluation-protocol.md).
- OQ-3: Which paid-call and training budgets apply? Owner: owner; paid teacher and System 2 runs stay blocked until it is explicit (T008, T009; evaluation-protocol.md).
- OQ-4: What latency, memory and cost thresholds apply? Owner: owner; none is defined in SPEC-029, and the draft targets under Non-functional requirements freeze at pre-fit review (T005, T008).
- OQ-5: Which final base-model rights apply to the artifact the owner builds? Owner: owner (Clarifications and unresolved decisions; SPEC-030).
- OQ-6: When is remote delivery authorized? Owner: owner; tracked separately from feature acceptance.
