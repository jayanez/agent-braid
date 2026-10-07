# SPEC-037: Planning and future implementation quickstart

## Available now

From an isolated Python 3.12+ environment on a full clean clone, inspect `spec.md`, `plan.md`, `tasks.md`, `validation-plan.md` and the shared program. No forecast CLI/runtime implementation exists in this planning change.

```sh
SPECIFY_FEATURE=037-forecast-advisory-integration SPECIFY_FEATURE_DIRECTORY=specs/037-forecast-advisory-integration .venv-speckit/bin/python .specify/scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
.venv-speckit/bin/python scripts/sync_github_tracking.py source
.venv-speckit/bin/python scripts/validate_spec_kit.py
.venv-speckit/bin/python scripts/validate_change.py --base develop --profile quick
```

Expected: structural/traceability checks; human review and acceptance evidence remain pending. Current snapshots detect authority changes; do not refresh them to hide drift. No model download, source capture or profiling experiment is run by these commands.

## After the applicable task gates

Implement the named task targets, replace prospective procedure references with actual tests/reports, and run focused `test_forecast*.py` controls. Optional ML tests run only in the approved isolated installation. Execute permissioned capture, real checkpoint conformance and frozen utility measurements only under their separate source/model/compute/operator gates.

Run `.venv-speckit/bin/python scripts/validate_change.py --base develop --profile pr` once on the stable implementation candidate. Freeze the clean integrated candidate before human acceptance review, capture exact obtained evidence and keep failed/blocked/deferred checks visible. Passing profiles do not accept utility, model promotion, founder decisions or independent validation.
