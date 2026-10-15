# Technical cost companion v1

This additive library contract implements SPEC-045 REQ-005/006 and the cost
boundaries in SPEC-034–036. It changes no existing forecast/advice/experiment
receipt, runtime grant, M4.5 ledger or worker limit. The entry points are
`forecast_cost.CostRecorder`, `validate_cost_ledger` and `summarize_cost_ledger`.
The version is `agent-braid-forecast-technical-cost-v1`.

## Scope and boundaries

A ledger binds a run ID, provenance domain, input digest and measured artifact
identity. It contains an end-to-end monotonic wall interval, phase offsets,
failure outcomes, CPU counters, memory observations and cleanup/publication
coverage. One clock origin covers preparation through final owned cleanup and
payload export. Final ledger publication after sealing is explicitly outside
that boundary; it remains a gap until independently measured by a supervisor.

Required stage inventory: data preparation, artifact provisioning, engine startup,
model startup, residency, forecasting, failure controls, advice, cache, grants,
replay, isolated preparation, isolated execution, waiting/deferred work,
verification, export and cleanup. Multiple phases can share a stage. Each phase
has a unique ID. Absent stages are gaps. Reused artifact preparation carries its
source digest and remains unallocated; it is neither free nor implicitly amortized.
A future amortization decision must specify its denominator and source receipt.
Explicit not-applicable reasons describe the selected procedure, not a waiver
for a future deployment or experiment.

The sum of phase durations is descriptive only. The union of measured intervals
plus the coordinator residual equals the complete wall interval. This residual
is unattributed wall time, not measured coordinator CPU; missing worker intervals
can also contribute to it. A failed,
refused, cancelled or timed-out phase retains its interval and outcome. Omitted
failure attempts cannot improve acceptance. Returned forecast refusals are kept
in their original packets; a completed instrumentation phase means the call
returned, not that a forecast succeeded.

## Counter semantics

Four CPU domains are required: coordinator process only, owned client children
excluding daemon/worker, worker cgroup including its descendants, and daemon
processes excluding containers. Counter deltas reject reset/negative values,
bools, repeated domains/meters and invalid intervals. A VM-wide CPU counter cannot
be added to its guest/worker counters. Distinct meter IDs and declared scopes
are schema assertions, not independently verified disjointness. Partial intervals
are gaps. Missing counters remain null, including worker/daemon counters lost
on crash. A full-boundary collector must take terminal snapshots before removal,
or retain an explicit reason when death prevents observation.

Process-lifetime RSS peak, cgroup-lifetime peak and periodic cgroup samples have
separate scopes. Samples carry their period; configured limits carry their own
value or missing reason. Memory observations are never summed. A sample maximum
is not a lifetime peak; a process-lifetime peak may predate the experiment.

## Validation and authority

Records are finite, bounded to 1 MiB, 1024 phases and 128 memory observations,
and canonically hashed. Validation verifies schema and integrity only.
`reportedCoverageComplete` describes the submitted inventory. It cannot verify
source authenticity, effective enforcement, disjoint CPU domains, financial
allocation, or any decision. `sourceBindingsVerified`, `fullDeploymentCostAccepted`,
`economicCostAccepted` and `executionAuthorization` remain false.

`scripts/reproduce_forecast_cost.py` measures owned synthetic baseline/cache work,
absent-model refusal, optional externally granted Git fixtures, export and cleanup.
It requires the imported package to reside in the current interpreter's purelib
installation and binds its actual Python file hashes, separately from a wheel
hash. Failed origin/identity preflight, handled interrupts and cleanup failures
produce nonzero terminal ledgers; missing identities stay null with a reason.
The CLI handles SIGTERM, while SIGKILL and storage failure still require the
external supervisor and retained partial outputs.
It records coordinator CPU and waited child CPU with their observation boundaries,
and host process RSS with platform units. It never loads a model, starts/stops
Docker, changes approval pins or accepts utility. Outputs use a new private
exclusive directory; failed or partial outputs are retained without overwrite.
Actual model/daemon counters and historical provisioning allocation remain open.

## Outer synthetic publication observer

`scripts/reproduce_forecast_cost_supervised.py` runs only the fixed installed
synthetic driver. It records a separate wall boundary through publication and
readback of its inner receipts/index. Its waited-child-tree counters overlap
inner CPU and are not summed with it. The parent terminal receipt's publication
remains a named gap, as do unavailable worker/daemon measurements and reused
provisioning. This narrows the measured publication boundary without changing
`publicationIncluded` or claiming complete deployment costs. A failed child or
missing receipt stays visible and cannot confirm cleanup.
