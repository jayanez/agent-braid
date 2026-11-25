# SPEC-082: owner decisions during refinement (2026-11-25)

The owner answered these points interactively while the spec was refined for wording,
structure and traceability. This record authorizes no code, no run and no execution
(`executionAuthorization` false).

| Point | Decision |
|---|---|
| Exclusion on runs in the first PR | Scope statement, no requirement ID: PR #1515 is merged and ran nothing. |
| Exclusion on harness verdicts | Covered by REQ-002 for task records: a verdict field is an unknown key and refuses. |
| Exclusion on relabeling tasks as native sessions | Covered by REQ-002: origin is a closed vocabulary, now stated in REQ-002 and SC-002. |
| Exclusion on changes to SPEC-049 | The D1 split rules are covered by REQ-004. Frozen records, D2–D3 and the T005 roster are a scope statement. |
| Exclusion on grant, promote, activate | Scope statement. Authorizing execution is covered by REQ-013; promotion belongs to SPEC-085. |
| Non-functional requirements | No performance or availability requirement applies. |
| OD-6 owner-admission route | Removed. OD-6 as decided on 2026-11-23 stands: SPEC-084 after its gates; if SPEC-084 is infeasible, tasks stay `qa-incomplete`. |
| QA status vocabulary | Closed list of five: `pending`, `qa-incomplete`, `qa-passed`, `rejected`, `withdrawn`. |

Limits: the owner decides as owner, not as an independent reviewer. `pending` is a new
value in REQ-002; no schema or code exists yet (T003).
