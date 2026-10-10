# SPEC-019 review preparation quickstart

Use an isolated Python 3.12+ environment with the pinned development and
Spec Kit requirements. Current commands exercise preparatory software only;
they do not collect data, fit weights, calibrate or evaluate real workloads.

Activate the environment so tests that launch `python3` also use Python 3.12+:

```sh
. .venv-speckit/bin/activate
```

```sh
.venv-speckit/bin/python -m unittest -v tests.test_m35_review_packet \
  tests.test_predictor_readiness tests.test_native_predictor
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
No training/evaluation command is available in this preparation increment;
T001/T007 and the cohort/label gates still precede those implementations.

Preserve the existing skipped contract tests as pending until actual acceptance
evidence exists. Technical profiles do not establish clean-room reproduction,
scientific validity, human approval or milestone closure.
