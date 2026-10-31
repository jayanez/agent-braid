# SPEC-065: Quickstart

Specification stage: only the structural checks below apply now.

```sh
python3 -m scripts.validate_spec_kit
python3 -m scripts.validate_change --base develop --profile quick
```

Expected: both pass in a clone without unreachable objects. In a shared-object
worktree the first fails with `public repository contains unreachable objects`;
use a fresh clone as described in `docs/development/SPEC_KIT.md`.

After implementation (planned, not runnable yet):

```sh
.venv-speckit/bin/python -m unittest tests.test_harness_manifest tests.test_harness_quota \
  tests.test_harness_transport_claude tests.test_harness_containment_macos \
  tests.test_harness_qualification_probes -v
```

Expected: all deterministic refusal tests pass; live probe tests are skipped
unless the probe run is explicitly enabled for a qualification attempt.

Qualification attempt (T009, only after founder decisions and ADR acceptance):
run the probe runner for the decided configuration, inspect
`evidence/qualification/<attempt>/summary.json`, and hand the bundle to the
issuer. Expected: either every effect `enforced` and HOST-01 complete, or a
retained not-qualified bundle. Neither outcome is a failure of the procedure.
