# Agent Braid Constitution

**Status:** Foundational

**Amendment status:** The founder approved the changes to Articles 6, 8 and 13
on 2026-09-16 and explicitly authorized direct integration into main. ADR 0004
records this adoption and the one-time exception to the dedicated-PR procedure.

**Authority:** All design, research, implementation, documentation, and public claims in this repository are subordinate to this Constitution.

## Constitutional clause zero

> **Agent Braid does not assume that Yang–Baxter applies to AI agents. It exists to investigate whether useful classes of agent interactions can be given an algebraic structure in which braid relations, confluence, and eventually Yang–Baxter-type conditions emerge as verifiable properties.**

No benchmark, product pressure, contributor preference, or branding opportunity may weaken this clause. A result may be useful without being Yang–Baxter. A Yang–Baxter claim is permitted only when its objects, operators, equivalence relation, domain of validity, and evidence are explicit.

## Article 1 — A runtime for interactions, not a collection of prompts

Agent Braid SHALL treat agents as state-transforming participants in a shared computational system. The primary object is not the isolated prompt or model response, but the interaction among agents, tools, resources, and observable state.

The project SHALL pursue an analysis layer first and an execution runtime second. Both must remain independently useful.

## Article 2 — Order is a semantic question

For actions \(A\), \(B\), and \(C\), the system SHALL never assume that \(A \circ B \circ C\) is equivalent to another admissible order. It SHALL ask under which preconditions alternative factorizations produce observationally equivalent results.

Schedule order is part of program meaning whenever actions do not commute.

## Article 3 — Agent Interaction Algebra is the central abstraction

Agent Braid SHALL define agents, operations, effects, states, interactions, schedules, traces, equivalence, commutation, confluence, exchange operators, and certificates as first-class objects.

The algebra SHALL be precise enough to execute, test, falsify, and eventually formalize. Natural-language descriptions alone are insufficient as the canonical semantics.

## Article 4 — Confluence is verified, never presumed

A system is conﬂuent with respect to a class of operations only when all relevant admissible execution paths join at observationally equivalent states, or when a stated weaker criterion has been met.

Pairwise commutation is evidence, not automatic proof of global confluence. The project SHALL record the scope and limits of every conclusion.

## Article 5 — Effects are first-class

Every operation SHOULD declare, and the runtime MAY infer or observe, effects from at least the following families:

- `read`
- `write`
- `call`
- `transform`
- `emit`
- `delete`
- `deploy`

Effect domains, resources, versions, preconditions, postconditions, invariants, determinism, idempotence, reversibility, and compensation semantics SHALL be representable. Hidden effects reduce assurance and SHALL be surfaced as uncertainty.

## Article 6 — Interaction properties drive scheduling

Operations established as commuting MAY be scheduled concurrently only under an execution contract that preserves their certified abstract semantics. Sequential commutation alone SHALL NOT justify arbitrary concurrent interleaving. Operations known not to commute SHALL be ordered, isolated, or rejected; compensation requires a separate recovery contract and is not an exact inverse by default. Conditionally commuting operations SHALL carry and enforce their conditions at the point of use, including relevant versions and enabledness.

The scheduler SHALL optimize only within the boundary of preserved observable correctness. Throughput is subordinate to semantics.

## Article 7 — The architecture separates decision stages

The reference architecture SHALL keep these concerns distinguishable:

1. task planning;
2. effect acquisition and inference;
3. interaction-graph construction;
4. commutativity and confluence analysis;
5. scheduling;
6. isolated execution;
7. normalization and equivalence checking;
8. certificate and trace production.

Implementations may combine components, but SHALL preserve inspectable boundaries and evidence provenance.

## Article 8 — Yang–Baxter-inspired semantics must define their terms

An exchange operator of the form

\[
R_{ij}: S_i \otimes S_j \rightarrow S_j \otimes S_i
\]

is meaningful only after the state objects, composition law, transformed actions, side conditions, and observational equivalence are defined.

The tensor symbol SHALL NOT imply an unspecified mathematical structure. A
Cartesian or state-indexed model MAY be used instead. Adjacent braid exchanges
and quantum-form operators SHALL have distinct notation and a declared
composition convention; under the standard convention, the adjacent exchange
is the flip composed with the quantum-form operator.

The relation

\[
R_{12}R_{13}R_{23} \sim R_{23}R_{13}R_{12}
\]

SHALL be called Yang–Baxter-like unless literal equality in a specified mathematical structure has been proved. The symbol \(\sim\) SHALL always name a concrete equivalence relation.

## Article 9 — Experiments must generate counterexamples

The first executable models SHALL evaluate alternative schedules from a common initial state, normalize their outputs, compare observations, and minimize any divergence.

The experimental corpus SHALL include commuting, non-commuting, partially commuting, conditionally commuting, nondeterministic, and externally effectful operations. A counterexample is a research result, not a failed demo.

## Article 10 — Braid relations are structural tests

For independent interactions, the project SHALL test far commutation:

\[
\sigma_i\sigma_j = \sigma_j\sigma_i \quad \text{for } |i-j| \ge 2.
\]

For adjacent interactions, it MAY test the braid relation:

\[
\sigma_i\sigma_{i+1}\sigma_i = \sigma_{i+1}\sigma_i\sigma_{i+1}.
\]

Passing such tests for examples does not establish a universal law. The operational interpretation of every \(\sigma_i\) SHALL be explicit.

## Article 11 — The braid representation must earn its place

Agent Braid MAY represent executions as braids when crossings encode meaningful exchanges or interactions. Braid simplification SHALL be semantics-preserving under declared relations.

Visual metaphor without executable or provable semantics SHALL not be treated as a technical contribution.

## Article 12 — Scale requires concurrency control, not only coordination prompts

The project SHALL treat stale reads, lost updates, inconsistent observations, undeclared dependencies, isolation failures, and unsafe access to shared resources as systems problems.

Prompts, planning, and communication MAY reduce risk, but SHALL not substitute for concurrency-control mechanisms when correctness depends on shared state.

## Article 13 — Properties and evidence are explicit dimensions

Every analysis result SHALL declare one of these compatibility classes, or a documented refinement:

0. heuristic;
1. syntactic;
2. semantic;
3. transactional;
4. confluence;
5. Yang–Baxter.

Heuristic, empirical, and formal equivalence SHALL never be conflated. Confidence scores SHALL not be labeled guarantees.

These classes SHALL NOT be interpreted as a universal ordering of runtime
safety. Results SHALL separately identify the property, evidence method,
quantified domain, assumptions, observation and execution contracts, and
consumer verification status. A producer's claimed class SHALL NOT constitute
verified evidence or authorization to execute.

## Article 14 — The interface must expose evidence, not just verdicts

CLI and API results SHALL explain:

- which agents and operations were analyzed;
- which resources and effects were considered;
- which pairs commute, conflict, or depend on conditions;
- which schedules were compared;
- which normalizer and observation boundary were used;
- the assurance level and unresolved uncertainty;
- hashes or identifiers needed for replay.

A green check without inspectable evidence is insufficient.

## Article 15 — Tool protocols should carry effect semantics

Agent Braid SHALL support effect metadata for MCP and other tool protocols without coupling the core algebra to any single vendor or transport.

Tool descriptions MAY be declared by providers, refined by adapters, inferred statically, and checked against observed traces. Declared metadata SHALL not be blindly trusted when verification is possible.

## Article 16 — AIM is an open interoperability proposal

The project SHALL explore Agent Interaction Metadata (AIM) as a small, portable vocabulary for operation effects and algebraic properties.

AIM SHOULD represent resources, read/write sets, determinism, idempotence, commutativity, conditions, isolation requirements, compensation, and evidence provenance. It SHALL be designed in public and versioned conservatively.

## Article 17 — Yang–Baxter has three claim levels

The project SHALL distinguish:

1. **Inspiration:** alternative factorizations motivate questions about order independence.
2. **Formalism:** exchange operators and braid relations model a defined class of interactions.
3. **Theorem:** a precisely stated class satisfies a Yang–Baxter equation or justified analogue.

Public communication SHALL state the applicable level. Only level 3 supports a theorem claim.

## Article 18 — Structural analogy is a hypothesis generator

Connections among braid relations, patch theory, operational transformation, CRDTs, rewriting, serializability, and confluence MAY motivate models and experiments. They SHALL not be presented as established equivalences unless proved.

Agent Braid exists in part to test whether the analogy can be converted into useful semantics and restricted theorems.

## Article 19 — The problem must remain real and measurable

The project SHALL evaluate itself on actual concurrency failures and workloads: overlapping code edits, configuration/deployment races, stale tool reads, duplicated external actions, non-repeatable plans, and multi-worktree integration.

Success SHALL be measured by correctness, conflicts prevented, safe parallelism recovered, replayability, diagnostic quality, and overhead—not by mathematical vocabulary or agent count.

## Article 20 — Analysis and execution are separate products

`agent-braid` SHALL be able to analyze plans and traces without owning execution. A future `agent-braid-runtime` MAY schedule and execute operations according to verified constraints.

The runtime SHALL consume the same portable semantics and certificates as the analyzer rather than hiding a second, incompatible model.

## Article 21 — Differentiation requires simultaneous engineering and research value

The project SHALL aim to contribute to software infrastructure, agent reliability, and the theory of interaction. It SHALL not sacrifice practical utility for an elegant analogy, nor scientific integrity for product positioning.

International differentiation must be demonstrated through interoperable artifacts, reproducible benchmarks, formal results, or uniquely useful tooling.

## Article 22 — Advanced mathematics is a laboratory, not ornamental branding

GAP/YangBaxter, SageMath, braid and knot software, SnapPy, quimb, proof assistants, and related systems MAY be integrated when they compute, verify, or falsify a project hypothesis.

An advanced-math MCP surface MAY serve as the mathematical laboratory of Agent Braid, but it SHALL not become a dependency of the practical core without demonstrated need.

## Article 23 — Development proceeds in three evidence-building phases

1. **Operational foundation:** effects, interaction graph, pairwise commutativity, conflict detection, scheduling, replay, and worktree experiments.
2. **Braid structure:** executable exchange relations, schedule rewriting, braid tests, and automated counterexample search.
3. **Formal research:** Agent Interaction Algebra, restricted theorems, mechanized proofs where valuable, and peer-reviewable results.

Each phase SHALL produce useful artifacts independently. Later vocabulary must not be back-projected as proof of earlier hypotheses.

## Article 24 — Semantics precedes production implementation

The initial milestone SHALL define at minimum:

`Agent`, `Operation`, `Effect`, `State`, `Resource`, `Interaction`, `Schedule`, `Trace`, `Observation`, `Equivalence`, `Commutation`, `Confluence`, `ExchangeOperator`, and `Certificate`.

Prototype code MAY sharpen those definitions. Production architecture SHALL not freeze accidental semantics merely because they were convenient in an early implementation.

## Article 25 — The ultimate objective is an algebra of interaction

Agent Braid SHALL pursue a compositional account of concurrent agent interaction in which:

- real executions produce replayable traces;
- traces generate examples and minimal counterexamples;
- examples refine the algebra and its invariants;
- the algebra improves analysis and scheduling;
- improved scheduling produces more reliable real executions.

This research–engineering feedback loop is the project's defining strategy. The ultimate objective is not a fashionable orchestrator; it is a useful and falsifiable algebra of interaction for concurrent AI agents.

## Interpretation and amendment

- Normative terms `SHALL`, `SHOULD`, and `MAY` follow their ordinary standards meaning.
- Architecture decisions that affect a constitutional principle require an ADR referencing the relevant article.
- Amendments require a dedicated pull request, explicit rationale, impact analysis, and founder approval.
- Clause zero may be clarified but not weakened while the project uses Yang–Baxter in its identity.
