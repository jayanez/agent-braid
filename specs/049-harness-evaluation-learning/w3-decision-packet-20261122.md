# W3 decision packet: T014 disposition, T007 promotion, D7 activation (2026-11-22)

Prepared by the orchestrator from the records on develop `7ee6ceed`. This packet decides
nothing. Each question below is answered by the owner, and the answers are recorded in a
separate decision record. Nothing here authorizes execution, promotion or a native unit.

## What T014 measured

Source: [evidence/t014.json](evidence/t014.json), report `run-t014-20261121d`.

- Route: Claude 2.1.292, Haiku, subscription, EUR 0, contained (SPEC-065 issuance
  2026-11-17, valid to 2026-12-17T22:19:29Z).
- Cohort: one lineage (L1), 5 holdout cases, arms A (base), B (guidance) and C (frozen
  offline refinement). 15 of 15 registered slots started, within the cap of 16. No slot
  is left.
- Rows: 13 correct, 1 incorrect (L1-C02-a:B), 1 not-attempted (L1-C02-a:A, slot lost
  when the terminal closed).

| Stratum | Units | A | B | C |
|---|---|---|---|---|
| continuity | 1 | 1/1 | 1/1 | 1/1 |
| coordination | 4 | 3/4 (1 not-attempted) | 3/4 (1 incorrect) | 4/4 |

Every comparison is `descriptive-only` (`below-D3-minimum`). The Clopper-Pearson 95 %
interval for a 1/1 cell is [0.025, 1]: the data cannot tell the arms apart.

Not measured: six endpoints (interventions, rework, interrupted recovery, conflict
precision and recall, false safe admissions, useful parallelism), correction and review
effort, costs (claim-blocked) and arm D (library ablation, infeasible in the window).
Units are not independent (no purge between units, T012-03 accepted for T014).

## Pre-registered rules that apply

- **D3 (SPEC-049):** with at most 4 independent lineages, any cohort stays descriptive
  only. More L1 units cannot produce a verdict.
- **T007 acceptance:** separate decisions per axis, cohort and profile; missing data or
  negative utility can justify no-go; never adopted because a report exists.
- **Promotion policy:** native ordinary use needs native evidence; approval cannot be
  inferred from passing tests or a merged PR.
- **D7 (SPEC-050, 2026-11-13):** a positive T014 leads to a Proposed ADR with measured
  criteria; a negative or **inconclusive** T014 closes the harness as experimental.
- **Plan, track G:** if D7 is negative or inconclusive, SPEC-077 (read-only harness MCP)
  is not published and its contract is archived.

## Q1. T014 disposition

| Option | What happens | Risk | Undo |
|---|---|---|---|
| **Close as inconclusive (recommended)** | T014 is ticked with the six endpoints, effort, costs and arm D listed as not measured on this roster. | None new; the limits are already in t014.json. | A later spec can register a new cohort with more lineages. |
| Keep open for a second cohort | Needs a new founder decision on the cap, new units and runs before 2026-12-17. | Under D3 it stays descriptive anyway; quota and owner time spent for no verdict. | Close later. |

## Q2. T007 promotion per axis

| Axis | Evidence | Recommendation |
|---|---|---|
| Continuity | 1 unit, all arms 1/1; a read-only described checkpoint, not real long-task recovery | **No-go for native ordinary use** (missing data) |
| Coordination | 4 units; B 3/4 with the incorrect row, C 4/4; conflict endpoints not measured | **No-go for native ordinary use** (missing data) |

No-go here means "not adopted", not "harmful". The offline `agent-braid harness` CLI
stays experimental and unchanged; nothing was promoted, so the rollback target is the
current state and the rehearsal is trivial. The alternative, per axis, is to leave the
decision pending, which keeps T007 and T010 open.

## Q3. D7 activation

| Option | What happens | Risk | Undo |
|---|---|---|---|
| **Apply D7: close the harness as experimental (recommended)** | No activation ADR. HAR closes with its actual scope: offline harness CLI experimental, native Claude containment qualified on one machine, no promotion. | The capability is shipped as experimental only. | A future spec with new evidence can propose an ADR. |
| Proposed ADR anyway | Draft an activation ADR without measured criteria. | Contradicts D7 and the promotion policy; nothing measured to base criteria on. | Reject the ADR. |

## Q4. SPEC-077 (read-only harness MCP) under an inconclusive D7

| Option | What happens |
|---|---|
| **T008 records "not published"; T003-T007 and T009 move to Deferred (recommended)** | ADR 0043 is marked Rejected under D7; the contract and spec stay in the repository as design history. HAR.3 loses 8 open issues. |
| Close SPEC-077 as not planned | Same, but the issues are closed instead of deferred, so a revival starts from new issues. |
| Keep SPEC-077 open in HAR.3 | Contradicts the plan's track G gate. |

## After the answers

The orchestrator writes `evidence/promotion/t007-owner-decisions-20261122.json`, ticks T014
and T007 per the answers, records SPEC-077 T008, updates `evaluation-report.md`, then
prepares T010 (dispositions; the independent Luna review is optional and only when
separately authorized), 050 T012 and the W4 release.
