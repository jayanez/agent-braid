# SPEC-072: Validation plan

Status (2026-11-08, draft): no procedure has obtained evidence. Deterministic
procedures run in CI and locally with targeted unit test modules. Development
and held-out runs use the SPEC-071 runner on the subscription route only.
Passing deterministic procedures does not establish H1.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record and `evidence/protocol-freeze.json` | protocol hash recorded before the first held-out rollout | held-out command with an edited protocol refused |
| procedure_002 | SC-002 | `tests/test_lightning_resources.py` (planned) | canonical round-trip; sha256 matches text | text/hash mismatch refused; unknown key refused |
| procedure_003 | SC-003 | Baseline on fake hosts | summary equals SPEC-071 fake summary | modified seed changes the summary |
| procedure_004 | SC-004 | APO tests with a fake optimizer host | beam sizes and rounds follow configuration; template hashes recorded | optimizer call outside the runner refused |
| procedure_005 | SC-005 | GEPA tests with synthetic reward vectors | Pareto front correct; child accepted only if minibatch improves | dominated candidate kept on the front detected |
| procedure_006 | SC-006 | contamination tests | clean input passes; check runs before every call | held-out text, id or canary in input refused |
| procedure_007 | SC-007 | stopping tests | each stop reason recorded; APO stops at 3 rounds | run continuing past a cap detected |
| procedure_008 | SC-008 | held-out evidence and analysis report | per host and arm: D4 verdict, Wilson intervals, paired comparison, H1 outcome by the rule | outcome claimed from a non-preregistered measure; canary hit in held-out not invalidating |
| procedure_009 | SC-009 | boundary tests | skill file bytes unchanged; no promotion, execute or MCP path | write to the skill path detected |
| procedure_010 | SC-010 | replay test | re-scoring stored transcripts reproduces selections | altered rollout record changes a selection |

Repository validation for every change: `quick` after an increment; the CI
`validate` aggregate on the PR head is the `pr`-profile evidence.
