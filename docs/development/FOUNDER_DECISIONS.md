# Founder decisions register

Index of the owner's (jayanez, founder) recorded decisions, in date order. The
decision text, the owner's verbatim answers and the recorded effects stay in the
dated source files linked below; this register only lists them. Several sources are
bound by path from `specs/*/assurance.json`, ADRs and `github-tracking.json`, so
they are kept in place unchanged. A decision here is a direction, scope or
administrative decision, not a scientific finding, review or acceptance.

Each source names its predecessor, so the chain is
2026-10-31 → 2026-11-01 → 2026-11-07 → 2026-11-08 → 2026-11-10. The earlier
[pending-closure packet](PENDING_CLOSURE_20261021.md) of 2026-10-21 is historical.

| Date | # | Decision (scope as recorded in the source) | Spec | Source |
|---|---|---|---|---|
| 2026-10-31 | 1 | Milestones with no open tasks: ADP.1 (#231), FC.2 (#510, #661), M0.5 trailing #10/#16 | SPEC-023, SPEC-045, SPEC-051, SPEC-002 | [FOUNDER_DECISIONS_20261031.md](FOUNDER_DECISIONS_20261031.md) (#796) |
| 2026-10-31 | 2 | Where blocked work goes | milestone `Deferred` | same |
| 2026-10-31 | 3 | System One S1.0–S1.4 | SPEC-028–033 | same |
| 2026-10-31 | 4 | M3.5 and FC.1 | SPEC-019, SPEC-034–037 | same |
| 2026-10-31 | 5 | PUB.1: SPEC-009 T009, the 7 cutover obligations | SPEC-009 | same |
| 2026-11-01 | 1 | System One after the 2026-10-31 deferral | SPEC-066 | [FOUNDER_DECISIONS_20261101.md](FOUNDER_DECISIONS_20261101.md) (0a251f8d) |
| 2026-11-01 | 2 | Native-only System One | SPEC-066 | same; [owner review](../../specs/066-system-one-shadow/owner-review-20261101.md) |
| 2026-11-01 | 3 | ADR 0034 | SPEC-066 | same |
| 2026-11-01 | 4 | Training data | SPEC-066 | same |
| 2026-11-01 | 5 | SC-006 | SPEC-066 | same |
| 2026-11-07 | 1 | Target | SPEC-069, SPEC-066 | [FOUNDER_DECISIONS_20261107.md](FOUNDER_DECISIONS_20261107.md) (#1151) |
| 2026-11-07 | 2 | SPEC-069 P3 | SPEC-069 | same |
| 2026-11-07 | 3 | Split of SPEC-069 work | SPEC-069 | same |
| 2026-11-07 | 4 | SPEC-066 T031 | SPEC-066 | same |
| 2026-11-07 | 5 | GitHub authority | SPEC-069, SPEC-066 | same |
| 2026-11-07 | 6 | Branch protection | repository | same |
| 2026-11-07 | 7 | Stale worktree | SPEC-066 | same |
| 2026-11-07 | 8 | Parallelism | SPEC-069, SPEC-066 | same |
| 2026-11-07 | 9 | Native-run credentials | SPEC-069 | same |
| 2026-11-07 | 10 | Native-run spend | SPEC-069 | same |
| 2026-11-07 | 11 | Pinned models (D9) | SPEC-069 | same |
| 2026-11-07 | 12 | Release | SPEC-069 T012 | same |
| 2026-11-08 | 1 | ADR 0039 accepted | SPEC-070 | [FOUNDER_DECISIONS_20261108.md](FOUNDER_DECISIONS_20261108.md) (#1164) |
| 2026-11-08 | 2 | ADR 0040 accepted | SPEC-070 | same |
| 2026-11-08 | 3 | ADR 0041 accepted; ADR 0042 stays proposed and deferred | SPEC-070 | same |
| 2026-11-08 | 4 | SPEC-071 OD-1 | SPEC-071 | same |
| 2026-11-10 | 1 | Next work | SPEC-071 | [FOUNDER_DECISIONS_20261110.md](FOUNDER_DECISIONS_20261110.md) (#1276) |
| 2026-11-10 | 2 | SPEC-071 T001 | SPEC-071 | same |
| 2026-11-10 | 3 | SPEC-071 REQ-014 | SPEC-071 | same |
| 2026-11-10 | 4 | SPEC-071 OD-2 | SPEC-071 | same |
| 2026-11-10 | 5 | Real host runs | SPEC-071 | same |
| 2026-11-26 | 1 | Deferred triage: SPEC-077 and #1473 closed as not planned | SPEC-077, HAR T014 | [deferred-triage-20261126.md](deferred-triage-20261126.md) |
| 2026-11-26 | 2 | Deferred triage: #1424 (Codex quota observer) closed as not planned | SPEC-044 (cancelled) | same |
| 2026-11-26 | 3 | Deferred triage: #1343 closed, superseded by SPEC-079 | SPEC-069, SPEC-079 | same |
| 2026-11-26 | 4 | Deferred triage: SPEC-033 T001/T005/T007 closed, partly covered by SPEC-066 | SPEC-033, SPEC-066 | same |
| 2026-11-26 | 5 | Deferred triage: SPEC-041 T008 rescued; T001/T006 and closure tasks kept | SPEC-041, SPEC-043 | same |
| 2026-11-26 | 6 | Deferred triage: SPEC-046 stays read-only and parked | SPEC-046 | same |
| 2026-11-26 | 7 | Deferred triage: System One, SPEC-076 and SPEC-060 kept with corrected reopen criteria | SPEC-028–033, SPEC-076, SPEC-060 | same |
| 2026-11-27 | 1 | SPEC-066 D8 moved: GO packet 2026-11-30 (was 2026-11-28), `advise` live 2026-12-02 on a go (was 2026-11-30), review 2026-12-31 unchanged | SPEC-066 T406 | [STATUS](../STATUS.md), [SPEC-066 tasks](../../specs/066-system-one-shadow/tasks.md) |

The 2026-11-08 record also points to program decisions L1–L5 in the
[BL program](../../specs/070-braid-lightning-foundations/program.md).

## Deferred triage 2026-11-26

Adversarial triage of the 72 open issues in milestone `Deferred` (#24) before the
tracking-sync phase. Facts, the per-issue matrix and the milestone description draft
are in [deferred-triage-20261126.md](deferred-triage-20261126.md). The owner chose, in
the words of the options selected: SPEC-077 and #1473, "Cerrar los 9 (Recomendado)";
#1424, "Cerrar not-planned (Recomendado)"; #1343, "Cerrar, superado por 079
(Recomendado)"; SPEC-033 T001/T005/T007, "Cerrar los 3, cubiertos en parte
(Recomendado)" (re-asked after a fact correction); SPEC-041, "T001/T006 parked, T008 rescate (Recomendado)"; closure
tasks, "Mantener parked con trigger (Recomendado)"; SPEC-043, "Parked con criterio
del record (Recomendado)"; SPEC-046, "Sí, solo lectura + parked (Recomendado)";
System One, "Parked con trigger corregido (Recomendado)"; SPEC-076, "Parked con
trigger (Recomendado)"; SPEC-060, "Parked con trigger y fecha (Recomendado)". Result:
14 issues to close as not planned, 1 rescued (#425 into SPEC-041), 57 kept. No GitHub
issue or milestone was changed; the next phase applies this.
