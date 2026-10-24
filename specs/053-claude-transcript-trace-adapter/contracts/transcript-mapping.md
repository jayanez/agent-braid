# Transcript mapping contract: `claude-subagent-transcript-v1`

Status: draft design, **BLOCKED by G0** and not an implemented or adopted API.
Nothing here is implemented, frozen, approved or authorizing. The mapper is an
engineering definition; the prediction that its read/write overlap anticipates
integration failures is hypothesis [H-CW1](../../../research/hypotheses/H-CW1-claude-workflow-integration.md),
untested. A transcript is the host's record of **requested** tool calls, not an
independently observed effect.

Requirement trace: REQ-003, REQ-004, REQ-005, REQ-006, REQ-007 (SC-003 to SC-007).

## Provisional input shape (to be pinned from the pre-freeze census)

The host documents where a subagent transcript lives (a JSONL file in a nested
`subagents/` folder, reported as `agent_transcript_path` in the SubagentStop hook
input; see [research.md](../research.md) RS-4). It does **not** document the line
schema. The shape below is an expectation drawn from the common
`tool_use` / `tool_result` content-block convention. It is unconfirmed for this
project. The founder's pre-freeze layout and tool-name census (task T002) reads
the founder's own existing subagent transcripts locally and keeps only a structure
and tool-name histogram, the G0 probe is written against that observed layout, and
PR5 then pins the observed shape as the transcript schema version that `-v1` accepts.
Until then no code may rely on it. A line that does not match the pinned shape is
a loss or a rejection (below), never a guess.

| Pointer (provisional) | Use | Retained |
|---|---|---|
| `type` | Select assistant or user records | no (control only) |
| `message.content[]` entries with `type == "tool_use"` | Tool request | class and counts only |
| `.name` | Tool name for the class table | class only (never the raw name unless in the table) |
| `.id` | Pair a request with its result | in memory only, never emitted |
| `.input.file_path`, `.input.notebook_path` | Resource path of `Read`, `Edit`, `Write`, `NotebookEdit` | as a normalized repository-relative path |
| `message.content[]` entries with `type == "tool_result"` | Outcome of a request | in memory only |
| `.tool_use_id`, `.is_error` | Pair result with request; failed call test | counts only |

Every other field, including prompts, assistant text, tool output, command
strings, patterns, URLs, thinking blocks and any `input` member not in the table,
is **not read into a retained structure**. The parser may traverse it to find the
line end, and discards it. Strings longer than 256 characters in an allowlisted
field reject the transcript.

## Tool name to effect kind

Order inside one transcript is line order, then content-array order.

| Tool name | Tool class | AIM effect kind | Resource | Notes |
|---|---|---|---|---|
| `Read` | `read` | `read` | `git://{repoId}/{path}` plus `readVersions[resource] = 0` | Only when the REQ-004 conditions hold; otherwise no effect and a loss |
| `Edit` | `write` | `write` | `git://{repoId}/{path}` | Failed call: no effect, loss |
| `Write` | `write` | `write` | `git://{repoId}/{path}` | Failed call: no effect, loss |
| `NotebookEdit` | `write` | `write` | `git://{repoId}/{path}` from `notebook_path` | Failed call: no effect, loss |
| `Bash` | `bash` | `unknown` | `claude-unknown://{repoId}/{instanceId}/bash` | Command text never read |
| `Grep`, `Glob` | `search` | `unknown` | `claude-unknown://{repoId}/{instanceId}/search` | Pattern never read |
| names starting `mcp__` | `mcp` | `unknown` | `claude-unknown://{repoId}/{instanceId}/mcp` | Server and tool names are not emitted |
| any other name (including `MultiEdit`, `Task`, web tools) | `other` | `unknown` | `claude-unknown://{repoId}/{instanceId}/other` | Conservative default |

Rules:

- The table is closed. A name that is not in it is `other`, never inferred from
  its spelling. Mapping `MultiEdit` to `write` would need a new mapper version,
  because the requirement lists only three write tools. The real tool inventory
  is pinned from the pre-freeze census (T002) at the T009 re-plan, and each
  write-capable tool the census finds that is not in this table gets its own
  conformance row (a write that falls into `other` is invisible as a write).
- At most one `unknown` effect per class and agent is emitted; the number of calls
  folded into it is an aggregate count in provenance.
- `unknown` resources are scoped to the agent so that two agents never share an
  `unknown` resource by accident. A shared exact resource with a write-like effect
  is what the existing analyzer reports as `conflicting`; `unknown` is not
  write-like.
- Effects go in the `inferred` channel only. `declared` and `observed` are empty
  arrays, because the transcript is the agent's recorded request, not a
  declaration by the operation and not an independent observation.
- `repoId` is the digest the Git adapter already computes (SHA-256 over the sorted
  root commits of the base), so transcript resources and `analyze-git` resources
  name the same file identically.

## Read binding and exclusions (REQ-004)

For each successful `Read` with a path inside the worktree:

1. Normalize lexically against the worktree root supplied in the conversion
   request (no filesystem access to the worktree; no symlink resolution).
2. Look the path up in the **base commit tree** with one bounded read-only Git
   call per agent (`ls-tree` through the existing bounded Git process wrapper).
3. If the entry is a regular blob and the same agent has not already written the
   path earlier in the transcript, emit a `read` effect and
   `readVersions[resource] = 0`, and add `{resource, objectId, objectFormat}` to
   the provenance `baseBlobs` table.

Version `0` means "the content at the base commit". The mapper never produces a
version greater than 0, because a transcript records no mid-run snapshot. The
integer carries no ordering; the identity is the object id in provenance (the
integer representation is a planning decision, see [research.md](../research.md) RS-2).

No read effect and no read version are emitted, and one loss code is counted, for:

| Loss code | Condition |
|---|---|
| `read-of-own-write` | The same agent wrote that path earlier in the transcript |
| `read-path-absent-at-base` | The path is not in the base tree |
| `read-outside-worktree` | Absolute or `..` path outside the worktree root |
| `read-non-regular-base-entry` | Symlink, gitlink (submodule) or other non-blob base entry |

## Coverage and losses (REQ-005)

- `effects.coverage.status` is always `partial`. Domain
  `claude-subagent-transcript-requested-tool-calls`, method
  `claude-subagent-transcript-v1`. It is never `complete` and never raised by
  any count.
- A loss never lowers coverage below `partial` in this mapper. This is
  deliberately different from the generic mapper (`generic-metadata-v1`), which
  sets `unknown` whenever it records a loss, and does not edit that rule (see
  [research.md](../research.md) RS-3). Losses are counted in provenance. In the
  analyzer `partial` and `unknown` produce the same pair labels, so this choice
  changes the label, not the analysis; it is reconsidered at the T009 re-plan.
- Failed tool calls produce no effect. A request with no result (interrupted or
  truncated transcript) is treated as failed here and counts under
  `failed-tool-call`. This differs from the G0 probe, which counts a write-class
  request without a result as an unknown writer; whether the mapper should emit
  an `unknown` effect for it is an open design question for the T009 re-plan, so
  that a write of unknown outcome is not silently dropped (Article 5).
- Because coverage is always `partial`, the existing analyzer can classify a pair
  as `conflicting`, `ordered` or `unknown`, and can **never** classify it
  `independent-candidate` from transcript evidence alone. The report must say so;
  independence is not a result this mapper can produce.
- Hidden effects remain surfaced as uncertainty (Article 5): `Bash`, `Grep`,
  `Glob` and MCP effects are invisible and stay `unknown`. The product keeps
  `Grep` and `Glob` as `unknown`, whereas the G0 descriptive call-share rate separates read-only
  searches from unknown writers; the conformance check (T018) reports that
  difference as a count.

| Loss code | Condition | Counted as |
|---|---|---|
| `failed-tool-call` | `is_error` true, or no matching result | integer count |
| `malformed-line` | A line is not a JSON object (including a truncated last line) | integer count |
| `unrecognized-record` | Parsed line not matching the pinned shape | integer count |
| `path-not-normalizable` | Empty, NUL-containing or over-long path | integer count |
| the four read codes above | See read binding | integer counts |

## Rejections (fail closed before analysis)

Diagnostics are fixed codes and never include a rejected value, field name, path
or line.

| Code | Condition |
|---|---|
| `transcript-count-limit` | More than 32 transcripts |
| `transcript-byte-limit` | A transcript over 32 MiB |
| `line-byte-limit` | A line over 1 MiB |
| `path-limit` | More than 512 distinct paths for one agent |
| `metadata-string-limit` | An allowlisted string over 256 characters |
| `nesting-limit` | JSON nesting over 16 |
| `duplicate-json-member` | Duplicate member in a line object |
| `nonfinite-json-number` | NaN or infinity |
| `transcript-unrecognized` | No line matched the pinned shape |
| `transcript-not-regular-file`, `transcript-read-failed`, `symlink-path-refused` | Local file checks |
| `admission-missing`, `admission-mismatch`, `admission-expired` | REQ-006 |
| `base-unresolvable`, `base-lookup-failed` | Git base lookup |
| `duplicate-instance-or-attempt` | Request identity collision |
| `invalid-aim-projection` | Projection rejected by the analyzer |

A rejection of one transcript is reported per agent. In the gate it degrades only
the transcript evidence (REQ-009).

## Bounds (planning defaults confirmed at clarification)

| Bound | Value |
|---|---|
| Transcripts per conversion | 32 |
| Bytes per transcript | 32 MiB |
| Bytes per line | 1 MiB |
| Distinct paths per agent | 512 |
| Allowlisted metadata string | 256 characters |
| JSON nesting depth | 16 |
| Operations in the projection | one per transcript, at most 32 (the plugin MCP operation limit) |

Reading is streaming: a transcript is read line by line from a regular,
non-symlink local file; no transcript is loaded whole. No network, no process
other than the bounded read-only Git call, no model call, no write other than the
explicit new output files.

## Conversion request and admission record (REQ-006)

The converter takes one conversion request (a small JSON file, not a transcript)
naming the base commit, the repository root, and one entry per agent (instance
identifier, attempt identifier, worktree root string, transcript path). It also
carries an `admission` object with a **new admission kind**,
`reviewed-real-source`, and the digest of a separate admission record file. The
existing `{"kind": "synthetic"}` admission is not accepted by this converter and
the existing importer does not accept the new kind; the two paths do not share a
branch.

Admission record fields (all required): `recordVersion`, `source` (owner and
scope: the founder's own sessions on an owner-controlled repository),
`rights` (statement and provider-terms confirmation status), `mapper`
(`claude-subagent-transcript-v1`), `transcriptSchemaPin`, `allowedFields` (must
equal the table above), `transformations` (digesting, normalization, counting),
`retention` (`allowlisted-metadata-and-counts`, never `aggregate-only`, which is
the G0 probe's rule), `retainedNonAggregate` (must list repository-relative paths,
base object ids and the per-transcript SHA-256), `pathDisclosure` (states that
paths are sensitive metadata that the converter retains and emits in the AIM
projection, and whether republication in the gate result is permitted; the
default is no, and the gate republishes paths only on operator opt-in),
`privacyBoundaries`, `reviewedBy` and `reviewRef` (a repository path to the
separate review record), `expires`. A record that is
missing, whose digest differs from the request, whose mapper, pin or allowed
fields differ, or that is past `expires`, is rejected with the fixed code above.
A record is an input to the check, not an approval: its bytes prove nothing about
who reviewed it. The task list keeps the review itself as a founder task.

## Outputs and provenance

Three artifacts, as in SPEC-023: the AIM projection (see
[the example](aim-trace-record.example.json)), the existing analysis report, and a
provenance file. Provenance holds mapper and pin identifiers, base commit,
`repoId`, per-agent transcript digest (a local SHA-256 of the raw file, labeled as
a local transformation), per-agent aggregate counts (tool calls by class, failed
calls, each loss code), the `baseBlobs` table (object ids), the bounds, the
admission record digest, `retention: "allowlisted-metadata-and-counts"`, a
`retainedNonAggregate` list naming the retained items that are not aggregates
(repository-relative paths, base object ids, the per-transcript SHA-256),
`executionAuthorization: false` and scientific limits. It never holds prompts,
file contents, command text or tool output.

The retention label is deliberately not `aggregate-only`: the artifacts keep
per-agent repository-relative paths (in the AIM projection), base object ids and a
digest of each raw transcript, which are metadata, not counts. `aggregate-only`
stays the G0 probe's label, because the probe retains no path or path hash.

Resource paths are necessarily present (they are the resource identity) and are
sensitive metadata: a file name can itself carry private text. The mapper does not
detect secrets in paths; it bounds their length and keeps the artifacts local.
Anything that republishes them (for example the gate result) is a separate
disclosure decision: the admission record must name path disclosure, and the gate
republishes transcript-derived paths only when the operator opts in
(`republishPaths`, default false).

## Relationship to the G0 probe

The G0 probe ([proposal](../../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md))
is a separate measurement tool with retained integer counts only. It counts failed
calls as unknown writers in its descriptive rate and attributes no changed file to them, whereas the mapper emits no effect for a failed call (SC-005);
C3 (attribution coverage of changes) stays tied to the probe and is not redefined by the mapper. PR5 adds a
conformance check that runs both on the same synthetic fixture and reports, not
hides, every difference. The probe's C3 attribution coverage stays the preregistered one.
