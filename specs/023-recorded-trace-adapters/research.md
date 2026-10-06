# Research and design decisions

## Inspected baseline

`agent_braid/analysis.py` accepts AIM `0.2.0-draft`, requires definition, instance
and attempt identity, rejects duplicate identities and dependency cycles, and
returns analysis-report `0.1.0-alpha`. It conservatively reports partial/unknown
coverage and external/transforming effects. It presently permits one attempt
per operation instance in an analysis batch.

`agent_braid/git_adapter.py` implements stable read-only Git observations.
`agent_braid/mcp_runtime.py` is an operator-configured stdio interface to the
bounded M4 runtime, with its own pinned protocol and grant checks. Neither is a
generic recorded-trace importer or an MCP deferred-task/state evidence adapter.
The initial adoption tracks in SPEC-011 are historical candidates; their earlier
statements about absent runtimes are not current assertions about M4.

## Decisions

| Question | Decision | Alternative and limit |
|---|---|---|
| First implementation | Generic synthetic metadata importer into existing AIM/report | Live SDK/client ingestion is deferred; no demonstrated need for a dependency |
| Missing semantics | Explicit loss plus unknown coverage; reject required identity gaps | Filling in effects, versions or dependencies could create false independence |
| Trace payload | Strict metadata allowlist and explicit source admission | Automated redaction alone cannot establish rights or complete semantic coverage |
| Identity across retries | Generic MVP rejects multiple attempts per instance | Provider spikes preserve timeline separately and report unsupported projection rather than flattening |
| Hashes | Preserve supplied source digests; label locally derived transformation hashes | A local metadata hash cannot be represented as the digest of unobserved source content |
| Provider order | Separate OpenAI approval and MCP async-state spikes after generic controls | Existing MCP stdio serving does not settle asynchronous recorded semantics |
| Ecosystem expansion | A2A/NeMo/OTel screening with explicit version/conformance/license/privacy gates | Popularity or a standards name is insufficient for adoption |
| Acceptance | Finite fixture retention, baseline parity and no false-safe fixture result | No claim of complete real-world effects or production safety follows |

## Source discovery prerequisite

T006/T007 must record a primary source URL, retrieval date, selected immutable
version/commit or specification revision, relevant sections, license and evidence
availability. This spec intentionally makes no claim about latest upstream
versions, SDK syntax or protocol support. If no bounded stable source can be
selected, record `inconclusive`/`watch` and preserve the negative result.

The lifecycle corpus is registered before mapping: approval requested/approved,
approval rejected, interruption/resumption, repeated attempts, deferred task
working/completed/failed, expired state, unsupported version and sensitive
payload. Record which source concepts cannot be represented in current AIM.
Missing cases cannot be removed after results are known.

## Hypothesis and invalidation

Structured source metadata may increase inspectable lifecycle/provenance coverage
relative to manually flattened operations. A lost identity/version, unsupported
state silently treated as completed, hidden payload leakage or a false-safe
classification invalidates promotion for that mapping. A negative spike is a
valid completed research deliverable; generic implementation can remain useful.

## Evidence status

These decisions arise from inspected repository code/contracts and existing
policy. No external documentation refresh, live provider run, new adapter test,
real trace admission or measured capability gain has been obtained here. Future
raw evidence belongs in `assurance.json` only after execution and provenance
capture. Human review and provider adoption remain pending.
