# SPEC-079 validation plan

Planned tests; none exists yet. Each scenario's `test_file` in `assurance.json` points here until its task (tasks.md) adds the test and records obtained evidence.

| REQ | SC | Planned test file | Planned test | Planned evidence |
|---|---|---|---|---|
| REQ-001 | SC-001 | `tests/test_tooling_mcp_units_redirect.py` | `UnitsRedirectTests.test_disjoint_units_are_refused` | Unit test output, T001. |
| REQ-001 | SC-002 | `tests/test_tooling_mcp_units_redirect.py` | `UnitsRedirectTests.test_overlapping_units_unchanged` | Golden comparison, T001. |
| REQ-001 | SC-003 | `tests/test_tooling_mcp_units_redirect.py` | `UnitsRedirectTests.test_validation_refusal_first` | Unit test output, T001. |
| REQ-002 | SC-004 | `tests/test_tooling_mcp_units_redirect.py` | `UnitsRedirectTests.test_redirect_is_bounded` | Unit test output, T001. |
| REQ-002 | SC-005 | `tests/test_tooling_mcp_units_redirect.py` | `UnitsRedirectTests.test_replay_cannot_fabricate_coverage` | Unit test output, T001. |
| REQ-003 | SC-006 | `tests/test_tooling_mcp_descriptions.py` | `DescriptionTests.test_analyze_work_description` | Frozen-text test, T002. |
| REQ-004 | SC-007 | `tests/test_tooling_mcp_descriptions.py` | `DescriptionTests.test_analyze_description` | Frozen-text test, T002. |
| REQ-005 | SC-008 | `tests/test_release_records.py` | `ReleaseRecordTests` | Release record diff, T003/T010. |
| REQ-006 | SC-009 | `tests/test_spec079_set.py` | `V4SetTests.test_no_leakage` | Builder --check output, T004. |
| REQ-007 | SC-010 | `tests/test_spec079_set.py` | `V4SetTests.test_gate0` | evidence/gate0-v4-report.json, T005. |
| REQ-008 | SC-011 | `tests/test_spec079_boundaries.py` | `FreezeTests.test_freeze_matches` | prompts/FREEZE-v4.json, T007. |
| REQ-009 | SC-012 | `tests/test_spec079_boundaries.py` | `FreezeTests.test_report_fields` | evidence/gate-v4-report.json, T008/T009. |
| REQ-010 | SC-013 | `tests/test_spec079_boundaries.py` | `FreezeTests.test_single_pass` | Converge record, T010. |
| REQ-011 | SC-014 | `tests/test_spec079_boundaries.py` | `BoundaryTests.test_frozen_paths_untouched` | Boundary test output, T007. |
| REQ-012 | SC-015 | `tests/test_spec079_shadow.py` | `ShadowCheckTests.test_reports_s1_to_s4` | Shadow report, T010. |
| REQ-012 | SC-016 | `tests/test_spec079_shadow.py` | `ShadowCheckTests.test_too_few_calls_is_inconclusive` | Unit test output, T010. |

Negative controls: SC-002, SC-003, SC-005, SC-010 (null baselines), SC-016.
