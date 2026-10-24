> Unpublished local draft payloads derived from `tasks.md` and `assurance.json` as they stand in this working tree. No remote issue, label, milestone, description or Project change was created, audited or applied, and none is authorized by this file. Source links target the eventual integrated `develop` branch and do not claim that these local files are already there. Refresh against the final candidate before any external use.

# Unpublished issue drafts

Milestone: M4.6 — Claude Code dynamic workflows (does not exist remotely; creation is forbidden in this delivery). One spec parent issue plus one issue per task; labels `spec` and `task`. Only the spec parent is marked Project review pending (draft flag only; tasks inherit it through the parent, the convention SPEC-052, SPEC-053 and SPEC-057 drafts use). Tasks marked `Founder:` are founder actions or decisions; tasks marked `Orchestrator-launched:` are host probes that the orchestrating session launches only after the founder authorizes that individual probe; tasks marked `Review:` need a reviewer other than the drafter; tasks marked `Integrator:` touch files owned by another track; tasks marked `Deferred:` are not scheduled. SPEC-059 is a sketch; no implementation task exists.

## SPEC-059

Proposed state: open. Parent: none. Milestone: M4.6 — Claude Code dynamic workflows. Labels: spec. Project review: pending (draft flag).

<!-- agent-braid-spec-id: SPEC-059 -->

Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)

Requirements: REQ-001, REQ-002, REQ-003, REQ-004, REQ-005.

Issue state is a bounded tracking record, not a scientific or founder approval.

## SPEC-059/T001

Proposed state: open. Parent: SPEC-059. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-059/T001 -->

## Task

Founder: after the G1 results are recorded and gate GN has passed, review `contracts/coordination-contract.md` and record a decision to adopt (with amendments), defer or reject it as the G2 contract of the specs/039 route, as a separate decision record that names the contract file hash and includes the retention and deletion rule. Acceptance: adopting the contract is not adopting the ADR and unblocks nothing alone. Planned evidence: decision record path and SHA-256. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)
- Trace: REQ-001 SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-059/T002

Proposed state: open. Parent: SPEC-059. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-059/T002 -->

## Task

Review: an independent reviewer checks the coordination contract (identity, concurrency, idempotency, recovery, delivery, privacy) for gaps and for any weakening of the Constitution, GOVERNANCE.md or ADRs, before T001. Planned evidence: review record. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)
- Trace: REQ-001 SC-001
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-059/T003

Proposed state: open. Parent: SPEC-059. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-059/T003 -->

## Task

Review: run the offline schema checks of validation procedure 002 (composition with the SPEC-057 settings schema, the resolved-delivery coherence rule, the invalid fixture, trailing line feed and bidirectional character cases) and record the outcome. Planned evidence: command output and hashes. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)
- Trace: REQ-002 SC-002
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-059/T004

Proposed state: open. Parent: SPEC-059. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-059/T004 -->

## Task

Founder: with the SPEC-057 owner, confirm that the G1 protocol defines the late-notice-harm measure before its freeze (how an arm with earlier notice differs from the pull arm, the observation unit and a threshold), or record that the Megaphone and the Doorbell are dropped. Planned evidence: the G1 proposal text and a decision record. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)
- Trace: REQ-003 SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-059/T005

Proposed state: open. Parent: SPEC-059. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-059/T005 -->

## Task

Orchestrator-launched: only if G2 is opened, probes HV-L1 to HV-L8 (hook context per surface, own-session socket acceptance, monitor and channel delivery, repetition after compaction or resume, loss and duplication, identifier survival across restart, lock and fsync behavior), each after the founder's individual authorization, and the founder's decision on the attributed-write recorder after HV-L7. Planned evidence: pinned probe receipts with the host version. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)
- Trace: REQ-003 SC-003
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-059/T006

Proposed state: open. Parent: SPEC-059. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-059/T006 -->

## Task

Deferred: interoperation adapters for mcp_agent_mail or Gas Town, only after demand or G1 evidence exists and the formats are read from dated releases; until then `contracts/interop-adapters.md` stays documentation. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)
- Trace: REQ-004 SC-004
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-059/T007

Proposed state: open. Parent: SPEC-059. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-059/T007 -->

## Task

Integrator: keep the HAR.3 cross-reference, hypothesis index and roadmap wording consistent with this sketch (H-LD3 withdrawn; SPEC-059 specified now and implemented later or never). Planned evidence: reviewed integration diff. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)
- Trace: REQ-005 SC-005
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.

## SPEC-059/T008

Proposed state: open. Parent: SPEC-059. Milestone: M4.6 — Claude Code dynamic workflows. Labels: task. Project review: inherited from the parent (no separate flag).

<!-- agent-braid-task-id: SPEC-059/T008 -->

## Task

Founder: after review, record the disposition of SPEC-059 (open G2, defer or never implement) and close the sketch; a GN fail or an inconclusive gate means G2 is not opened. Planned evidence: decision record. Obtained: none.

- Source: [spec.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/spec.md) · [tasks.md](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/tasks.md) · [assurance.json](https://github.com/jayanez/agent-braid/blob/develop/specs/059-claude-orchestration-ledger/assurance.json)
- Trace: REQ-005 SC-005
- State basis: Source checkbox in tasks.md.

Planned and obtained evidence are separate in assurance.json. Closing this issue does not imply human review or scientific proof.
