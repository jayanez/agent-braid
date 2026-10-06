# Proposed closed simulation architecture

Status: draft for ADR and public contract review before implementation integration.
The candidate model is effectful-workload-simulation-v1; existing integer-batch,
AIM/Git/M3/runtime contracts stay unchanged. No canonical ADR is adopted here.

Private configurations contain state, versions, immutable canonical aliases,
pending instances, captured reads, per-instance outcome and chronological events.
Each primitive is an atomic closed modeled transition: snapshot-read,
literal-write, derived-write, guarded-write, config-read, add-constant,
external-action. Derived values and guards refer to earlier identified captured
results. Predicates use only bounded integer equality/order. A simulated external
step appends an in-memory event; it never calls a provider or dispatches code.

Freeze input grammar, defaults, aliases/cycle handling, outcome alternatives and
observation before coding. Enforce existing planned limits: 1–6 instances,
64 resources/aliases, strings256, signed integer absolute bound 2**63-1,
expression depth12, input8MiB, <=720 topological schedules, <=20000 complete
paths, <=120000 steps and <=240000 events. Cap exhaustion is inconclusive and
retains visited counts plus conservative unvisited upper bound. No sampled
probability or silent truncation.

Exact observation preserves state, versions, results, outcomes and chronological
events; selected-values preserves only selected canonical values and outcomes.
Success matches under the latter are globally terminal-projection-match. Failed
paths retain emitted effects and suffix; they cannot produce equivalence or
runtime admission. Alias/hidden-effect uncertainty prevents independence.

Review must pin named race controls, immutable request/report digests, branch
replay/tamper rules, full-cost accounting and H2 guard-free additive class with
all intermediate values in bounds. H2 terminal candidates never mean semantic
commutation. Numerical feasibility thresholds are descriptive and may fail.
No sockets/processes/callbacks/imports from fixture text are permitted. Future
real adapter rights/refinement/isolation/execution need a separate adopted contract.
