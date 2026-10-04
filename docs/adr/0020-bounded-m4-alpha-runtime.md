# ADR 0020: Complete bounded M4 alpha runtime

- Status: Accepted by explicit founder decision on 2026-10-04 for SPEC-021 candidate 0de9d31; G1 and final closure remain separate gates.
- Date: 2026-10-04
- Decider: Juan Antonio Yáñez García, founder.
- Articles: 2–7, 12–16, 19–25.

## Context

SPEC-020 provides a durable, separately acknowledged serial fixed-patch result.
It does not cover runtime MCP clients, actual host portability or bounded parallel
preparation. ADR 0014 explicitly requires a new reviewed contract and authority
for broader capabilities. The roadmap still has six candidate M4 deliverables.

## Decision

Adopt SPEC-021's closure-matrix as the bounded engineering meaning of complete
M4 alpha. Integrate the analyzer's existing portable semantics with a separately
governed policy path, isolated concurrent fixed-patch preparation and serialized
private publication. Add a version-pinned stdio MCP adapter with Codex and Claude
Code as actual client observations. Keep the source read-only and the supported
operation language unchanged from SPEC-020. Add no arbitrary-code, promotion,
network-service or deployment capability.

Operator authority is supplied through a local operator path outside the model's
tool registry and binds the exact manifest and policy. A returned digest, producer
certificate, tool annotation or host identity is insufficient. Maintain one durable
logical run across retries, cancellation and explicit recovery.

Keep core runtime dependencies empty; an optional MCP SDK needs a recorded,
compatible pin and license check. Expanded execution contracts, numerical budgets
and host/protocol revision pins require G1 review before execution. Acceptance of
this proposal authorizes only the specified bounded implementation work. It grants
no authority to install hosts, create credentials, run paid exercises without an
agreed budget, publish externally, or close the milestone.

## Consequences and limits

A whole-M4 engineering closure becomes reviewable rather than inferred from
SPEC-020. Its exact coverage is two actual clients on Darwin arm64 plus independent
Linux x86_64 core/protocol reproduction. Other combinations remain unclaimed.
A speedup may be negative or inconclusive; safety and reproducibility must pass,
and usefulness then requires a documented founder decision. M3/M3.5 scientific
work, independent external validation and formal results remain separate.

On adoption, place this exact reviewed text in docs/adr, record founder provenance
and identify authority changes for all current assurance records. Re-review those
records before refreshing their authority bindings. Preserve historical approvals.

## Acceptance and closure

G0 records the exact candidate and the bounded scope. Whole-M4 closure is a later
G4 decision against all six obtained-evidence rows, fresh reproduction, independent
Luna review, disclosed limitations and unresolved findings. No passing CI status,
proposal approval, tag or evidence digest is itself milestone acceptance.

## Adoption provenance

The founder adopted the scope text from frozen candidate `0de9d31ae2cd6479b43a5d630e2932f5997f6235`.
Only title/status metadata and this provenance section differ from the reviewed
proposal. [Decision record](../../specs/021-m4-alpha-runtime/founder-review.json)
binds every reviewed proposal artifact; SPEC-020 acceptance remains unchanged.
