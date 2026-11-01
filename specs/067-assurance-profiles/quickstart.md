# SPEC-067: Quickstart

Specification stage: only the structural checks apply now.

```sh
python3 -m scripts.validate_spec_kit
python3 -m scripts.validate_change --base develop --profile quick
```

Expected: both pass in a clone without unreachable objects. In a shared-object
worktree the first fails with `public repository contains unreachable objects`;
use a fresh clone as described in `docs/development/SPEC_KIT.md`.

After implementation (planned, not runnable yet):

```sh
.venv-speckit/bin/python -m unittest discover -s tests -p "test_harness_assurance*.py" -v
```

Expected: deterministic positive and negative tests pass. Adopting a profile,
standing authorizations and the H1 evaluation each need their own operator
record and are not exercised by tests.
