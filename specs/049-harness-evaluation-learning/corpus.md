# Repository-derived pilot cases

Status: proposed sampling frame; no native user data or model evaluation collected.
Source baseline: `69e7d374e5aaf13376486664e7368711d9826e6f`.
The owner requested both continuity and coordination, delegated case selection,
and retained context-loss/recovery and conflict/rework as target situations.

| Family | Repository evidence | Proposed experiment and oracle |
|---|---|---|
| C01 — Interrupted work and fresh context | `tests/test_m4_alpha_scheduler.py::test_fresh_process_kill_preserves_prefix_and_resume_does_not_rerun_workers`; `tests/test_tooling_sessions.py::test_candidate_drift_after_dispatch_is_retained_as_interrupted` | Interrupt an owned multi-step task at registered checkpoints; restart with a bounded handoff, inject source/policy drift or missing evidence, and compare correct completion, repeated work, duplicate effects and corrections. Existing real process-kill fixtures test the fixed-patch domain; they do not establish native LLM session recovery. |
| C02 — Conflict and uncertainty | `tests/test_git_adapter.py::test_overlap_dependency_delete_binary_and_uncertainty_are_conservative`; `tests/test_m4_alpha_scheduler.py::test_changed_footprints_limits_and_stale_inputs_never_start_workers` | Matched overlapping, dependent, stale and unknown-footprint edits. Ground truth is the constructed effect/dependency fixture plus an independent verifier. Measure conflict precision/recall and false safe admissions; conservative abstention has an explicit coverage/efficiency cost. |
| C03 — Useful independent work and combined recovery | `tests/test_m4_alpha_scheduler.py::test_real_overlap_isolated_resources_and_serial_effect_agreement`; `test_dependencies_serialize_waves_and_reversed_order_is_safe`; `test_new_recovery_grant_preserves_worker_journal_without_rerun` | Compare independent versus dependent work from a common source, then interrupt at the integration boundary. Verify private worker effects and output against the serial reference. Measure eligible parallelism recovered, unnecessary serialization and total verification/recovery overhead. Do not infer arbitrary concurrent native safety. |
| C04 — Delivery with unresolved gates | `specs/028-system-one-core/decision-delivery/handoffs/DDP-T08.md`; `handoffs/coordinator.md` | A task assembles a bounded evidence handoff while retaining exact dependency meanings, changed-source context and pending gates. Independent checks verify artifact/source identity and whether unresolved conditions remain visible. Human comprehension/intervention is a separate optional observed endpoint. These files show a real project handoff need, not measured productivity loss. |

Prioritize C01 and C02 as complementary correctness controls, then C03 to test
optimization without rewarding indiscriminate serialization. C04 adds a realistic
long-task packaging case and a held-out family if source yield supports it.
Do not reuse the same fixture in discovery and holdout by merely renaming files.

## Eligibility and source gates

Engineering cohort: owned, synthetic fixtures derived from these controls with
known initial state, deterministic outcomes and permission for derived materials.
Native cohort: future owner-permissioned repository tasks with explicit rights,
privacy/secret inventory, reproducible initial state and an independent outcome
definition. Record all candidate families, exclusions and actual yield before
sampling. A historical test or handoff is not a record of actual user correction
frequency, native agent behavior or representative task distribution.

Missing native yield produces a feasibility result and pending native evaluation;
it never authorizes substituting synthetic outcomes for product acceptance.
