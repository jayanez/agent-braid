# Planned verification and evidence

**Status:** prospective commands and checks, not executed feature evidence. All new implementation tests and harness paths below are future targets.

## SC-001 — Cost accounting

Implement `tests/test_m4_utility.py` phase-accounting tests with an injectable monotonic clock. Verify that full-cost intervals include evidence, grants, consumer verification and cleanup; reject overlapping or missing accounting claims. Phase sums may differ only by an explicitly recorded unallocated coordinator interval.

## SC-002 — Registered paired evaluation

Implement the harness entrypoint `python3 scripts/measure_m4_utility.py --manifest <frozen-manifest.json> --output <new-output.json>`. Test immutable block order, 2 warm-up/20 measured pairs, parity-alternated treatment order, rejected fixture sizes, hash drift and invalid pair retention. Do not execute this future command until its implementation and manifest are reviewed and frozen.

## SC-003 — No weakened execution boundary

Run `python3 -m unittest tests.test_git_runtime tests.test_m4_alpha_policy tests.test_m4_alpha_scheduler tests.test_m4_utility`. Zero unsafe admissions; compare admitted final trees to the serial reference. Include cancellation, fresh-process recovery and duplicate delivery in the separately frozen reproduction.

## SC-004 — Decision packet

Check that all registered blocks and negative/inconclusive results appear in the packet; utility acceptance and milestone closure are explicit separate fields. Reject a packet that describes measurements as formal or production evidence or changes historical NO-GO without a new decision.

## Repository gates

Use `python3 scripts/validate_change.py --base develop --profile quick` during implementation and `--profile pr` once stable. These commands are not measurement or approval.
