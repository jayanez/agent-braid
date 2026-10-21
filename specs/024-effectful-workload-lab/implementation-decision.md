# SPEC-024 architecture decision request

Status: pending founder decision. Prepared 2026-10-21 from public develop
`a6329c828011d1468fed3dfa4e98f5a8531167e2`. This file records a concrete proposal,
not adoption or permission for real effects. Existing task checkboxes remain
unchanged until their criteria and evidence are complete.

## Proposed bounded decision

Adopt the separate `effectful-workload-simulation-v1` architecture for the
SPEC-024 implementation only: an isolated standard-library simulator, immutable
inert JSON requests, closed atomic transitions, finite schedule/branch replay,
and explicit local report output. Review the exact proposed
[interface](contracts/simulation-v1.md) before deciding. Its SHA-256 at the
decision-request observation is
`ec0851a4503ec0d40d7dff9a8b9542a5d3dcc44843d2458c8dd738ebd4dedad5`.

Retain 1–6 operations, at most 64 resources and aliases, 256-character scalar
strings, signed integers bounded by 2**63-1, expression depth 12, input 8 MiB,
720 schedules, 20,000 attempted paths, 120,000 steps and 240,000 events. Lower
caps including zero remain explicit. Partial/error paths retain prior effects;
cap exhaustion is inconclusive. Declared effects cannot override actual modeled
access. Projection agreement is terminal-only and a separate finite event
diagnostic remains visible. Every report denies execution authorization.

The implementation may read bounded inert JSON and exclusively create explicitly
selected report files. It cannot launch processes, contact services, evaluate
fixture code, run models, collect real sources or execute an external action.
The modeled external-action primitive only appends to an in-memory event list.
Comparisons use the preregistered synthetic corpus and complete descriptive
cost accounting; a negative or inconclusive result is legitimate completion.

## Alternatives and consequences

- Extending `integer-batch-v1` would silently change ADR 0005's exclusion of
  partial external failure; reject that alternative and preserve its interpreter.
- Reusing runtime grants would confuse simulation with real execution; reject.
- Real database/API/deployment adapters and arbitrary project execution remain
  outside this decision and require separate reviewed refinement and authority.

No Constitution, accepted ADR, runtime schema, AIM certificate, source admission,
System One capability or frozen evidence is changed by accepting this bounded
architecture. Add the canonical ADR at the next unused identity during the
approved integration step; do not reserve an identity used by the HAR track.
Record the actual founder response and its scope separately. Technical Luna
inspection is not founder adoption, scientific acceptance or independent proof.

## Entry and exit gates

The feature requires “an ADR and public contract review before integrating its
implementation” (SPEC-024 spec.md, Authorities), and T002 depends on T001. The
implementation workflow stops on a missing required review. Complete technical
contract review and obtain the bounded architecture disposition before dependent
implementation. User authorization to implement the multi-track plan is recorded
as work authority, not silently converted into this feature decision.

After that decision, execute T002–T008 in their actual dependency order. Focused
positive/negative controls, quick/PR profiles, exact-candidate evidence and
separate scientific/human review remain required. No issue or milestone closes
merely because this decision request or a technical review exists.
