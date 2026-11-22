# SPEC-081: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the exact
candidate commit, input hashes, command, exit, outcome and limits. Passing checks do
not prove safety or utility and are not approval. Owner-run observations are
evidence, never implied by a passing validation profile.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | dated owner review record (T001), Codex review triage (T002) | OD-1 to OD-7 decided or deferred; authorized tasks named; every Codex finding triaged | review treated as approval of an unbuilt candidate; finding dropped without a reason |
| procedure_002 | SC-002 | capture script tests with a fake binary, then the owner run (T003, T004) | every row observed or `unobserved` with version, command and limits; raw output outside the repository | dry run sends a prompt; a secret, path or assistant text appears in the committed summary |
| procedure_003 | SC-003 | diff of T004 rows against spec claims (T004) | each contradiction amends the spec before T006; missing Pi core MCP selects OD-3 | design work starts on an unobserved or contradicted claim |
| procedure_004 | SC-004 | plugin build test and install in a disposable Pi profile (T005, T006) | exact packaged skills with canonical text; other hosts' files byte-identical | a skill missing or duplicated; byte drift in Codex, Claude or OpenCode files accepted |
| procedure_005 | SC-005 | stdio differential test against Codex and Claude results (T007) | equal core report values; unknown IDs, arbitrary roots and ungranted execution refuse | an implicit workspace or a host approval accepted as a grant |
| procedure_006 | SC-006 | installer profile tests with foreign entries (T008) | only receipt-owned entries change; modified owned entry refuses with a stable code; harness registry refuses native Pi sessions | a foreign entry edited; Pi reported as qualified |
| procedure_007 | SC-007 | doctor fixtures under a write monitor, one mutation per finding kind (T009) | each finding reported with its source path; no file changes | a removed check still passes; any write observed |
| procedure_008 | SC-008 | inspection test of packaged skills, setup text and docs (T010) | no grant issued; no sandbox claimed; the no-permission-layer limit present | packaged text that implies isolation or authority |
| procedure_009 | SC-009 | native observation runbook and release record (T011, T012) | rows observed, contradicted or `unobserved`; no contradiction; release cites the owner decision | release with a contradiction or without the owner decision |
