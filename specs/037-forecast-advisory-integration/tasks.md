# SPEC-037: Tasks

All implementation, collection, experiment and approval checkboxes remain pending. Paths outside this spec are prospective targets. Dependency independence is not authorization for concurrent agents. Every receipt must bind actual command, candidate/input hashes, environment, all attempted outcomes and limits.

- [ ] T001 (REQ-001 REQ-002 REQ-003 / SC-001 SC-002 SC-003): Review the separate forecast/advice contract and runtime boundary.
  Dependencies: SPEC-034/T001; SPEC-035/T002 interface review. Target files: specs/037-forecast-advisory-integration/contracts/interface.md; adr-proposal.md.
  Verification: Review exact additive capability, deterministic candidate generation and one-local-profile limit; no model-enabled execution is accepted.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/037-forecast-advisory-integration/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/037-forecast-advisory-integration/evidence/t001.json`. Obtained evidence: none.
- [ ] T002 (REQ-001 / SC-001): Implement default-off read-only forecast library and CLI discovery.
  Dependencies: T001; SPEC-035/T007. Target files: agent_braid/forecast_advice.py; agent_braid/forecast_cli.py; tests/test_forecast_cli.py.
  Verification: Default/help paths load no ML; version errors, absent optional backend and forecast refusal stay precise and side-effect free.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/037-forecast-advisory-integration/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/037-forecast-advisory-integration/evidence/t002.json`. Obtained evidence: none.
- [ ] T003 (REQ-002 REQ-003 / SC-002 SC-003): Implement immutable admissible action mapping and grant controls.
  Dependencies: T001; SPEC-034/T005; SPEC-035/T007. Target files: agent_braid/forecast_policy.py; tests/test_forecast_policy.py.
  Verification: Produce only existing supported preparation choices; refuse stale/forged/over-budget/unknown inputs and never issue operator authority.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/037-forecast-advisory-integration/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/037-forecast-advisory-integration/evidence/t003.json`. Obtained evidence: none.
- [ ] T004 (REQ-004 / SC-004): Implement or explicitly defer the optional typed System 1 bridge.
  Dependencies: T003; independently accepted SPEC-028/031 consumer contract for the selected branch. Target files: agent_braid/forecast_system_one.py; tests/test_forecast_system_one.py.
  Verification: Runtime-only advice has no System 1 dependency; a deferred bridge stays unavailable and no whole-capability support is claimed.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/037-forecast-advisory-integration/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/037-forecast-advisory-integration/evidence/t004.json`. Obtained evidence: none.
- [ ] T005 (REQ-005 / SC-005): Add shadow-mode observations and complete fallback traces.
  Dependencies: T002 T003. Target files: agent_braid/forecast_trace.py; tests/test_forecast_trace.py.
  Verification: Reference actions remain unchanged; capture only actual outcome labels and full advisory overhead under approved source/operator boundaries.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/037-forecast-advisory-integration/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/037-forecast-advisory-integration/evidence/t005.json`. Obtained evidence: none.
- [ ] T006 (REQ-003 REQ-005 REQ-006 / SC-003 SC-005 SC-006): Validate authority, drift, cancellation and rollback boundaries.
  Dependencies: T005. Target files: tests/test_forecast_runtime_boundary.py; specs/037-forecast-advisory-integration/evidence/.
  Verification: Exercise malicious forecasts, altered policies, expired receipts, unavailable backends and in-flight recovery with unchanged verifiers/grants.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/037-forecast-advisory-integration/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/037-forecast-advisory-integration/evidence/t006.json`. Obtained evidence: none.
- [ ] T007 (REQ-005 REQ-006 / SC-005 SC-006): Prepare the exact-capability promotion or defer packet.
  Dependencies: T006; SPEC-036/T009 accepted positive utility for promotion, or explicit no-go/defer. Target files: specs/037-forecast-advisory-integration/promotion-packet.md; assurance.json.
  Verification: Bind utility, installed adapter, resource/population/thresholds, end-to-end costs, drift monitoring and rollback; no-go keeps learned traffic shadow/off.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/037-forecast-advisory-integration/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/037-forecast-advisory-integration/evidence/t007.json`. Obtained evidence: none.
- [ ] T008 (REQ-006 / SC-006): Record founder capability adoption or no-go and milestone interpretation.
  Dependencies: T007. Target files: specs/037-forecast-advisory-integration/capability-decision.json.
  Verification: Accept only the exact eligible capability or document no-go; any execution still needs an independent grant and full M4/M3.5 closure remains outside FC.1.
  Planned commands after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v` plus the requirement-specific procedure in `specs/037-forecast-advisory-integration/validation-plan.md`; source/model/launch/founder decisions require their actual reviewer record.
  Planned evidence: `specs/037-forecast-advisory-integration/evidence/t008.json`. Obtained evidence: none.
