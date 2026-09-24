# ADR 0014: Contract boundary for parallel integration

- **Status:** Accepted by explicit founder decision on 2026-09-24 for the bounded T013 prototype. No runtime or promotion authority is granted.
- **Date:** 2026-09-24
- **Deciders:** Juan Antonio Yáñez García, founder
- **Constitutional articles:** 6, 7, 12–14, 19–20

## Context

The accepted [ADR 0013](0013-isolated-git-replay-and-advisory-planning.md)
establishes a bounded experiment over fixed commit patches and tracked Git
trees. Its result is consultative, and it explicitly does not prove that live
integration work is safe to execute in parallel. M2 follow-up work must address
resource limits and concurrent callers, plan integrity, and a separately
enforced execution contract before testing a parallel integration prototype.

## Proposal

Adopt the draft [parallel integration contract](../architecture/PARALLEL_INTEGRATION.md)
as the design boundary for T013, subject to review. Any prototype must pin a
common base, isolate each operation's worktree and index, bind verified
dependencies and declared read/write/shared-resource footprints, enforce
resource limits, reject stale inputs at use time, and fail closed on conflicts,
missing checks, or incomplete traces. A single coordinator computes candidate
integration state privately; agents cannot mutate the target ref. The first
prototype is read-only and shall not promote results.

Git replay evidence and `executionAuthorization: false` remain distinct from
runtime admission. Neither equal final trees nor path-disjoint changes supply
missing footprints, test results, or external-effect guarantees. Any broader
capabilities require a new reviewed contract and explicit authority.

## Consequences

- T009–T011 strengthen bounded Git execution and plan-artifact validation but
  do not themselves implement concurrent integration.
- T012 is accepted for the exact proposal and contract hashes in
  `specs/012-m2-git-replay-planner/t012-founder-review.json`.
- T013 may begin within the bounded local, read-only profile recorded in the
  feature plan and evidence. It must measure safety and resource overhead
  against serial integration and retain negative cases.
- M2 remains open; neither this proposal nor a passing local profile closes it.

## Validation and review

The contract proposal will be checked for consistency with Constitution
Articles 6, 12, and 19 and with ADR 0013. The prototype's corpus must include
stale-base, undeclared-resource, conflict, resource-exhaustion, cancellation,
and failed-validation cases. Zero unsafe admissions and agreement with a serial
reference are required before reporting a useful parallelism result.

Passing automated checks does not accept this decision. Founder review must
record the exact reviewed contract revision before T013 implementation starts.
The founder decision was recorded on 2026-09-24. It authorizes the prototype
work only; promotion and any expansion of execution authority remain prohibited.
