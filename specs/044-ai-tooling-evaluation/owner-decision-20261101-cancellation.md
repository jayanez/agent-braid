<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# SPEC-044 registered evaluation: owner cancellation, 2026-11-01

**Status:** owner decision, recorded by the coordinator session.
**Scope:** the SPEC-044 tasks parked in the `Deferred` milestone by the
[M4.5 closure decision](owner-decision-20261031-m45-closure.md).

## Decision

During the Deferred triage of 2026-11-01, the owner was asked whether to fund the
preregistered native evaluation: CLI vs MCP-only vs MCP-plus-skills, 108 registered
attempts, Codex coverage and the observation-contract correction. The owner answered
"Cancelar (Recommended)" (cancel).

## Effect

| Task | Issue | Disposition |
|---|---|---|
| T001 | #451 | cancelled, not completed |
| T002 | #452 | cancelled, not completed |
| T005–T010 | #455–#460 | cancelled, not completed |
| T017 | #595 | cancelled, not completed |
| T018 | #596 | cancelled, not completed |
| Parent SPEC-044 | #450 | closed; its remaining tasks are cancelled or already done |

Each task has an `agent-braid-task-cancellation-v1` record in [evidence/](evidence/),
bound to the unchanged task line by SHA-256. Issues close as "not planned".

## Boundaries

- No criterion is marked complete. No registration, attempt, comparison, admission
  or human acceptance exists or is claimed.
- SPEC-044/T003 and T004 keep their prior bounded closures unchanged.
- The observational receipts of 2026-10-31 stay bounded evidence for the tasks they
  cover. They are not a substitute for the cancelled registered comparison.
- The telemetry pilot NO-GO stands. `native-observation-contract-v1.md` is
  unchanged.
- SPEC-041, SPEC-043, SPEC-046 and SPEC-060 stay in `Deferred` under their own
  reopen criteria.

## Reopen criteria

A new owner decision to fund a registered native evaluation, with a fresh
preregistration bound to an exact candidate. Reopening creates new tasks; it does not
uncheck or rewrite these records.
