# SPEC-077: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the exact
candidate commit, input hashes, command, exit, outcome and limits. Passing checks do
not prove safety or utility and are not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001) | OD-1 to OD-6 decided or deferred; contract accepted, amended or rejected | review treated as approval of an unimplemented candidate |
| procedure_002 | SC-002, SC-003, SC-005, SC-008 | Codex read-only review with the packet's output schema (T002) | output matches the schema; every finding triaged | findings dropped without a recorded reason |
| procedure_003 | SC-002 to SC-005 | implementation review of `agent_braid/harness_mcp.py` against the contract (T003) | only the four tools; no import of frozen harness files | a write, subprocess or network path reachable from a tool |
| procedure_004 | SC-002 to SC-008 | `tests.test_harness_mcp` (T004) with one mutation control per guard | all tests pass; each mutation makes its test fail | link, `..`, cap, pointer redaction or tool-set guard removed and tests still pass |
| procedure_005 | SC-002, SC-007 | plugin and installed-verifier tests (T005) | counts match the new listing; telemetry per OD-4 | stale tool count accepted |
| procedure_006 | SC-009 | held-out set freeze (T006) | SHA-256 recorded before the first run | set edited after any result is seen |
| procedure_007 | SC-009 | automated driver, 10 prompts × 3 repetitions per host (T007) | target of OD-2 met per host | a forbidden-effect prompt answered with a harness call presented as the effect |
| procedure_008 | SC-010 | publication decision record (T008) | each gate condition cites evidence | publication with T014 missing or D7 closing the harness |
| procedure_009 | SC-010 | docs and capability-field update tests (T009) | `pluginOrMcpSurface` matches the published state | field reports a surface that is not published |
