# Roadmap

The roadmap follows evidence, not calendar promises. Milestones are exit-criterion driven.

The [spec and milestone index](docs/development/SPEC_MILESTONE_INDEX.md) maps all
38 specs to the 18 registered GitHub milestones. Titles follow `ID — Capability`;
track prefixes do not establish an implementation sequence. Historical closure
records retain their original names, scope and decisions.

<a id="m05--open-strategy-and-research-preview-preparation"></a>

## M0.5 — Open strategy and preview preparation

**Status:** closed internally on 2026-09-19 against candidate
`d7bff443729571e031180b4c31920632e2a7d3ae`; see the
[closure record](docs/releases/M0_5_CLOSURE.md). The research-preview proposal is
approved; publication, repository visibility and history operations were outside
that closure's authorization. The later
[cutover audit](docs/releases/publication/CUTOVER_AUDIT_2026-09-25.md) records public
availability and the separate historical authorization-reconciliation gate.
Independent validation remains `pending`.

**Objective:** turn the validated foundation into an inspectable open-tooling
thesis without weakening the scientific boundary.

Deliverables:

- product thesis, ecosystem map, market model, and community impact metrics;
- versioned scientific and technology radar with weekly, monthly, and milestone cadence;
- formal M0 readiness inventory with pending human and founder decisions;
- local read-only alpha analyzer and a versioned analysis-report contract;
- editable international trends report updated at milestone boundaries.

Exit criteria:

- the certificate pilot has a recorded human review decision;
- the founder separately approves the bounded M0.5 review, M0.5 closure and the
  research-preview proposal;
- a clean internal reproduction is bound to a frozen candidate and the founder
  approves its stated limits before a research-preview proposal;
- independent validation is reported transparently and invited publicly, but is
  not a publication or milestone gate under ADR 0009;
- the analyzer reference corpus has zero false-safe `independent-candidate` classifications;
- market scenarios expose assumptions, units, uncertainty, and double-counting rules;
- no artifact claims production safety or general Yang–Baxter validity.

<a id="m0--formalization-before-implementation"></a>

## M0 — Operational foundations

**Status:** closed internally on 2026-09-18; see the
[closure record](docs/releases/M0_CLOSURE.md). This is not a claim of
independent reproduction, production safety, or a general mathematical result.

**Objective:** establish a shared semantic and scientific foundation.

Deliverables:

- constitutional principles and claim discipline;
- canonical terminology;
- initial operation/effect/trace/certificate models;
- AIM draft schema;
- experiment and counterexample protocols;
- ADRs for foundational choices;
- repository validation in CI.

Exit criteria:

- every core term has a testable working definition;
- a bounded interpreter, negative controls and scoped certificate checks run locally;
- independence and schedule-equivalence premises are explicit and linked to tests;
- the constitutional proposal has completed its required dedicated review;
- the schema represents at least text edits, tool reads, external writes, and deployment effects;
- two alternative schedules can be described without host-specific vocabulary;
- at least two host-origin workloads are representable through the same
  canonical AIM concepts without implying adapter correctness or execution;
- unresolved mathematical questions are explicit;
- the adopted license map, contributor terms, and trademark policy are present
  and validated.

## M1 — Observable interaction analyzer

**Status:** closed internally on 2026-09-18 against candidate
`fa958277bd919c827e781df63d8371afd6f111c9` after an approved bounded M1 radar
review, a 14-observation clean-room reproduction and separate founder
scientific-review and closure decisions. See the
[closure record](docs/releases/M1_CLOSURE.md). Independent validation remains
`pending`; no production-safety or execution-authorization claim is made.

**Objective:** deliver practical conflict and independence analysis without executing agents.

Deliverables:

- CLI for AIM manifests and recorded traces;
- read/write/effect-set extraction;
- conflict and interaction graph;
- pairwise commutation classifications;
- Git diff/worktree adapter;
- human- and machine-readable analysis reports.

Exit criteria:

- benchmark fixtures cover commuting, conflicting, conditional, and unknown pairs;
- no unsafe pair is labeled commuting in the reference corpus;
- results expose evidence and assurance level;
- performance is measured against file-level and Git merge baselines.
- M1 receives separate founder scientific-review and closure decisions against a
  frozen clean-room reproduction; external validation may remain `pending`.

The Git/worktree adapter architecture is accepted in ADR 0008. Its first corpus
measures syntactic path observations only; M1 closure does not establish semantic
commutation or correctness beyond the declared corpus.

<a id="m2--confluence-laboratory-and-scheduler"></a>

## M2 — Confluence lab and scheduler

**Objective:** explore schedules in isolation and convert evidence into consultative preparation plans.

The first implementation cut is tracked by
[`012-m2-git-replay-planner`](specs/012-m2-git-replay-planner/spec.md). It replays
all admissible orders for 2–4 fixed commit patches in a temporary bare repository
and fresh index, observing `tracked-tree-v1`. Follow-up work added bounded Git
resource controls, a read-only parallel-integration prototype and synthetic
benchmarking. Preparation waves remain advisory; integration is serial and every
plan has `executionAuthorization: false`.

The real-workload experiment in
[`013-m2-real-workload`](specs/013-m2-real-workload/spec.md) is complete under
its separately approved corpus and ADR 0015 profile. The internal normalizer and
counterexample-reduction increments in
[`014-m2-observation-normalizer`](specs/014-m2-observation-normalizer/spec.md)
and [`015-m2-counterexample-reducer`](specs/015-m2-counterexample-reducer/spec.md)
are also merged and reviewed. Their evidence remains limited to fixed-patch Git
replay and `tracked-tree-v1`. The private
[`016-m2-partial-order-reduction`](specs/016-m2-partial-order-reduction/spec.md)
candidate compares selected replays with the exhaustive 2–4 operation oracle.
Its repeated-context real-Git fixture also supplies the positive end-to-end
reduction absent from SPEC-015's original review. Its bounded internal review
was approved on 2026-09-26; the approval confirms that the oracle is regenerated
and checked by the existing verifier, not by an independent replay engine, and
that uncertain paths prevent interchange. The final M2 candidate
`61e731aeb1cb631b9c0d083f71d38ca620cc4742` passed 17/17 internal
clean-room observations. The founder separately ratified its bounded scientific
review and approved internal M2 closure on 2026-09-27. Independent external
validation remains pending; see the [closure record](docs/releases/M2_CLOSURE.md).

The [readiness review](docs/releases/M2_READINESS_REVIEW.md) and final
candidate-bound record support all four M2 exit criteria only within their
declared finite Git and read-only preparation domains. SPEC-016 remains a
private experiment; its promotion requires a separate contract. Broader
workload adapters, executable integration and ref promotion require their own
reviewed contracts and authorization. M2 closure supplies none of these.

Deliverables:

- schedule enumerator and partial-order reducer;
- sandboxed replay adapters;
- normalizer interface;
- confluence certificates;
- minimal counterexample reducer;
- constraint-aware scheduler.

Exit criteria:

- certificates reproduce from immutable fixtures;
- the scheduler recovers parallelism over sequential execution;
- the observation contract is fixed before execution and all excluded differences
  remain in raw traces; terminal projection is never claimed contextual;
- destructive/external effects default to safe policies.

Technology and functionality adoption is governed by the
[radar-to-adoption pathline](research/adoption/ADOPTION_PATHLINE.md). OpenAI
Agents and MCP may enter bounded local spikes first; A2A requires a selected
version and conformance artifact; OpenTelemetry remains optional while relevant
conventions are experimental; external research algorithms remain comparators
until reproduced. No weekly radar signal changes M2 contracts automatically.

## M3 — Braid semantics

**Objective:** test whether meaningful exchange operators exist beyond independent swaps.

The first candidate is [SPEC-018](specs/018-structured-exchange/spec.md):
bounded anchored-sequence insertion with context-dependent residual positions.
Its experimental evidence is consultative. The founder approved ADR 0017 and
SPEC-018 as a bounded experiment, then separately approved internal M3 closure
on 2026-09-27 for `anchored-sequence-v1`; see the
[closure record](docs/releases/M3_CLOSURE.md). Finite success and a candidate
mathematical argument do not establish a general scientific result. External
independent validation remains pending. M2 fixed-patch evidence is not
promoted to this new domain.

Deliverables:

- residual-operation interface;
- executable braid relation tests;
- property-based generation of triples;
- catalog of positive classes and counterexamples;
- formal specification for the strongest surviving class.

Exit criteria:

- at least one nontrivial exchange class is defined precisely;
- braid tests are reproducible and convention-explicit;
- claims distinguish empirical, exhaustive finite, and proved results;
- runtime consequences are quantified.

<a id="m35--native-specialized-proposal-predictor"></a>

## M3.5 — Native proposal predictor

**Objective:** test whether a small, local learned advisor improves selection
of candidates for the deterministic M3 verifier. [SPEC-019](specs/019-native-predictor/spec.md)
is a draft for offline training, versioned structural features, held-out
evaluation and abstention. It is independent of M3 closure. A score is
heuristic; the verifier remains the only source of bounded exchange evidence.
No external Laya/Jev service is required or integrated.

## M4 — Agent Braid runtime

**Objective:** integrate analysis, scheduling, execution, and certificates in a model-agnostic runtime.

The first bounded increment is [SPEC-020](specs/020-m4-local-git-runtime/spec.md):
a separately authorized private Git result, serial isolated fixed-patch execution,
per-step effect/result checks and process-crash recovery. It has no dependency
on M3/M3.5 data. ADR 0019 and this bounded increment were
[accepted by the founder](specs/020-m4-local-git-runtime/founder-review.json)
against frozen candidate `4dd52c8` on 2026-10-03; source promotion, repository-code execution and external adapters
remain separate contracts. This does not close the full M4 milestone.

The proposed completion track is [SPEC-021](specs/021-m4-alpha-runtime/spec.md),
with a [six-row alpha exit matrix](specs/021-m4-alpha-runtime/closure-matrix.md).
The founder approved its scope against frozen candidate `0de9d31` and adopted
[ADR 0020](docs/adr/0020-bounded-m4-alpha-runtime.md) on 2026-10-04.
Implementation is authorized within the documented gates; whole-M4 acceptance
remains a separate decision.

On 2026-10-05 the founder recorded a G4 NO-GO for accepting SPEC-021 as a useful
speedup capability under the current evidence. Six paired trials produced
equivalent verified trees, but their median serial/parallel total-wall ratio was
0.5581 in a small, uncontrolled sample. This does not show that parallelism is
generally unhelpful and does not close M4. SPEC-021 and the M4 milestone remain
open; the decision and its limits are recorded in
[`g4-decision.json`](specs/021-m4-alpha-runtime/g4-decision.json). M3/M3.5
scientific gates are unchanged.

The [2026-10-06 engineering delivery](docs/development/autonomous-delivery.md)
obtained fresh hosted Linux x64 controls (44 M3.5 synthetic tests and 68 M4
runtime/protocol tests), reduced redundant preparation and retained a separate
descriptive cost record. Parallel execution still cost more than serial on the
owned fixture. Governed tracking was reconciled; administrative T014 completion
merged in [PR #220](https://github.com/jayanez/agent-braid/pull/220) and
[issue #218](https://github.com/jayanez/agent-braid/issues/218) closed on 2026-10-06.
This delivery leaves the G4 NO-GO, SPEC-021's open state and M4's open milestone
in effect.

Candidate deliverables:

- MCP and host-runtime adapters;
- transactional/isolation policies;
- live effect verification;
- replay and recovery;
- CI and policy gates;
- portability tests across agent environments.

This milestone proceeds only if validated M1–M2 engineering results justify the
complexity. M3 is an independent research track: a negative braid result cannot
block useful, sound engineering. Real adapter refinement remains a prerequisite.

## Parallel mathematical laboratory

The project may expose selected GAP/YangBaxter, SageMath, SnapPy, quimb, or proof-assistant capabilities when a concrete research hypothesis requires them. The laboratory remains modular and cannot block the practical analyzer.

## Deferred decisions

- implementation language and package topology;
- changes to the established licensing boundary;
- governance expansion beyond founder-led decisions;
- hosted service or commercial offering;
- specific model/runtime integrations.

Each requires an ADR or governance decision with alternatives and consequences.

## Adoption overlay

The technical milestones remain authoritative. Adoption is a second dimension:

| Stage | Technical gate | Adoption focus |
|---|---|---|
| Software | M1–M2 | Local code, Git, worktree, CI, and recorded-trace workloads |
| Platforms | Stable M2 contracts | Generic trace, OpenAI Agents, MCP, then evaluated A2A/NeMo adapters |
| Enterprise | Defensible M4 execution contracts | Recorded traces and dry-runs before any external write path |

M3 remains an independent research line. Platform adapters translate into AIM;
they do not fork the semantics. Enterprise progression additionally requires
authorization, idempotency, isolation, privacy, guardrails, and recovery review.

## Foundational implementation portfolio — 2026-10-05

The [review and implementation portfolio](docs/development/FOUNDATION_IMPLEMENTATION_PORTFOLIO.md) maps foundational obligations to existing and proposed work. This portfolio began as a dated proposal. As of 2026-10-07, SPEC-022 measurement instrumentation and its 180-minute successor preparation are implemented, SPEC-027 provides read-only refinement assessments, and SPEC-028 provides a synthetic System 1 reference core. Registered capture, capability adoption and human acceptance retain their separate gates; creating tasks does not adopt execution contracts or promise a positive research result. Closed milestones retain their historical scope.

| Milestone / track | Implementation or next package | Exit boundary |
|---|---|---|
| M3.5 | [SPEC-019 preparation](specs/019-native-predictor/implementation-readiness.md) | Metadata/synthetic tooling first; real-source rights, yield, protocol and labels before fitting |
| M4 | [SPEC-022 utility follow-up](specs/022-m4-utility-followup/spec.md) | Instrumentation and owner-approved 180-minute successor preparation implemented; exact stable-harness/capture review, registered comparison and a new utility decision remain pending; preserve SPEC-021 NO-GO |
| M4 real workload | [SPEC-038](specs/038-m4-real-workload-closure/spec.md) | Exact source rights and protocol approved; bounded harness merged and validated; two frozen operations/20 slots statically admitted and technically reviewed; owner stable-candidate/manifest review, capture and a new whole-M4 founder decision remain pending |
| M4 refinement contracts | [SPEC-027](specs/027-runtime-refinement-contracts/spec.md) | Read-only source-promotion, code-isolation and external-effect assessments implemented; each capability still needs a recorded disposition, separate adoption and execution authority |
| ADP.1 — Recorded-trace adapters | [SPEC-023](specs/023-recorded-trace-adapters/spec.md) | Conservative offline trace mappings and reviewed spike/adoption decisions; no execution authority |
| LAB.1 — Effectful workload lab | [SPEC-024](specs/024-effectful-workload-lab/spec.md) | Reproducible finite simulated effects, failures and nondeterminism; no real external adapters |
| RES.1 — Formal interaction research | [SPEC-025](specs/025-contextual-proof-obligations/spec.md) | Bounded contextual controls, explicit proof premises and reviewed restricted claims/comparator feasibility |
| GOV.1 — Governance and adoption | [SPEC-026](specs/026-adoption-evidence-program/spec.md) | Auditable adoption/impact and reproduction intake, plus current historical-tracking reconciliation |

The three new milestones are capability/exit driven and have no calendar deadline. Platform runtime expansion, source promotion, arbitrary-code isolation, real databases/API/deploy execution, new paid services and proof-assistant dependencies need separate reviewed contracts and authorization. Their next step is a feasibility/contract decision in the relevant package rather than implicit implementation authority. Existing adoption tracks retain `watch` and `research-only` dispositions until a new recorded decision.

<a id="proposed-native-system-1-track"></a>

## Native System 1 implementation track

The [System 1 planning program](specs/028-system-one-core/program.md) contains
SPEC-028–033: typed advisory contracts, prospective evaluation, an own neural
decision experiment, bounded integration, advanced product capabilities and
separate promotion/rollback. The [reference analysis](specs/028-system-one-core/reference-analysis.md)
compares Strands Decider and Laya without integrating either project. Five registered
S1 milestones and 49 pending tasks complement existing tracks; they do not replace
SPEC-019 or reopen SPEC-021's M4 utility NO-GO. Architecture, data, budgets and
per-capability acceptance remain explicit review gates.

## FC.1 — Forecast-guided parallelism experiment

The [forecasting program](specs/034-workload-forecast-data/program.md) contains
SPEC-034–037 in one dedicated milestone: permissioned numeric workload telemetry,
an optional local Chronos-2 adapter, prospective forecast and complete-cost
parallelism evaluation, and separate read-only/shadow integration plus exact
capability promotion/rollback. Four specs and 33 implementation/gate tasks are
drafts with human review pending; no model or workload experiment has run.

The target is to learn when and where admitted preparation is economically
worthwhile on Agent Braid's own permissioned workloads. Initial choices retain
the existing serial/parallel fixed-patch contracts and one reviewed local
resource profile; distributed placement, new hosts, paid services, arbitrary
repository-code execution and model fitting are deferred. Chronos-2 is the
selected zero-shot integration; cheap baselines remain mandatory and an optional
Toto comparator needs pre-holdout selection and its own approved budget.

Source/rights/yield, artifact/deployment approval, frozen budgets/holdout, actual
operator authority, complete utility interpretation and operational promotion
remain distinct gates. Negative, inconclusive and infeasible research outcomes
are valid. Forecast quality does not establish scheduling benefit or semantics;
SPEC-019, native System 1 model gates, SPEC-021 G4 NO-GO and M4 open status remain
unchanged. Milestone creation does not accept any capability or execute its tasks.
