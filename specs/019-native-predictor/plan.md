# SPEC-019 preliminary implementation plan

## Technical context and scope

M3.5 is separate from M3 closure. The proposal is a small offline trained
linear model with versioned structural features and local standard-library
inference. It cannot replace or weaken SPEC-018 verification.

## Constitution check before research

Articles 6 and 13 prohibit treating score as guarantee or scheduling
permission; Article 9 requires counterexamples; Articles 14 and 19 require
provenance and measured utility. No MUST conflict is accepted.

## Research, assumptions and alternatives

Compare against the M3 rule advisor. External Laya/Jev services and larger
models add dependencies without a demonstrated benefit and are outside scope.
Split by structural family to avoid near-duplicate leakage.

## Design and compatibility

First preregister corpus, feature schema, labels, partitioning, abstention,
calibration and costs. Then train only offline and freeze model artifact.
Inference emits a proposal with version and no certificate. Existing verifier
must independently accept any selected candidate.

## Validation strategy

Pair SC-001..005 with deterministic tests and held-out metrics in M3.5 work.
Compare against rule baseline and report no-gain or negative outcomes.

## Constitution check after design

Prediction remains heuristic and advisory, with execution authorization false.
No M3/M2 contract is changed.

## Human review and unresolved decisions

Dataset, metric thresholds, privacy constraints, architecture and publication
need separate review before M3.5 implementation.
