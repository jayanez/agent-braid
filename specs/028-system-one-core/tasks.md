# SPEC-028: Tasks

Checked tasks record bounded technical implementation and review; human acceptance remains separate.
IDs are stable inside the spec. Cross-spec dependencies use SPEC-nnn/Tnnn.
No task authorizes parallel agents, paid calls, data collection or live execution.
Paths outside this spec are prospective implementation targets, not existing files.
All evidence records include command, input/candidate hashes, environment and limits.

- [x] T001 (REQ-001 REQ-002 REQ-004 / SC-001 SC-002 SC-004): Review the feature-local architecture decision and freeze v1 limits.
  Dependencies: none. Target files: adr-proposal.md, contracts/decision-api.md.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Review record binds contract, threat boundary and defaults before implementation. Planned evidence: candidate-bound report under specs/028-system-one-core/evidence/t001.json; obtained: none.
- [x] T002 (REQ-001 REQ-002 / SC-001 SC-002): Implement immutable typed request and response validation.
  Dependencies: T001. Target files: agent_braid/system_one.py, tests/test_system_one_core.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_core -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Run malformed-input, finite-number, option-identity and exact-budget boundary tests. Planned evidence: candidate-bound report under specs/028-system-one-core/evidence/t002.json; obtained: none.
- [x] T003 (REQ-001 REQ-005 / SC-001 SC-005): Implement rule backend, backend protocol and offline capability discovery.
  Dependencies: T002. Target files: agent_braid/system_one_backends.py, tests/test_system_one_backends.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_backends -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Verify no Torch/provider imports in base package and unknown is explicit. Planned evidence: candidate-bound report under specs/028-system-one-core/evidence/t003.json; obtained: none.
- [x] T004 (REQ-003 / SC-003): Implement provenance digests and distinct probability fields.
  Dependencies: T002. Target files: agent_braid/system_one.py, tests/test_system_one_core.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_core -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Mutate every identity component and verify binding; test uniform and forced distributions. Planned evidence: candidate-bound report under specs/028-system-one-core/evidence/t004.json; obtained: none.
- [x] T005 (REQ-003 REQ-004 / SC-003 SC-004): Implement abstain, defer and refuse outcomes without authorization.
  Dependencies: T003 T004. Target files: agent_braid/system_one_policy.py, tests/test_system_one_policy.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_policy -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Forged confidence, grants and certificate fields never create execution authority. Planned evidence: candidate-bound report under specs/028-system-one-core/evidence/t005.json; obtained: none.
- [x] T006 (REQ-002 REQ-006 / SC-002 SC-006): Implement bounded admission and request-local backend state.
  Dependencies: T003 T005. Target files: agent_braid/system_one_backends.py, tests/test_system_one_concurrency.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_concurrency -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Use barrier-driven interleaving, overload and cancellation; check no cross-request state. Planned evidence: candidate-bound report under specs/028-system-one-core/evidence/t006.json; obtained: none.
- [x] T007 (REQ-001 REQ-005 / SC-001 SC-005): Add opt-in CLI decision namespace and compatibility checks.
  Dependencies: T005 T006. Target files: agent_braid/cli.py, tests/test_system_one_cli.py.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest tests.test_system_one_cli -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Compare legacy fixtures byte-for-byte; no default behavior change. Planned evidence: candidate-bound report under specs/028-system-one-core/evidence/t007.json; obtained: none.
- [x] T008 (REQ-001 REQ-002 REQ-003 REQ-004 REQ-005 REQ-006 / SC-001 SC-002 SC-003 SC-004 SC-005 SC-006): Capture core boundary evidence and request contract review.
  Dependencies: T007. Target files: specs/028-system-one-core/assurance.json, evidence/.
  Planned command after implementation: `.venv-speckit/bin/python -m unittest discover -s tests -p "test_system_one*.py" -v`; for manual source/budget/review gates, capture an actual reviewer decision rather than substituting a test result.
  Verification: Run feature tests, PR profile and fresh offline install; human acceptance remains separate. Planned evidence: candidate-bound report under specs/028-system-one-core/evidence/t008.json; obtained: none.

Final candidate verification: `.venv-speckit/bin/python scripts/validate_change.py
--base develop --profile pr`. Tests/procedures and feature evidence do not substitute
for human review, scientific interpretation, explicit source rights or promotion.

## Obtained engineering evidence (2026-10-07)

T001–T007 are bound by `evidence/luna-core-cli.json`, the 33-test focused
log and the fresh offline wheel check. These are synthetic software checks.
T008 completed the bounded engineering packet: quick/sensitive and stable PR
profiles each passed 558 tests with four documented skips on `abeca31`; the
supported clean authority/evidence freeze binds `0e17c4d`. Exact offline wheel
installation and Luna contract/core/CLI review are recorded. Human/model/data/
founder acceptance remains separate.
