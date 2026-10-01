# SPEC-019 preliminary implementation plan

## Technical context and scope

M3.5 is separate from M3 closure. The proposal is a small offline trained
linear model with versioned local features and local standard-library
inference. It cannot replace or weaken SPEC-018 verification.

## Constitution check before research

Articles 6 and 13 prohibit treating score as guarantee or scheduling
permission; Article 9 requires counterexamples; Articles 14 and 19 require
provenance and measured utility. No MUST conflict is accepted.

## Research, assumptions and alternatives

Compare against the M3 rule advisor. External Laya/Jev services and larger
models add dependencies without a demonstrated benefit and are outside scope.
Split by repository plus editing-workflow family, keep related sessions and
near duplicates together, and report per-family prevalence and exclusions.

## Design and compatibility

First register a consented source and contiguous sampling windows, audit the
exact M3 eligibility and freeze the two-dimension human rubric. Attempt
policy-blind labels for every admitted pair, seal holdout labels, and freeze
family partitions, feature schema, baseline priority, abstention, sigmoid
calibration and total-analysis-time boundary. Then train only offline and
freeze the model artifact.
Inference emits a proposal with version and no certificate. Existing verifier
must independently accept any selected candidate.

Before real-source onboarding, the local synthetic instrument records a base
event and two operation events per session in an exclusive, hashed JSONL log.
Its audit calls the unchanged M3 request validator and reports complete
session/pair admission and exclusion counts. This verifies only the capture
adapter and accounting. A later phase inspects existing event feeds after
permission and privacy decisions; Git patch histories alone are ineligible.

The [feasibility audit](feasibility-audit.md) and
[source register](source-audit.md) are gates before that preregistration. The
present valid corpus has no divergent verifier labels, while the M3 proposal
is an exact structural rule. The founder approved source discovery and later
bounded ADR 0018 preparation;
the proposed [workload protocol](workload-protocol.md) and
[annotation rubric](annotation-rubric.md) still require review, actual data
and privacy clearance. This plan does not authorize fitting a model to a
degenerate label or counting syntactically invalid inputs as semantic
counterexamples.

For the owned-flow route, use the T008 local sidecar and two disposable private
lab repositories documented in [instrumentation](instrumentation.md). Register
one immutable 14-day UTC window per workflow only after rights/privacy review
and a successful audit-repository runner. Pin exact engineering document blobs
for `lab/main` and `lab/develop`; changes stop sync until reviewed. The local
journal and keyed seal secret never enter GitHub. Run the prospective audit and
compare observed yield only after all gates; two workflows do not satisfy the
five-family target.

## Validation strategy

Pair SC-001..005 with deterministic tests and held-out metrics in M3.5 work.
SC-006 binds the synthetic capture fixture, report, focused regression test
and their hashes, with zero admitted real pairs.
SC-007 binds sidecar, filtered export and remote-seal adversarial tests. A
successful software check is not an upstream-completeness or real-yield result.
Before that, record source permissions and session/pair exclusion counts,
reviewer disagreement, class coverage and policy-blind annotation coverage.
Compare against the rule baseline at matched verifier budgets and record the
specified total-analysis-time components. Report no-gain, negative and
inconclusive outcomes.

## Constitution check after design

Prediction remains heuristic and advisory, with execution authorization false.
No M3/M2 contract is changed.

## Human review and unresolved decisions

The stable M3 verifier, actual target population, source permissions, label
provenance, family split, metric thresholds, calibration feasibility, privacy
constraints, architecture and publication need separate review before M3.5
training or integration. This candidate is not an approved protocol.
