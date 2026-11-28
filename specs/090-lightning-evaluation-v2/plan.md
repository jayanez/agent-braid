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
2. **Reserve (REQ-005).** A reserve is frozen with the split in a per-class draw order fixed by a recorded
   seed. Every `instrument` prompt counts as 0/3 in the verdict; the next reserve prompt of the same class
   runs in the same session block and is reported only, up to the OD-8 cap (a replaced reserve prompt counts
   toward it).
3. **Slice sizing (REQ-009, REQ-031, REQ-041).** The confirmation slice is sized in majority-pass units.
   With D the per-prompt majority-pass difference (challenger minus incumbent, values −1, 0, 1), the pilot
   gives the discordance q = P(D ≠ 0) and the advantage a = E[D], so σ_m² = q − a². The confirmation size is
   n = ⌈((z₁₋α′ + z₁₋β)·σ_m/(Δ − δ))²⌉ at α′ = the OD-16 family-wise α divided by the number of challengers
   that can reach confirmation (the Holm worst case), the OD-4 power, and the margin δ and target advantage
   Δ > δ of OD-3. This is power to reject "advantage ≤ δ" when the true advantage is Δ; at a true advantage of
   exactly δ the power equals α′, so sizing on δ alone would be wrong. Sizing is refused when Δ exceeds the
   pilot's exact upper bound on q, because an advantage cannot exceed the discordance. Each confirmation
   prompt runs 3 repetitions, as majority pass requires. The elimination slice is a screen with no power
   target: it takes the OD-4 budget left after confirmation, and each of its prompts runs
   r* = max(1, round(√((c_p/c_r)(1−ρ)/ρ))) repetitions, with c_p/c_r and ρ measured by the pilot. A slice
   whose power at Δ is below the OD-4 power is refused as underpowered (REQ-031): at n = 5 a two-sided exact
   McNemar test cannot reach 0.05 (smallest p-value 0.0625), a one-sided exact sign test reaches 1/32 only
   when all five pairs are discordant in one direction, and McNemar's n counts discordant pairs only. When
   the sized budget exceeds the OD-4 budget there is no default; the owner chooses (REQ-041).
4. **Selection (REQ-008, REQ-010, REQ-011, REQ-034, REQ-035, REQ-041).** Each elimination round assigns the
   same new prompts to every surviving challenger and ranks them by the per-prompt valid-rate difference
   against the incumbent; the OD-11 rule drops challengers; rounds stop when one survives or the
   elimination budget is spent. The survivors are tested against the incumbent on the confirmation slice,
   frozen before elimination and disjoint from it, on per-prompt majority pass; the incumbent is replaced
   only when the OD-11 test rejects "advantage ≤ δ", with Holm over the family at the OD-16 α. Elimination
   uses the finer valid-rate statistic because it separates candidates with fewer prompts; it only screens.
   The replacement test uses majority pass so that what selection certifies is the gate A estimand.
5. **Audit set (REQ-012, REQ-027, REQ-036).** Authored and frozen in T021, checked for disjointness by
   normalized text and fingerprint, never passed to selection, scored once per winner and never used to
   choose between runs; every selection slice, split, reserve and twin is checked against it when frozen.
6. **Verdict (REQ-038).** Gate A is conjunctive: `met` needs the lower bound, the all-fail bound and the
   class rule. A false `met` requires at least one component's null to be true while every component
   passes; each component at level α bounds that probability by α (intersection–union principle), so no
   adjustment is needed. Precedence: `invalidated` > `held` > `missed` and `met`.
7. **Stops and resume (REQ-037).** One rule for quota stops and host or model changes, shared with SPEC-091:
   a pinned host or model that differs before any rollout refuses the run without spending the split; a
   change during a held-out run, or a blocked resume, invalidates and spends it; a resume fills only the
   unfilled slots in frozen order on the same bytes, host and model.
8. **Pilot freeze (REQ-039).** T020 freezes its protocol section, prompts and the OD-21 arms before it runs.
9. **Drift (REQ-013, REQ-021, REQ-040).** The runner records versions and the server-reported model per
   rollout, refuses a session whose host or model differs from the pin, schedules A/A anchors and
   interleaved blocks from a recorded seed, applies the OD-19 action, and refuses adaptive allocation for
   held-out and audit runs.
10. **Gate 0 (REQ-015, REQ-044).** Static Gate 0 (T023) scores references and null baselines with no rollout;
    the tripwire run (T022) on the twin is Gate 0's only rollouts, against the gate A threshold.
11. **Journal (REQ-016).** Every decision function takes the journal and returns the decision and its hash.
12. **Concurrency (REQ-018).** `parallel` above 1 is refused unless OD-6 is recorded as adopted.
13. **Owner yes (REQ-017, REQ-045).** The runner reads `evidence/owner-yes.md` and refuses a run without a
    dated line naming its task, run and frozen protocol hash.
14. **Data model and evolution.** The journal, the gate A report and the simulation record each carry a
    `schema` version string; a reader rejects an unknown version instead of guessing. The SPEC-078 and
    SPEC-079 report schemas are not changed; new fields go into the new schema versions only.
15. **Dependency failure.** T019 depends on T020 (the gate A noise pilot, REQ-032); if T020 fails or is
    unavailable, T019 MUST NOT run, the slice size stays undecided and T016 stays blocked; no default size is substituted.

## Validation strategy

Generated from `assurance.json`; each test file is listed in the Files of the task that owns it.

| Task | REQ | SC | Test file |
|---|---|---|---|
| T002 | REQ-002, REQ-003 | SC-002, SC-004 | `tests/test_lightning_stats.py` |
| T004 | REQ-002, REQ-033 | SC-003, SC-038 | `tests/test_lightning_sim.py` |
| T005 | REQ-003 | SC-005 | `tests/test_lightning_sim.py` |
| T006 | REQ-008, REQ-009, REQ-010, REQ-011, REQ-031, REQ-034, REQ-035, REQ-041 | SC-011, SC-012, SC-013, SC-014, SC-015, SC-036, SC-039, SC-040, SC-049 | `tests/test_lightning_selection.py`, `tests/test_lightning_sim.py` |
| T007 | REQ-016 | SC-021 | `tests/test_lightning_selection.py` |
| T008 | REQ-014, REQ-017, REQ-045 | SC-019, SC-022, SC-053 | `tests/test_lightning_runner.py` |
| T009 | REQ-001, REQ-004, REQ-006, REQ-023, REQ-026, REQ-028, REQ-030, REQ-038 | SC-001, SC-006, SC-009, SC-028, SC-031, SC-033, SC-035, SC-045, SC-046 | `tests/test_lightning_gate_a.py` |
| T010 | REQ-005 | SC-007, SC-008 | `tests/test_lightning_gate_a.py` |
| T011 | REQ-012, REQ-027, REQ-036 | SC-016, SC-032, SC-041 | `tests/test_lightning_selection.py` |
| T012 | REQ-013, REQ-021, REQ-037, REQ-040 | SC-017, SC-018, SC-026, SC-042, SC-043, SC-044, SC-048 | `tests/test_lightning_drift.py` |
| T013 | REQ-015 | SC-020 | `tests/test_lightning_gate_a.py` |
| T014 | REQ-019 | SC-024 | `tests/test_lightning_selection.py` |
| T015 | REQ-018 | SC-023 | `tests/test_lightning_runner.py` |
| T016 | REQ-007, REQ-020, REQ-022, REQ-024, REQ-029, REQ-042, REQ-043 | SC-010, SC-025, SC-027, SC-029, SC-034, SC-050, SC-051 | `tests/test_spec090_boundaries.py` |
| T017 | REQ-025 | SC-030 | `tests/test_spec090_boundaries.py` |
| T020 | REQ-032, REQ-039 | SC-037, SC-047 | `tests/test_spec090_pilot.py`, `tests/test_spec090_boundaries.py` |
| T023 | REQ-044 | SC-052 | `tests/test_lightning_gate_a.py` |

Negative controls are listed in [validation-plan.md](validation-plan.md). Labels are scorer outcomes; the
only human judgment is the 0/3 review. Missing results count as failed repetitions. Calibration is not
claimed. Cost: simulations spend no quota; the gate A noise pilot (T020) is about 180 rollouts at the OD-14
recommendation; the gate A run (T017) is about 300 rollouts plus reserve, EUR 0.

## Constitution check after design

Unchanged: no execution authority, no new dependency, no paid route, frozen paths untouched, simulations
and preregistration precede observation. No blocker.

## Human review and unresolved decisions

OD-1 to OD-21 are open (spec.md). The owner's yes is required for T020 (pilot), T022 (Gate 0 tripwire run) and
T017 (gate A run); T023 is a static Gate 0 with no rollout; and the owner reviews every freeze (T016, T020, T021).
SPEC-079 T009 is not decided here.
