# SPEC-038: M4 real-workload closure protocol

## Development status — 2026-10-08

Exact source rights and protocol are approved for bounded implementation and
preparation. See [implementation readiness](implementation-readiness.md) for the
scoped decision and current gates. Earlier proposal descriptions below retain
their design-time context; stable review, capture and whole-M4 acceptance remain pending.

## Purpose and scope

Prepare a reviewable protocol for one prospective, permissioned real-repository
workload to evaluate the bounded local runtime in SPEC-020/ADR 0019. This is a
research protocol and source-feasibility packet. It authorizes no capture,
repository code or tests, grants, provider calls, installation, ref promotion,
or execution by itself. Exact source rights and protocol are approved through
the separate owner decision; runtime admission and capture remain pending.
A completed evaluation may validly conclude infeasible, negative, or inconclusive.

Owner-permissioned source frame, subject to runtime feasibility review: the
two immutable M2 public workstream commits recorded in
[source-rights-manifest.json](source-rights-manifest.json). They represent
actual Agent Braid engineering: observation normalization and counterexample
reduction. Their M2 corpus is a lead, not an M4 sample, and the historical
approvals authorize neither M4 execution nor its costs. Initial patch inspection
shows one 3-path, 64-line modification and one 5-path, 999-line addition/change.
Static diff shape is within the current aggregate path and byte ceilings (8
paths and 63,080 diff bytes); both operations have ordinary 100644 A/M paths
and their source footprints do not overlap. This is a read-only static finding,
not runtime admission or a rights decision. No alternative source is
substituted. Runtime preparation and execution are not authorized by this
specification. If current runtime preparation rejects the candidate after the
required reviews, report infeasible; do not change source identity or runtime
semantics to make it fit.

## Authorities

Constitution Articles 0, 2–7, 9, 12–15, 19–25; GOVERNANCE.md; ADRs 0013, 0014,
0019 and 0020; SPEC-020; SPEC-021 and its six-row closure matrix/G4 decision;
SPEC-022's synthetic measurement protocol and stable harness review; SPEC-013's
M2 source/decision records; operational semantics; Spec Kit and validation
profiles. Feature records cannot amend these authorities. SPEC-021's historical
G4 NO-GO and M4-open status remain unchanged. SPEC-022 evidence remains
synthetic and separate.

## Requirements and acceptance scenarios

### REQ-001 — Exact source rights, provenance, and feasibility

Before any capture implementation, name the source owner/rightsholder, exact
repository/base/operation commits and patch hashes, permission scope and term,
redistribution/retention limits, provenance, and permitted local processing.
Obtain a new, explicit approval covering the exact M4 protocol and workload.
Verify the immutable source and common base without running project code. Freeze
the complete source frame and retain every candidate, exclusion, and reason.
Do not treat M2 founder approval or the public availability of commits as rights
or M4 consent.

- **SC-001:** Given absent, ambiguous, expired, or narrower-than-needed rights,
  when readiness is reviewed, then capture is blocked and the record says
  rights-pending/infeasible with no source execution.
- **SC-002:** Given a candidate outside fixed-patch limits, when feasibility is
  checked, then it is refused; no replacement corpus is silently selected.

### REQ-002 — Fixed protocol and runtime boundary

Use only the unchanged SPEC-020/ADR 0019 contracts: 2–4 distinct immutable
ordinary-text A/M operations from one base; complete paths and dependencies;
fixed patches; 16 changed-path and 256-KiB aggregate caps; private destination;
existing independent operator grant, verifier, and `tracked-tree-v1` observation.
No arbitrary repository code, tests, hooks, network, provider/model calls,
external writes, source-ref promotion, paid services, installation, or new host.
Unknown effects/dependencies, unsupported modes, drift, invalid grant, or
verification disagreement are refusals/failures, never successful observations.

- **SC-003:** Given a frozen eligible manifest and a malformed, stale, unsafe,
  missing-authority, or wrong-tree case, when the protocol's negative controls
  are evaluated, then the current runtime refuses or records failure without
  promoting a ref or weakening the grant/verifier boundary.

### REQ-003 — Matched comparison and full cost boundary

Compare the actual SPEC-021 policy coordinator in `--mode serial` and
`--mode parallel` on identical immutable inputs and matched environment. Run two
operation orders (AB and BA), two unscored warm-up pairs per order, and three
measured pairs per order (six measured pairs total). Use the exact seed and
deterministic pair/treatment order in `protocol-review-packet.md`; freeze it in
the stable manifest. Retain all intended, attempted, valid, invalid, failed,
refused, recovered, and unexecuted slots; no optional stopping, replacements,
or complete-case denominator. The total dispatch budget is 45 minutes, with no
new treatment started after expiry; each treatment has a 360-second observation
deadline matching the existing SPEC-021 tool timeout. A timeout is incomplete,
not a hard-kill authorization. A separate fresh Python process inspects all 20
treatment slots and independently verifies each completed result. For each
treatment, total wall begins before evidence/input production and ends after
consumer verification, report serialization, and cleanup; include replay,
preparation, grants, execution and verification, with disjoint phases and
explicit residual. Report fresh-process verification and source/rights,
operator, setup, and final observer costs separately. Nested views are not
double-counted. This six-pair sample is descriptive only; it has no threshold,
population or causal claim.

- **SC-004:** Given six registered measured pairs plus four warm-up pairs and a
  frozen deterministic treatment order, when any pair is refused, invalid,
  failed, interrupted, recovered, or not dispatched, then its original slot
  remains visible and no replacement is inserted.
- **SC-005:** Given phase timers and receipts, when total cost is reported, then
  all named phases, residuals, setup/rights/operator costs, and omitted or
  unmeasured costs are explicit and non-overlapping.

### REQ-004 — Actual-task relevance and bounded interpretation

Explain why the workload represents an actual Agent Braid repository task,
which decision boundary it exercises, and what remains unsupported. Report
conflicts/dependencies, refusal behavior, verified final trees, safe recovery,
diagnostic usefulness, overlap observations, and complete overhead. A negative
or null result is valid. Do not infer generalized utility, Article 19 discharge,
confluence, causality, safety, or Yang–Baxter properties from this finite case.

- **SC-006:** Given complete, negative, inconclusive, or infeasible outcomes,
  when the result packet is prepared, then all preserve protocol adherence and
  interpretation limits; none changes SPEC-021's G4 decision or closes M4.

### REQ-005 — Two separate human review boundaries and milestone decision

Before implementation/capture, obtain protocol-and-source-rights review of the
exact workload, rights evidence, protocol, limits, order, budgets, and stop
rules. After a narrow harness exists, freeze and independently review its exact
candidate and stable manifest before any capture-specific approval. These are
separate decisions. After evidence, prepare a complete decision packet for a
new founder decision over whole M4; only that exact decision can change M4
status. No prior decision is inherited.

- **SC-007:** Given no protocol/source approval or no stable harness/manifest
  review, when capture is requested, then it remains blocked at the applicable
  boundary.
- **SC-008:** Given a complete actual-workload packet, when whole-M4 status is
  considered, then the historical SPEC-021 G4 NO-GO remains visible and a new
  explicit founder whole-M4 decision is required.

## Scientific boundaries and compatibility

Hypothesis: on this particular actual repository task, the unchanged runtime
may provide sufficiently useful verified/recoverable results to justify its
measured total cost. The protocol can reject this hypothesis. The independent
unit is a task operation/pair within this one source frame, not repeated timers
as independent workloads; population-level conclusions are unsupported.

Observation is current `tracked-tree-v1`; execution is the existing
`authorized-serial-index-patch-v1`. No schema, public API, grant, capability,
host, or runtime contract change is proposed. M2's old test and approval records
are provenance only; they are not reused as M4 outcomes. Synthetic SPEC-022
results cannot substitute for actual-task evidence. M3/M3.5 gates are
independent and unchanged.

## Evidence and unresolved questions

Obtained M4 evidence: none. Planned evidence and all unresolved rights/yield
questions are in `assurance.json`, `research.md`, and the review packet. No
source execution, probing, or capture was performed while preparing this spec.
