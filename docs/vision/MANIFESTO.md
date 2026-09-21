# The Agent Braid Manifesto

More agents do not automatically create a better system. They create more interleavings, more shared-state interactions, and more ways for locally reasonable actions to produce a globally incorrect result.

Agent Braid begins from a systems premise: concurrent autonomous agents need explicit semantics for effects, isolation, ordering, and observable correctness. Better prompts are useful, but they cannot replace concurrency control when agents read and change the same world.

Our engineering ambition is to make interaction properties operational. A runtime should know which actions may commute, which conditions justify an exchange, which operations must serialize, and why. It should produce evidence that can be inspected and replayed.

Our mathematical ambition is more speculative. Braid relations and the Yang–Baxter equation are canonical models of coherent local exchanges. We will investigate whether a nontrivial class of agent interactions can be given analogous structure. We will not assume the answer.

That creates a robust project:

- if only conservative effect analysis survives, we still prevent real concurrency failures;
- if empirical confluence checking works, we gain safer parallelism and better debugging;
- if residual operations form braid-like structures, we gain compositional schedule transformations;
- if a restricted Yang–Baxter theorem emerges, it must earn its name through definitions and proof.

The repository is therefore both infrastructure and laboratory. Real agents generate traces. Traces expose counterexamples. Counterexamples refine the algebra. The algebra improves the scheduler. The scheduler creates more reliable agent systems and better experimental data.

We are not building another orchestrator whose correctness rests on confidence. We are building toward an algebra of interaction whose uncertainty is explicit and whose strongest statements are falsifiable.
