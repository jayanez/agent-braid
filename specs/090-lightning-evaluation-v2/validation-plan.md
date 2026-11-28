# SPEC-090 validation plan

Planned tests; none exists yet. Each scenario's `test_file` in `assurance.json` points here until its task (tasks.md) adds the test and records obtained evidence. Simulation tests (SIM) run before any real rollout and spend no quota.

| REQ | SC | Planned test file | Planned test | Planned evidence |
|---|---|---|---|---|
| REQ-001 | SC-001 | `tests/test_lightning_gate_a.py` | `GateATests.test_majority_pass_per_prompt` | Output of T009. |
| REQ-002 | SC-002 | `tests/test_lightning_stats.py` | `StatsTests.test_clopper_pearson_lower` | Output of T002. |
| REQ-002 | SC-003 | `tests/test_lightning_sim.py` | `SimGateATests.test_type_i_and_ii` | Output of T004. |
| REQ-003 | SC-004 | `tests/test_lightning_stats.py` | `StatsTests.test_all_fail_upper` | Output of T002. |
| REQ-003 | SC-005 | `tests/test_lightning_sim.py` | `SimAllFailTests.test_coverage` | Output of T005. |
| REQ-004 | SC-006 | `tests/test_lightning_gate_a.py` | `GateATests.test_held_until_review` | Output of T009. |
| REQ-005 | SC-007 | `tests/test_lightning_gate_a.py` | `GateATests.test_reserve_replacement` | Output of T010. |
| REQ-005 | SC-008 | `tests/test_lightning_gate_a.py` | `GateATests.test_reserve_cap_invalidates` | Output of T010. |
| REQ-006 | SC-009 | `tests/test_lightning_gate_a.py` | `GateATests.test_class_rule` | Output of T009. |
| REQ-007 | SC-010 | `tests/test_spec090_boundaries.py` | `FreezeTests.test_repetitions_fixed` | Output of T016. |
| REQ-008 | SC-011 | `tests/test_lightning_selection.py` | `SelectionTests.test_paired_same_slice` | Output of T006. |
| REQ-008 | SC-012 | `tests/test_lightning_sim.py` | `SimSelectionTests.test_paired_beats_n5` | Output of T006. |
| REQ-009 | SC-013 | `tests/test_lightning_selection.py` | `SelectionTests.test_slice_sizing` | Output of T006. |
| REQ-010 | SC-014 | `tests/test_lightning_selection.py` | `SelectionTests.test_synchronized_rounds` | Output of T006. |
| REQ-011 | SC-015 | `tests/test_lightning_selection.py` | `SelectionTests.test_incumbent_kept` | Output of T006. |
| REQ-012 | SC-016 | `tests/test_lightning_selection.py` | `AuditTests.test_audit_never_selected` | Output of T011. |
| REQ-013 | SC-017 | `tests/test_lightning_drift.py` | `DriftTests.test_host_change_requires_rebaseline` | Output of T012. |
| REQ-013 | SC-018 | `tests/test_lightning_drift.py` | `DriftTests.test_interleaved_blocks` | Output of T012. |
| REQ-014 | SC-019 | `tests/test_lightning_gate_a.py` | `ReportTests.test_metadata_fields` | Output of T008. |
| REQ-015 | SC-020 | `tests/test_lightning_gate_a.py` | `Gate0Tests.test_tripwire_blocks` | Output of T013. |
| REQ-016 | SC-021 | `tests/test_lightning_selection.py` | `ReplayTests.test_replay_identical` | Output of T007. |
| REQ-017 | SC-022 | `tests/test_spec090_boundaries.py` | `FreezeTests.test_simulation_required` | Output of T016. |
| REQ-018 | SC-023 | `tests/test_lightning_runner.py` | `RunnerTests.test_parallel_refused_without_decision` | Output of T015. |
| REQ-019 | SC-024 | `tests/test_lightning_selection.py` | `SelectionTests.test_gepa_apo_use_paired` | Output of T014. |
| REQ-020 | SC-025 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_frozen_paths_untouched` | Output of T016. |
| REQ-021 | SC-026 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_no_adaptive_allocation` | Output of T012. |
| REQ-022 | SC-027 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_subscription_only` | Output of T016. |
| REQ-023 | SC-028 | `tests/test_lightning_gate_a.py` | `ReportTests.test_no_threshold_share` | Output of T009. |
| REQ-024 | SC-029 | `tests/test_spec090_boundaries.py` | `FreezeTests.test_fresh_split` | Output of T016. |
| REQ-025 | SC-030 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_no_promotion` | Output of T017. |
| REQ-026 | SC-031 | `tests/test_lightning_gate_a.py` | `ReportTests.test_no_wilson_verdict` | Output of T009. |
| REQ-027 | SC-032 | `tests/test_lightning_selection.py` | `AuditTests.test_selection_rejects_audit_items` | Output of T011. |
| REQ-028 | SC-033 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_no_retroactive_gate` | Output of T009. |
| REQ-029 | SC-034 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_no_llm_judge` | Output of T016. |
| REQ-030 | SC-035 | `tests/test_lightning_gate_a.py` | `GateATests.test_review_record_redacted` | Output of T009. |
| REQ-031 | SC-036 | `tests/test_lightning_selection.py` | `SelectionTests.test_minimum_slice_rejected` | Output of T006. |

Negative controls: SC-008 (reserve cap invalidates), SC-009 (class rule), SC-015 (incumbent kept below the margin), SC-017 (host change), SC-020 (tripwire blocks), SC-022 (simulation required), SC-023 (parallel refused), SC-036 (minimum slice), SC-025 to SC-030 and SC-032 to SC-035 (boundaries).
