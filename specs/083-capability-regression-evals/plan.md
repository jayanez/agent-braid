# Implementation plan: SPEC-083 capability versus regression evaluation protocol

## Approach

- **Amend by reference.** SPEC-049's frozen protocol stays as written. This spec
  adds the regression class and its rules. A later, founder-approved task adds one
  dated cross-reference line to the SPEC-049 protocol; no frozen value changes.
- **Contract first.** The later code phase starts with a written contract,
  `specs/083-capability-regression-evals/contracts/regression-protocol.md`: the
  registration record (proposed name `braid-harness-regression-registration/v0.1`),
  the report record (proposed `braid-harness-regression-report/v0.1`), the
  estimators and the decision table. Names are proposals until reviewed.
- **Worked fixtures before code.** Hand-computed fixtures fix the expected Δ,
  bounds, pass@k and pass^k values, plus negative controls (trial-level errors,
  missing outcomes, infrastructure over threshold).
- **One pure module.** A new offline module computes everything from sealed
  records and per-trial outcome records. It reads no clock, host, model or network
  and returns `executionAuthorization: false`, like `agent_braid/harness_evaluation.py`.
- **Exact arithmetic.** Rates and estimators use `fractions.Fraction`; the t
  quantile and bootstrap are the only floating-point steps, rounded outward and
  recorded with their method.

## Constitutional check

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence; negative results are valid | `inconclusive` is a first-class verdict that blocks promotion; H1 and H2 may fail |
| 9 | Experiments generate counterexamples | Negative-control fixtures for each guard; a counterexample is recorded |
| 13 | Evidence method, domain and assumptions explicit | Each report names class, estimand, method, cluster level, corpus, split and profile |
| 14 | Evidence, not verdicts | Per-task outcomes, infrastructure table, three missing-outcome bounds and hashes |
| 19 | Real, measurable problem | Gate runs on the SPEC-082 real-failure corpus |
| 20 | Analysis separate from execution | The module only reads records; no launch, grant or promotion |
| 21 | Reproducible benchmarks | Sealed records, recorded seeds and exact arithmetic allow replay |
| 24 | Semantics before production | Contract and fixtures precede code |

No MUST conflict found. No SHOULD deviation recorded.

## Affected files for the later code phase (named, not edited here)

- New: `agent_braid/harness_regression.py` (registration validation, pairing,
  estimators, decision); `tests/test_harness_regression.py`;
  `specs/083-capability-regression-evals/contracts/regression-protocol.md`;
  `specs/083-capability-regression-evals/fixtures/`.
- Changed, read-only surface: `agent_braid/harness_cli.py` (`evaluation-summary`
  recognizes the regression report format; no new write command). Coordinate with
  SPEC-080, whose skill lists `evaluation-summary`.
- Changed docs: `docs/tooling/HARNESSING.md` (describe the two classes).
- Cross-reference only, founder decision required:
  `specs/049-harness-evaluation-learning/evaluation-protocol.md`.
- Unchanged: `agent_braid/harness_evaluation.py`, `agent_braid/harness_promotion.py`,
  every SPEC-049 frozen record.

## Phases

1. **P0 review.** Owner review (T001) and Codex review (T002).
2. **P1 contract.** Contract and worked fixtures (T003, T004).
3. **P2 implementation.** Module, tests with mutation controls, read-only CLI view,
   docs and the SPEC-049 cross-reference (T005–T008).
4. **P3 first registration.** Owner seals the first record on the SPEC-082 corpus
   (T009). The first verdict (T010) waits for trials from SPEC-084 or the existing
   laboratory. Any verdict, including `inconclusive`, closes T010.

## Validation profile

Per [VALIDATION_PROFILES.md](../../docs/development/VALIDATION_PROFILES.md):

- This documentation PR: `python3 -m scripts.validate_spec_kit`; CI `validate` on
  the PR head is the `pr` evidence. Assurance records are sensitive paths, so a
  requested `quick` profile escalates.
- Code phase: targeted `tests/test_harness_regression.py` and
  `tests/test_harness_evaluation.py` while iterating, then `quick`; CI `pr` on the
  head. The statistics module counts as a scientific algorithm (sensitive).

## Rollback

Documentation: revert the PR. Code phase: the module is additive and offline;
removing it leaves SPEC-049 evaluation and promotion unchanged. No stored state
is migrated. A sealed registration stays on record even if the module is removed.
