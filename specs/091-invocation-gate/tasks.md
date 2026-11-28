# SPEC-091: Tasks

**Milestone:** provisional, BL.2c (OD-15).

Stable task IDs. Completion requires obtained evidence; task completion does not imply owner acceptance
or support for H1 to H3. Parallelizable is a dependency property and does not authorize concurrent
agents. One pull request per task; the owner approves each merge. Each real run (T008, T009, T012, T015)
needs its own frozen protocol and the owner's yes; no other task spends quota.

`quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P0 — owner review

- [ ] T001 (OD-1..OD-16, OD-B1, ADR 0046): Owner review of this specification and ADR 0046: commit the dated OD-B1 record (2026-11-27) and the strategy approval (2026-11-28), and decide or defer each of OD-1 to OD-16. Files: `specs/091-invocation-gate/evidence/t001-owner-decisions.md`. Dependencies: none. Verification: owner review; `python -m scripts.validate_spec_kit`.

## Phase P1 — items, laboratory, levers and target (no quota)

- [ ] T002 (REQ-002, REQ-003, REQ-019, REQ-027, REQ-028 / SC-002, SC-003, SC-020, SC-028, SC-029): Labelling rubric, label record schema with sha256 freeze and versioning, item-set builder with near-miss and per-label counts, leakage checks against SPEC-069, v2, v3 and v4, and refusal of v4 prompts unless OD-1 allows them. Files: `scripts/spec091_build_items.py`, `specs/091-invocation-gate/labelling-rubric.md`, `tests/test_spec091_items.py`. Dependencies: T001 (OD-1, OD-2, OD-8). Verification: `python -m unittest tests.test_spec091_items`.
- [ ] T003 (REQ-004, REQ-021, REQ-022, REQ-031 / SC-004, SC-022, SC-023, SC-032): Gate B laboratory profile with the OD-5 tools and pinned co-installed skills recorded in `configDigest`; other tools stay disabled; subscription-only guard. Files: `scripts/spec069_native_runs.py` (new profile only; existing profiles unchanged), `tests/test_spec091_lab.py`. Dependencies: T001 (OD-5). Verification: `python -m unittest tests.test_spec091_lab` and `quick`.
- [ ] T004 (REQ-005, REQ-006, REQ-024, REQ-032 / SC-005, SC-007, SC-025, SC-033): Lever arms as laboratory builds: `anthropic/alwaysLoad` in `analyze-work` `_meta`, MCP server instructions, use-case-first skill description; re-verify the host caps against host documentation; single-difference check; release check that refuses `_meta` or server-instruction changes without the OD-10 record. Files: `agent_braid/tooling_mcp.py`, `agent_braid/plugin_mcp.py`, `integrations/agent-braid/plugin/`, `tests/test_spec091_levers.py`. Dependencies: T001 (OD-10, OD-14). Verification: `python -m unittest tests.test_spec091_levers tests.test_tooling_mcp` and `quick`.
- [ ] T005 (REQ-005, REQ-007, REQ-008 / SC-006, SC-008, SC-009): Factual `UserPromptSubmit` hook arm with the OD-4 text frozen by sha256 and no prompt persistence; explicit command arm named per OD-12 with its deterministic-entry check. Files: `integrations/agent-braid/plugin/`, `tests/test_spec091_levers.py`. Dependencies: T001 (OD-4, OD-11, OD-12). Verification: `python -m unittest tests.test_spec091_levers`.
- [ ] T006 (REQ-009, REQ-010, REQ-029 / SC-010, SC-011, SC-030): `target.kind` gains the OD-14 kinds; `lightning_resources` splits and recombines each target with every other byte hashed; caps refuse oversized candidates; SPEC-072 skill configurations replay identically. Files: `agent_braid/lightning_config.py`, `agent_braid/lightning_resources.py`, `tests/test_lightning_resources.py`. Dependencies: T001 (OD-14). Verification: `python -m unittest tests.test_lightning_resources` and the SPEC-072 replay tests.
- [ ] T007 (REQ-018 / SC-019): SIM: coverage of the recall and false-positive bounds, type I and II error of the 2×2 analysis for main effects and interaction with known effects and correlation 0.41 to 0.81, and factorial journal replay. Requires SPEC-090 T003. Files: `scripts/spec090_simulate.py` (gate B mode), `tests/test_lightning_sim.py`, `specs/091-invocation-gate/evidence/sim-gate-b.json`. Dependencies: T002. Verification: `python -m scripts.spec090_simulate --gate-b`.

## Phase P2 — development pilots (real rollouts, owner yes each)

- [ ] T008 (REQ-012 / SC-013): Noise pilot on fresh development prompts: within-prompt correlation, candidate disagreement rate, A/A drift; output in the SPEC-090 input format. Requires SPEC-090 T008 and T012. Files: `specs/091-invocation-gate/evidence/noise-pilot.json`, `tests/test_spec091_pilots.py`. Dependencies: T003, T007, owner yes. Verification: report schema test and the run directory.
- [ ] T009 (REQ-011 / SC-012): Development factorial 2³ (product name × form × completeness sentence) at the OD-6 size, descriptive per-cell intervals (H3). Files: `scripts/spec091_build_items.py` (factorial mode), `specs/091-invocation-gate/evidence/dev-factorial.json`. Dependencies: T002, T003, T007, owner yes. Verification: `python -m unittest tests.test_spec091_pilots` and the run directory.

## Phase P3 — preregistered 2×2 factorial

- [ ] T010 (REQ-001, REQ-017, REQ-026 / SC-001, SC-018, SC-027): Gate B analysis: recall and false-positive rate with exact bounds by label and class, factorial effects, report fields. Files: `agent_braid/lightning_gate_b.py`, `tests/test_lightning_gate_b.py`. Dependencies: T002; requires SPEC-090 T002. Verification: `python -m unittest tests.test_lightning_gate_b`.
- [ ] T011 (REQ-013, REQ-023 / SC-014, SC-024): Write and freeze the 2×2 protocol (description × hook, OD-7 counts, seeded interleaved blocks, H1 and H2), its labelled item set and the pinned builds, on a `develop` commit; boundary tests. Files: `specs/091-invocation-gate/evaluation-protocol.md`, `scripts/spec091_freeze.py`, `tests/test_spec091_boundaries.py`. Dependencies: T004, T005, T008, T009, T010. Verification: `python -m scripts.spec091_freeze --check`.
- [ ] T012 (REQ-013 / SC-014): Run the frozen 2×2 factorial once (owner yes) and report both metrics per cell, main effects and interaction. Files: `specs/091-invocation-gate/evidence/factorial-2x2.json`. Dependencies: T011, owner yes. Verification: `agent_braid.lightning_gate_b` on the run directory.

## Phase P4 — light text optimization and held-out

- [ ] T013 (REQ-009, REQ-020 / SC-021): One to three contrastive rewrites of the adopted targets from false positives and false negatives (5 to 20 candidates, SPEC-090 OD-7), selected by the SPEC-090 paired selection with a reward that includes the false-positive component. Requires SPEC-090 T006 and T011. Files: `agent_braid/lightning_resources.py`, `tests/test_lightning_resources.py`. Dependencies: T006, T012. Verification: `python -m unittest tests.test_lightning_resources`.
- [ ] T014 (REQ-014, REQ-015 / SC-015, SC-016): Gate B held-out item set and labelled twin, Gate 0 with the SPEC-090 tripwire, freeze; refused unless T012 meets the OD-9 criterion and OD-3 is decided. Files: `specs/091-invocation-gate/prompts/`, `scripts/spec091_freeze.py`. Dependencies: T012, T001 (OD-3, OD-9). Verification: `python -m scripts.spec091_freeze --check`.
- [ ] T015 (REQ-001 / SC-001): One gate B held-out run (owner yes); report recall and false-positive rate against OD-3. Files: `specs/091-invocation-gate/evidence/gate-b-report.json`. Dependencies: T014, owner yes. Verification: `agent_braid.lightning_gate_b` on the run directory.
- [ ] T016 (REQ-016, REQ-030 / SC-017, SC-031): If OD-13 adopts it, run `claude plugin eval` once as a non-gating contrast and record its version and disagreements. Files: `specs/091-invocation-gate/evidence/plugin-eval-contrast.json`. Dependencies: T004, T005, owner yes. Verification: report review.
- [ ] T017 (REQ-025 / SC-026): Converge: record H1 to H3 outcomes (supported, not supported or inconclusive); any lever ships only through a SPEC-073 promotion decision and OD-11. Dependencies: T012, and T015 or the owner's decision not to run it. Verification: `python -m scripts.validate_spec_kit` and owner review.
