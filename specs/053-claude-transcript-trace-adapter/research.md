# Research decisions: SPEC-053

Status: draft planning input. Nothing here is evidence of a result: gate G0 has
not been frozen or run, no transcript has been read for this project, and every
mapper decision below is an engineering definition. Claim labels: the mapping
rules are engineering definitions; the prediction that read/write overlap
anticipates integration failures is the untested hypothesis
[H-CW1](../../research/hypotheses/H-CW1-claude-workflow-integration.md); no
analogy or formal claim is made; the host documentation cited below is
vendor-authored primary documentation, not peer-reviewed.

Decision ids below are `RS-n` (research decision n). They are named apart from the
release names R1 (commit-level SPEC-052 gate) and R2 (release with transcripts).

## Sources and how they were read

Primary host documentation, read on 2026-10-23 through a page scraper (the page
text was read; the byte hash of each page was not recorded, so these are
point-in-time readings, not pinned artifacts):

| Source | What it was used for | What it does **not** say |
|---|---|---|
| [Dynamic workflows](https://code.claude.com/docs/en/workflows) | A workflow is a JavaScript script run by a host runtime that orchestrates subagents; a plugin ships workflows in a `workflows/` directory, namespaced by plugin name; the script has no direct filesystem or shell access, agents do; the runtime tracks each agent's result; default of 16 concurrent agents and 1,000 agents per run | It does not describe the format of subagent transcripts, and the page text read does not describe merging or conflict detection across agents |
| [Plugin components](https://code.claude.com/docs/en/plugins/components) | `workflows/` is a plugin component; plugin MCP tool names have the form `mcp__plugin_<plugin>_<server>__<tool>`; the only valid plugin-agent `isolation` value is `"worktree"` | It does not say whether plugin MCP tools or plugin agents are reachable from inside a workflow agent (SPEC-052 host verification HV-1) |
| [Hooks](https://code.claude.com/docs/en/hooks) | The SubagentStop input carries `agent_transcript_path`, the subagent's own transcript, stored in a nested `subagents/` folder (the documented example ends in `.../subagents/agent-<id>.jsonl`); `transcript_path` is the main session's transcript; the main transcript "may lag the in-memory conversation" because it is written asynchronously; hook inputs name `tool_name`, `tool_input` and `tool_use_id` | It documents the **path** of a subagent transcript, not the JSON of its lines. The hook field names are hook-input fields, not a promise about transcript line fields |

Verified Agent Braid code limits (read in this worktree):

| Fact | Where | Consequence for the plan |
|---|---|---|
| The importer admits only `{"kind": "synthetic"}` and rejects anything else with `source-not-admitted`; the only mapper is `generic-metadata-v1`; limits 1 MiB, 64 operations, 512 events, depth 16, strings 256 | `agent_braid/trace_adapter.py` | A real source needs a new admission kind and cannot ride the synthetic branch |
| Whenever a mapping records a loss, the importer forces coverage to `unknown` | `trace_adapter.py`, `_effects` and the end of the operation loop | The transcript mapper's required `partial` coverage cannot reuse that function unchanged |
| A `read` effect without an entry in `readVersions` records the loss `missing-read-resource-version` | `trace_adapter.py` | A read effect must come with a version, or be dropped |
| `readVersions` is a map from resource to a non-negative integer, and the analyzer only reports `validate-read-versions-at-use`; it never compares values | `agent-interaction-metadata.schema.json`, `agent_braid/analysis.py` | The integer is an identity placeholder with no ordering semantics |
| A shared exact resource with a write-like effect is `conflicting`, including read plus write; coverage other than `complete` yields `unknown` at best; `independent-candidate` needs complete coverage; `unknown` effects are not write-like | `agent_braid/analysis.py` (`WRITE_LIKE`, `_interaction`) | Read/write hazards are visible to the unchanged analyzer; partial coverage means a transcript can never produce an independent candidate |
| Attempt identifiers must be unique across the whole batch, not only per instance | `analysis.py` `_validate_batch` (found by running the example) | The mapper derives `attemptId` from the instance identifier |
| The Git adapter names files `git://{repoId}/{path}` and unsupported ones `git-unsupported://...`; `repoId` is a digest of the sorted root commits | `agent_braid/git_adapter.py` | Transcript file resources use the same scheme so both layers name a file identically |
| `analyze-trace` accepts `--mapper` with exactly one choice | `agent_braid/cli.py` | A new mapper does not fit by widening that tuple without touching a SPEC-023 command |

## RS-1. Place the mapper in a separate module, leave `trace_adapter.py` unchanged

Decision: add `agent_braid/claude_transcript_trace.py`. It imports only public
names from `trace_adapter` (`InvalidTrace`, `TraceArtifacts`, `canonical_bytes`,
`digest_bytes`) and `analysis.analyze`, owns its own bounded validators and its
own conversion request, and is reached through a new CLI subcommand
(`analyze-claude-transcripts`). `trace_adapter.py`, the `analyze-trace`
subparser and the synthetic path are not edited, so SPEC-023 behavior is
unchanged by construction and REQ-008 reduces to proving that.

Rationale: the spec leaves "edit versus separate module" to planning. The edit
route has three collisions: the constant admission check, the loss-to-unknown
rule, and the file's role as the SPEC-023 owner's acceptance surface. A separate
module resolves all three without a conditional branch inside a reviewed file.

Alternatives:

- Edit `trace_adapter.py` (add a mapper and an admission kind). Rejected: touches
  a SPEC-023-owned sensitive file, needs a mapper-specific exception to the
  loss-to-unknown rule, and puts a vendor name in the generic module. Kept as the
  documented fallback if review asks for it; it would trigger the sensitive
  profile and the SPEC-023 owner's review before merge.
- Put the mapping in `analysis.py`. Rejected: Article 15 and the spec forbid
  coupling the core to a vendor, and the spec says `analysis.py` stays unchanged.
- Expose the mapper as a new plugin MCP tool. Rejected for this feature: the spec
  keeps the plugin MCP tool set and limits unchanged unless a separately reviewed
  change says otherwise, and the plugin MCP is workspace-bound, whereas
  transcripts live under the user's Claude project directory.

Residual risk: a sibling module still depends on SPEC-023's public names. A
signature change there would break it, so the SPEC-023 owner's review (REQ-008) is
retained and a test pins the imported names.

## RS-2. Integer representation of base-blob `readVersions`

Decision: `readVersions[resource] = 0` means "the content at the base commit".
The identity is the Git object id, carried **outside** the AIM record in the
provenance table `baseBlobs: [{resource, objectId, objectFormat}]`. The mapper
never emits a value greater than 0, because a transcript has no mid-run snapshot.

Rationale: the analyzer attaches no meaning to the integer beyond "a precondition
exists", and the schema offers only a non-negative integer. A constant with an
out-of-band identity table keeps the AIM record schema-valid, adds no vendor field
to the core schema, and is honest about what is known: every read is of the
single base snapshot. The binding is auditable (object id) without pretending the
integer orders anything.

Alternatives:

- Integer derived from the object id (first 48 bits). Rejected: collision risk,
  unreadable, and it invites comparing values the analyzer never compares.
- Ordinal index into the provenance table. Rejected: unstable across runs when the
  set of paths changes, and meaningless to a reader of the AIM record alone.
- Put the object id in the resource string. Rejected: it would stop a transcript
  resource from matching the Git adapter's `git://{repoId}/{path}` identity, which
  is what makes cross-layer comparison possible.

Limit: version 0 for all reads loses the distinction between "read an old blob
that another agent later rewrote" and any other read of base content. That
distinction is exactly what the hazard needs, and it comes from the shared
resource, not from the version value.

## RS-3. How `partial` coverage coexists with the loss-to-unknown rule

Decision: the new module applies its own rule: coverage is `partial` always;
losses are counted in provenance and never change coverage. The generic importer's
rule (loss implies `unknown`) is untouched and still applies to
`generic-metadata-v1`.

Rationale: for a transcript, some loss is the normal case (failed calls, `Bash`),
so mapping loss to `unknown` would make every transcript `unknown` and erase the
distinction between "we know several file effects but not others" and "we know
nothing". The spec requires `partial`, never `complete`. Since `partial` already
blocks `independent-candidate` in the analyzer, the conservative direction is
preserved.

Open for the T009 re-plan (review of 2026-10-24): in the analyzer `partial` and `unknown` coverage produce identical pair labels, so this departure from SPEC-023 changes the reported label and not the analysis; following SPEC-023, or setting `unknown` above a stated loss ratio, remains a candidate. Likewise a write request with no result record is dropped as a failed call here, whereas the G0 probe counts it as an unknown writer in its descriptive rate and attributes no file to it; an `unknown` effect for it remains a candidate. Neither is decided before G0.

Alternatives: emit `unknown` when any loss exists (rejected: contradicts SC-005);
add a `partial` carve-out to the generic importer (rejected: edits SPEC-023
behavior). An agent with no recognized tool-call record at all is rejected as
`transcript-unrecognized` rather than emitted as an empty partial record.

## RS-4. Transcript source, layout and the unconfirmed line schema

Decision: the converter reads the subagent transcript file named by the caller
(a path, or the files under `<transcriptDir>/subagents/`), never the main session
transcript, and never through a hook. The line schema is **provisional**: PR5
pins it from the pre-freeze layout and tool-name census (T002) and the host versions recorded during the runs, and `-v1` refuses
anything else. The G0 probe, not the product mapper, is the first reader.

Rationale: the hooks page documents the subagent transcript's location in a nested
`subagents/` folder but not its line format. Writing the mapper against an
assumed format would present a guess as a contract. The transcript is written
asynchronously, so a reader may see a truncated last line or a lagging file: a
truncated last line is a counted loss (`malformed-line`), and the gate must read
transcripts after the workflow has completed.

Alternatives:

- Capture tool calls live with `SubagentStop` or `PostToolUse` hooks. Rejected:
  ADR 0024 and the SPEC-052 proposal keep the plugin hook-free, and live capture
  is out of scope in the spec.
- Read the main session transcript for sidechain records. Rejected: the layout is
  not documented as stable, and a main transcript mixes more private content.
- Use the workflow runtime's recorded agent results. Rejected: the documented
  runtime records results, not tool-call streams, and the script has no filesystem
  access.

## RS-5. Tool classes and conservative defaults

Decision: exactly the table in
[contracts/transcript-mapping.md](contracts/transcript-mapping.md): `Read` is a
read; `Edit`, `Write`, `NotebookEdit` are writes; `Bash`, `Grep`, `Glob`, any name
starting `mcp__` and every other name are `unknown`. The table is closed and
versioned; a name is never classified by its spelling beyond the `mcp__` prefix.

Rationale: this is the spec's list, and it is the same classification the G0 probe
uses, so the descriptive call-share unknown rate and the product's unknown share are comparable.
Treating an unlisted tool as `unknown` can only reduce what the analyzer concludes
(Article 5: hidden effects reduce assurance and are surfaced).

Alternatives: map `MultiEdit` and similar tools to `write` (rejected for `-v1`:
outside the spec list; a later mapper version can add them after review). Count a
failed `Bash` as an unknown effect (rejected for the mapper by SC-005; the G0
probe counts failed calls as unknown writers in its descriptive rate and attributes no file to them (C3), so the two are reported side by side,
not merged).

## RS-6. Effect channel and resource naming

Decision: transcript effects go in `inferred`; `declared` and `observed` are
empty. Files use `git://{repoId}/{path}` with repository-relative POSIX paths
normalized lexically against the worktree root in the conversion request. Unknown
effects use `claude-unknown://{repoId}/{instanceId}/{class}`, scoped to the agent.

Rationale: the transcript is the agent's recorded request, which is neither a
declaration by the operation nor an independent observation (SC-005). Sharing the
Git adapter's resource scheme lets a gate compare layers. Scoping `unknown`
resources to one agent prevents two agents from appearing to share a resource only
because both used `Bash`.

Alternatives: `observed` (rejected: overstates); a Claude-specific resource scheme
for files (rejected: breaks cross-layer matching); no resource for `unknown`
(rejected: the schema requires a non-empty resource).

## RS-7. Privacy, retention and bounds

Decision: stream each transcript line by line from a regular non-symlink local
file with the clarified bounds (32 transcripts, 32 MiB per transcript, 1 MiB per
line, 512 distinct paths per agent, 256-character metadata strings, depth 16);
retain only allowlisted metadata and aggregate counts, labeled
`allowlisted-metadata-and-counts`, with the non-aggregate items (repository-relative
paths, base object ids, the per-transcript SHA-256) named in the admission record and
the provenance; emit fixed diagnostic codes with no rejected value; reject duplicate JSON members; make no network call;
start no process other than one bounded read-only Git call per agent.

Rationale: transcripts hold prompts, file contents, command output and possibly
secrets. The existing importer's discipline (fixed codes, bounded parser, owner-only
exclusive output, symlink refusal) is the precedent. The defaults come from the
founder's 2026-10-23 clarification and match the SPEC-023 string and depth limits.

A label of `aggregate-only` was rejected for the product because it would overstate
what is retained: the AIM projection carries per-agent paths, the provenance carries
object ids and a raw-file digest. That label remains correct for the G0 probe, which
retains integer counts only.

Alternatives: load a transcript whole (rejected: memory bound), tolerant parsing
of oversized lines by truncation (rejected: silently changes the observation),
redaction of secrets (rejected: not claimable; the allowlist plus aggregation is
the boundary, as in SPEC-023). Residual risk, stated, not solved: repository-relative
paths are sensitive metadata and can themselves contain private text; the mapper
bounds them and keeps outputs local but does not detect secrets.

## RS-8. Real-source admission kind

Decision: the converter accepts only the new admission kind
`reviewed-real-source`, bound by digest to a separate admission record that names
rights, allowed fields, transformations, retention, privacy boundaries, mapper,
transcript schema pin, reviewer reference and expiry. Missing, mismatched or
expired records are rejected with fixed codes (`admission-missing`,
`admission-mismatch`, `admission-expired`). The synthetic kind is neither accepted
by this converter nor changed in the importer.

Rationale: SPEC-023 requires a separately reviewed record before any real source,
and SC-006 requires a new admission kind with the synthetic path unchanged. A byte
check proves the record matches the request, not who reviewed it; review stays a
human task (the founder's own sessions are the only in-scope source, and the
provider-terms confirmation in the budget-and-source decision is still pending).

## RS-9. How the gate reaches the converter (gate v2 interface)

Decision (to be reconfirmed at PR6): the converter is reached through the bundled CLI
(a new additive subcommand `analyze-claude-transcripts`). The conversion is folded
into the existing analyze-phase agent of the SPEC-052 gate, which receives only the
aggregate report, the projection and the provenance, never transcript content. No new
plugin MCP tool is added and SPEC-052's four-agent, five-phase shape is unchanged.

Rationale: the plugin MCP tool set and limits stay unchanged by the spec, and the MCP
is bound to registered workspaces, while transcripts sit outside the repository. This
uses SPEC-052's single definition of the constrained Bash (explicit launcher
subcommands only, never the launcher binary) and, unlike SPEC-052's fallback, uses
the CLI alongside working MCP tools, so it needs exactly one more allowlist entry,
`analyze-claude-transcripts`, recorded in SPEC-052's Clarifications and REQ-016 as a
planning amendment approved by the founder on 2026-10-24. Folding the
conversion into the analyze agent keeps SPEC-052's static four-agent test (T004) and
D-4 intact; a fifth agent would need a reviewed SPEC-052 change. Transcript paths are
not SPEC-052 identifiers, so SPEC-052 REQ-008 (agent prompts embed only validated
identifiers) needs a reviewed amendment that admits a closed path-token class, and
the arguments overlay defines that class. If host verification shows the Bash cannot
be constrained, or the amendment is refused, gate v2 has no safe interface and the
transcript part of the gate is no-go while the commit-level gate stays valid. This is
the main unresolved feasibility dependency of REQ-009 and is recorded as a risk and a
finding, not assumed away.

Alternatives: a fifth conversion agent (rejected for now: needs a SPEC-052 change to
the agent bound), a new MCP tool (needs a separately reviewed change to a frozen tool
set), a model reading transcripts (rejected: puts private content in a model context
and violates Article 12's script-computed gating), a shell pipeline in the workflow
script (rejected: the script has no shell access per the workflows page), a
`transcriptDir` alone without ordinal alignment (rejected: host file names are agent
identifiers, so a directory cannot tie a file to a source).

## RS-10. Result schema v2 is additive, opt-in and written against the real v1

Decision: v2 is emitted only when transcripts are supplied; otherwise the v1 result
is emitted unchanged. The SPEC-052 v1 schema is committed, so the contracts use its
real names: `schemaVersion` (a new constant `.../v0.2`, not a `resultVersion` field),
per-pair hazards attached to `analysis.interactions[]` (there is no top-level `pairs`),
a new required `transcriptEvidence`, an arguments overlay for transcript inputs, and
explicit statements of the canonical `limits` and `unobserved` entries that v2
replaces. `agentsUsed` and `phases` do not change. Fields are described in
[contracts/gate-result-v2.md](contracts/gate-result-v2.md).

Rationale: SPEC-052 rejects unknown members in v1 (top level and `request`), so a
strict v1 validator cannot accept a v2 payload. "v1 consumers keep working" can only
hold if v1 output is unchanged when transcripts are absent and every v1 field keeps
its meaning in v2; SC-010 now says so. v1 requires the limit "Reads are not
observed; read hazards are outside this gate." and the `unobserved` entry
`transcripts`, which a result that reports read hazards would contradict, so v2
replaces exactly those.

Alternatives: a `resultVersion` field (rejected: v1 has none and rejects it), a
top-level `pairs` member (rejected: v1 has none and three existing pair lists), a
separate transcript result next to the v1 result (rejected for now: the migration
cost is the same and the gate would emit two documents), republishing paths by
default (rejected: opt-in only).

## RS-11. Gate G0 and what it can and cannot decide

G0 is a preregistered feasibility screen with the thresholds (C1a, C1b, C2, C3), the
order of evaluation, arms, kill outcome and retention pinned in the
[proposal](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md) and its
inputs record; this plan changes none of them. The plan only orders the human and
evidence steps around it. Points the plan keeps visible:

- Only C1b can unblock PR5 and PR6: it needs a reference failure that both merge-tree
  baselines, naive path overlap and `analyze-git` (primary and inclusive flags) all
  missed and that the probe flagged. C1a (commit-level evidence) informs release R1
  and unlocks nothing; a pass on commit-level evidence alone cannot approve building a
  component the experiment did not exercise.
- Designed overlap makes the reference-failure prevalence high by construction, so C2
  must exceed that prevalence and the naive path-overlap precision; it is a floor, not
  evidence of usefulness.

- C3 (revision 3) is attribution coverage of changes: attributed over changed files, at least 0.60, because the pre-freeze census on the founder's own transcripts (1,418 subagent files, 65,639 tool calls; aggregate-only, raw output not committed) shows `Bash` at 80.2% of calls and 85.4% of calls in the unknown class (read-only searches 0.0%, `Read` 7.8%), so the call-share definition would fail by construction. The threshold is a founder-amendable proposal; the call-share unknown rate is descriptive only.
- Source yield and consent come first: the budget-and-source decision is
  unsigned (the 2026-10-24 chat declaration applied to the revision 1 bytes and is superseded by revisions 2 and 3) and the provider-terms confirmation is pending. No run counts before the
  founder signs and freezes.
- The reference outcome (serial merge plus tests, run twice) is observed; every
  tool prediction is a proxy hashed before the reference exists. No human label is
  used.
- The unit is the run; pairs are not independent trials. Ten or more designed runs
  on one repository support existence and a rough precision screen, not prevalence,
  generalization or a false-negative rate. A single hit can satisfy C1a or C1b.
- `g0-fail`, `g0-inconclusive` and `g0-pass` are all valid outcomes. A pass
  unblocks planning of PR5 and PR6; it adopts nothing.
- Differences between the probe and the mapper (failed-call handling, the
  absent-at-base rule) are reported, because C2 and C3 are measured on the probe
  and the product mapper is a different instrument.

## RS-12. Whether an ADR is needed

SPEC-023's acceptance wording asks that new contracts or architectural boundaries
carry migration and versioning notes and an applicable ADR before implementation
acceptance. The additive mapper adds one identifier, one admission kind, one
subcommand and one provenance shape and changes no existing contract. This plan
therefore proposes a migration and versioning note (as SPEC-023 has) and treats
"is a canonical ADR required" as an explicit question for the SPEC-023 owner and
the founder at the start of PR5, not as a decision made here. Nothing in `docs/adr`
changes in this delivery.

## Limits of this research

- No transcript has been read; the line shape is an expectation, not a finding.
- A structural pass of the documents or fixtures is not a scientific result.
- Host behavior (plugin MCP tools and plugin agents inside workflow agents, nested
  calls, Bash constraint to the plugin launcher) is unconfirmed in the host
  documentation and needs the founder's native observation.
- Host version drift is possible; versions are recorded in the G0 manifest, not
  controlled.
- No speed, safety, completeness or conflict-rate claim is made; parallel runtime
  speedup remains a recorded NO-GO (SPEC-021 G4, SPEC-022, SPEC-038).
