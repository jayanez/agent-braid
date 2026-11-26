# SPEC-058: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run, no freeze and
no signature.

Owner decisions asked in this session: none. No product decision was needed.

Derived without a question:

- Non-functional requirements, Security and privacy, Terminology, Risks and assumptions, Exit criteria and Open questions were written from `spec.md`, `plan.md` (Risks, Requirement to scenario to test to evidence), `tasks.md` and the Clarifications. Each line cites its REQ or task. No new REQ was added, so `assurance.json`, `tasks.md` and `validation-plan.md` are unchanged, following the SPEC-057 precedent for obligations that existing REQs already cover.
- The "Genuinely open" list of "Evidence and unresolved questions" moved into Open questions OQ-1 to OQ-11; the old section links to it. OQ-1 to OQ-4 are the items that T001 lists. Owners are those the sources name; OQ-10 says the sources name none beyond the founder.
- The SPEC-057 row of the family table said implementation waits for #671, #672 and the carrying pull request to merge. SPEC-057's Status line records them as merged, so the row now cites that.
- No numeric limit for memory or wall time is stated anywhere; the hook p95 of 500 ms is the G1 proposal's proposed criterion, and the Non-functional section says so.
- State checked: all 28 tasks in `tasks.md` are unchecked and `assurance.json` has no obtained evidence, so the Status line ("Nothing is implemented ... Obtained evidence: none") and the per-REQ "Planned evidence only" lines are accurate and unchanged.

Found and not fixed here (out of this refinement's scope):

- `plan.md` Sequence and the Clarifications name #671, #672 and the carrying pull request as preconditions in the future tense ("come first", "implementation after ... merged"); the Clarifications are dated decisions of 2026-10-24 and are kept as written.
- Whether SPEC-057 increment I-3 (the policy-profile schema) has merged was not checked; the candidate tasks T010 to T021 and T023 to T025 still state it as a precondition.

Limits: the owner decides as owner, not as an independent reviewer.
