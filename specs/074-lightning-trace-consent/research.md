# SPEC-074: Research

Shared research: [SPEC-070 research](../070-braid-lightning-foundations/research.md).

Spec-specific decisions:

- **Upstream adapters.** agent-lightning v0.x (`agentlightning/adapter/triplet.py`)
  builds a `TraceTree` from spans, finds LLM calls, matches rewards
  (`RewardMatchPolicy`) and emits triplets (`TracerTraceToTriplet`);
  `agentlightning/adapter/messages.py` (`TraceToMessages`) emits OpenAI-style
  message lists with tool calls. Both depend on OpenTelemetry spans and
  pydantic; the port keeps the tree, matching and output shapes over Agent
  Braid's own records, with no OpenTelemetry or pydantic import.
- **Upstream tracers** (`agentlightning/tracer/`) capture content by default
  through instrumentation; not ported. Agent Braid reads existing local records.
- **Redaction reuse.** `scripts/spec069_native_runs.py` has `SECRET_PATTERNS`,
  `Secrets.redact/scan/assert_clean` and `guard_leaks`; the pattern set moves to
  a shared runtime module so the script and Lightning use one list.
- **Retention precedent.** `agent_braid/system_one_shadow.py` uses
  `RETENTION_DAYS = 30` and `purge()`; Lightning follows the same model with a
  configurable bound of 90 days.
- **Rejected alternatives.** A `raw` consent level; redaction at export time
  only (content would sit unredacted on disk); one-way hashing of all text
  (useless for prompt optimization).
