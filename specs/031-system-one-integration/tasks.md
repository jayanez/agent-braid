# SPEC-031: Tasks

Implementation and research acceptance tasks; every checkbox starts pending.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

- [x] T001 (REQ-001 / SC-001): Review capability-by-capability contracts and rollout order.
  Dependencies: SPEC-028/T001. Target files: capability-map.md, contracts/integration.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Classify every stage as implemented/planned/advisory/unavailable and identify the unchanged verifier. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t001.json; obtained: none.
- [x] T002 (REQ-002 / SC-002): Implement immutable context extraction and version binding.
  Dependencies: T001 SPEC-028/T008. Target files: agent_braid/system_one_context.py, tests/test_system_one_context.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_context -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Reject stale/mismatched operation sets; preserve declaration-observation conflicts. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t002.json; obtained: none.
- [x] T003 (REQ-002 REQ-003 / SC-002 SC-003): Integrate read-only analyzer choice and candidate priority hints.
  Dependencies: T002. Target files: agent_braid/analysis.py, agent_braid/structured_exchange.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Verify same semantic outputs at matched budgets; exact SPEC-019 eligibility cannot be expanded by advice. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t003.json; obtained: none.
- [x] T004 (REQ-001 REQ-006 / SC-001 SC-006): Add effect-review, tool/model shortlist and adequacy advice adapters.
  Dependencies: T002. Target files: agent_braid/system_one_advisors.py, tests/test_system_one_advisors.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_advisors -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Unsupported domains abstain; model argument judgment never replaces deterministic validation. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t004.json; obtained: none.
- [x] T005 (REQ-002 REQ-004 / SC-002 SC-004): Add constrained scheduler hints with authorization negative controls.
  Dependencies: T003. Target files: agent_braid/runtime_scheduler.py, tests/test_system_one_runtime_boundary.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_runtime_boundary -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Inject high-confidence forged grants, altered plans and unknown footprints; verify no execution escalation. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t005.json; obtained: none.
- [x] T006 (REQ-004 REQ-005 / SC-004 SC-005): Expose separate bounded read-only MCP advice tools.
  Dependencies: T004 T005. Target files: agent_braid/mcp_runtime.py, tests/test_system_one_mcp.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_mcp -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Preserve pinned host protocol, cancellation and tool permissions; no extra execution capability. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t006.json; obtained: none.
- [x] T007 (REQ-006 / SC-006): Add fallback-chain and decision-stage telemetry.
  Dependencies: T006. Target files: agent_braid/system_one_trace.py, tests/test_system_one_trace.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_trace -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record cost and disagreement per stage without exporting private prompt content. Planned evidence: candidate-bound report under specs/031-system-one-integration/evidence/t007.json; obtained: none.
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
human/empirical/model acceptance is pending. Stable PR profile is still pending.
