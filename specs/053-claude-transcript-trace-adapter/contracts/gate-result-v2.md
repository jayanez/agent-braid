# Gate result v2 delta and migration note

Status: draft design, **BLOCKED by G0 and by the SPEC-052 v1 gate** (PR2). Nothing
here is implemented, adopted or authorizing. It is written against the committed
SPEC-052 contracts, which exist now (SPEC-052 PR1):
[braid-gate-result.schema.json](../../052-claude-workflow-gate/contracts/braid-gate-result.schema.json)
(`schemaVersion` `agent-braid-claude-gate-result/v0.1`) and
[braid-gate-args.schema.json](../../052-claude-workflow-gate/contracts/braid-gate-args.schema.json).
The machine fragments are [gate-result-v2.delta.schema.json](gate-result-v2.delta.schema.json)
and [braid-gate-args-v2.delta.schema.json](braid-gate-args-v2.delta.schema.json).
They are overlays: apply them to a copy of the v1 schema (see "Composition"). If
SPEC-052 changes its v1 schema before PR6, this note is reconciled again; it does
not edit the SPEC-052 files.

Requirement trace: REQ-009 and REQ-010 (SC-009, SC-010).

## Facts about v1 that shape v2

- `schemaVersion` is a constant, there is no `resultVersion` field.
- The top level and `request` have `additionalProperties: false`, so any added
  member needs a new `schemaVersion`; a strict v1 validator rejects a v2 payload.
- There is no top-level `pairs`. Pairs live in `analysis.interactions`
  (`left`, `right`, `classification`, `sharedResources`, `coverage`),
  `baseline.pairs` and `agreement.pairs`. `left` and `right` are operation
  instance identifiers.
- `assurance` (Article 13 and 14) is required and its members are constants:
  `compatibilityClass` `0-heuristic`, `property`, `evidenceMethod`, `domain`,
  `assumptions` (four entries), `observationContract`, `executionContract` and
  `notAGuarantee` `true`. The v1 `evidenceMethod` and `observationContract` name
  only the analyzer report, the merge-tree baseline and replay, so they cannot
  describe a result that also reports transcript hazards.
- `limits` must contain eight canonical strings (at most 16 entries), one of which
  is "Reads are not observed; read hazards are outside this gate."; `unobserved`
  must contain `uncommitted-work`, `reads` and `transcripts`.
- `agentsUsed` is at most 4 and `phases` is a fixed list of five (`validate`,
  `analyze`, `baseline`, `finalize`, `report`); SPEC-052 REQ-008, task T004 and
  D-4 bound the workflow to four agents, strictly sequential.
- The v1 arguments schema accepts only `base`, `sources` and `workspaceId`
  (`additionalProperties: false`), and SPEC-052 REQ-008 lets agent prompts embed
  only validated identifiers and schema-bound results.

## When v2 is emitted

- No transcript input supplied: the gate runs and emits the v1 result and accepts
  only the v1 arguments, byte for byte as before; the v1 `assurance` constants
  remain the valid ones. v2 is opt-in by input.
- Transcript inputs supplied: the gate emits v2 (`schemaVersion` `.../v0.2`). If
  every transcript fails, the result is still v2 with
  `transcriptEvidence.status: "unavailable"`, so a consumer can tell "not
  requested" (v1) from "requested and unavailable" (v2).

## Arguments delta

[braid-gate-args-v2.delta.schema.json](braid-gate-args-v2.delta.schema.json) adds
three optional members to the v1 arguments: `transcripts` (one entry per agent
with its `source` ordinal, a `worktreeRoot`, and either an absolute `path` or a
`file` name under `<transcriptDir>/subagents/`), `transcriptDir` and
`republishPaths` (default false). The ordinal alignment is what ties a transcript
file to its source; a directory alone cannot, because the host names files by agent
identifier.

Reconciling with SPEC-052 REQ-008 (identifiers only in prompts): a transcript path
is not a ref name or commit identifier. The delta therefore defines a closed
absolute-path token (simple characters only; no whitespace, quotes, metacharacters,
`..`, `//`, option-leading text or trailing slash). The script has no filesystem
access, so the path must reach the converting agent in its prompt. This needs a
reviewed SPEC-052 amendment that admits validated path tokens beside validated
identifiers (and T004's prompt rule with it). That amendment is a dependency of
REQ-009, not something this feature performs; without it the transcript part of
the gate is no-go.

## Interface and agent bound

The plugin MCP tool set is unchanged and the MCP is bound to registered
workspaces, so it cannot read transcripts that live under the user's Claude
project directory. The converter is therefore reached through the bundled CLI, a
new additive subcommand `analyze-claude-transcripts`, used **alongside** the
working MCP tools and not only as a fallback. The constrained Bash is defined
once, by SPEC-052's Clarifications and REQ-016(d): a host permission rule set that
allows only the fixed read-only Git prefixes and explicit launcher subcommands from
a closed list, never the launcher binary as a whole (the launcher also exposes
grant and execute subcommands). SPEC-052's v1 closed list is `analyze-git`,
`plan-git`, `verify-git` and the argument-less `plugin workspaces`, admitted only
on its fallback path. Gate v2 needs exactly one more entry, `analyze-claude-transcripts`.
SPEC-052's Clarifications and REQ-016 record that entry as a **planning amendment
pending founder review**, not approved: it is admitted only for gate v2 (blocked by
G0 and by SPEC-052's v1 gate), gate v1 never allows it, and the subcommand is
read-only toward the repository, the registry and the transcripts and creates only
its own new private output files at explicit paths. This note uses that
definition; it does not define a second one.

The conversion is folded into the existing `analyze`-phase agent: that agent
already owns the commit-level analysis, so the workflow keeps four agents, five
phases and `agentsUsed <= 4`, and SPEC-052's static test (at most four `agent(`
call sites) is unchanged. The agent receives only the aggregate report, the
projection and the provenance, never transcript content. If host verification HV-1
or the Bash constraint (with the one added subcommand) fails, or the SPEC-052
amendments (this allowlist entry and the validated path tokens above) are refused,
there is no safe interface and the transcript part of the gate is no-go, a valid
negative result that leaves the commit-level gate unchanged.

The `analyze` phase `status` and `detail` describe only the commit-level analysis.
A transcript failure is reported in `transcriptEvidence` and nowhere else.

## What v2 changes

| v1 location | v2 change |
|---|---|
| `schemaVersion` | Constant becomes `.../v0.2` |
| `assurance` | `compatibilityClass` stays `0-heuristic` and `notAGuarantee` stays `true`. `property`, `evidenceMethod`, `domain`, `assumptions`, `observationContract` and `executionContract` constants are extended for transcript evidence (the exact v2 constants are in [the delta](gate-result-v2.delta.schema.json)): the property adds heuristic read/write hazards from requested tool calls with partial coverage and still denies semantic commutation and independence; the evidence method adds the converter `analyze-claude-transcripts` and the mapper `claude-subagent-transcript-v1`; the domain adds the converter bounds; two assumptions are added (transcript matched to the source by ordinal with an unpinned line schema, and the one additional allowlisted subcommand recorded by host receipts); the observation contract adds the transcript conversion status, counts and hazards and says a missing or partial transcript never means no hazard; the execution contract adds that the converter reads locally without network or model and creates only its own new private output files outside the repository |
| `transcriptEvidence` (new, required) | `status` (`used`, `degraded`, `unavailable`), mapper and pin identifiers, `coverage: "partial"` constant, `retention: "allowlisted-metadata-and-counts"`, `retainedNonAggregate` naming repository-relative paths, base object ids and the per-transcript SHA-256, per-agent `status` (`mapped`, `missing`, `unreadable`, `oversized`, `unrecognized`, `rejected`) with a fixed diagnostic code, aggregate tool-call counts by class, loss counts, `pairsWithHazards`, `unknownShare` (two integers) and its own limits |
| `request.transcripts` (new, optional) | Echo of the transcript inputs as `count`, `mode` and `republishPaths` only; the supplied paths are not echoed |
| `analysis.interactions[]` | One optional member `transcriptHazards`: analyzer classification (`conflicting`, `ordered`, `unknown`; never `independent-candidate`), hazard kinds (`read-write`, `write-write`, `unknown-effect`), read/write overlap count, `resourcesRepublished`, bounded `resources` only when the operator opted in, `coverage: "partial"` |
| `unobserved` | Requires `uncommitted-work`, `reads` and `tool-calls`; `transcripts` is no longer required and is listed only for an agent whose transcript was not mapped |
| `limits` | The canonical "Reads are not observed; read hazards are outside this gate." is replaced by a statement that reads are known only as requested calls with partial coverage; three entries are added (transcripts record requested calls and `Bash`, search and MCP effects are invisible; independence is never concluded from transcripts; transcript-derived paths are sensitive and republished only on opt-in, and status, replay and preparation reflect commit-level evidence only). The other seven canonical limits are kept verbatim |

The replaced `limits` entry and the dropped `unobserved` requirement are replaced
because they would otherwise contradict a result that reports read hazards.

## What v2 does not change

- `gate`, `operationCount`, `agentsUsed`, `phases`, `refusal`, `pinned`, `baseline`,
  `agreement`, `replay`, `prepare`, `advisoryOrder`, `staleRefs` and `status` keep
  their names, types and meaning. In particular `status` is computed from
  commit-level evidence only: transcript hazards never change it, never trigger or
  suppress replay or preparation, and `ok-certified` keeps its commit-level
  meaning (the added limit says so). Whether transcript hazards should ever block
  preparation is a PR6 design decision, because doing so would change the meaning
  of a v1 field.
- The `git merge-tree` baseline, the agreement classification, replay eligibility
  and the commit-level unknown share are computed from the same inputs by the same
  rules and are never modified by transcript data.
- `executionAuthorization` is `false`. No v2 member can carry a grant, an approval
  or a promotion.
- A transcript problem degrades **only** `transcriptEvidence` (and the optional
  per-pair member for the affected agents). It never changes a commit-level label,
  never turns a commit-level `conflicting` or `unknown` into anything weaker, and
  never turns a missing transcript into "no hazard".
- Because transcript coverage is always `partial`, no pair is ever
  `independent-candidate` from transcript evidence; the schema omits that value.
  Transcript evidence can surface `conflicting`, `ordered` and `unknown`; it cannot
  provide positive independence evidence.

## Composition

To check the overlay against the committed v1 schema: copy the v1 schema; replace
the `schemaVersion` constant, the six extended `assurance` constants, the `unobserved` and `limits` `allOf` lists and add
`request.properties.transcripts`, `analysis.oneOf[1]...interactions.items.properties.transcriptHazards`
and the top-level `transcriptEvidence` (also added to `required`) from the delta;
move the delta `$defs` to the schema root; then run
`Draft202012Validator.check_schema` and validate a v1 sample (accepted by v1,
rejected by v2) and a v2 sample (accepted by v2, rejected by v1); a v2 sample that carries the v1 `assurance` constants must be rejected by v2, and a v1 sample keeps the v1 constants. The same overlay
works for the arguments delta. This check is part of task T023.

## Consumer migration

| Consumer | Action |
|---|---|
| Reads only known v1 fields and ignores the rest | Keeps working on v2 with no change; it simply does not see the new members. It must not infer from a v1 `unobserved`, `limits` or `assurance` constant expectation, which v2 changes as above |
| Validates strictly against the v1 schema (SPEC-052 REQ-007 rejects unknown members) | Must dispatch on `schemaVersion`. A v2 payload fails strict v1 validation **by design**; the v1 result remains obtainable by not supplying transcripts |
| New v2 consumer | Validate with the v2 schema (v1 plus this delta); treat `transcriptEvidence.status` `degraded` and `unavailable` as reduced evidence, not as absence of hazards |

The sentence "v1 consumers keep working" in SC-010 is satisfied in exactly this
bounded sense (SC-010 now states it): the v1 result is unchanged when transcripts
are not requested, and every v1 field keeps its name, type and meaning inside v2.
It cannot mean that a strict v1 validator accepts a v2 payload.

## Privacy of the result

The result carries counts, fixed codes and, only on operator opt-in
(`republishPaths`), bounded repository-relative paths. It carries no prompts, file
contents, command text, tool output or transcript text. Paths are sensitive
metadata; the commit-level result already names conflicted paths, and that v1
behavior is unchanged. `transcriptEvidence.retention` is the truthful product label
`allowlisted-metadata-and-counts` and `retainedNonAggregate` lists the retained
non-aggregate items; the label `aggregate-only` is reserved for the G0 probe.

## Version policy

A later `schemaVersion` or any change to the meaning of a v1 field requires a new
migration note and review. Adding a member to v2 is allowed only if it is
optional, and is recorded here.
