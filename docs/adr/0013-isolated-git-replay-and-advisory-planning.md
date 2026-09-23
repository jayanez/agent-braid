# ADR 0013: Isolated Git replay and advisory planning

- **Status:** proposed for review
- **Date:** 2026-09-23
- **Deciders:** founder review pending
- **Constitutional articles:** 2, 4, 6, 7, 9, 12–14, 19–21, 23–25

## Context

M1 observes committed and worktree path changes without applying them. M2 needs
reproducible evidence from alternative schedules, while the current Git evidence
does not establish merge behavior or semantic correctness. The first M2 cut
should test a narrow, immutable fixed-patch domain without turning the analyzer
into an execution runtime.

## Decision proposed

Add a standard-library-only replay layer for 2–4 commit operations sharing one
resolved base. Bound the batch to 64 changed paths and 1 MiB of aggregate patch
bytes. Resolve the existing M1 request to immutable commits, retrieve the
base/source objects into a temporary bare repository using only local file
transport, and apply every admissible operation order to a fresh temporary Git
index with `git apply --cached --binary`. Do not checkout files, run project
commands, contact network services, or mutate the source repository.

Name the observation `tracked-tree-v1`; it is the Git tree after all patches in
one order, including path names, modes and blob identities. Record all orders,
patch digests, per-step tree IDs, statuses and limits. A verifier independently
reconstructs and replays every schedule. Complete equal trees produce
`equivalent-observed`; differing complete trees produce `divergent`; any failed
patch application produces `inconclusive`. Unsupported operations remain
explicitly ineligible and cannot produce candidate waves, even when their fixed
patch happens to replay completely.

Emit dependency waves only when evidence verifies, every schedule completes
with the same tracked tree, and every operation is supported and certain.
Otherwise provide a deterministic serial order only when its replay completes;
all other cases require manual review. Every output states
`executionAuthorization: false`. Integration remains serial.

Add separate `0.1.0-alpha` replay-evidence and plan contracts. Preserve existing
AIM, report, Git request/provenance and certificate contracts. Keep exhaustive
enumeration for this four-operation cap; partial-order reduction, project test
execution, counterexample minimization and concurrent execution are later work.

## Alternatives considered

- Trust M1 path-disjointness for wave planning: rejected because it observes
  changed paths but does not replay patches or establish even fixed-patch tree
  equivalence.
- Reuse the integer certificate schema: rejected because that schema binds a
  different model and its verifier cannot replay Git patches.
- Execute tests or agents in temporary worktrees: deferred because it requires
  a broader sandbox, test-command and effect contract.
- Implement partial-order reduction now: deferred; at most 24 schedules fit
  the bounded first cut and complete enumeration is easier to verify.

## Consequences

The replay adds a local Git object copy and scratch indexes but no runtime
dependency. Evidence is reproducible while source commit objects remain
available. The verifier proves only a finite claim about fixed patches and the
named tracked-tree observation. It cannot establish source-code correctness,
hidden semantic independence, arbitrary interleaving safety, production safety,
or execution authorization. Negative and inconclusive results remain valid
research outcomes.

## Validation

Require tests for disjoint patches, different hunks in one file, conflict,
dependency, uncertain/unsupported paths, invalid or missing commits, tampered
evidence, omitted/duplicated orders, and unchanged source repository state.
Compare against serial, path-overlap and Git merge baselines. Report the zero
false-candidate threshold and both required positive utility cases. A passing
check does not accept this ADR or close M2; founder review remains pending.

## References

- [Constitution](../../CONSTITUTION.md)
- [M1 Git adapter](0008-read-only-git-worktree-adapter.md)
- [Operational semantics](../theory/OPERATIONAL_SEMANTICS.md)
- [Feature specification](../../specs/012-m2-git-replay-planner/spec.md)
