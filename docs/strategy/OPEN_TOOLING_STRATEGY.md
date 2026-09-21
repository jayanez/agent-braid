# Open tooling strategy

**Positioning:** Portable, evidence-carrying concurrency analysis for multi-agent systems.

## Product thesis

Agent Braid should first become useful open infrastructure. Its initial product is
a local, deterministic, read-only analyzer that explains which recorded or
declared operations appear independent, conflicting, ordered, or unknown. It
does not execute agents and its reports never authorize execution.

The immediate user promise is practical: carry inspectable evidence about
shared resources, effects, dependencies, uncertainty, and ordering constraints
across tools and runtimes. The mathematical program remains a falsifiable
research track and possible technical advantage, not the initial product claim.

## Initial users and jobs

| User | Problem | Initial job |
|---|---|---|
| Multi-agent application engineer | Parallel work can race on code, configuration, tools, or state | Analyze a plan or trace before choosing an execution policy |
| Platform engineer | Each orchestrator exposes different traces and controls | Translate portable metadata into one conservative interaction report |
| Reliability or security reviewer | A green verdict hides assumptions and evidence gaps | Inspect evidence, uncertainty, versions, and limits independently |
| Researcher | Concurrency claims are difficult to reproduce across systems | Re-run bounded fixtures and publish counterexamples or scoped results |

## Wedge and differentiation

Orchestrators decide who acts; protocols move messages; observability products
record what happened; guardrails constrain actions. Agent Braid targets the gap
between those layers: justification for which operations may overlap, which must
be ordered, and what evidence supports that conclusion. It should integrate
with existing systems rather than replace them.

The defensible assets are portable contracts, conservative analyzers,
reproducible counterexamples, independently reproduced benchmarks, and a public
claim discipline. Mathematical results become differentiating only when they
produce a sharper analysis, a valid restricted theorem, or a useful negative
result.

## Open-first sequence

1. **Research preview:** publish contracts, fixtures, a read-only analyzer, and
   the scientific radar after M0 closure and founder approval.
2. **Software adoption:** validate local code/Git/CI workloads during M1–M2.
3. **Platform adoption:** add adapters only after the core report and AIM mapping
   are stable enough to prevent semantic forks.
4. **Enterprise readiness:** begin with recorded traces and dry-runs. Consider
   write-capable integrations only after authorization, isolation, idempotency,
   versioning, recovery, privacy, and security contracts are defensible.

Repository visibility, package publication, external writes, production-safety
claims, and commercial services require separate decisions. A future plugin is
an optional distribution layer, never the source of truth.

## Decision principles

- Prefer `unknown` to unsupported safety.
- Measure false-safe classifications before optimization.
- Keep analyzer semantics vendor-neutral and adapters one-way into AIM.
- Publish limits and negative results with positive results.
- Separate executable controls, scientific interpretation, human review, and
  founder approval.

This strategy is subordinate to the [Constitution](../../CONSTITUTION.md),
especially Articles 1, 6, 13–16, and 19–25.
