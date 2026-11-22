# SPEC-085: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the
candidate commit, input hashes, command, exit, outcome and limits. Passing checks do
not prove safety or utility and are not approval. Procedures 001 to 009 map one to one
to SC-001 to SC-009; procedures 010 to 012 support review, rehearsal and release.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001) | OD-1 to OD-7 decided or deferred; spec accepted, amended or rejected | review read as approval of unwritten code |
| procedure_002 | SC-002 | label, hash and registration tests against the T003 format (T003, T004) | unknown label, bad hash and unregistered hash refused; journal unchanged | a refused move still appends a record |
| procedure_003 | SC-003 | actor tests plus a code search for callers of the move function (T004, T007) | only the owner actor accepted; no caller in evaluation or auto-promotion code | an agent or automatic-policy actor accepted |
| procedure_004 | SC-004 | chain tests: edit, delete, reorder, race (T003, T004) | `broken-chain` or `concurrent-update` refusals; no state served | a tampered journal replays without refusal |
| procedure_005 | SC-005 | gate tests with fresh, inconclusive, inferior, absent and stale verdicts (T005) | only the fresh non-inferior verdict moves `candidate` | an inconclusive verdict accepted |
| procedure_006 | SC-006 | gate tests for `adopted`: axes approved, pending, rejected; target not at `candidate` (T005) | only the all-approved, at-`candidate` case accepted | one missing axis accepted |
| procedure_007 | SC-007 | rollback tests with valid and revoked prior targets (T006) | valid target recorded as `rollback`; revoked target refused `revoked-evidence` | history shortened by a rollback |
| procedure_008 | SC-008 | CLI view under a write monitor; skill text checked against the SPEC-080 read command list (T008, T010) | no write; three labels and divergence listed; skill shows the view only | the view or skill can write a record or names the move script |
| procedure_009 | SC-009 | move under a filesystem monitor (T007, T009) | only the pointer journal changes; `executionAuthorization` false | a T013 transaction begins or a host file changes |
| procedure_010 | SC-001 | Codex review of the merged candidate (T002) | raw output kept; every finding triaged with a reason | findings dropped without a reason |
| procedure_011 | SC-004, SC-007, SC-009 | synthetic rehearsal: move, rollback, forged record, race (T011) | every expected refusal and record observed | a real label moved during rehearsal |
| procedure_012 | SC-001, SC-008 | release decision record (T012) | release or no-release cites T002, T011 and owner acceptance | docs claim a pointer surface that is not released |
