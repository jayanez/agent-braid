# Terminology

| Term | Working definition |
|---|---|
| **Agent** | An identifiable participant that proposes or executes operations. Model, prompt, or vendor identity alone does not define its semantics. |
| **Operation** | A possibly partial and effectful transition over state, with an input, result, trace, and evidence. |
| **State** | The modeled information that operations may observe or change. |
| **Shared state** | State accessible to more than one operation or agent, directly or through aliases and external services. |
| **Resource** | A named region of state, such as a file, AST node, table, branch, API object, deployment, or event stream. |
| **Effect** | An observable interaction with a resource or environment, including read, write, call, transform, emit, delete, and deploy. |
| **Declared effect** | Effect advertised by a tool, adapter, or operation author. |
| **Observed effect** | Effect derived from execution instrumentation or trace evidence. |
| **Hidden effect** | Relevant effect absent from the available model. Hidden effects reduce the assurance level. |
| **Interaction** | A dependency, conflict, exchange, or other relation between operation instances. |
| **Schedule** | An admissible total or partial order of operation instances. |
| **Trace** | Replay-oriented evidence of an execution or analysis, including versions, effects, results, and relevant choices. |
| **Observation boundary** | The projection used to decide which differences between states matter. |
| **Observational equivalence** | Equality of two states under a named observation boundary. |
| **Normalization** | A deterministic transformation used to remove irrelevant representational differences before comparison. |
| **Commutation** | Equivalence of two operation orders over a stated domain and observation boundary. |
| **Conditional commutation** | Commutation that holds only under explicit, stable conditions. |
| **Far commutation** | Exchange of interactions considered independent because they do not meaningfully overlap. |
| **Conflict** | Evidence that operations cannot safely be reordered or combined under the current assumptions. |
| **Confluence** | The property that admissible divergent executions can join at equivalent outcomes. |
| **Local confluence** | Joinability of immediate divergences. |
| **Global confluence** | Joinability of arbitrary finite divergences in the defined system. |
| **Exchange operator** | An operator that swaps and, when necessary, transforms neighboring interactions. |
| **Residual operation** | The transformed form of an operation after exchanging it with another operation. |
| **Braid** | A representation of interacting strands whose crossings denote defined exchange operations. |
| **Braid relation** | Coherence condition equating two three-exchange compositions. |
| **Yang–Baxter hypothesis** | The unproved proposition that useful restricted classes of agent interactions admit YB-like coherent exchange operators. |
| **AIM** | Agent Interaction Metadata, the proposed portable effect and property vocabulary. |
| **Confluence certificate** | Machine-readable evidence of the schedules, assumptions, observations, and checks supporting an equivalence result. |
| **Assurance level** | A compatibility class, not a universal strength order; property, method, domain and execution contract are separate. |
| **Minimal counterexample** | A reduced state and operation set that still violates the tested property. |
| **Safe parallelism** | Concurrency admitted by stated evidence and correctness boundaries, not merely by available compute. |

Additional distinctions: a **definition** names an operation's semantics; an
**instance** fixes its inputs; an **attempt** identifies one execution. **Terminal
equivalence** compares completed observations; **contextual equivalence** also
preserves enabledness and observations under admitted continuations. **Trace
safety** constrains intermediate effects. **Serializability** relates histories
to a serial execution and does not require all serial orders to agree.
**Compensation** follows a recovery contract and is not necessarily an inverse.

## Reserved wording

The project uses these phrases conservatively:

- **proved** only for a formal derivation with stated assumptions;
- **verified** only for a specified property and verification method;
- **empirically equivalent** for finite tested executions;
- **YB-inspired** for structural motivation without a Yang–Baxter result;
- **Yang–Baxter** without qualification only when the mathematical structure and equality are explicit.
