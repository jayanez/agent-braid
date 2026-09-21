# Ecosystem map

This map is a positioning aid, not a claim of feature parity or superiority.
Entries are based on first-party descriptions and must be refreshed through the
[research radar](../../research/radar/README.md).

| Layer | Representative systems | Primary concern | Agent Braid relationship |
|---|---|---|---|
| Orchestration | [OpenAI Agents SDK](https://openai.github.io/openai-agents-python/multi_agent/), [Anthropic multi-agent research](https://www.anthropic.com/engineering/multi-agent-research-system) | Agent delegation, handoffs, coordination and parallel work | Consume recorded plans/traces; do not replace orchestration |
| Protocols | [A2A](https://a2a-protocol.org/latest/specification/), MCP | Interoperable tasks, artifacts, messages and tool access | Map effect, identity, version and idempotency metadata into AIM without creating parallel semantics |
| Observability and evaluation | [NVIDIA NeMo Agent Toolkit](https://docs.nvidia.com/nemo/agent-toolkit/latest/) and runtime-native traces | Trace, profile, evaluate, and debug behavior | Attach portable concurrency evidence and ordering analysis to traces |
| Guardrails and policy | Runtime permissions, policy engines, sandboxes | Constrain allowed behavior | Produce evidence for a policy decision; never authorize execution itself |
| Concurrency control | Transactions, serializability, optimistic control, Git merge | Preserve correctness under shared-state interaction | Apply conservative resource/effect analysis and version constraints |
| Formal and algebraic methods | Rewriting, confluence, partial orders, braid/Yang–Baxter research | State and prove properties in defined domains | Maintain a bounded laboratory; treat analogy as hypothesis until proved |

Recent unreviewed work such as [CoAgent](https://arxiv.org/abs/2606.15376)
and the position paper [Multi-Agent Systems Should Prioritize Concurrency
Control](https://arxiv.org/abs/2608.18092) is directly adjacent. Agent Braid has
not reproduced either paper. They enter the M2 comparison backlog as source
claims, not evidence of Agent Braid's novelty, correctness or performance.

MCP's current security guidance identifies authorization, session, local-process
and SSRF risks. These reinforce the existing rule that external trace ingestion
and write-capable adapters require dedicated privacy and security review; protocol
support alone cannot satisfy that gate.

## Competitive gap under test

The hypothesis is that teams need portable, evidence-carrying analysis between
orchestration and execution policy. This is not yet established market demand.
It will be tested through integrations, independent reproductions, benchmark
coverage, contributor activity, and interviews. A negative result should narrow
or invalidate the thesis rather than be reframed as success.

## Adapter rule

Adapters for generic traces, OpenAI Agents, MCP, A2A, or NeMo must preserve:

- operation and attempt identity;
- resource/effect meaning and coverage status;
- dependency and version information;
- evidence provenance and hashes;
- unknown or unsupported fields without inventing certainty.

An adapter translates to AIM. It cannot create a second compatibility model or
raise an assurance class merely because the source is trusted.
