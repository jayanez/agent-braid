# SPEC-036: Implementation plan

## Technical context and scope

SPEC-034 data readiness and SPEC-035 measured adapter; SPEC-037 constrained advice mapping for the policy arm. Existing SPEC-022 accounting can be reused only with candidate-bound validation. SPEC-019 labels and SPEC-030 model fitting are not prerequisites.
Later held-out permissioned workload episodes/resource profiles admitted by SPEC-034, using the unchanged SPEC-020/021 fixed-patch execution language and observation/verifier contracts.
This is a planning packet. Future implementation targets named below do not yet exist because this change adds no runtime code.

## Constitution check before research

Articles 2/6/12 require unchanged dependency, enabledness, isolation and point-of-use constraints. Articles 7/20 distinguish numeric forecasting, discrete advice, analysis and execution. Articles 13/14 require provenance, unknowns and heuristic labels. Article 19 requires observed utility and complete costs; clause zero/Articles 9/21/23–25 preserve negative results and scientific limits. No MUST conflict or SHOULD deviation is proposed.

## Research, assumptions and alternatives

H1: numeric telemetry is forecastable at useful horizons. H2: forecast-informed choices improve complete wall time against a validation-selected non-model policy at matched admission and verification. H1 does not imply H2; either may fail.
Read [research.md](research.md), the [program](../034-workload-forecast-data/program.md) and [evaluation protocol](../036-forecast-parallelism-experiment/evaluation-protocol.md). Cheap rules and no-model outcomes remain possible. No available real corpus, permitted source window, effective placement diversity, device support or compute budget is presumed.

## Design and compatibility

First freeze the source window, grouped chronological partitions, targets/horizons, roster, transforms, action mapping, full cost boundary and decision thresholds. Backtest forecasting on immutable cutoff receipts. Then compare permitted serial/parallel choices using fresh owned results and independently supplied exact operator grants, rotating treatment order and retaining every refused/failed case. Evaluate deployment-costed recommendations, not an offline oracle that selects the fastest observed future action.
Use versioned feature-local [interface proposals](contracts/interface.md) and [data records](data-model.md). Core `dependencies = []` remains the default. Additive public APIs/extras require normal contract/versioning review during implementation; no legacy schema changes are made here.

## Validation strategy

Each REQ maps to its SC, named [prospective procedure](validation-plan.md), tasks and empty assurance evidence. Test stubs/owned synthetic controls first; permissioned source and real checkpoint procedures require their distinct gates. Run the repository quick profile after coherent implementation increments and the full PR profile once on a stable candidate. Keep clean-room capture, model cost measurements, human interpretation and founder adoption separate.
SPEC-034 data readiness and SPEC-035 measured adapter; SPEC-037 constrained advice mapping for the policy arm. Existing SPEC-022 accounting can be reused only with candidate-bound validation. SPEC-019 labels and SPEC-030 model fitting are not prerequisites.

## Constitution check after design

No model score grants effects, operator authority, commutation, certificate issuance or new runtime resources. Proposed metadata/model workers do not run repository code. Historical contracts and M4 utility NO-GO stay unchanged. Unsupported evidence or hardware leads to refusal/defer/inconclusive, not weakened safety or favorable metric selection.

## Human review and unresolved decisions

Technical contract review; source rights/privacy and prospective yield; optional dependency/model provenance; installed hardware and enforceable numerical caps; frozen targets/roster/splits/budgets; independent outcome/cost review; exact capability promotion. All remain pending. Negative/infeasible protocol completion is distinct from capability acceptance.
