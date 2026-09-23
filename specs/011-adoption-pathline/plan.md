# Implementation plan

## Technical context and scope

Add a dependency-free adoption-track registry next to the read-only radar. The
registry links a source claim to a falsifiable differentiation hypothesis and a
sequence of bounded gates. It is governance metadata, not AIM and not an
execution contract.

The implementation is limited to the registry, schema, validator, tests,
documentation and five initial candidate records. It does not implement adapters,
install SDKs, contact external services or change public runtime behavior.

## Design decisions

- Keep weekly radar JSON immutable and read-only; link future records to tracks.
- Use one stable `trackId` per adoption investigation and one explicit `stage`.
- Require a baseline, comparable alternative, capability delta, falsifiable
  hypothesis and evidence plan before `differentiation-hypothesis`.
- Require a local, deterministic spike before `specified`.
- Require a separate Spec Kit feature and ADR for contracts, dependencies,
  security boundaries, runtime behavior or scientific claims.
- Reuse AIM and the existing analysis-report contract for later adapters; do not
  create a parallel compatibility model.
- Never overwrite historical radar or adoption decisions; revisions create new
  records or append an auditable transition.

## Adoption record model

Each track contains source references, an explicit owner and next decision,
capability/baseline comparison, hypothesis, metrics, evidence plan, affected
artifacts, risks, stage history, decision and limits. The validator enforces
allowed stages, terminal decisions, required fields, monotonic transition order,
existing artifact references, source URLs and links to committed radar IDs when
available. It does not decide whether a capability is genuinely superior.

## Seeded candidates

The initial registry records all five current signals as `triaged` or
`research-only` candidates with no obtained evidence and no implementation task:

1. OpenAI Agents approval-aware evidence — `triaged`.
2. MCP asynchronous task/state analysis — `triaged`.
3. A2A conformance-backed task evidence — `watch` pending a selected version/TCK.
4. OpenTelemetry evidence transport — `watch` because conventions are
   experimental and content may be sensitive.
5. CoAgent/MTPO — `research-only` because the source is an unreproduced preprint.

These dispositions are process defaults for the first record, not scientific or
market conclusions. A future monthly or milestone review may change them.

## Validation strategy

The paired tests cover a valid registry, missing baseline/metric, invalid stage
transition, adopted track without the required feature reference, missing source
provenance, stale artifact references, duplicate IDs and a negative spike outcome.
Repository validation additionally checks JSON, links, Spec Kit structure and the
existing full suite. Clean-room reproduction and provider execution remain outside
this feature.

## Human review and unresolved decisions

The registry is draft until a human reviews the seeded dispositions. No record
marks a technology `adopted`. Any future promotion beyond the spike stage requires
its own founder/reviewer decision and, when applicable, an ADR and PR.
