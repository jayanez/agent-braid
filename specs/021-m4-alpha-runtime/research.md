# Research and design decisions

Engineering design research, not a new scientific study. Obtained runtime or host
compatibility evidence is now limited to the G1 no-model handshakes and local
C1/C2 implementation tests. Whole-M4 acceptance and actual tool-host exercises
remain pending.

## MCP revision compatibility

Context7 was queried against the official protocol repository and version-specific
2026-07-28 documentation on 2026-10-04. Published protocol generations differ in
lifecycle and version handling. Do not combine older initialize-based semantics
with newer discovery/per-request metadata. Choose and record a revision actually
supported by both installed clients in G1, then pin its official schema and tests.
The newest document is not evidence that either installed host supports it.

Primary references:
- https://modelcontextprotocol.io/specification/2026-07-28/server/discover
- https://modelcontextprotocol.io/specification/2026-07-28/basic/versioning
- https://modelcontextprotocol.io/specification/2026-07-28/server/tools
- https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-11-25/basic/lifecycle.mdx

A minimal dependency-free adapter versus an isolated optional official SDK remains
a G1 choice. Compare protocol completeness, host support, maintenance cost and
licensing before choosing; no package is installed by this proposal.

## Authority and trust

A model receives preparation output, including its digest. Exposing execute with
only that digest would let preparation masquerade as operator approval. Therefore
use a separate trusted local operator grant path; keep grant creation out of the
model tool registry. Do not claim protection against arbitrary shell access by a
hostile same-UID process. Host UI confirmations are useful human interaction but
not automatically machine-verifiable authority at the server.

## Concurrency

Retain serial execution as the reference. Recover bounded parallel preparation
through adapter-verified footprints and genuinely separated writable state, with
one coordinator publishing checked checkpoints. A rejected parallel plan may be
replanned serially, but requires a newly bound grant. No automatic expansion from
M2 replay evidence or from path disjointness. Changing observations, grant scope or
execution contract is a reviewed change, not an implementation convenience.

## Portability and measurement

Installed CLI paths and no-model handshake compatibility were observed; actual
host tool execution/recovery has not yet occurred. Proposed
primary host: Codex; contrast: Claude Code. Actual version/protocol support remains
an implementation gate. The minimal alpha coverage is two real clients on Darwin
and a deterministic core/protocol Linux reproduction. Claims name this exact matrix.
Measure correctness and overhead on frozen owned fixtures. Performance outcomes
may be negative or inconclusive. These records do not establish arbitrary-agent
safety or validate M3/M3.5 hypotheses.

## G1 observed compatibility and pin

See g1-contract.md, g1-review.json and g1-evidence/. Both installed clients
accepted 2025-11-25 and listed tools using a local no-effect server. No model
call, private runtime execution or persistent host configuration change occurred.
The implementation preflight chooses stdlib transport, zero new dependencies,
explicit phase budgets and purpose-bound operator grants. Paid/model-backed host
exercises remain gated on a separately agreed consumption budget.
