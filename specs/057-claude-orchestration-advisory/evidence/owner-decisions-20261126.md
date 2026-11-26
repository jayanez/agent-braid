# SPEC-057: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run, no freeze and
no signature.

Owner decision (asked in this session):

- Stale status. `spec.md` said "Obtained evidence: none" and "Nothing is implemented" (the Status line, the Evidence section and 17 per-REQ Verification lines), while `assurance.json` holds obtained evidence for SC-001 to SC-010, SC-013 and SC-015 to SC-017, `tasks.md` checks T012 to T025, T032, T040 and T042, and #671 and #672 are merged. The owner chose to correct all of it. The Status line, the Evidence paragraph and the 14 Verification lines with evidence now cite `assurance.json` and the evidence files; SC-011, SC-012 and SC-014 keep "obtained evidence: none". No scope change and no task state change.

Derived without a question (no product decision was needed):

- Non-functional requirements, Security and privacy, Terminology, Risks and assumptions, Exit criteria and Open questions were written from spec.md, plan.md (Risks, Evidence handling, file-level design), tasks.md and the Clarifications. Each line cites its REQ or task. No new REQ was added, so `assurance.json`, `tasks.md` and `validation-plan.md` are unchanged, following the SPEC-053 and SPEC-032 precedent for obligations that existing REQs already cover.
- The "Genuinely open" list of "Evidence and unresolved questions" moved into Open questions OQ-1 to OQ-8; the old section now links to it. OQ-8 groups the "Planning interpretations" that the Clarifications mark as not founder-approved. Owners are those the sources name; OQ-6 says the sources name none.
- No numeric limit for latency, memory or wall time is stated anywhere, so the Non-functional section says so.

Found and not fixed here (out of this refinement's scope; for a later change):

- `tasks.md` opening paragraph still says all tasks are pending except T012 to T016 and that `obtained_evidence` covers only SC-001 to SC-003 and part of SC-017.
- `validation-plan.md` introduction and gate map still say no check has run and list "None" as executed checks.
- `plan.md` Delivery section still names the dependency pull requests in the future tense.

Limits: the owner decides as owner, not as an independent reviewer.
