# SPEC-052: owner decisions during refinement (2026-11-26)

The spec was refined for structure under the 2026-11-25 conventions in
`docs/development/SPEC_KIT.md`. This record authorizes no code, no run, no freeze,
no release and no publication.

Decided by the owner:

- **Status line.** The owner chose to correct only `spec.md`. The old line said
  implementation and host verification were pending with no obtained evidence, while
  `tasks.md` ticks T004 to T021 and T023 to T032 with files under `evidence/`. The new
  line restates what `tasks.md` and `evidence/` already record and says that the
  "obtained evidence: none" wording of the scenarios refers to `assurance.json`. No
  task state, evidence claim or `assurance.json` content changed, and the stale
  sentence in the header of `tasks.md` ("All tasks are pending") was left as is.

Derived without a question:

- Non-functional requirements, Security and privacy, Terminology, Risks and
  assumptions, Exit criteria and Open questions were written from spec.md, plan.md
  (Risks table, Assumptions), tasks.md, contracts/braid-gate-result.schema.json,
  founder-decision-20261025.md and the files in `evidence/`. Each line cites its REQ
  or task. No new REQ was added, so `assurance.json`, `validation-plan.md` and
  `tasks.md` are unchanged.
- Statements bound only by a task or the ADR proposal (no network, nothing uploaded)
  are marked as task-level, not REQ-bound.
- The spec states no numeric latency or memory limit beyond the inherited MCP limits;
  the Non-functional section says so instead of inventing one.
- Open questions OQ-1 to OQ-8 come from the founder decision points in tasks.md,
  plan.md and the Evidence section. Owners are those the sources name; OQ-5, OQ-7 and
  OQ-8 say that the sources name none.
- The "What remains open" sentence in the Evidence section is labelled as the
  planning-time list; the wording is otherwise unchanged.

Limits: the owner decides as owner, not as an independent reviewer.
