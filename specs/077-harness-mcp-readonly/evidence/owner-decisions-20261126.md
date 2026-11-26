# SPEC-077 owner decisions (2026-11-26)

Refinement of the specification structure under the "Specification conventions" of `docs/development/SPEC_KIT.md`. Asked interactively; the owner chose the recommended option in every question.

| Decision | Answer | Meaning |
|---|---|---|
| Exclusions without a requirement | "3 REQ nuevos (Recomendado)" | REQ-011 (portable server, host configuration and `HARNESSING.md` claims untouched), REQ-012 (no submitted values, host paths or extra contents in results; contract invariant 5) and REQ-013 (host approval grants nothing; contract invariant 6), with scenarios SC-011 to SC-013 in `assurance.json`, procedures 010 to 012 and tags in T003 and T004. |
| Exit criteria | "Dos niveles (Recomendado)" | Closed: the T008 "not published" record and the T002 review record. If reopened: evidence of procedures 001 to 012 and a new publication decision. |
| OD-1 to OD-5 | "Diferidas con T001 (Recomendado)" | Listed as open questions, owner the founder, decided only if the surface is reopened. OD-6 is recorded as decided (rejected, T008). |

REQ-001 to REQ-010 are unchanged. Also fixed without a decision: `plan.md` validation table pointed REQ-009 and REQ-010 to procedures 009 and 010; they are procedures 007 and 008. No scope or scientific claim changes; `executionAuthorization` stays false. Open questions left: OD-1 to OD-5.
