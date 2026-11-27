# SPEC-089: Validation plan (skeleton)

Status: draft skeleton; no procedure has obtained evidence. Procedures for the
measurement itself are added with the design, after the owner decisions. Passing checks
do not measure any host and are not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | list the tasks and search the sections for a validity definition, split, gate, sample size or analysis | no design task precedes T001; no such statement in the skeleton | a design statement written before T001 |
| procedure_002 | SC-002 | compare the later frozen split with the recorded hashes of every earlier held-out and test set | no shared prompt | a prompt shared with a spent set |
| procedure_003 | SC-003 | list the change set paths | no tool, skill, guidance or scorer file | an edit to one of them |
| procedure_004 | SC-004 | trace each reported claim to a recorded host, model, build and set | every claim traced | a claim about an unmeasured cell |
| procedure_005 | SC-005 | produce a report with a host that cannot run | the host is `unobserved` with its reason | the host dropped or filled in |
| procedure_006 | SC-006 | produce a report for a missed gate | outcome recorded as missed; specification complete | a missed gate read as failure of the specification |
| procedure_007 | SC-007 | inspect run records and plan outputs | owner authorization cited; subscription route; `executionAuthorization` false before | a run without a cited authorization |
| procedure_008 | SC-008 | check the dependency records when the first design task is created | SPEC-079 T010 converged and owner decisions recorded | a design task created before them |
