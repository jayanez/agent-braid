# Founder closure decisions — 2026-10-31

Successor of [PENDING_CLOSURE_20261021.md](PENDING_CLOSURE_20261021.md). This
record carries the owner's (jayanez, founder) administrative closure decisions
of 2026-10-31. Provenance: the answers below were relayed verbatim by the
coordinating session from the owner's coordinator chat; the transcript itself is
not stored in the repository. They are tracking decisions, not scientific
findings, reviews or acceptance.

## Decisions (verbatim)

| # | Scope | Owner's answer | Recorded effect |
|---|---|---|---|
| 1 | Milestones with no open tasks: ADP.1 (#231), FC.2 (#510, #661), M0.5 trailing #10/#16 | "Sí, cerrar los tres" | SPEC-023, SPEC-045, SPEC-051 and SPEC-002 parents close; SPEC-002/T006 closes by state override; milestones 10 and 20 close. Human review stays **pending** for all of them. |
| 2 | Where blocked work goes | "Milestone 'Deferred'" | One milestone, `Deferred`, holds the parked specs. |
| 3 | System One S1.0–S1.4 | "Cerrar como diferido" | DDP tasks are checked and closed as done; the other tasks of SPEC-028–033 and all of SPEC-030/032 move to `Deferred`; milestones 13–17 close. |
| 4 | M3.5 and FC.1 | "Cancelar por inviables" | Signed dispositions are written in `specs/019` and `specs/034`–`037` by a separate change. The tracking side (issues closed as not planned, milestones 9 and 18 closed) is **not** in this record's change; it follows that change's merge. |

## System One specifics

- DDP tasks checked: SPEC-028 T009–T011, SPEC-029 T026–T027, SPEC-031 T010–T011
  and SPEC-033 T009, each linked to its evidence in the respective `tasks.md`.
  SPEC-028/T009 (DDP-T01) is checked by this decision on the delivered
  documentary contracts alone.
- Specs moved to `Deferred` keep their parent issues **open**. Their closed DDP
  task issues travel with them because tracking assigns milestones per spec, not
  per task.
- Reopen criteria for the deferred System One work: SPEC-029 T001 source
  permissions are granted **and** admitted real groups are greater than zero.
- Still pending and not touched: human, Claude, scientific, admission,
  calibration, promotion, activation, product-publication and host-adoption
  gates ([pending gates](../system-one/addenda/v1-publication-closure-20261021/pending-gates.md)).

## Precedents followed

- Task closure by recorded override: SPEC-004/T005 in `github-tracking.json`
  (`task_state_overrides`), here SPEC-002/T006.
- Parent closure with human review pending: SPEC-017 and SPEC-021 (closed
  parents). The closed parents leave `project_review_pending`, which may only
  name open issues; their pending review is recorded here instead.

## Not covered

GOV.1, PUB.1, LAB.1, RES.1, M4.5 and HAR milestones await later decisions and are
unchanged. Nothing here authorizes execution, publication, training, source
admission or any claim; closing an issue records an administrative decision only.

## Applying the tracking side

After this change is merged into `develop`: create the `Deferred` milestone, run
`scripts/sync_github_tracking.py audit` and review the plan, then `apply` with
its digest from a clean `develop` checkout. Record the resulting `open_issues`
count per milestone.
