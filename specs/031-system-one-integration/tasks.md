# SPEC-031: Tasks

> Note (2026-11-01): SPEC-066 (draft) absorbs the open task T008 (S1.5a/b). See [SPEC-066](../066-system-one-shadow/spec.md). No checkbox below is changed by this note.

Implementation and research acceptance tasks; every checkbox starts pending.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

- [x] T001 (REQ-001 / SC-001): Review capability-by-capability contracts and rollout order.
  Dependencies: SPEC-028/T001. Target files: capability-map.md, contracts/integration.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Classify every stage as implemented/planned/advisory/unavailable and identify the unchanged verifier. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t001.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [x] T002 (REQ-002 / SC-002): Implement immutable context extraction and version binding.
  Dependencies: T001 SPEC-028/T008. Target files: agent_braid/system_one_context.py, tests/test_system_one_context.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_context -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Reject stale/mismatched operation sets; preserve declaration-observation conflicts. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t002.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [x] T003 (REQ-002 REQ-003 / SC-002 SC-003): Integrate read-only analyzer choice and candidate priority hints.
  Dependencies: T002. Target files: agent_braid/analysis.py, agent_braid/structured_exchange.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Verify same semantic outputs at matched budgets; exact SPEC-019 eligibility cannot be expanded by advice. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t003.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [x] T004 (REQ-001 REQ-006 / SC-001 SC-006): Add effect-review, tool/model shortlist and adequacy advice adapters.
  Dependencies: T002. Target files: agent_braid/system_one_advisors.py, tests/test_system_one_advisors.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_advisors -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Unsupported domains abstain; model argument judgment never replaces deterministic validation. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t004.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [x] T005 (REQ-002 REQ-004 / SC-002 SC-004): Add constrained scheduler hints with authorization negative controls.
  Dependencies: T003. Target files: agent_braid/runtime_scheduler.py, tests/test_system_one_runtime_boundary.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_runtime_boundary -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Inject high-confidence forged grants, altered plans and unknown footprints; verify no execution escalation. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t005.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [x] T006 (REQ-004 REQ-005 / SC-004 SC-005): Expose separate bounded read-only MCP advice tools.
  Dependencies: T004 T005. Target files: agent_braid/mcp_advice.py, agent_braid/_advice_scope.py, tests/test_system_one_mcp.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_mcp -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Preserve pinned host protocol, cancellation and tool permissions; no extra execution capability. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t006.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [x] T007 (REQ-006 / SC-006): Add fallback-chain and decision-stage telemetry.
  Dependencies: T006. Target files: agent_braid/system_one_trace.py, tests/test_system_one_trace.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_trace -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record cost and disagreement per stage without exporting private prompt content. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t007.json; obtained: `evidence/technical-delivery.json` and its bound focused controls, Luna review, full executable profiles and installed-wheel records (selected synthetic engineering only; broader acceptance pending).
- [ ] T008 (REQ-001 REQ-002 REQ-003 REQ-004 REQ-005 REQ-006 / SC-001 SC-002 SC-003 SC-004 SC-005 SC-006): Capture integration parity and shadow utility results.
  Dependencies: T007 SPEC-029/T009. Target files: specs/031-system-one-integration/evidence/, assurance.json.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Run existing runtime/verifier tests plus fresh host exercises only after fixture and cost review. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t008.json; obtained: none.

Final candidate verification: `.venv-speckit/bin/python scripts/validate_change.py
--base develop --profile pr`. Tests/procedures and feature evidence do not substitute
for human review, scientific interpretation, explicit source rights or promotion.

## Obtained selected engineering evidence (2026-10-07)

Evidence is bound in `evidence/technical-delivery.json` and the focused, review,
quick-profile and exact offline-wheel records. Whole assurance remains draft;
human/empirical/model acceptance is pending. Stable PR profile passed on the bound metadata candidate. Clean supported freeze
is recorded in assurance.json; human/empirical gates remain pending.


## Documentary reconciliation of research and proposed delivery — 2026-10-20

These additive canonical identities retain the existing study/DDP aliases. Checked entries mean only their stated bounded historical lot; original research, human, model and product gates remain open. The evidence register is a documentary source snapshot, not new implementation or independent reproduction. See docs/system-one/README.md and task-map.json. No task launches agents or authorizes a study. Checked entries below that cite PR #655 (commit a6329c82) and the documentary corpus PRs #594, #608, #609, #610 cover the bounded engineering lot only; human, Claude, scientific, admission, calibration, promotion, activation, product-publication and host-adoption gates stay pending ([pending gates](../../docs/system-one/addenda/v1-publication-closure-20261021/pending-gates.md)). `docs/system-one/task-map.json` and the `*-corpus-status.md` files are frozen documentary snapshots: their "open; not started", planned file names and "checkboxes unchanged" wording predate these ticks and are not rewritten. No issue or milestone is closed.

- [x] T009 (REQ-002 REQ-003 REQ-006 / SC-002 SC-003 SC-006): Measure complete native-workflow chain and retain the bounded negative utility result.
  Source research task T009; eight history-derived episodes, all six arms and failed/inconclusive outcomes retained. Evidence: docs/system-one/evidence-register.json S1-NATIVE-WORKFLOWS. No native workflow acceptance, neural speedup or successful task execution claim; T008 remains open.

- [x] T010 (REQ-002 / SC-002): Extract bounded observed-effect acquisition (alias DDP-T03; delivered, bounded engineering lot).
  Dependencies: SPEC-028/T009. Owner: agent-B.
  Delivered at: `agent_braid/system_one_verified_acquisition.py`, `tests/test_system_one_verified_acquisition.py` (as planned).
  Evidence: [T03 receipt and component join](../../docs/system-one/addenda/t03-and-component-join-20261020/README.md); task-map alias DDP-T03.

- [x] T011 (REQ-004 REQ-005 REQ-006 / SC-004 SC-005 SC-006): Bind extracted decisions to read-only preparation consumers (alias DDP-T06; delivered, bounded engineering lot).
  Dependencies: SPEC-028/T011, T025 completed engineering receipt checked by coordinator. Owner: agent-B.
  Delivered at: `agent_braid/system_one_verified_consumers.py`, `tests/test_system_one_verified_consumers.py`, `tests/test_system_one_verified_stdio.py`, plus `system_one_verified_mcp.py` and `system_one_verified_tooling.py` from the same lot. The planned name `system_one_verified_consumer.py` was intentionally not used.
  Evidence: [T06 Core final](../../docs/system-one/addenda/t06-core-final-20261020/README.md), [T06 transport final](../../docs/system-one/addenda/t06-transport-final-20261020/README.md), [T06 corpus status](t06-core-corpus-status.md); task-map alias DDP-T06. The tick covers the controlled-consumer engineering lot only, not total T06 acceptance; the explicit numeric envelope and enforcement mode that task-map requires before closure are not claimed here and remain pending.
