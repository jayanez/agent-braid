# Mathematical Foundations

This document fixes the initial mathematical vocabulary of Agent Braid. It is a working specification, not a claim that the final structure has already been found.

The executable restricted interpretation and composition rules are specified in
[bounded operational semantics](docs/theory/OPERATIONAL_SEMANTICS.md). The
[scientific integration](docs/theory/SCIENTIFIC_INTEGRATION.md) records corrections
and remaining proof obligations. These definitions do not certify production execution.

## 1. State and observations

Let \(S\) be a state space. A state may include files, syntax trees, databases, tool outputs, external resources, agent memory, environment configuration, and version metadata.

Correctness is rarely equality of every internal bit. For an observation boundary \(O\), define:

\[
s \sim_O t \iff O(s) = O(t).
\]

Examples of \(O\) include:

- a normalized repository tree plus test results;
- selected database relations and constraints;
- externally visible API responses;
- emitted events under a specified identity-aware delivery contract;
- a formally specified projection of state.

Every confluence result must name its observation boundary. Two schedules may be equivalent for tests and still differ in logs, timestamps, cost, or external side effects.

## 2. Operations and partiality

An operation is modeled initially as a partial, effectful state transformation:

\[
a : S \rightharpoonup S \times V \times T,
\]

where \(V\) is a result value and \(T\) is an execution trace. Undefinedness
denotes inadmissible input in the abstract fragment. Failed attempts, especially
failures after an effect, require explicit outcomes; they must not be collapsed
into an undefined function. Authorization is an independent execution premise.

For deterministic pure examples, this reduces to \(a : S \rightharpoonup S\). Real operations may instead require a transition-system, monadic, or event-structure semantics. The project must not erase nondeterminism merely to make commutation easy to state.

## 3. Effects

For an operation \(a\), its effect summary \(E(a)\) may contain:

\[
E(a) = (R_a, W_a, C_a, X_a, P_a, Q_a, I_a),
\]

with read set \(R_a\), write set \(W_a\), calls/emissions \(C_a\), destructive or external effects \(X_a\), precondition \(P_a\), postcondition \(Q_a\), and preserved invariants \(I_a\).

Disjointness rules provide sufficient but generally not necessary conditions for commutation. For example:

\[
W_a \cap (R_b \cup W_b) = \varnothing
\quad\land\quad
W_b \cap (R_a \cup W_a) = \varnothing
\]

is a useful candidate rule only if undeclared external effects, aliases, generated files, and semantic dependencies are excluded.

## 4. Pairwise commutation

Operations \(a\) and \(b\) commute on a domain \(D \subseteq S\) under observation \(O\) when both compositions are defined and:

\[
\forall s \in D,\quad \llbracket a;b\rrbracket(s) \sim_O \llbracket b;a\rrbracket(s).
\]

Here sequence `a;b` executes a first and threads its entire configuration into b,
including results and events. Equality is terminal unless preservation under all
admitted continuations and enabledness is established separately.

The project distinguishes:

- **exact commutation:** equality in the chosen semantic state space;
- **observational commutation:** equality after \(O\);
- **conditional commutation:** the relation holds under explicit predicate \(P(s)\);
- **empirical commutation:** tested on a finite corpus, with no universal claim;
- **probabilistic commutation:** equivalence is distributional and the metric is stated.

## 5. Schedules, independence, and traces

A schedule is an admissible ordering or partial ordering of operation instances. A trace records identities, inputs, declared and observed effects, versions, results, timing, nondeterministic choices where available, and hashes of relevant artifacts.

An independence relation \(I \subseteq \Sigma \times \Sigma\) over operation labels may induce a trace monoid in restricted cases: adjacent independent actions may be swapped without changing the equivalence class. This is a useful baseline for far commutation, not yet a braid action.

## 6. Confluence

For a transition relation \(\rightarrow\), local confluence asks whether one-step divergences can join:

\[
s \rightarrow s_1 \land s \rightarrow s_2
\implies
\exists u: s_1 \rightarrow^{*} u \land s_2 \rightarrow^{*} u.
\]

With observational equivalence, the join may be weakened to states \(u_1 \sim_O u_2\). Global confluence extends the property to arbitrary finite divergences.

Agent Braid must state whether a result concerns:

- a single initial state or all states in a domain;
- pairwise commutation, local confluence, or global confluence;
- terminating or possibly non-terminating systems;
- exact or observational equality;
- pure state changes or external effects.

## 7. Exchange operators

When two neighboring operation-bearing strands interact, an exchange operator may rewrite both order and residual operations:

\[
B_s(a,b) = (b',a'),
\]

Both pairs must form admissible paths with the same source and equal or explicitly
equivalent targets; an exchange may not invent an unconstrained repair state.

An exchange may transform operations rather than merely swapping \((a,b)\) to
\((b,a)\). Residual operations are important when one edit must be transformed
against another, as in patch and operational-transformation settings.

The exact carrier might be operations, effectful morphisms, patches, events, state-indexed actions, or another structure. Choosing it is part of the research problem.

## 8. Braid and Yang–Baxter conditions

For adjacent exchanges \(\sigma_i\), braid coherence asks:

\[
\sigma_i\sigma_{i+1}\sigma_i
=
\sigma_{i+1}\sigma_i\sigma_{i+1}.
\]

A set-theoretic Yang–Baxter candidate may take \(B : X \times X \to X \times X\) and test:

\[
B_{12}B_{23}B_{12}
=
B_{23}B_{12}B_{23},
\]

With right-to-left function composition, B is the adjacent exchange and
\(B=P\circ R\) for flip P and the quantum-form R. Other formulations use \(R_{12}R_{13}R_{23}=R_{23}R_{13}R_{12}\). Agent Braid must never mix conventions without defining the operators and composition order.

The project hypothesis is that a restricted class of agent interactions may admit such coherent exchange operators up to \(\sim_O\). This has not been established.

## 9. Certificates

A confluence certificate is evidence about a concrete analysis, not an unconditional proof. At minimum it identifies:

- initial-state or artifact hashes;
- operation and agent identities;
- declared and observed effects;
- schedules explored or proof rule applied;
- normalizer and observation boundary;
- equivalence result and counterexample, if any;
- assurance level and tool versions;
- assumptions and unobserved effect domains.

## 10. Immediate research obligations

Before invoking Yang–Baxter as a formal result, the project must answer:

1. What is the carrier \(X\) or state-indexed category?
2. What exactly does \(R\) exchange or transform?
3. Is composition total, partial, nondeterministic, or probabilistic?
4. What is the equivalence relation \(\sim\)?
5. Which preconditions are stable under exchange?
6. How are irreversible external effects represented?
7. Does pairwise exchange extend coherently to triples?
8. Can the claimed property be decided, approximated, or only tested?
9. Which useful runtime optimization follows from the result?

Negative answers and impossibility results are within scope.
