# SPEC-032: Planning verification and implementation handoff

From repository root, with pinned isolated tooling installed:

```sh
SPECIFY_FEATURE_DIRECTORY="$PWD/specs/032-system-one-product" python3 .specify/scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
python3 scripts/validate_spec_kit.py
python3 scripts/sync_github_tracking.py source
(umask 0022 && .venv-speckit/bin/python scripts/validate_change.py --base develop --profile pr)
```

Expected now: planning structure is valid, acceptance scenarios remain draft and
obtained evidence empty. All implementation tasks remain unchecked. Procedures in
validation-plan.md are not runnable feature tests. After implementation, run the
task-specific named tests and common workload protocol, preserve raw results, bind
candidate/input hashes and replace prospective references before validating scenarios.
Review human/model/data/hardware and publication gates independently. Freeze only
after a clean candidate commit; do not claim founder approval from hash checks.

POSIX note: the existing runtime permission-refusal fixture creates an explicit
0755 directory and expects it to remain 0755. A restrictive inherited umask 0077
turns that fixture into an accepted 0700 store. Use the scoped standard umask above
for the validator; runtime private stores still explicitly require 0700.

## Planning dependency controls

Review the selected/deferred ledger from T001 against the branch rules in tasks.md:

- Schema only: T004 and its core prerequisites can proceed while SPEC-030 is pending;
  T008 requires T004, without export, routing, catalogue, lifecycle or hook tasks.
- Core hooks only: T007 needs the core and selected wheel contents, without a model,
  catalogue or batching implementation; T008 requires only that selected branch.
- Reference model lifecycle: T006 requires the exact selected model, while deferred
  quantization or routing cannot block it unless the worker actually uses them.
- All deferred: T008 may record reasons and reconsideration conditions after T001;
  T002 through T007 remain pending, with no validated scenarios or feature acceptance.

These are planning consistency checks, not executed feature tests. For every subset,
retain model/domain/calibration/workload gates where applicable and the separate
SPEC-033 promotion decision. Re-run each quickstart's selector from a clean checkout
and with unrelated feature metadata; FEATURE_DIR must name the requested spec.
