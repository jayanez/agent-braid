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

Before Gate 1, the owner turns on review transcripts for the lab profile (T011;
nothing is stored without it) and raises its rollout cap to the Gate 1 count.
`init` rewrites every setting from its flags, so the flags below repeat the lab
profile's other values; only consent and `maxRollouts` (30 to 300) change. Check
the preview, then apply it with the printed digest:

```sh
agent-braid lightning init --home ~/.local/state/agent-braid/lightning-lab --non-interactive --hosts claude-code --algorithm baseline --repetitions 3 --max-rollouts 300 --trace-consent redacted
agent-braid lightning init --home ~/.local/state/agent-braid/lightning-lab --non-interactive --hosts claude-code --algorithm baseline --repetitions 3 --max-rollouts 300 --trace-consent redacted --apply --preview-digest <digest>
agent-braid lightning run --home ~/.local/state/agent-braid/lightning-lab --dry-run --prompt-set v2-test   # 300 planned, 300 within budget
```

Records are redacted on ingest, kept for the profile's retention (30 days) and
removed with `agent-braid lightning purge`. Undo: the same `init` with
`--trace-consent none` stops new records.

Real runs: see T006 and T009 in [tasks.md](tasks.md). Each needs the owner's
yes on the stated rollout count; the exact command is recorded there at T005.
