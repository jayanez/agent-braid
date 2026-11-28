# SPEC-090: Tasks

**Milestone:** provisional, BL.2c (OD-10).

Stable task IDs. Completion requires obtained evidence; task completion does not imply owner acceptance
or support for H1 to H3. Parallelizable is a dependency property and does not authorize concurrent
agents. One pull request per task; the owner approves each merge. No task spends quota before T016's
freeze, the simulation record and the owner's yes.

`quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P0 — owner review

- [ ] T001 (OD-1..OD-13, ADR 0046): Owner review of this specification and ADR 0046: record the 2026-11-28 strategy approval with its date, and decide or defer each of OD-1 to OD-13 in a dated record. Files: `specs/090-lightning-evaluation-v2/evidence/t001-owner-decisions.md`. Dependencies: none. Verification: owner review; `python -m scripts.validate_spec_kit`.

## Phase P1 — statistical core and simulation (no quota)

- [ ] T002 (REQ-002, REQ-003 / SC-002, SC-004): Exact Clopper–Pearson lower and upper bounds by bisection on binomial sums (no new dependency), the all-fail count, exact sign and McNemar tests, and the slice-sizing formula of plan.md. Files: `agent_braid/lightning_stats.py`, `tests/test_lightning_stats.py`. Dependencies: none. Verification: `python -m unittest tests.test_lightning_stats` and `quick`.
- [ ] T003 (REQ-017): Simulation harness: candidate pools with known per-prompt pass probabilities drawn from a beta distribution matched to a given within-prompt correlation (range 0.41 to 0.81 from v2 to v4, replaced by the pilot value in T019), with seeded, recorded draws. Files: `scripts/spec090_simulate.py`, `tests/test_lightning_sim.py`. Dependencies: T002. Verification: `python -m unittest tests.test_lightning_sim`.
- [ ] T004 (REQ-002, REQ-017 / SC-003): SIM: gate A type I error at the 0.80 boundary and power at chosen alternatives, for each OD-1 option and the class rule. Files: `specs/090-lightning-evaluation-v2/evidence/sim-gate-a.json`. Dependencies: T003. Verification: `python -m scripts.spec090_simulate --gate-a`.
- [ ] T005 (REQ-003, REQ-017 / SC-005): SIM: coverage of the all-fail bound over a grid of θ, for each OD-2 option; report the detection rate of a deterministic defect affecting 2 to 3 % of prompts. Files: `specs/090-lightning-evaluation-v2/evidence/sim-all-fail.json`. Dependencies: T003. Verification: `python -m scripts.spec090_simulate --all-fail`.
- [ ] T006 (REQ-008, REQ-009, REQ-010, REQ-011, REQ-017, REQ-031 / SC-011..SC-015, SC-036): Paired, synchronized selection module with incumbent margin; SIM comparing synchronized halving, SySRs and paired racing, each with the OD-11 tests, against top-k on n = 5 independent means (H1). Files: `agent_braid/lightning_selection.py`, `tests/test_lightning_selection.py`, `specs/090-lightning-evaluation-v2/evidence/sim-selection.json`. Dependencies: T002, T003. Verification: `python -m unittest tests.test_lightning_selection` and `python -m scripts.spec090_simulate --selection`.
- [ ] T007 (REQ-016 / SC-021): Decision journal (results, seeds, frozen hashes) and replay: each decision is a pure function of the journal. Files: `agent_braid/lightning_selection.py`, `tests/test_lightning_selection.py`. Dependencies: T006. Verification: `python -m unittest tests.test_lightning_selection`.

## Phase P2 — run machinery (no quota)

- [ ] T008 (REQ-014 / SC-019): Run reports carry `configDigest`, per-rollout host CLI, model and plugin versions, tool-call count and skill-invoked flag; existing SPEC-078 and SPEC-079 reports are not rewritten. Files: `agent_braid/lightning_runner.py`, `agent_braid/lightning_store.py`, `tests/test_lightning_runner.py`. Dependencies: none. Verification: `python -m unittest tests.test_lightning_runner` and `quick`.
- [ ] T009 (REQ-001, REQ-004, REQ-006, REQ-023, REQ-026, REQ-028, REQ-030 / SC-001, SC-006, SC-009, SC-028, SC-031, SC-033, SC-035): Gate A analysis in a new module (the SPEC-078 and SPEC-079 analysis modules stay unchanged): majority pass, exact bounds, class rule, `held` until review, redacted review record, no threshold-share field and no Wilson verdict, rejection of pre-existing runs such as v4; document gate A in `docs/tooling/LIGHTNING.md`. Files: `agent_braid/lightning_gate_a.py`, `tests/test_lightning_gate_a.py`, `docs/tooling/LIGHTNING.md`. Dependencies: T002. Verification: `python -m unittest tests.test_lightning_gate_a`.
- [ ] T010 (REQ-005 / SC-007, SC-008): Reserve replacement in frozen draw order up to the OD-8 cap; above the cap the verdict is `invalidated`. Files: `agent_braid/lightning_gate_a.py`, `tests/test_lightning_gate_a.py`. Dependencies: T009, T001 (OD-8). Verification: `python -m unittest tests.test_lightning_gate_a`.
- [ ] T011 (REQ-012, REQ-027 / SC-016, SC-032): Audit set handling: frozen by sha256, disjointness check against slices, development sets and splits, never passed to selection; winner reported with an exact interval. Files: `agent_braid/lightning_selection.py`, `tests/test_lightning_selection.py`. Dependencies: T006, T001 (OD-5). Verification: `python -m unittest tests.test_lightning_selection`.
- [ ] T012 (REQ-013, REQ-021 / SC-017, SC-018, SC-026): Drift controls: host and model pin check, re-baseline refusal on change, A/A anchors, seeded interleaved blocks; refusal of adaptive allocation for held-out and audit runs. Files: `agent_braid/lightning_runner.py`, `tests/test_lightning_drift.py`. Dependencies: T008. Verification: `python -m unittest tests.test_lightning_drift`.
- [ ] T013 (REQ-015 / SC-020): Gate 0 invocation tripwire on a development twin with the OD-9 threshold; a failing tripwire refuses the held-out run. Files: `agent_braid/lightning_gate_a.py`, `tests/test_lightning_gate_a.py`. Dependencies: T008, T001 (OD-9). Verification: `python -m unittest tests.test_lightning_gate_a`.
- [ ] T014 (REQ-019 / SC-024): GEPA and APO selection steps call the paired selection for configurations under this specification; SPEC-072 configurations replay unchanged. Files: `agent_braid/lightning_gepa.py`, `agent_braid/lightning_apo.py`, `tests/test_lightning_selection.py`. Dependencies: T006. Verification: `python -m unittest tests.test_lightning_selection` and the SPEC-072 replay tests.
- [ ] T015 (REQ-018 / SC-023): Refuse `parallel` above 1 without a recorded OD-6 adoption; if adopted, implement bounded concurrency with decision replay identical across `parallel` values. Files: `agent_braid/lightning_runner.py`, `tests/test_lightning_runner.py`. Dependencies: T001 (OD-6), T007. Verification: `python -m unittest tests.test_lightning_runner`.

## Phase P3 — preregistration and gate A run

- [ ] T019 (REQ-009, REQ-017 / SC-013): Re-run T004 to T006 with the noise-pilot parameters and record the slice size. Requires SPEC-091 T008 (noise pilot). Files: `specs/090-lightning-evaluation-v2/evidence/sim-pilot-parameters.json`. Dependencies: T004, T005, T006. Verification: `python -m scripts.spec090_simulate --all --pilot specs/091-invocation-gate/evidence/noise-pilot.json`.
- [ ] T016 (REQ-007, REQ-017, REQ-020, REQ-022, REQ-024, REQ-029 / SC-010, SC-022, SC-025, SC-027, SC-029, SC-034): Complete `evaluation-protocol.md` with the T001 values, write the fresh gate A split, reserve and twin (OD-13), run Gate 0 with the tripwire, and freeze protocol, split, reserve, simulation record and pinned plugin commit by sha256 on a `develop` commit; boundary tests. Files: `specs/090-lightning-evaluation-v2/prompts/`, `scripts/spec090_freeze.py`, `tests/test_spec090_boundaries.py`. Dependencies: T001, T009 to T013, T019. Verification: `python -m scripts.spec090_freeze --check`.
- [ ] T017 (REQ-025 / SC-030): One gate A run on the frozen split, only after the owner's yes; report every preregistered statistic. Files: `specs/090-lightning-evaluation-v2/evidence/gate-a-report.json`. Dependencies: T016, owner yes. Verification: `agent_braid.lightning_gate_a` on the run directory.
- [ ] T018 (REQ-025): Converge: record H1 to H3 outcomes (supported, not supported or inconclusive) and the gate verdict, if T017 ran. Dependencies: T004 to T007, T017 or the owner's decision not to run it. Verification: `python -m scripts.validate_spec_kit` and owner review.
