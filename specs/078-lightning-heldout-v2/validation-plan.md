# SPEC-078: Validation plan

Status (2026-11-20): draft; procedures 001 to 007 and 012 have obtained evidence (T001 to T005; Gate 0 passed; frozen at develop 8ee703db). Deterministic procedures run in CI and locally
with targeted unit test modules. Real runs (procedure_008, procedure_011) use
the SPEC-071 runner on the subscription route only and need the owner's yes on
the stated rollout count. Passing deterministic procedures does not establish
H-A0 or H-G2.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | `tests/test_spec069_guidance.py` `DependencyReadRuleTests` | rule-following HELD-04 answer valid; dependency alone gives `ordered` | old-rule answer invalid |
| procedure_002 | SC-002 | `tests/test_spec078_set.py` | three disjoint splits; every class in every split; deterministic build | v1 prompt copied or normalized-equal refused; a split missing a class refused; shared 8-word window across splits refused; a path absent from the prompt refused; a unit without a fixture-file effect refused |
| procedure_003 | SC-003 | `tests/test_spec078_gate0.py` (references) | every case's reference accepted and valid | a case with a wrong reference blocks Gate 0; complete-coverage variant of a partial case invalid |
| procedure_004 | SC-004 | `tests/test_spec078_gate0.py` (follower) | every follower request accepted and valid | skill edit removing a pinned rule fails the pin test; follower with the old read rule fails on chain cases |
| procedure_005 | SC-005 | `tests/test_spec078_gate0.py` (null baselines) | each null fails on the classes REQ-005 lists; none meets OD-1 on any split | a null baseline that passes a case it should fail is reported |
| procedure_006 | SC-006 | `tests/test_spec078_analysis.py` (review rule) | 0/3 prompt held until classified; `instrument` invalidates the arm and requires a new set version | unclassified 0/3 prompt counted is refused |
| procedure_007 | SC-007 | `tests/test_spec078_freeze.py`, `evidence/protocol-freeze.json` | set and protocol hashes recorded on a `develop` commit before any rollout | edited split, protocol, Gate 0 script or A0 skill refused; missing freeze refused |
| procedure_008 | SC-008 | Gate 1 run record and analysis (`evidence/gate1-a0.json`) | 300 rollouts, per-prompt table, Wilson, clustered SE, OD-1 verdict, secondary figures | analysis unit tests on synthetic results: known Wilson bounds, known sign-test p-values |
| procedure_009 | SC-009 | regression-suite doc and command (if A0 meets) | one command re-runs the suite and reports the OD-1 verdict | fake-host run reproduces the recorded verdict |
| procedure_010 | SC-010 | `tests/test_lightning_edits.py` (if Gate 2) | edits bounded by budget; kept only on strict validation gain; front matter fixed; length cap; diff produced | over-budget edit, front-matter edit and non-improving edit refused |
| procedure_011 | SC-011 | Gate 2 test and v1 runs (if Gate 2) | paired exact test vs A0; v1 no-regression; canary invalidates | canary hit on fake host invalidates the arm |
| procedure_012 | SC-012 | `tests/test_spec078_boundaries.py` | no scorer, set or skill writes; no promotion, execute, recover or grant import; no API key; stdlib only | forbidden import or write detected |
| procedure_013 | SC-013 | `tests/test_spec078_kind_guidance.py` | both sentences in the kind-selection section; units on disjoint writes reports unknown; aim with placeholder digests reports independent-candidate | the sentences removed fail the pin |
| procedure_014 | SC-015 | v3 build and `evidence/gate0-v3-report.json` | fresh split disjoint from v1/v2 and the skill; Gate 0 passes before any rollout | a v2 fact pattern, a shared window or a prompt not following its facts is refused |
| procedure_016 | SC-014 | v3 freeze and `evidence/gate1-v3-a0prime.json` | freeze on a develop commit; 300 rollouts and the OD-1 verdict | an unfrozen or edited v3 run is refused |
