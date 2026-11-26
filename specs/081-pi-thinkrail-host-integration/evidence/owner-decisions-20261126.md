# SPEC-081: owner decisions during refinement (2026-11-26)

The owner answered these points interactively while the spec was refined for wording,
structure and traceability. This record authorizes no code, no run and no execution
(`executionAuthorization` false). OD-1 to OD-7 of the spec stay open until T001.

| Point | Decision |
|---|---|
| Exclusions (MUST NOT) without a REQ | New requirements with scenarios: REQ-009 (no native sessions), REQ-010 (no new authority), REQ-011 (other hosts' bytes), REQ-012 (no new tool, contract or npm publication without OD-1), REQ-013 (no write to real configuration), REQ-014 (no secret in committed material). Scenarios SC-010 to SC-015 reuse procedures 002, 004, 005, 006 and 008. |
| Non-functional requirements | Regroup existing REQ-002, REQ-003, REQ-006, REQ-011 and REQ-013; no performance or availability requirement is declared. |
| Raw session JSONL outside the repository | New REQ-015 with scenario SC-016 (procedure_002; T003, T004). |
| Check for REQ-012 | No source defines a method; procedure_010 is a placeholder and OQ-1 stays open for the owner. |

Limits: the owner decides as owner, not as an independent reviewer. `assurance.json`
is in `current` authority mode; its snapshot hashes only authority documents.
