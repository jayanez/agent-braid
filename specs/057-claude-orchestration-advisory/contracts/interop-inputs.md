# Interoperability inputs (deferred design)

Status: draft design, documentation only. Nothing here is implemented and nothing is scheduled (tasks T030 and T031 are deferred). The founder decided on 2026-10-24 to interoperate with existing coordination tools rather than rebuild locks or leases, to write the contract as documentation now, and to defer import adapters until there is demand or G1 evidence. This document fixes the shape of the optional inputs so that a later change can be reviewed against it.

## Rules that apply to every import

1. **Input only.** An import produces a declared or observed input to the existing analyzer, with the provenance `imported` and an `importedFrom` member naming the tool and the dated version (rendered `imported:<tool>@<version>`; the declaration schema carries both members). It is never authority, never a grant, and never changes `executionAuthorization` (always false).
2. **Offline and bounded.** Imports read a file the operator provides, within the bounds of REQ-017 (at most 1 MiB, 32 units, 512 paths per unit, 256-character strings). Agent Braid does not run the other tool, call its network interface or open its database.
3. **Verified before built.** No adapter is written until the other tool's output format has been read from a dated release and recorded in this directory with the version, and there is demand or G1 evidence for the import. All of the output formats below are unconfirmed today.
4. **No claim without a dated source.** Statements about another tool cite the source and date. Archived or tiny projects are not treated as evidence of demand, and a README-only characterization is not used as parity or behind evidence by this specification.
5. **Class stays honest.** An imported claim is a declaration by another tool and carries the `declared-only` label; an imported observation is labelled with that tool's observation limits.

## Candidate inputs

Sources are the radar entries of `research/radar/2026-10-23-claude-workflows.json` (RAD-2026-014, RAD-2026-015) and `research/radar/2026-10-24-claude-orchestration.json` (RAD-2026-016 to RAD-2026-020), and the repository metadata read with read-only GitHub API calls on 2026-10-24. READMEs are self-reported and no tool behavior was reproduced.

| Tool | Possible input | Maps to | Dated source | Unconfirmed |
| --- | --- | --- | --- | --- |
| Clash | `clash status --json` pairwise conflict predictions between worktrees | an observed, file-level text-conflict signal next to the Git adapter | RAD-2026-014, repository page accessed 2026-10-23 | The JSON field names and stability on a given release; the prediction method as claimed by its README |
| mcp_agent_mail | File reservations (path or glob, TTL, exclusive flag) stored as JSON in Git | declared ownership with an expiry | RAD-2026-015 (2026-10-23) and RAD-2026-018 (README read 2026-10-24; 2,222 stars, pushed 2026-10-23) | The artifact layout on a given release; how reservations map to unit ids |
| git-kura | Path seals held in the Git common directory | declared writes per task key | RAD-2026-020: repository `tooppoo/git-kura` confirmed on 2026-10-24 (described as a conflict-aware keyed worktree coordinator for Git; Apache-2.0; 0 stars; last push 2026-09-14); the seal behavior is known from its README only | The seal storage format and behavior; any use as evidence of parity or of being behind |
| Gas Town and Beads | Task and worker state; work items and dependencies | declared dependencies and ownership for units; completed-work state as a quiesced checkpoint signal | RAD-2026-016 and RAD-2026-017 (READMEs read 2026-10-24) | Any file format; whether a merge-queue verification step can call an external read-only checker |

## Agent Braid as an evidence gate

A merge queue or orchestrator that already runs a verification step may call the documented, read-only Agent Braid commands (the SPEC-052 gate over commit sources, or the SPEC-057 pre-flight and receipt) and read their results. Agent Braid does not integrate into, depend on, start or configure that tool. Whether any such tool can call an external checker is an unconfirmed question for the dated review in T030.

## What this document does not do

It does not claim that these tools lack a capability, that Agent Braid is better than any of them, or that their users want this. Plain write exclusion, leases, glob ownership, textual conflict prediction, blocking through hooks, shared claim state and liveness recovery are areas where the radar records these tools as at parity or ahead; declared-footprint pre-flight scheduling (OpenWeft, Orchestune), symbol-level overlap (DriftWatch) and combined-tree checks that name missing evidence (Radar) are recorded as parity or behind as well. Agent Braid's own bounded, untested candidate is the combination of an Article 13 compatibility class, pairwise classification that includes unknown, declared read/write hazards and declared-versus-observed receipts (REQ-015); unknown as a result is not claimed by itself.
