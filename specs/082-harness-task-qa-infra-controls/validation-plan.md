# SPEC-082: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the exact
candidate commit, input hashes, command, exit, outcome and limits. Passing checks do
not prove task validity, harness utility or safety, and are not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001); Codex review triage (T002) | OD-1 to OD-7 decided or deferred in a dated record; every Codex finding triaged | review treated as approval of unimplemented code; findings dropped without reason |
| procedure_002 | SC-002 | schema and validator tests (T003, T004, T008) | complete records validate; each missing field, unknown key or wrong hash refuses with code and pointer | a guard removed and its test still passes |
| procedure_003 | SC-003 | inventory replay from the frozen rule (T005) | every inspected PR listed with status and reason; rule hash recorded before the first task record | a PR silently skipped; rule edited after a task exists |
| procedure_004 | SC-004 | partition validator tests on fixtures and the real manifest (T004, T006) | lineage-crossing, L1 split, unresolved L3 assigned and post-outcome reassignment all refuse; resolved L3 accepted; components recomputed from edges match | a crossing lineage accepted |
| procedure_005 | SC-005 | private-byte scan over the public tree, Git history and a sample optimizer context (T004, T007) | no plain identity hash, task id or long private line found; private tasks only as salted commitments and receipts; use count equals recorded evaluations | a planted private line or plain hash not detected |
| procedure_006 | SC-006 | oracle 3/3 and no-op check per task (T009) | oracle passes 3/3, no-op fails; others set `rejected` | a flaky oracle marked `qa-passed` |
| procedure_007 | SC-007 | deterministic exploit probes (T010) and exploit agent (T011) | every probe and the agent fail; the planted weak verifier is caught | an exploit passes and the task stays `qa-passed` |
| procedure_008 | SC-008 | review record check (T012) | per `qa-passed` task: two blind model reviews with ids and versions, hashes before both critiques, two cross-critiques, owner adjudication of each disagreement | a majority recorded as consensus; a model review labeled human; a critique before both blind reviews |
| procedure_009 | SC-009 | synthetic job summaries with injected infra errors (T014, T015) | infra errors counted apart, outside the agent denominator, shown in bounds; over OD-5 the job is `invalid`; accounting per registered trial; stop precedence as REQ-009 | an infra error counted as 0 or pass |
| procedure_010 | SC-010 | trial-record validator tests (T003, T014) | requested/observed mismatch gives `config-drift`; missing resource fields refuse | a drifted trial scored `pass` or `fail` |
| procedure_011 | SC-011 | run-id register tests (T014) | duplicate run id and a result with a foreign or mismatched nonce refuse; byte-identical independent results accepted | a reused run id accepted |
| procedure_012 | SC-012 | contamination record review (T013) | each task shows canary, source date and cutoff relation; limitation text present | a task or report called contamination-free |
| procedure_013 | SC-013 | freeze record inspection (T016) | hashes, counts per partition, stratum and lineage, QA status and the `private-holdout` count against the 20-task target and `executionAuthorization: false` present | `qa-incomplete` tasks handed to regression use |
