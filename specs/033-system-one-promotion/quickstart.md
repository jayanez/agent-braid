# SPEC-033: Planning verification and implementation handoff

From repository root, with pinned isolated tooling installed:

```sh
SPECIFY_FEATURE=033-system-one-promotion python3 .specify/scripts/python/check_prerequisites.py --json --require-tasks --include-tasks
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
