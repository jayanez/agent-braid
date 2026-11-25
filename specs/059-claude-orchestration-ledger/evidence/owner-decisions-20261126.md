# SPEC-059: owner decisions during refinement (2026-11-26)

The owner answered these points interactively while the spec was refined for wording,
structure and traceability. This record authorizes no code, no run and no promotion
(`executionAuthorization` false).

| Point | Decision |
|---|---|
| Missing `plan.md` | Left as is, with a stated reason: the feature is a sketch that is specified now and implemented later or never, and a plan is written only if G2 opens. No separate planning task. |
| Obligations with no covering REQ (the ledger never blocks and is never reclaimed automatically; the ledger is content-free, private and outside Git) | No new REQ and no change to `assurance.json`. The spec points to C1, C5 and C12 of `contracts/coordination-contract.md` and records OQ-8: convert them into REQ-006 and REQ-007 if G2 opens. |
| The nine decisions of 2026-10-24 | Stated as decided. The chosen answers are in the spec and in section 9.1 of the contract; the options offered then are not preserved in the repository. The pending addendum concerns only the planning interpretations and the values marked proposed. |

Derived without a question: Non-functional requirements (no performance or availability requirement; proposed bounds remain OQ-4), Security and privacy, Terminology, Risks, Assumptions (from `assurance.json`), Exit criteria (from the validation plan and tasks).

Limits: the owner decides as owner, not as an independent reviewer.
