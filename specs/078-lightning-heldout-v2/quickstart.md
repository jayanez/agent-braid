# SPEC-078 quickstart

Deterministic checks (no rollouts, no credentials):

```sh
.venv-speckit/bin/python -m unittest tests.test_spec069_guidance   # T001 rule pin
.venv-speckit/bin/python -m scripts.spec078_build_set --check       # set is reproducible (T002)
.venv-speckit/bin/python -m scripts.spec078_gate0                   # Gate 0 report; exit 0 only if every check passes (T004)
.venv-speckit/bin/python -m scripts.spec078_freeze --check        # the freeze still holds
.venv-speckit/bin/python -m scripts.validate_spec_kit
```

Expected: every test passes; Gate 0 prints zero failing cases, zero null baselines
meeting OD-1, and the per-split class coverage table.

Real runs: see T006 and T009 in [tasks.md](tasks.md). Each needs the owner's
yes on the stated rollout count; the exact command is recorded there at T005.
