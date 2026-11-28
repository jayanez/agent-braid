# Quickstart: SPEC-091

Nothing below exists yet; these are the planned commands. Structural and simulation checks spend no quota:

```sh
python3.13 -m scripts.validate_spec_kit
python3.13 -m pytest tests/test_spec091_items.py tests/test_spec091_lab.py tests/test_spec091_levers.py tests/test_lightning_resources.py
python3.13 -m scripts.spec090_simulate --gate-b          # simulation record (T007)
python3.13 -m scripts.spec091_freeze --check             # after T011 or T014: hashes match develop
```

Real runs (noise pilot, development factorial, 2×2 factorial, held-out) each need their own freeze and the
owner's yes; then `agent_braid.lightning_gate_b` on the run directory. Any result is a valid outcome.
