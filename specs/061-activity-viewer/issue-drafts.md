> Unpublished local draft payloads derived from `tasks.md` and `assurance.json` by the repository's source inventory. No remote issue, label, milestone, description or Project change was created, audited or applied by this file. Source links target `develop` after merge. Regenerate after any task change.

# Unpublished issue drafts

Milestone: VIS.1 — Activity viewer (created only by the reviewed apply after merge). One spec parent plus 37 task issues; labels `spec` and `task`. Only the parent is marked Project review pending. Founder or owner decisions: T001–T003, T005. Owner-run host probes: T030–T033. Optional: T035.

## SPEC-061

Proposed state: open. Parent: none. Milestone: VIS.1 — Activity viewer. Labels: spec. Project review: pending (draft flag).

Title: [SPEC-061] SPEC-061: Read-only local activity and concurrency viewer

<!-- agent-braid-spec-id: SPEC-061 -->

Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)

Requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014, REQ-015.

Issue state is a bounded tracking record, not a scientific or founder approval.

## SPEC-061/T001

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T001] Owner review of the specification, plan, contracts and open decisions OD-3 to OD-6. Dependencies: T008...

<!-- agent-braid-task-id: SPEC-061/T001 -->

## Task

Owner review of the specification, plan, contracts and open decisions OD-3 to OD-6. Dependencies: T008. Files: `spec.md`, `plan.md`, `contracts/`. Evidence: review record in this directory.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: all REQ
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T002

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T002] Decide ADR 0032 (activity viewer companion). Dependencies: none. Files: docs/adr/0032-activity-viewer-...

<!-- agent-braid-task-id: SPEC-061/T002 -->

## Task

Decide ADR 0032 (activity viewer companion). Dependencies: none. Files: `docs/adr/0032-activity-viewer-companion.md`. Evidence: ADR status change merged.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-004, REQ-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T003

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T003] Founder decision on ADR 0033 (vendored Three.js, MIT boundary). Dependencies: none. Files: docs/adr/00...

<!-- agent-braid-task-id: SPEC-061/T003 -->

## Task

Founder decision on ADR 0033 (vendored Three.js, MIT boundary). Dependencies: none. Files: `docs/adr/0033-vendored-threejs-mit-boundary.md`. Evidence: ADR status change merged.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-010, REQ-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T004

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T004] Add the VIS track to ROADMAP, STATUS, the milestone index, the AI tooling program, GitHub tracking sou...

<!-- agent-braid-task-id: SPEC-061/T004 -->

## Task

Add the VIS track to ROADMAP, STATUS, the milestone index, the AI tooling program, GitHub tracking source and validation profile notes. Dependencies: none. Files: `ROADMAP.md`, `docs/STATUS.md`, `docs/development/SPEC_MILESTONE_INDEX.md`, `specs/039-ai-tooling-program/program.md`, `docs/development/github-tracking.json`, `docs/development/GITHUB_TRACKING.md`, `docs/tooling/README.md`. Verification: `python3 scripts/sync_github_tracking.py source`. Evidence: merged change and source output.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-015
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T005

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T005] After merge to develop, publish VIS.1 tracking: audit, review, apply --confirm-repository jayanez/agen...

<!-- agent-braid-task-id: SPEC-061/T005 -->

## Task

After merge to `develop`, publish VIS.1 tracking: `audit`, review, `apply --confirm-repository jayanez/agent-braid --plan-sha256 <digest>`, record the milestone number, re-audit to zero operations, set the parent issue to Review pending in Project 6. Dependencies: T004 merged. Evidence: audit and apply outputs, milestone number in `github-tracking.json`.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-015
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T006

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T006] Record derived tracks VIS.2–VIS.4 with scope, sources, gates and open questions. Dependencies: none. F...

<!-- agent-braid-task-id: SPEC-061/T006 -->

## Task

Record derived tracks VIS.2–VIS.4 with scope, sources, gates and open questions. Dependencies: none. Files: `tracks.md`. Evidence: owner review in T001.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T007

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T007] Review the host-verification runbook. Dependencies: none. Files: host-verification-runbook.md. Evidenc...

<!-- agent-braid-task-id: SPEC-061/T007 -->

## Task

Review the host-verification runbook. Dependencies: none. Files: `host-verification-runbook.md`. Evidence: owner review in T001.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T008

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T008] Freeze the specification candidate with python3 -m scripts.validate_spec_kit freeze specs/061-activity...

<!-- agent-braid-task-id: SPEC-061/T008 -->

## Task

Freeze the specification candidate with `python3 -m scripts.validate_spec_kit freeze specs/061-activity-viewer`. Dependencies: T004, T006, T007. Evidence: historical snapshot in `assurance.json`.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T009

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T009] Keep STATUS, ROADMAP, the milestone index, tracking source and Project 6 current at each VIS.1 closure...

<!-- agent-braid-task-id: SPEC-061/T009 -->

## Task

Keep STATUS, ROADMAP, the milestone index, tracking source and Project 6 current at each VIS.1 closure. Dependencies: T005. Evidence: audit with zero operations after each closure.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-015
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T010

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T010] view_loom.py: constants, limits, strict JSON, validate_event, canonical bytes; schema parity test. Tes...

<!-- agent-braid-task-id: SPEC-061/T010 -->

## Task

`view_loom.py`: constants, limits, strict JSON, `validate_event`, canonical bytes; schema parity test. Tests first. Files: `agent_braid/view_loom.py`, `tests/test_view_loom.py`, `tests/fixtures/view/loom/`. Verification: procedure_001.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-001 / SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T011

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T011] activity-viewer rule in scripts/validate_change.py, test in tests/test_validation_profiles.py, paragra...

<!-- agent-braid-task-id: SPEC-061/T011 -->

## Task

`activity-viewer` rule in `scripts/validate_change.py`, test in `tests/test_validation_profiles.py`, paragraph in `docs/development/VALIDATION_PROFILES.md`. Verification: procedure_013.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-013 / SC-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T012

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T012] Adapters for analysis reports, Git replay plans, scheduler preparations, grants and runtime state. Fil...

<!-- agent-braid-task-id: SPEC-061/T012 -->

## Task

Adapters for analysis reports, Git replay plans, scheduler preparations, grants and runtime state. Files: `agent_braid/view_adapters.py`, `tests/test_view_adapters.py`, `tests/fixtures/view/artifacts/`. Dependencies: T010. Verification: procedure_002.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-002 / SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T013

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T013] Adapters for ownership notices and receipts (JSON only), workflow-gate results and absence cases. Depe...

<!-- agent-braid-task-id: SPEC-061/T013 -->

## Task

Adapters for ownership notices and receipts (JSON only), workflow-gate results and absence cases. Dependencies: T012. Verification: procedure_002, procedure_003.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-002 / SC-002; REQ-003 / SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T014

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T014] Host stream adapters (claude -p stream-json, codex exec --json) and the example replay examples/view/l...

<!-- agent-braid-task-id: SPEC-061/T014 -->

## Task

Host stream adapters (`claude -p` stream-json, `codex exec --json`) and the example replay `examples/view/loom-replay.jsonl` generated from owned fixtures. Dependencies: T012. Verification: procedure_002.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-002 / SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T015

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T015] view_store.py ring, seq, caps, eviction gaps, bounded subscriber queues. Files: agent_braid/view_store...

<!-- agent-braid-task-id: SPEC-061/T015 -->

## Task

`view_store.py` ring, seq, caps, eviction gaps, bounded subscriber queues. Files: `agent_braid/view_store.py`, `tests/test_view_store.py`. Dependencies: T010. Verification: procedure_006.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-006 / SC-006
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T016

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T016] view_serve.py loopback bind, token, Host and Origin checks, headers, body limits, route table. Files:...

<!-- agent-braid-task-id: SPEC-061/T016 -->

## Task

`view_serve.py` loopback bind, token, `Host` and `Origin` checks, headers, body limits, route table. Files: `agent_braid/view_serve.py`, `tests/test_view_serve.py`. Dependencies: T015. Verification: procedure_004.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-004 / SC-004
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T017

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T017] SSE with Last-Event-ID, /snapshot, replay mode, view_tail.py bounded polling, --record/--record-effort...

<!-- agent-braid-task-id: SPEC-061/T017 -->

## Task

SSE with `Last-Event-ID`, `/snapshot`, replay mode, `view_tail.py` bounded polling, `--record`/`--record-effort` writing capped at 50 000 events. Dependencies: T016, T020. Verification: procedure_004, procedure_006, procedure_007.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-004 / SC-004; REQ-006 / SC-006; REQ-007 / SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T018

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T018] view_otlp.py OTLP HTTP/JSON logs and metrics, allowlist, salting, shape-unpinned. Files: agent_braid/v...

<!-- agent-braid-task-id: SPEC-061/T018 -->

## Task

`view_otlp.py` OTLP HTTP/JSON logs and metrics, allowlist, salting, `shape-unpinned`. Files: `agent_braid/view_otlp.py`, `tests/test_view_otlp.py`, `tests/fixtures/view/otlp/`. Dependencies: T015. Verification: procedure_005.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-005 / SC-005
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T019

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T019] view_hooks.py Claude HTTP hooks and Codex notify or hook shim; dropped-attribute names inventory; ephe...

<!-- agent-braid-task-id: SPEC-061/T019 -->

## Task

`view_hooks.py` Claude HTTP hooks and Codex notify or hook shim; dropped-attribute names inventory; ephemeral effort handling. Dependencies: T015. Verification: procedure_005, procedure_007.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-005 / SC-005; REQ-007 / SC-007
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T020

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T020] view_model.py pure model: lanes, adjacent swap decomposition, relMs axis with gap compression, waves,...

<!-- agent-braid-task-id: SPEC-061/T020 -->

## Task

`view_model.py` pure model: lanes, adjacent swap decomposition, `relMs` axis with gap compression, waves, serial fallback, counters. Files: `agent_braid/view_model.py`, `tests/test_view_model.py`. Dependencies: T010. Verification: procedure_003, procedure_010.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-003 / SC-003; REQ-010 / SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T021

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T021] view_export.py minimal export from a recorded or replay file (--from) with SPEC-043 destination rules....

<!-- agent-braid-task-id: SPEC-061/T021 -->

## Task

`view_export.py` minimal export from a recorded or replay file (`--from`) with SPEC-043 destination rules. Files: `agent_braid/view_export.py`, `tests/test_view_export.py`. Dependencies: T020. Verification: procedure_007, procedure_008.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-007 / SC-007; REQ-008 / SC-008
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T022

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T022] Effort evidence pack: --arm, --arm-note, --baseline, pairwise comparisons in the harness comparison sh...

<!-- agent-braid-task-id: SPEC-061/T022 -->

## Task

Effort evidence pack: `--arm`, `--arm-note`, `--baseline`, pairwise comparisons in the harness comparison shape. Dependencies: T021, T027. Verification: procedure_009.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-009 / SC-009
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T027

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T027] view_render.py ASCII, braille, SVG and RGBA frames; /frame.svg and /frame.txt. Files: agent_braid/view...

<!-- agent-braid-task-id: SPEC-061/T027 -->

## Task

`view_render.py` ASCII, braille, SVG and RGBA frames; `/frame.svg` and `/frame.txt`. Files: `agent_braid/view_render.py`, `tests/test_view_render.py`. Dependencies: T020. Verification: procedure_011.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-011 / SC-011
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T023

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T023] Vendor Three.js r182 prebuilt modules (three.module.js, three.core.js) and OrbitControls with manifest...

<!-- agent-braid-task-id: SPEC-061/T023 -->

## Task

Vendor Three.js r182 prebuilt modules (`three.module.js`, `three.core.js`) and OrbitControls with `manifest.json`; add `LICENSES/three-MIT.txt`, the LICENSE paragraph and the THIRD_PARTY section. Dependencies: T003. Files: `integrations/agent-braid-view/web/vendor/**`, `LICENSE`, `LICENSES/`, `docs/development/THIRD_PARTY.md`. Verification: procedure_010.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-010 / SC-010; REQ-013 / SC-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T024

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T024] Web bundle: scene, playback, table view, hashed import map and CSP. Files: integrations/agent-braid-vi...

<!-- agent-braid-task-id: SPEC-061/T024 -->

## Task

Web bundle: scene, playback, table view, hashed import map and CSP. Files: `integrations/agent-braid-view/web/*`. Dependencies: T023, T020. Verification: procedure_010.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-010 / SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T025

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T025] Evidence panel, legend with "not a guarantee", Article 19 counters. Dependencies: T024. Verification:...

<!-- agent-braid-task-id: SPEC-061/T025 -->

## Task

Evidence panel, legend with "not a guarantee", Article 19 counters. Dependencies: T024. Verification: procedure_010.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-010 / SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T026

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T026] tests/test_view_web_bundle.py (hashes, no remote URL, no eval, CSP). Dependencies: T024. Verification:...

<!-- agent-braid-task-id: SPEC-061/T026 -->

## Task

`tests/test_view_web_bundle.py` (hashes, no remote URL, no `eval`, CSP). Dependencies: T024. Verification: procedure_010.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-010 / SC-010
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T028

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T028] view_cli.py with serve, export, validate, env, --surface; registration in agent_braid/cli.py. Files: a...

<!-- agent-braid-task-id: SPEC-061/T028 -->

## Task

`view_cli.py` with `serve`, `export`, `validate`, `env`, `--surface`; registration in `agent_braid/cli.py`. Files: `agent_braid/view_cli.py`, `agent_braid/cli.py`, `tests/test_view_cli.py`. Dependencies: T016, T021. Verification: procedure_011, procedure_012.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-011 / SC-011; REQ-012 / SC-012
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T029

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T029] Boundary tests (tests/test_view_boundaries.py) and regression run of governance, plugin package and va...

<!-- agent-braid-task-id: SPEC-061/T029 -->

## Task

Boundary tests (`tests/test_view_boundaries.py`) and regression run of governance, plugin package and validation profiles. Dependencies: T028. Verification: procedure_013.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-013 / SC-013
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T030

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T030] Claude Code OpenTelemetry attribute names

<!-- agent-braid-task-id: SPEC-061/T030 -->

## Task

Claude Code OpenTelemetry attribute names.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-014 / SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T031

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T031] Codex [otel] export shape

<!-- agent-braid-task-id: SPEC-061/T031 -->

## Task

Codex `[otel]` export shape.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-014 / SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T032

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T032] Claude desktop browser pane loads the viewer

<!-- agent-braid-task-id: SPEC-061/T032 -->

## Task

Claude desktop browser pane loads the viewer.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-014 / SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T033

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T033] Codex Desktop MCP Apps rendering (unobserved valid)

<!-- agent-braid-task-id: SPEC-061/T033 -->

## Task

Codex Desktop MCP Apps rendering (`unobserved` valid).

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-014 / SC-014
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T034

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T034] docs/tooling/VIEWER.md, integrations/agent-braid-view/README.md, tooling index. Dependencies: T028. Ve...

<!-- agent-braid-task-id: SPEC-061/T034 -->

## Task

`docs/tooling/VIEWER.md`, `integrations/agent-braid-view/README.md`, tooling index. Dependencies: T028. Verification: procedure_015.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: REQ-015 / SC-015
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T035

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T035] Owner-run comprehension observation. Dependencies: T034. Verification: procedure_hvis1

<!-- agent-braid-task-id: SPEC-061/T035 -->

## Task

Owner-run comprehension observation. Dependencies: T034. Verification: procedure_hvis1.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: optional, H-VIS1
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T036

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T036] Pre-PR reviews (code review, quality, simplification), validate_change --profile pr on the stable cand...

<!-- agent-braid-task-id: SPEC-061/T036 -->

## Task

Pre-PR reviews (code review, quality, simplification), `validate_change --profile pr` on the stable candidate, `/speckit-converge`. Dependencies: T010–T029, T034.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-061/T037

Proposed state: open. Parent: SPEC-061. Milestone: VIS.1 — Activity viewer. Labels: task. Project review: inherited from the parent (no separate flag).

Title: [SPEC-061 T037] Record obtained evidence in assurance.json, freeze, owner review of VIS.1 closure. Dependencies: T036

<!-- agent-braid-task-id: SPEC-061/T037 -->

## Task

Record obtained evidence in `assurance.json`, freeze, owner review of VIS.1 closure. Dependencies: T036.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/061-activity-viewer/assurance.json)
- Trace: See the parent issue and assurance record.
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.
