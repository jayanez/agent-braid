# Repository-derived pilot cases

Status: proposed sampling frame; no native user data or model evaluation collected.
Source baseline: `69e7d374e5aaf13376486664e7368711d9826e6f`.

The [kickoff source registration](source-registration.md) inspects these anchors
at `a6329c828011d1468fed3dfa4e98f5a8531167e2`, recording exact source identities,
rights basis and actual versus proposed yield. It preserves this historical
baseline and supplies no native admission or obtained HAR outcome. C01/C03 share
fixture ancestry; partitioning by family name alone does not prevent leakage.
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

## T001 registration ledger (2026-10-27)

Status: registered inventory for `049/T001`; not a frozen roster. No HAR case was
created, no native source was admitted, and no user-intervention history exists in
this corpus. Identities, rights and the observed/planned yield split are in
[source-registration.md](source-registration.md); the readback head is
`61b5c39cf6a499d7e7249af01df43b4f4f36981a`, with all anchor bytes unchanged from
the pinned hashes.

### Pinned anchors and honest labels

Every entry below is a repository test or document, so every derived case is
`synthetic` (owned, constructed, deterministic). The label `native` is reserved
for future permissioned tasks and is currently unused.

| Family | Anchor (path, symbol) | Pinned SHA-256 of file | Label | What it actually is |
|---|---|---|---|---|
| C01 | `tests/test_m4_alpha_scheduler.py::test_fresh_process_kill_preserves_prefix_and_resume_does_not_rerun_workers` | `03966aac...82f3ba52` | synthetic, real killed fixture process | Fixed-patch runtime control; not native LLM recovery |
| C01 | `tests/test_tooling_sessions.py::test_candidate_drift_after_dispatch_is_retained_as_interrupted` | `17c80f57...894fe33` | synthetic adapter | Synthetic-receipt session double |
| C02 | `tests/test_git_adapter.py::test_overlap_dependency_delete_binary_and_uncertainty_are_conservative` | `f27408f8...78b4c067` | synthetic | Constructed overlap/dependency/uncertainty fixture |
| C02 | `tests/test_m4_alpha_scheduler.py::test_changed_footprints_limits_and_stale_inputs_never_start_workers` | `03966aac...82f3ba52` | synthetic | Pre-dispatch refusal control |
| C03 | `tests/test_m4_alpha_scheduler.py::test_real_overlap_isolated_resources_and_serial_effect_agreement`, `test_dependencies_serialize_waves_and_reversed_order_is_safe`, `test_new_recovery_grant_preserves_worker_journal_without_rerun` | `03966aac...82f3ba52` | synthetic | Fixed-patch scheduler controls |
| C04 | `specs/028-system-one-core/decision-delivery/handoffs/DDP-T08.md`, `handoffs/coordinator.md` | `fe7268ef...437b46a6f` (S04), `827b0dda...974479bbd` (S05) | documents; derived task would be synthetic | Describe a delivery need, not measured productivity loss |

Full 64-hex hashes and Git blob IDs are in `source-registration.md`.

### Lineage groups (leakage unit)

| Group | Members | Basis | Partition rule |
|---|---|---|---|
| L1 | S01 anchors (C01, C02, C03) via S06 `GitRuntimeTests.setUp` | S01 `setUpClass` reuses the S06 `a.txt`/`b.txt` base and patches | One unit; never split across discovery and holdout |
| L2 | S02 anchor (C01) | Own `examples/tooling` inventory/prompts copy; separate construction | Candidate separate unit |
| L3 | S03 anchor (C02) | Builds an `a.txt`/`b.txt` base by its own `setUp` with equivalent content to S06 | Relation to L1 unresolved; stays unassigned until resolved, then merges into L1 or stands alone |
| L4 | S04, S05 (C04) | Same decision-delivery feature handoffs | One unit; candidate held-out family only if a derived task is constructed and qualifies |

Maximum observed disjoint lineages today: 4 (3 if L3 merges into L1). Case
definitions derived from one group count as one independent unit for inference.

### Expected yield

Observed and planned counts are tabulated in
[source-registration.md](source-registration.md) ("Observed versus planned
yield"). Constructing more variants of L1 increases case count, not independent
units. Native yield is unknown and produces a feasibility result, never a
substitute from synthetic outcomes.

### Exclusions registered at this step

- Credentials, private histories, unrelated repositories, hidden grader material.
- N01–N04 as case sources (source-registration negative controls only).
- Any claim of historical user intervention frequency, native agent behavior or
  representative task distribution.
