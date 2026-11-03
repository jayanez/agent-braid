# SPEC-067: Quickstart

Implemented at unit level: T002 to T010 are done and T011 is open; no profile is adopted and no standing
authorization is issued. The structural checks and the unit tests below apply now.

```sh
python3 -m scripts.validate_spec_kit
python3 -m scripts.validate_change --base develop --profile quick
```

Expected: both pass in a clone without unreachable objects. In a shared-object
worktree the first fails with `public repository contains unreachable objects`;
use a fresh clone as described in `docs/development/SPEC_KIT.md`.

Unit level (deterministic; nothing executes, merges or approves):

```sh
.venv-speckit/bin/python -m unittest discover -s tests -p "test_harness_assurance*.py" -v
```

Expected: all deterministic positive and negative tests pass (OK). Adopting a profile,
standing authorizations and the H1 evaluation each need their own operator
record and are not exercised by tests.
