# SPEC-052 contracts

Status: draft design, not an adopted or implemented interface. The workflow
`/agent-braid:braid-gate` does not exist yet. These files fix the planned shape
so that tests can be written first (tasks T004 to T008). They do not change any
existing contract, schema, MCP tool or grant.

| File | Purpose |
| --- | --- |
| [braid-gate-args.schema.json](braid-gate-args.schema.json) | The only accepted arguments: `base`, `sources`, `workspaceId`. JSON Schema draft 2020-12. |
| [braid-gate-result.schema.json](braid-gate-result.schema.json) | The single structured result for every outcome, including refused, busy and inconclusive. JSON Schema draft 2020-12. |

Both schemas reject unknown fields (`additionalProperties: false`). The schemas
were checked to be valid draft 2020-12 documents with the pinned `jsonschema`
package in the repository's isolated environment, as a planning aid only. Sample
envelopes validated against the first draft; after the review edits of
2026-10-23 (assurance block, hardening marker, stale-reference rule, new refusal
rules) only schema validity was re-checked and samples must be re-validated by
T007. None of this is obtained evidence for any requirement.

## Arguments

- `base`, `sources[]`: simple ref names (branch or tag) or full commit
  identifiers. The character set excludes `@`, `{`, `^`, `~`, `:`, spaces and a
  leading `-`, so an identifier can neither act as an option nor as a revision
  expression, and agent prompts can embed it without raw repository text.
- `sources`: 2 to 32 unique entries. One source is refused because it yields no
  pairwise evidence (founder clarification 2026-10-23).
- `workspaceId`: required, 32 lowercase hexadecimal characters as issued by
  plugin setup; never inferred or defaulted.
- Rules that need repository state are not schema rules and are reported as
  refusals by the validation phase: source equals base, unresolvable reference,
  duplicate after resolution, not a descendant of the base, not present in the
  registered repository, repository root differs from the registered workspace.

## Result

- `executionAuthorization` is the constant `false`. No field can carry, request
  or accept a grant.
- `assurance` is the Article 13 and 14 block, set by the script as constants:
  `compatibilityClass` (`0-heuristic`), `property`, `evidenceMethod`, `domain`,
  `assumptions`, `observationContract`, `executionContract` and a constant
  `notAGuarantee: true`. The class is a producer claim, not verified evidence or
  authorization. The envelope also separates what the analyzer observed, what the
  baseline observed and what is `unobserved`.
- `status` is one of `refused`, `busy`, `inconclusive`, `hazards-found`,
  `ok-analyzed`, `ok-certified`. No value is an approval, a safety statement or
  a speed statement (`assurance.notAGuarantee`). `ok-certified` means only: the
  analysis had no conflicting or unknown pair, the baseline was clean, replay
  evidence produced a certificate for 2 to 4 operations and the prepare tool
  returned a batch.
- Absent observations are `null` and never mean clean. A skipped replay carries a
  `skipReason` and never counts as a pass.
- `phases` is a fixed five-entry sequence (`validate`, `analyze`, `baseline`,
  `finalize`, `report`) with `agentUsed`; `agentsUsed` is at most 4 and counts the agents the script launched (a lower bound when the host restarts stalled attempts, REQ-010).
- Echoed strings (`request`, `refusal.input`, `refusal.message`, `phases[].detail`) are untrusted text: they may carry repository-controlled or tool-controlled content and must not be fed back to a model as instructions. Tightening the echoed name fields to the arguments pattern is T047; the schema is unchanged in this revision.
- `analysis` mirrors the analyzer without rewriting it: interaction
  classes, coverage and unknown effects.
- `baseline` records the pairwise `git merge-tree --write-tree` result with the
  explicit base as merge base, the constant `hardening` marker (one fixed
  hardened Git template for every phase) and a `repositoryStateCheck`. Merge
  results are ephemeral and never applied. `agreement` classifies
  each pair (`both-clean`, `both-conflicting`, `analyzer-stricter`,
  `baseline-stricter`, `analyzer-unknown`, `baseline-unavailable`,
  `not-comparable`). A pair where the analyzer says `independent-candidate` and the
  baseline conflicts is flagged `counterexample` and blocks conservativeness
  wording (REQ-015).
- `staleRefs` is the end-of-run re-resolution report; a non-empty report forces
  status `inconclusive` (schema rule) rather than a silent reanalysis.
- `advisoryOrder` is `null` unless the analysis declares dependencies; the gate
  declares none. `prepare.batch.order` is the input order of `sources`, not a
  recommendation.
- `refusal.rule` also covers `workspace-not-registered`, `workspace-root-mismatch`,
  `runtime-enabled-workspace` (any registered workspace has runtime enabled or a
  grant store) and `unsafe-tool-surface` (REQ-016). On the constrained-CLI
  fallback the registry rules are computed from the rows printed by the read-only
  launcher subcommand `plugin workspaces` (REQ-016(e)); rows that cannot be
  obtained or parsed refuse with `mcp-unavailable`. The envelope does not record
  whether the host allowlist was observed; that outcome (HV-1, HV-5) is kept in
  host receipts and stated by the `assumptions` constant.
- `limits` must contain each canonical limit statement verbatim (the schema uses
  `contains` for each), so the limits are identical across statuses.

## Mapping to requirements

| Requirement | Contract elements |
| --- | --- |
| REQ-001 | args schema; `refusal.rule` for `unknown-field`, `missing-field`, `wrong-type` |
| REQ-002 | `refusal.rule`, `pinned`, `operationCount` |
| REQ-003 | `analysis`, `phases[analyze]`, `agentsUsed` |
| REQ-004 | `replay` |
| REQ-005 | `prepare` (`mode` is the constant `serial`; no grant field exists) |
| REQ-006 | `baseline` (including `hardening`) |
| REQ-007 | the whole envelope, `assurance`, `limits`, `executionAuthorization`, `staleRefs`, `advisoryOrder`, `agentsUsed` |
| REQ-016 | `refusal.rule` for `runtime-enabled-workspace` and `unsafe-tool-surface` |
| REQ-010 | `status` busy and inconclusive, `refusal.rule` for `mcp-unavailable`, `limit-exceeded`, `timeout`, `workspace-not-registered` |
| REQ-015 | `agreement` |

## Versioning

`schemaVersion` is `agent-braid-claude-gate-result/v0.1`. Any later gate v2
(transcript-derived hazards, SPEC-053 REQ-009 and REQ-010, blocked by G0) must
use a new schema version and must not reinterpret these fields. The v1
`assurance` constants (including `evidenceMethod`, `observationContract`, `domain`
and `assumptions`) stay valid whenever no transcripts are supplied, because the gate
then emits this v1 result unchanged. SPEC-053's v2 delta extends those four
constants, and `property` and `executionContract`, only under the new
`schemaVersion` (see its `gate-result-v2.md`); `compatibilityClass` stays
`0-heuristic` and `notAGuarantee` stays `true`. No change to the v1 schema is
needed to allow the documented extension.
