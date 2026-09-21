# ADR 0008: Read-only Git and worktree adapter

## Status

Accepted by explicit founder decision on 2026-09-18. This architectural
acceptance authorizes the reviewed alpha design, not repository mutation,
concurrent execution, scientific approval, M1 closure, or production use.

## Context

The M1 analyzer needs evidence from real code-change workloads while preserving
the separation between adapters, AIM, analysis, scheduling and execution. Git
can expose committed and worktree path mutations, but mergeability and disjoint
paths do not establish semantic commutation.

## Decision

Add a local `agent-braid analyze-git` adapter using Python 3.12 and read-only Git
subprocesses. A versioned alpha request names a base commit and at least two
commit or worktree sources. Refs resolve once, worktree snapshots are observed
twice, and any change during observation is rejected.

The adapter maps stable path mutations to AIM 0.2 records in memory. Repository
identity derives from root commits rather than local paths. Complete coverage
means only tracked and non-ignored untracked path mutations in the observed Git
snapshot. Ignored files, hidden effects and undeclared semantic dependencies are
outside that domain. Unsupported or explicitly uncertain paths remain unknown.

The existing analysis report remains unchanged. Adapter provenance is bound into
the AIM input digest and emitted as a required, separate versioned artifact via
an explicit `--provenance-output` path.

## Alternatives

- Git-library dependencies would enlarge the alpha runtime and its supply chain.
- Automatic merge or checkout experiments would violate the read-only product
  boundary.
- Treating clean merges as semantic independence would overstate the evidence.

## Consequences

The adapter provides reproducible syntactic evidence but cannot detect hidden
invariants, generated artifacts or semantic coupling. Git must be installed.
Provider adapters and execution remain later, separately reviewed work.
