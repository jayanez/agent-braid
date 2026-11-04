# VIS.1c — Loom viewer redesign (plan)

Planning package for a third delivery of SPEC-061 (track VIS.1, milestone #25).
Nothing here implements the viewer; no code, schema, ADR or vendor file changes.
Every implementation task in [tasks.md](../tasks.md) (T051 onwards) is unticked.

## Why this is VIS.1c inside SPEC-061 and not a new spec

| Option | Verdict |
|---|---|
| New spec (SPEC-069) | Rejected. It would split one product surface across two specs and two milestones, and `scripts/sync_github_tracking.py` derives desired records from every `specs/*/spec.md`, so a new spec number needs a `github-tracking.json` entry that this change must not touch. It also would not remove the need to amend SPEC-061 REQ-010, which it contradicts. |
| Edit REQ-010 in place | Rejected. REQ-010 is covered by the T001 approval and the VIS.1a closure; rewriting it would blur what was approved. |
| **VIS.1c amendment of SPEC-061 (chosen)** | Same precedent as the "VIS.1a amendment (2026-11-03)": a dated amendment section in `spec.md` with the owner's answers verbatim, new requirement IDs (REQ-016 to REQ-023) instead of edits to REQ-001 to REQ-015, new task IDs (T050 onwards), a statement that the T001 approval and the historical snapshot do not cover it, and review at its own closure. New requirements supersede REQ-010 only where stated (default view). |

Deliberately not edited, to avoid invalidating `current` authority/evidence snapshots of
other specs (all ADRs and `contracts/` are in the authority inventory; historical
records are never rewritten): `docs/adr/0033-...md`, `loom-event.schema.json`,
`ui-security-privacy.md`, `docs/STATUS.md`, `ROADMAP.md`, the milestone index, the
tracking source and the Constitution. The ADR 0033 amendment and the contract amendment
are therefore **drafts in this folder**; on acceptance, separate reviewed changes move
them to `docs/adr/` and `contracts/`.

## Contents

| File | Purpose |
|---|---|
| [owner-decisions.md](owner-decisions.md) | Decisions recorded 2026-11-04 (verbatim) and the open decision list with recommendations |
| [plan.md](plan.md) | Architecture, phases, file ownership, validation, risks |
| [design-system.md](design-system.md) | Tokens, components, motion, page structure, copy guide for sections, titles and buttons |
| [timeline-2d.md](timeline-2d.md) | 2D timeline design (default view) |
| [three-d-fixes.md](three-d-fixes.md) | 3D fixes mapped to Three.js r186 APIs |
| [contract-v0.2-amendment-draft.md](contract-v0.2-amendment-draft.md) | `agent-braid-loom/v0.2` draft with privacy review items |
| [adr-0033-amendment-draft.md](adr-0033-amendment-draft.md) | ADR 0033 amendment, **Proposed** |
| [skill-lens-findings.md](skill-lens-findings.md) | What each design lens added to the audit |
| [audit/](audit/) | Source UX audit: report (Spanish, verbatim), screenshots, wireframes, synthetic fixture |

Requirements and acceptance scenarios are in the "VIS.1c amendment" section of
[spec.md](../spec.md); tasks T050 to T066 are in [tasks.md](../tasks.md).

## Evidence boundary

The audit is a read-only inspection of `develop` at `e8060ac5` using a synthetic
replay (`audit/fixture/rich.jsonl`, 34 events, 9 lanes, no owner data). Findings are
tagged [M] measured, [C] read in code, [I] inferred. No screen reader and no owner
session was used. Line references in the audit were checked against the current tree
only by symbol (for example `BUNDLE_FILES` is now at `agent_braid/view_cli.py:52`);
implementation tasks must re-read the code. The fixture is synthetic and not hook-faithful (some hook-adapter lanes close with outcome `ok`, whereas real hooks always close `unknown`, `view_hooks.py`); SC-017 checks lane timing, not outcomes, against it. A measured finding is not a usability
result: the acceptance scenarios ask for owner or user review before closure.
Claim level stays "inspiration" (SPEC-061); nothing here claims speedup, safety or
that a class, glyph or colour is a guarantee.
