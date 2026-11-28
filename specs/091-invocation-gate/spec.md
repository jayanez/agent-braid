# Feature specification: SPEC-091 — Invocation gate (gate B)

**Milestone:** provisional, BL.2c — Lightning tool-level kind-choice fix (OD-15).
**Status:** draft. Nothing is implemented or run, and nothing here authorizes a rollout.
**Decision record:** [ADR 0046](../../docs/adr/0046-lightning-evaluation-design.md) (Proposed).

## Purpose and scope

On SPEC-079's v4 held-out set, where no prompt names the product, the model called `analyze-work` in 53 of
300 rollouts; 221 rollouts made no tool call, 57 used `ToolSearch` and 24 invoked the skill
([diagnosis](../079-kind-choice-tool-fix/evidence/t008-diagnosis-and-strategy-review.md)). Seven things
changed between v3 and v4, so the cause is not isolated. Whether Agent Braid is to be invoked at all when
the user does not name it was not decided anywhere in the repository. The owner stated on 2026-11-27
(OD-B1, not yet committed; T001 records it) that items are labelled before measurement and scored by label.

This specification defines gate B of ADR 0046 and the work it needs: labelled items, a laboratory with
competing tools and co-installed skills, architecture levers measured as arms, an optimizer target beyond
the skill body, two development pilots, a preregistered 2×2 factorial (description × hook) and, last, a
frozen gate B held-out. The statistics are those of [SPEC-090](../090-lightning-evaluation-v2/spec.md).

This is engineering plus a research protocol:

- Engineering: labels and item sets (REQ-002, REQ-003, REQ-019, REQ-027, REQ-028); the laboratory
  (REQ-004, REQ-022); the levers (REQ-005 to REQ-008, REQ-024, REQ-025, REQ-032); the optimizer target and
  caps (REQ-009, REQ-010, REQ-020, REQ-029); reports (REQ-001, REQ-017, REQ-026).
- Research: simulations first (REQ-018), then the noise pilot (REQ-012), the development factorial
  (REQ-011), the 2×2 factorial (REQ-013) and the held-out (REQ-014, REQ-015), each a separate owner yes.

Out of scope, each stated as a requirement: spent v4 prompts as a held-out set, and as development
material without OD-1 (REQ-019); an invocation-only reward (REQ-020); provider keys and other secrets (REQ-021); LLM
judges (REQ-031); a gating contrast harness (REQ-030); weaker containment (REQ-022); frozen SPEC-069, SPEC-078 and SPEC-079 records (REQ-023); tool
contract changes before the ADR 0038 decision (REQ-024); levers on by default without promotion (REQ-025).
Not covered at all: gate A and the statistical machinery (SPEC-090); hosts other than `claude-code`;
SPEC-079 T009, which stays the owner's decision.

## Authorities

Constitution clause zero and Articles 9, 12, 13, 14, 19, 20, 21 and 23;
[GOVERNANCE.md](../../GOVERNANCE.md); [claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md) (EUR 0);
[ADR 0030](../../docs/adr/0030-native-plugin-surface-naming.md) (surface naming);
[ADR 0035](../../docs/adr/0035-native-claude-laboratory-containment.md) (lab containment);
[ADR 0038](../../docs/adr/0038-analyze-work-request-contract.md) (`analyze-work` contract, D12 cap);
[ADR 0039](../../docs/adr/0039-braid-lightning-boundary.md) (Lightning boundary, unchanged);
[ADR 0046](../../docs/adr/0046-lightning-evaluation-design.md) (Proposed). Precedents:
[SPEC-071](../071-lightning-rollouts-reward/spec.md) (runner, profiles),
[SPEC-073](../073-lightning-promotion/spec.md) (promotion),
[SPEC-079](../079-kind-choice-tool-fix/spec.md) (v4, T008),
[SPEC-090](../090-lightning-evaluation-v2/spec.md) (machinery).

## Clarifications

- **OD-B1 — Item labels (owner, 2026-11-27).** Items are labelled `tool-necessary` (the needed fact is not
  in the prompt, for example repository state), `tool-beneficial` (the product gives a verified, auditable
  artifact the prose answer does not) or `tool-unnecessary`, before data are collected. Recall is required
  on the first two labels; not invoking is required on the third. The decision was stated in a planning
  session; T001 commits its dated record.
- **Strategy approval (2026-11-28).** As SPEC-090; T001 records it.
- Every numeric parameter and the hook wording are open (Owner decisions). None is filled in.

## Requirements and acceptance scenarios

- **REQ-001 — Gate B metrics.** Gate B MUST score prompts that do not name the product with two separate metrics whose unit is the item, not the rollout, each with its own bound at the α of OD-3 computed from the per-item outcome of OD-17: recall over `tool-necessary` and `tool-beneficial` items, and the false-positive rate over `tool-unnecessary` and near-miss items, where an item counts as calling `analyze-work` by the OD-17 rule.
  - SC-001: Given a labelled run with three repetitions per item and known per-item calls, when the gate B analysis runs, then it reports recall and the false-positive rate over items, with the OD-17 bound, and no rollout-level bound.
- **REQ-002 — Labels before measurement.** Every gate B item MUST carry one label, `tool-necessary`, `tool-beneficial` or `tool-unnecessary` (OD-B1, 2026-11-27), assigned by the OD-2 procedure from a written rubric and frozen by sha256 before any rollout on it.
  - SC-002: Given an item set whose label record hash differs from the frozen one, when a run is requested, then the runner refuses.
- **REQ-003 — Item pool composition.** The item-set builder MUST reject a gate B item set that holds no near-miss items (prompts that resemble a tool use but are `tool-unnecessary`).
  - SC-003: Given an item set without near-miss items, when the builder checks it, then it refuses.
- **REQ-004 — Realistic laboratory.** Gate B measurements MUST run in a laboratory profile with the OD-5 competing host tools enabled, the OD-5 pinned co-installed skills present, both recorded in the configuration digest.
  - SC-004: Given the gate B lab profile, when its configuration is built, then the OD-5 tools are allowed, the pinned skills are installed and both are in configDigest.
- **REQ-005 — Lever arms.** Each lever MUST be a separately measurable arm: `anthropic/alwaysLoad` in the `analyze-work` tool `_meta`; MCP server instructions; a skill description that leads with the use case; a factual `UserPromptSubmit` hook; and a documented explicit command. The explicit command is checked as a deterministic entry (it reaches `analyze-work` on every rollout), not scored for recall.
  - SC-005: Given the lever catalogue, when arms are built, then one arm exists per lever, each with its own digest.
  - SC-006: Given the explicit command arm, when it is run on its check prompts, then every rollout reaches analyze-work.
- **REQ-006 — One difference per arm.** The comparison configurator MUST reject two compared arms that differ in more than one lever outside the preregistered factorials; compared arms share the pinned plugin build, host and model.
  - SC-007: Given two arms differing in two levers outside a factorial, when the comparison is configured, then it refuses.
- **REQ-007 — Factual hook text.** The `UserPromptSubmit` hook text MUST be the factual, non-imperative wording the owner approves in OD-4, frozen by sha256 with the protocol that uses it.
  - SC-008: Given a hook text that differs from the frozen hash, when the hook arm is built, then the build refuses.
- **REQ-008 — Hook data handling.** The hook MUST NOT store, log or transmit the user prompt, which may hold personal data or secrets; its only output is its frozen context string.
  - SC-009: Given a prompt containing a marker string, when the hook runs, then the marker appears in no file, log or output written by the hook.
- **REQ-009 — Optimizer target beyond the skill body.** `target.kind` in `agent_braid/lightning_config.py` MUST accept the kinds adopted in OD-14 (proposed: the skill description and the MCP server instructions) besides `skill`, with `agent_braid/lightning_resources.py` splitting and recombining each target so that every byte outside the target is unchanged and hashed.
  - SC-010: Given a skill-description candidate, when it is recombined with the skill file, then only the description field differs and the other bytes hash as before.
- **REQ-010 — Size caps.** The candidate validator MUST reject, without truncating, a candidate above its host limit (re-verified against host documentation at T004; documented today as at most 1,536 characters for a skill description and at most 4,096 for server instructions) or above the ADR 0038 D12 cap of 1,500 approximate tokens for the compact `analyze-work` definition.
  - SC-011: Given a description candidate one character over its cap, when it is validated, then it is refused with a size code.
- **REQ-011 — Development factorial pilot.** Before any gate B held-out, a 2³ factorial on fresh development prompts (plus spent v4 prompts only if and as OD-1 allows) MUST cross product name (present or absent), form (directive or question) and the completeness sentence (present or absent), at the size of OD-6, reported descriptively with exact intervals per cell. It estimates the effect of three of the seven v3/v4 differences on fresh prompts; it does not isolate the v3 to v4 change, and it is not a gate.
  - SC-012: Given the pilot design, when it is built, then each of the 8 cells has the OD-6 count and every prompt is fresh, except spent v4 prompts in the form OD-1 allows.
- **REQ-012 — Noise pilot.** A gate B noise pilot MUST estimate, in the gate B laboratory on prompts that do not name the product, the within-prompt correlation of invocation, the disagreement rate between candidates and A/A drift, and publish them in the SPEC-090 sizing input format for gate B selection (T013) and the OD-7 sizes; gate A is sized from its own pilot (SPEC-090 REQ-032).
  - SC-013: Given a noise pilot run, when its report is built, then it contains the correlation, the disagreement rate and A/A differences with intervals in the SPEC-090 input format.
- **REQ-013 — Preregistered 2×2 factorial.** The description × hook factorial MUST be preregistered and frozen before its run, with arms interleaved in randomized blocks and the rollouts per cell and metric of OD-7; the analysis reports both metrics per cell, the main effects and the interaction, and tests the interaction for equivalence within ±η of OD-18 by two one-sided tests (TOST).
  - SC-014: Given a factorial schedule, when it is generated from the frozen seed, then arms interleave in blocks and the counts per cell match the protocol.
- **REQ-014 — Gate B held-out.** A gate B held-out set MUST be frozen by sha256 and scored once, and MAY be built only after the 2×2 factorial meets the OD-9 criterion (recall rising with a stable false-positive rate).
  - SC-015: Given a factorial report that misses the OD-9 criterion, when a held-out freeze is requested, then it refuses.
- **REQ-015 — Gate B tripwire.** Gate 0 of a gate B held-out MUST run the SPEC-090 invocation tripwire on a labelled development twin.
  - SC-016: Given a twin below the tripwire threshold, when Gate 0 runs, then the held-out run is refused.
- **REQ-016 — Official harness contrast.** If OD-13 adopts it, `claude plugin eval` MUST be run once as a contrast with its version recorded.
  - SC-017: Given an adopted OD-13, when the contrast task runs, then one contrast record exists with the harness version.
- **REQ-017 — Gate B report.** Gate B reports MUST carry per-label and per-class recall and false-positive counts, invocation and skill-invoked counts, the lever arm, `configDigest` and per-rollout versions (SPEC-090 REQ-014).
  - SC-018: Given a recorded run, when the report is built, then every listed field is present.
- **REQ-018 — Simulation before any real run.** Before any real rollout under this specification, simulations MUST record: coverage of the recall and false-positive bounds; type I and II error of the 2×2 analysis with known effects and the correlation range 0.41 to 0.81; and replay determinism of the factorial journal.
  - SC-019: Given known recall and false-positive rates per cell, when the analysis is simulated (SIM), then bound coverage is at least nominal and the error rates are reported per design option.
- **REQ-019 — Spent v4 prompts.** Spent v4 prompts MUST NOT be used as a gate B held-out set, nor as gate B development material unless the owner allows it in OD-1, in the form OD-1 states.
  - SC-020: Given an item set containing a v4 prompt without a recorded OD-1 allowance, when it is checked, then the builder refuses.
- **REQ-020 — No invocation-only reward.** An optimizer reward for invocation MUST include the false-positive component on `tool-unnecessary` items, so that no invocation-only reward is used.
  - SC-021: Given a reward configuration with recall only, when it is validated, then it is refused.
- **REQ-021 — Provider secrets.** A run MUST NOT read or accept a provider API key or other secret; it uses the subscription route at EUR 0 only.
  - SC-022: Given a rollout environment holding a provider key variable, when the run starts, then it is rejected before any rollout, as SPEC-071 does, and the key value appears in no record.
- **REQ-022 — Containment kept.** Enabling competing tools MUST NOT weaken the laboratory containment: tools outside OD-5 stay disabled and the disposable profile and workspace rules of SPEC-071 stay in force.
  - SC-023: Given a lab profile requesting a tool outside OD-5, when it is built, then the build refuses.
- **REQ-023 — Frozen records untouched.** This specification MUST NOT edit the SPEC-069 scorer or prompt sets, or the SPEC-078 and SPEC-079 splits, protocols and FREEZE files.
  - SC-024: Given the diff of every task, when the boundary test runs, then no frozen path changed.
- **REQ-024 — Tool contract changes behind a decision.** `_meta` or MCP server instructions of `analyze-work` MUST NOT change in a shipped build before the OD-10 decision on ADR 0038 is recorded.
  - SC-025: Given a shipped build with alwaysLoad and no recorded OD-10 decision, when the release check runs, then it fails.
- **REQ-025 — No default shipping of levers.** A lever MUST NOT ship enabled by default in a release without the owner's promotion decision under SPEC-073 and the hook policy of OD-11.
  - SC-026: Given a release build, when its plugin manifest is checked, then no lever is enabled without a recorded promotion decision.
- **REQ-026 — No combined score.** Gate B MUST NOT combine recall and the false-positive rate into one score (split from REQ-001).
  - SC-027: Given a gate B report, when its fields are listed, then no field combines the two metrics.
- **REQ-027 — Measured labels immutable.** A label change after measurement MUST create a new item-set version, leaving the measured version unchanged (split from REQ-002).
  - SC-028: Given a relabelled item, when the record is saved, then a new version is created and the measured version is unchanged.
- **REQ-028 — Counts stated before authoring.** Each gate B item set MUST state its per-label and per-class counts, at the sizes of OD-8, before its prompts are authored (split from REQ-003).
  - SC-029: Given an item set whose counts were recorded after its prompts, when it is checked, then it is rejected.
- **REQ-029 — Skill configurations replay.** Existing `skill` target configurations MUST replay byte-identically after the target extension (split from REQ-009).
  - SC-030: Given an existing SPEC-072 skill configuration, when it is replayed, then the candidate hashes are identical to the recorded ones.
- **REQ-030 — Contrast never gates.** A `claude plugin eval` result MUST NOT change a gate verdict (split from REQ-016).
  - SC-031: Given a contrast result that disagrees with the lab, when the gate verdict is computed, then the verdict is unchanged and the disagreement is reported.
- **REQ-031 — No LLM judge.** A run MUST NOT use an LLM judge for labels, rewards or gates (split from REQ-021).
  - SC-032: Given a reward or label configuration naming a model-graded component, when it is validated, then it is rejected.
- **REQ-032 — D12 cap kept.** The compact `analyze-work` definition MUST stay within the ADR 0038 D12 cap of 1,500 approximate tokens in every lever build (split from REQ-024).
  - SC-033: Given every lever build, when the definition size is measured, then it is at most 1,500 approximate tokens.

## Non-functional requirements

Operational and quality constraints, each with its source:

- Size caps per host documentation, re-verified at T004: 1,536 characters for a skill description, 4,096
  for server instructions; the ADR 0038 D12 cap of 1,500 approximate tokens for `analyze-work` (REQ-010,
  REQ-024).
- Determinism: factorial schedules and journals replay from a recorded seed (REQ-013, REQ-018).
- Cost: EUR 0 on the subscription route (REQ-021). Planned real budgets, each an OD: development factorial
  about 200 rollouts (OD-6), 2×2 factorial about 200 rollouts per cell and metric (OD-7). At 8.5 to 17.9 s
  per rollout, 200 rollouts take about 28 to 60 minutes.
- Compatibility: existing `skill` configurations replay byte-identically (REQ-009).

## Security and privacy

- The hook MUST NOT store, log or transmit the user prompt, which may hold personal data or secrets (REQ-008).
- A run MUST NOT read or accept a provider API key or other secret (REQ-021).
- Laboratory containment is not weakened when competing tools are enabled (REQ-022); no LLM judge (REQ-031).
- Whether a released plugin may ship a `UserPromptSubmit` hook is an owner decision (OD-11, REQ-025).
- Transcripts follow the SPEC-074 consent and redaction rules; reports carry counts, not prompt text beyond
  the synthetic items.

## Terminology

- **Gate B:** the unprompted-invocation gate (REQ-001).
- **Labels**, allowed values: `tool-necessary`, `tool-beneficial`, `tool-unnecessary` (OD-B1, REQ-002).
- **Near-miss item:** a `tool-unnecessary` prompt that resembles a tool use (REQ-003).
- **Item outcome:** whether an item counts as calling `analyze-work`, by the OD-17 rule over its rollouts
  (REQ-001).
- **Recall:** share of `tool-necessary` and `tool-beneficial` items whose item outcome is a call (REQ-001).
- **False-positive rate:** share of `tool-unnecessary` and near-miss items whose item outcome is a call
  (REQ-001).
- **Lever**, an architecture change measured as an arm; allowed values: `alwaysLoad`, server instructions,
  skill description, hook, explicit command (REQ-005).
- **Competing tools, co-installed skills:** the OD-5 laboratory set (REQ-004).
- **Development factorial:** the 2³ pilot of REQ-011. **Noise pilot:** REQ-012. **2×2 factorial:** REQ-013.
- **Target kinds**, allowed values: `skill` today, plus the kinds OD-14 adopts (REQ-009).
- **2×2 factorial levels**, allowed values: description `current` or `use-case-first`; hook `absent` or
  `present` (REQ-013).
- **Hypothesis outcomes**, allowed values: supported, not supported, inconclusive (T017).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md); SPEC-090 terms apply.

## Scientific boundaries and compatibility

Hypotheses (preregistered per run in [evaluation-protocol.md](evaluation-protocol.md); none is a
completion condition):

- **H1** — At least one lever raises recall over the current build without a false-positive rise beyond
  the OD-9 margin.
- **H2** — In the 2×2 factorial the description × hook interaction lies within ±η (OD-18), shown by two
  one-sided tests (TOST). If equivalence is not shown, the interaction is reported descriptively and no
  additivity is claimed; a non-significant interaction test alone supports nothing.
- **H3** — Product name, form and the completeness sentence each change the invocation rate in the
  development factorial (descriptive). It estimates the effect of three of the seven v3/v4 differences
  on fresh prompts; it does not isolate the v3 to v4 change.

Domain: one host (`claude-code`), one pinned model, the OD-5 laboratory, labelled synthetic prompts.
Observation contract: transcript tool names per rollout, by label; SPEC-069 `validFirstAttempt` for calls
as a secondary measure. Execution contract: simulations only until each run's freeze and owner yes.

Limits: labels encode product intent, not ground truth; the host's tool-search ranking is undocumented and
`alwaysLoad` on a plugin-provided server is untested here; external activation figures (a forced-evaluation
hook at 100 % against 50 to 55 % on 22 prompts; always-on skills opened 0 of 198 times against 28 of 66
for path-gated skills, 2610.14216) are leads; an invocation-only reward can teach keyword triggers
(2609.16268, abstract), which is why REQ-020 exists.

## Evidence and unresolved questions

Planned and obtained evidence are kept in `assurance.json`; none is obtained. Inputs already in the
repository: the SPEC-079 T008 report with its invocation block, and the diagnosis. The v4 recall figure
(53/300) is unlabelled and is a baseline description, not a gate B result.

## Owner decisions (open)

Open questions: OD-1 to OD-18. Each has options, a recommendation and its evidence; none is decided.

- **OD-1 — Spent v4 prompts as development material.** Options: (a) no reuse, as the SPEC-079 protocol
  says "v4 is not reused for a second arm"; (b) reuse, labelled, as development material for the pilots only, never as a
  held-out; (c) read their recorded traces descriptively only, with no new rollout on them. Evidence: v4 is
  confounded by seven changes and unlabelled; reuse saves authoring but any future held-out from the same
  templates would leak. Recommendation: (c).
- **OD-2 — Labelling procedure.** Options: owner alone; author and owner label independently, the owner
  adjudicates, agreement reported; a third labeller. Evidence: labels are product intent (OD-B1).
  Recommendation: two independent labels, owner adjudicates, agreement and every disagreement recorded.
- **OD-3 — Gate B bounds and α.** Options: recall lower bound of 0.6, 0.7 or 0.8; false-positive upper
  bound of 0.05, 0.10 or 0.20; α as SPEC-090 OD-1. Evidence: no labelled data yet; v4's unlabelled call
  rate is 53/300. Recommendation: fix both after the 2×2 factorial and before any held-out; record the
  rationale.
- **OD-4 — Hook wording.** Options: (a) one factual sentence that Agent Braid analysis tools are available
  in this session; (b) (a) plus what they return (a verified, auditable report); (c) no hook arm.
  Evidence: host documentation advises factual, non-imperative context; imperative text can trigger
  injection defences. Recommendation: (b); the owner writes the final text, frozen by hash.
- **OD-5 — Competing tools and co-installed skills.** Options: `Read`, `Grep`, `Glob` only; plus `Bash`;
  co-installed skills: none, or a pinned set chosen by the owner. Evidence: the current lab disables all
  four tools and installs one plugin. Recommendation: `Read`, `Grep`, `Glob` and a pinned set of public
  skills; `Bash` stays off for containment.
- **OD-6 — Development factorial size.** Options: about 25 prompts × 1 repetition per cell (about 200
  rollouts); × 3 repetitions. Recommendation: 25 × 1.
- **OD-7 — 2×2 rollouts per cell and metric.** Options: 150, 200 or 300. Evidence: detecting 18 % to 30 %
  recall needs about 156 rollouts per arm one-sided at 80 % power (own calculation); that figure treats
  rollouts as independent and ignores clustering within items (correlation 0.81 on v4), so with the item
  as the unit (OD-17) the effective sample is closer to the number of items. Recommendation: 200 rollouts
  per cell as a floor, with the item count set from the gate B noise pilot.
- **OD-8 — Item pool sizes and label shares.** Options: equal thirds; weighted to recall labels; a fixed
  near-miss share. Recommendation: set per run from OD-7, with at least one quarter near-miss among
  `tool-unnecessary` items.
- **OD-9 — Factorial criterion before a held-out.** Options: recall lower bound above the current build's
  upper bound, with the false-positive difference upper bound at most 0.05 or 0.10. Recommendation: 0.05.
- **OD-10 — ADR 0038 and the tool contract.** Options: amend ADR 0038 before `_meta` or server
  instructions ship; a new ADR; drop those arms. Recommendation: amend ADR 0038; lab builds can measure
  first.
- **OD-11 — Hook in released plugins.** Options: laboratory only; opt-in user configuration; on by default.
  Recommendation: laboratory only until gate B passes, then opt-in.
- **OD-12 — Explicit command name.** Options under ADR 0030 naming. Recommendation: the owner picks.
- **OD-13 — `claude plugin eval` contrast.** Options: run as a non-gating contrast; skip. Evidence: its
  behaviour on this host is unverified. Recommendation: run once as a contrast.
- **OD-14 — Target kinds.** Options: skill description; server instructions; tool description (bound by
  the D12 cap). Recommendation: the first two.
- **OD-15 — Milestone.** As SPEC-090 OD-10.
- **OD-17 — Per-item outcome for gate B.** Options: (a) item majority call (at least 2 of 3 rollouts call
  `analyze-work`) with an exact Clopper–Pearson bound over items; (b) item mean call rate with a cluster
  bootstrap or beta-binomial bound; (c) rollout-level shares, rejected as anti-conservative because
  rollouts of one item are correlated (0.81 on v4). Evidence: gate A uses (a) for the same reason.
  Recommendation: (a) as the gate statistic, (b) reported as a secondary description.
- **OD-18 — Equivalence margin η for the interaction.** Options: ±0.05, ±0.10 or ±0.15 on the difference
  of differences in recall (and separately in the false-positive rate). Evidence: with about 200 rollouts
  per cell the standard error of a difference of differences near p = 0.5 is about 0.07 before clustering
  (own calculation), so ±0.05 is not attainable at that size. Recommendation: ±0.10.
- **OD-16 — Skill `paths` field.** Options: measure it as a lever; skip. Recommendation: only if the
  development factorial points to file-type triggers.

## Risks and assumptions

- Risk: labels encode intent that the owner later revises, splitting item versions (REQ-002, T002).
- Risk: the lab's tool and skill set does not represent the owner's real sessions (REQ-004, OD-5).
- Risk: `alwaysLoad` behaves differently for plugin-provided servers (REQ-005, T004).
- Risk: a hook raises recall by keyword triggering, raising false positives (REQ-007, REQ-020, H1).
- Risk: host updates change tool-search behaviour mid-study (REQ-006; SPEC-090 REQ-013).
- Risk: the development factorial is too small to separate eight cells (REQ-011, OD-6).
- Assumption: host documentation of the lever mechanics is current (REQ-005, REQ-010).
- Assumption: SPEC-090 delivers bounds, selection and drift controls before real runs (REQ-018, T007).

## Exit criteria

Verification is complete when the obtained evidence for SC-001 to SC-033 in the
[validation plan](validation-plan.md) exists, the simulation record (T007) and the pilot reports (T008,
T009) are committed, the 2×2 factorial result is recorded (T012), and the T017 converge record is written.
A null, negative or invalidated result is a valid completion when recorded. Passing checks are not approval.

## Open questions

- OD-1 to OD-18 above; owner: the founder.
- Whether each real run (T008, T009, T012, T015) happens; owner: the founder.
