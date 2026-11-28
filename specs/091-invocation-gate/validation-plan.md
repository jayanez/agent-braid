# SPEC-091 validation plan

Planned tests; none exists yet. Each scenario's `test_file` in `assurance.json` points here until its task (tasks.md) adds the test and records obtained evidence. Simulation tests (SIM) run before any real rollout and spend no quota.

| REQ | SC | Planned test file | Planned test | Planned evidence |
|---|---|---|---|---|
| REQ-001 | SC-001 | `tests/test_lightning_gate_b.py` | `GateBTests.test_two_metrics` | Output of T010. |
| REQ-002 | SC-002 | `tests/test_spec091_items.py` | `LabelTests.test_labels_frozen_before_run` | Output of T002. |
| REQ-003 | SC-003 | `tests/test_spec091_items.py` | `LabelTests.test_near_miss_required` | Output of T002. |
| REQ-004 | SC-004 | `tests/test_spec091_lab.py` | `LabTests.test_competitors_present` | Output of T003. |
| REQ-005 | SC-005 | `tests/test_spec091_levers.py` | `LeverTests.test_one_arm_per_lever` | Output of T004. |
| REQ-005 | SC-006 | `tests/test_spec091_levers.py` | `LeverTests.test_explicit_command_entry` | Output of T005. |
| REQ-006 | SC-007 | `tests/test_spec091_levers.py` | `LeverTests.test_single_difference` | Output of T004. |
| REQ-007 | SC-008 | `tests/test_spec091_levers.py` | `HookTests.test_hook_text_frozen` | Output of T005. |
| REQ-008 | SC-009 | `tests/test_spec091_levers.py` | `HookTests.test_prompt_not_persisted` | Output of T005. |
| REQ-009 | SC-010 | `tests/test_lightning_resources.py` | `TargetTests.test_description_target_isolated` | Output of T006. |
| REQ-010 | SC-011 | `tests/test_lightning_resources.py` | `TargetTests.test_caps_refuse` | Output of T006. |
| REQ-011 | SC-012 | `tests/test_spec091_pilots.py` | `PilotTests.test_factorial_cells` | Output of T009. |
| REQ-012 | SC-013 | `tests/test_spec091_pilots.py` | `PilotTests.test_noise_report_format` | Output of T008. |
| REQ-013 | SC-014 | `tests/test_spec091_pilots.py` | `FactorialTests.test_blocks_and_counts` | Output of T011. |
| REQ-014 | SC-015 | `tests/test_lightning_gate_b.py` | `GateBTests.test_heldout_requires_factorial` | Output of T014. |
| REQ-015 | SC-016 | `tests/test_lightning_gate_b.py` | `GateBTests.test_tripwire` | Output of T014. |
| REQ-016 | SC-017 | `tests/test_lightning_gate_b.py` | `GateBTests.test_contrast_recorded` | Output of T016. |
| REQ-017 | SC-018 | `tests/test_lightning_gate_b.py` | `GateBTests.test_report_fields` | Output of T010. |
| REQ-018 | SC-019 | `tests/test_lightning_sim.py` | `SimGateBTests.test_coverage_and_errors` | Output of T007. |
| REQ-019 | SC-020 | `tests/test_spec091_items.py` | `LabelTests.test_v4_reuse_refused` | Output of T002. |
| REQ-020 | SC-021 | `tests/test_lightning_resources.py` | `TargetTests.test_invocation_only_reward_refused` | Output of T013. |
| REQ-021 | SC-022 | `tests/test_spec091_boundaries.py` | `BoundaryTests.test_subscription_only` | Output of T003. |
| REQ-022 | SC-023 | `tests/test_spec091_lab.py` | `LabTests.test_containment_kept` | Output of T003. |
| REQ-023 | SC-024 | `tests/test_spec091_boundaries.py` | `BoundaryTests.test_frozen_paths_untouched` | Output of T011. |
| REQ-024 | SC-025 | `tests/test_spec091_boundaries.py` | `BoundaryTests.test_adr0038_decision_required` | Output of T004. |
| REQ-025 | SC-026 | `tests/test_spec091_boundaries.py` | `BoundaryTests.test_levers_not_default` | Output of T017. |
| REQ-026 | SC-027 | `tests/test_lightning_gate_b.py` | `GateBTests.test_no_combined_score` | Output of T010. |
| REQ-027 | SC-028 | `tests/test_spec091_items.py` | `LabelTests.test_relabel_is_new_version` | Output of T002. |
| REQ-028 | SC-029 | `tests/test_spec091_items.py` | `LabelTests.test_counts_before_authoring` | Output of T002. |
| REQ-029 | SC-030 | `tests/test_lightning_resources.py` | `TargetTests.test_skill_target_unchanged` | Output of T006. |
| REQ-030 | SC-031 | `tests/test_lightning_gate_b.py` | `GateBTests.test_contrast_non_gating` | Output of T016. |
| REQ-031 | SC-032 | `tests/test_spec091_boundaries.py` | `BoundaryTests.test_no_llm_judge` | Output of T003. |
| REQ-032 | SC-033 | `tests/test_spec091_levers.py` | `LeverTests.test_d12_cap_kept` | Output of T004. |
| REQ-033 | SC-034 | `tests/test_spec091_pilots.py` | `FactorialTests.test_screening_protocol` | Output of T018. |
| REQ-034 | SC-035 | `tests/test_lightning_gate_b.py` | `GateBTests.test_conjunctive_verdict` | Output of T010. |
| REQ-034 | SC-036 | `tests/test_lightning_gate_b.py` | `GateBTests.test_verdict_precedence` | Output of T010. |
| REQ-035 | SC-037 | `tests/test_spec091_pilots.py` | `PilotTests.test_pilot_freeze_required` | Output of T008. |
| REQ-036 | SC-038 | `tests/test_spec091_boundaries.py` | `BoundaryTests.test_shared_stop_rule` | Output of T011. |
| REQ-037 | SC-039 | `tests/test_lightning_gate_b.py` | `GateBTests.test_holm_levers` | Output of T010. |
| REQ-038 | SC-040 | `tests/test_spec091_boundaries.py` | `BoundaryTests.test_same_build_certification` | Output of T023. |
| REQ-039 | SC-041 | `tests/test_lightning_gate_b.py` | `GateBTests.test_listing_absence_is_instrument` | Output of T010. |
| REQ-040 | SC-042 | `tests/test_spec091_items.py` | `LabelTests.test_gate_b_item_without_product` | Output of T002. |
| REQ-041 | SC-043 | `tests/test_lightning_gate_b.py` | `GateBTests.test_selection_rule_and_tie_break` | Output of T019. |
| REQ-042 | SC-044 | `tests/test_spec091_items.py` | `LabelTests.test_gate_b_audit_disjoint` | Output of T022. |

Negative controls: SC-002 (labels frozen), SC-003 (near-miss required), SC-007 (single difference), SC-008 (hook text), SC-009 (prompt not persisted), SC-011 (caps), SC-015 (held-out before factorial), SC-016 (tripwire), SC-020 to SC-026 and SC-028, SC-029, SC-031 to SC-033 (boundaries), SC-035 and SC-036 (verdict), SC-037 (pilot freeze), SC-038 (shared stop rule), SC-040 (same-build certification), SC-041 (listing absence is instrument), SC-042 (gate B item with product name), SC-044 (gate B audit disjoint).
