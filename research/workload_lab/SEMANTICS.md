# Closed effectful workload semantics

The exact wire/transition contract is
[simulation-v1](../../specs/024-effectful-workload-lab/contracts/simulation-v1.md),
adopted by the [feature-local architecture decision](../../specs/024-effectful-workload-lab/architecture-decision-20261021.md).
This package is experimental simulation, not a runtime or an AIM certificate.

`model.validate` rejects invalid requests before exploration. Each schedule starts
from a deep private initial configuration. `step` consumes the head of the chosen
pending schedule on success/error; blocking retains the current unexecuted head.
Earlier effects survive an error. Write and version overflow are checked before
either mutation. The event ledger is a per-path set of explicit keys, not a real
exactly-once delivery mechanism. No fixture text becomes code or a callback.

`explore_paths` enumerates lexical topological orders and outcome products in
declared branch order. Assigned, attempted, completed and partial counts remain
distinct. A cap stops before exceeding its count, preserving the partial path
and pending suffix. A zero event cap still permits operations that emit nothing;
a zero step cap attempts a path but cannot take a step. Exact equality at a cap
is complete only if no admissible assignments remain unvisited.

Raw configurations and before/after step records remain in all reports.
`compare` separates exact finite agreement from selected-value terminal projection
matches and reports every raw mismatch dimension. Failure/blocking or incomplete
coverage is inconclusive. `trace_safety` separately reports event chronology,
duplicates and retained events on error paths; no status is a universal safety
or contextual-equivalence verdict.

`evidence.explore` binds the original request and current source/contract bytes.
`verify` regenerates the full deterministic report. Timings stay in the separate
experiment report. CLI reads bounded nonsymlink regular files and exclusively
creates explicit outputs. Its report transport bound is 512 MiB; an oversized
encoded artifact is refused, never silently truncated or labeled complete.
Model count limits do not establish a hard process-memory or wall-time guarantee.
All outputs retain `executionAuthorization: false`.
