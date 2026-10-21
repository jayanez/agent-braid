# ADR: Closed effectful workload simulation

- Status: adopted by the founder for SPEC-024 implementation on 2026-10-21.
- Decision-maker: Juan Antonio Yáñez García, direct owner message in this task.
- Scope: the exact bounded architecture T001, followed by T002–T004 and the
  controls/comparison; no model, real-source or external-action execution.

## Actual approval

The owner stated: “Apruebo la arquitectura acotada T001 de SPEC-024. Continúa
con T002–T004, manteniendo la simulación local, sin modelos, fuentes reales ni
acciones externas, y después avanza con los controles y la comparación.”

This adopts the [decision request](implementation-decision.md) and its reviewed
[simulation contract](contracts/simulation-v1.md), SHA-256
`ec0851a4503ec0d40d7dff9a8b9542a5d3dcc44843d2458c8dd738ebd4dedad5`.
The earlier pending statuses remain dated preparation observations; their
bytes and the contract bytes are preserved. The technical Luna review and the
actual founder decision are separate records.

## Decision and consequences

Implement a separate standard-library finite simulator with private state,
captured reads, versions, immutable aliases, branches and retained event traces.
Preserve ADR 0005's integer-batch domain, all runtime/grant interfaces and frozen
evidence. Local JSON input and exclusive explicit report output are the only
filesystem interface. An external-action primitive appends an in-memory event;
it never dispatches a service or launches a process. Counts, uncertainty,
failure-after-effect and projection limits remain inspectable.

Reject silently extending integer-batch semantics, reusing runtime grants or
integrating real DB/API/deployment execution. The numeric envelope, finite H2
class, whole-cost controls and legitimate negative/inconclusive completion remain
exactly those in the approved contract. No scientific, human proof, external
reproduction, model fitting, data admission or capability promotion is accepted.

## Authority-inventory and integration boundary

Keep this adopted feature-local ADR as the decision record during implementation.
A new file under docs/adr would change the repository-wide authority inventory,
including SPEC-047's current snapshot owned by another track. Do not refresh
that snapshot or alter its approvals as a side effect. Canonical ADR numbering
and placement are a separately reviewed integration operation at the next unused
identity, with explicit inventory-impact reconciliation. This does not block the
owner-authorized isolated simulator implementation, reopen HAR, or reserve its
ADR identity. Historical source and evidence bindings remain unchanged.
