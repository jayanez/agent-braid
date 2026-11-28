# Feature specification: SPEC-091 — Invocation gate (gate B)

**Milestone:** provisional, BL.2c — Lightning tool-level kind-choice fix (OD-15).
**Template:** spec-kit feature specification.
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

Actors: the owner, who decides every OD, reviews every freeze and says yes to every run; the operator
who runs the `agent-braid lightning` CLI; and the host under test (`claude-code`), whose user-facing
behaviour is measured. No actor gains execution authority.

This is engineering plus a research protocol:

- Engineering: labels and item sets (REQ-002, REQ-003, REQ-019, REQ-027, REQ-028, REQ-040, REQ-042); the
  laboratory (REQ-004, REQ-022); the levers (REQ-005 to REQ-008, REQ-024, REQ-025, REQ-032, REQ-043); the
  optimizer target and caps (REQ-009, REQ-010, REQ-020, REQ-029); reports, verdict and session facts
  (REQ-001, REQ-017, REQ-026, REQ-034, REQ-039); same-build certification and selection (REQ-038,
  REQ-041); freezes and stops (REQ-035, REQ-036).
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


#### REQ-001 — Gate B metrics

Gate B MUST score prompts that do not name the product with two separate metrics whose unit is the item, not the rollout, each with its own bound at the α of OD-3 computed from the per-item outcome of OD-17: recall over `tool-necessary` and `tool-beneficial` items, and the false-positive rate over `tool-unnecessary` items (including near-misses), where an item counts as calling `analyze-work` by the OD-17 rule.

- SC-001: Given a labelled run with three repetitions per item and known per-item calls, when the gate B analysis runs, then it reports recall and the false-positive rate over items, with the OD-17 bound, and no rollout-level bound.

#### REQ-002 — Labels before measurement

- (a) Every gate B item MUST carry one label, `tool-necessary`, `tool-beneficial` or `tool-unnecessary` (OD-B1, 2026-11-27), assigned by the OD-2 procedure from a written rubric and frozen by sha256 before any rollout on it.
- (b) Labels MUST freeze only when Cohen's κ between the two labellers reaches the OD-21 threshold on each label pair; otherwise the rubric MUST be revised and the items relabelled.
- SC-002: Given an item set whose label record hash differs from the frozen one, when a run is requested, then the runner refuses.

#### REQ-003 — Item pool composition

The item-set builder MUST reject a gate B item set that holds no near-miss items (prompts that resemble a tool use but are `tool-unnecessary`).

- SC-003: Given an item set without near-miss items, when the builder checks it, then it refuses.

#### REQ-004 — Realistic laboratory

Gate B measurements MUST run in a laboratory profile with the OD-5 competing host tools enabled, the OD-5 pinned co-installed skills present, both recorded in the configuration digest.

- SC-004: Given the gate B lab profile, when its configuration is built, then the OD-5 tools are allowed, the pinned skills are installed and both are in configDigest.

#### REQ-005 — Lever arms

Each lever MUST be a separately measurable arm: `anthropic/alwaysLoad` in the `analyze-work` tool `_meta`; MCP server instructions; a skill description that leads with the use case; a factual `UserPromptSubmit` hook; and a documented explicit command. The explicit command is checked as a deterministic entry (it reaches `analyze-work` on every rollout), not scored for recall.

- SC-005: Given the lever catalogue, when arms are built, then one arm exists per lever, each with its own digest.
- SC-006: Given the explicit command arm, when it is run on its check prompts, then every rollout reaches analyze-work.

#### REQ-006 — One difference per arm

The comparison configurator MUST reject two compared arms that differ in more than one lever outside the preregistered factorials; compared arms share the pinned plugin build, host and model.

- SC-007: Given two arms differing in two levers outside a factorial, when the comparison is configured, then it refuses.

#### REQ-007 — Factual hook text

The `UserPromptSubmit` hook text MUST be the factual, non-imperative wording the owner approves in OD-4, frozen by sha256 with the protocol that uses it.

- SC-008: Given a hook text that differs from the frozen hash, when the hook arm is built, then the build refuses.

#### REQ-008 — Hook data handling

The hook MUST NOT store, log or transmit the user prompt, which may hold personal data or secrets; its only output is its frozen context string.

- SC-009: Given a prompt containing a marker string, when the hook runs, then the marker appears in no file, log or output written by the hook.

#### REQ-009 — Optimizer target beyond the skill body

`target.kind` in `agent_braid/lightning_config.py` MUST accept the kinds adopted in OD-14 (proposed: the skill description and the MCP server instructions) besides `skill`, with `agent_braid/lightning_resources.py` splitting and recombining each target so that every byte outside the target is unchanged and hashed.

- SC-010: Given a skill-description candidate, when it is recombined with the skill file, then only the description field differs and the other bytes hash as before.

#### REQ-010 — Size caps

The candidate validator MUST reject, without truncating, a candidate above its host limit (re-verified against host documentation at T004; documented today as at most 1,536 characters for a skill description and at most 4,096 for server instructions) or above the ADR 0038 D12 cap of 1,500 approximate tokens for the compact `analyze-work` definition.

- SC-011: Given a description candidate one character over its cap, when it is validated, then it is refused with a size code.

#### REQ-011 — Development factorial pilot

Before any gate B held-out, a 2³ factorial MUST cross product name (present or absent), form (directive or question) and the completeness sentence (present or absent) on fresh development prompts, plus spent v4 prompts only to the extent OD-1 allows, at the size of OD-6, reported descriptively with exact intervals per cell. The pilot estimates the effect of three of the seven v3/v4 differences on fresh prompts; the pilot does not isolate the v3 to v4 change and is not a gate.

- SC-012: Given the pilot design, when it is built, then each of the 8 cells has the OD-6 count and every prompt is fresh, except spent v4 prompts in the form OD-1 allows.

#### REQ-012 — Noise pilot

- (a) A gate B noise pilot MUST estimate, in the gate B laboratory on prompts that do not name the product, using the two OD-27 arms: the within-item correlation of invocation, the variance of paired per-item differences in the item outcome, the discordance between the two arms (share of items whose item outcomes differ), A/A drift and item-level recall on recall-labelled items.
- (b) The pilot MUST publish these estimates in the SPEC-090 sizing input format for gate B selection (T019), the OD-7 sizes and the OD-22 threshold.
- (c) Gate A is sized from its own pilot (SPEC-090 REQ-032).
- SC-013: Given a noise pilot run, when its report is built, then it contains the within-item correlation, the paired per-item difference variance, the discordance, A/A differences and item-level recall with intervals in the SPEC-090 input format.

#### REQ-013 — Preregistered 2×2 factorial

- (a) The description × hook factorial MUST be preregistered and frozen before its run as a within-item design (every item runs in all four cells), with arms interleaved in randomized blocks and the items per cell of OD-7 (rollouts derived as items × 3).
- (b) The protocol MUST name the contrasts (description main effect, hook main effect, interaction as the difference of differences).
- (c) The protocol MUST name the candidate analyses (exact paired McNemar per contrast on the item outcome; a logistic mixed model with an item random effect; a sign-flip permutation test on item-level differences), from which T007 picks one.
- (d) The protocol MUST state Holm over the recall main effects at the OD-19 family-wise α, with false-positive noninferiority per effect.
- (e) The protocol MUST state the TOST equivalence test of the interaction within ±η of OD-18.
- (f) If the hook arm is recorded as unavailable (REQ-039), the factorial MUST reduce to the preregistered description-only paired comparison (use-case-first against current, hook absent).
- (g) In that case REQ-014 MUST use the description-only comparison.
- SC-014: Given a factorial schedule, when it is generated from the frozen seed, then arms interleave in blocks and the counts per cell match the protocol.

#### REQ-014 — Gate B held-out

- (a) A gate B held-out set MUST be frozen by sha256 and scored once.
- (b) A gate B held-out set MUST NOT be built before the 2×2 factorial meets the paired OD-9 criterion in the decisive cell named under REQ-044, at the OD-19 family-wise α, or its preregistered description-only fallback does (REQ-013): on the same items, the recall difference against the shipped build has a lower bound above zero, and false positives are noninferior, with the exact upper bound on the paired false-positive difference at or below the OD-9 margin.
- SC-015: Given a factorial report that misses the OD-9 criterion, when a held-out freeze is requested, then it refuses.

#### REQ-015 — Gate B tripwire

- (a) Gate 0 of a gate B held-out MUST run the SPEC-090 invocation tripwire on a twin of recall-labelled items, of the OD-22 size, drawn with the split and reserve by the seeded partition of SPEC-090 REQ-042.
- (b) The tripwire MUST use the gate B threshold: the T008 item-level recall (item outcome of OD-17) on `tool-necessary` and `tool-beneficial` items, minus the OD-22 margin.
- (c) Gate B MUST NOT use the gate A threshold.
- SC-016: Given a twin below the tripwire threshold, when Gate 0 runs, then the held-out run is refused.

#### REQ-016 — Official harness contrast

If OD-13 adopts it, `claude plugin eval` MUST be run once as a contrast with its version recorded.

- SC-017: Given an adopted OD-13, when the contrast task runs, then one contrast record exists with the harness version.

#### REQ-017 — Gate B report

Gate B reports MUST carry per-label and per-class recall and false-positive counts, with near-misses reported separately from other `tool-unnecessary` items, both metrics also on the agreed-only subset (items both labellers labelled alike), invocation and skill-invoked counts, the lever arm, `configDigest` and per-rollout versions (SPEC-090 REQ-014).

- SC-018: Given a recorded run, when the report is built, then every listed field is present.

#### REQ-018 — Simulation before any real run

Before any real rollout under this specification, simulations MUST record: coverage of the recall and false-positive bounds; type I and II error of the 2×2 analysis with known effects and the correlation range 0.41 to 0.81; and replay determinism of the factorial journal.

- SC-019: Given known recall and false-positive rates per cell, when the analysis is simulated (SIM), then bound coverage is at least nominal and the error rates are reported per design option.

#### REQ-019 — Spent v4 prompts

Spent v4 prompts MUST NOT be used as a gate B held-out set, nor as gate B development material unless the owner allows it in OD-1, in the form OD-1 states.

- SC-020: Given an item set containing a v4 prompt without a recorded OD-1 allowance, when it is checked, then the builder refuses.

#### REQ-020 — No invocation-only reward

An optimizer reward for invocation MUST include the false-positive component on `tool-unnecessary` items, so that no invocation-only reward is used.

- SC-021: Given a reward configuration with recall only, when it is validated, then it is refused.

#### REQ-021 — Provider secrets

A run MUST NOT read or accept a provider API key or other secret; it uses the subscription route at EUR 0 only.

- SC-022: Given a rollout environment holding a provider key variable, when the run starts, then it is rejected before any rollout, as SPEC-071 does, and the key value appears in no record.

#### REQ-022 — Containment kept

Enabling competing tools MUST NOT weaken the laboratory containment: tools outside OD-5 stay disabled and the disposable profile and workspace rules of SPEC-071 stay in force.

- SC-023: Given a lab profile requesting a tool outside OD-5, when it is built, then the build refuses.

#### REQ-023 — Frozen records untouched

This specification MUST NOT edit the SPEC-069 scorer or prompt sets, or the SPEC-078 and SPEC-079 splits, protocols and FREEZE files.

- SC-024: Given the diff of every task, when the boundary test runs, then no frozen path changed.

#### REQ-024 — Tool contract changes behind a decision

`_meta` or MCP server instructions of `analyze-work` MUST NOT change in a shipped build before the OD-10 decision on ADR 0038 is recorded.

- SC-025: Given a shipped build with alwaysLoad and no recorded OD-10 decision, when the release check runs, then it fails.

#### REQ-025 — No default shipping of levers

- (a) A lever MUST NOT ship enabled by default in a release without the owner's promotion decision under SPEC-073, the hook policy of OD-11 and the same-build certification of REQ-038.
- (b) Because the plugin is shared by codex, claude and opencode (`integrations/agent-braid/hosts.json`), a lever MUST ship scoped to claude-code only unless a non-regression measurement exists on each other host; SPEC-089 (a skeleton for analyze-work validity on Codex and OpenCode) does not yet specify that measurement.
- SC-026: Given a release build, when its plugin manifest is checked, then no lever is enabled without a recorded promotion decision.

#### REQ-026 — No combined score

Gate B MUST NOT combine recall and the false-positive rate into one score (split from REQ-001).

- SC-027: Given a gate B report, when its fields are listed, then no field combines the two metrics.

#### REQ-027 — Measured labels immutable

A label change after measurement MUST create a new item-set version, leaving the measured version unchanged (split from REQ-002).

- SC-028: Given a relabelled item, when the record is saved, then a new version is created and the measured version is unchanged.

#### REQ-028 — Counts stated before authoring

Each gate B item set MUST state its per-label and per-class counts, at the counts its OD sets (OD-6, OD-7, OD-8, OD-22 to OD-25), before its prompts are authored (split from REQ-003).

- SC-029: Given an item set whose counts were recorded after its prompts, when it is checked, then it is rejected.

#### REQ-029 — Skill configurations replay

Existing `skill` target configurations MUST replay byte-identically after the target extension (split from REQ-009).

- SC-030: Given an existing SPEC-072 skill configuration, when it is replayed, then the candidate hashes are identical to the recorded ones.

#### REQ-030 — Contrast never gates

A `claude plugin eval` result MUST NOT change a gate verdict (split from REQ-016).

- SC-031: Given a contrast result that disagrees with the lab, when the gate verdict is computed, then the verdict is unchanged and the disagreement is reported.

#### REQ-031 — No LLM judge

A run MUST NOT use an LLM judge for labels, rewards or gates (split from REQ-021).

- SC-032: Given a reward or label configuration naming a model-graded component, when it is validated, then it is rejected.

#### REQ-032 — D12 cap kept

The compact `analyze-work` definition MUST stay within the ADR 0038 D12 cap of 1,500 approximate tokens in every lever build (split from REQ-024).

- SC-033: Given every lever build, when the definition size is measured, then it is at most 1,500 approximate tokens.

#### REQ-033 — Lever screening run

Before the 2×2 factorial, each lever arm (`alwaysLoad`, server instructions) MUST be compared with the shipped build on the same items in one preregistered, frozen screening run (T018), on item-level recall (superiority) and false positives (noninferiority: exact upper bound on the paired difference at or below the OD-9 margin).

- SC-034: Given the screening protocol, when it is frozen, then it names both arms, the shipped build, the shared items and the Holm family of REQ-037.

#### REQ-034 — Gate B verdict

- (a) The gate B verdict MUST be `met` only when the recall lower bound and the false-positive upper bound both meet OD-3; requiring both keeps a false `met` at or below α by the intersection–union principle.
- (b) The verdict MUST use the allowed values and precedence of SPEC-090 REQ-038: `invalidated` over `held` over `missed` and `met`, with the invalidating events of SPEC-090 REQ-038.
- (c) The verdict MUST be `held` while a slot is unfilled after a stop or a label disagreement is not yet adjudicated under OD-2.
- SC-035: Given a run whose recall bound meets OD-3 and whose false-positive bound does not, when the verdict is computed, then it is missed.
- SC-036: Given a run with an open label review and a canary hit, when the verdict is computed, then it is invalidated.

#### REQ-035 — Development pilot freezes

- (a) Each development pilot and the contrast run (T008, T009, T018, T016) MUST run only after its protocol section, its labelled items and its pinned builds are frozen by sha256 on a `develop` commit and the owner says yes.
- (b) Pilot items MUST NOT enter a held-out set or its twin.
- SC-037: Given a pilot run whose item file hash differs from its pilot freeze, when it is requested, then it is rejected.

#### REQ-036 — Stops and resume

Every quota stop, host or model change, or resume MUST follow SPEC-090 REQ-037 unchanged.

- SC-038: Given a gate B held-out run stopped by quota after which the model changed, when a resume is requested, then it is rejected and the run is invalidated as SPEC-090 REQ-037 states.

#### REQ-037 — Family-wise error for levers and effects

- (a) Recall superiority tests of H1 (each lever against the shipped build) and of the 2×2 main effects MUST be adjusted by Holm within each family at the family-wise α of OD-19.
- (b) False positives MUST enter as a noninferiority condition per comparison (exact upper bound on the paired difference at or below the OD-9 margin), never as a superiority test.
- (c) A lever MUST be accepted only when both hold (intersection–union).
- SC-039: Given two levers with recall p-values 0.01 and 0.04 at family-wise α 0.05, the second with a false-positive upper bound above the margin, when the family is adjusted, then Holm rejects both recall nulls but only the first lever is accepted.

#### REQ-038 — Same-build certification

A build that changes the skill description, the server instructions, `_meta` or the hook MUST be proposed for promotion only when gate B is met on it and, on that same build, at least one of these holds: gate A is met; it is noninferior to the shipped build under SPEC-049 on a fresh gate A split (SPEC-090 OD-17 option b).

- SC-040: Given a build that met gate B but has no gate A or SPEC-049 result on the same build, when a promotion proposal is checked, then it is rejected.

#### REQ-039 — Per-rollout session facts

Each rollout MUST record whether the hook context appeared, whether the host emitted a safety notice, and whether the skill and the `analyze-work` tool were present in the session listing; a missing skill or tool is an `instrument` event for that rollout, and an arm whose hook context never appears is recorded as unavailable.

- SC-041: Given a rollout whose session listing lacks `analyze-work`, when it is scored, then it is recorded as an instrument event, not as a non-call.

#### REQ-040 — Product name absent from gate B items

The gate B builder MUST reject, with zero rollouts, any gate B item that contains the product name.

- SC-042: Given a gate B pool with one item naming the product, when the builder runs, then it rejects the pool before any rollout and names the item.

#### REQ-041 — Gate B selection rule

Gate B selection (T019) MUST follow a preregistered rule, with no combined score:

- (a) Selection MUST take as incumbent the 2×2 cell that met OD-9.
- (b) Selection MUST rank challengers in elimination by the paired item-level recall difference against the incumbent.
- (c) Selection MUST replace the incumbent only when a challenger's recall advantage exceeds δ_B of OD-28 and the exact upper bound on its false-positive increase is at or below the OD-9 margin, each tested at the OD-19 family-wise α with Holm over the challengers.
- (d) When several challengers are accepted, selection MUST break the tie by the largest lower bound on recall advantage, then the shortest artifact, then the lowest candidate id.
- (e) Selection MUST score the winner once on the labelled gate B audit set (REQ-042) for both gate B metrics, and once on the SPEC-090 gate A audit set, whose items name the product by design, for authoring validity only, each with noninferiority to the incumbent.
- SC-043: Given two accepted challengers with equal recall lower bounds, when the winner is chosen, then the shorter artifact wins and both audits are scored once with noninferiority against the incumbent.

#### REQ-042 — Labelled gate B audit set

A labelled gate B audit set of the OD-25 size MUST be authored from its own pool, labelled under REQ-002, frozen by sha256, kept disjoint from every slice, pilot, split and twin, and scored once per winner.

- SC-044: Given a selection input that contains a gate B audit item, when selection is configured, then it is rejected.

#### REQ-043 — Description lever as an overlay

The use-case-first skill description MUST be a laboratory overlay applied when a lever build is assembled; the canonical `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md`, which is the optimizer's origin path and default target, stays byte-identical.

- SC-045: Given a lever build with the description overlay, when the repository files are hashed after the build, then the canonical SKILL.md hash is unchanged and only the build output carries the overlay.

#### REQ-044 — Preregistered decisive cell

The T011 freeze MUST name the one preregistered 2×2 cell whose paired comparison against the shipped-build cell must meet OD-9 for REQ-014, tested at the OD-19 family-wise α.

- SC-046: Given a 2×2 protocol that names no decisive cell, when the freeze check runs, then it is rejected.

## Non-functional requirements

Operational and quality constraints, each with its source:

- Size caps per host documentation, re-verified at T004: 1,536 characters for a skill description, 4,096
  for server instructions; the ADR 0038 D12 cap of 1,500 approximate tokens for `analyze-work` (REQ-010,
  REQ-032).
- Determinism: factorial schedules and journals replay from a recorded seed (REQ-013, REQ-018).
- Cost: EUR 0 on the subscription route (REQ-021). Every quota-spending task has its own freeze and the
  owner's yes.

Budget from T001 to the gate B verdict, at the recommended OD values:

| Task | Size | Rollouts | At 8.5 s | At 17 s |
|---|---|---|---|---|
| T001–T007, T010, T011, T013, T014, T022 | no rollouts | 0 | 0 | 0 |
| T008 gate B noise pilot | 20 items × 3 × 3 runs (OD-23) | 180 | 26 min | 51 min |
| T009 development factorial | 25 items × 8 cells × 1 (OD-6) | 200 | 28 min | 57 min |
| T018 lever screening | (60 + 60) items × 3 × 3 arms (OD-24) | 1,080 | 2.6 h | 5.1 h |
| T012 2×2 factorial | (150 + 60) items × 3 × 4 cells (OD-7, OD-8) | 2,520 | 6.0 h | 11.9 h |
| T019 selection (only if OD-20 (a) needs it) | elimination 60 items × 1 over 10, 5 and 3 candidates (1,080); confirmation (75 recall + 60 `tool-unnecessary`) items × 3 arms × 3 (1,215; illustrative: discordance 0.10, gap 0.10, OD-28); gate B audit 90 × 3; gate A audit 128 × 3 | 2,949 | 7.0 h | 13.9 h |
| T023 gate A on the same build (REQ-038) | 100 × 3 plus reserve 5 × 3, twin 20 × 1 | 335 | 47 min | 95 min |
| T021 Gate 0 tripwire | twin 20 × 1 (OD-22) | 20 | 3 min | 6 min |
| T015 gate B held-out | (150 + 60) items × 3 (OD-25) | 630 | 1.5 h | 3.0 h |
| T016 contrast | 20 items × 3 × 2 (OD-13) | 120 | 17 min | 34 min |
| A/A anchors | 20 per session × 10 sessions (SPEC-090 OD-20) | 200 | 28 min | 57 min |
| **Total with selection** | | **8,234** | **19.4 h** | **38.9 h** |
| **Total without selection** | | **5,285** | **12.5 h** | **25.0 h** |

Combined with gate A (SPEC-090, 575 rollouts): 8,809 rollouts with selection (20.8 h at 8.5 s, 41.6 h at
17 s) or 5,860 without (13.8 h, 27.7 h). Subscription quota windows, not cash, bind these runs.
- Compatibility: existing `skill` configurations replay byte-identically (REQ-029).

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
- **False-positive rate:** share of `tool-unnecessary` items (including near-misses) whose item outcome is a
  call (REQ-001).
- **Item:** a gate B prompt; **within-item** correlation is SPEC-090's within-prompt correlation for items.
- **Discordance:** the share of items whose item outcomes differ between two arms (REQ-012).
- **Shipped build, incumbent, challenger, missing result, unfilled slot, canary, invalidating event,
  owner yes record:** as defined in SPEC-090 Terminology.
- **Agreed-only subset:** items both labellers labelled alike (REQ-017).
- **Gate B twin:** recall-labelled items drawn with the split by the seeded partition (REQ-015).
- **Incumbent (gate B selection):** the 2×2 cell that met OD-9 (REQ-041).
- **Gate verdicts**, allowed values: `met`, `missed`, `held`, `invalidated`; precedence as SPEC-090 REQ-038
  (REQ-034).
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

- **H1** — At least one lever (screened in T018 or in the 2×2 factorial) raises item-level recall over the incumbent, with Holm over the levers at the OD-19 family-wise α, while its false positives are noninferior within the OD-9 margin (REQ-037).
- **H2** — In the 2×2 factorial the description × hook interaction lies within ±η (OD-18), shown by two one-sided tests (TOST); if equivalence is not shown, the interaction is reported descriptively and no additivity is claimed, because a non-significant interaction test alone supports nothing; at the recommended sizes H2 is likely inconclusive unless OD-7 reaches the item count that OD-18 states.
- **H3** — Product name, form and the completeness sentence each change the invocation rate in the development factorial (descriptive); it estimates the effect of three of the seven v3/v4 differences on fresh prompts and does not isolate the v3 to v4 change.

Real-run order, the same in ADR 0046, SPEC-090 and SPEC-091: the gate A noise pilot (SPEC-090 T020) and,
independently and in either order, the gate B noise pilot and development factorial (SPEC-091 T008,
T009); then lever screening (SPEC-091 T018) and the 2×2 factorial (T012); then, only where it applies,
gate B selection (T019) and the same-build gate A run (T023); then the frozen held-out runs (SPEC-090 T022
and T017; SPEC-091 T021 and T015). Each run MUST be behind its own freeze and owner yes record (SPEC-090 REQ-017 and SPEC-090 REQ-045).

Multiplicity: gate B is conjunctive (recall bound and false-positive bound), so a false `met` stays at or
below α by the intersection–union principle (REQ-034); H1 and the 2×2 main effects are adjusted by Holm
(REQ-037).

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

Open questions: OD-1 to OD-28. Each has options, a recommendation and its evidence, or says plainly that no
evidence exists; none is decided. The 0.81 figure below is the ANOVA ICC of per-prompt pass counts on v4.

- **OD-1 — Spent v4 prompts as development material.** Options: (a) no reuse, as the SPEC-079 protocol
  says "v4 is not reused for a second arm"; (b) reuse, labelled, as development material for the pilots
  only, never as a held-out, which overrides that frozen SPEC-079 rule and so requires a recorded SPEC-079
  amendment first; (c) read their recorded traces descriptively only, with no new rollout on them.
  Evidence: v4 is confounded by seven changes and unlabelled; reuse saves authoring but any future
  held-out from the same templates would leak. Recommendation: (c).
- **OD-2 — Labelling procedure.** Options: owner alone; author and owner label independently, the owner
  adjudicates, agreement reported; a third labeller. Evidence: labels are product intent (OD-B1).
  Recommendation: two independent labels, owner adjudicates, agreement and every disagreement recorded.
- **OD-3 — Gate B bounds.** Options for the rule that fixes them: (i) fixed values chosen now: recall lower
  bound 0.6, 0.7 or 0.8, false-positive upper bound 0.05, 0.10 or 0.20; (ii) a rule applied after the 2×2
  factorial and before any held-out, with floors fixed at T001: recall bound = max(best 2×2 cell's
  item-level lower bound, R_min) and false-positive bound = min(shipped build's 2×2 upper bound plus the
  OD-9 margin, F_max), with R_min and F_max owner parameters (options: R_min 0.5 or 0.6; F_max 0.10 or
  0.20). Without the floors, a best cell at recall 0.20 would yield a `met` for a useless arm, and an arm
  equal to that cell would be tested against its own earlier bound (about a coin flip). α follows
  SPEC-090 OD-1. Evidence: no labelled data yet; v4's unlabelled call rate is 53/300. Recommendation: (ii)
  with R_min = 0.6 and F_max = 0.10, recorded before the held-out is built.
- **OD-4 — Hook wording.** Options: (a) one factual sentence that Agent Braid analysis tools are available
  in this session; (b) (a) plus what they return (a verified, auditable report). The former option "no
  hook arm" was removed: REQ-013 and H2 need the hook factor; if the hook context never appears on the
  pinned host, REQ-013's preregistered description-only fallback applies instead. Evidence: host
  documentation advises factual, non-imperative context; imperative text can trigger injection defences,
  so each rollout records whether a safety notice appeared (REQ-039). Recommendation: (b); the owner
  writes the final text, frozen by hash.
- **OD-5 — Competing tools and co-installed skills.** Options: `Read`, `Grep`, `Glob` only; plus `Bash`;
  co-installed skills: none, or a pinned set chosen by the owner. Evidence: the current lab disables all
  four tools and installs one plugin. Recommendation: `Read`, `Grep`, `Glob` and a pinned set of public
  skills; `Bash` stays off for containment.
- **OD-6 — Development factorial size.** Options: 25 items × 1 repetition per cell (200 rollouts);
  25 items × 3 repetitions (600). Evidence: no development factorial has run; at 25 items per
  cell an exact 95 % interval on a cell rate near 0.5 is about ±0.2 (own calculation), enough to see large
  effects only. Recommendation: 25 × 1, reported as descriptive.
- **OD-7 — 2×2 recall-labelled items per cell.** Options: 67, 156 or 300 `tool-necessary` and
  `tool-beneficial` items per cell, at 3 repetitions; the `tool-unnecessary` count is OD-8, so a cell holds
  OD-7 + OD-8 items. Evidence: an unpaired one-sided test at 80 % power needs 156 units per arm to detect
  recall 0.18 against 0.30 (own calculation); here the unit is the item, so 156 recall-labelled items per
  arm. The within-item design pairs arms on the same items and needs fewer, computed from the gate B
  noise pilot's discordance (REQ-012). At 67 recall items per cell H2 is inconclusive at any η in OD-18 up
  to ±0.15. Recommendation: 156 recall items per cell, reduced to the paired size once T008 reports the
  discordance.
- **OD-8 — `tool-unnecessary` items per comparison and label shares.** False positives are a
  noninferiority condition: the exact one-sided 95 % upper bound on the paired false-positive difference,
  taken conservatively as the bound on the share of items where only the lever arm calls, is met when it
  is at or below the OD-9 margin. Arithmetic (own calculation), upper bounds for 0, 1, 2 and 3 such items: n = 50:
  0.058, 0.091, 0.121, 0.148 (a perfect lever cannot meet a 0.05 margin); n = 60: 0.049, 0.077, 0.101,
  0.124; n = 120: 0.025, 0.039, 0.052, 0.063. Options: (a) 120 `tool-unnecessary` items with margin 0.05
  (tolerates one extra call); (b) 60 items with margin 0.10 (tolerates one); (c) 200 items with margin
  0.05 (tolerates three). At least one quarter are near-misses, reported separately. Evidence: no
  labelled pool exists. Recommendation: (b), the cheapest attainable option.
- **OD-9 — Paired criterion before a held-out.** Rule: in the decisive cell named under REQ-044, on the
  same items, the recall difference (that cell minus the shipped-build cell) has an exact lower bound above
  zero, and false positives are noninferior: the exact upper bound on the paired false-positive difference
  is at or below the margin; both at the OD-19 family-wise α. Options for the margin: 0.05 (needs about 120
  `tool-unnecessary` items, OD-8) or 0.10 (needs about 60). Evidence: no 2×2 data yet; a superiority
  framing would let over-callers through. Recommendation: margin 0.10 with OD-8 (b), at OD-19 α 0.05.
- **OD-10 — ADR 0038 and the tool contract.** Options: amend ADR 0038 before `_meta` or server
  instructions ship; a new ADR. The former option "drop those arms" was removed: REQ-033 and OD-14
  require them; they stay laboratory-only until the decision is recorded. Evidence: ADR 0038 governs the
  `analyze-work` contract and its D12 cap and says nothing about `_meta` or server instructions.
  Recommendation: amend ADR 0038; laboratory builds can measure first.
- **OD-11 — Hook in released plugins.** Options: laboratory only; opt-in user configuration; on by default.
  Evidence: no measurement exists; a hook adds context to every prompt, a new authority and privacy
  surface (Security and privacy). Recommendation: laboratory only until gate B passes, then opt-in.
- **OD-12 — Explicit command.** Options: (a) document the existing plugin skill, invoked as
  `/agent-braid:analyze`, as the explicit entry, adding no surface; (b) add a new plugin command named
  under ADR 0030. Evidence: ADR 0030 decision 3 names plugin skills without the brand prefix inside the
  plugin namespace, so `analyze` already exists. Recommendation: (a).
- **OD-13 — `claude plugin eval` contrast.** Options: run once as a non-gating contrast on 20 items × 3
  runs with and without the plugin (120 rollouts); skip. Evidence: its behaviour on this host is
  unverified. Recommendation: run once.
- **OD-14 — Target kinds.** Options: skill description; server instructions; tool description (bound by
  the D12 cap). Evidence: the `analyze-work` definition sits near the D12 cap (about 1,499 of 1,500
  tokens), so a tool-description target has almost no room. Recommendation: the first two.
- **OD-15 — Milestone.** Options: BL.2c (provisional, used in tracking now); a new BL milestone created by
  the owner, shared with SPEC-090. Evidence: no milestone for Lightning evaluation exists in
  `github-tracking.json`. Recommendation: a new milestone, the same as SPEC-090 OD-10.
- **OD-16 — Skill `paths` field.** Options: measure it as a lever; skip. Evidence: path-gated skills were
  opened 28 of 66 times against 0 of 198 for always-on skills (2610.14216, lead), but this skill has no
  natural file-type trigger. Recommendation: only if the development factorial points to file-type
  triggers.
- **OD-17 — Per-item outcome for gate B.** Options: (a) item majority call (at least 2 of 3 rollouts call
  `analyze-work`) for both metrics, with exact Clopper–Pearson bounds over items; (b) item mean call rate
  with a cluster bootstrap or beta-binomial bound, admissible only as a secondary description, because
  OD-3 and OD-9 use exact bounds; (d) majority call for recall and any call (at least 1 of 3) for the
  false-positive metric, with exact bounds. The former option "rollout-level shares" was removed: it
  contradicts REQ-001 and is anti-conservative (ICC 0.81 on v4). Evidence: majority call is lenient for
  false positives, since a call in 1 of 3 rollouts on an unnecessary item is not counted although the
  user would have seen it. Recommendation: (d), with (b) reported.
- **OD-18 — Equivalence margin η for the interaction.** Options: ±0.10, ±0.15 or ±0.20 on the difference of
  differences in item-level recall (and separately in the false-positive rate). Evidence: at p near 0.5 the
  standard error of the item-level difference of differences is about 1/√k for k items per cell counted
  for that metric (own calculation): 67 recall items give about 0.12, so TOST at ±0.10 has almost no power;
  about 80 % power at a true interaction of zero needs about 856 recall-labelled items per cell for ±0.10,
  381 for ±0.15 and 214 for ±0.20, and as many `tool-unnecessary` items for the false-positive metric.
  Recommendation: ±0.15 if OD-7 reaches about 380 recall items per cell; otherwise state before the run
  that H2 is likely inconclusive at the planned size.
- **OD-19 — Family-wise α for levers and effects.** Options: 0.05 with Holm within each family (H1 levers ×
  two metrics; the two 2×2 main effects); 0.10 with Holm; no adjustment, reported as exploratory.
  Evidence: up to five levers on two metrics would inflate false claims without adjustment.
  Recommendation: 0.05 with Holm.
- **OD-20 — Arm under test in T014 and T015.** Options: (a) the best 2×2 cell that met OD-9, with text
  optimization (T013, T019) only if that cell misses the OD-3 bounds on its 2×2 estimates; (b) always the
  T019 selection winner; (c) both, on two held-out sets. It is recorded before T019 runs, never after an
  audit result is visible. Evidence: selection adds an estimated 2,949 rollouts at the recommended ODs (Budget table; the actual
  count follows OD-7, OD-28 and the pilot discordance) and one
  contrastive rewrite captures most of the gain while further iterations move F1 by less than 0.5 %
  (2606.30775, paper). Recommendation: (a).
- **OD-21 — Label agreement threshold.** Options: Cohen's κ of at least 0.6 or 0.8 on each label pair.
  Evidence: no labels exist yet; below the threshold the rubric is revised and items relabelled (REQ-002).
  Recommendation: 0.6, with both metrics also reported on the agreed-only subset.
- **OD-22 — Gate B tripwire: twin size and margin.** Options: twin of 20 or 40 recall-labelled items × 1
  repetition; margin 0.05 or 0.10 below the T008 invocation rate on recall-labelled items. Evidence: on v4
  the unprompted call rate was 53/300, about 0.18, so the gate A threshold would refuse every gate B
  split. Recommendation: 20 × 1, margin 0.10.
- **OD-23 — Gate B noise pilot size (T008).** Options: 20 or 40 development items × 3 repetitions × 3 runs
  (two candidate arms plus an A/A pair). Evidence: none for gate B. Recommendation: 20 items (180
  rollouts).
- **OD-24 — Lever screening size (T018).** Options: 60 recall-labelled plus 60 `tool-unnecessary` items × 3
  repetitions × 3 arms (1,080 rollouts); 120 plus 120 (2,160). Evidence: OD-8 (b) needs about 60
  `tool-unnecessary` items for a 0.10 margin. Recommendation: 60 plus 60.
- **OD-25 — Gate B held-out and audit sizes.** Options for the held-out (T015): 150 recall-labelled plus 60
  `tool-unnecessary` items × 3 (630 rollouts), or 300 plus 120 (1,260); for the labelled gate B audit set
  (T022): 90 or 180 items. Evidence: OD-7 and OD-8 arithmetic. Recommendation: 150 plus 60, and 90.
- **OD-26 — Product scope: explicit-only or unprompted invocation.** Options: (a) explicit-only: gate B is
  not run, and the documented command (OD-12) is the supported path; (b) unprompted invocation is a
  requirement and gate B runs. Evidence: v4 baseline 53/300 unprompted calls; gate B costs an estimated 8,234
  rollouts with selection or 5,285 without at the recommended ODs (Budget table: 12.5 to 38.9 hours at 8.5
  to 17 s per rollout), against an estimated 575 for gate A; the actual counts follow the size ODs. Trade-off: (a) saves that budget and the hook's authority and
  privacy surface but leaves users who do not name the product without the tool; (b) pursues that use at
  the stated cost. Recommendation: none; this is the owner's product call.
- **OD-27 — Gate B pilot arms.** No candidate exists before selection, so the noise pilot's two arms need
  a definition. Options: (a) the shipped build and one named lever build (for example the use-case-first
  description overlay), digests frozen in the pilot freeze; (b) the shipped build twice only (A/A, no
  discordance estimate). Evidence: the paired sizes of OD-7 and T019 need a discordance between two
  different arms (REQ-012). Recommendation: (a), with the lever named by the owner at T001.
- **OD-28 — Gate B selection margin δ_B.** Options: 0, 0.02 or 0.05 in item-level recall advantage over
  the incumbent. Evidence: as SPEC-090 OD-3, the confirmation size grows as 1/(Δ_B − δ_B)²; with discordance
  0.10 and a gap of 0.10, about 75 recall items per arm at the Holm worst case 0.05/3 (own calculation).
  Recommendation: 0.02.

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

Verification is complete when the obtained evidence for SC-001 to SC-046 in the
[validation plan](validation-plan.md) exists, the simulation record (T007) and the pilot reports (T008,
T009) are committed, the 2×2 factorial result is recorded (T012), and the T017 converge record is written.
A null, negative or invalidated result is a valid completion when recorded. Passing checks are not approval.

## Open questions

- OD-1 to OD-28 above; owner: the founder.
- Whether each real run (T008, T009, T018, T012, T019, T023, T021, T015, T016) happens; owner: the founder.
