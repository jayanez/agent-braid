<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# S1.5 documentation salvage record (2026-11-07)

Founder decision 7 of
[2026-11-07](../../../docs/development/FOUNDER_DECISIONS_20261107.md) asks for the
uncommitted S1.5 documentation edits of a stale local worktree to be compared with
`develop` and salvaged where still valid. This record lists each hunk and its
disposition. Automated wave track T5; no review or approval is implied.

## Source

- Worktree branch `claude/s15-docs-readme` at `49e31e81` (100 commits behind `767870b3`
  on 2026-11-07), owner machine. The worktree was read only (`git diff` and file
  reads). Nothing was checked out, stashed, added, committed, reset or cleaned
  there.
- Compared with `develop` at `767870b3`.

## Hunks

| File | Hunk | Disposition |
|---|---|---|
| `README.md` | System One shadow badge | Already on `develop`, same text. Not ported. |
| `README.md` | "Agent Braid also supports an opt-in System One decision layer" paragraph | Already on `develop`, same text. Not ported. |
| `README.md` | "Try a decision layer without trusting it" bullet | Already on `develop`, same text. Not ported. |
| `README.md` | "How it works" diagram and text version | Superseded on `develop`: the overview diagram plus a drill-down that uses the same alt text and the same six-step text (step 6 now links the user guide). Not ported. |
| `README.md` | Diagram source and Mermaid link | Superseded: `develop` links `docs/assets/` sources and the Mermaid diagram. Not ported. |
| `README.md` | Diagnostics row with the System One shadow mode link | Already on `develop`. Not ported. |
| `ROADMAP.md` | S1.5 paragraph: milestone #26, S1.5a merged in `0.1.0-alpha.5`, shadow week dates | Already on `develop`; this change updates the paragraph further to the facts of 2026-11-07. |
| `docs/STATUS.md` | S1.5 row: "Opt-in shadow mode supported", receipt due 2026-11-09 | Already on `develop`; this change updates the row further. |
| `docs/STATUS.md` | "Inspect local System 1 decisions" capability row | Already on `develop`, same text. Not ported. |
| `docs/system-one/README.md` | "Current state (2026-11-02)" section | Already on `develop`, same text. Not ported. |
| `docs/system-one/RESUMPTION.md` | "Current state (2026-11-02)" section | The worktree file is byte-identical to `develop`. Not ported. |
| `docs/tooling/SYSTEM_ONE_SHADOW.md` | Status line naming `0.1.0-alpha.5`; non-claim paragraph; downgrade warning for `0.1.0-alpha.4` and earlier | Already on `develop` (status line now reads "`0.1.0-alpha.5` and later"). Also skipped by ownership: open PR #1152 (track T3, T031) edits this file. Nothing left to port later. |
| `docs/assets/agent-braid-how-it-works.svg` and `.archify.json` (untracked) | Diagram and Archify source | Already on `develop` as `agent-braid-system2-system-one.svg` and `.archify.json`, added in #974. The JSON sources differ only in the Archify output path; the SVG on `develop` is the later render. Not ported, so no new asset needs a provenance or licence check. |

## Result

No hunk carried content that was both still accurate and absent from `develop`. The
only follow-up is the status update in the same pull request (STATUS and ROADMAP
S1.5 entries, plus a new M4.8 row and section), which states only merged facts.
