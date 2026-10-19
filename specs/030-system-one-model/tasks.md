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


## Documentary reconciliation of research and proposed delivery — 2026-10-20

These additive canonical identities retain the existing study/DDP aliases. Checked entries mean only their stated bounded historical lot; original research, human, model and product gates remain open. The evidence register is a documentary source snapshot, not new implementation or independent reproduction. See docs/system-one/README.md and task-map.json. No task launches agents or authorizes a study.

- [ ] T009 (REQ-001 REQ-002 REQ-004 REQ-006 / SC-001 SC-002 SC-004 SC-006): Record pinned Laya source reuse, licenses, model-source candidates and additive text-profile migration contract.
  Preserve the source task identity and pending broader acceptance; partial source software/research evidence is in docs/system-one/evidence-register.json and source-documents.json. The local additive source REQ-007/008 text is a proposal, not silently installed into the historical assurance contract. Do not rebuild implemented runtime/scorers or infer missing human/clean-candidate approval. Scope and exact original text: docs/system-one/task-map.json.

- [ ] T010 (REQ-001 REQ-002 REQ-004 REQ-006 / SC-001 SC-002 SC-004 SC-006): Implement local artifact install/verify/remove, digest pins and optional packaging with required upstream notices.
  Preserve the source task identity and pending broader acceptance; partial source software/research evidence is in docs/system-one/evidence-register.json and source-documents.json. The local additive source REQ-007/008 text is a proposal, not silently installed into the historical assurance contract. Do not rebuild implemented runtime/scorers or infer missing human/clean-candidate approval. Scope and exact original text: docs/system-one/task-map.json.

- [ ] T011 (REQ-001 REQ-002 REQ-004 REQ-006 / SC-001 SC-002 SC-004 SC-006): Implement encoder and pointer scorers, full-input rendering, killable diagnostic worker and bounded refusal controls using tiny random offline fixtures.
  Preserve the source task identity and pending broader acceptance; partial source software/research evidence is in docs/system-one/evidence-register.json and source-documents.json. The local additive source REQ-007/008 text is a proposal, not silently installed into the historical assurance contract. Do not rebuild implemented runtime/scorers or infer missing human/clean-candidate approval. Scope and exact original text: docs/system-one/task-map.json.

- [ ] T012 (REQ-001 REQ-002 REQ-004 REQ-006 / SC-001 SC-002 SC-004 SC-006): Implement supervised/export and analytic evaluation preparation; capture tests, installed-wheel parity and pending research/acceptance gates.
  Preserve the source task identity and pending broader acceptance; partial source software/research evidence is in docs/system-one/evidence-register.json and source-documents.json. The local additive source REQ-007/008 text is a proposal, not silently installed into the historical assurance contract. Do not rebuild implemented runtime/scorers or infer missing human/clean-candidate approval. Scope and exact original text: docs/system-one/task-map.json.

- [ ] T013 (REQ-001 REQ-002 REQ-004 REQ-006 / SC-001 SC-002 SC-004 SC-006): Execute the separately preregistered common-data, frozen-backbone comparison of marker0, Laya-derived
  Preserve the source task identity and pending broader acceptance; partial source software/research evidence is in docs/system-one/evidence-register.json and source-documents.json. The local additive source REQ-007/008 text is a proposal, not silently installed into the historical assurance contract. Do not rebuild implemented runtime/scorers or infer missing human/clean-candidate approval. Scope and exact original text: docs/system-one/task-map.json.

- [ ] T014 (REQ-001 REQ-002 REQ-004 REQ-006 / SC-001 SC-002 SC-004 SC-006): Integrate the opt-in choice-only semantic artifact v2 with complete token accounting, safe export/load,
  Preserve the source task identity and pending broader acceptance; partial source software/research evidence is in docs/system-one/evidence-register.json and source-documents.json. The local additive source REQ-007/008 text is a proposal, not silently installed into the historical assurance contract. Do not rebuild implemented runtime/scorers or infer missing human/clean-candidate approval. Scope and exact original text: docs/system-one/task-map.json.

- [ ] T015 (REQ-001 REQ-002 REQ-004 REQ-006 / SC-001 SC-002 SC-004 SC-006): Implement and independently review the opt-in resident diagnostic API with one owned worker, full source-byte
  Preserve the source task identity and pending broader acceptance; partial source software/research evidence is in docs/system-one/evidence-register.json and source-documents.json. The local additive source REQ-007/008 text is a proposal, not silently installed into the historical assurance contract. Do not rebuild implemented runtime/scorers or infer missing human/clean-candidate approval. Scope and exact original text: docs/system-one/task-map.json.

- [ ] T016 (REQ-001 REQ-004 / SC-001 SC-004): Register learned interpretation and selection follow-up only (alias DDP-T09; proposed, not started).
  Dependencies: Separate owner authorization; SPEC-029/T008; SPEC-030 rights/budget gates. Owner: unassigned / blocked.
  Targets: specs/030-system-one-model/verified-plan-learned-proposal.md. Verification planned: Document/contract review only; no runtime command required before implementation.
  Criterion and negatives: docs/system-one/task-map.json alias DDP-T09; no obtained implementation evidence. Preserve no-authority and separate decision/prepare-budget boundaries.
