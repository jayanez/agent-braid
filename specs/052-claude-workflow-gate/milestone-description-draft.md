# M4.6 milestone description draft

Unpublished. Source-derived proposal for a milestone that does not exist remotely yet; no remote write, creation or approval was performed and publication is forbidden in this delivery. Milestone title (ID — Capability): **M4.6 — Claude Code dynamic workflows**. Number: unassigned.

## Proposed description

The text below is identical to the description already recorded for this milestone in `docs/development/github-tracking.json` (read, not edited by this track; SHA-256 of the UTF-8 text `972595fb1b312e1640c9bdda6342ffbde357f8413c6f5eca8311c23be3f56acc`):

> Read-only Agent Braid evidence for Claude Code dynamic workflows and orchestrator-style parallel agents: integration gate (SPEC-052), G0-gated transcript adapter (SPEC-053), advisory ownership/pre-flight/checkpoint/recovery core (SPEC-057), G1-gated opt-in guard (SPEC-058) and G2-gated ledger/push (SPEC-059); planning only, no execution authority. Extra cash spend EUR 0.

## Source facts at the planning candidate

- SPEC-052 contributes 1 spec parent and 47 task issues, all pending (see [tracking-drafts.json](tracking-drafts.json)). Obtained evidence: none; human review pending; nothing frozen or approved.
- SPEC-053 contributes 1 spec parent and 33 task issues, all pending (see its [tracking-drafts.json](../053-claude-transcript-trace-adapter/tracking-drafts.json)); its requirements REQ-003 to REQ-010 are blocked by G0. SPEC-057, SPEC-058 and SPEC-059 (added 2026-10-24) contribute their own spec parents and task issues; see their tracking-drafts.json files. The combined M4.6 count is computed by the integrator from all five tasks files.
- This file is the single milestone description draft for M4.6; the SPEC-053 tracking drafts point here and do not carry their own.
- The gate (SPEC-052) is independent of the G0 experiment; the SPEC-053 adapter and a gate v2 are blocked by G0, which may end negative or inconclusive and still allow closure.
- Recorded context kept visible: parallel runtime speedup is a recorded NO-GO (SPEC-021 G4, SPEC-022, SPEC-038); the milestone makes no speed claim.

## Publication notes (for a later, separately authorized step)

- The existing synchronizer creates and audits issues but does not reconcile the description of an existing milestone, and the milestone must first exist with a number recorded in the tracking configuration (`milestone_numbers`). Creation and any description write are separate founder-authorized operations; a read-back is needed after each.
- Labels used by the issue drafts: `spec` and `task`. Project Review pending is a draft flag on the spec parent of each M4.6 spec (SPEC-052 to SPEC-059) (tasks inherit it through the parent); the configuration lists are not edited here.
- A description in sentence case with the "ID — Capability" title format matches the other milestones in the configuration.
