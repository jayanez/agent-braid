# SPEC-036: Tasks

All implementation, collection, experiment and approval checkboxes remain pending. Paths outside this spec are prospective targets. Dependency independence is not authorization for concurrent agents. Every receipt must bind actual command, candidate/input hashes, environment, all attempted outcomes and limits.

- [ ] T001 (REQ-001 REQ-007 / SC-001 SC-007): Review and freeze the prospective experiment registration.
  Dependencies: SPEC-034/T007; SPEC-035/T001; exact source/compute review. Target files: specs/036-forecast-parallelism-experiment/evaluation-protocol.md; registration-candidate.json.
  Verification: Freeze numerical values, splits, roster and primary groups before holdout; record a reviewed launch decision or infeasibility.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t001.json`. Obtained evidence: none.
- [ ] T002 (REQ-002 REQ-005 / SC-002 SC-005): Implement inexpensive baselines and complete accounting controls.
  Dependencies: T001 protocol review; SPEC-034/T004. Target files: agent_braid/forecast_baselines.py; tests/test_forecast_baselines.py; phase accounting reuse.
  Verification: Implement persistence/EWMA/development-only operation regression; reconcile cost intervals and undefined scaled-error denominators.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t002.json`. Obtained evidence: none.
- [ ] T003 (REQ-002 REQ-003 / SC-002 SC-003): Implement immutable rolling-origin forecast evaluation.
  Dependencies: T002; SPEC-035/T007. Target files: agent_braid/forecast_evaluation.py; tests/test_forecast_evaluation.py.
  Verification: Use purged episode folds and exact cutoff receipts; aggregate by target/horizon/resource without leaking future values or test groups.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t003.json`. Obtained evidence: none.
- [ ] T004 (REQ-004 / SC-004): Bind the frozen admissible action mapper to each decision.
  Dependencies: T002; SPEC-037/T003. Target files: agent_braid/forecast_experiment.py; tests/test_forecast_experiment.py.
  Verification: Record the complete candidate set and fallback; treat observed future policy timings as labels only, never as decision inputs.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t004.json`. Obtained evidence: none.
- [ ] T005 (REQ-005 / SC-005): Implement the owned paired policy measurement harness.
  Dependencies: T003 T004; existing runtime measurement contract review. Target files: agent_braid/forecast_experiment.py; tests/test_forecast_experiment_costs.py.
  Verification: Use separate operator grants and fresh owned run directories per arm; rotate registered treatment order and capture full deployment costs.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t005.json`. Obtained evidence: none.
- [ ] T006 (REQ-003 REQ-004 REQ-006 / SC-003 SC-004 SC-006): Run leakage, authority, drift and recovery negative controls.
  Dependencies: T005. Target files: tests/test_forecast_experiment_controls.py; specs/036-forecast-parallelism-experiment/evidence/.
  Verification: Refuse high-scored unsafe/unknown resources; preserve all injected failures and existing verification/recovery semantics.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t006.json`. Obtained evidence: none.
- [ ] T007 (REQ-001 REQ-002 REQ-003 REQ-005 REQ-007 / SC-001 SC-002 SC-003 SC-005 SC-007): Execute the approved frozen real-workload holdout comparison.
  Dependencies: T006; SPEC-034/T008; SPEC-035/T008; launch/source/budget and per-run operator authority. Target files: private holdout receipts; specs/036-forecast-parallelism-experiment/evidence/.
  Verification: Run every registered arm/window within its budget; never widen caps, replace failures, inspect holdout to tune or claim an unexecuted placement.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t007.json`. Obtained evidence: none.
- [ ] T008 (REQ-006 REQ-007 REQ-008 / SC-006 SC-007 SC-008): Produce the complete uncertainty and utility decision packet.
  Dependencies: T007 or a recorded pre-launch infeasibility exit after T001. Target files: specs/036-forecast-parallelism-experiment/result-report.md; assurance.json.
  Verification: Report all groups, refusals, failures, missing observations and break-even costs; record supported/negative/inconclusive/infeasible outcome with actual evidence.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t008.json`. Obtained evidence: none.
- [ ] T009 (REQ-008 / SC-008): Obtain the bounded experiment interpretation and adoption decision.
  Dependencies: T008. Target files: specs/036-forecast-parallelism-experiment/utility-decision.json.
  Verification: A separate human/founder decision binds the exact candidate/population; a negative protocol may finish, but forecasting promotion needs positive accepted utility.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/036-forecast-parallelism-experiment/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/036-forecast-parallelism-experiment/evidence/t009.json`. Obtained evidence: none.
