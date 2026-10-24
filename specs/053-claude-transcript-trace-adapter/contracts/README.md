# SPEC-053 contracts

Draft design artifacts for the transcript adapter and gate v2. All of them are
**BLOCKED by G0**: no implementation, schema adoption or release follows from
them until the founder freezes G0, runs it and records a pass. They are
feature-local; they change no file under `schemas/`, `docs/adr/` or
`docs/architecture/`, so they do not alter the authority inventory.

| File | Content | Requirements |
|---|---|---|
| [transcript-mapping.md](transcript-mapping.md) | Tool name to effect kind table, coverage rule, allowlisted fields, bounds, rejections, admission record, provenance | REQ-003 to REQ-007 |
| [aim-trace-record.example.json](aim-trace-record.example.json) | Two-agent AIM `0.2.0-draft` projection that validates against `schemas/0.2.0-draft/agent-interaction-metadata.schema.json` and analyzes to one `conflicting` pair through a read/write overlap | REQ-003 to REQ-005 |
| [gate-result-v2.md](gate-result-v2.md) | v2 delta description (including the extended Article 13/14 `assurance` constants), interface and agent-bound reconciliation with SPEC-052's single constrained-Bash definition, and migration note, written against the committed SPEC-052 v1 schemas | REQ-009, REQ-010 |
| [gate-result-v2.delta.schema.json](gate-result-v2.delta.schema.json) | Overlay fragment for the result: `schemaVersion` `.../v0.2`, extended `assurance` constants, `transcriptEvidence`, per-interaction `transcriptHazards`, replaced `unobserved` and `limits` | REQ-010 |
| [braid-gate-args-v2.delta.schema.json](braid-gate-args-v2.delta.schema.json) | Overlay fragment for the arguments: optional `transcripts`, `transcriptDir`, `republishPaths` | REQ-009 |

The example and the fragments are checked structurally by the commands in
[quickstart.md](../quickstart.md). A passing structural check proves the example
is well formed; it proves nothing about real transcripts, the mapping's
soundness or any integration outcome.

The shape of the transcript lines the mapper reads is provisional and is not part
of any contract until it is pinned from the pre-freeze census (task T002).
