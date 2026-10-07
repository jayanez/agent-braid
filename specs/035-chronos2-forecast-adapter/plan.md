# SPEC-035: Implementation plan

## Technical context and scope

SPEC-034 telemetry/window/resource contracts. Synthetic adapter work can proceed after interface review without real-workload admission; actual model download/loading needs the distinct artifact/budget gate.
Bounded univariate/multivariate numeric histories and allowlisted covariates from SPEC-034, initially one request at a time on an explicitly measured CPU profile.
This is a planning packet. Future implementation targets named below do not yet exist because this change adds no runtime code.

## Constitution check before research

Articles 2/6/12 require unchanged dependency, enabledness, isolation and point-of-use constraints. Articles 7/20 distinguish numeric forecasting, discrete advice, analysis and execution. Articles 13/14 require provenance, unknowns and heuristic labels. Article 19 requires observed utility and complete costs; clause zero/Articles 9/21/23–25 preserve negative results and scientific limits. No MUST conflict or SHOULD deviation is proposed.

## Research, assumptions and alternatives

An existing pretrained Chronos-2 model may produce useful forecasts on local telemetry without fine-tuning; prediction quality, latency and CPU economics remain unmeasured.
Read [research.md](research.md), the [program](../034-workload-forecast-data/program.md) and [evaluation protocol](../036-forecast-parallelism-experiment/evaluation-protocol.md). Cheap rules and no-model outcomes remain possible. No available real corpus, permitted source window, effective placement diversity, device support or compute budget is presumed.

## Design and compatibility

Add a lazy optional forecast-chronos extra and a dedicated bounded local worker. Load only an approved, immutable local checkpoint and package closure; disable network access and reject remote paths/custom remote code. Map explicit missingness into the pinned backend only after role-specific conformance tests. Normalize backend tensors into target/horizon/quantile records with complete provenance. A worker failure yields a typed refusal and the existing non-model policy.
Use versioned feature-local [interface proposals](contracts/interface.md) and [data records](data-model.md). Core `dependencies = []` remains the default. Additive public APIs/extras require normal contract/versioning review during implementation; no legacy schema changes are made here.

## Validation strategy

Each REQ maps to its SC, named [prospective procedure](validation-plan.md), tasks and empty assurance evidence. Test stubs/owned synthetic controls first; permissioned source and real checkpoint procedures require their distinct gates. Run the repository quick profile after coherent implementation increments and the full PR profile once on a stable candidate. Keep clean-room capture, model cost measurements, human interpretation and founder adoption separate.
SPEC-034 telemetry/window/resource contracts. Synthetic adapter work can proceed after interface review without real-workload admission; actual model download/loading needs the distinct artifact/budget gate.

## Constitution check after design

No model score grants effects, operator authority, commutation, certificate issuance or new runtime resources. Proposed metadata/model workers do not run repository code. Historical contracts and M4 utility NO-GO stay unchanged. Unsupported evidence or hardware leads to refusal/defer/inconclusive, not weakened safety or favorable metric selection.

## Human review and unresolved decisions

Technical contract review; source rights/privacy and prospective yield; optional dependency/model provenance; installed hardware and enforceable numerical caps; frozen targets/roster/splits/budgets; independent outcome/cost review; exact capability promotion. All remain pending. Negative/infeasible protocol completion is distinct from capability acceptance.
