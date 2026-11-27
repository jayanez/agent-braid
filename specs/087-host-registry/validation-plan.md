# SPEC-087: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the
candidate commit, input hashes, command, exit, outcome and limits. Passing checks do
not prove host behavior, qualification or usefulness and are not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001) | each open question decided or deferred; spec approved, amended or rejected | review read as approval of unwritten code |
| procedure_002 | SC-002 | code search plus guard test over the listed sites | every site reads the registry; no literal host collection remains | a site that keeps its own list and still passes |
| procedure_003 | SC-003 | registry unit test | identifiers exactly codex, claude-code, opencode in order | a fourth identifier or a reordering still passes |
| procedure_004 | SC-004 | input tests per surface with claude, claude-code, an unsupported host and an unknown value | both spellings select the same host; unsupported and unknown refuse with the existing codes | alias accepted for a host the surface does not support |
| procedure_005 | SC-005 | recorded fixture commands per surface before and after | output bytes identical | a stored spelling changed and the comparison still passes |
| procedure_006 | SC-006 | recorded membership table versus capability queries | members and order equal the table; missing capability returns no host | a member added or dropped and the test still passes |
| procedure_007 | SC-007 | union and per-capability comparison; add-host mutation | no host or capability differs from the table | a host or capability added without a table change passes |
| procedure_008 | SC-008 | hosts.json SHA-256 and registry consistency test | file unchanged and equal to the registry's plugin-assets spelling | registry spelling altered and the test still passes |
| procedure_009 | SC-009 | key-set test for each feature-owned table | each key set equals its capability query | a key added without the capability passes |
| procedure_010 | SC-010 | guard test over the tree and over a loose-list fixture | only recorded exceptions; the fixture is reported | the fixture list not reported |
| procedure_011 | SC-011 | import under traced file, network and environment access | no access; identical answers on repeat | any traced access or import side effect |
| procedure_012 | SC-012 | git diff over frozen fixtures and evidence; existing verifiers | no change; verifiers still accept | a rewritten stored record |
| procedure_013 | SC-013 | existing harness registry and gate tests, unchanged | pass; gate query is claude-code and codex without opencode | a gate or row changed to make a test pass |
| procedure_014 | SC-014 | inspect registry fields and touched command results | no qualification, observation or authorization field; executionAuthorization false where present | a capability read as an authorization |
| procedure_015 | SC-015 | list viewer vocabulary and registry identifiers | braid and other only in the viewer vocabulary | braid or other registered as a host |
| procedure_016 | SC-016 | list the change set paths | no other spec, Constitution, replica or closed spec changed | an edit to SPEC-080, SPEC-081 or a closed spec |
| procedure_017 | SC-017 | fake host added to a copy of the registry; run guard and key-set tests | exactly the feature-owned tables lacking it reported; no loose list | adding the host needs an edit to another host list |
