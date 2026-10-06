# SPEC-030: Tasks

Implementation and research acceptance tasks; every checkbox starts pending.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

- [ ] T001 (REQ-001 REQ-004 / SC-001 SC-004): Approve base model and corpus rights plus immutable revision manifests.
  Dependencies: SPEC-029/T008. Target files: research/system_one/model-sources.json, training-protocol.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record base-weight license separately from code/dataset licenses and approved download/training budget. Planned evidence: candidate-bound report under specs/030-system-one-model/evidence/t001.json; obtained: none.
- [ ] T002 (REQ-002 / SC-002): Implement native decoder pointer scorer with tiny offline fixtures.
  Dependencies: T001 SPEC-028/T008. Target files: agent_braid_system_one/decoder.py, tests/test_system_one_decoder.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_decoder -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Verify dynamic masks, unseen option IDs, no generate call and fp32 probability math. Planned evidence: candidate-bound report under specs/030-system-one-model/evidence/t002.json; obtained: none.
- [ ] T003 (REQ-002 REQ-006 / SC-002 SC-006): Implement native encoder scorer and linear model comparator.
  Dependencies: T001 SPEC-028/T008. Target files: agent_braid_system_one/encoder.py, tests/test_system_one_encoder.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_encoder -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Test marker identity, option permutation and frozen-backbone baseline at common budgets. Planned evidence: candidate-bound report under specs/030-system-one-model/evidence/t003.json; obtained: none.
- [ ] T004 (REQ-003 / SC-003): Implement cache fork and uncached-equivalence checks.
  Dependencies: T002. Target files: agent_braid_system_one/cache.py, tests/test_system_one_cache.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_cache -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Test recurrent/attention layouts, batch sizes, cancellation and fp32 tolerance; refuse unknown mutable layouts. Planned evidence: candidate-bound report under specs/030-system-one-model/evidence/t004.json; obtained: none.
- [ ] T005 (REQ-001 REQ-004 / SC-001 SC-004): Implement offline training, export and calibrated artifact verification.
  Dependencies: T002 T003 T004. Target files: research/system_one/train.py, agent_braid_system_one/artifact.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Manifest exact hashes, objectives and splits; no unsafe pickle or trust_remote_code; tampering fails closed. Planned evidence: candidate-bound report under specs/030-system-one-model/evidence/t005.json; obtained: none.
- [ ] T006 (REQ-004 REQ-006 / SC-004 SC-006): Execute preregistered training ablations within approved budget.
  Dependencies: T005 SPEC-029/T008. Target files: research/system_one/runs/, training-protocol.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Retain every seed and stopping reason; reward/distillation are conditional ablations, not assumed improvements. Planned evidence: candidate-bound report under specs/030-system-one-model/evidence/t006.json; obtained: none.
- [ ] T007 (REQ-003 REQ-005 / SC-003 SC-005): Run device, precision, caching and failure parity matrix.
  Dependencies: T006. Target files: research/system_one/parity/, tests/test_system_one_parity.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_parity -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Record threshold crossing and decision changes, peak memory, OOM and unsupported devices. Planned evidence: candidate-bound report under specs/030-system-one-model/evidence/t007.json; obtained: none.
- [ ] T008 (REQ-006 / SC-006): Record architecture go/no-go from common paired evaluation.
  Dependencies: T007 SPEC-029/T009. Target files: specs/030-system-one-model/selection.md, assurance.json.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Bind the exact model/evaluation candidate; permit no-model result and require separate promotion review. Planned evidence: candidate-bound report under specs/030-system-one-model/evidence/t008.json; obtained: none.

Final candidate verification: `.venv-speckit/bin/python scripts/validate_change.py
--base develop --profile pr`. Tests/procedures and feature evidence do not substitute
for human review, scientific interpretation, explicit source rights or promotion.
