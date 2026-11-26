# SPEC-043: owner decisions during refinement (2026-11-26)

The owner answered these points interactively while the spec was refined for wording,
structure and traceability. This record authorizes no code, no run and no promotion.

| Point | Decision |
|---|---|
| Exclusions with no covering REQ (no source ref promotion, repository-code/hook execution, arbitrary network effects, new scientific guarantee; existing contracts unchanged) | Scope statements in the spec under "Exclusions", backed by `assurance.json` `scientific_limits`; REQ-003, REQ-004 and REQ-007 are cited only where their text covers part of an exclusion. No new REQ and no change to `assurance.json` or tasks. |
| Numeric bounds for "bounded node/edge input" and "overlarge content" (REQ-005, REQ-007) | Not stated in the spec; recorded as OQ-7 with the founder as owner. The values in code are not adopted as requirements. |
| REQ-007 ("without scripts") against `contracts/presentation.md` ("Offline HTML may use reviewed self-contained presentation code") | REQ-007 governs. The contract line now says offline HTML contains no scripts (REQ-007). `assurance.json` is unchanged. |

Derived without a question:

- Status line: aligned with `tasks.md` (T002, T004–T007 and T011–T014 done; T001,
  T003, T008 Deferred; T009, T010 open) and with the evidence bound in `assurance.json`.
- The statement that SPEC-044 T017/T018 were pending is replaced by their cancellation
  of 2026-11-01 (`../044-ai-tooling-evaluation/owner-decision-20261101-cancellation.md`).
- Non-functional requirements, Security and privacy, Terminology, Risks, Assumptions
  (from `assurance.json` and `plan.md`), Exit criteria (from the validation plan and
  `tasks.md`), Actors and Open questions OQ-1 to OQ-7.
- Headings are kept; "Evidence and unresolved questions" holds the open questions.

Not changed, reported for follow-up: the `tasks.md` header of SPEC-044 still lists T017
and T018 as open although the cancellation record cancels them; `checklists/requirements.md`
CHK-008 is unchecked although five scenarios have obtained evidence; the spec's "five
skills" wording predates the later skill count.

Limits: the owner decides as owner, not as an independent reviewer.
