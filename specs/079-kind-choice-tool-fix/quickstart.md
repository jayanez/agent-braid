# Quickstart: SPEC-079

Structural checks (no quota):

```sh
python3 -m scripts.validate_spec_kit                      # expect: structural gates passed
python3 -m pytest tests/test_tooling_mcp_units_redirect.py tests/test_tooling_mcp_descriptions.py
python3 -m scripts.spec079_build_v4 --check               # expect: exit 0, zero collisions
python3 -m scripts.spec079_build_v4 --gate0 specs/079-kind-choice-tool-fix/evidence/gate0-v4-report.json
python3 -m scripts.spec079_freeze --check                 # expect: hashes match develop
```

Gate run (spends 300 rollouts; only after the freeze and the owner's yes): run the SPEC-071 held-out
command on `prompts/v4-test.json` with the plugin pinned to the frozen commit, then
`agent_braid.lightning_heldout_v2.analyse`. Expected: a report with the OD-1 verdict; any verdict is a
valid outcome.
