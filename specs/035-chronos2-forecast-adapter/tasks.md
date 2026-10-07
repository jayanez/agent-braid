# SPEC-035: Tasks

All implementation, collection, experiment and approval checkboxes remain pending. Paths outside this spec are prospective targets. Dependency independence is not authorization for concurrent agents. Every receipt must bind actual command, candidate/input hashes, environment, all attempted outcomes and limits.

- [ ] T001 (REQ-002 REQ-005 / SC-002 SC-005): Review the Chronos-2 artifact, package closure and CPU envelope.
  Dependencies: SPEC-034/T001; model/dependency/budget review. Target files: specs/035-chronos2-forecast-adapter/model-manifest-candidate.json; dependency-lock proposal.
  Verification: Review exact rights and wheel/checkpoint hashes before provisioning; freeze supported hardware and measurable limits.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/035-chronos2-forecast-adapter/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/035-chronos2-forecast-adapter/evidence/t001.json`. Obtained evidence: none.
- [ ] T002 (REQ-001 REQ-002 / SC-001 SC-002): Implement the lazy optional adapter interface with stubs.
  Dependencies: T001 interface review; SPEC-034/T002. Target files: agent_braid/forecast_chronos.py; pyproject.toml; tests/test_forecast_chronos.py.
  Verification: Default imports and CLI never load ML; unknown/unapproved revisions refuse and the optional installed wheel contains the backend.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/035-chronos2-forecast-adapter/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/035-chronos2-forecast-adapter/evidence/t002.json`. Obtained evidence: none.
- [ ] T003 (REQ-003 / SC-003): Implement target, covariate and missingness translation.
  Dependencies: T002; SPEC-034/T004. Target files: agent_braid/forecast_chronos_inputs.py; tests/test_forecast_chronos_inputs.py.
  Verification: Check channel order, regular grid, late values, past-only masks and cross-partition groups against pinned preprocessing source.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/035-chronos2-forecast-adapter/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/035-chronos2-forecast-adapter/evidence/t003.json`. Obtained evidence: none.
- [ ] T004 (REQ-004 / SC-004): Implement typed quantile outputs and median labeling.
  Dependencies: T003. Target files: agent_braid/forecast_outputs.py; tests/test_forecast_outputs.py.
  Verification: Assert target/horizon/quantile axes, p50 semantics, finite ordered outputs, units and uncalibrated interval labels.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/035-chronos2-forecast-adapter/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/035-chronos2-forecast-adapter/evidence/t004.json`. Obtained evidence: none.
- [ ] T005 (REQ-005 / SC-005): Implement the reviewed bounded offline CPU worker.
  Dependencies: T002; exact lifecycle/enforcement review. Target files: agent_braid/forecast_worker.py; tests/test_forecast_worker.py.
  Verification: Use owned worker timeout/crash/cancellation controls; do not claim enforced memory isolation on an unsupported backend.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/035-chronos2-forecast-adapter/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/035-chronos2-forecast-adapter/evidence/t005.json`. Obtained evidence: none.
- [ ] T006 (REQ-006 / SC-006): Implement receipt-bound reuse and request isolation.
  Dependencies: T004 T005; SPEC-034/T005. Target files: agent_braid/forecast_cache.py; tests/test_forecast_cache.py.
  Verification: Exercise changed cutoff, masks, artifact and resource revision plus cancellation; retain causal cached/uncached parity and costs.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/035-chronos2-forecast-adapter/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/035-chronos2-forecast-adapter/evidence/t006.json`. Obtained evidence: none.
- [ ] T007 (REQ-001 REQ-003 REQ-004 REQ-005 REQ-006 REQ-007 / SC-001 SC-003 SC-004 SC-005 SC-006 SC-007): Validate the installed optional wheel and adapter controls.
  Dependencies: T004 T005 T006. Target files: tests/test_forecast_chronos_packaging.py; specs/035-chronos2-forecast-adapter/evidence/.
  Verification: Run synthetic/stub refusal and packaging procedures; classify every unavailable real-model/device procedure as pending.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/035-chronos2-forecast-adapter/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/035-chronos2-forecast-adapter/evidence/t007.json`. Obtained evidence: none.
- [ ] T008 (REQ-002 REQ-007 / SC-002 SC-007): Run approved real Chronos-2 CPU conformance and cost capture.
  Dependencies: T007; separate approved provisioning/loading and compute envelope. Target files: private approved local checkpoint; specs/035-chronos2-forecast-adapter/evidence/; assurance.json.
  Verification: Measure real checkpoint output/cost on owned synthetic signals offline; retain cold/warm/failure results without claiming real-workload utility.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/035-chronos2-forecast-adapter/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/035-chronos2-forecast-adapter/evidence/t008.json`. Obtained evidence: none.
