# SPEC-029: Prospective corpus and unbiased decision evaluation

## Purpose and scope

Research protocol and tooling for permissioned, representative decision data and paired comparisons. Synthetic conformance cases are never counted as real workload utility.

Status: draft planning, human review pending. Dependencies: SPEC-028 contracts; SPEC-019 source feasibility is reusable only inside its original eligible population.
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

## Evidence and unresolved questions

Source inspection is in the analysis manifest; planned validation is in
[validation-plan.md](validation-plan.md). Feature/model/workload acceptance evidence:
none. All obtained_evidence arrays are empty and human_review is pending. Passing
planning validators establishes artifact structure, not implementation or utility.
