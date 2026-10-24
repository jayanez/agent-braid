# Requirements-quality checklist

This checklist records properties of the documents, not evidence or approval.

- [x] CHK-001 Every requirement REQ-001..REQ-016 has exactly one scenario, a `procedure_req_NNN` section and planned (not obtained) evidence.
- [x] CHK-002 Scenarios use Given/When/Then and each states failure or inconclusive handling.
- [x] CHK-003 Exclusions are explicit: no transcript analysis (SPEC-053), no pre-flight or orchestration coordination (SPEC-057 to SPEC-059), no fan-out, edits, merges, refs, hooks, mods, grants or execution.
- [x] CHK-004 Analogy, hypothesis, empirical and formal statements are separated; H1 and H2 are not requirements; negative results are valid.
- [x] CHK-005 Known analyzer limits (A/M-only write effects, unknown for deletes, renames, binaries and symlinks, empty read versions, file-level conflicts, equal-to-base false negative) are stated and tied to requirements.
- [x] CHK-006 Host-dependent claims are marked unconfirmed until verified (REQ-013); no documentation claim is presented as observation.
- [x] CHK-007 `executionAuthorization: false`, host approval is not authority and grants stay outside the workflow (ADR 0021, Article 20).
- [x] CHK-008 No speed or agent-count claim; recorded NO-GO results are cited.
- [x] CHK-009 Budget stays EUR 0 additional; no publication, push or remote artifact is part of this delivery.
- [x] CHK-010 ADR handled as a feature-local proposal with no reserved number.
- [x] CHK-011 Public text is English; vendor names identify hosts only.
- [ ] CHK-012 Independent review of requirement wording and limits.
- [x] CHK-013 Material ambiguities resolved by clarification: see [spec.md Clarifications](../spec.md#clarifications) (planning decisions of 2026-10-23, not approval); what remains open is listed in the spec's "Evidence and open questions" section.
- [ ] CHK-014 Implementation, host verification, release acceptance and founder decisions (all pending).
- [x] CHK-015 The agents' tool surface is restricted by a host allowlist and by refusing runtime-enabled registrations, not by prompts alone (REQ-016; Article 12; ADR 0021).
- [x] CHK-016 The result carries the Article 13 assurance block and states that no status is a guarantee (REQ-007).
