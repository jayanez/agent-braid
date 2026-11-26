# SPEC-076: owner decisions during refinement (2026-11-26)

The owner answered these points interactively while the spec was refined for wording,
structure and traceability. This record authorizes no code, no run and no execution
(`executionAuthorization` false). The spec stays deferred.

| Point | Decision |
|---|---|
| Exclusions with no covering REQ (cash spend and paid GPU rental, training on host-model output without the SPEC-075 terms gate, Hydra, automatic promotion) | Scope statements, no new REQ and no change to `assurance.json`. They cite ADR 0021, criterion 4 of `deferral.md`, the `training` contract and SPEC-073. Kubernetes (REQ-007) and System One loading (REQ-013) keep their REQ. |
| ADR 0042 lists "a base model and licence chosen" as a reopen criterion; `deferral.md`, REQ-001 and T001 do not | Open question for the founder (T001); REQ-001 and `deferral.md` unchanged. |
| REQ-009 expects token IDs and drop-and-count of overlong records from SPEC-075; SPEC-075 keeps token IDs out of records and marks bounds `truncated` | Open question for the founder at reopening; REQ-009 and SPEC-075 unchanged. |
| Non-functional requirements | No performance or availability requirement applies; numeric values are proposals in the `training` contract. |

Derived without a question: Terminology, Risks (from `plan.md`), Assumptions (from `assurance.json` and `plan.md`), Exit criteria (from the validation plan and tasks), Security and privacy, the other open questions (GPU-hour cap, meaning of "SPEC-075 delivered", CI versus GPU procedures, contract rules without REQ, RLOO variant, effect of a no-go). The heading "Evidence and unresolved questions" is kept and points to the new "Open questions" section; "Open decisions" keeps its heading and now says all four are open; Risks and assumptions stay under one heading.

Limits: the owner decides as owner, not as an independent reviewer. The options offered are not preserved in the repository.
