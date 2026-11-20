# SPEC-078 quickstart

Deterministic checks (no rollouts, no credentials):

```sh
.venv-speckit/bin/python -m unittest tests.test_spec069_guidance   # T001 rule pin
.venv-speckit/bin/python -m scripts.spec078_build_set --check       # set is reproducible (T002)
.venv-speckit/bin/python -m scripts.spec078_gate0                   # Gate 0 report; exit 0 only if every check passes (T004)
.venv-speckit/bin/python -m scripts.validate_spec_kit
```

Expected: every test passes; Gate 0 prints zero failing cases, zero null baselines
meeting OD-1, and the per-split class coverage table.

Real runs (owner yes on the rollout count first; subscription route; see
[LIGHTNING.md](../../docs/tooling/LIGHTNING.md)):

```sh
agent-braid lightning run --prompt-set v2-test --arm final   # Gate 1, 300 rollouts (T006)
```

The exact held-out command and its flags are fixed at T005 and recorded here
before Gate 1.
