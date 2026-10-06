# SPEC-029: Tasks

Implementation and research acceptance tasks; every checkbox starts pending.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

- [ ] T001 (REQ-001 / SC-001): Review source permissions, sampling frame and prospective yield.
  Dependencies: SPEC-028/T001. Target files: research/system_one/source-register.json, source-audit.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record permission decisions, eligibility/exclusion counts and zero-yield outcomes before fitting. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t001.json; obtained: none.
- [ ] T002 (REQ-002 / SC-002): Freeze label rubric, two-reviewer adjudication and missing-label policy.
  Dependencies: T001. Target files: research/system_one/rubric.md, preregistration.json.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Seal policy-blind labels including disputed and unresolved cases; no teacher label is truth. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t002.json; obtained: none.
- [ ] T003 (REQ-002 REQ-005 / SC-002 SC-005): Implement group split and near-duplicate contamination audit.
  Dependencies: T002. Target files: research/system_one/corpus.py, tests/test_system_one_corpus.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_corpus -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Test session/repository/workflow grouping, duplicates, embargo and held-out leakage. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t003.json; obtained: none.
- [ ] T004 (REQ-005 / SC-005): Build deterministic adversarial conformance and sensitivity suites.
  Dependencies: T002. Target files: examples/system_one/adversarial.jsonl, tests/test_system_one_sensitivity.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_sensitivity -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Cover English/Spanish negation and code-mix, label ordering, injected instructions and option collapse. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t004.json; obtained: none.
- [ ] T005 (REQ-003 REQ-006 / SC-003 SC-006): Freeze candidate roster, resource budgets and paired evaluation plan.
  Dependencies: T003 T004. Target files: research/system_one/preregistration.json, evaluation-protocol.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record hardware matrix, latency/memory envelopes, seeds and stop rules before fitting. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t005.json; obtained: none.
- [ ] T006 (REQ-004 / SC-004): Implement metrics and calibration/threshold split enforcement.
  Dependencies: T005. Target files: research/system_one/metrics.py, tests/test_system_one_metrics.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_metrics -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Compare analytic fixtures; reject non-finite metrics and test-label threshold tuning. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t006.json; obtained: none.
- [ ] T007 (REQ-003 REQ-006 / SC-003 SC-006): Implement common baseline runners and complete cost accounting.
  Dependencies: T005 T006. Target files: research/system_one/evaluate.py, tests/test_system_one_evaluation.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_evaluation -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Preserve refusals, fallback/verifier costs, cold starts and all attempted requests. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t007.json; obtained: none.
- [ ] T008 (REQ-001 REQ-002 REQ-004 / SC-001 SC-002 SC-004): Review pre-fit feasibility and seal untouched test manifest.
  Dependencies: T007. Target files: research/system_one/manifests/, prefit-review.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Check class/group coverage and calibration feasibility; founder data/budget decision is pending. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t008.json; obtained: none.
- [ ] T009 (REQ-003 REQ-004 REQ-005 REQ-006 / SC-003 SC-004 SC-005 SC-006): Execute registered comparison or document infeasibility and null results.
  Dependencies: T008. Target files: research/system_one/results/, specs/029-system-one-evaluation/assurance.json.
  Branch requirements: The comparison branch additionally requires SPEC-030/T006. A recorded pre-fit NO-GO at T008 permits the infeasibility-report branch without training; blocked SPEC-030 tasks remain pending.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: For comparison, report paired group bootstrap and all seeds without selecting favorable runs or silently changing scope. For infeasibility, bind the T008 NO-GO, actual source/yield counts and missing permissions or budget; leave unexecuted model metrics unavailable and training tasks pending. Completing this report does not approve training, architecture selection or promotion. Planned evidence: candidate-bound report under specs/029-system-one-evaluation/evidence/t009.json; obtained: none.

Final candidate verification: `.venv-speckit/bin/python scripts/validate_change.py
--base develop --profile pr`. Tests/procedures and feature evidence do not substitute
for human review, scientific interpretation, explicit source rights or promotion.
