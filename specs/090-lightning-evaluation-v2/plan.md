# Implementation plan: SPEC-090 — Lightning evaluation v2: statistical machinery and gate A

## Technical context and scope

- New modules: `agent_braid/lightning_stats.py` (exact bounds and tests), `agent_braid/lightning_selection.py`
  (paired synchronized selection, audit set, journal and replay), `agent_braid/lightning_gate_a.py`
  (gate A analysis, reserve, tripwire); `scripts/spec090_simulate.py`, `scripts/spec090_freeze.py`.
- Changed modules: `agent_braid/lightning_runner.py` and `agent_braid/lightning_store.py` (metadata, drift
  controls, `parallel` guard), `agent_braid/lightning_gepa.py` and `agent_braid/lightning_apo.py` (selection
  step only, REQ-019).
- Unchanged: `scripts/spec069_scoring.py`, `agent_braid/lightning_heldout_v2.py` to `_v4.py`, every SPEC-078
  and SPEC-079 split, protocol and FREEZE file (REQ-020).
- Out of scope: everything in spec.md "Out of scope"; gate B and its lab are SPEC-091.

## Constitution check before research

Clause zero and Articles 9, 12, 13, 14, 19, 20, 21, 23. Obligations mapped: preregistration before
observation (REQ-017, T016); evidence bounded to its domain (one host, model, split per run); replayable
decisions (Article 14, REQ-016); negative results recorded (T018); EUR 0 (ADR 0021); Lightning boundary
(ADR 0039: no promotion, no training, no LLM judge). No MUST conflict found. SHOULD deviation: none.

## Research, assumptions and alternatives

See [research.md](research.md). No user, telemetry or third-party data is used; prompts are authored
synthetic tasks over the SPEC-069 fixture workspace, so no consent gate applies to the split. Redacted
transcripts for the 0/3 review follow SPEC-074.

## Design

1. **Estimands (REQ-001 to REQ-003).** For prompt i with p_i, its per-repetition probability of a valid
   first attempt, and three repetitions
   independent given p_i: the prompt passes with probability π(p_i) = 3p_i² − 2p_i³ and is 0/3 with
   probability (1 − p_i)³. With prompts drawn independently, the passing count is Binomial(n, E[π(p)]) and
   the 0/3 count is Binomial(n, θ) with θ = E[(1 − p)³]. Both bounds are exact Clopper–Pearson bounds on
   these binomials, at the α of OD-1. A share of prompts with p below a threshold is a different functional,
   not identified by three repetitions (REQ-023).
2. **Reserve (REQ-005).** A reserve is frozen with the split in a draw order fixed by a recorded seed. Each
   `instrument` prompt is replaced by the next reserve prompt, scored in a separate run of the same arm, up to
   the OD-8 cap.
3. **Slice sizing (REQ-009).** With d_i the per-prompt paired difference averaged over r repetitions,
   σ_d² = σ_b² + σ_w²/r from the gate A noise pilot (REQ-032), the slice size is
   n = ⌈((z₁₋α + z₁₋β)·σ_d/(Δ − δ))²⌉ at the α and power of OD-1 and OD-4, the margin δ and the target
   advantage Δ > δ of OD-3. This is power to reject "advantage ≤ δ" when the true advantage is Δ; at a true
   advantage of exactly δ the power equals α, so sizing on δ alone would be wrong. A size below the smallest n whose exact test can reach α is refused
   (at n = 5 the smallest two-sided exact McNemar p-value is 0.0625).
4. **Selection (REQ-008, REQ-010, REQ-011).** Each round assigns the same new items to every surviving
   candidate; the OD-11 rule drops candidates; the incumbent is replaced only when the OD-11 test rejects
   "challenger advantage ≤ δ".
5. **Audit set (REQ-012).** Built and frozen like a split, checked for disjointness by normalized text and
   fingerprint, never passed to selection; the winner's audit result is reported with an exact interval.
6. **Drift (REQ-013, REQ-021).** The runner records versions per rollout, refuses a session whose host or
   model differs from the pin, schedules A/A anchors and interleaved blocks from a recorded seed, and refuses
   adaptive allocation for held-out and audit runs.
7. **Tripwire (REQ-015).** Gate 0 runs the development twin first (OD-9) and refuses the held-out run below
   the threshold.
8. **Journal (REQ-016).** Every decision function takes the journal and returns the decision and its hash.
9. **Concurrency (REQ-018).** `parallel` above 1 is refused unless OD-6 is recorded as adopted.
10. **Data model and evolution.** The journal, the gate A report and the simulation record each carry a
    `schema` version string; a reader rejects an unknown version instead of guessing. The SPEC-078 and
    SPEC-079 report schemas are not changed; new fields go into the new schema versions only.
11. **Dependency failure.** If the gate A noise pilot (T020, dependency of T019) fails or is unavailable, T019
    does not run, the slice size stays undecided and T016 stays blocked; no default size is substituted.

## Validation strategy

| REQ | SC | Test | Planned evidence |
|---|---|---|---|
| REQ-001, REQ-004, REQ-006, REQ-023, REQ-026, REQ-028, REQ-030 | SC-001, SC-006, SC-009, SC-028, SC-031, SC-033, SC-035 | `tests/test_lightning_gate_a.py` | unit test output, T009 |
| REQ-002, REQ-003 | SC-002, SC-004 | `tests/test_lightning_stats.py` | reference values, T002 |
| REQ-002, REQ-003, REQ-033 | SC-003, SC-005, SC-038 | `tests/test_lightning_sim.py`, `scripts/spec090_simulate.py` | simulation records, T004, T005 |
| REQ-032 | SC-037 | `tests/test_spec090_pilot.py` | pilot report, T020 |
| REQ-005 | SC-007, SC-008 | `tests/test_lightning_gate_a.py` | unit test output, T010 |
| REQ-008 to REQ-011, REQ-031 | SC-011 to SC-015, SC-036 | `tests/test_lightning_selection.py`, simulation | T006 |
| REQ-012, REQ-016, REQ-019, REQ-027 | SC-016, SC-021, SC-024, SC-032 | `tests/test_lightning_selection.py` | T007, T011, T014 |
| REQ-013, REQ-021 | SC-017, SC-018, SC-026 | `tests/test_lightning_drift.py` | T012 |
| REQ-014, REQ-018 | SC-019, SC-023 | `tests/test_lightning_runner.py` | T008, T015 |
| REQ-015 | SC-020 | `tests/test_lightning_gate_a.py` | T013 |
| REQ-007, REQ-017, REQ-020, REQ-022, REQ-024, REQ-029 | SC-010, SC-022, SC-025, SC-027, SC-029, SC-034 | `tests/test_spec090_boundaries.py` | T016 |
| REQ-025 | SC-030 | `tests/test_spec090_boundaries.py` | T017 |

Negative controls are listed in [validation-plan.md](validation-plan.md). Labels are scorer outcomes; the
only human judgment is the 0/3 review. Missing results count as failed repetitions. Calibration is not
claimed. Cost: simulations spend no quota; the gate A noise pilot (T020) is about 180 rollouts at the OD-14
recommendation; the gate A run (T017) is about 300 rollouts plus reserve, EUR 0.

## Constitution check after design

Unchanged: no execution authority, no new dependency, no paid route, frozen paths untouched, simulations
and preregistration precede observation. No blocker.

## Human review and unresolved decisions

OD-1 to OD-13 are open (spec.md). The owner's yes is required for T016's freeze review and for T017.
SPEC-079 T009 is not decided here.
