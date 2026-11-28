# Feature specification: SPEC-090 — Lightning evaluation v2: statistical machinery and gate A

**Milestone:** provisional, BL.2c — Lightning tool-level kind-choice fix (OD-10).
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
support: a Wilson bound read as a 95 % bound, a "no prompt is 0/3" rule that is not an identified
functional, top-k selection on independent means of five cases, and no audit of the winner.

This is engineering plus a research protocol:

- Engineering: exact bounds and the all-fail bound (REQ-001 to REQ-007); paired, synchronized selection
  with an incumbent margin and an audit set (REQ-008 to REQ-012, REQ-019, REQ-027); drift controls, run metadata,
  a Gate 0 invocation tripwire and replayable decisions (REQ-013 to REQ-016); runner concurrency kept
  behind an owner decision (REQ-018).
- Research: simulation tests of the procedures before any real run (REQ-017; H1 to H3), then a
  preregistered gate A split (T016) whose run is a separate owner decision.

Out of scope, each stated as a requirement: frozen SPEC-069, SPEC-078 and SPEC-079 records (REQ-020) and
any retroactive use of the new gate on v4 (REQ-028); the Wilson verdict (REQ-026); adaptive allocation, including Thompson Sampling, in
held-out or audit data (REQ-021); provider keys and other secrets (REQ-022); LLM judges (REQ-029); a non-identified gate
quantity (REQ-023); spent sets as a gate A held-out split (REQ-024); automatic promotion (REQ-025).
Not covered here at all: gate B, item labels, the invocation lab and its levers, the optimizer target
extension and the pilots, which are SPEC-091; weight training (ADR 0042, deferred); hosts other than
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
- **OD-B1 (2026-11-27).** Gate B items are labelled before measurement; it binds SPEC-091 and is
  recorded there.
- Every numeric parameter below is open (Owner decisions). None is filled in.

## Requirements and acceptance scenarios

- **REQ-001 — Gate A unit and outcome.** Gate A MUST score prompts that name the product. The unit is the prompt; a prompt passes when at least 2 of its 3 repetitions are `validFirstAttempt` under the unchanged SPEC-069 scorer, giving one binary result per prompt. A missing rollout result counts as a failed repetition.
  - SC-001: Given a prompt with repetition outcomes valid, valid, invalid, when the gate A analysis scores it, then the prompt passes; with valid, invalid, missing it fails.
- **REQ-002 — Exact lower bound on the passing share.** Gate A MUST report the exact one-sided Clopper–Pearson lower bound of the passing share at the α of OD-1. The pass threshold for the bound is 0.80, inherited from SPEC-078 OD-1.
  - SC-002: Given 88 passing prompts of 100 and α = 0.05, when the bound is computed, then it equals the exact Clopper–Pearson value 0.8128 to four decimals .
  - SC-003: Given a candidate pool with known pass probabilities and the measured within-prompt correlation, when the gate is simulated (SIM), then its type I error at the boundary does not exceed α within simulation error and its power is reported.
- **REQ-003 — All-fail upper bound.** Gate A MUST report the exact one-sided Clopper–Pearson upper bound of the all-fail rate θ = E[(1−p)³], estimated by the count of prompts with 0 of 3 valid repetitions, together with its comparison against the preregistered threshold of OD-2. The rule "no prompt is 0/3" is not used for splits frozen under this specification.
  - SC-004: Given 2 prompts at 0/3 out of 100 and α = 0.05, when the bound is computed, then it equals 0.0616 to four decimals.
  - SC-005: Given prompt populations with known θ, when the bound is simulated (SIM), then its coverage is at least 1 − α within simulation error for every θ in the grid.
- **REQ-004 — Review of each 0/3 prompt.** Each prompt at 0/3 MUST be held until the owner classifies it as `model` or `instrument` on redacted transcripts; disagreements are recorded verbatim. The verdict is `held` while any 0/3 prompt is unreviewed.
  - SC-006: Given a run with one unreviewed 0/3 prompt, when the gate A analysis runs, then the verdict is held and names the prompt.
- **REQ-005 — Instrument replacement from a frozen reserve.** For a split frozen under this specification, a prompt classified `instrument` MUST be replaced by the next prompt of a reserve frozen by sha256 with the split, in a preregistered draw order, up to the cap of OD-8; the replaced prompt and its results stay in the record. Exceeding the cap invalidates the run. SPEC-079, where `instrument` invalidates the run, is unchanged.
  - SC-007: Given two instrument findings and a cap of three, when replacement runs, then the first two reserve prompts in frozen order replace them and both originals stay in the report.
  - SC-008: Given instrument findings above the cap, when replacement runs, then the verdict is invalidated.
- **REQ-006 — Class rule.** Gate A MUST also require that every class of the split has at least half of its prompts passing.
  - SC-009: Given a class with 4 of 10 prompts passing, when the gate A analysis runs, then the gate is not met whatever the bounds.
- **REQ-007 — Three repetitions.** Gate A MUST use 3 repetitions per prompt. A different number needs a new owner decision recorded before the split is frozen.
  - SC-010: Given a protocol declaring 2 repetitions without a recorded decision, when the freeze check runs, then it refuses.
- **REQ-008 — Paired comparison on one fixed slice.** Candidate selection MUST decide on per-prompt paired differences, averaged over repetitions, with every surviving candidate evaluated on the same fixed slice of prompts and repetitions; independent means are never the decision statistic.
  - SC-011: Given two candidates and a slice, when selection runs, then both are scored on identical prompt and repetition identifiers and the decision statistic is computed from paired differences.
  - SC-012: Given known-p candidates with the within-prompt correlation of the noise pilot, when paired selection and n = 5 independent means are simulated (SIM), then paired selection picks an ε-good candidate at a rate at least as high as n = 5, reported with its simulation interval.
- **REQ-009 — Slice sized from the pilot.** The slice size MUST come from the SPEC-091 noise pilot (variance of paired differences, discordance rate) through the formula in plan.md, at the α, power and margin of OD-1, OD-3 and OD-4.
  - SC-013: Given pilot variance, α, power and margin, when the sizing function runs, then it returns the documented formula value .
- **REQ-010 — Synchronized elimination.** Elimination MUST be synchronized: in each round all surviving candidates see the same new items. The elimination rule is the one the owner picks in OD-11 after the simulation comparison.
  - SC-014: Given three candidates in a round, when elimination runs, then all three receive the same item identifiers before any is dropped.
- **REQ-011 — Incumbent kept unless the margin is met.** The incumbent MUST be kept unless a challenger beats it by the preregistered margin of OD-3 under the test of OD-11 at the selection α of OD-1.
  - SC-015: Given a challenger whose paired advantage is below the margin, when selection decides, then the incumbent is kept.
- **REQ-012 — Audit set.** An audit set of the size of OD-5 MUST be frozen by sha256, disjoint by normalized text and fingerprint from every selection slice, development set and held-out split. The selected candidate is reported on it with an exact confidence interval.
  - SC-016: Given a selection run, when its inputs are traced, then no audit item identifier appears in any selection input.
- **REQ-013 — Drift controls.** Every real run under this specification MUST pin the host CLI version with auto-update off and the model; record the host, model and plugin versions per rollout; include A/A anchors each session; interleave arms in randomized blocks with a recorded seed; and require a new baseline after any host or model change.
  - SC-017: Given a host version change between two sessions, when the run continues, then it stops with a re-baseline required refusal.
  - SC-018: Given a session, when arms are scheduled, then the block order is reproducible from the seed and contains the A/A anchors.
- **REQ-014 — Run metadata.** Run reports MUST carry `configDigest`, per-rollout host CLI, model and plugin versions, the tool-call count and whether the skill was invoked.
  - SC-019: Given a recorded rollout, when the report is built, then every listed field is present and a missing field fails the report.
- **REQ-015 — Gate 0 invocation tripwire.** Gate 0 of every split frozen under SPEC-090 or SPEC-091 MUST reject the held-out run when the invocation rate on a development twin is below the preregistered threshold of OD-9.
  - SC-020: Given a twin run whose invocation rate is below the threshold, when Gate 0 evaluates the tripwire, then it fails and the held-out run is refused.
- **REQ-016 — Replayable decisions.** Every selection and gate decision MUST be a pure function of a journal (results, seeds, frozen hashes); replaying a journal gives an identical decision.
  - SC-021: Given a recorded journal, when it is replayed twice, then both decisions and their hashes are identical.
- **REQ-017 — Simulation before any real run.** The runner MUST reject a real run under this specification whose protocol lacks the hash of the recorded simulation evidence of T004 to T007 or the owner's recorded yes.
  - SC-022: Given a protocol without the simulation record hash, when a run is requested, then the runner refuses before any rollout.
- **REQ-018 — Runner concurrency.** The runner MUST reject a `parallel` value above 1 unless the owner adopts concurrency in OD-6; if adopted, A/A anchors measure the effect and a decision replay is identical for any `parallel` value.
  - SC-023: Given a configuration with parallel 2 and no recorded OD-6 adoption, when the run starts, then it refuses.
- **REQ-019 — Optimizer selection steps.** The GEPA and APO selection steps (`agent_braid/lightning_gepa.py`, `agent_braid/lightning_apo.py`) MUST use the paired selection of REQ-008 to REQ-011 for splits under this specification; their candidate target stays the skill body.
  - SC-024: Given a GEPA round over three candidates, when its survivors are chosen, then the choice comes from the paired selection module and not from a top-k mean.
- **REQ-020 — Frozen records untouched.** This specification MUST NOT edit the SPEC-069 scorer or prompt sets, the SPEC-078 or SPEC-079 splits, protocols or FREEZE files.
  - SC-025: Given the diff of every task, when the boundary test runs, then no frozen path changed.
- **REQ-021 — No adaptive allocation in frozen data.** Held-out and audit data MUST NOT be collected with adaptive allocation, including Thompson Sampling.
  - SC-026: Given a held-out or audit run configuration, when it is validated, then any allocation other than the fixed uniform schedule is refused.
- **REQ-022 — Cost and route.** A run MUST NOT read or accept a provider API key or other secret; it uses the subscription route at EUR 0 only.
  - SC-027: Given a rollout environment holding a provider key variable, when the run starts, then it is rejected before any rollout, as SPEC-071 does, and the key value appears in no record.
- **REQ-023 — No non-identified gate quantity.** Gate A MUST NOT report a share of prompts with pass probability below a threshold as a gate quantity.
  - SC-028: Given a gate report, when its fields are listed, then no such quantity appears.
- **REQ-024 — Fresh gate A held-out split.** Gate A under this specification MUST use a fresh split: one that shares no prompt, fingerprint or normalized 8-word window with the spent v2, v3 or v4 sets.
  - SC-029: Given a candidate split that shares a normalized 8-word window with v2, v3 or v4, when the builder checks it, then it refuses.
- **REQ-025 — Human promotion.** A gate A pass MUST NOT promote a candidate; promotion stays human under SPEC-073 with SPEC-049 noninferiority.
  - SC-030: Given a passed gate, when its outputs are read, then no promotion pointer changes and `executionAuthorization` is false.
- **REQ-026 — No Wilson verdict.** Gate A MUST NOT use the Wilson interval as its verdict statistic (split from REQ-002).
  - SC-031: Given a gate A report, when its verdict inputs are listed, then only the exact bounds of REQ-002 and REQ-003 and the class rule appear.
- **REQ-027 — Audit set not read by selection.** Selection MUST NOT read any audit set item (split from REQ-012).
  - SC-032: Given a selection call given an audit item identifier, when it runs, then it is rejected.
- **REQ-028 — No retroactive gate.** The gate A rules of this specification MUST NOT be applied to the SPEC-079 v4 run or any split frozen before this specification (split from REQ-020).
  - SC-033: Given the SPEC-079 v4 run directory, when the gate A analysis is invoked on it, then it is rejected as out of scope.
- **REQ-029 — No LLM judge.** A run MUST NOT use an LLM judge as a reward, label or gate source (split from REQ-022).
  - SC-034: Given a reward configuration naming a model-graded component, when it is validated, then it is rejected.
- **REQ-030 — Redacted review records.** The 0/3 review record MUST contain only transcripts redacted under SPEC-074, so that no unredacted prompt, file content, personal data or secret enters it.
  - SC-035: Given a review record built from a transcript holding a planted secret marker, when it is saved, then the marker appears nowhere in the record.
- **REQ-031 — Minimum testable slice.** The sizing function MUST reject a slice smaller than the least size at which the OD-11 exact test can reach the selection α; a slice of 5 prompts is below it for a two-sided exact McNemar test at 0.05 (split from REQ-009).
  - SC-036: Given a requested slice of 5 prompts at α = 0.05 two-sided, when the sizing function runs, then it is rejected with the minimum size in the message.

## Non-functional requirements

Operational and quality constraints, each with its source:

- Exactness: bounds are exact binomial (Clopper–Pearson) values computed without new dependencies;
  agreement with reference values to four decimals (REQ-002, REQ-003).
- Determinism: decisions replay bit-identically from a journal; seeds are recorded (REQ-016).
- Cost: simulations spend no quota; real runs use the subscription route at EUR 0 (REQ-017, REQ-022).
- Throughput: the runner stays sequential unless OD-6 says otherwise (REQ-018). At the observed 8.5 to
  17.9 s per rollout, 300 rollouts take about 43 to 90 minutes (SPEC-079 evidence).
- Sizes, α, margins and thresholds come from the owner decisions below; no value is assumed.

## Security and privacy

- The 0/3 review record MUST contain only SPEC-074-redacted transcripts, so no personal data or secret enters it (REQ-030).
- A run MUST NOT read or accept a provider API key or other secret (REQ-022).
- A gate MUST NOT promote a candidate; `executionAuthorization` stays false (REQ-025).
- Frozen records and spent sets stay untouched (REQ-020, REQ-024, REQ-028).

## Terminology

- **Gate A:** the authoring-validity gate over prompts that name the product (REQ-001 to REQ-007).
- **Gate B:** the unprompted-invocation gate of SPEC-091.
- **Passing prompt:** at least 2 of 3 `validFirstAttempt` repetitions (REQ-001).
- **All-fail rate θ:** E[(1−p)³] over the prompt population, estimated by the 0/3 count (REQ-003).
- **Reserve:** prompts frozen with a split, used in a preregistered order to replace `instrument`
  prompts (REQ-005).
- **Slice:** the fixed prompts and repetitions on which all candidates are compared (REQ-008).
- **Incumbent:** the current artifact; kept unless a challenger meets the margin (REQ-011).
- **Audit set:** items never read by selection, used to report the winner (REQ-012).
- **A/A anchor:** the same arm run twice in a session to measure drift (REQ-013).
- **Development twin:** a development set built like a held-out split, used by the Gate 0 tripwire
  (REQ-015).
- **Zero-prompt classes**, allowed values: `model`, `instrument` (REQ-004).
- **Gate verdicts**, allowed values: `met`, `missed`, `held`, `invalidated` (REQ-004, REQ-005).
- **Repetition outcomes**, allowed values: valid, invalid, missing; missing counts as invalid (REQ-001).
- **Hypothesis outcomes**, allowed values: supported, not supported, inconclusive (T018).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Scientific boundaries and compatibility

Hypotheses (preregistered in [evaluation-protocol.md](evaluation-protocol.md); none is a completion
condition; all are about procedures under simulation, not about models):

- **H1** — Paired selection on one fixed slice picks an ε-good candidate more often than independent
  means on n = 5.
- **H2** — The exact all-fail bound has at least nominal coverage.
- **H3** — Gate A's type I error at the 0.80 boundary is at most α.

Domain: statistical procedures and their simulated behaviour; real runs are one host
(`claude-code`), one pinned model and one split each. Observation contract: unchanged SPEC-069 scorer
outcomes, per-prompt majority pass, exact bounds, paired differences. Execution contract: simulations
only until T016 and the owner's yes. Compatibility: new modules; SPEC-078 and SPEC-079 analysis and
records are unchanged; existing configurations keep `parallel` 1 and `target.kind` `skill`.

Limits: prompts are templated, so independence across prompts is an assumption a simulation cannot
remove; the cost ratio behind three repetitions is an assumption the noise pilot measures; cited
preprints are leads.

## Evidence and unresolved questions

Planned and obtained evidence are kept in `assurance.json`; none is obtained. Inputs already in the
repository: the SPEC-079 T008 report and diagnosis, and the within-prompt correlations of v2 (0.52), v3
(0.41) and v4 (0.81), which are ANOVA estimates from per-prompt pass counts.

## Owner decisions (open)

Open questions: OD-1 to OD-13. Each has options, a recommendation and its evidence; none is decided.

- **OD-1 — α.** Options: one-sided 0.05; 0.025; 0.10; separate α for selection. Evidence: SPEC-078 OD-1
  says "95 %" but Wilson with z = 1.96 is a one-sided 97.5 % bound; at α = 0.05, 88/100 gives an exact
  lower bound of 0.8128 (own calculation). Recommendation: 0.05 one-sided for gate A; the selection α is
  set from the T006 simulation.
- **OD-2 — All-fail threshold τ.** Options: 0.05 (at α = 0.05 tolerates one 0/3 prompt in 100: bound
  0.0466); 0.075 (tolerates two: 0.0616); 0.10 (tolerates four: 0.0892). Evidence: v2 had three and v3
  two 0/3 prompts, all reviewed as `model` and tied to the deterministic `units` defect that SPEC-079
  fixed. Recommendation: 0.05, so that two or three 0/3 prompts per 100 still fail the gate; confirm
  with the T005 coverage results.
- **OD-3 — Paired margin δ.** Options: 0.02, 0.05, 0.10 in mean paired difference of the per-prompt
  valid rate. Evidence: the slice grows as 1/δ² (plan.md formula); near ties are not resolvable at any
  allocation. Recommendation: 0.05, revised after the noise pilot gives σ_d.
- **OD-4 — Power and slice size.** Options: 80 % or 90 % power; slice size computed from the noise
  pilot; a fixed cap per session. Evidence: no pilot yet; n = 5 supports no test. Recommendation: 80 %,
  size from the formula, capped by one session's quota.
- **OD-5 — Audit set size.** Options: 128 items (about ±4.5 points); 64 (about ±6); other. Evidence:
  2610.09239 (lead). Recommendation: 128.
- **OD-6 — `parallel` above 1.** Options: keep 1; implement up to 2; up to 4. Evidence: the runner is
  sequential (`agent_braid/lightning_runner.py`, header comment) though the configuration accepts more;
  concurrency effects on quota and host behaviour are unmeasured. Recommendation: keep 1 for gates;
  revisit for development runs after A/A anchors.
- **OD-7 — Candidate pool size.** Options: 5, 10 or 20 candidates per selection. Evidence: the review
  proposes 5 to 20 from one to three contrastive rewrites. Recommendation: at most 10 until T006 shows
  the slice can separate more.
- **OD-8 — Reserve size and replacement cap.** Options: reserve of 10 or 20 prompts; cap of 3, 5 or 10
  replacements. Evidence: v4 had 79 0/3 prompts; a cap prevents a run from becoming a new split.
  Recommendation: reserve 10 % of the split, cap equal to the reserve.
- **OD-9 — Tripwire threshold and twin size.** Options: 20 prompts × 1 repetition with a threshold set
  from the development invocation rate minus a margin; a larger twin. Evidence: about 20 prompts and a
  few minutes would have exposed the T008 collapse. Recommendation: 20 × 1; the threshold is set after
  the SPEC-091 development factorial.
- **OD-10 — Milestone.** Options: BL.2c (provisional, used in tracking now); a new BL milestone created
  by the owner. Recommendation: a new milestone; tracking moves after it exists.
- **OD-11 — Elimination rule and paired test.** Options: synchronized successive halving; SySRs;
  paired racing; with an exact sign test, an exact McNemar test on majority pass, or a sign-flip
  permutation test on d_i − δ. Evidence: none of these has been compared under this noise model
  (SySRs was shown on deterministic scores only). Recommendation: decide from T006; prior choice
  synchronized halving with the sign-flip test.
- **OD-12 — Sequential prompt-level gate.** Options: adopt a sequential version with a prefixed random
  order; fixed sample only. Evidence: the review estimates 35 to 45 % fewer prompts (lead, not verified
  here). Recommendation: fixed sample for the first gate A split.
- **OD-13 — Gate A split size and class plan.** Options: 100 prompts as in SPEC-078 and SPEC-079; a
  size from power. Evidence: comparability with OD-1 arithmetic. Recommendation: 100, class plan written
  in T016.

## Risks and assumptions

- Risk: templated prompts are clustered, so prompt independence is optimistic (REQ-002, REQ-003, T004).
- Risk: the simulation model omits a real noise source, such as host drift within a session
  (REQ-013, T006).
- Risk: the replacement reserve turns a bad split into a new split (REQ-005, OD-8).
- Risk: three repetitions are not optimal if prompt cost differs from the assumed 6 to 10 rollouts
  (REQ-007, SPEC-091 noise pilot).
- Risk: changing the GEPA and APO selection steps alters SPEC-072 replay (REQ-019, T014).
- Assumption: repetitions are independent given a prompt's pass probability (REQ-003).
- Assumption: the SPEC-069 scorer and fixture workspace are reused unchanged (REQ-001, REQ-020).
- Assumption: SPEC-091 runs the noise pilot that sizes the slice (REQ-009, T006).

## Exit criteria

Verification is complete when the obtained evidence for SC-001 to SC-036 in the
[validation plan](validation-plan.md) exists, the simulation record (T004 to T007) is committed, the
protocol is frozen (T016), and the T018 converge record is written. A negative simulation result, a
missed gate or an inconclusive run is a valid completion when recorded. Passing checks are not approval.

## Open questions

- OD-1 to OD-13 above; owner: the founder.
- Whether the gate A real run (T017) happens at all; owner: the founder.
