# ADR 0024: Explicit local aggregate telemetry

- **Status:** proposed; implementation authorized on 2026-10-16, architectural adoption pending
- **Date:** 2026-10-16
- **Constitutional articles:** 5, 7, 12–15, 19–21

## Record identity

This proposal was numbered ADR 0023 in the historical telemetry candidate. The current repository assigns ADR 0023 to the second history correction. This renumbering preserves the proposal’s pending status and does not adopt it. The historical source bytes are retained at [the recorded proposal snapshot](../../specs/046-local-technical-telemetry/historical/adr-0023-local-technical-telemetry.md), SHA-256 `01552324429237a9f7114b223ee024687ba578d4efe72c8a0b6f49792125e989`.

## Context

M4.5 needs opt-in technical reliability/performance and analyzer-result summaries before a separately admitted Codex/Claude pilot. Existing measurement receipts and forecast episode telemetry contain domain-specific provenance and cannot be reused as general product telemetry.

## Proposed decision

SPEC-046 owns a common standard-library collector at the portable MCP and two analyzer CLI boundaries. Explicit `off|local` consent defaults to off. Store daily numeric counters/histograms in private, bounded, transactional SQLite outside repositories, retain 30 UTC dates on access, and expose manual strict incremental export/merge and purge. Never collect content or persistent repository/user/team/installation identities. No service, upload, daemon or additional spend. No internal algorithm instrumentation or skill-side collection.

## Consequences and limits

Aggregate observations carry fixed coverage/loss limits and do not guarantee anonymity or constitute experiment/native/human acceptance evidence. Local failures are swallowed only at the optional measurement boundary; product outcomes and permissions retain their owning contracts. Export batches have random per-batch identities and no persistent installation ID. User-managed exports/backups outlive local purge. Daily aggregates and receipt/evaluation artifacts remain distinct. Independent review, architectural adoption and founder acceptance are pending; no prior evidence is rebound to this candidate.
