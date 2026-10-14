# SPEC-045: Tasks

Original FC.1 task criteria remain unchanged. Independent dependency properties do not authorize concurrent agents. Technical completion is distinct from actual model/source/founder acceptance.

- [ ] T001 (REQ-001 REQ-002 REQ-003 REQ-004 / SC-001 SC-002 SC-003 SC-004): Record the integrated synthetic engineering boundary and ownership.
  Dependencies: none. Targets: forecast modules, tests and feature-local evidence.
  Verification: record the owner scope, technical/model boundary review, memory/stdio/deadline contract and module ownership; behavior is verified by later tasks. This does not approve sources or model artifacts.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: none.
- [ ] T002 (REQ-001 REQ-005 / SC-001 SC-005): Build the reproducible synthetic signal and fixed-patch laboratory.
  Dependencies: T001. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: none.
- [ ] T003 (REQ-001 REQ-002 REQ-003 REQ-004 / SC-001 SC-002 SC-003 SC-004): Integrate the local forecasting session API and CLI flow.
  Dependencies: T002. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: none.
- [ ] T004 (REQ-003 REQ-004 / SC-003 SC-004): Expose separate bounded local read-only MCP forecasting tools.
  Dependencies: T003. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: none.
- [ ] T005 (REQ-005 / SC-005): Store, inspect and export owned immutable numeric receipts.
  Dependencies: T004. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: none.
- [ ] T006 (REQ-001 REQ-002 REQ-003 REQ-004 REQ-005 / SC-001 SC-002 SC-003 SC-004 SC-005): Validate installed API/CLI/MCP and failure lifecycle parity.
  Dependencies: T005. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: none.
- [ ] T007 (REQ-002 REQ-006 / SC-002 SC-006): Capture approved actual Chronos CPU conformance and complete costs.
  Dependencies: T006; exact artifact/provisioning/compute approval. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: after exact artifact approval, `.venv-speckit/bin/python scripts/reproduce_forecast_cpu.py --manifest PRIVATE_MANIFEST --output PRIVATE_OUTPUT`. Capture cold/resident/failure/container limits separately from stub engineering.
  Planned evidence: `evidence/engineering.json`; obtained evidence: none.
- [ ] T008 (REQ-005 REQ-006 / SC-005 SC-006): Publish the technical completion packet and bounded tracking readback.
  Dependencies: T006; retain T007 as a separate actual-model gate. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: none.

## Obtained evidence supplement (2026-10-14)

The original unchecked criteria and historical assurance remain unchanged.
`convergence-2026-10-14.md` maps T001–T008 to the engineering, independent installed,
actual v3/v5 and cost-companion evidence, with consumer-specific remaining gates.
The technical-cost contract and optional paired-arm observer address REQ-005/006;
the synthetic daemon-loss test supports REQ-002 without claiming a real engine
crash. T007 still requires full deployment costs and its exact real control chain;
T008 still requires governed integration/publication/tracking readback.
