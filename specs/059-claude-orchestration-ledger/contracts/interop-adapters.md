# Interoperability adapters (documentation now; adapters deferred)

Status: draft design, **documentation only**. The founder decided on 2026-10-24 to interoperate with existing coordination tools rather than build locks or leases, to write the contract as documentation now, and to defer import adapters until there is demand or G1 evidence. Nothing here is implemented and nothing is scheduled before gate G2 (tasks marked `Deferred:`). This document extends the SPEC-057 interoperability inputs (`specs/057-claude-orchestration-advisory/contracts/interop-inputs.md`) to the two tools that matter most for a shared ledger. It makes no claim about those tools beyond what the dated sources show.

## Rules for every adapter

1. **Input only, one direction.** An adapter reads a file the operator provides and records an `import-recorded` event (tool, version, input digest, item count, role). It maps items to declared or observed inputs with provenance `imported:<tool>@<version>` (the SPEC-057 declaration carries the same information as `provenance: imported` plus `importedFrom`). It never writes to the other tool's store, never calls its network interface or CLI, never opens its database, and never treats its state as authority or as a grant. `executionAuthorization` stays `false`.
2. **Trust label `imported`.** An imported claim is a declaration by another tool and carries the `declared-only` label. An imported observation carries that tool's own observation limits.
3. **Offline and bounded.** At most 1 MiB, 32 units, 512 paths per unit, 256-character strings. Larger input is refused before parsing, with a ledger error.
4. **Verified before built.** No adapter is written until the other tool's output format has been read from a dated release and recorded here with the version, and there is demand or G1 evidence for the import. Every format below is **unconfirmed** today.
5. **Optional.** The ledger, the notices and every transport work with no import.
6. **Evidence gate, not integration.** A merge queue or orchestrator that already runs a verification step may call the documented read-only Agent Braid commands and read their results. Agent Braid does not depend on, start or configure that tool.

## Candidate inputs

Sources are the radar entries of `research/radar/2026-10-23-claude-workflows.json` (RAD-2026-014, RAD-2026-015) and `research/radar/2026-10-24-claude-orchestration.json` (RAD-2026-016 to RAD-2026-033), `docs/strategy/ECOSYSTEM.md` and the repository metadata read with read-only GitHub API calls on 2026-10-24. READMEs are self-reported and no tool behavior was reproduced.

| Tool | Possible input | Maps to | Dated source | Unconfirmed |
|---|---|---|---|---|
| mcp_agent_mail | File reservations (path or glob, TTL, exclusive flag), stored as JSON artifacts in its Git archive; agent identities and inboxes | `claim-overlap` hazards and `claim-recorded` events with an expiry hint; identities mapped only as labels | RAD-2026-018 (README read 2026-10-24) | The artifact layout on a given release; mapping of its agent names to unit ids; whether reservations carry enough to expand globs exactly; reservations are advisory in its README |
| Gas Town and Beads | Worker and work-item state, dependencies, completed-work signals, event log | Declared dependencies and ownership per unit; completed work as a quiesced-checkpoint signal; nothing else | RAD-2026-016 and RAD-2026-017 (READMEs read 2026-10-24) | Any file format; whether a verification gate can call an external read-only checker; stability across releases |
| Clash | `clash status --json` pairwise merge-tree predictions | An observed file-level text-conflict signal next to the Git adapter (designed by SPEC-057) | RAD-2026-014 (accessed 2026-10-23) | JSON field stability |
| git-kura | Path seals in the Git common directory | Declared writes per task key (designed by SPEC-057) | RAD-2026-020; the repository `tooppoo/git-kura` was confirmed to exist on 2026-10-24 with read-only GitHub API calls (0 stars, last push 2026-09-14) | The seal storage format and behavior (known from its README only). It is a radar entry, is not used here as parity or behind evidence, and an earlier note that the orchestrator had not found it is superseded by that confirmation |

Popularity figures are reading-day numbers from the radar entries and are not repeated here: they are not evidence of demand or quality, and archived or tiny projects (claude-net is archived; agent-coord and git-kura have a handful of stars at most) are not treated as evidence either way. Related tools in the same radar pass that hold durable claims or leases and that this specification does not import from today are recorded in the radar only (CoProgrammer RAD-2026-030, Edda and tracecraft RAD-2026-031, relayBrain RAD-2026-029, TeamBus RAD-2026-028).

## What an adapter must not do

It must not reconcile the other tool's lease expiry with a Braid claim by releasing anything; must not write a reservation, bead or message into the other tool; must not launch, message or resume any agent that the other tool manages; and must not claim that Agent Braid replaces, improves on or is unique relative to the other tool. Where the dated pass records the other tool as at parity or ahead (shared claim state, liveness recovery, leases and seals, inboxes, merge queues, durable claim and audit ledgers, tamper-evident ledgers), the ledger is a thin local record that exists so that Braid's own notices have a durable, idempotent home, and the correct user action may be to use the other tool and import its state.

## Dated prior-art pass

The coordination prior-art pass is recorded: `research/radar/2026-10-24-claude-orchestration.json` (`priorArtPass`, RAD-2026-016 to RAD-2026-033, including the official-marketplace sweep RAD-2026-033 of 315 plugins), `docs/strategy/ECOSYSTEM.md` and adoption track AT-2026-007. Task T006 would repeat or extend it for coordination, only if adapters are ever wanted (GitHub topic searches with ledger, lease, mailbox and handoff terms, and the complete documentation of mcp_agent_mail and Gas Town, of which the market track read only the first 100k of one 126k-character README) and records query set, date and sources read versus not read in `specs/059-claude-orchestration-ledger/evidence/prior-art-coordination.md` (not created by this specification). Until then the only permitted wording is the bounded sentence recorded in ECOSYSTEM.md, or its shorter form `no surveyed shipped plugin found` with the same query set and date; the ledger itself is not claimed as novel.
