# SPEC-032: Tasks

Implementation and research acceptance tasks; every checkbox starts pending.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

- [ ] T001 (REQ-001 REQ-002 / SC-001 SC-002): Review supported feature subset and CPU/device budget matrix.
  Dependencies: SPEC-030/T008. Target files: product-decisions.md, contracts/product.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record supported languages/tasks and deployment envelopes; defer optional features explicitly. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t001.json; obtained: none.
- [ ] T002 (REQ-001 / SC-001): Implement optional export/quantization with CPU reference parity.
  Dependencies: T001. Target files: agent_braid_system_one/export.py, tests/test_system_one_export.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_export -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Measure probability/decision changes, cold/warm latency and peak RSS; no blanket speed claims. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t002.json; obtained: none.
- [ ] T003 (REQ-002 / SC-002): Implement evidence-bound language/task/model routing.
  Dependencies: T001. Target files: agent_braid/system_one_router.py, tests/test_system_one_router.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_router -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Test Spanish, English, unknown languages, short code and mixed-script input before confidence routing. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t003.json; obtained: none.
- [ ] T004 (REQ-003 / SC-003): Implement bounded schema-to-question compiler.
  Dependencies: SPEC-028/T008 T001. Target files: agent_braid/system_one_schema.py, tests/test_system_one_schema.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_schema -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Cover nested local refs, enums, nullability, cycles, ordering and refusal of free-form generation. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t004.json; obtained: none.
- [ ] T005 (REQ-004 / SC-004): Implement shortlist and tournament with subset provenance.
  Dependencies: T003 SPEC-029/T009. Target files: agent_braid/system_one_catalogue.py, tests/test_system_one_catalogue.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_catalogue -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Compare recall@k and tournament group/order sensitivity; calibrate final chain separately. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t005.json; obtained: none.
- [ ] T006 (REQ-005 / SC-005): Implement token-budget batching and reference-counted model lifecycle.
  Dependencies: T002 T003. Target files: agent_braid_system_one/worker.py, tests/test_system_one_lifecycle.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_lifecycle -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Barrier tests cover unload-during-inference, cancellation, overload and cross-request contamination. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t006.json; obtained: none.
- [ ] T007 (REQ-006 / SC-006): Implement observer hooks and fresh offline wheel install checks.
  Dependencies: T004 T005 T006. Target files: agent_braid/system_one_hooks.py, tests/test_system_one_packaging.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_packaging -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Test sealed-input mutation, blocked hooks and installed extras in a clean environment. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t007.json; obtained: none.
- [ ] T008 (REQ-001 REQ-002 REQ-003 REQ-004 REQ-005 REQ-006 / SC-001 SC-002 SC-003 SC-004 SC-005 SC-006): Capture per-feature evaluation and accept or defer each extension.
  Dependencies: T007. Target files: specs/032-system-one-product/feature-acceptance.md, assurance.json.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Retain negative recall/language/parity findings; no all-or-nothing feature adoption. Planned evidence: candidate-bound report under specs/032-system-one-product/evidence/t008.json; obtained: none.

Final candidate verification: `.venv-speckit/bin/python scripts/validate_change.py
--base develop --profile pr`. Tests/procedures and feature evidence do not substitute
for human review, scientific interpretation, explicit source rights or promotion.
