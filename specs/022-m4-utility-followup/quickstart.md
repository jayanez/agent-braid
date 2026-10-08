# Verification and evaluation preparation

Protocol T001 was approved against public `3777e578`. The owner separately approved the 180-minute successor for implementation and preparation; its exact stable candidate and manifest were subsequently reviewed and authorized for registered capture. The registered synthetic capture completed on candidate `b85f7e5`; see the [derived result](evidence/registered-capture-summary-b85f7e5.json). The owner approved a bounded T006 interpretation; see the [decision packet](decision-packet.md) and [decision record](utility-decision-20261008.json). This interpretation supports no useful-speedup claim or parallel performance default for the measured families; it is not a general claim about parallelism. The founder accepted bounded M4 alpha engineering and evaluation as complete with negative utility on 2026-10-09; the historical G4 NO-GO remains. See the [SPEC-038 decision](../038-m4-real-workload-closure/whole-m4-founder-decision-20261009.json). Tracking reconciliation remains a separate pending administrative step.

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

Preparation writes exact immutable plan bytes and provenance. It creates no grants and executes no treatment. CLI `--execute` and `--registered` are refused. The library runner requires a separate approval bound to the exact manifest SHA-256 and stable candidate. Each admitted block has two warm-up and twenty measured pairs, with parity-alternated order and unique private destinations. The default `--plan-version v1` retains the original 45-minute dispatch horizon. The distinct successor is prepared explicitly with `--plan-version v2`, using exactly 180 minutes. All fixture copies are reconstructed separately before the selected plan's dispatch clock starts. A v2 registration review also requires `reviewedPlanVersion: "spec022-paired-evaluation-plan-v2"`; neither the old protocol review nor a v1 manifest review authorizes v2 dispatch. Failures and unexecuted treatments are retained; no favorable complete-case result is produced for an incomplete block.

For the approved preparation scope, use the same preparation command with `--plan-version v2`. Changed preparation/trial inputs require fresh matching diagnostic records before it can succeed; the existing v1 manifests and diagnostic hashes are historical, not silently refreshed. See `successor-protocol-180m.md` for compatibility and the later review boundary.

## SC-003 — Existing execution boundaries

No runtime optimization was selected from the exploratory diagnosis. Current replay, policy, exact operator grants, consumers and final verification are retained. Tests exercise source drift, malformed/reused descriptors, fresh scopes, fixed caps, manifest/order contradictions, failure accounting and dispatch-budget exhaustion. Existing runtime, policy and scheduler suites remain repository gates. Fresh-process recovery and duplicate-delivery controls belong to the separately reviewed registered reproduction.

## SC-004 — Decision boundary

A future decision packet must include every block and negative/inconclusive outcome. Measurements are descriptive synthetic observations. SPEC-021 NO-GO, actual-workload acceptance and milestone closure remain unchanged until a separate recorded decision.

## Repository gates

Run `python3 scripts/validate_change.py --base develop --profile quick` during implementation and `--profile pr` once stable. Their passing results are not measurement or human approval. See the evidence receipts for executed checks rather than inferring execution from these commands.
