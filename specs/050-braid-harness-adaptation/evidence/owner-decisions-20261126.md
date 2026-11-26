# SPEC-050: owner decisions during refinement (2026-11-26)

The owner answered these points interactively while the spec was refined for wording,
structure and traceability. This record authorizes no code, no run and no execution
(`executionAuthorization` false). Earlier records in the feature folder stay as written.

| Point | Decision |
|---|---|
| Cost ceilings (D2 caps, EUR 0) | New REQ-009 with SC-009 in the spec and `procedure_req_009` in the validation plan. The owner chose to add the requirement; `assurance.json` is not mirrored, see the limit below. Source: owner decision 3 of 2026-11-08. |
| Non-widening of existing authority | New REQ-010 with SC-010 and `procedure_req_010`, also not yet in `assurance.json`. It states what "Scientific boundaries and compatibility" already said. |
| D5 independent review | Owner answer: "El modelo puede ser Codex o de Claude Code, pero no se omite la revisión independiente del modelo". The independent model review stays required, and the model may be Codex or Claude Code. Luna is no longer the only named reviewer. Whether the 2026-11-24 GPT-6 review meets D5 is left as OQ-3 for the owner to confirm; the delta review after the native evidence remains pending. |
| Heading change | None. "Evidence and unresolved decisions" keeps its name because unresolved decisions remain (see Open questions). |

Changes made from the feature's own files, with no owner question:

- The status line and the evidence paragraph now say that T001–T011 are closed offline-only and that `assurance.json` holds no obtained scenario evidence.
- D7 is recorded as applied by SPEC-049 T007, from the SPEC-049 evaluation report.
- D4 (retention 30 days) and D6 are recorded as decided, although contract section 12 question 1, `capability-report.md` and the T011 and T012 notes still list retention as pending.

Left unchanged and reported: `tasks.md` is not edited (its lines are not changed by this refinement). Stale statements remain there and in `plan.md` and `validation-plan.md`: "All implementation and gate tasks remain pending", "All twelve tasks are pending", "No feature acceptance checks have run", the T012 note "no review record yet" and "native cohort pending" while SPEC-049/T014 used 15 of 15 slots, and contract section 1 still recording SPEC-049/T005 as open.

Limit found after the answers: `assurance.json` is draft/pending with historical snapshots and its exact bytes are validated against the preserved public draft tag. Any change makes `python -m scripts.validate_spec_kit` fail with "export manifest does not bind required file". It was therefore left unchanged, and SC-009 and SC-010 are not yet in it (OQ-15).

Limits: the owner decides as owner, not as an independent reviewer. REQ-009 and REQ-010 have no task tag yet (OQ-15).
