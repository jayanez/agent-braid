# SPEC-080: owner decisions during refinement (2026-11-26)

The owner answered these points interactively while the spec was refined for wording,
structure and traceability. This record authorizes no code, no run and no execution
(`executionAuthorization` false). The decisions OD-1 to OD-7 of 2026-11-23 are in
`t001-owner-review.md` and are unchanged.

| Point | Decision |
|---|---|
| Exclusion on a new MCP tool | Scope statement, no requirement ID: ADR 0043 stays Rejected. |
| Exclusion on global host instructions, user configuration and permissions | Scope statement. REQ-007 covers only keys the OpenCode profile does not own; the header of `tasks.md` repeats the limit. |
| Other exclusions | Covered as far as their text reaches: REQ-003 and SC-003 (read commands only), REQ-004 (decline rules), REQ-006 (OpenCode unqualified, Claude and Codex rows unchanged), REQ-009 (consent). |
| REQ-007 wording | Corrected to the observation of T007: OpenCode 2.1.4 reads both the singular and the plural shapes. The REQ text and the assumption in `assurance.json` were updated to match; scope and scenario are unchanged. |
| Non-functional requirements | No performance or availability requirement applies. The plan's target of under 80 lines for `SKILL.md` stays plan guidance, not a requirement. |
| Open questions | None remain. |

Limits: the owner decides as owner, not as an independent reviewer. `assurance.json`
text changed, so its authority snapshot must be regenerated before any freeze.
