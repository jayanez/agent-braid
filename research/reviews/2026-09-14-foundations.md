# Scientific Review of Agent Braid Foundations

**Historical review:** 2026-09-14; incorporated 2026-09-15. This records the
assessment of commit `77ca4b599dc26edb6a37bb91850b9e96a9866f91`, not the current
implementation status. See [integration decisions](../../docs/theory/SCIENTIFIC_INTEGRATION.md)
for the current disposition of findings. The original diagnostic script is now
[the laboratory controls](../lab/controls.py).

## Executive assessment

Agent Braid has a scientifically defensible research direction, but not yet a scientifically validated execution system. Its strongest foundation is the explicit separation of analogy, hypothesis, empirical evidence, finite exhaustive verification, and proof. The commitment to preserve negative results and retain engineering value if the Yang–Baxter hypothesis fails should remain unchanged.

The operational core is grounded in established concurrency-control and programming-language theory. Effects, commutativity, causal order, replay, and restricted confluence are appropriate tools. However, several definitions are not yet sufficient to justify scheduling decisions, and the repository contains no implemented scheduler, operational interpreter, residual transformation algorithm, or mathematical proof development. The repository validator checks document structure, selected metadata, JSON parsing, and links; it does not establish algorithmic correctness.

The recommended decision is to proceed with a bounded executable semantics and conservative analysis prototype, while withholding production-safety and Yang–Baxter claims. Before implementation semantics become fixed, address the distinction between sequential commutation and concurrent execution, the compositionality of observations, the representation of failures and results, and the separation between mathematical properties and evidence strength.

The reviewed repository revision is `77ca4b599dc26edb6a37bb91850b9e96a9866f91`. Literature comparisons are bounded to information available on 14 September 2026. This assessment does not amend the Constitution, change draft interfaces, or certify an implementation that does not yet exist.

## 1. What is supported and what remains open

| Foundation | Assessment | Necessary qualification |
|---|---|---|
| Effect-based independence | Established technique; appropriate starting point | Effects must soundly cover reads, writes, enabledness and relevant environment interaction |
| Semantic commutativity | Established technique; potentially useful | Include returned values, failures, domains and execution/recovery semantics |
| Alternative-schedule exploration | Appropriate validation method | Enumerating a few schedules establishes only the observed scope |
| Partial-order reduction | Established algorithmic foundation | Independence and property-preservation conditions must be proved for the selected model |
| Confluence | Appropriate mathematical property | Distinguish terminal agreement, joinability, termination and safety along traces |
| Residual transformations | Plausible restricted research direction | Requires typed contexts, admissibility, intent contracts and coherence obligations |
| Braid/Yang–Baxter structure | Legitimate research question; unestablished for project operations | A known abstract solution is not evidence that real agent tools instantiate it |
| Assurance levels 0–5 | Useful labels, misleading as a scalar strength hierarchy | A property class and a proof method are different dimensions |
| AIM and certificates | Useful drafts, not yet sufficient verification contracts | Schema validity must be separated from semantic validity and verified evidence |
| Novelty and performance | Not demonstrated | Compare with classical semantic concurrency control and recent agent-state systems |

Commutativity-based concurrency control substantially predates LLM agents. Weihl's work covers partial and nondeterministic operations, return-sensitive conflicts, and recovery; its relevance is not confined to simple disjoint writes. Agent Braid should position these as foundations to specialize, not new discoveries. [1](https://consensus.app/papers/commutativitybased-concurrency-control-for-abstract-weihl/69ec9365070051ca81578b8d0624ad47/?utm_source=chatgpt)

Likewise, CRDT research already supplies restricted convergence constructions, and machine-checked convergence frameworks distinguish causal order, concurrent commutation, successful interpretation, and network assumptions. These are useful models for the structure of Agent Braid's own proof obligations. [2](https://perso.lip6.fr/Marc.Shapiro/papers/2011/Comprehensive-CRDTs-RR7506-2011-01.pdf), [3](https://www.cl.cam.ac.uk/~arb33/papers/GomesEtAl-VerifyingSEC-OOPSLA2017.pdf)

## 2. Findings requiring correction before production design

### F1. Sequential commutation does not authorize arbitrary concurrent interleaving

**Priority: critical.** Constitution Article 6 permits concurrent scheduling of operations established as commuting. That implication needs an explicit execution-model condition.

Let both abstract operations increment an integer: `A(x) = x + 1` and `B(x) = x + 1`, without returning the old value. Their sequential compositions agree. But an implementation that performs a separate read and write can execute `read_A(0), read_B(0), write_A(1), write_B(1)`. The result is 1, whereas either serial execution produces 2.

This counterexample does not refute commutativity. It refutes the unrestricted inference from an abstract equation to an implementation's interleavings. Require an atomic implementation, an appropriate serializability/linearizability guarantee, or a proof that the permitted lower-level interleavings refine the abstract operations. Linearizability specifically relates concurrent histories to legal sequential behavior while respecting real-time precedence; it is not equivalent to comparing final states. [4](https://www.cs.columbia.edu/~wing/publications/HerlihyWing90.pdf)

Recommended normative clarification: commuting operations may execute concurrently only under an execution contract that preserves the certified abstract semantics. A compensating operation is not by itself such a contract, and serializing unknown operations is a concurrency precaution, not a guarantee that either operation is authorized or correct.

Affected material: `CONSTITUTION.md`, Article 6; `README.md`, core diagram; `ARCHITECTURE.md`, scheduler and execution boundaries.

### F2. Observational equality is not automatically compositional

**Priority: critical.** `MATHEMATICAL_FOUNDATIONS.md` defines equivalence by `O(s) = O(t)`. This is a legitimate equivalence relation when O is a function, but it need not support replacing one intermediate state with another.

Consider states `(visible, hidden)`, with observation equal to `visible`. Let A set `hidden = 1` and B set `hidden = 2`. Both execution orders leave the visible component unchanged. A later operation C that copies `hidden` into `visible` distinguishes the orders.

For a terminal, explicitly bounded comparison, the original observation can be adequate. For reusable schedule rewrites, require preservation under all admitted continuations, or a suitable congruence/simulation contract. In a deterministic partial model this includes both equal enabledness and preservation of equivalence after each permitted operation. It is not enough to check the projection immediately after a pair.

Define three contracts separately: terminal observation equality, contextual equivalence for admitted continuations, and safety over execution traces. A final repository tree cannot reveal that an intermediate action exposed a secret or sent an unwanted message. Event deduplication must not erase distinct externally meaningful effects merely because their payloads match.

Affected material: `MATHEMATICAL_FOUNDATIONS.md`, sections 1, 4 and 6; `TERMINOLOGY.md`; normalizer and certificate specifications.

### F3. Operation composition, failure and identity are underspecified

**Priority: critical.** The current type `a: S ⇀ S × V × T` is followed by expressions such as `a(b(s))`. Those expressions require a lifting/composition rule because b returns a triple, not a state.

For the initial deterministic fragment, lift an operation instance into a configuration containing state, a result map keyed by instance ID, pending operations and an event trace. Define exactly which result feeds which later input, how events compose, and whether a failure halts a batch or produces an explicit transition. Never silently project away results to make the formula type-check.

Two atomic fetch-and-increment operations illustrate why this matters: either order leaves the counter at 2, but the value returned to A differs. If A uses that value in a later decision, the histories are not interchangeable. Similarly, a timeout after a remote write has a different meaning from a precondition failure before any effect. Undefinedness alone cannot represent both safely.

Adaptive generation also changes the object being compared. Replaying frozen proposed operations tests their execution semantics; running agents afresh under another schedule tests a policy that may produce different operations. Both experiments are useful, but neither substitutes for the other. Fixed seeds do not make uncontrolled external observations identical.

Affected material: `MATHEMATICAL_FOUNDATIONS.md`, sections 2 and 4; AIM instance/trace model; experiment protocol.

### F4. Pair checks must cover reachable contexts, not only the initial state

**Priority: high.** The Constitution correctly warns against extrapolating pairwise evidence. The implementation guidance should state the missing condition positively.

Start from `(x,y,z) = (0,0,0)` and define A as `x := 1`, B as `y := 1`, and C as `z := x*y`. Every pair agrees in both orders when tested from the initial state. Nevertheless, executing A, B, C yields z = 1, while A, C, B yields z = 0. All six schedules were enumerated in the accompanying finite check.

This is not a counterexample to the theorem about commuting functions on a closed domain: A and C do not commute once B has changed y. It shows why certificates tied only to one initial pair test cannot justify later exchanges. Conditions must remain valid at the point of use, including resource versions, enabledness and causal dependencies.

For a fixed finite batch, pairwise independence proved on all relevant reachable states can justify swapping adjacent incomparable operations and hence equivalence of topological orders. The existence of such a proof is much stronger than collecting successful pair tests.

Affected material: H1 and H2 in `RESEARCH.md`; graph edge scope; scheduler admission and certificate invalidation.

### F5. Confluence, serializability, task correctness and invariant preservation are different

**Priority: high.** Confluence concerns joinability of diverging reductions. Serializability concerns correspondence to a serial history. Task correctness concerns the actual specification. None should be represented as a synonym for another.

A confluent system can converge reliably to an incorrect answer. A serializable system can legitimately produce different outcomes for different serial orders. A correct recovery policy can restore a business invariant without undoing every observable consequence. Endpoint equality alone does not establish trace safety or progress.

For a terminating reduction relation, local confluence implies confluence by Newman's lemma. This does not allow an unqualified transfer to arbitrary adaptive agent loops or an arbitrary observation quotient. A fixed batch can supply a decreasing measure—the number of pending operations—only if each successful step removes an operation and the model does not silently add unbounded retries or new work. The exact confluence definitions and termination premise are standard rewriting theory. [5](https://math.univ-lyon1.fr/homes-www/malbos/Ens/lar.pdf)

Add invariant-confluence analysis as a separate research connection. Bailis and colleagues characterize when coordination can be avoided while preserving application invariants under their transaction/merge assumptions. That result is not the same as ordinary schedule confluence and is not an unconditional theorem about agents. [6](https://www.vldb.org/pvldb/vol8/p185-bailis.pdf)

A simple target case is write skew: two isolated branches respectively set x and y to 1 after each checks that the other remains 0. Both preserve `x+y ≤ 1` locally, but merging their disjoint writes violates it. Read dependencies reveal the conflict; write overlap alone does not.

### F6. Assurance is multidimensional, not a universal ladder

**Priority: high.** The levels mix methods (`syntactic`, `semantic`), an execution contract (`transactional`), and mathematical properties (`confluence`, `Yang–Baxter`). These do not form a general order of increasing runtime safety.

A proved disjointness rule can be more dependable for a particular execution decision than a braid identity established on an unrelated abstract carrier. A Yang–Baxter proof does not imply authorization, isolation, successful termination, correct external effects or complete instrumentation.

Keep 0–5 as compatibility labels if required, but supplement them with independently checked fields: property, evidence method, quantified domain, assumptions, execution contract, observation contract, verification status and trusted components. Distinguish the level a producer claims from the evidence a consumer has verified. Promotion must never be inferred from a larger integer alone.

Affected material: Constitution Article 13, `ASSURANCE_LEVELS.md`, README assurance table, both schemas.

### F7. The certificate schema permits unsupported and internally meaningless claims

**Priority: high.** The draft allows level 5 with `equivalent-observed` and no proof artifact. It also allows two identical schedules referring to unknown operation IDs, duplicate operation IDs, missing operations and no declared/observed effects. The prose requires several fields that the schema cannot express directly, including analysis/tool versions and effect evidence.

An explicit negative-control certificate combining duplicate operation IDs, two identical schedules naming an undeclared operation, level 5, and no proof artifact passed JSON Schema validation. Both schema documents and the existing AIM example also passed their structural checks. The counterexample therefore concerns missing semantic obligations, not malformed JSON.

This is a design gap, not an exploit in a deployed verifier: no verifier exists yet. Separate structural validation from semantic checking. The latter must resolve IDs, verify completeness or explicitly permitted partial schedules, enforce dependencies, bind all referenced artifacts, and check the rule's premises against the actual instance.

A universal or symbolic proof need not enumerate two schedules. Conversely, two matching traces do not establish a universal rule. Use a discriminated evidence model such as empirical replay, exhaustive finite enumeration, or proof-rule application, each with its own required evidence. A certificate's name may remain stable, but its verified claim must be narrower than its name when appropriate.

AIM likewise needs instance-level identity and read versions in the execution envelope, separate declared/observed evidence, and explicit coverage. An empty effect list must not be interpreted as “proved pure” without a coverage contract. Generic extensions can prototype fields, but interoperability requires shared semantics.

### F8. Hypotheses and milestone exits need sharper quantifiers

**Priority: high.** H1 combines a prospective theorem with a measurement problem. Separate the soundness of the independence rule from the soundness and usefulness of the effect extractor. A counterexample caused by an omitted read refutes the extractor's claim, not necessarily the rule under complete effects.

H2's reference to preserving independent invariants is insufficient to prove commutativity: many operations preserve the same invariants but yield different states or results. H3's “more coherently” needs a defined property and comparator. H4's existential claim about all practically useful classes cannot be falsified by searching one finite candidate space.

Reformulate H4 per carrier, operation grammar, transformation family, admissibility conditions and workload. An exhaustive search can then establish a negative result within that space. Practical usefulness should have declared acceptance thresholds rather than being retrofitted after an algebraic result is found.

Clarify the experiment protocol's prohibition on calling finite testing a proof: exhaustive checking of a precisely defined finite model can establish that finite proposition, with trust placed in the checker and encoding. It does not establish an unbounded theorem. This matches the existing claim-discipline vocabulary.

Finally, make the practical runtime dependent on validated engineering milestones, not on a positive braid result. `ROADMAP.md` currently gates M4 on M1–M3; a negative M3 result should not block a useful, sound analyzer/runtime.

## 3. A bounded mathematical kernel

Start with finite batches of identified, deterministic operations over a versioned resource map. Use configuration `C = (state, pending, results, events, versions)`. Inputs and accepted observation rules are immutable within an experiment. Reads of absence, directory membership or query predicates must be modeled when they affect decisions; otherwise phantom dependencies disappear from the abstraction.

Specify a transition `C —a→ C'` with explicit preconditions, successful result, failure outcome and effects. Distinguish an operation definition from one proposed instance, one execution attempt, and one committed effect. This prevents retries from appearing to be either a new logical action or a magically idempotent repetition.

### Restricted theorem target T1: independence

Assume deterministic transitions, complete read/write footprints including enabledness, no effects outside the modeled state, writes confined to their declared locations, and the cross-read/write disjointness conditions in the existing foundation. Assume both operations are enabled and their result/event representation does not introduce an unmodeled conflict.

Under these premises, executing either operation cannot change the inputs or enabledness of the other. Their writes affect disjoint locations. Each operation therefore produces the same own result in either order, and the resulting states and per-instance results agree. Events must agree under an independently justified observation contract; arbitrary chronological logs need not be literally equal.

This is a proof sketch for a restricted semantic rule, not a proof that a real tool meets its premises. The difficult engineering obligation is a sound adapter and a runtime refinement that preserves the rule.

### Restricted theorem target T2: schedule equivalence

Take a finite partially ordered batch. Suppose every incomparable pair satisfies the independence rule in all reachable contexts in which a swap is used. Suppose swapping preserves admissibility and the selected equivalence is preserved by every remaining suffix. Then all complete linear extensions yield equivalent observations.

Proof sketch: connect any two linear extensions by adjacent swaps of incomparable elements. Each swap preserves admissibility and meaning by the stated hypotheses. Compositionality propagates equality through the suffix; transitivity gives equality of the complete executions. This is a useful first theorem without Yang–Baxter terminology.

Neither theorem covers arbitrary nondeterministic generation, external failures, retries, partial instrumentation or non-atomic mutation. Add those as separate model extensions with separate proof obligations, rather than silently broadening the first theorem's wording.

For nondeterministic policies, choose whether a claim concerns sets of possible outcomes, matched executions under a coupling, distributions under a specified metric, or trace refinement. Approximate pairwise distributional agreement also needs a composition/error-budget argument before being used across many exchanges.

## 4. Yang–Baxter and residual operations

The promising connection is coherent transformation of operations, not a physical law governing agents. Set-theoretic Yang–Baxter solutions are an established mathematical field; merely finding an abstract carrier and a solution would not establish project novelty. [7](https://arxiv.org/abs/math/9801047)

Define an adjacent exchange B separately from the quantum-form R. If P is the flip, the standard convention relates them through `B = P ∘ R`; write the composition convention explicitly. Use ordinary Cartesian products initially. A tensor product of agent states needs a defined categorical structure and should not substitute for one.

For partial operations, a useful starting domain is composable paths: `a: s → s1`, `b: s1 → s2`. An exchange produces a well-typed alternative path `b': s → t1`, `a': t1 → s2`, or an explicitly equivalent endpoint under an adequate observation contract. The current free output state in `R(a,b,s) = (b',a',s')` needs this discipline to prevent arbitrary state repair from masquerading as a valid exchange.

Require five obligations: admissibility, preservation of specified intent/results/effects, closure of the residual operation class, stable conditions, and coherence of alternative transformation paths. A residual cannot erase an operation's intent by turning it into a no-op solely to obtain convergence. For general natural-language intent, these obligations remain unspecified until an executable contract is supplied.

Operational Transformation is especially relevant prior art. Randolph and colleagues show an impossibility result for simultaneously satisfying TP1 and TP2 with particular basic insert/delete signatures; this warns that metadata choices can determine what is provable. It is not an impossibility theorem for all text collaboration. Xu and colleagues show how integration mechanisms can avoid problematic CP2 contexts, so not every correct collaborative system must satisfy an unrestricted transformation identity. [8](https://arxiv.org/pdf/1302.3292), [9](https://cscw.acm.org/2014/cscw2014_program.pdf)

A direct equivalence between OT's properties and Agent Braid's proposed equation must be proved through an explicit mapping. Similar diagrams are motivation, not that mapping.

### A nontrivial positive control

For a group G define `B(a,b) = (b, b⁻¹ab)`. This is the standard conjugation-rack construction, not a new Agent Braid result. It preserves the algebraic product because `b(b⁻¹ab) = ab`. Both three-exchange paths send `(a,b,c)` to `(c, c⁻¹bc, c⁻¹b⁻¹abc)`, establishing the braid relation by group identities. [10](https://arxiv.org/pdf/0808.0108)

The accompanying script independently checks all 36 pairs and 216 triples in the six-element permutation group S3. The exchange is bijective and has non-involutive cases. This is an exact finite control for the equation and implementation conventions, not evidence about agent operations, patches or network calls.

For a braid-group action the exchanges must be invertible. Without invertibility, satisfying the relations can instead define a positive braid-monoid action. If exchanges also satisfy `B² = identity`, the action factors through the symmetric group. Do not confuse invertibility of an exchange of descriptions with reversibility of executing a real-world action.

The hard question is whether a useful operation class admits efficient, intent-preserving residuals satisfying these conditions. A group model does not solve deletions, partial patches, irreversible sends or authorization. An honest negative answer for those classes is compatible with a successful product.

## 5. Recommended algorithms and implementation sequence

| Component | Initial algorithmic choice | Correctness obligation |
|---|---|---|
| Reference semantics | Small deterministic interpreter over immutable fixtures | Explicit transitions, domains, errors, results and event semantics |
| Effect analysis | Conservative resource normalization and footprint rules | Coverage includes aliases, control dependencies and absence/predicate reads |
| Conflict graph | Resource-indexed candidate generation; label uncertainty | No missing dependency caused by incomplete coverage |
| Schedule planning | Preserve dependencies; orient unresolved conflicts by a chosen admissible order | Acyclicity, condition validity and no unauthorized operation |
| Execution | Isolated proposals plus controlled validation and commit | Validation and mutation occur under one atomic/exclusive boundary |
| Exploration | Full enumeration for small models; then proven POR/DPOR | Reduction preserves the property under the model's independence relation |
| Counterexamples | Delta reduction followed by fresh replay | State whether the result is locally minimal or globally minimal |
| Certification | Small independent checker for rules and replay evidence | Validate premises and artifacts, not producer confidence |

Dynamic partial-order reduction is a concrete baseline, not something to reinvent under braid terminology. Its independence conditions and backtracking obligations are essential. A reduction that prunes schedules based on an unsound effect model can remove the only failing execution. Cycle, fairness and property-specific conditions matter when moving beyond a bounded acyclic model. [11](https://users.soe.ucsc.edu/~cormac/papers/popl05.pdf)

A practical initial execution policy is to allow concurrent planning and isolated patch production, followed by a deterministic commit gate. Validate read versions, dependencies, authorization and invariants against the current state while holding the boundary that prevents a new race between validation and commit. If stale, replan or apply only a transformation whose rule has been independently checked. This is a proposed baseline, not a claim that the project already implements optimistic concurrency control correctly.

Treat irreversible external actions separately. A simulated replay must not send a second message, perform a second payment or redeploy a service. Compensation requires its own observable contract, failure handling and escalation path. Delivery guarantees, idempotency keys and authorization must be enforced by the relevant adapter/provider; a hash or post-hoc certificate cannot create them.

The small trusted checker is a promising architectural improvement. Let an LLM suggest effects, invariants, residuals and explanations, but permit a strong execution verdict only when deterministic checks establish the selected rule's premises. Explicitly include the resource adapter, normalizer, sandbox and artifact binding in the trusted computing base. “Model-agnostic” does not mean “assumption-free.”

## 6. Contemporary comparison and defensible differentiation

Recent papers establish that agent concurrency and shared-state management are active research areas. The following results are authors' reports, not independently reproduced measurements. The consulted agent papers are arXiv versions; peer-review status is not inferred from their presence in an academic search index.

| Work | Direct overlap | Consequence for Agent Braid |
|---|---|---|
| CoAgent, Lyu et al., 2026 | Shared-state concurrency control, footprints, selective repair, fixed serialization order | Compare execution assumptions and recovery contracts, not only throughput |
| STORM, Liu et al., 2026 | Mediated shared-workspace state and conflict detection at write time | A worktree baseline alone is insufficient for a competitive evaluation |
| CodeCRDT, Pugachev, 2025 | Concurrent code generation with deterministic replicated-state convergence | Measure semantic correctness separately from merge convergence |

CoAgent explicitly conditions serializability on protocol compliance and correct agent judgments about affected premises. Its reported empirical correctness is not an unconditional theorem that LLM conflict judgments are sound. This presents a possible differentiation: Agent Braid could make strong admission rules independently checkable and expose a clear boundary for heuristic assistance. The proposed advantage remains to be built and measured. [12](https://arxiv.org/html/2606.15376v1)

STORM evaluates explicit workspace-state management against multi-agent worktree isolation on coding/research benchmarks. It is a relevant engineering comparator, but its reported task scores should not be reinterpreted as proof of Agent Braid's proposed observational or braid properties. [13](https://arxiv.org/html/2605.20563v1)

CodeCRDT reports task-dependent speedups and slowdowns despite convergent replicated edits. Its discussion distinguishes semantic inconsistencies from CRDT convergence, and its semantic-conflict measurement is preliminary. This supports evaluating separate correctness and performance outcomes rather than treating a successful merge as a successful task. [14](https://arxiv.org/html/2510.18893v1)

The strongest prospective contribution is therefore a portable, evidence-carrying semantic interface connecting analyzers, runtime admission and independently checkable certificates, with restricted residual rules where justified. Neither the name nor the use of algebra establishes novelty. A publication claim requires a precise comparison and reproducible evidence beyond this targeted literature assessment.

## 7. Revised experiment programme

### Tier A: finite semantic checks

Build a versioned corpus with disjoint reads/writes, read-modify-write races, operation-return dependence, conditional commutation, hidden-state observations, write skew, aliasing, absence reads, enabledness changes and unsuccessful operations. Include the five counterexamples in `verify_models.py` as negative controls.

For each bounded domain, declare state count, operation grammar, admissibility and enumeration completeness. Enumerate every execution within that domain before adding reduction. Then compare the reduced and unreduced outcome sets. Differential agreement on a corpus is valuable regression evidence, while the reduction's soundness still needs a general proof within its stated model.

### Tier B: concrete adapters

Use synthetic and consented local repositories with generated files, renames, shared configuration, stale snapshots, semantic cross-file dependencies and invariant violations. Compare sequential execution, uncontrolled parallelism, file/range overlap, three-way merging, a version-validating commit gate, and semantic rules.

Keep task inputs and correctness oracles fixed. Evaluate raw trace safety and terminal results separately. Measure wall-clock latency, tokens, retries, analysis overhead, false-safe decisions, false serialization and unknown rate. Do not improve apparent precision merely by classifying every difficult case as unknown without reporting coverage.

### Tier C: adaptive agents

Separate replayed tool-operation tests from live policy tests. Record prompts, context, model/version, tool observations, operation-instance identity and randomness controls where available. Count the scenario or task as the principal experimental unit; multiple schedules from the same task are correlated observations, not automatically independent samples.

Use paired comparisons over shared tasks, hold-out task families, repeated runs and uncertainty intervals. Define a non-inferiority margin for correctness before examining speedups. Under independent Bernoulli trials, zero failures in n trials gives a one-sided 95% upper bound `1 − 0.05^(1/n)`, approximately `3/n`; it never establishes zero failure probability. Applying that calculation to correlated schedules would be unjustified.

Pre-register ablations: remove semantic rules, remove version checks, remove residualization, and remove schedule reduction separately. This isolates whether mathematics adds value beyond a competent conventional concurrency-control baseline. Publish negative cases and the complete costs of analysis and recovery.

### Tier D: restricted algebraic research

Use three controls: the ordinary flip, the known conjugation exchange, and deliberately invalid exchanges. For each new carrier, specify transformation closure, semantic preservation, domain stability and intent contracts before testing triples. If a claim is modulo observation, check that the equivalence is compatible with further exchanges.

Accept a braid result as operationally useful only after demonstrating a concrete benefit: a sound reduction in distinct schedules, a compositional transformation guarantee, a smaller proof obligation, or measurable parallelism unavailable to the stated baseline. A visually simpler braid diagram alone is not such a benefit.

## 8. Proposed documentation changes and release gates

These are recommendations, not applied changes.

| Priority | Proposed change | Acceptance criterion |
|---|---|---|
| P0 | Clarify Article 6 and the README concurrency diagram | No direct inference from abstract commutation to unsafe interleaving |
| P0 | Define typed operational composition, outcomes and continuation-safe observations | Every mathematical expression has a declared domain and composition rule |
| P0 | Separate property, evidence and execution contract | Level 5 alone cannot authorize an operation or claim production safety |
| P0 | Specify certificate semantic checking | Invalid IDs, unsupported proof claims and stale premises are rejected |
| P1 | Add interpreter and negative-control corpus | All five documented counterexamples reproduce; positive controls pass |
| P1 | State and prove restricted independence/schedule theorems | Assumptions link explicitly to adapter and runtime obligations |
| P1 | Sharpen H1–H5 and experiment acceptance thresholds | Each negative result has a bounded interpretation |
| P1 | Add classical and contemporary research references | Established results are not presented as project novelty |
| P1 | Decouple runtime delivery from positive braid results | A failed algebraic hypothesis does not block validated engineering |
| P2 | Add partial residual classes and formal developments | New rules are soundly connected to execution semantics |

Constitutional amendments should follow the existing dedicated-review and founder-approval procedure. Schema changes should be proposed as a versioned draft evolution or an explicitly versioned extension; do not silently repurpose the meaning of `0.1.0-draft`. The present audit does not authorize a schema migration or public release.

M0 should exit with a bounded semantics, a first proof obligation set, executable fixtures and a truthful certificate model—not just a complete vocabulary. M1 should demonstrate a conservative classifier with visible coverage and failures. Runtime admission should remain restricted until the semantic model and adapter isolation agree in executable tests and documented arguments.

## 9. Evidence limits and overall recommendation

The five counterexamples and S3 checks are reproducible finite diagnostics, not a production benchmark. The two theorem targets have ordinary mathematical proof sketches, not machine-checked developments. No tool adapter, scheduler or certificate checker has been proved correct, and no claimed performance advantage has been independently measured.

The literature assessment is targeted, not an exhaustive novelty search or a systematic review with complete database coverage. Abstract-only access is identified in the sources. Conflicting bibliographic years may reflect proceedings and preprint dates; recent arXiv findings must remain distinguishable from peer-reviewed results. No inaccessible paper or missing result has been treated as negative evidence.

Proceed with Agent Braid as an evidence-carrying concurrency-analysis project. Retain the ambitious algebraic research track, but make the first dependable product rest on explicit operation semantics, conservative effect rules, checked commit boundaries, and honest evidence. The most valuable immediate improvement is not adding more mathematical vocabulary: it is closing the gap between each asserted property and the concrete execution decision it is allowed to justify.

## Sources

1. William E. Weihl. *Commutativity-based concurrency control for abstract data types*, 1988. [Retrieved paper record](https://consensus.app/papers/commutativitybased-concurrency-control-for-abstract-weihl/69ec9365070051ca81578b8d0624ad47/?utm_source=chatgpt). Record identifies the HICSS proceedings version, vol. 2, pp. 205–214. Abstract-level support only; the journal version is a distinct bibliographic item. Used for historical scope, not a reconstruction of its proof.

2. Marc Shapiro, Nuno Preguiça, Carlos Baquero, Marek Zawirski. [A comprehensive study of Convergent and Commutative Replicated Data Types](https://perso.lip6.fr/Marc.Shapiro/papers/2011/Comprehensive-CRDTs-RR7506-2011-01.pdf). INRIA RR-7506, January 2011. Author-hosted technical report; convergence constructions and assumptions.

3. Victor B. F. Gomes, Martin Kleppmann, Dominic P. Mulligan, Alastair R. Beresford. [Verifying Strong Eventual Consistency in Distributed Systems](https://www.cl.cam.ac.uk/~arb33/papers/GomesEtAl-VerifyingSEC-OOPSLA2017.pdf). PACMPL 1, OOPSLA, article 109, 2017. Sections 4–7 and conclusions; formal convergence and network obligations.

4. Maurice P. Herlihy, Jeannette M. Wing. [Linearizability: A Correctness Condition for Concurrent Objects](https://www.cs.columbia.edu/~wing/publications/HerlihyWing90.pdf). ACM TOPLAS 12(3), 463–492, 1990. DOI: 10.1145/78969.78972. History-based concurrent correctness.

5. Philippe Malbos. [Lectures on Algebraic Rewriting](https://math.univ-lyon1.fr/~malbos/Ens/lar.pdf), December 2019, section 1.4, theorem 1.4.1. Author-hosted lecture notes. Used for the precise statement of Newman's lemma, not as evidence of a new result. The theorem is attributed there to M. H. A. Newman, 1942.

6. Peter Bailis, Alan Fekete, Michael J. Franklin, Ali Ghodsi, Joseph M. Hellerstein, Ion Stoica. [Coordination Avoidance in Database Systems](https://www.vldb.org/pvldb/vol8/p185-bailis.pdf). PVLDB 8(3), 185–196, 2014; VLDB 2015 cycle. [Retrieved record](https://consensus.app/papers/coordination-avoidance-in-database-systems-bailis-fekete/c1c16bfccdb35374a332a01b7113277a/?utm_source=chatgpt). Invariant-confluence model and limitations.

7. Pavel Etingof, Travis Schedler, Alexandre Soloviev. [Set-theoretical solutions to the quantum Yang–Baxter equation](https://arxiv.org/abs/math/9801047). 1998 preprint, Duke Mathematical Journal 100(2), 169–209, 1999. Abstract-level historical positioning; no classification theorem is imported into Agent Braid.

8. Aurel Randolph, Hanifa Boucheneb, Abdessamad Imine, Alejandro Quintero. [On Consistency of Operational Transformation Approach](https://arxiv.org/pdf/1302.3292). EPTCS 107, 45–59, 2013, Infinity 2012 proceedings. DOI: 10.4204/EPTCS.107.5. Restricted signatures, TP1/TP2 and counterexamples. Related later work: [On Synthesizing a Consistent Operational Transformation Approach](https://consensus.app/papers/on-synthesizing-a-consistent-operational-transformation-randolph-boucheneb/263931ef942c5a7cb912f957bce819ed/?utm_source=chatgpt), IEEE Transactions on Computers 64, 1074–1089, 2015; later paper consulted at abstract level only.

9. Yi Xu, Chengzheng Sun, Mo Li. *Achieving convergence in operational transformation: conditions, mechanisms and systems*. CSCW 2014. [Official conference programme and author abstract](https://cscw.acm.org/2014/cscw2014_program.pdf); [retrieved paper record](https://consensus.app/papers/achieving-convergence-in-operational-transformation-xu-sun/737b2bba8d005a72869947a962ac8b2e/?utm_source=chatgpt). Abstract-level evidence for CP2-avoidance mechanisms; full proof not audited.

10. Michael Eisermann. [Yang–Baxter deformations and rack cohomology](https://arxiv.org/pdf/0808.0108). 2008 preprint. Introduction and section 2.2; conjugation racks and braid operators. The finite S3 check is an independent diagnostic of this standard construction.

11. Cormac Flanagan, Patrice Godefroid. [Dynamic Partial-Order Reduction for Model Checking Software](https://users.soe.ucsc.edu/~cormac/papers/popl05.pdf). POPL 2005, 110–121. Independence, exploration and bounded safety assumptions.

12. Hongtao Lyu, Dingyan Zhang, Mingyu Wu, Xingda Wei, Haibo Chen. [CoAgent: Concurrency Control for Multi-Agent Systems](https://arxiv.org/html/2606.15376v1). arXiv:2606.15376v1, 13 June 2026. [Retrieved record](https://consensus.app/papers/coagent-concurrency-control-for-multiagent-systems-lyu-zhang/3c0ef19d9a81540eb3ec2d990ae55a5c/?utm_source=chatgpt). Sections 1, 5 and 7; conditional guarantee and reported evaluation. Preprint evidence, not independent replication.

13. Mengyang Liu, Taozhi Chen, Zhenhua Xu, Xue Jiang, Yihong Dong. [Multi-agent Collaboration with State Management](https://arxiv.org/html/2605.20563v1). arXiv:2605.20563, 2026. [Retrieved record](https://consensus.app/papers/multiagent-collaboration-with-state-management-liu-chen/b796bfc89f6e56d69e05f7031aa63d15/?utm_source=chatgpt). Author name follows the primary arXiv record rather than the abbreviated secondary index. STORM state mediation and reported benchmarks. Preprint evidence.

14. Sergey Pugachev. [CodeCRDT: Observation-Driven Coordination for Multi-Agent LLM Code Generation](https://arxiv.org/html/2510.18893v1). arXiv:2510.18893v1, 2025. [Retrieved record](https://consensus.app/papers/codecrdt-observationdriven-coordination-for-multiagent-pugachev/30d7240f5e0959d7894da21f79c5999a/?utm_source=chatgpt). Performance variation and semantic-conflict limitations. Preprint evidence.
