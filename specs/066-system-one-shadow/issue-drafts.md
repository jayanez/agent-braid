> Unpublished local draft payloads derived from `tasks.md` by the same record shape as the other specs' drafts (`assurance.json` does not exist yet, so its link will resolve after T005). No remote issue, label, milestone, description or Project change was created, audited or applied by this file. Source links target `develop` after merge. Regenerate after any task change.

# Unpublished issue drafts

Milestone: S1.5 — System One shadow activation (created only by the reviewed apply after merge). One spec parent plus 39 task issues; labels `spec` and `task`. Only the parent is marked Project review pending. Owner decisions and owner-run checks: T001 (review, accepted 2026-11-01), T030 (real-use session, SC-006), T105 (label adjudication), T403 (go/no-go). S1.5a implementation: T010-T022. Blocked outline tasks: T101-T403, not startable until T032.

## SPEC-066

Proposed state: open. Parent: none. Milestone: S1.5 — System One shadow activation. Labels: spec. Project review: pending (draft flag).

Title: [SPEC-066] SPEC-066: System One shadow activation and reference-grade decisions

<!-- agent-braid-spec-id: SPEC-066 -->

Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)

Requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008.

Issue state is a bounded tracking record, not a scientific or founder approval.

## SPEC-066/T001

Proposed state: closed. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T001] Owner review of the specification, plan, episode contract and open decisions OD-1 to OD-8, including t...

<!-- agent-braid-task-id: SPEC-066/T001 -->

## Task

Owner review of the specification, plan, episode contract and open decisions OD-1 to OD-8, including the specification notes recorded in `research.md`. Dependencies: T005. Files: `spec.md`, `plan.md`, `contracts/`. Evidence: review record in this directory that also records the decisions taken on OD-1 to OD-8 and the SC-006 session definition. Evidence (2026-11-01): `owner-review-20261101.md`.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: all REQ
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T002

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T002] Add the S1.5 track to ROADMAP, STATUS, the milestone index, docs/system-one/README.md and RESUMPTION,...

<!-- agent-braid-task-id: SPEC-066/T002 -->

## Task

Add the S1.5 track to ROADMAP, STATUS, the milestone index, `docs/system-one/README.md` and `RESUMPTION`, the GitHub tracking source (`specs` entry, milestone, `project_review_pending`) and `GITHUB_TRACKING.md`. Dependencies: none. Files: `ROADMAP.md`, `docs/STATUS.md`, `docs/development/SPEC_MILESTONE_INDEX.md`, `docs/system-one/README.md`, `docs/development/github-tracking.json`, `docs/development/GITHUB_TRACKING.md`. Verification: `python3 scripts/sync_github_tracking.py source`. Evidence: merged change and source output.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T003

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T003] Support a task-level milestone override in the tracking source so the absorbed SPEC-029, SPEC-031 and...

<!-- agent-braid-task-id: SPEC-066/T003 -->

## Task

Support a task-level milestone override in the tracking source so the absorbed SPEC-029, SPEC-031 and SPEC-033 tasks can move to S1.5 while their parent specs stay in Deferred. Tests first. Dependencies: T002. Files: `scripts/sync_github_tracking.py`, `docs/development/github-tracking.json`, `docs/development/GITHUB_TRACKING.md`, `tests/test_github_tracking.py`. Verification: `python3 -m unittest tests.test_github_tracking -v` and `python3 scripts/sync_github_tracking.py source`. Evidence: merged change.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T004

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T004] After merge to develop, publish S1.5 tracking: audit scoped with --new-record-key for exactly the miss...

<!-- agent-braid-task-id: SPEC-066/T004 -->

## Task

After merge to `develop`, publish S1.5 tracking: `audit` scoped with `--new-record-key` for exactly the missing SPEC-066 records, review, `apply --confirm-repository jayanez/agent-braid --plan-sha256 <digest>`, move the 15 absorbed issues from Deferred, record the milestone number, re-audit to zero operations, set the parent to Review pending in Project 6, and update the Deferred milestone description and the reopen condition. Dependencies: T002, T003 merged. Evidence: audit and apply outputs, milestone number in `github-tracking.json`.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T005

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T005] Freeze the specification candidate with python3 -m scripts.validate_spec_kit freeze specs/066-system-o...

<!-- agent-braid-task-id: SPEC-066/T005 -->

## Task

Freeze the specification candidate with `python3 -m scripts.validate_spec_kit freeze specs/066-system-one-shadow`. Dependencies: T002. Evidence: historical snapshot in `assurance.json`.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T010

Proposed state: closed. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T010] Reason table and episode builder: pure functions that turn a System 2 report plus the operation name a...

<!-- agent-braid-task-id: SPEC-066/T010 -->

## Task

Reason table and episode builder: pure functions that turn a System 2 report plus the operation name and analysis kind into an episode object, with the exact sentence-to-code table, the 64-pair cap, `effectKinds` as `null` (the report carries no kinds) and the `unmapped-reason` skip. Include the drift test that scans the analyzer's reason sentences and fails if one is missing from the table. Tests first. Files: `agent_braid/system_one_shadow.py`, `tests/test_system_one_shadow.py`, `tests/fixtures/system_one_shadow/`. Dependencies: T001 (T001 waived for implementation by the 2026-11-01 owner plan approval; required before T032). Verification: procedure_002.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-003 / SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T011

Proposed state: closed. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T011] Episode validator and privacy test: closed vocabularies, key sets, bounds, canonical bytes, duplicate...

<!-- agent-braid-task-id: SPEC-066/T011 -->

## Task

Episode validator and privacy test: closed vocabularies, key sets, bounds, canonical bytes, duplicate members, and a seeded test with hostile instance IDs, resource names, paths and prompts proving none of them appears in the serialized episode; negative controls inject one extra string, an unknown reason code and a mislabelled field. Files: `agent_braid/system_one_shadow.py`, `tests/test_system_one_shadow.py`. Dependencies: T010. Verification: procedure_002.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-003 / SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T012

Proposed state: closed. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T012] Pinned identity: compiled backend ID and manifest digest, comparison with the installed identity, iden...

<!-- agent-braid-task-id: SPEC-066/T012 -->

## Task

Pinned identity: compiled backend ID and manifest digest, comparison with the installed identity, `identity-mismatch` refusal, and the constant `abstained` / `calibration-absent` answer of the reference backend. A test fails when the installed manifest digest changes without the compiled constant. Files: `agent_braid/system_one_shadow.py`, `tests/test_system_one_shadow.py`. Dependencies: T010. Verification: procedure_008.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-007 / procedure_008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T013

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T013] EpisodeStore: telemetry-equivalent path safety, private files, 4 MiB day cap, 30-date retention on acc...

<!-- agent-braid-task-id: SPEC-066/T013 -->

## Task

`EpisodeStore`: telemetry-equivalent path safety, private files, 4 MiB day cap, 30-date retention on access, non-blocking lock, unknown-file refusal, in-memory refusal counters, and a parity test against the telemetry path checker. Negative controls: symlink at each level, repository ancestor, group-readable file, extra hard link, foreign owner, oversize, busy lock, unknown file, full disk. Files: `agent_braid/system_one_shadow.py`, `tests/test_system_one_shadow_store.py`. Dependencies: T011. Verification: procedure_003. Status 2026-11-01: Partly implemented: store with path safety, cap, retention, lock and refusal counters; the full negative-control matrix and telemetry-parity test are pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-004 / SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T014

Proposed state: closed. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T014] Observer, budget and wiring: ToolingConfig.system_one, ShadowObserver with the 50 ms stage checks and...

<!-- agent-braid-task-id: SPEC-066/T014 -->

## Task

Observer, budget and wiring: `ToolingConfig.system_one`, `ShadowObserver` with the 50 ms stage checks and exception containment, lazy call from `ToolingService.invoke` after the envelope, and the byte-parity test between `off` and `shadow` for every tool with fixed UUID and clock. Negative controls: an observer that raises, a store that refuses, an over-budget clock, an input that mutates if the observer writes to it. Files: `agent_braid/system_one_shadow.py`, `agent_braid/tooling_mcp.py`, `tests/test_system_one_shadow_parity.py`. Dependencies: T012, T013 (T001 waived for implementation by the 2026-11-01 owner plan approval; required before T032). Verification: procedure_001, procedure_003.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-002 / SC-001, SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T015

Proposed state: closed. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T015] Consent: registry systemOne member (decode, plan_setup, digest only when shadow), plugin setup --syste...

<!-- agent-braid-task-id: SPEC-066/T015 -->

## Task

Consent: registry `systemOne` member (decode, `plan_setup`, digest only when `shadow`), `plugin setup --system-one`, router pass-through to `ToolingConfig`, reconnect-required behaviour, and the digest and bytes equality test for absent and `off`. Files: `agent_braid/plugin_registry.py`, `agent_braid/plugin_cli.py`, `agent_braid/plugin_mcp.py`, `tests/test_system_one_shadow_consent.py`, `tests/test_plugin_registry.py`. Dependencies: T014. Verification: procedure_005.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-001 / SC-005
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T016

Proposed state: closed. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T016] plugin-status systemOne block with configured and active mode, store state and retention; no directory...

<!-- agent-braid-task-id: SPEC-066/T016 -->

## Task

`plugin-status` `systemOne` block with configured and active mode, store state and retention; no directory creation, no episode bodies; existing status tests updated. Files: `agent_braid/plugin_mcp.py`, `tests/test_system_one_shadow_consent.py`, `tests/test_plugin_mcp.py`. Dependencies: T015. Verification: procedure_009.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-008 / procedure_009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T017

Proposed state: closed. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T017] system-one report (text and agent-braid-s1-report/v0.1 JSON) and purge with confirmation or --yes, ove...

<!-- agent-braid-task-id: SPEC-066/T017 -->

## Task

`system-one report` (text and `agent-braid-s1-report/v0.1` JSON) and `purge` with confirmation or `--yes`, over the strict validator, with invalid lines counted and no episode body printed. Files: `agent_braid/system_one_shadow.py`, `agent_braid/system_one_cli.py`, `agent_braid/cli.py`, `tests/test_system_one_shadow_store.py`, `tests/test_system_one_cli.py`. Dependencies: T013 (T001 waived for implementation by the 2026-11-01 owner plan approval; required before T032). Verification: procedure_004.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-005 / SC-004
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T018

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T018] --telemetry {off,local} on every system-one subcommand, the observe wrapper in cli.py, the system-one...

<!-- agent-braid-task-id: SPEC-066/T018 -->

## Task

`--telemetry {off,local}` on every `system-one` subcommand, the `observe` wrapper in `cli.py`, the `system-one` CLI operation in `OPERATIONS`, LIMITS and `docs/tooling/TELEMETRY.md` text, and a test that no metric other than the new operation cell appears. Files: `agent_braid/cli.py`, `agent_braid/tooling_telemetry.py`, `docs/tooling/TELEMETRY.md`, `tests/test_tooling_telemetry.py`, `tests/test_system_one_cli.py`. Dependencies: T017. Verification: procedure_007. Status 2026-11-01: Partly implemented: `--telemetry`, `observe` wrapper and the `system-one` CLI operation; `docs/tooling/TELEMETRY.md` and the no-other-metric test are pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-006 / procedure_007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T019

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T019] Boundary and validation-profile checks: off never imports the shadow module (subprocess sys.modules ch...

<!-- agent-braid-task-id: SPEC-066/T019 -->

## Task

Boundary and validation-profile checks: `off` never imports the shadow module (subprocess `sys.modules` check), the shadow module imports no network module and no model library, no new `executionAuthorization: true`, and the planner routes every touched path to the expected rule; update the `system-one-core` boundary text. Files: `scripts/validate_change.py`, `tests/test_validation_profiles.py`, `tests/test_system_one_shadow_boundaries.py`, `docs/development/VALIDATION_PROFILES.md`. Dependencies: T014. Verification: procedure_001, `python3 scripts/validate_change.py --base develop --profile quick`. Status 2026-11-01: Pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-002, REQ-003 / SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T020

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T020] User documentation: docs/tooling/SYSTEM_ONE_SHADOW.md (what is recorded, what is never recorded, how t...

<!-- agent-braid-task-id: SPEC-066/T020 -->

## Task

User documentation: `docs/tooling/SYSTEM_ONE_SHADOW.md` (what is recorded, what is never recorded, how to enable, report, purge, non-claims and limits including the filesystem-stall limit), plus updates to `docs/tooling/PLUGIN_PRIVACY.md` and `docs/tooling/INSTALL.md`. Dependencies: T017, T018. Evidence: merged documents and a docs link check. Status 2026-11-01: Pending; README and the plugin setup skill carry interim text.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: all REQ
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T021

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T021] Overhead measurement: median and p95 of the shadow step for 2, 12 and 32 operations on the owner machi...

<!-- agent-braid-task-id: SPEC-066/T021 -->

## Task

Overhead measurement: median and p95 of the shadow step for 2, 12 and 32 operations on the owner machine, with and without a warm store, reported as a measurement receipt (not a gate) with the 50 ms budget as reference. Dependencies: T014. Evidence: `evidence/overhead-<date>.json`. Status 2026-11-01: Pending.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-002 / SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T022

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T022] Episode v0.2 enrichment: extend the builder, validator and store to agent-braid-s1-episode/v0.2 ([cont...

<!-- agent-braid-task-id: SPEC-066/T022 -->

## Task

Episode v0.2 enrichment: extend the builder, validator and store to `agent-braid-s1-episode/v0.2` ([contract](contracts/episode-v0.2.md)): resource classes (src/test/docs/config/lockfile/generated), path depth, directory overlap, per-side effect kinds read from the validated request, and per-repo salted resource hashes in a separate field; v0.1 episodes stay readable. Tests first, including a seeded privacy test that no raw name or path appears and that the salt never appears in an episode, and a purge test that removes the salt. Files: `agent_braid/system_one_shadow.py`, `tests/test_system_one_shadow.py`, `tests/fixtures/system_one_shadow/`. Dependencies: T011. Verification: procedure_010 (see [validation-plan.md](validation-plan.md)). Status 2026-11-01: Pending; the owner decided v0.2 ships with S1.5a (R11, R12).

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-003 / SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T030

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T030] Enable shadow on the owner machine with plugin setup --system-one shadow --apply, reconnect, work norm...

<!-- agent-braid-task-id: SPEC-066/T030 -->

## Task

Enable `shadow` on the owner machine with `plugin setup --system-one shadow --apply`, reconnect, work normally with Agent Braid, then run `system-one report`. Commit a redacted receipt under the `docs/development/REAL_USE_EVIDENCE.md` rules: sources consulted, window, episode and pair counts, DP-1 opportunity share, plugin and package version, no identifiers. Zero episodes is a valid receipt and is reported as such. Dependencies: T014, T015, T017, T020. Evidence: `evidence/real-use-shadow-<date>.json`.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-002, REQ-003 / SC-006
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T031

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T031] Pre-PR reviews (code review, quality, simplification), validate_change --profile pr on the stable cand...

<!-- agent-braid-task-id: SPEC-066/T031 -->

## Task

Pre-PR reviews (code review, quality, simplification), `validate_change --profile pr` on the stable candidate, `/speckit-converge`. Dependencies: T010–T021.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T032

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T032] Record obtained evidence in assurance.json, freeze, and owner review of the S1.5a closure, with the de...

<!-- agent-braid-task-id: SPEC-066/T032 -->

## Task

Record obtained evidence in `assurance.json`, freeze, and owner review of the S1.5a closure, with the decision whether S1.5b starts. Dependencies: T030, T031.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T101

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T101] Owner consent record that admits the owner's own work (episodes, real runs, and the SPEC-047, SPEC-053...

<!-- agent-braid-task-id: SPEC-066/T101 -->

## Task

Owner consent record that admits the owner's own work (episodes, real runs, and the SPEC-047, SPEC-053 and SPEC-059 real-use sources) as the only permissioned corpus, restricted to plugin-registered workspaces (other repositories only on the owner's express approval), reusing the SPEC-051 validator; third-party sources stay excluded. Carries forward SPEC-029 T001 (#285). Dependencies: T032. Evidence: owner record.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-101
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T102

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T102] Outcome observer that joins DP-1 episodes with a later runtime conflict, merge conflict or verify resu...

<!-- agent-braid-task-id: SPEC-066/T102 -->

## Task

Outcome observer that joins DP-1 episodes with a later runtime conflict, merge conflict or verify result under a random join key; pairs without an outcome stay unlabelled. Dependencies: T101. Files: to be set by the S1.5b plan.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-102
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T103

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T103] Amended label rubric: observed outcomes primary, owner adjudication of a random sample for label noise...

<!-- agent-braid-task-id: SPEC-066/T103 -->

## Task

Amended label rubric: observed outcomes primary, owner adjudication of a random sample for label noise, missing-label policy frozen before any fit. Carries forward SPEC-029 T002 (#286). Dependencies: T101.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-103
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T104

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T104] Build the owned corpus with group split, near-duplicate audit, class and size coverage shown before an...

<!-- agent-braid-task-id: SPEC-066/T104 -->

## Task

Build the owned corpus with group split, near-duplicate audit, class and size coverage shown before any fit, and the pre-fit feasibility review that seals the untouched test manifest. Carries forward SPEC-029 T003 (#287) and T008 (#292). Dependencies: T102, T103.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-101, REQ-102, REQ-103
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T105

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T105] Owner adjudication of the random label sample. Dependencies: T103, T104. Evidence: owner record

<!-- agent-braid-task-id: SPEC-066/T105 -->

## Task

Owner adjudication of the random label sample. Dependencies: T103, T104. Evidence: owner record.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-103
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T106

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T106] Git-history replay labels: pair real branches or commits of the owner's plugin-registered workspaces,...

<!-- agent-braid-task-id: SPEC-066/T106 -->

## Task

Git-history replay labels: pair real branches or commits of the owner's plugin-registered workspaces, obtain the observed conflict with `git merge-tree`, reuse the SPEC-012 replay planner, and emit structural episodes only (same privacy rules as REQ-003). A repository outside the registered workspaces requires the owner's express approval first. Tests first; negative controls: an unregistered repository, a pair without an observable outcome (stays unlabelled), a merge-tree failure. Dependencies: T101, T022. Files: to be set by the S1.5b plan.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-104
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T201

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T201] Tri-state abstention, echoed threshold and per-bucket, risk-scaled thresholds fitted on a split disjoi...

<!-- agent-braid-task-id: SPEC-066/T201 -->

## Task

Tri-state abstention, echoed threshold and per-bucket, risk-scaled thresholds fitted on a split disjoint from evaluation; metrics and split enforcement. Carries forward SPEC-029 T006 (#290). Dependencies: T104.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-201
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T202

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T202] Two named confidence signals, normalized entropy and maximum probability, with stated formulas and no...

<!-- agent-braid-task-id: SPEC-066/T202 -->

## Task

Two named confidence signals, normalized entropy and maximum probability, with stated formulas and no accuracy wording. Dependencies: T201.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-202
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T203

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T203] Drift demotion to off on a different or mixed backend identity until a new calibration is pinned, plus...

<!-- agent-braid-task-id: SPEC-066/T203 -->

## Task

Drift demotion to `off` on a different or mixed backend identity until a new calibration is pinned, plus domain-drift monitoring. Carries forward SPEC-033 T004 (#325). Dependencies: T201.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-203
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T204

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T204] Batched questions over one state, bounded batches, per-question failure isolation, parity with unbatch...

<!-- agent-braid-task-id: SPEC-066/T204 -->

## Task

Batched questions over one state, bounded batches, per-question failure isolation, parity with unbatched evaluation. Dependencies: T201.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-204
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T205

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T205] Option-order invariance by rotation, equivariance tests and the adversarial conformance and sensitivit...

<!-- agent-braid-task-id: SPEC-066/T205 -->

## Task

Option-order invariance by rotation, equivariance tests and the adversarial conformance and sensitivity suites. Carries forward SPEC-029 T004 (#288). Dependencies: T201.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-205
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T206

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T206] Evaluation gate in CI with minimum accuracy, maximum ECE, per-slice metrics and a tolerance against a...

<!-- agent-braid-task-id: SPEC-066/T206 -->

## Task

Evaluation gate in CI with minimum accuracy, maximum ECE, per-slice metrics and a tolerance against a committed baseline. Dependencies: T201, T205.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-206
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T301

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T301] Native model module inside agent_braid, standard library only (dependencies = []; no numpy, no extra,...

<!-- agent-braid-task-id: SPEC-066/T301 -->

## Task

Native model module inside `agent_braid`, standard library only (`dependencies = []`; no numpy, no extra, no download): calibrated logistic regression or boosted trees over the episode v0.2 structural features, behind the existing `Backend` protocol, with deterministic training, own weights and a pinned manifest digest. Tests first. Dependencies: T206.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-301
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T302

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T302] Calibration and abstention: temperature or isotonic scaling and abstention thresholds fitted on a cali...

<!-- agent-braid-task-id: SPEC-066/T302 -->

## Task

Calibration and abstention: temperature or isotonic scaling and abstention thresholds fitted on a calibration split disjoint from training and evaluation; freeze the resource budgets and the paired evaluation plan; implement the common baseline runners (rule backend, SPEC-019 linear model) with complete cost accounting. Carries forward SPEC-029 T005 (#289) and T007 (#291). Dependencies: T301.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-301
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T303

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T303] Ablation with and without the per-repo salted resource hashes, then the registered comparison at a com...

<!-- agent-braid-task-id: SPEC-066/T303 -->

## Task

Ablation with and without the per-repo salted resource hashes, then the registered comparison at a common risk budget (or a documented infeasibility). Keep the hashes only if they measurably improve precision without degrading calibration. Record the H-S1 verdict; a null or negative result is valid. Carries forward SPEC-029 T009 (#293) and SPEC-031 T008 (#311). Dependencies: T302.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-301
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T401

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T401] Immutable promotion registry, shadow trace capture and retention reuse, and atomic rollback to off. Ca...

<!-- agent-braid-task-id: SPEC-066/T401 -->

## Task

Immutable promotion registry, shadow trace capture and retention reuse, and atomic rollback to `off`. Carries forward SPEC-033 T002 (#323) and T003 (#324). Dependencies: T303.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-401
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T402

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T402] Paired shadow pilot with complete chain costs on the owner's work. Carries forward SPEC-033 T006 (#327...

<!-- agent-braid-task-id: SPEC-066/T402 -->

## Task

Paired shadow pilot with complete chain costs on the owner's work. Carries forward SPEC-033 T006 (#327). Dependencies: T401.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-401
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-066/T403

Proposed state: open. Parent: SPEC-066. Milestone: S1.5 — System One shadow activation. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-066 T403] Owner go/no-go per decision point and tracking reconciliation; advise only on a recorded go. Carries f...

<!-- agent-braid-task-id: SPEC-066/T403 -->

## Task

Owner go/no-go per decision point and tracking reconciliation; `advise` only on a recorded go. Carries forward SPEC-033 T008 (#329). Dependencies: T402.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/066-system-one-shadow/assurance.json)
- Trace: REQ-401
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## Existing deferred issues to move to S1.5

Read-only check on 2026-11-01 with `gh issue view N --json number,title,state,milestone`: all 15 are open in milestone Deferred. Only the milestone changes; titles, bodies, parents and acceptance criteria stay. Moving an issue does not close, accept or authorize anything. It needs the task-level override of SPEC-066/T003, then the reviewed apply of T004.

| Issue | Task | Carried forward by | Current milestone | Target milestone |
|---|---|---|---|---|
| #285 | SPEC-029/T001 | SPEC-066/T101 | Deferred | S1.5 — System One shadow activation |
| #286 | SPEC-029/T002 | SPEC-066/T103 | Deferred | S1.5 — System One shadow activation |
| #287 | SPEC-029/T003 | SPEC-066/T104 | Deferred | S1.5 — System One shadow activation |
| #288 | SPEC-029/T004 | SPEC-066/T205 | Deferred | S1.5 — System One shadow activation |
| #289 | SPEC-029/T005 | SPEC-066/T302 | Deferred | S1.5 — System One shadow activation |
| #290 | SPEC-029/T006 | SPEC-066/T201 | Deferred | S1.5 — System One shadow activation |
| #291 | SPEC-029/T007 | SPEC-066/T302 | Deferred | S1.5 — System One shadow activation |
| #292 | SPEC-029/T008 | SPEC-066/T104 | Deferred | S1.5 — System One shadow activation |
| #293 | SPEC-029/T009 | SPEC-066/T303 | Deferred | S1.5 — System One shadow activation |
| #311 | SPEC-031/T008 | SPEC-066/T303 | Deferred | S1.5 — System One shadow activation |
| #323 | SPEC-033/T002 | SPEC-066/T401 | Deferred | S1.5 — System One shadow activation |
| #324 | SPEC-033/T003 | SPEC-066/T401 | Deferred | S1.5 — System One shadow activation |
| #325 | SPEC-033/T004 | SPEC-066/T203 | Deferred | S1.5 — System One shadow activation |
| #327 | SPEC-033/T006 | SPEC-066/T402 | Deferred | S1.5 — System One shadow activation |
| #329 | SPEC-033/T008 | SPEC-066/T403 | Deferred | S1.5 — System One shadow activation |

Correction to the requested list: the brief named #322, #323, #324, #326 and #328 for SPEC-033 T002, T003, T004, T006 and T008. Those issues are T001, T002, T003, T005 and T007. The matching issues are #323, #324, #325, #327 and #329, used above. #322 (T001, promotion criteria review), #326 (T005, rollback implementation) and #328 (T007, closure packet) stay in Deferred because the founder decision of 2026-11-01 lists only SPEC-033 T002, T003, T004, T006 and T008 as absorbed; the owner can add them at T001.

Stay in Deferred: the parents SPEC-028 to SPEC-033, SPEC-031 T001-T007, SPEC-030 and SPEC-032 tasks, SPEC-033 T001, T005 and T007, and every other open S1 issue.

