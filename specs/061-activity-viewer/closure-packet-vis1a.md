<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# SPEC-061 VIS.1a closure packet (2026-11-03)

Status: **VIS.1a closed and frozen 2026-11-03.** The owner approved the closure
(answer "Arreglar 1+2, luego cerrar (Recommended)"; record
`owner-review-vis1a-closure-20261103.json`); closure findings 1 and 2 were fixed in #1013,
the evidence was recorded in #1017 and the assurance snapshots were advanced to 62a44fb7.
VIS.1b go/no-go T035 is due by 2027-01-31 after real use; T047 holds the review
follow-ups (findings 3 to 12). The text below is the packet as written for the review.
Engineering evidence is local unit tests; host verification and the owner's use of the
viewer are separate.

## What was delivered

VIS.1a is the coordination slice: a read-only, loopback-only viewer of Agent Braid
artifacts and observational Claude Code hooks, shipped as a companion (ADR 0032) with
vendored Three.js r186 (ADR 0033). Pull requests in this track, oldest first
(`git log 3bce7e58..HEAD`, SPEC-061 only):

| PR | Task | Content |
|---|---|---|
| #977, #981 | T017, T019 tick | Server and hook-ingest bookkeeping |
| #978 | T019 | Observational Claude Code hook ingest and allowlist re-pin |
| #980 | T024 | First-party web bundle: table view and evidence panel |
| #982 | T028 | `agent-braid view serve`, `validate`, `env` |
| #986 | T026 | Web bundle security and vendored-manifest tests |
| #987 | A1–A4 | Amendment record and task ticks T024–T028 |
| #989 | T025 | Three.js braid scene and manifest-checked vendor serving |
| #995 | T041 | Discovery of watch roots from registered plugin workspaces |
| #996 | T042 | Per-source checkboxes for scene and table |
| #997 | T040 | Plugin keeps private local copies of `analyze-work` reports |
| #1000 | docs | Ticks T040–T042, adds T044 |
| #1003 | T044 | Per-root source identity and checkboxes |
| #1005 | T043 | Web bundle and vendored files shipped in the built wheel |
| this PR | T029, T034, T036, T037 prep | Boundary tests, viewer guide, root banner, closure review, evidence receipt |

Earlier VIS.1a work (contract, validation rule, adapters, store, vendored Three.js,
model, ownership and gate adapters, server, replay, watch; PRs before #977) is
covered by the earlier ticks in `tasks.md`.

## Amendments A1–A4 (2026-11-03)

- **A1** — discovery without configuration and source filtering: T041 (discover roots
  from the plugin registry, `--no-discover`), T042 (per-source checkboxes), T044
  (per-root checkboxes with non-path labels `root 1` to `root 8`).
- **A2** — T040: the plugin keeps a private local copy of each `analyze-work` report
  (30 days, 64 MiB, 1,500 copies, never uploaded).
- **A3** — T043: the wheel ships the bundle and vendored files.
- **A4** — as recorded in `spec.md` and `tasks.md` (documentation and closure tasks).

## Deviations recorded in the track PRs

- Opacity by class was dropped from the scene: REQ-010 forbids ranking a class as safer
  than another, and opacity would do so.
- Scene draw cap of 2,000 elements, with the rest stated as not drawn and kept in the table.
- T040 copy count cap of 1,500 (each copy takes two of the watcher's 4,096 directory
  entries, `view_tail.MAX_ENTRIES`).
- This PR: `ArtifactTail` gains a read-only `roots` property (not in the T044 file list)
  so the start banner can print the label to path mapping from the exact order the
  labels were assigned.
- This PR: the `assurance.json` evidence entries of T037 prep were **not** added; see
  "Evidence" below.

## Closure review (T036)

Three read-only Sonnet reviews ran over `git diff 3bce7e58..HEAD` for the viewer
modules, `plugin_mcp.py`, the bundle, the tests and the guide: code correctness, quality,
simplification. No high-severity defect was reported.

Applied in this PR: hook payload strings that UTF-8 cannot encode (lone surrogates) are
treated as absent instead of causing a 500 (test added); a pointless f-string; a vacuous
`sleep` assertion; one shared node-missing skip rule for the scene test; narrower
exception and clearer name in a boundary test; the docs test now also requires a
`verified` receipt for a `verified` row; the guide states that restarting the viewer
requires restarting Claude Code (the ingest token is new at each start) and the exact
`--port` range.

### Closure findings (not applied)

1. **Resolved by the closure-fixes PR (T045).** Watcher loads report copies oldest first and the store caps are lifetime caps
   (4,096 crossings, 256 strands, 64 waves, 1,024 grants), so with many retained copies
   the newest reports can be truncated. Fix: walk `analysis-*` directories newest first or
   scan the newest N at start; or count live entities. Needs a design call. Medium.
2. **Resolved by the closure-fixes PR (T046).** Two `view serve` instances share the cookie name `braid_view` on loopback, so the
   second overwrites the first's session. Fix: name the cookie per port. Medium.
3. **Resolved by #1026 (design choice: a closed strand stays closed, later events leave a shape-unpinned gap; reopening is deferred until a resumed-session contract exists).** Hook strands never reopen after `SessionEnd` or `SubagentStop` and later events for
   them are dropped without a gap; `_strands` and `_children` are unbounded. Needs a
   decision on resumed sessions (REQ-003 absence rule). Low-medium.
4. **Resolved by #1026.** The static bundle serves every non-dot regular file in `web/`, while the contract says
   files listed in a manifest. Fix: allowlist or first-party manifest. Low.
5. **Resolved by #1026.** Slow-client connection slots: the 10-second socket timeout is per read, not per request.
   Loopback only. Low.
6. **Resolved by the closure-fixes PR (spec.md and assurance.json REQ-013/SC-013 text).** REQ-013 and SC-013 in `spec.md` say the plugin package and its tests are unchanged;
   T040 changed `plugin_mcp.py` and `tests/test_plugin_mcp.py`. Record the exception in
   the spec text (spec amendment, owner decision). Low.
7. **Resolved by #1026.** `IngestRefusal` and the inventory limits live in `view_serve`, so loading `view_hooks`
   loads the network modules transitively. Move to `view_loom` or `view_store`. Small.
8. **Resolved by #1026.** Root labels live in a module-level registry beside the store (`view_tail`), and
   `view_serve` imports the watcher for them. Cleaner: label per entry in the store, or a
   provider passed to the server. Follow-up.
9. **Resolved by #1025.** Web bundle tests rely on source-text assertions for playback, SSE resume, evidence
   panel and scene-failure fallback; extend the Node page driver with behaviour tests.
10. **Resolved by #1025, #1026 and this PR.** Simplifications: `_serve` is long (split into replay, roots, banner); `server._ingest_token`
    is read by the CLI (expose a property); the bundle/vendor path is derived in three
    places; the same exception-to-code mapping is written twice in `plugin_mcp.py`;
    HTTP test helpers are duplicated in five test files; `_private` is imported across
    modules.
11. **Resolved by #1025.** Report-copy pruning lists up to about 1,500 directories on every `analyze-work`
    while a lock is held; discovery runs once at start (restart after the first analysis).
12. **Resolved by this PR (CI installs setuptools and sets `AGENT_BRAID_REQUIRE_BUILD_TESTS=1`).** The wheel and sdist build tests are skipped without Python 3.12+ and setuptools 68+;
    CI is the evidence for SC-012's wheel claim.

## Converge pass (read-only consistency of spec, tasks, assurance and code)

- `tasks.md`: every VIS.1a task is ticked except the closure tasks T035, T036 and T037
  (T036 is done by this PR but is left for the orchestrator to tick after merge) and
  the VIS.1b tasks.
- `spec.md` vs code: REQ-001 to REQ-006, REQ-010, REQ-012 to REQ-015 are implemented and
  have tests; REQ-007 to REQ-009 and REQ-011 (frames) are VIS.1b; REQ-005 has only its
  Claude hook part. Gap: closure finding 6 (REQ-013 text).
- `assurance.json`: `obtained_evidence` holds the census (SC-002, SC-006) and the three
  host receipts (SC-014) only. Gap: SC-001, SC-003, SC-004, SC-005, SC-010 to SC-013 and
  SC-015 have none, and the scenarios point to `validation-plan.md` procedures rather
  than test names.
- Docs: `STATUS.md` row updated; the tooling index links the guide; `PLUGIN_PRIVACY.md`
  already states the report copies.

## Evidence (T037 prep; historical, resolved by #1017)

The spec-kit validator checks every `obtained_evidence` item against a file at the
`evidence_snapshot` commit (`b21c1c3b`, mode `historical`) by path and SHA-256. A new
receipt cannot exist at that commit, so an entry for it would fail validation until the
snapshot is advanced, which is part of the freeze and was not touched. This PR therefore
adds only the receipt
`specs/061-activity-viewer/evidence/vis1a-local-tests-20261103.json`
(sha256 `e60b1dbe33a188565990b0e11b5eea8059c9baab06a8107e281ff883b679dbe4`):
command, test modules per scenario, outcome (598 tests OK, 4 skipped) and limits.
At the freeze, the orchestrator adds one `obtained_evidence` item to each of SC-001 to SC-004,
SC-006, SC-010 to SC-013 and SC-015, and to SC-005 for the hook part, with that `path`
and `sha256`, the receipt's `command`, a scenario-specific `outcome` and its `limits`,
while advancing the evidence snapshot.

## Owner decisions needed (historical; resolved 2026-11-03)

Resolved: item 1 by the owner's answer recorded in the status line (findings 1 and 2 fixed in #1013, then close); item 2 (T035) stays open.

1. **Approve the VIS.1a closure** so the orchestrator can advance the evidence snapshot,
   record the evidence entries and freeze. Decide whether closure findings 1 and 2 (newest
   reports truncated; shared cookie) must be fixed before the owner opens the viewer on
   real sessions; both can bite in daily use.
2. **T035 go/no-go for VIS.1b by 2027-01-31**, after you open the viewer on real sessions
   and record the descriptive observation of procedure_hvis1 and the census result:
   keep, re-scope or close VIS.1 as Deferred for VIS.1b and VIS.2 to VIS.4.
