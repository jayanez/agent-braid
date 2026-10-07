# SPEC-034: Tasks

All implementation, collection, experiment and approval checkboxes remain pending. Paths outside this spec are prospective targets. Dependency independence is not authorization for concurrent agents. Every receipt must bind actual command, candidate/input hashes, environment, all attempted outcomes and limits.

- [ ] T001 (REQ-001 REQ-005 / SC-001 SC-005): Review source, privacy, telemetry and local resource boundaries.
  Dependencies: none. Target files: source-register.md; resource-catalogue.md; adr-proposal.md.
  Verification: Record exact source owners, metadata allowlist, target population and technical review; no collection approval is inferred from this planning packet.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/034-workload-forecast-data/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/034-workload-forecast-data/evidence/t001.json`. Obtained evidence: none.
- [ ] T002 (REQ-002 / SC-002): Implement bounded telemetry records and synthetic negative fixtures.
  Dependencies: T001 technical boundary review. Target files: agent_braid/forecast_data.py; tests/test_forecast_data.py.
  Verification: Exercise units, booleans-as-numbers, null reasons, duplicate receipts and phase reconciliation without reading user workloads.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/034-workload-forecast-data/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/034-workload-forecast-data/evidence/t002.json`. Obtained evidence: none.
- [ ] T003 (REQ-001 REQ-002 / SC-001 SC-002): Add permissioned runtime metadata capture hooks.
  Dependencies: T002; separate source-window/operator approval. Target files: agent_braid/forecast_telemetry.py; tests/test_forecast_telemetry.py.
  Verification: Capture only registered counters around an existing admitted runtime; preserve source immutability and complete window/exclusion receipts.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/034-workload-forecast-data/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/034-workload-forecast-data/evidence/t003.json`. Obtained evidence: none.
- [ ] T004 (REQ-003 REQ-004 / SC-003 SC-004): Implement cutoff-aware series compilation and split purging.
  Dependencies: T002. Target files: agent_braid/forecast_windows.py; tests/test_forecast_windows.py.
  Verification: Reject late-data leakage, overlapping episode folds, unknown cadence and implicit target filling; freeze normalization from development data only.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/034-workload-forecast-data/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/034-workload-forecast-data/evidence/t004.json`. Obtained evidence: none.
- [ ] T005 (REQ-005 / SC-005): Implement reviewed local resource eligibility receipts.
  Dependencies: T001 T002. Target files: agent_braid/forecast_resources.py; tests/test_forecast_resources.py.
  Verification: Reject unknown/stale/over-budget resource IDs; describe actual admitted local slots without claiming distributed placement support.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/034-workload-forecast-data/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/034-workload-forecast-data/evidence/t005.json`. Obtained evidence: none.
- [ ] T006 (REQ-001 REQ-003 REQ-004 / SC-001 SC-003 SC-004): Freeze and collect the approved prospective source window.
  Dependencies: T003 T004 T005; source rights and numerical capture budget reviewed. Target files: specs/034-workload-forecast-data/source-register.md; private capture receipts.
  Verification: Freeze source/candidate hashes, temporal cutoffs, partitions, duration and storage limits before capture; retain all failures and exclusions.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/034-workload-forecast-data/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/034-workload-forecast-data/evidence/t006.json`. Obtained evidence: none.
- [ ] T007 (REQ-004 REQ-006 / SC-004 SC-006): Audit yield and record the experiment data-readiness decision.
  Dependencies: T006. Target files: specs/034-workload-forecast-data/readiness.md; private window inventory.
  Verification: Report independent groups and full missingness; inspect action/outcome variation in the development pilot only and keep later outcome values sealed; absent usable data is infeasible, not implicit permission to widen the workload domain.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/034-workload-forecast-data/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/034-workload-forecast-data/evidence/t007.json`. Obtained evidence: none.
- [ ] T008 (REQ-001 REQ-002 REQ-003 REQ-004 REQ-005 REQ-006 / SC-001 SC-002 SC-003 SC-004 SC-005 SC-006): Capture data-contract validation and bounded human review packet.
  Dependencies: T007. Target files: specs/034-workload-forecast-data/evidence/; assurance.json.
  Verification: Bind exact procedures, raw receipts and limits to the candidate; protocol completion does not accept forecasting utility.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/034-workload-forecast-data/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/034-workload-forecast-data/evidence/t008.json`. Obtained evidence: none.
