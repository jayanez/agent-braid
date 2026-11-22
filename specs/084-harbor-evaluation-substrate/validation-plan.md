# SPEC-084: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the
candidate commit, input hashes, command, exit, outcome and limits. A passing check
does not prove safety, fidelity or utility and is not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001) | ADR 0045 accepted, amended or rejected; OD-1 to OD-6 decided or deferred | review treated as a go for a job |
| procedure_002 | SC-001 | Codex read-only review, raw output kept (T002) | every finding triaged with a reason | findings dropped without a reason |
| procedure_003 | SC-003 | pin check on a job config (T003) | digests and exact versions present; floating tag refuses | a `latest` tag accepted |
| procedure_004 | SC-002 | credential scan of layers, config, logs, trajectories (T004) | auth works and no credential found | a planted test token in a layer is not detected |
| procedure_005 | SC-004 | quota stop check with stale, missing and over-cap readings (T005) | batch does not start; stop recorded | batch starts on a stale reading |
| procedure_006 | SC-006 | network probes per phase (T006) | off-allowlist and verifier connections denied and logged | a probe connects |
| procedure_007 | SC-002, SC-003, SC-004, SC-006 | feasibility record (T007) | each gate cites its evidence; any fail yields infeasible | P2 started after a failed gate |
| procedure_008 | SC-005, SC-011 | `tests/test_harness_harbor.py` (T008) | configs complete; candidate hash mismatch refuses; `executionAuthorization` false | missing resource field accepted |
| procedure_009 | SC-007, SC-008 | `tests/test_harness_atif.py` on recorded fixtures (T009) | classes kept; hash matches; missing stays missing | missing reward counted as 0 or as pass |
| procedure_010 | SC-005 | job plus rerun from exported config (T010) | identical config hash, digests, resources, model, effort, candidate; new run id | cached result reused |
| procedure_011 | SC-010 | three injected controls (T011) | each ends as an infra error with its reason code | a control counted as agent failure |
| procedure_012 | SC-009 | registration hash before shadow data (T012) | hash recorded before the first shadow trial | rule edited after a result is seen |
| procedure_013 | SC-009 | shadow run and agreement rule (T013) | per-task agreement recorded; disagreement sets a block | block cleared without an explanation record |
| procedure_014 | SC-008, SC-011 | report review (T014) | verdicts cite SPEC-083 rules; no pointer or registry write | Harbor mean quoted as a verdict |
