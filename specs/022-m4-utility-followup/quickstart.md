# Verification and evaluation preparation

Protocol T001 was approved against public `3777e578`. Whole-feature human review, stable harness/registered manifest review, actual-workload utility acceptance and G4/M4 closure remain pending. The implementation does not turn protocol approval into registered-execution approval.

Run commands in an isolated Python 3.12+ environment with its `bin` directory first in `PATH`, including child interpreters.

## SC-001 — Cost accounting

`tests/test_utility_accounting.py` and `tests/test_m4_utility.py` exercise injectable clocks, disjoint required phases, explicit residuals, omitted counters, grant/verification/cleanup and source integrity. The real boundary test runs an owned pinned two-operation fixture through both complete serial and parallel paths. Optional unavailable observations have explicit reasons; accepted budget-output bytes are distinct from unknown total captured bytes.

Recurring registered-wrapper candidate, manifest and source checks occur in input and closing residual before the outer tick closes. The outer interval includes input loading, replay, preparation, grants, execution, independent verification, operational serialization and cleanup. Closing envelope construction and shared output are separately observed. Exact operational encoded bytes are retained alongside the later authoritative closing status.

## SC-002 — Immutable paired evaluation

Exploratory diagnostics use a clean candidate and fresh external output:

```sh
python3 scripts/measure_m4_utility.py --diagnostic-block independent-2-1024 --output /absolute/fresh/diagnostic.json
```

This runs one serial-first diagnostic pair; it is not registered evaluation. The manifest inventory retains all nine blocks, including five pinned cap exclusions. Diagnostic source hashes must match the stable candidate before preparing the paired plan:

```sh
python3 scripts/prepare_m4_utility_trials.py --diagnostics /absolute/diagnostics --destination-root /absolute/fresh/private-trials --output /absolute/fresh/registered-manifest.json
```

Preparation writes exact immutable plan bytes and provenance. It creates no grants and executes no treatment. CLI `--execute` and `--registered` are refused. The library runner requires a separate approval bound to the exact manifest SHA-256 and stable candidate. Each admitted block has two warm-up and twenty measured pairs, with parity-alternated order and unique private destinations. All fixture copies are reconstructed separately before the runner's 45-minute dispatch clock starts. Failures and unexecuted treatments are retained; no favorable complete-case result is produced for an incomplete block.

## SC-003 — Existing execution boundaries

No runtime optimization was selected from the exploratory diagnosis. Current replay, policy, exact operator grants, consumers and final verification are retained. Tests exercise source drift, malformed/reused descriptors, fresh scopes, fixed caps, manifest/order contradictions, failure accounting and dispatch-budget exhaustion. Existing runtime, policy and scheduler suites remain repository gates. Fresh-process recovery and duplicate-delivery controls belong to the separately reviewed registered reproduction.

## SC-004 — Decision boundary

A future decision packet must include every block and negative/inconclusive outcome. Measurements are descriptive synthetic observations. SPEC-021 NO-GO, actual-workload acceptance and milestone closure remain unchanged until a separate recorded decision.

## Repository gates

Run `python3 scripts/validate_change.py --base develop --profile quick` during implementation and `--profile pr` once stable. Their passing results are not measurement or human approval. See the evidence receipts for executed checks rather than inferring execution from these commands.
