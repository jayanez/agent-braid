# Feature specification: SPEC-090 — Lightning evaluation v2: statistical machinery and gate A

**Milestone:** provisional, BL.2c — Lightning tool-level kind-choice fix (OD-10).
**Template:** spec-kit feature specification.
**Status:** draft. Nothing is implemented or run, and nothing here authorizes a rollout.
**Decision record:** [ADR 0046](../../docs/adr/0046-lightning-evaluation-design.md) (Proposed).

## Purpose and scope

SPEC-079 T008 passed 17 of 100 v4 prompts against a gate of 88. The model called `analyze-work` in 53 of
300 rollouts, and 51 of those 53 first requests were valid
([diagnosis](../079-kind-choice-tool-fix/evidence/t008-diagnosis-and-strategy-review.md)). Two endpoints
were measured as one: authoring validity and unprompted invocation. ADR 0046 separates them into gate A
and gate B. This specification covers the shared statistical machinery and gate A.
[SPEC-091](../091-invocation-gate/spec.md) covers gate B.

The review behind ADR 0046 found that the current gate and selection use quantities the data cannot
support: a Wilson bound read as a 95 % bound, a "no prompt is 0/3" rule that is an all-fail test with
an implicit threshold, top-k selection on independent means of five cases, and no audit of the winner.

Actors: the owner, who decides every OD, reviews every freeze and says yes to every run; the operator
who runs the `agent-braid lightning` CLI; and the host under test (`claude-code`), whose user-facing
behaviour is measured. No actor gains execution authority.

This is engineering plus a research protocol:

- Engineering: exact bounds and the all-fail bound (REQ-001 to REQ-007, REQ-026, REQ-038); paired,
  synchronized selection with an incumbent margin, a confirmation slice, Holm and an audit set (REQ-008 to
  REQ-012, REQ-019, REQ-027, REQ-031, REQ-034 to REQ-036, REQ-041); split construction (REQ-024, REQ-042,
  REQ-043); Gate 0 (REQ-015, REQ-044); stops, resume and drift (REQ-037, REQ-040); owner yes records
  (REQ-045); redacted review records (REQ-030); the pilot freeze (REQ-039); drift controls, run metadata,
  a Gate 0 invocation tripwire and replayable decisions (REQ-013 to REQ-016); runner concurrency kept
  behind an owner decision (REQ-018).
- Research: simulation tests of the procedures, including a template-clustered scenario, before any real
  run (REQ-017, REQ-033; H1 to H3), a gate A noise pilot that sizes the slice (REQ-032), then a
  preregistered gate A split (T016) whose run is a separate owner decision.

Out of scope, each stated as a requirement: frozen SPEC-069, SPEC-078 and SPEC-079 records (REQ-020) and
any retroactive use of the new gate on v4 (REQ-028); the Wilson verdict (REQ-026); adaptive allocation, including Thompson Sampling, in
held-out or audit data (REQ-021); provider keys and other secrets (REQ-022); LLM judges (REQ-029); a non-identified gate
quantity (REQ-023); spent sets as a gate A held-out split (REQ-024); automatic promotion (REQ-025).
Not covered here at all: gate B, item labels, the invocation lab and its levers, the optimizer target
extension and the gate B pilots, which are SPEC-091; weight training (ADR 0042, deferred); hosts other than
`claude-code`; SPEC-079 T009, which stays the owner's decision.

## Authorities

Constitution clause zero and Articles 9, 12, 13, 14, 19, 20, 21 and 23;
[GOVERNANCE.md](../../GOVERNANCE.md); [claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md) (EUR 0);
[ADR 0039](../../docs/adr/0039-braid-lightning-boundary.md) (Lightning boundary, unchanged);
[ADR 0040](../../docs/adr/0040-braid-lightning-mit-vendoring.md) (vendored APO, legacy `v0.x`);
[ADR 0042](../../docs/adr/0042-braid-lightning-local-weight-training.md) (deferred);
[ADR 0046](../../docs/adr/0046-lightning-evaluation-design.md) (Proposed). Precedents:
[SPEC-049](../049-harness-evaluation-learning/spec.md) (noninferiority),
[SPEC-071](../071-lightning-rollouts-reward/spec.md) (runner, quota stops),
[SPEC-073](../073-lightning-promotion/spec.md) (promotion), [SPEC-078](../078-lightning-heldout-v2/spec.md) (OD-1, Gate 0),
[SPEC-079](../079-kind-choice-tool-fix/spec.md) (v4, T008).

## Clarifications

- **Strategy approval (2026-11-28).** The owner approved the corrected strategy that ADR 0046 records,
  as a planning decision. No dated record exists in the repository yet; T001 records it.
- **OD-B1 (2026-11-27).** Gate B items are labelled before measurement; it has no committed record yet,
  binds SPEC-091, and SPEC-091 T001 records it.
- Every numeric parameter other than those inherited from SPEC-078 OD-1 and the approved strategy (the
  2-of-3 majority, 3 repetitions and the 0.80 threshold) is open (Owner decisions). None is filled in.

## Requirements and acceptance scenarios


#### REQ-001 — Gate A unit and outcome

Gate A MUST score prompts that name the product. The unit is the prompt; a prompt passes when at least 2 of its 3 repetitions are `validFirstAttempt` under the unchanged SPEC-069 scorer, giving one binary result per prompt. A missing rollout result MUST count as a failed repetition.

- SC-001: Given a prompt with repetition outcomes valid, valid, invalid, when the gate A analysis scores it, then the prompt passes; with valid, invalid, missing it fails.

#### REQ-002 — Exact lower bound on the passing share

Gate A MUST report the exact one-sided Clopper–Pearson lower bound of the passing share at the α of OD-1; this condition holds when the bound is at least 0.80, the threshold inherited from SPEC-078 OD-1.

- SC-002: Given 88 passing prompts of 100 and α = 0.05, when the bound is computed, then it equals the exact Clopper–Pearson value 0.8128 to four decimals.
- SC-003: Given a candidate pool with known per-repetition probabilities of a valid first attempt, the measured within-prompt correlation and, separately, a template-clustered scenario, when the gate is simulated (SIM), then its type I error at the boundary does not exceed α within simulation error in the independent scenario, and its type I error, power and coverage are reported for the clustered scenario.

#### REQ-003 — All-fail upper bound

- (a) Gate A MUST report the exact one-sided Clopper–Pearson upper bound of the all-fail rate θ = E[(1−p)³], with p a prompt's per-repetition probability of a valid first attempt, estimated by the count of prompts with 0 of 3 valid repetitions.
- (b) This condition holds when the bound is at most the preregistered threshold τ of OD-2.
- (c) The rule "no prompt is 0/3" MUST NOT be used for splits frozen under this specification.
- SC-004: Given 2 prompts at 0/3 out of 100 and α = 0.05, when the bound is computed, then it equals 0.0616 to four decimals.
- SC-005: Given prompt populations with known θ, when the bound is simulated (SIM), then its coverage is at least 1 − α within simulation error for every θ in the grid.
- SC-054: Given a protocol under this specification that states the rule "no prompt is 0/3" as a gate condition, when the freeze check runs, then it refuses.

#### REQ-004 — Review of each 0/3 prompt

Each prompt at 0/3 MUST be held until the owner classifies it as `model` or `instrument` on redacted transcripts. The verdict MUST be `held` while any 0/3 prompt is unreviewed.

- SC-006: Given a run with one unreviewed 0/3 prompt, when the gate A analysis runs, then the verdict is held and names the prompt.

#### REQ-005 — Instrument replacement from a frozen reserve

For a split frozen under this specification:

- (a) the verdict MUST be computed with every prompt classified `instrument` counted as 0/3;
- (b) after the owner classifies a prompt `instrument`, the runner MUST run the next reserve prompt of the same class, in the preregistered per-class draw order of the reserve frozen by sha256 with the split, on the same frozen bytes and the same pinned host and model as the split;
- (c) the runner MUST add that reserve result to the report only;
- (d) replacements MUST NOT exceed the cap of OD-8, and a replaced reserve prompt MUST count toward the cap;
- (e) the replacements MUST follow the safeguards adopted in OD-18;
- (f) exceeding the cap, or a host or model change before the reserve run, MUST invalidate the run.
- (g) This requirement MUST NOT change SPEC-079, where `instrument` invalidates the run.
- SC-007: Given a run that meets the gate only if two `instrument` prompts are dropped, with a cap of three, when replacement runs, then the verdict counts both as 0/3 and stays missed, and the two reserve results appear in the report only.
- SC-008: Given instrument findings above the cap, or a host or model change before the reserve run, when replacement runs, then the verdict is invalidated.
- SC-055: Given a split with one prompt classified `instrument`, when replacement runs, then the next reserve prompt of the same class in the preregistered draw order runs on the same frozen bytes and the same pinned host and model as the split.
- SC-056: Given a split whose record of the safeguard adopted in OD-18 is missing, when replacement is requested, then it is refused and names the missing record.

#### REQ-006 — Class rule

Gate A MUST also require that every class of the split has at least half of its prompts passing.

- SC-009: Given a class with 4 of 10 prompts passing, when the gate A analysis runs, then the gate is not met whatever the bounds.

#### REQ-007 — Three repetitions

Gate A MUST use 3 repetitions per prompt. The freeze check MUST refuse a different number unless a new owner decision is recorded before the split is frozen.

- SC-010: Given a protocol declaring 2 repetitions without a recorded decision, when the freeze check runs, then it refuses.

#### REQ-008 — Paired comparison on one fixed slice

Elimination MUST rank candidates by per-prompt paired differences in the valid rate, averaged over repetitions, with every surviving candidate evaluated on the same fixed slice of prompts and repetitions; independent means MUST NOT be the decision statistic. The finer valid-rate difference MUST be used only to screen; the replacement test of REQ-011 MUST use per-prompt majority pass, the gate A estimand.

- SC-011: Given two candidates and a slice, when selection runs, then both are scored on identical prompt and repetition identifiers and the decision statistic is computed from paired differences.
- SC-012: Given known-p candidates with within-prompt correlation over the 0.41 to 0.81 range before the pilots and with the pilot's parameters in the re-run (T019) before any selection or held-out run, when paired selection and n = 5 independent means are simulated (SIM), then paired selection picks an ε-good candidate (within ε of OD-3 of the best) at a rate at least as high as n = 5, reported with its simulation interval.

#### REQ-009 — Slice sized from the pilot

The confirmation slice size MUST come from the gate A noise pilot of REQ-032 through the plan.md formula, in majority-pass units: variance σ_m² = discordance minus the squared advantage a² (σ_m² uses the pilot's point estimate of the discordance and a = Δ), the margin δ and target advantage Δ > δ of OD-3, the power of OD-4, and the Holm worst-case level, the OD-16 family-wise α divided by the maximum number of challengers admitted to confirmation (OD-7). The elimination slice is a screen with no power target; its size MUST be the OD-4 budget share left after confirmation. Each elimination prompt MUST run r* = max(1, round(√((c_p/c_r)(1−ρ)/ρ))) repetitions; each confirmation prompt MUST run 3, as majority pass requires. The sizing function MUST refuse an input whose Δ exceeds the pilot's exact upper bound on the majority-pass discordance, the share of prompts (unit: prompt) on which the two arms' majority-pass outcomes differ, because an advantage cannot exceed it.

- SC-013: Given pilot discordance estimate 0.30 with exact upper bound 0.33, ρ 0.5, c_p/c_r 8, family-wise α 0.05 over 3 challengers, power 0.80, δ 0.02 and Δ 0.07, and a second input with Δ 0.35, when the sizing function runs, then it returns the plan.md confirmation size at level 0.05/3 with σ_m² = 0.30 − 0.07², r* = 3, and refuses the second input because Δ exceeds the discordance bound.

#### REQ-010 — Synchronized elimination

Elimination MUST be synchronized: in each round all surviving candidates see the same new items. The elimination rule MUST be the one the owner picks in OD-11 after the simulation comparison.

- SC-014: Given three candidates in a round, when elimination runs, then all three receive the same item identifiers before any is dropped.

#### REQ-011 — Incumbent kept unless the margin is met

The incumbent MUST be kept unless a challenger beats it by the preregistered margin δ of OD-3 under the test of OD-11, on per-prompt majority pass, on the confirmation slice of REQ-034, at the family-wise α of OD-16.

- SC-015: Given a challenger whose paired majority-pass advantage on the confirmation slice is below the margin, although its elimination-slice advantage exceeds it, when selection decides, then the incumbent is kept and the elimination-slice result is not used in the test.

#### REQ-012 — Audit set

An audit set of the size of OD-5 MUST be frozen by sha256, disjoint by normalized text and fingerprint from every selection slice, development set and held-out split. The selected candidate MUST be reported on it with an exact 1 − α confidence interval (OD-1).

- SC-016: Given a selection run, when its inputs are traced, then no audit item identifier appears in any selection input.

#### REQ-013 — Drift controls

Every real run under this specification:

- (a) MUST pin the host CLI version with auto-update off, and the model;
- (b) MUST record the host, model and plugin versions per rollout;
- (c) MUST include A/A anchors of the OD-20 size each session, drawn from development prompts only during held-out runs;
- (d) MUST interleave arms in randomized blocks with a recorded seed;
- (e) MUST re-baseline after any host or model change, with the runner rerunning the A/A pair and the twin on the new host;
- (f) when any pilot estimate leaves its recorded interval after a re-baseline, sizing MUST rerun before the next freeze.
- SC-017: Given a development run whose host version changed between two of its sessions, when the next session starts, then it stops with a re-baseline required refusal; a held-out run in the same case follows REQ-037 instead.
- SC-018: Given a session, when arms are scheduled, then the block order is reproducible from the seed and contains the A/A anchors at the OD-20 size, drawn from development prompts only when the run is a held-out run.
- SC-057: Given a run configuration without a pinned host CLI version, with host auto-update on, or without a pinned model, when a real run is requested, then the runner refuses before any rollout.
- SC-058: Given a re-baseline after which a pilot estimate lies outside its recorded interval, when the next freeze is requested, then it is refused until sizing has rerun.

#### REQ-014 — Run metadata

Run reports MUST carry `configDigest`, per-rollout host CLI, model and plugin versions, the server-reported model identifier, the tool-call count and whether the skill was invoked.

- SC-019: Given a recorded rollout, when the report is built, then every listed field is present and a missing field fails the report.

#### REQ-015 — Gate 0 invocation tripwire

Gate 0 MUST reject a held-out run when the invocation rate on its development twin is below that gate's own threshold: for gate A, the T020 invocation rate of the shipped-build arm on product-naming prompts minus the OD-9 margin; for gate B, the threshold of SPEC-091 REQ-015. One threshold MUST NOT be applied to both gates.

- SC-020: Given a twin run whose invocation rate is below the threshold, when Gate 0 evaluates the tripwire, then it fails and the held-out run is refused.

#### REQ-016 — Replayable decisions

- (a) Every selection and gate decision MUST be a pure function of a journal (results, seeds, frozen hashes).
- (b) A replay of a journal MUST give an identical decision.
- SC-021: Given a recorded journal, when it is replayed twice, then both decisions and their hashes are identical.

#### REQ-017 — Simulation before any real run

The runner MUST reject a real run under this specification unless its frozen protocol carries the hash of the recorded simulation evidence (T004 to T007, plus T019 for runs sized from the pilot) and an owner yes record (REQ-045) names that protocol's hash; a development pilot (T020) needs the T004 to T007 record and its own pilot freeze (REQ-039) in place of T019.

- SC-022: Given a protocol without the simulation record hash, when a run is requested, then the runner refuses before any rollout.

#### REQ-018 — Runner concurrency

The runner MUST reject a `parallel` value above 1 unless the owner adopts concurrency in OD-6; if adopted, A/A anchors MUST measure the effect and a decision replay MUST be identical for any `parallel` value.

- SC-023: Given a configuration with parallel 2 and no recorded OD-6 adoption, when the run starts, then it refuses.

#### REQ-019 — Optimizer selection steps

For splits under this specification:

- (a) the GEPA and APO selection steps (`agent_braid/lightning_gepa.py`, `agent_braid/lightning_apo.py`) MUST use the paired selection of REQ-008 to REQ-011;
- (b) their candidate target MUST stay the skill body.
- SC-024: Given a GEPA round over three candidates, when its survivors are chosen, then the choice comes from the paired selection module, not from GEPA's minibatch-mean acceptance against the parent or APO's top-k beam.

#### REQ-020 — Frozen records untouched

This specification MUST NOT edit the SPEC-069 scorer or prompt sets, the SPEC-078 or SPEC-079 splits, protocols or FREEZE files.

- SC-025: Given the diff of every task, when the boundary test runs, then no frozen path changed.

#### REQ-021 — No adaptive allocation in frozen data

Adaptive allocation, including Thompson Sampling, MUST NOT be used to collect held-out or audit data.

- SC-026: Given a held-out or audit run configuration, when it is validated, then any allocation other than the fixed uniform schedule is refused.

#### REQ-022 — Cost and route

A run MUST NOT read or accept a provider API key or other secret. A run MUST use only the subscription route at EUR 0.

- SC-027: Given a rollout environment holding a provider key variable, when the run starts, then it is rejected before any rollout, as SPEC-071 does, and the key value appears in no record.

#### REQ-023 — No non-identified gate quantity

Gate A MUST NOT report, as a gate quantity, the share of prompts whose p is below a threshold, with p, a prompt's per-repetition probability of a valid first attempt.

- SC-028: Given a gate report, when its fields are listed, then no such quantity appears.

#### REQ-024 — Fresh gate A held-out split

Gate A under this specification MUST use a fresh split, reserve and twin: none shares a prompt, fingerprint or normalized 8-word window with SPEC-069, v2, v3, v4 and the frozen audit set.

- SC-029: Given a candidate reserve that shares a normalized 8-word window with v4, and a twin that shares a prompt with the frozen audit set, when the builder checks them, then it refuses both.

#### REQ-025 — Human promotion

A gate A pass MUST NOT promote a candidate; promotion MUST stay human under SPEC-073 with SPEC-049 noninferiority, and a build that changes the skill description, server instructions, `_meta` or the hook also needs the same-build certification of SPEC-091 REQ-038.

- SC-030: Given a passed gate, when its outputs are read, then no promotion pointer changes and `executionAuthorization` is false.

#### REQ-026 — No Wilson verdict

Gate A MUST NOT use the Wilson interval as its verdict statistic (split from REQ-002).

- SC-031: Given a gate A report, when its verdict inputs are listed, then only the exact bounds of REQ-002 and REQ-003 and the class rule appear.

#### REQ-027 — Audit set not read by selection

Selection MUST NOT read any audit set item; the freeze check MUST check every selection slice against the frozen audit set by normalized text and fingerprint when the slice is frozen (split from REQ-012).

- SC-032: Given a selection call given an audit item identifier, when it runs, then it is rejected.

#### REQ-028 — No retroactive gate

The gate A rules of this specification MUST NOT be applied to the SPEC-079 v4 run or any split frozen before this specification (split from REQ-020).

- SC-033: Given the SPEC-079 v4 run directory, when the gate A analysis is invoked on it, then it is rejected as out of scope.

#### REQ-029 — No LLM judge

A run MUST NOT use an LLM judge as a reward, label or gate source (split from REQ-022).

- SC-034: Given a reward configuration naming a model-graded component, when it is validated, then it is rejected.

#### REQ-030 — Redacted review records

The 0/3 review record MUST contain only transcripts redacted under SPEC-074, so that no unredacted prompt, file content, personal data or secret enters it.

- SC-035: Given a review record built from a transcript holding a planted secret marker, when it is saved, then the marker appears nowhere in the record.

#### REQ-031 — Minimum testable slice

- (a) The sizing function MUST reject a slice whose power at the target advantage Δ, from the plan.md formula, is below the OD-4 power.
- (b) When it rejects a slice, the sizing function MUST name the needed size.
- (c) A 5-prompt slice is underpowered: a two-sided exact McNemar test cannot reach 0.05 (smallest p-value 0.0625), a one-sided exact sign test reaches 1/32 only when all five pairs are discordant in one direction, and McNemar's n counts discordant pairs only (split from REQ-009).
- SC-036: Given a requested slice of 5 prompts with pilot discordance 0.30, at the OD-4 power and the OD-3 δ and Δ, when the sizing function runs, then it is rejected as underpowered with the needed size in the message.

#### REQ-032 — Gate A noise pilot

Before the slice is sized, a gate A noise pilot MUST run in the current laboratory on fresh development prompts that name the product, at the size of OD-14, and estimate the within-prompt correlation ρ, the variances of the per-prompt valid-rate and majority-pass differences between two candidate arms, their majority-pass discordance, A/A drift and the invocation rate, each with an interval, and record the cost ratio c_p/c_r (authoring and freezing time per prompt over mean rollout time, both measured).

- SC-037: Given a gate A noise pilot run, when its report is built, then it holds ρ, both paired-difference variances, the discordance, A/A differences and the invocation rate with intervals, and the measured c_p/c_r, in the sizing input format.

#### REQ-033 — Template-clustered simulation

- (a) The simulations of T004 and T005 MUST include a template-clustered scenario in which prompts of one template or class share a latent effect on p, over a grid of between-class variances.
- (b) Each of those simulations MUST report type I error, power and coverage under that scenario against the tolerance of OD-15.
- SC-038: Given a clustered scenario with nonzero between-class variance, when the gate A and all-fail simulations run, then type I error, power and coverage are reported per variance and compared with the OD-15 tolerance.

#### REQ-034 — Confirmation slice

The replacement test of REQ-011 MUST run on a confirmation slice frozen by sha256 before elimination starts and disjoint by prompt, fingerprint and normalized text from the elimination slice, so that no elimination result enters the test.

- SC-039: Given a confirmation slice sharing one prompt with the elimination slice, when selection is configured, then it is rejected.

#### REQ-035 — Family-wise error

When more than one challenger reaches the confirmation test, the tests MUST be adjusted by Holm over that family at the family-wise α of OD-16.

- SC-040: Given three challengers reaching confirmation with raw p-values 0.01, 0.03 and 0.04 at family-wise α 0.05 (Holm thresholds 0.0167, 0.025, 0.05), when the tests are adjusted, then Holm rejects only the first.

#### REQ-036 — Audit scored once per winner and incumbent

The audit set MUST be scored once for each selected winner and once for its incumbent, and its result MUST NOT be an input to a choice between runs, candidates or configurations.

- SC-041: Given a second audit scoring of the same winner, or an audit result passed to a choice between runs, when it is requested, then it is rejected.

#### REQ-037 — Stops, host changes and resume

A frozen protocol MUST pin the host version and model.

- (a) When the host or model at start differs from the pinned one, the runner MUST refuse the run before any rollout; the split MUST stay unspent, and the run MUST wait for a refreeze.
- (b) A held-out run MUST start only when the remaining quota estimate covers all its slots.
- (c) When a quota stop or a host or model change occurs during a run, the runner MUST stop the session and keep every completed rollout.
- (d) A resume MUST run only on the same frozen bytes and the same pinned host and model, after the runner compares the earlier session's A/A anchors with the new session's under OD-19; when the between-session anchor difference exceeds the OD-19 threshold, the runner MUST apply the OD-19 action (REQ-040).
- (e) A resume MUST fill exactly the unfilled (prompt, repetition) slots in their frozen order.
- (f) A resume MUST NOT rerun a completed slot or draw a new prompt.
- (g) When a host or model change blocks the resume of a held-out split, the run MUST be recorded as `invalidated`, and the split MUST be marked spent.
- (h) A spent split MUST NOT be rescored.
- (i) SPEC-091 MUST apply this rule unchanged.
- SC-042: Given a frozen protocol whose pinned host differs from the installed host, when a run is requested, then it is refused before any rollout and the split stays unspent.
- SC-043: Given a held-out run stopped by quota after which the host version changed, when a resume is requested, then it is rejected, the verdict is invalidated and the split is marked spent.
- SC-044: Given a run stopped by quota with the host unchanged, when it is resumed, then the runner first compares the earlier session's A/A anchors with the new session's under OD-19, only the missing slots run, in frozen order, and completed slots are untouched.
- SC-059: Given a held-out run whose remaining quota estimate covers fewer than all its slots, when it is requested, then the runner refuses before any rollout.
- SC-060: Given a split recorded as spent, when a second scoring of it is requested, then it is rejected.

#### REQ-038 — Gate A verdict

- (a) The gate A verdict MUST be `met` only when the passing-share lower bound, the all-fail upper bound and the class rule all hold; requiring every condition keeps a false `met` at or below α by the intersection–union principle.
- (b) The verdict MUST apply the precedence `invalidated` over `held` over `missed` and `met`.
- (c) An invalidating event MUST give `invalidated`.
- (d) Otherwise, an unreviewed 0/3 prompt, an unfilled slot or the OD-19 hold action (REQ-040) MUST give `held`.
- (e) Otherwise, the verdict MUST be `met` or `missed`.
- SC-045: Given a run with an unreviewed 0/3 prompt and a canary hit, when the verdict is computed, then it is invalidated.
- SC-046: Given a run whose lower bound and class rule hold but whose all-fail bound exceeds τ, when the verdict is computed, then it is missed.
- SC-061: Given a run with one unfilled slot and no invalidating event, and a second run with a session under the OD-19 hold action and no invalidating event, when each verdict is computed, then both are held.

#### REQ-039 — Development pilot freeze

A development pilot (T020) MUST run only after its protocol section, its prompts and the arms under test are frozen by sha256 on a `develop` commit; pilot prompts are development prompts and MUST NOT enter a held-out split, reserve, twin or audit set.

- SC-047: Given a pilot run whose prompt file hash differs from the pilot freeze, when it is requested, then it is rejected.

#### REQ-040 — A/A drift rule

When an A/A anchor difference exceeds the threshold of OD-19, the runner MUST apply the OD-19 action to that session before its results enter any decision: the hold action gives the verdict `held` until a re-baseline, and the invalidate action gives `invalidated` (REQ-038).

- SC-048: Given an A/A difference above the threshold, when the session closes, then the OD-19 action is applied and recorded.

#### REQ-041 — Selection stopping rule

Selection rounds MUST stop when one candidate survives or the OD-4 slice budget is spent; the OD-11 rule MUST leave at most the OD-7 maximum number of challengers, which then go to the confirmation test; the configurator MUST reject a quota cap that would leave the slice below its REQ-031 size rather than shrinking the slice, and there is no default: the owner chooses a smaller pool, a larger Δ or no selection (OD-4).

- SC-049: Given a session cap smaller than the sized slice, when selection is configured, then it is rejected with the needed size.

#### REQ-042 — Seeded partition of one pool

- (a) The split, the reserve and the twin of a gate MUST be drawn by a seeded random partition of one authored pool.
- (b) The freeze MUST record the seed.
- SC-050: Given an authored pool and a seed, when the partition is drawn twice, then both draws are identical and the three parts are disjoint and cover the pool.

#### REQ-043 — Product name in gate A items

The gate A builder MUST reject, with zero rollouts, any gate A item that does not name the product.

- SC-051: Given a gate A pool with one item lacking the product name, when the builder runs, then it rejects the pool before any rollout and names the item.

#### REQ-044 — Static Gate 0

Before the tripwire run, Gate 0 MUST score, with zero rollouts, the reference answer of every split prompt (all valid) and a rule-violating null baseline per class (gate not met), as SPEC-078 did.

- SC-052: Given a frozen split with its references and per-class null baselines, when static Gate 0 runs, then every reference is valid, every null baseline misses the gate, and no rollout is spent.

#### REQ-045 — Owner yes record

Every run that spends quota MUST have an owner yes record before its first rollout: a dated line in `specs/090-lightning-evaluation-v2/evidence/owner-yes.md` naming the specification, the task, the run and the frozen protocol hash, written by the owner; the runner MUST refuse a run whose record is missing or names another hash.

- SC-053: Given a frozen protocol with no matching owner yes line, when a run is requested, then the runner refuses before any rollout and names the missing record.

## Non-functional requirements

Operational and quality constraints, each with its source:

- Exactness: bounds are exact binomial (Clopper–Pearson) values computed without new dependencies;
  agreement with reference values to four decimals (REQ-002, REQ-003).
- Determinism: decisions replay bit-identically from a journal; seeds are recorded (REQ-016).
- Cost: simulations spend no quota; real runs use the subscription route at EUR 0 (REQ-017, REQ-022).
  Quota-spending tasks: T020 (pilot), T022 (Gate 0 run) and T017 (gate A run), each behind a freeze and
  the owner's yes.
- Estimated cost of the gate A noise pilot: 180 rollouts at the recommended OD-14 size (REQ-032); the
  actual count follows the OD-14 decision.
- Throughput: the runner stays sequential unless OD-6 says otherwise (REQ-018). At the observed 8.5 to
  17.9 s per rollout, 300 rollouts take about 43 to 90 minutes (SPEC-079 evidence).
- Sizes, α, margins and thresholds come from the owner decisions below; no value is assumed.

Budget from T001 to the gate A verdict, at the recommended OD values (no selection runs under this
specification; the gate A run on a SPEC-091 build is counted in SPEC-091):

| Task | Size | Rollouts | At 8.5 s | At 17 s (rounded from 16.4–17.9 observed) |
|---|---|---|---|---|
| T001–T016, T018, T019, T021, T023 | no rollouts | 0 | 0 | 0 |
| T020 gate A noise pilot | 20 prompts × 3 repetitions × 3 runs (OD-14), A/A pair included | 180 | 26 min | 51 min |
| T022 Gate 0 tripwire | twin 20 × 1 (OD-9) | 20 | 3 min | 6 min |
| T017 gate A run | 100 × 3 (OD-13) plus at most 3 reserve prompts × 3 (the OD-8 cap) | 309 | 44 min | 88 min |
| A/A anchors | 20 per session × 2 sessions, T022 and T017 (OD-20); the pilot's A/A pair is inside OD-14 | 40 | 6 min | 11 min |
| **Total** | | **549** | **1.3 h** | **2.6 h** |

The SPEC-091 table gives the gate B budget and the combined total.

## Security and privacy

- The 0/3 review record MUST contain only SPEC-074-redacted transcripts, so no personal data or secret enters it (REQ-030).
- A run MUST NOT read or accept a provider API key or other secret (REQ-022).
- A gate MUST NOT promote a candidate; `executionAuthorization` stays false (REQ-025).
- Frozen records and spent sets stay untouched (REQ-020, REQ-024, REQ-028).

## Terminology

- **Gate A:** the authoring-validity gate over prompts that name the product (REQ-001 to REQ-007).
- **Gate B:** the unprompted-invocation gate of SPEC-091.
- **Passing prompt:** at least 2 of 3 `validFirstAttempt` repetitions (REQ-001).
- **p:** a prompt's per-repetition probability of a valid first attempt (REQ-001 to REQ-003).
- **All-fail rate θ:** E[(1−p)³] over the prompt population, estimated by the 0/3 count (REQ-003).
- **Margin δ and target advantage Δ:** δ is the advantage above which a challenger replaces the
  incumbent; Δ > δ is the true advantage at which the slice is sized for power (REQ-009, REQ-011).
- **Reserve:** prompts frozen with a split, used in a preregistered order to replace `instrument`
  prompts (REQ-005).
- **Slice:** the fixed prompts and repetitions on which all candidates are compared (REQ-008).
- **Discordance:** the share of prompts (unit: prompt) on which two arms' majority-pass outcomes differ
  (REQ-009).
- **r\*:** repetitions per elimination-slice prompt, max(1, round(√((c_p/c_r)(1−ρ)/ρ))), with c_p/c_r the measured cost
  ratio of authoring a prompt to running a rollout (REQ-009, REQ-032).
- **Re-baseline:** rerunning the A/A pair and the twin on a new host or model; if any pilot estimate leaves
  its recorded interval, sizing reruns before the next freeze (REQ-013).
- **Confirmation slice:** a frozen slice disjoint from the elimination slice, used only for the
  replacement test (REQ-034).
- **ε-good:** within ε of OD-3 of the best candidate's per-prompt majority-pass share (H1, SC-012).
- **Shipped build:** the released plugin build at freeze time (tool, skill and server bytes, named by
  commit and digests). **Incumbent:** the artifact selection compares against, the shipped build unless a
  protocol names another; kept unless a challenger meets the margin (REQ-011). **Challenger:** a candidate
  compared with the incumbent.
- **Elimination slice:** the slice on which challengers are screened (REQ-008).
- **Missing result:** a rollout that ran but returned no parseable outcome; it counts as a failed
  repetition (REQ-001). **Unfilled slot:** a (prompt, repetition) not yet run after a stop; it gives `held`
  until a resume fills it (REQ-037, REQ-038). **OD-19 hold action:** the A/A drift action that gives `held`
  until a re-baseline (REQ-040).
- **Canary:** the SPEC-071 planted token (`CANARY_TOKEN` in `agent_braid/lightning_hosts.py`); its
  appearance in a rollout transcript is a canary hit.
- **Invalidating event**, allowed values: canary hit; replacement cap exceeded; host or model change before
  the reserve run; host or model change that blocks a held-out resume; the OD-19 invalidate action
  (REQ-005, REQ-037, REQ-038, REQ-040).
- **Owner yes record:** the dated line of REQ-045.
- **Audit set:** items never read by selection, used to report the winner and its incumbent (REQ-012,
  REQ-036).
- **A/A anchor:** the same arm run twice in a session to measure drift (REQ-013).
- **Development twin:** a development set built like a held-out split, used by the Gate 0 tripwire
  (REQ-015).
- **Zero-prompt classes**, allowed values: `model`, `instrument` (REQ-004).
- **Gate verdicts**, allowed values: `met`, `missed`, `held`, `invalidated`; precedence `invalidated` >
  `held` > `missed` and `met` (REQ-038).
- **Repetition outcomes**, allowed values: valid, invalid, missing; missing counts as invalid (REQ-001).
- **Hypothesis outcomes**, allowed values: supported, not supported, inconclusive (T018).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Scientific boundaries and compatibility

Hypotheses (preregistered in [evaluation-protocol.md](evaluation-protocol.md); none is a completion
condition; all are about procedures under simulation, not about models):

- **H1** — Paired selection on one fixed slice picks an ε-good candidate (ε of OD-3) more often than independent means on n = 5 (simulation).
- **H2** — The exact all-fail bound has at least nominal coverage (simulation).
- **H3** — Gate A's type I error at the 0.80 boundary is at most α (simulation).

Domain: statistical procedures and their simulated behaviour; real runs are one host
(`claude-code`), one pinned model and one split each. Observation contract: unchanged SPEC-069 scorer
outcomes, per-prompt majority pass, exact bounds, paired differences. Execution contract: simulations
only, except T020 (pilot freeze and owner yes), T022 and T017 (T016 freeze and owner yes). Compatibility: new modules; SPEC-078 and SPEC-079 analysis and
records are unchanged; existing configurations keep `parallel` 1 and `target.kind` `skill`.

Real-run order, the same in ADR 0046, SPEC-090 and SPEC-091: the gate A noise pilot (SPEC-090 T020) and,
independently and in either order, the gate B noise pilot (SPEC-091 T008) and development factorial
(SPEC-091 T009); then lever screening (SPEC-091 T018) and the 2×2 factorial (SPEC-091 T012); then gate B
selection (SPEC-091 T019) only when SPEC-091 OD-20 requires it, and the same-build gate A run
(SPEC-091 T023) whenever the arm under test changes the description, server instructions, `_meta` or the
hook; then SPEC-091 T021 and T015. SPEC-090 T022 and T017 depend only on SPEC-090 T016 and may run at any
point after it. SPEC-091 T016 may run at any point after its own freeze. Each run MUST be behind its own
freeze and owner yes record (SPEC-090 REQ-017, SPEC-090 REQ-045, SPEC-091 REQ-045).

Multiplicity: each gate is conjunctive (gate A: lower bound, all-fail bound and class rule), so a false
`met` stays at or below α by the intersection–union principle without adjustment (REQ-038); selection
over several challengers is adjusted by Holm at the OD-16 family-wise α (REQ-035).

Limits: prompts are templated, so independence across prompts is an assumption a simulation cannot
remove; the cost ratio behind three repetitions is an assumption the noise pilot measures; cited
preprints are leads.

## Evidence and unresolved questions

Planned and obtained evidence are kept in `assurance.json`; none is obtained. Inputs already in the
repository: the SPEC-079 T008 report and diagnosis, and the within-prompt correlations of v2 (0.52), v3
(0.41) and v4 (0.81), which are ANOVA estimates (ICC) from per-prompt pass counts.

## Owner decisions (open)

Open questions: OD-1 to OD-21. Each has options, a recommendation and its evidence, or says plainly that no
evidence exists; none is decided. Parameters inherited from SPEC-078 OD-1 and the approved strategy (the
2-of-3 majority, 3 repetitions and the 0.80 threshold) are not reopened.

- **OD-1 — α.** Options: one-sided 0.05; 0.025; 0.10. Evidence: SPEC-078 OD-1 says "95 %" but Wilson with
  z = 1.96 is a one-sided 97.5 % bound. With the exact Clopper–Pearson bound at α = 0.05, 87/100 already
  passes (0.8013), one prompt fewer than the SPEC-078 Wilson gate (88/100); at α = 0.025, 88/100 gives
  0.7998 and 89/100 is needed (0.8117) (own calculation). The owner is choosing whether to loosen the gate
  by one prompt (0.05) or keep it one prompt stricter (0.025). Recommendation: 0.05 for each gate component;
  the conjunctive verdict keeps a false `met` at or below α (REQ-038). The family-wise α for selection is
  OD-16.
- **OD-2 — All-fail threshold τ.** The 0/3 count is Binomial(n, θ), so the earlier rule "no prompt is 0/3"
  is itself an all-fail test: at α = 0.05 and n = 100 it equals τ in [0.0295, 0.0466), since 0, 1, 2 and 3
  zero-prompts give exact upper bounds 0.0295, 0.0466, 0.0616 and 0.0757 (own calculation). Choosing τ is
  therefore knowingly keeping or loosening that rule. Options: (a) τ in [U(0), U(1)), where U(k) is the
  exact upper bound for k zero-prompts at the OD-1 α and the OD-13 n: [0.0295, 0.0466) at α 0.05,
  [0.0362, 0.0545) at 0.025, [0.0228, 0.0383) at 0.10, n = 100 (own calculation); the owner records one
  number; this keeps the rule (one 0/3 prompt fails the gate); (b) τ = 0.05, which tolerates one 0/3 prompt
  in 100 at α 0.05 and 0.10 and none at 0.025, where U(0) = 0.0362 and U(1) = 0.0545. Options at or
  above 0.075 were removed: at α 0.05, on v3 data (two 0/3 prompts, bound 0.0616) they return `met`, and from 0.0757 on
  v2 data (three, bound 0.0757) too, with the deterministic `units` defect present. Trade-off: (a) detects a defect affecting even one prompt in 100
  but fails a sound arm whenever one prompt is unlucky; (b) halves that false alarm at the cost of missing
  a defect confined to a single prompt. Evidence: the v2 and v3 0/3 prompts were real defects, reviewed as
  `model`. Recommendation: (a); confirm with T005.
- **OD-3 — Margin δ, target advantage Δ and ε.** All three are in majority-pass share, the unit of the
  confirmation test; elimination has no power target (REQ-009). Options for δ: 0, 0.02, 0.05; for Δ: δ + 0.05
  or δ + 0.10; for ε, the tolerance of "ε-good" (within ε of the best candidate): ε = δ or ε = Δ − δ.
  Evidence: the replacement test rejects "advantage ≤ δ", so its power at a true advantage of exactly δ
  equals α. Confirmation prompts per arm from the plan.md formula at 80 % power and the Holm worst case
  0.05/3 (own calculation), at δ = 0.02 with a = Δ: discordance 0.10 gives 336 prompts at Δ − δ = 0.05 and 76 at
  0.10; discordance 0.30 gives 1,041 and 252. Small gaps are therefore unaffordable unless the pilot's discordance is low.
  Recommendation: δ = 0.02, Δ = δ + 0.10 and ε = δ, revised after the gate A noise pilot.
- **OD-4 — Power and slice budget.** Options: 80 % or 90 % power; a per-session quota cap or none; and,
  when the sized budget exceeds the cap, no default: the owner chooses (i) a smaller pool, (ii) a larger Δ
  or (iii) no selection (REQ-041). Evidence: no pilot exists yet, so no slice size can be computed; a
  5-prompt slice is underpowered (REQ-031). Recommendation: 80 %, one five-hour quota window as the cap,
  and the choice among (i) to (iii) made when the sizes are known. Choosing no cap changes REQ-009: the
  elimination slice size is then no longer the budget share left after confirmation, and the owner records it.
- **OD-5 — Audit set size.** Options: 128 items; 64. Evidence: the winner's-curse bias removal has RMSE
  near 4.5 points at 128 items and near 6 at 64 (2610.09239, lead); the exact 95 % interval at p ≈ 0.85 is
  about 0.78 to 0.91 at 128 items (about ±6.5 points) and about 0.73 to 0.92 at 64 (about ±9.5) (own
  calculation). Recommendation: 128, authored and frozen in T021.
- **OD-6 — `parallel` above 1.** Options: keep 1; implement up to 2; up to 4. Evidence: the runner is
  sequential (`agent_braid/lightning_runner.py`, header comment) though the configuration accepts more;
  concurrency effects on quota and host behaviour are unmeasured. Recommendation: keep 1 for gates;
  revisit for development runs after A/A anchors.
- **OD-7 — Candidate pool size and challengers admitted to confirmation.** Options: 5, 10 or 20 candidates
  per selection; and the maximum number of challengers admitted to confirmation: 1, 3 or 5. Evidence: the
  review proposes 5 to 20 from one to three contrastive rewrites; for the maximum there is no evidence
  beyond the sizing arithmetic, which divides the OD-16 α by it (REQ-009; the OD-3 figures use 3).
  Recommendation: at most 10 candidates until T006 shows the slice can separate more, and a maximum of 3
  challengers admitted to confirmation (REQ-041).
- **OD-8 — Reserve size and replacement cap.** Options: reserve of 5 or 10 prompts; cap of 2, 3 or 5
  replacements per 100 prompts. Evidence: v2 and v3 had two or three 0/3 prompts each, all reviewed as
  `model`, so `instrument` findings are expected to be rare; v4's 79 0/3 prompts reflected an invocation
  collapse, not instrument defects, and do not support a large cap; a large cap lets replacement reshape
  the split after seeing outcomes. Recommendation: reserve 5, cap 3.
- **OD-9 — Gate A tripwire: twin size and margin.** Options: twin of 20 or 40 product-naming prompts × 1
  repetition; margin 0.10 or 0.20 below the T020 invocation rate of the shipped-build arm. The gate B threshold is separate
  (SPEC-091 OD-22): unprompted invocation was 53/300 (0.18) on v4, so one threshold would refuse every
  gate B split. Evidence: about 20 prompts and a few minutes would have exposed the T008 collapse; on v3,
  with the product named, 294 of 300 rollouts called `analyze-work` (repo), so a twin of 20 at a 0.10
  margin leaves room for noise. Recommendation: 20 × 1, margin 0.10.
- **OD-10 — Milestone.** Options: BL.2c (provisional, used in tracking now); a new BL milestone created
  by the owner. Evidence: no milestone for Lightning evaluation exists in `github-tracking.json`.
  Recommendation: a new milestone; tracking moves after it exists.
- **OD-11 — Elimination rule and confirmation test.** Elimination options: synchronized successive
  halving; SySRs; paired racing. Confirmation test options: (a) a one-sided exact unconditional test of the
  paired majority-pass difference against δ, maximizing the p-value over the nuisance discordance
  (Berger–Boos style), exact for any δ ≥ 0; (b) a sign-flip permutation test on the per-prompt
  majority-pass difference minus δ, which is exact only when those differences are symmetric about δ under
  the null; per-prompt differences take only the values −1, 0 and 1, so that holds at δ = 0 and not for
  δ > 0, where the test is approximate and its size is checked in T006; (c) the exact conditional McNemar
  test, only when δ = 0. Evidence: none has been compared under this noise model (SySRs was shown on
  deterministic scores only). Recommendation: decide from T006; prior choice synchronized halving with (a).
- **OD-12 — Sequential prompt-level gate.** Options: fixed sample only; a sequential version with a
  prefixed random order, admissible only if a sequential exact bound and its simulation are added to this
  specification first, because it invalidates the fixed-n bounds of REQ-002 and REQ-003 and their
  simulations. Evidence: the review estimates 35 to 45 % fewer prompts (lead, not verified here).
  Recommendation: fixed sample.
- **OD-13 — Gate A split size and class plan.** Options: 100 prompts as in SPEC-078 and SPEC-079; a size
  from power. Evidence: comparability with the OD-1 arithmetic. Recommendation: 100, class plan written
  in T016. Choosing a size from power changes the arithmetic stated at n = 100: the OD-1 and OD-2 figures
  and the worked values of SC-002 and SC-004 no longer describe the gate split and are recomputed.
- **OD-14 — Gate A noise pilot size.** Options: 20 fresh product-naming prompts × 3 repetitions × 3 runs
  (the two OD-21 arms, plus one repeated run of the shipped build for the A/A pair): 180 rollouts; 40
  prompts (360). Evidence: within-prompt correlation (ANOVA ICC of per-prompt pass counts) ranged 0.41 to
  0.81 on v2 to v4, so each endpoint needs its own pilot. Recommendation: 20 prompts.
- **OD-15 — Tolerance under clustering and fallback.** Options: accept the exact bounds when simulated
  coverage under the clustered scenario stays within 0.01 of 1 − α, or within 0.02; otherwise a fallback:
  (a) a class-level resampling bound, only with at least 10 classes; (b) a design-effect-adjusted exact
  bound with effective size n / (1 + (m − 1)ρ_class), where m is the mean number of prompts per class and
  ρ_class the between-class intraclass correlation of prompt pass outcomes. Evidence: exact bounds hold by
  construction only for independent prompts; v4 had 7 classes, too few for (a). Recommendation: tolerance
  0.01; fallback (b), with (a) only when there are at least 10 classes.
- **OD-16 — Family-wise α for selection.** Options: 0.05 with Holm over the challengers reaching
  confirmation; 0.10 with Holm. Sizing uses the Holm worst case, this α divided by the number of
  challengers admitted to confirmation (OD-7, REQ-009). The option "a single surviving challenger only" was
  removed: it conflicts with REQ-035 and REQ-041 when several survive. Evidence: several challengers
  (OD-7) would inflate a false replacement without adjustment. Recommendation: 0.05 with Holm.
- **OD-17 — Arm under test in T016 and T017.** Options: (a) the build shipped at freeze time (current tool
  and skill); (b) a build proposed under SPEC-091 REQ-038 (same-build certification) on a fresh gate A
  split; (a) then (b). The option "the winner of a selection run" was removed: no task in this
  specification runs a gate A selection. Evidence: none yet. Recommendation: (a) now, (b) when SPEC-091
  proposes a build, each named by plugin commit and artifact digests in its frozen protocol.
- **OD-18 — Instrument safeguards.** REQ-005 already counts every replaced prompt as 0/3 in the verdict,
  so the former option "report both bounds with replaced prompts counted as failures" is now mandatory and
  removed as an option. Options: (a) an outcome-blind validity review of every split and reserve prompt
  before measurement; (b) a preregistered random sample of passing prompts reviewed with the 0/3 prompts.
  Evidence: only 0/3 prompts are reviewed today, from transcripts that show the outcome. Recommendation:
  (a); (b) when the owner's review time allows.
- **OD-19 — A/A drift threshold and action.** Options: threshold: the two-sided exact paired bound on the
  A/A difference in per-rollout valid rate excludes zero at the OD-1 α, or the absolute difference exceeds
  0.10 or 0.20; action: hold the session's results and require a re-baseline, or invalidate the session. Evidence: no A/A data exist yet in this repository.
  Recommendation: bound excludes zero; hold and re-baseline. During held-out runs anchors use development
  prompts only (REQ-013).
- **OD-20 — A/A anchor size.** Options: 10 or 20 development prompts × 1 repetition × 2 runs per session.
  Evidence: no A/A data exist yet; 20 prompts give 40 rollouts, about 6 to 12 minutes per session at the
  observed 8.5 to 17.9 s per rollout. Recommendation: 10 prompts (20 rollouts per session).
- **OD-21 — Pilot arms.** No candidate exists before any selection, so the pilot's "two candidate arms"
  need a definition. Options: (a) the shipped build and one named variant (for example the skill body
  with its first example removed), digests frozen in the pilot freeze; (b) the shipped build twice only
  (A/A, no discordance estimate). Evidence: the slice formula needs a paired discordance between two
  different arms (REQ-009). Recommendation: (a), with the variant named by the owner at T001. Choosing (b)
  removes the discordance and paired-difference estimates of REQ-032, so REQ-009 cannot size a
  confirmation slice.

## Risks and assumptions

- Risk: templated prompts are clustered, so prompt independence is optimistic (REQ-002, REQ-003, T004).
- Risk: the simulation model omits a real noise source, such as host drift within a session
  (REQ-013, T006).
- Risk: the replacement reserve turns a bad split into a new split (REQ-005, OD-8).
- Risk: three repetitions are not optimal if prompt cost differs from the assumed 6 to 10 rollouts
  (REQ-007, REQ-032).
- Risk: changing the GEPA and APO selection steps alters SPEC-072 replay (REQ-019, T014).
- Assumption: repetitions are independent given p, a prompt's per-repetition probability of a valid
  first attempt (REQ-003); template clustering across prompts is simulated, not assumed away (REQ-033).
- Assumption: the SPEC-069 scorer and fixture workspace are reused unchanged (REQ-001, REQ-020).
- Assumption: the gate A noise pilot runs in the current laboratory before sizing (REQ-032, T020).

## Exit criteria

Verification is complete when the [validation plan](validation-plan.md) has obtained evidence for every SC
whose owning task ran; a conditional task not run is recorded with the owner decision that skipped it; the
simulation record (T004 to T007) is committed, the protocol is frozen (T016), and the T018 converge record
is written. A negative simulation result, a
missed gate or an inconclusive run is a valid completion when recorded. Passing checks are not approval.

## Open questions

- OD-1 to OD-21 above; owner: the founder.
- Whether the gate A real run (T017) happens at all; owner: the founder.
