# Research and decision record

## Observed source claims

- OpenAI Agents documents agents, handoffs, tools, guardrails, sessions, tracing
  and pause/approve/resume flows.
- MCP documents asynchronous tasks, task status, protocol version metadata and
  explicit state handles in its evolving specification.
- A2A provides task/artifact interoperability and is developing conformance tools.
- OpenTelemetry GenAI/agent conventions expose useful trace metadata but remain
  experimental in relevant areas and may include sensitive content.
- CoAgent/MTPO reports a concurrency-control protocol in an unreproduced preprint.

These are source claims, not Agent Braid evidence.

## Alternatives considered

1. Integrate provider SDKs directly from the weekly radar: rejected because it
   creates dependency and semantic drift before a capability is demonstrated.
2. Put all adoption metadata into radar entries: rejected because historical
   snapshots would become mutable and weekly surveillance would become a delivery
   mechanism.
3. Track only market popularity: rejected because popularity is not a measurable
   correctness or interoperability gain.
4. Use a separate adoption registry with bounded spikes: selected because it
   preserves source provenance, decision history and the existing evidence boundary.

## Limits

The pathline can prioritize work and prevent unsupported adoption claims. It cannot
prove that a technology is best for the market, establish scientific novelty or
replace a feature-specific review. The initial five dispositions are provisional.
