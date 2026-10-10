# SPEC-019 synthetic software and review quickstart

**Current status (2026-10-10):** T002/#182 synthetic trainer/inference and
T004/#184 verifier-boundary software are complete. The implementation can fit
and calibrate only caller-declared synthetic rows and evaluate synthetic
inventories. It is a library surface, not a CLI workflow, and it does not adapt
real feeds. No real pairs are admitted; no real-workload fit or result exists.
The remaining experiment is tracked in [software-completion.md](software-completion.md).

Use an isolated Python 3.12+ environment with the pinned development and
Spec Kit requirements. The commands below exercise synthetic software and
repository validation; they do not collect or evaluate real workloads.

Activate the environment so tests that launch `python3` also use Python 3.12+:

```sh
. .venv-speckit/bin/activate
```

```sh
.venv-speckit/bin/python -m unittest -v \
  tests.test_native_predictor tests.test_native_predictor_training \
  tests.test_native_predictor_evaluation tests.test_native_predictor_adapter \
  tests.test_native_predictor_contract tests.test_predictor_readiness \
  tests.test_m35_review_packet
.venv-speckit/bin/python -m scripts.check_m35_review_packet
.venv-speckit/bin/python scripts/validate_change.py --base develop --profile quick
```

The packet checker reads only the six committed inputs listed in its `FILES`
constant. Exit 0 means their preparatory shape and byte commitments are present,
not that the experiment is ready. A supplied `--expected-packet-sha256` pin must
match; missing/unsafe/malformed files or drift exit 2 with redacted diagnostics.
All source capture, training, execution and human-approval verification flags
remain false, and real admitted pairs remain zero. Symlinks/nonregular files and
unsupported safe-file primitives fail closed; current support is POSIX hosts
with directory-relative no-follow opens.

```sh
.venv-speckit/bin/python -m scripts.check_m35_review_packet \
  --expected-packet-sha256 <reviewed-packet-sha256>
.venv-speckit/bin/python scripts/validate_change.py --base develop --profile pr
```

`<reviewed-packet-sha256>` is a placeholder for the concrete printed commitment.
Hashes bind supplied bytes, not reviewers or permission. Review the source
packet, complete protocol/rubric and model interfaces before issuing any
source-specific capture decisions. Then follow the existing prospective pilot
runbook with its actual successful registrations and fixed 14-day windows.
The focused software suite includes synthetic training, calibration, inference,
adapter, evaluation and verifier-boundary controls. Its 2026-10-10 recorded run
passed 115 controls with zero skips or failures; see the
[completion evidence](../../docs/experiments/evidence/m35-software-completion-2026-10-10/README.md).
The final public-draft provenance repair separately passed exact-head and
post-merge CI (885 tests, two skips) and all four integration-matrix configurations;
see the [delivery record](../../docs/development/m35-project-alignment.md). These are
software and repository checks, not real-data or scientific evidence. Technical
profiles do not establish source permission, clean-room scientific reproduction,
human approval or milestone closure.
