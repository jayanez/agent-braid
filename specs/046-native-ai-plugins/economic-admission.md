# Plugin + telemetry: economic admission — NO-GO

Decision date: 2026-10-17. Scope: first documentary batch only.
Source inspected: `48f4226db1e1b0565b1f8faf0eca81c150a65d30`.
Disposition: **NO-GO / unavailable / no-decision**. No economic action is
admitted, no forecast binding is implemented and no scenario execution is authorized.

## Identity reconciliation

The [consolidated identity map](identity-reconciliation.md) and its
[source inventory](identity-reconciliation.json) are the shared documentary
record for this batch. Published native plugins retain **SPEC-046 / ADR-0024**;
active local telemetry uses **SPEC-047 / ADR-0025**. The telemetry source
migration is local and unintegrated. Historical evidence and SPEC-044/T004 are
unchanged; no approval transfers to a different candidate.

## Admission rule and inspected surface

The proposed scenario is one real, read-only Agent Braid maintenance operation
with immutable input, exposed through the installed plugin and optionally
instrumented by the existing local telemetry design. Hosts are observation
blocks; repeating a task in two hosts does not create two independent episodes.
A viable economic decision needs at least two actually supported, permitted,
equivalent actions, result invariants, a causal decision-time state and complete
comparable costs. No new policy, scheduler or execution authority may be invented
to satisfy this gate.

`agent_braid/plugin_mcp.py` delegates to immutable workspace services;
`ToolingService.tools` in `agent_braid/tooling_mcp.py` exposes `analyze-work`,
`analyze` and `prepare` in analysis-only mode. The facade also exposes
`plugin-status` and `workspaces`. These are different operations, not equivalent
economic actions. `contracts/interface.md` permits runtime tools only with
explicit runtime configuration and existing exact grants. Those capabilities
exist but are outside this admitted analysis-only scenario; no fixed-runtime
pilot permission or acceptance transfers here.

| Proposed alternative set | Admission | Reason |
| --- | --- | --- |
| CLI versus MCP or two host wrappers | Rejected | Transport/observation variants do not establish distinct economic actions with equivalent outcomes and full costs. |
| Forecast enabled versus disabled | Rejected | Instrumentation/advisory comparison is not an underlying economic action set. |
| Immediate versus deferred analysis | Rejected | Would require a new scheduling/deadline policy; service duration and user latency can move in opposite directions. |
| Analyze, prepare, status and workspace listing | Rejected | Different purposes and outputs; no common result invariant. |
| Runtime serial versus parallel execution | Not admitted | Separate runtime configuration/grants and workload; outside this read-only scenario and its authority. |

FC.1 and FC.2 reconfirmed in the coordinated chat on this date that plugin/v0.1
has no two admitted economically equivalent alternatives or known forecast/grant
binding. Their source-bound accounting/ledger increment adds no plugin action,
native entry or runtime authority. The existing FC.1 `real-utility-resumption.md`,
section “Plugin and telemetry coordination”, independently retains these same gates in its local source
candidate based on `48f4226`. This batch references that result without
importing the ledger implementation. The telemetry owner separately completed
the local identity migration and retained NO-GO and open tasks.

## Evidence limits and stop

Aggregate `telemetry-batch/v1` data do not provide ordered independent episodes,
decision-time causal availability, paired counterfactual outcomes or complete
costs. Existing installation fixtures and host journeys establish their stated
engineering scope only; they are not real workload economic episodes. Neither
those observations nor the registered 108 attempts are reused as new utility
or forecasting evidence. No budget is borrowed from the fixed-runtime pilot;
additional spending remains EUR 0.

The minimum alternative-set gate fails. Stop after this documentary batch:
no evaluator, binding stub, scheduler, collector expansion, host/model invocation,
capture, installation, experiment, product release or issue closure. A future
reconsideration requires an explicitly identified existing action set, equivalence
criteria, causal state, full costs, permissions and its own authorization before
implementation or capture. This NO-GO does not close M4.5 or pending telemetry tasks.
