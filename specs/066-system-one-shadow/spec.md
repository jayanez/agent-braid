# SPEC-066: System One shadow activation and reference-grade decisions

**Track:** S1.5 — System One shadow activation (resumes the deferred System One
program, SPEC-028–033; never a gate of the core, of M4.x, HAR or VIS)

**Status:** draft specification. The owner chose this direction on 2026-11-01
("Shadow + datos propios") and asked to adopt the strongest capabilities of the
Laya and Jev references; the decision is recorded in
[founder decisions 2026-11-01](../../docs/development/FOUNDER_DECISIONS_20261101.md).
The owner refined the direction on 2026-11-01 (binding): System One has its own,
fully native layer-1 decision system, and Laya and Jev are design references
only (see Exclusions). The owner accepted this scope, the H-S1 thresholds and the
privacy design in
[owner-review-20261101.md](owner-review-20261101.md).
[ADR 0034](../../docs/adr/0034-system-one-shadow-advisory-boundary.md) records the
advisory boundary. Human review of this specification stays pending.

## Why this specification exists

The 2026-11-01 completeness audit
([audit](../../docs/system-one/addenda/completeness-audit-20261101/README.md))
found that System One is present but unused:

- About 4,360 lines of `agent_braid/system_one*.py` and `mcp_advice.py` are on
  `develop`, but no product path calls them. The only user entry point is the
  opt-in `agent-braid system-one` command over synthetic fixtures. The advice
  wrappers `analysis.analyze_with_advice`,
  `structured_exchange.verify_candidates_with_advice` and
  `runtime_scheduler.select_ready_rank_hint` have no source callers.
- No learned model exists: `BACKEND_ID = "stdlib-rule-fixture-v1"`, calibration
  is the constant `absent`, and the strict policy always abstains.
- Use cannot be observed: telemetry has no System One operation, and real-use
  sources on 2026-11-01 contain zero System One invocations.
- The reopen condition of the deferred work (SPEC-029 T001 source permission with
  admitted real groups) depends on RF-T03/T04/T05, which have no owner. The
  original design also required blind labelling by two human reviewers, which a
  one-person project cannot supply.

The useful question is not whether a learned model can repeat the deterministic
analyzer: System 2 here is exact and cheap. System One earns its cost only where
System 2 is undetermined. Today that means pairs classified `unknown` because a
footprint is partial or an effect is external, where an operator must still decide
whether to serialize. Their ground truth arrives later as an observed outcome.

## Purpose and scope

This specification turns System One into a measured, owner-consented, local
subsystem in stages:

1. **S1.5a (this delivery): shadow mode.** For every successful `analyze-work`
   call, record one System One decision episode next to the unchanged System 2
   result, without changing any output. The runtime `analyze` tool returns
   evidence and an advisory plan without the interaction report, so it yields no
   episode in v0.1.
2. **S1.5b: owned corpus.** Admit the owner's own episodes and real-use sources
   as a permissioned corpus, and join episodes with later observed outcomes.
3. **S1.5c: reference-grade contracts.** Adopt the strongest Laya/Jev decision
   semantics without a model: tri-state abstention, risk-scaled thresholds, two
   declared confidence signals, pinned identity with drift demotion, batched
   questions over one state, option-order invariance and an evaluation gate.
4. **S1.5d: native learned model.** Add a small native model (calibrated
   logistic regression or boosted trees, stdlib only) over structural features
   behind the existing `Backend` protocol, with our own architecture, training and
   weights. It is fitted on the owned corpus, calibrated with temperature or
   isotonic scaling and abstention thresholds on a separate calibration split, and
   compared at a common risk budget with rules and SPEC-019's linear model. It
   includes an ablation of the per-repo salted resource hashes (REQ-003).
5. **S1.5e: go/no-go per decision point.** Move from `shadow` to `advise` only
   where measured improvement and calibration are accepted by the owner, with
   atomic rollback to `off`.

Only S1.5a is specified to implementation level here. S1.5b–e carry outline
requirements; each needs its own plan and task review before implementation.

Claim level (labels of [claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md)): engineering and hypothesis. H-S1 is a registered
hypothesis (below); nothing in S1.5a supports it or any utility claim.

Exclusions:
- No change to any analysis, preparation, scheduling or runtime result.
- No new execution authority: `executionAuthorization` stays the constant false.
- No network access and no remote service.
- No external services, third-party decision models, or pretrained encoders, ever
  (owner direction 2026-11-01). This covers Jev/TypeSafe or any hosted service,
  Laya, Von, kev, Rizzo, SemIf, Nimble, NanoJev and Strands Decider as local
  backends, and generic pretrained encoders (ModernBERT, mmBERT, Qwen and the
  like). Laya and Jev are design references only: ideas are re-implemented by us.
- No content, paths, resource names, identifiers or prompts in episodes.
- No change to the SPEC-047 telemetry store or its batch schema.
- No change to the portable MCP envelope.

## Decision points

| ID | Decision point | System 2 today | System One question | Label source |
|---|---|---|---|---|
| DP-1 | Unknown-pair resolution | `unknown`, serialize unless stronger evidence | choice: `likely-independent` / `likely-conflicting` / `undetermined` | Observed outcome of the later run or merge (S1.5b) |
| DP-2 | Ready-rank hint | Original order | ordering hint | Observed completion order and conflicts (S1.5b) |
| DP-3 | Tool-call risk advice | None | boolean risk advice, never a boundary | Owner adjudication (S1.5b) |

S1.5a instruments DP-1 only. It records every pair, marks whether System 2 was
determinate, and records a System One answer from the installed backend. With the
reference rule backend, that answer is an abstention.

## Requirements — S1.5a (implementation level)

**REQ-001 Consent and mode.**
- The plugin registry gains an optional `systemOne` consent with values `off` and
  `shadow`; a missing value means `off`.
- `agent-braid plugin setup --system-one {off,shadow}` persists it. It applies
  after reconnect, like telemetry consent.
- When the value is `off`, the registry bytes and `configuration_digest` are
  unchanged from the current schema.
- `ToolingConfig` gains `system_one: str = "off"` and refuses other values.
- Shadow requires an explicit `shadow` consent; telemetry consent never implies it.

**REQ-002 Output parity.** In `shadow` mode, every MCP envelope is byte-identical
to the envelope in `off` mode for the same input. This covers `analyze`,
`analyze-work`, `prepare` and all runtime tools.
- Shadow work runs after the envelope is built. The request path only hands the
  report to one background worker with a single-slot queue and never waits for
  it; when the worker is busy, the report is dropped and counted (`busy`).
  Artifact-backed reports above 1 MiB are not decoded (`oversize-report`).
- Shadow work never raises into the caller.
- Shadow work stays within a fixed budget of 50 ms of wall time per call; over
  budget, the episode is recorded as `skipped`.

**REQ-003 Episode contract.** Each successful `analyze-work` call (AIM or Git) in
`shadow` mode appends at most one episode that conforms to
[agent-braid-s1-episode/v0.2](contracts/episode-v0.2.md); lines written as
[v0.1](contracts/episode-v0.1.md) stay readable. Episodes contain only derived
structural features:
- the System 2 classification, reason codes (including `read-version`) and
  constraints
- coverage statuses
- shared-resource counts and a dependency flag
- complete per-class pair counts, so shares cover pairs beyond the 64-pair cap

v0.1 recorded per-side effect kinds as `null`. v0.2 enriches the episode with structural features: resource classes
(src/test/docs/config/lockfile/generated), path depth, directory overlap and
per-side effect kinds taken from the request (AIM) or from the Git adapter's resource schemes. It adds per-repo salted resource
hashes in a separate field, used only by the S1.5d ablation (hashes are kept only
if they measurably improve precision without degrading calibration).

Episodes contain no resource names, paths, identifiers, unsalted digests of
content, or text.

**REQ-004 Local private store.**
- Episodes go to `~/.local/share/agent-braid/system-one/episodes-<UTC date>.jsonl`.
- The store reuses the telemetry location rules: canonical paths, no symlinks,
  outside repositories, owner-only permissions, single hard link.
- It is bounded: at most 4 MiB per day file, at most 64 pairs per episode, and 30
  UTC dates retained on access.
- A busy, unsafe or full store refuses the episode and counts the refusal in
  memory. It never blocks or fails the caller. Refusals and internal errors
  before storage exist only as these in-memory counts.
- The 50 ms budget is a work budget checked between stages; it bounds the
  episode computation, not a filesystem write.

**REQ-005 Usage report.**
- `agent-braid system-one report` prints the retained episode counts per day,
  operation, System 2 classification and System One status. It also prints the
  share of System 2 `unknown` pairs, which is the DP-1 opportunity.
- `--format json` emits `agent-braid-s1-report/v0.1`: per-day and total counts
  of episodes, operations, recorded System 2 classes, all analysed pairs per
  class and System One statuses, plus `pairsRecorded`, `pairsAnalysed`,
  `unknownPairs`, `unknownShare` (over all analysed pairs), `invalidLines`,
  this process's refusal counts, limits and `executionAuthorization: false`.
- `agent-braid system-one purge` deletes the store after confirmation, or with
  `--yes`.
- The report reads only the store and never prints episode bodies.

**REQ-006 Observable command use.**
- The `system-one` CLI command accepts `--telemetry {off,local}`, default `off`,
  and runs under the existing `observe` wrapper.
- Telemetry gains the CLI operation `system-one`. This is the only telemetry
  change: aggregates only, no new metric.

**REQ-007 Pinned identity.**
- Every episode records the backend identifier, the model-manifest digest and the
  analyzer rule set.
- If the installed backend's manifest digest differs from the digest compiled
  into the shadow module, the shadow records `refused` with reason
  `identity-mismatch`. The output is still unaffected.

**REQ-008 Plugin status.** `plugin-status` reports
`systemOne: {configuredMode, activeMode, store: {location, present},
episodeRetentionDays: 30}`. It never reports episode contents.

## Requirements — S1.5b–e (outline; need their own plan review)

- **REQ-101 Owned-source admission (S1.5b).** An owner consent record admits the
  owner's own work as the only training population: (1) real runs (execute and
  verify results, real conflicts, the SPEC-059 ledger, SPEC-053 transcripts) and
  (2) git-history replay (REQ-104). It closes SPEC-029 T001 for the owned
  population only. It reuses the SPEC-051 pure owned-work validator (ADR 0026).
  Third-party sources stay excluded. Admission is restricted to
  plugin-registered workspaces; any future repository requires the owner's
  express approval first.
- **REQ-102 Outcome observer (S1.5b).** Join DP-1 episodes with the later observed
  outcome from the sources of REQ-101: a runtime conflict, a merge conflict, a
  verify pass or fail, or a replayed branch/commit outcome (REQ-104). Pairs
  without an observed outcome stay unlabelled, never imputed.
- **REQ-104 Git-history replay labels (S1.5b).** Labels also come from replaying
  the git history of the owner's repositories: pairs of real branches or commits
  are taken from history, the observed conflict is obtained with
  `git merge-tree`, and the SPEC-012 replay planner is reused. The replay is
  restricted to plugin-registered workspaces; adding a repository requires the
  owner's express approval. Replayed pairs yield structural episodes only, with
  the same privacy rules as REQ-003.
- **REQ-103 Amended label rubric (S1.5b).** Observed outcomes are primary labels.
  Owner adjudication of a random sample measures label noise. This replaces
  SPEC-029's two-blind-reviewer requirement for the owned population and is
  reported as a limitation.
- **REQ-201 Tri-state abstention (S1.5c).**
  - Responses carry `abstention: passed | abstained | unevaluated`.
  - The applied threshold is echoed back.
  - Thresholds are set per bucket and scale with risk.
  - Thresholds are fitted only on a calibration split disjoint from evaluation.
- **REQ-202 Declared confidence (S1.5c).** Responses carry two named signals with
  stated formulas: normalized entropy and maximum probability. Neither is called
  accuracy.
- **REQ-203 Drift demotion (S1.5c).** If a different backend identity answers, or
  answers within one batch mix identities, the decision point demotes to `off`
  until a new calibration is pinned.
- **REQ-204 Batched questions (S1.5c).** Several typed questions are evaluated
  against one state, and bounded batches of states are supported, with
  per-question failure isolation.
- **REQ-205 Option-order invariance (S1.5c).** Choice answers are averaged over
  rotations of the option order. Equivariance tests report the share of answers
  that flip.
- **REQ-206 Evaluation gate (S1.5c).** CI checks minimum accuracy, maximum ECE,
  per-slice metrics and tolerance against a committed baseline on the admitted
  corpus.
- **REQ-301 Native learned model (S1.5d).** A native model module inside
  `agent_braid`, implemented with the standard library only (`pyproject.toml`
  declares `dependencies = []`, so numpy is not available and is not introduced).
  It is a small model (calibrated logistic regression or boosted trees) over
  structural features, with our own architecture, training and weights, fitted on
  the owned corpus. Temperature or isotonic calibration and abstention thresholds
  are fitted on a separate calibration split. It includes an ablation with and
  without the per-repo salted resource hashes, keeping the hashes only if they
  measurably improve precision without degrading calibration. It is compared at a
  common risk budget with the rule backend and the SPEC-019 linear model. A
  NO-GO is a valid result.
- **REQ-401 Promotion (S1.5e).** `advise` per decision point only after an owner
  go decision on recorded shadow evidence, with atomic rollback to `off`.

## Hypothesis

**H-S1** (thresholds confirmed by the owner on 2026-11-01). On the owner's DP-1 pairs that System 2 marks `unknown`, a calibrated
local System One backend can advise `likely-independent` with an observed false
independence rate of at most 2% at a coverage of at least 30% of those pairs.
Falsification: the S1.5d paired comparison does not reach both bounds at the
common risk budget. Null and negative results are valid outcomes. Nothing in
S1.5a tests H-S1.

## Success criteria (S1.5a)

- SC-001: The parity test shows identical envelopes in `off` and `shadow` mode for
  fixtures of every tool.
- SC-002: Episodes validate against the v0.1 contract, and a seeded test
  confirms they contain no input strings.
- SC-003: Store refusals (unsafe path, oversize, busy) leave the caller's result
  and timing within budget.
- SC-004: `system-one report` reports counts that match seeded episodes.
- SC-005: With `systemOne` absent or `off`, the registry digest is unchanged.
- SC-006: A real owner session in `shadow` mode produces at least one episode,
  recorded as a redacted receipt under `docs/development/REAL_USE_EVIDENCE.md`
  rules. This is a pending owner-run check, not implied by tests.
- SC-007: `system-one --telemetry local` records a CLI `system-one` aggregate
  and nothing else (REQ-006).
- SC-008: A changed backend manifest digest yields `refused` /
  `identity-mismatch` episodes and unchanged envelopes (REQ-007).
- SC-009: `plugin-status` shows the configured and active modes and the store
  presence, and no episode data (REQ-008).

## References

- Laya (`NandhaKishorM/laya`, v0.4.19, Apache-2.0) and Jev (TypeSafe AI, hosted)
  are design references only, summarized in
  [reference analysis](../028-system-one-core/reference-analysis.md). Neither is a
  dependency, backend or training source of any stage; their ideas are
  re-implemented natively.
- Earlier System One record: [system-one corpus](../../docs/system-one/README.md).
