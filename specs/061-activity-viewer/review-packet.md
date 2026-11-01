# SPEC-061 T001: owner review packet

Prepared for the owner's review of the activity viewer specification (VIS.1).
This file records no decision, creates no review record, ticks no task and does
not freeze anything. It is a reading aid. The review is recorded separately
against the frozen candidate (T008) once the owner answers.

## 1. What to read, in order

1. [spec.md](spec.md): purpose, scope, the requested decisions D1–D6 and
   REQ-001 to REQ-015.
2. [contracts/ui-security-privacy.md](contracts/ui-security-privacy.md): authority,
   network boundary, routes, data minimization and the
   [deviation table](contracts/ui-security-privacy.md#deviations-from-the-never-collect-list)
   (OD-7).
3. [plan.md](plan.md#human-review-and-unresolved-decisions): deliveries VIS.1a and
   VIS.1b, ordering and the open decisions.
4. [tasks.md](tasks.md) and [validation-plan.md](validation-plan.md): probes and
   census first, the T035 checkpoint (`procedure_census`, `procedure_hvis1`).
5. [tracks.md](tracks.md) (T006) and
   [host-verification-runbook.md](host-verification-runbook.md) (T007).
6. Optional: [contracts/loom-event.schema.json](contracts/loom-event.schema.json),
   [contracts/effort-evidence-pack.md](contracts/effort-evidence-pack.md),
   [research.md](research.md).

Already decided and not under review here: ADR 0032 and ADR 0033 (accepted
2026-11-01, Three.js pinned at r186), OD-4 (Q-VIS1 is a descriptive observation at
T035) and the VIS.1 publication (milestone #25, parent #810).

## 2. Requested decisions D1–D6 (confirm)

Recorded in [spec.md](spec.md#owner-decisions-requested-pending-t001) as requested
on 2026-10-31, with the D2, D3, D4 and D6 amendments of the adversarial and
counterfactual reviews. T001 confirms them or names any to reopen.

| ID | In short |
|---|---|
| D1 | Opt-in companion in this repository, never in the plugin package. |
| D2 | First surface: loopback web viewer with Three.js; other surfaces planned and selectable. |
| D3 | VIS.1a: contract, server, SSE, `--watch`, observational Claude Code hooks, replay, web viewer. VIS.1b: OTLP/JSON ingest. |
| D4 | Effort in memory only; export omits it by default; `--include-effort` pack in VIS.1b, labeled host estimates. |
| D5 | Track documentation kept current from the start. |
| D6 | Independent track VIS.1–VIS.4; VIS.1 is one milestone with deliveries 1a and 1b and a go/no-go checkpoint. |

## 3. Open decisions and recommendations

| ID | Question | Recommendation | Why |
|---|---|---|---|
| OD-3 | Public name | Keep "Loom" as working name and `agent-braid view` as the command; decide the public name before VIS.1 release notes | The command is stable; the name only matters at release. |
| OD-5 | Renderer | WebGL2 only in VIS.1; WebGPU is a later option | ADR 0033 vendors only the WebGL build; broad support. |
| OD-6 | Default port | OS-assigned; `--port` optional | Avoids collisions and squatting on a fixed port. |
| OD-7 | Never-collect deviations | Accept the six rows of the deviation table as listed | Each row has a purpose, a retention limit and an explicit flag; nothing reaches the SPEC-047 store. |
| OD-8a | Checkpoint date (T035) | **2027-01-31** | About 13 weeks for the VIS.1a slice (about 15 tasks plus the probes); if it passes without a slice, VIS.1 closes as Deferred. |
| OD-8b | Census threshold (T038) | **At least 5 sessions or run directories in the last four weeks with at least one coordination artifact, and at least 3 of the 6 artifact kinds present overall** | Below it the viewer would mostly show empty strands; the result then re-scopes VIS.1 to replay of curated artifacts, it does not cancel it. |

OD-7 detail, for the record: token counts, cost, exact durations and exact model
identifiers stay in process memory and are omitted from the default export; they
reach disk only with `--record-effort` or `--include-effort`. Salted identifiers,
relative artifact paths with SHA-256 hashes and sub-day relative time are kept in
memory and recordings because ordering and evidence inspection (Article 14) need
them.

## 4. Documents confirmed by the same review

- T006: [tracks.md](tracks.md) records VIS.2–VIS.4 with scope, entry gates and open
  questions; none is discarded.
- T007: [host-verification-runbook.md](host-verification-runbook.md) is the
  procedure for the owner-run probes T030–T033 (throwaway listeners, names never
  values).

## 5. What acceptance would not cover

- Implementation, host verification receipts or any probe result.
- The VIS.1b scope, which depends on the T035 checkpoint decision.
- VIS.2–VIS.4 specifications, which need their own reviews.
- Any claim that the braid shortens locating hazards (Q-VIS1 is an open question).
- Scientific validity, release or publication of any package.

## 6. Answer requested

1. Confirm D1–D6 as recorded, or name any to reopen.
2. OD-3, OD-5, OD-6, OD-7: accept the recommendations or give another answer.
3. OD-8: the checkpoint date and the census threshold.
4. Confirm T006 (tracks) and T007 (runbook).
