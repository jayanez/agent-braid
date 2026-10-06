# SPEC-033: Tasks

Implementation and research acceptance tasks; every checkbox starts pending.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

- [ ] T001 (REQ-002 REQ-006 / SC-002 SC-006): Review capability-specific promotion and rollback criteria.
  Dependencies: SPEC-029/T008 SPEC-031/T001. Target files: promotion-protocol.md, contracts/promotion.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Freeze risk/quality/cost envelopes and responsible reviewers before observing candidate rankings. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t001.json; obtained: none.
- [ ] T002 (REQ-001 / SC-001): Implement shadow-only trace capture and retention controls.
  Dependencies: T001 SPEC-031/T007. Target files: agent_braid/system_one_trace.py, tests/test_system_one_shadow.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_shadow -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Prove identical legacy outputs under shadow, bounded storage and privacy-preserving metadata. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t002.json; obtained: none.
- [ ] T003 (REQ-002 REQ-004 / SC-002 SC-004): Implement immutable artifact/capability promotion registry.
  Dependencies: T002. Target files: agent_braid/system_one_registry.py, tests/test_system_one_registry.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_registry -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Bind exact candidate and review scope; test altered calibration, policy and optional backend. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t003.json; obtained: none.
- [ ] T004 (REQ-003 / SC-003): Implement domain drift checks and label-aware monitoring.
  Dependencies: T003. Target files: agent_braid/system_one_monitor.py, tests/test_system_one_drift.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_drift -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Unknown/unlabeled drift stays unknown; affected domains deterministically defer. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t004.json; obtained: none.
- [ ] T005 (REQ-004 REQ-005 / SC-004 SC-005): Implement atomic rollback and bounded fallback chains.
  Dependencies: T003 T004. Target files: agent_braid/system_one_policy.py, tests/test_system_one_rollback.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_rollback -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Inject outages, OOM, stale manifests and deadline exhaustion; verify no paid/provider call by default. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t005.json; obtained: none.
- [ ] T006 (REQ-001 REQ-002 REQ-006 / SC-001 SC-002 SC-006): Run paired shadow pilot with complete chain costs.
  Dependencies: T005 SPEC-029/T009 SPEC-031/T008. Target files: research/system_one/shadow-results/, shadow-protocol.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record actual permissions, label coverage, total costs and conflicts; no generic throughput claim. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t006.json; obtained: none.
- [ ] T007 (REQ-002 REQ-006 / SC-002 SC-006): Build exact-candidate closure packet with fresh reproduction.
  Dependencies: T006. Target files: specs/033-system-one-promotion/closure.md, assurance.json.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Separate software passing, utility/no-gain, host/hardware coverage and pending independent review. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t007.json; obtained: none.
- [ ] T008 (REQ-002 REQ-006 / SC-002 SC-006): Record founder per-capability go/no-go and reconcile tracking.
  Dependencies: T007. Target files: specs/033-system-one-promotion/founder-review.json, docs/development/github-tracking.json.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Only an actual decision changes adoption/tracking; do not auto-close M3.5 or M4. Planned evidence: candidate-bound report under specs/033-system-one-promotion/evidence/t008.json; obtained: none.

Final candidate verification: `.venv-speckit/bin/python scripts/validate_change.py
--base develop --profile pr`. Tests/procedures and feature evidence do not substitute
for human review, scientific interpretation, explicit source rights or promotion.
