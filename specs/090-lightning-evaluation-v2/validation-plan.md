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
| REQ-014 | SC-019 | `tests/test_lightning_runner.py` | `RunnerTests.test_metadata_fields` | Output of T008. |
| REQ-015 | SC-020 | `tests/test_lightning_gate_a.py` | `Gate0Tests.test_tripwire_blocks` | Output of T013. |
| REQ-016 | SC-021 | `tests/test_lightning_selection.py` | `ReplayTests.test_replay_identical` | Output of T007. |
| REQ-017 | SC-022 | `tests/test_lightning_runner.py` | `RunnerTests.test_simulation_required` | Output of T008. |
| REQ-018 | SC-023 | `tests/test_lightning_runner.py` | `RunnerTests.test_parallel_refused_without_decision` | Output of T015. |
| REQ-019 | SC-024 | `tests/test_lightning_selection.py` | `SelectionTests.test_gepa_apo_use_paired` | Output of T014. |
| REQ-020 | SC-025 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_frozen_paths_untouched` | Output of T016. |
| REQ-021 | SC-026 | `tests/test_lightning_drift.py` | `DriftTests.test_no_adaptive_allocation` | Output of T012. |
| REQ-022 | SC-027 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_subscription_only` | Output of T016. |
| REQ-023 | SC-028 | `tests/test_lightning_gate_a.py` | `ReportTests.test_no_threshold_share` | Output of T009. |
| REQ-024 | SC-029 | `tests/test_spec090_boundaries.py` | `FreezeTests.test_fresh_split` | Output of T016. |
| REQ-025 | SC-030 | `tests/test_lightning_gate_a.py` | `GateATests.test_no_promotion` | Output of T009. |
| REQ-026 | SC-031 | `tests/test_lightning_gate_a.py` | `ReportTests.test_no_wilson_verdict` | Output of T009. |
| REQ-027 | SC-032 | `tests/test_lightning_selection.py` | `AuditTests.test_selection_rejects_audit_items` | Output of T011. |
| REQ-028 | SC-033 | `tests/test_lightning_gate_a.py` | `GateATests.test_no_retroactive_gate` | Output of T009. |
| REQ-029 | SC-034 | `tests/test_spec090_boundaries.py` | `BoundaryTests.test_no_llm_judge` | Output of T016. |
| REQ-030 | SC-035 | `tests/test_lightning_gate_a.py` | `GateATests.test_review_record_redacted` | Output of T009. |
| REQ-031 | SC-036 | `tests/test_lightning_selection.py` | `SelectionTests.test_minimum_slice_rejected` | Output of T006. |
| REQ-032 | SC-037 | `tests/test_spec090_pilot.py` | `PilotTests.test_gate_a_noise_report` | Output of T020. |
| REQ-033 | SC-038 | `tests/test_lightning_sim.py` | `SimGateATests.test_clustered_scenario` | Output of T004. |
| REQ-034 | SC-039 | `tests/test_lightning_selection.py` | `SelectionTests.test_confirmation_slice_disjoint` | Output of T006. |
| REQ-035 | SC-040 | `tests/test_lightning_selection.py` | `SelectionTests.test_holm_family` | Output of T006. |
| REQ-036 | SC-041 | `tests/test_lightning_selection.py` | `AuditTests.test_audit_once_per_winner` | Output of T011. |
| REQ-037 | SC-042 | `tests/test_lightning_drift.py` | `DriftTests.test_host_mismatch_refuses_before_rollout` | Output of T012. |
| REQ-037 | SC-043 | `tests/test_lightning_drift.py` | `DriftTests.test_blocked_resume_invalidates` | Output of T012. |
| REQ-037 | SC-044 | `tests/test_lightning_drift.py` | `DriftTests.test_resume_fills_missing_slots` | Output of T012. |
| REQ-038 | SC-045 | `tests/test_lightning_gate_a.py` | `GateATests.test_verdict_precedence` | Output of T009. |
| REQ-038 | SC-046 | `tests/test_lightning_gate_a.py` | `GateATests.test_conjunctive_verdict` | Output of T009. |
| REQ-039 | SC-047 | `tests/test_spec090_boundaries.py` | `FreezeTests.test_pilot_freeze_required` | Output of T020. |
| REQ-040 | SC-048 | `tests/test_lightning_drift.py` | `DriftTests.test_aa_threshold_action` | Output of T012. |
| REQ-041 | SC-049 | `tests/test_lightning_selection.py` | `SelectionTests.test_cap_does_not_shrink_slice` | Output of T006. |
| REQ-042 | SC-050 | `tests/test_spec090_boundaries.py` | `FreezeTests.test_seeded_partition` | Output of T016. |
| REQ-043 | SC-051 | `tests/test_spec090_boundaries.py` | `FreezeTests.test_gate_a_item_names_product` | Output of T016. |
| REQ-044 | SC-052 | `tests/test_lightning_gate_a.py` | `Gate0Tests.test_static_gate0` | Output of T023. |
| REQ-045 | SC-053 | `tests/test_lightning_runner.py` | `RunnerTests.test_owner_yes_required` | Output of T008. |
| REQ-003 | SC-054 | `tests/test_spec090_boundaries.py` | `FreezeTests.test_zero_prompt_rule_refused` | Output of T016. |
| REQ-005 | SC-055 | `tests/test_lightning_gate_a.py` | `GateATests.test_reserve_order_same_bytes_host_model` | Output of T010. |
| REQ-005 | SC-056 | `tests/test_lightning_gate_a.py` | `GateATests.test_instrument_safeguard_record_required` | Output of T010. |
| REQ-013 | SC-057 | `tests/test_lightning_drift.py` | `DriftTests.test_pins_required` | Output of T012. |
| REQ-013 | SC-058 | `tests/test_lightning_drift.py` | `DriftTests.test_resize_after_rebaseline` | Output of T012. |
| REQ-037 | SC-059 | `tests/test_lightning_drift.py` | `DriftTests.test_quota_must_cover_all_slots` | Output of T012. |
| REQ-037 | SC-060 | `tests/test_lightning_drift.py` | `DriftTests.test_spent_split_not_rescored` | Output of T012. |
| REQ-038 | SC-061 | `tests/test_lightning_gate_a.py` | `GateATests.test_held_on_unfilled_slot_or_hold_action` | Output of T009. |

Negative controls: SC-007 (instrument counted as 0/3), SC-008 (cap exceeded invalidates), SC-009 (class rule), SC-015 (incumbent kept below the margin), SC-017 (host change), SC-020 (tripwire blocks), SC-022 (simulation required), SC-023 (parallel refused), SC-036 (underpowered slice), SC-039 (confirmation slice disjoint), SC-041 (audit once), SC-042 (host mismatch refused before rollout), SC-043 (blocked resume), SC-045 and SC-046 (verdict), SC-047 (pilot freeze), SC-049 (cap does not shrink), SC-051 (gate A item without product name), SC-052 (null baselines), SC-054 (zero-0/3 rule refused), SC-056 (safeguard record required), SC-057 (pins required), SC-058 (sizing reruns after a re-baseline), SC-059 (quota covers all slots), SC-060 (spent split not rescored), SC-061 (held), SC-025 to SC-030 and SC-032 to SC-035 (boundaries).
