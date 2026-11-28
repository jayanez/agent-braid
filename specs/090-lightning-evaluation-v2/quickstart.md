# Quickstart: SPEC-090

Nothing below exists yet; these are the planned commands. Structural and simulation checks spend no quota:

```sh
python3.13 -m scripts.validate_spec_kit
python3.13 -m pytest tests/test_lightning_stats.py tests/test_lightning_selection.py tests/test_lightning_gate_a.py
python3.13 -m scripts.spec090_simulate --all              # simulation record (T004 to T007)
python3.13 -m scripts.spec090_freeze --check              # after T016: hashes match develop
```

Gate A run (about 300 rollouts plus reserve; only after the freeze, the simulation record and the owner's
yes): run the SPEC-071 held-out command on the frozen split with the plugin pinned to the frozen commit,
then `agent_braid.lightning_gate_a`. Any verdict is a valid outcome.
