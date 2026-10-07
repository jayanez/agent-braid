# FC.1 — Forecast-guided parallelism experiment

Status: four draft implementation/research specs, dated 2026-10-07. This packet
plans the experiment and Chronos-2 integration; it has no model, source-window or
utility acceptance evidence. No implementation task is completed.

The useful capability under investigation is that Agent Braid learns from
permissioned observed workloads when and where admitted parallel preparation is
economically worthwhile. In the initial experiment learning means using frozen
history, a pretrained zero-shot forecaster and development-only policy selection;
it does not mean fitting Chronos or continual self-training.

| Spec | Deliverable | Exit boundary |
|---|---|---|
| [034](spec.md) | Permissioned numeric telemetry, causal windows and local resource receipts | Source/privacy/yield decision; no assumed real corpus |
| [035](../035-chronos2-forecast-adapter/spec.md) | Optional local Chronos-2 adapter with typed forecasts | Approved immutable artifact plus installed CPU conformance/costs |
| [036](../036-forecast-parallelism-experiment/spec.md) | Rolling-origin forecast and complete-cost policy experiment | Supported, negative, inconclusive or infeasible decision; positive result is not mandatory |
| [037](../037-forecast-advisory-integration/spec.md) | Read-only advice, shadow, System 1 bridge and exact promotion/rollback | Separate utility and founder capability decisions; independent operator grant for execution |

The dedicated [FC.1 milestone](https://github.com/jayanez/agent-braid/milestone/18)
contains four parent specs and 33 implementation/gate tasks. Parent issues:
[034](https://github.com/jayanez/agent-braid/issues/335),
[035](https://github.com/jayanez/agent-braid/issues/344),
[036](https://github.com/jayanez/agent-braid/issues/353) and
[037](https://github.com/jayanez/agent-braid/issues/363). The tasks remain open. Completion of a research protocol with no benefit
does not accept an operational forecasting capability or close M4/M3.5.

## Supported when and where

When: choose between the existing admitted serial and parallel preparation modes
for the next bounded batch. Forecasting can recommend serial or abstain; it does
not add automatic delay/retry/migration or new waves. Economic advice considers
advisory overhead and the whole safety/verification chain.

Where: the initial registered local host/resource profile and its existing
admitted capacity/worker slots. Do not claim distributed placement or choose
unregistered hosts. If only one profile/option has actual measurements, placement
comparison is unavailable or inconclusive. A broader resource set needs a new
reviewed execution/refinement contract and fresh group evidence.

## Ordered gates and critical path

1. G0: technical review of data/advice boundaries and the feature-local ADR
   proposal; record source owners, workload domain and numerical capture limits.
2. Implement standard-library envelopes, synthetic controls and permission-aware
   capture/window/resource tooling (034/T002–T005). Stubs and cheap baselines can
   proceed without ML download or a successful research hypothesis.
3. G1: source/privacy/window/yield and experiment registration, including purged
   partitions, candidate roster, primary groups, outcomes, budgets and fallback.
   Insufficient yield has an explicit infeasibility exit (034/T007–T008,
   036/T001 and 036/T008). It does not require model fitting.
4. G2: exact optional dependency/checkpoint/license/deployment approval (035/T001)
   before provisioning/loading; implement stubs and source-verified mapping,
   bounded worker and installed conformance (035/T002–T008). Synthetic CPU
   conformance may run without permissioned workload utility data after G2.
5. Implement the read-only deterministic mapper and shadow controls
   (037/T001–T003, T005–T006), then the complete evaluation harness
   (036/T002–T006). Optional System 1 bridging has its own accepted interface;
   neither native neural-model selection nor bridge completion blocks the
   runtime-only experiment.
6. G3: freeze an integrated candidate and complete launch receipt, then obtain
   actual source/compute/per-run operator authority for the registered holdout
   experiment (036/T007). The experiment needs G1 data readiness and G2 measured
   real Chronos conformance. No current document supplies either approval.
7. G4: review all costs/outcomes and issue an exact-population utility decision
   (036/T008–T009). A valid negative/inconclusive/infeasible result ends the
   research protocol with forecasting unpromoted.
8. G5: optional positive capability promotion, drift controls and rollback
   decision (037/T007–T008). A positive utility decision alone never issues an
   operator grant. Founder capability adoption and milestone interpretation are
   recorded separately.

Dependency graph: 034 contracts → 035 adapter and 037 mapper; 034 readiness +
035 conformance + 037 mapper → 036 experiment → 037 promotion. Baseline/synthetic
engineering and shadow tooling are possible before positive utility. No cycle
requires an experiment result in order to build its own measurement tools.

## Definition of experiment completion

Register every source/episode/window/arm/exclusion and numerical decision rule;
obtain actual conformance and outcome evidence, or a documented feasibility
exit; execute all admitted controls with raw provenance; report complete coverage,
forecast accuracy, interval behavior, deployment costs and group uncertainty;
record the bounded human interpretation. No guarantee, speedup or promotion is
required to finish the research protocol.

Operational adoption additionally requires complete verifier/grant/refusal
controls, measured useful total cost for the selected group, accepted installed
hardware/artifacts, exact-capability founder decision and a rollback path.
Historical SPEC-021 G4 NO-GO and M4 open status remain in effect.

## Explicit deferrals and decisions

No cloud endpoints, paid services, new runners, arbitrary repository commands,
source-ref promotion, fine-tuning, continual learning or generalized scheduling
safety model. Toto is an optional prespecified comparator; Chronos-2 and cheap
baselines are mandatory for an executable positive-result experiment. TimesFM-3
is deferred because its downloaded weights have non-commercial/non-production
restrictions; no new TimesFM integration is proposed.

The [protocol](../036-forecast-parallelism-experiment/evaluation-protocol.md)
states proposed numbers and mandatory review before collection/evaluation. The
[source manifest](../035-chronos2-forecast-adapter/reference-sources.json)
records inspected upstream identities, not installation or approval. Workload
rights, actual yield, resource diversity and CPU economics remain unknown.
