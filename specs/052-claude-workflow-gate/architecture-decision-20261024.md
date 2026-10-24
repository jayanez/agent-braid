# SPEC-052 architecture decision record: Claude-only workflows component

Status: **unsigned template; no decision recorded**. Prepared 2026-10-24 for
founder task T033. Nothing here adopts, amends or rejects
[ADR 0029](../../docs/adr/0029-claude-dynamic-workflows.md) (Proposed).
Trace: 052/REQ-009/SC-009, REQ-011/SC-011.

## Reviewed packet

| Item | Value |
|---|---|
| ADR | `docs/adr/0029-claude-dynamic-workflows.md`, SHA-256 `<fill at decision: sha256 of the file as reviewed>` |
| ADR 0024 change | link-only section; `docs/adr/0024-native-ai-plugins.md` |
| Authority impact review | `authority-impact-review.json` (self-review; independent review: `<pending>`) |
| Source commit reviewed | `<fill: full commit SHA>` |
| Open host verifications | HV-1..HV-5 (T029): `<fill: obtained / not obtained>` |

## Decision (founder fills exactly one)

- [ ] **Adopt** ADR 0029 as written, including the no-go list.
- [ ] **Amend**, with the amendments listed below, then adopt.
- [ ] **Reject**: keep the documentation recipe only; close R1 as no-go.

Amendments / conditions: `<none | list>`

## Scope statement (to be confirmed by the decider)

Adoption, if chosen, covers only a Claude-only `workflows/` component with
`braid-gate`. It does not accept a release, bump the version, publish to
plugin-dist, enable hooks, mods, agents, parallel or worktree agents, or widen
any MCP, grant or runtime limit. R1 and its version are separate decisions (T037).

## Provenance of the decision

| Field | Value |
|---|---|
| Decider | Juan Antonio Yáñez García (`@jayanez`) |
| Decision date | `<fill>` |
| Provenance kind | `<explicit owner message | signed commit | other>` |
| Source / verbatim instruction | `<fill; quote the owner's own words>` |
| Identity limit | A conversation instruction is not a cryptographic identity attestation. |

## After the decision (not done by this packet)

1. Set the ADR 0029 status line and date; re-snapshot the five current records
   again (the ADR bytes change) and update `authority-impact-review.json`.
2. T036: reconcile README/inventory wording, flip the builder default, tests.
3. Obtain independent review scoped to the authority delta.
4. If the number 0029 was taken meanwhile, renumber before adoption.

Signature: `<unsigned>`
