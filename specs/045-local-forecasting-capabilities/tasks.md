# SPEC-045: Tasks

Original FC.1 task criteria remain unchanged. Independent dependency properties do not authorize concurrent agents. Technical completion is distinct from actual model/source/founder acceptance.

- [x] T001 (REQ-001 REQ-002 REQ-003 REQ-004 / SC-001 SC-002 SC-003 SC-004): Record the integrated synthetic engineering boundary and ownership.
  Dependencies: none. Targets: forecast modules, tests and feature-local evidence.
  Verification: record the owner scope, technical/model boundary review, memory/stdio/deadline contract and module ownership; behavior is verified by later tasks. This does not approve sources or model artifacts.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: historical engineering/model/installed evidence is mapped in `convergence-2026-10-14.md` and the additive `evidence/reconciliation-acceptance.json`; actual-model/cost and tracking obligations retain their own gates.
- [x] T002 (REQ-001 REQ-005 / SC-001 SC-005): Build the reproducible synthetic signal and fixed-patch laboratory.
  Dependencies: T001. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: historical engineering/model/installed evidence is mapped in `convergence-2026-10-14.md` and the additive `evidence/reconciliation-acceptance.json`; actual-model/cost and tracking obligations retain their own gates.
- [x] T003 (REQ-001 REQ-002 REQ-003 REQ-004 / SC-001 SC-002 SC-003 SC-004): Integrate the local forecasting session API and CLI flow.
  Dependencies: T002. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: historical engineering/model/installed evidence is mapped in `convergence-2026-10-14.md` and the additive `evidence/reconciliation-acceptance.json`; actual-model/cost and tracking obligations retain their own gates.
- [x] T004 (REQ-003 REQ-004 / SC-003 SC-004): Expose separate bounded local read-only MCP forecasting tools.
  Dependencies: T003. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: historical engineering/model/installed evidence is mapped in `convergence-2026-10-14.md` and the additive `evidence/reconciliation-acceptance.json`; actual-model/cost and tracking obligations retain their own gates.
- [x] T005 (REQ-005 / SC-005): Store, inspect and export owned immutable numeric receipts.
  Dependencies: T004. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: historical engineering/model/installed evidence is mapped in `convergence-2026-10-14.md` and the additive `evidence/reconciliation-acceptance.json`; actual-model/cost and tracking obligations retain their own gates.
- [x] T006 (REQ-001 REQ-002 REQ-003 REQ-004 REQ-005 / SC-001 SC-002 SC-003 SC-004 SC-005): Validate installed API/CLI/MCP and failure lifecycle parity.
  Dependencies: T005. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: historical engineering/model/installed evidence is mapped in `convergence-2026-10-14.md` and the additive `evidence/reconciliation-acceptance.json`; actual-model/cost and tracking obligations retain their own gates.
- [ ] T007 (REQ-002 REQ-006 / SC-002 SC-006): Capture approved actual Chronos CPU conformance and complete costs.
  Dependencies: T006; exact artifact/provisioning/compute approval. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: after exact artifact approval, `.venv-speckit/bin/python scripts/reproduce_forecast_cpu.py --manifest PRIVATE_MANIFEST --output PRIVATE_OUTPUT`. Capture cold/resident/failure/container limits separately from stub engineering.
  Planned evidence: `evidence/engineering.json`; obtained evidence: historical engineering/model/installed evidence is mapped in `convergence-2026-10-14.md` and the additive `evidence/reconciliation-acceptance.json`; actual-model/cost and tracking obligations retain their own gates. The admitted worker/daemon control is obtained in `evidence/integrated-worker-2026-10-15/index.json`; `obtained-accounting-2026-10-15.md` retains the exact complete-cost gaps, so T007 stays open.
- [x] T008 (REQ-005 REQ-006 / SC-005 SC-006): Publish the technical completion packet and bounded tracking readback.
  Dependencies: T006; retain T007 as a separate actual-model gate. Targets: forecast modules, tests and feature-local evidence.
  Verification: execute the mapped scenarios and negative controls; model/source decisions require actual authority.
  Command: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_forecast*.py" -v`.
  Planned evidence: `evidence/engineering.json`; obtained evidence: historical engineering/model/installed evidence is mapped in `convergence-2026-10-14.md` and the additive `evidence/reconciliation-acceptance.json`; actual-model/cost and tracking obligations retain their own gates. The reviewed technical publication packet is `obtained-accounting-2026-10-15.md` and `evidence/integrated-worker-2026-10-15/index.json`; remote closure requires integration followed by scoped issue and Project readback, independently of T007.

## Obtained evidence supplement (2026-10-14)

The literal criteria and historical assurance remain unchanged. T001–T006 have bounded engineering acceptance against the retained installed evidence and current validation; T007 and T008 remain open.
`convergence-2026-10-14.md` maps T001–T008 to the engineering, independent installed,
actual v3/v5 and cost-companion evidence, with consumer-specific remaining gates.
The technical-cost contract and optional paired-arm observer address REQ-005/006;
the synthetic daemon-loss test supports REQ-002 without claiming a real engine
crash. T007 still requires full deployment costs and its exact real control chain;
T008 still requires governed integration/publication/tracking readback.

## Obtained accounting and technical publication supplement (2026-10-15)

The [obtained packet](obtained-accounting-2026-10-15.md) and `evidence/integrated-worker-2026-10-15/index.json` bind the successful admitted worker/daemon control, nine retained setup allocations, unsuccessful qualification attempts and remaining cost gaps. T007 retains its literal complete-cost criterion and remains open. T008 remains unchecked until reviewed publication and bounded readback are obtained. Apply its remote closure only from the subsequent evidence-backed source update. This does not close T007, parent or milestone, refresh historical assurance, or grant scientific/model/source/ADR/promotion acceptance. Earlier supplements retain their dated historical status.

## Technical publication/readback acceptance (2026-10-15)

PR #521 is integrated at `ff01ce46213854b3dd0116f9a4eb28efb740448b`. The scoped issue audit returned zero operations after the two reviewed text updates; authenticated Project readback observed all nine managed records in the three views. `evidence/technical-publication-readback-2026-10-15.json` binds those obtained facts and their validation. T008 is checked for its completed publication/inventory-readback criterion; the following scoped remote transition and final closed/Done readback remain separate operations. T007, parent #510 and milestone #20 remain open for the unresolved complete-cost gate. No scientific, model-load, source, ADR or promotion authority is inferred.

## Selected-flow measurement preparation (2026-10-15)

The additive implementation in [selected-flow-implementation-2026-10-15.md](selected-flow-implementation-2026-10-15.md) reuses the obtained worker control and paired Git harness, defines the separate finite v2 observation boundary, and prepares fresh model/cache-to-policy collection. It closes no original criterion. T007 remains open for authentic selected-flow capture and literal complete-cost acceptance; T008 stays closed. New execution requires its exact reviewed package and owner admission.

## Owner-adopted T007 cancellation (2026-10-15)

The [disposition](t007-disposition.md) and [owner provenance record](evidence/t007-owner-disposition-2026-10-15.json) adopt the reviewed proposal to cancel T007's unmet complete-cost remainder as partial/infeasible. The exact original T007 line and unchecked checkbox above remain unchanged. The selected-flow measurement is obtained in the linked public receipts; no new model/VM execution accompanies this decision. Registered tracking requests `closed/not_planned`, separately from completion, after reviewed integration and scoped readback. Report seven completed tasks plus one cancelled/partial task; T008 stays completed. Parent #510 and milestone #20 stay open; no FC.1/source/experiment/scientific/ADR/promotion gate is accepted. Dated historical supplements retain their original scopes and status.
