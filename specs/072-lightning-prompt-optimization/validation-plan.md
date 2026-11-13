# SPEC-072: Validation plan

Status (2026-11-13, converged at T012): every procedure has obtained evidence
in `evidence/procedure_NNN.json`, bound in `assurance.json`. procedure_001 binds
the owner review and protocol freeze, procedure_008 the owner-approved held-out
run, whose outcome is negative (H1 not supported); the other procedures are
deterministic tests on fake hosts or synthetic rewards. The exploratory E1/E2
descriptive table (protocol analysis step 7) has not been produced. Deterministic
procedures run in CI and locally with targeted unit test modules. Development
and held-out runs use the SPEC-071 runner on the subscription route only.
Passing deterministic procedures does not establish H1.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record and `evidence/protocol-freeze.json` | protocol hash recorded before the first held-out rollout | held-out command with an edited protocol refused |
| procedure_002 | SC-002 | `tests/test_lightning_resources.py` | canonical round-trip; sha256 matches text | text/hash mismatch refused; unknown key refused |
| procedure_003 | SC-003 | Baseline on fake hosts | summary equals SPEC-071 fake summary | modified seed changes the summary |
| procedure_004 | SC-004 | APO tests with a fake optimizer host | beam sizes and rounds follow configuration; template hashes recorded | optimizer call outside the runner refused |
| procedure_005 | SC-005 | GEPA tests with synthetic reward vectors | Pareto front correct; child accepted only if minibatch improves | dominated candidate kept on the front detected |
| procedure_006 | SC-006 | contamination tests | clean input passes; check runs before every call; optimizer call sandboxed | held-out text, id or canary in input refused; optimizer reading `held-out.json`, scoring source or `.git` refused |
| procedure_007 | SC-007 | stopping tests | each stop reason recorded; APO stops at 3 rounds | run continuing past a cap detected |
| procedure_008 | SC-008 | held-out evidence and analysis report | per host and arm: D4 verdict, Wilson intervals, paired comparison; H1 by the rule (A0 misses and A2 GEPA meets D4 in every required host; `not assessable` where A0 meets D4) | outcome claimed from a non-preregistered measure; canary hit in held-out not invalidating |
| procedure_009 | SC-009 | boundary tests | skill file bytes unchanged; no promotion, execute or MCP path | write to the skill path detected |
| procedure_011 | SC-011 | SPEC-049 pair loader test over synthetic summaries and the committed T010 pair | `Registration` and `EvaluationRecord` validate against `REGISTRATION_FORMAT` and `REPORT_FORMAT`; A = A0, C = A2 | arm C set to A1 refused; altered report breaks `registrationSha256` |
| procedure_010 | SC-010 | replay test | re-scoring stored parsed attempts reproduces selections | altered attempt-result record changes a selection |

Repository validation for every change: `quick` after an increment; the CI
`validate` aggregate on the PR head is the `pr`-profile evidence.
