# Owner decisions, 2026-11-08 (SPEC-050/T001)

Recorded from interactive founder answers relayed by the orchestrator. Quoted text
is the owner's own answer where one was provided; decisions 3 and 4 were relayed as
summaries and are recorded as summaries, not as quotations. These records authorize
no native execution, adopt no ADR and change no task status.

| # | Topic | Decision |
|---|---|---|
| 1 | Freeze timing | "Congelar ya". Freeze the T001 contract now as an offline design contract. SPEC-049/T005 is recorded as an OPEN dependency; any T005 result reopens the contract by versioned amendment. |
| 2 | ADR status | "Mantener propuesta". The feature-local ADR proposal stays a proposal. No `docs/adr` entry is created, `specs/048-harness-variant-laboratory/adr-proposal.md` is not edited and SPEC-048 historical records are not frozen. Staged admission decisions are recorded only in [contracts/interface.md](contracts/interface.md). |
| 3 | Numeric limits | Reuse the SPEC-049 D2 caps unchanged for every profile: 30 minutes per unit, session at most 10 % of the 5-hour window, cohort at most 15 % of the weekly window, EUR 0. |
| 4 | Blocked from the start | Hooks, plugins/tool loops and delegated roles (no containment qualification; Codex not installed). Native effects stay blocked until the SPEC-048/T008 verdict. |

Deviation to note when T001 closes: tasks.md T001 lists `adr-proposal.md` as a
target file; decision 2 means it is intentionally not edited.

Effect: [contracts/interface.md](contracts/interface.md) sections 1, 6 and 8.
`tasks.md` and `assurance.json` are intentionally untouched here.
