# SPEC-061: Read-only local activity and concurrency viewer

**Track:** VIS.1 — Activity viewer (independent track; never a gate of the core,
of M4.x or of HAR)

**Status:** draft specification. The owner approved the direction and the
decisions below on 2026-10-31. [ADR 0032](../../docs/adr/0032-activity-viewer-companion.md)
(companion boundary) and [ADR 0033](../../docs/adr/0033-vendored-threejs-mit-boundary.md)
(vendored third-party code) are Proposed. Nothing is implemented by this change. Implementation tasks start
only after ADR 0032 is accepted; vendoring tasks also need ADR 0033.

## Purpose and scope

Agent Braid computes which operations commute, conflict, depend on conditions or
remain unknown, how work is grouped into waves, which grants authorize a run,
which ownership hazards were noticed and what a workflow gate decided. Today these
facts exist only as JSON artifacts and a static presentation layer (SPEC-043).
People who run several Claude Code or Codex agents cannot watch them, and the
coordination layer, which is the product's distinctive value, stays invisible.

This specification defines an opt-in, read-only, local companion (working name
"Loom", command `agent-braid view`) that:

1. translates existing Agent Braid artifacts and host telemetry into one versioned,
   ordered event stream, contract `agent-braid-loom/v0.1`;
2. serves that stream on the loopback interface, live (Server-Sent Events) and as
   replay;
3. renders it in a local web viewer as a braid in three dimensions (Three.js),
   where every visible element is bound to a computed fact and its evidence;
4. keeps effort data (tokens, cost, durations) in memory, records it only on
   explicit request, and exports it only as a comparative evidence pack.

This is engineering work with one recorded hypothesis (H-VIS1) that is not an
acceptance condition. VIS.1 covers the contract, adapters, ingest, server, replay,
web viewer, export and pure text/SVG frame rendering. Later tracks are planned in
[tracks.md](tracks.md) and are never discarded: VIS.2 (SPEC-062, Claude Code mod
pane and hook automation), VIS.3 (SPEC-063, Codex MCP App and a terminal UI) and
VIS.4 (SPEC-064, other hosts such as Cursor, OpenCode and Pi).

Exclusions: no execution, scheduling, grant issuance, retry, cancellation or any
write to a repository, registry, run directory or host configuration; no change to
the analyzer, runtime, ownership commands, plugin package (`integrations/agent-braid/`),
portable MCP contract or SPEC-047 telemetry store; no remote service, upload,
account or network listener outside loopback; no claim of speedup, cost saving or
safety; no reading of prompts, messages or transcripts in VIS.1.

## Authorities

Constitution clause zero and Articles 11, 13, 14, 19, 20, 21, 22 and 24;
[GOVERNANCE.md](../../GOVERNANCE.md) (license boundary, public contract change);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md); ADR 0012, ADR 0021,
ADR 0024 and ADR 0029 (no hooks, mods, monitors, agents or channels in the plugin
package); proposed ADR 0032 and ADR 0033; SPEC-039
[program](../039-ai-tooling-program/program.md) route "Embedded visual
interaction"; SPEC-043 presentation layer; SPEC-047
[data contract](../047-local-technical-telemetry/data-contract.md) and
[telemetry policy](../../docs/tooling/TELEMETRY.md); the SPEC-057 never-collect
list, which is scoped to telemetry about the SPEC-057 commands; this viewer writes
no telemetry and follows the same minimization by design.

## Owner decisions recorded

| ID | Decision (2026-10-31) |
|---|---|
| D1 | The viewer is an opt-in companion inside this repository, never inside the `agent-braid` plugin package. |
| D2 | First surface: web 3D with Three.js on loopback. The Claude Code mod pane, a terminal UI and a Codex MCP App are planned; the surface is selectable by configuration; the design stays host-agnostic for Cursor, OpenCode, Pi and others. |
| D3 | Live-capable from VIS.1: contract, loopback server, Server-Sent Events, OTLP/JSON ingest for Claude Code and Codex, replay and the web viewer. |
| D4 | Effort data is ephemeral in memory. Export omits it by default; `--include-effort` builds a comparative evidence pack aligned with `agent-braid harness compare`, so cost impact can be shown at work. |
| D5 | Track documentation (ROADMAP, STATUS, milestone index, program, GitHub tracking) is updated from the start. |
| D6 | Tracking as independent track VIS.1–VIS.4, with GitHub milestone, issues and Project 6 entries created through the reviewed tracking reconciliation after merge. |

## Requirements and acceptance scenarios

### REQ-001 — Versioned event contract

Every event is one JSON object per line with `schemaVersion`
`agent-braid-loom/v0.1`, a strictly increasing integer `seq`, a `kind` from a
closed list, a relative monotonic time `at` (`relMs`, `basis`), a `source`
(`adapter`, `evidenceRef`, `host`), an `assurance` block
(`compatibilityClass`, `notAGuarantee: true`) and `executionAuthorization`
fixed to `false`. `compatibilityClass` is the Article 13 class declared by the
analysis fact an event carries and is `null` for events that carry no analysis
result (strands, effort, gaps, session). The closed kinds are `session.origin`,
`analysis.report`, `strand.open`, `strand.update`, `strand.close`,
`crossing.classified`, `wave.planned`, `wave.started`, `wave.finished`,
`grant.issued`, `grant.consumed`, `grant.expired`, `grant.refused`,
`hazard.noticed`, `gate.phase`, `gate.result`, `runtime.phase`, `effort.sample`
and `observation.gap`. Status and mode values are copied verbatim from their
source contracts. Lines are at most 16 KiB. A file or POST body with more than
50 000 events is refused; the live in-memory ring instead evicts old events and
announces each evicted range (REQ-006). The schema and an illustrative example are
in [contracts/](contracts/).

**SC-001:** Given the schema and a corpus of valid and seeded invalid events, when
each line is validated, then valid lines pass and every line with an unknown kind,
a missing or non-false `executionAuthorization`, a crossing without an integer
class, an effort event with a class, a status outside its source enum, an
`evidenceRef` path that is absolute or contains `..`, a non-increasing `seq`,
duplicate JSON members, a non-finite number or an oversized line is refused with a
stable reason and no partial acceptance.

Verification: [procedure_001](validation-plan.md#procedure_001); T010.

### REQ-002 — Artifact adapters bound to evidence

Deterministic adapters translate, without recomputing or reinterpreting them:
analysis reports (report-level summary, uncertainty and limits; per pair the
classification, shared resources, reasons, constraints, evidence method, coverage,
rule set and compatibility class), Git replay plans, scheduler preparations (waves
and workers), runtime grants and phases, ownership pre-flight notices and receipts
read as JSON files, workflow-gate results and host stream events (`claude -p`
stream-json, `codex exec --json`). Each event carries an `evidenceRef` (artifact
path relative to its declared root, plus a SHA-256 of the artifact bytes). Events
the viewer derives rather than reads (a grant expiry observed after its recorded
validity) carry `derived: true`. Viewer modules do not import
`agent_braid.ownership` and contain no ownership command name.

**SC-002:** Given the owned fixtures for each artifact family, when each adapter
runs twice, then both outputs are byte-identical, every crossing equals one pair of
the source analysis with the same classification, shared resources, evidence block
and class, every status equals its source value, every event's `evidenceRef` hash
matches the artifact, and a static import check finds no ownership import in any
viewer module.

Verification: [procedure_002](validation-plan.md#procedure_002); T012–T014.

### REQ-003 — Absence never looks clean

`unknown` classifications, `not-observed` hazards, partial coverage, unparsed host
shapes, truncated streams and ring eviction are carried as events and rendered
distinctly from independent or clean results. `observation.gap` reasons form a
closed list: `subagent-usage-unattributed`, `stream-truncated`, `shape-unpinned`,
`ring-evicted`, `host-unverified`, `not-observed`.

**SC-003:** Given fixtures with each absence case, when they are adapted and the
viewer model is built, then each produces its event or gap, no absence case is
counted as independent, clean or conflict-free, and the counters report it
separately.

Verification: [procedure_003](validation-plan.md#procedure_003); T013, T020.

### REQ-004 — Loopback server boundary

`agent-braid view serve` binds only to `127.0.0.1` (or `::1`), prints a random
per-session token and serves every route under that token. Requests with a
non-loopback `Host` or `Origin`, a wrong token, an oversized body, a wrong content
type, duplicate JSON members or non-finite numbers are refused with the statuses in
the [UI, security and privacy contract](contracts/ui-security-privacy.md#refusal-statuses).
Responses carry the contract's Content Security Policy with no remote origins. The
server exposes no route that executes, schedules, grants, writes to a repository
or changes host configuration. Limits: 256 strands, 4 096 crossings, 64 waves,
1 024 grants, 8 concurrent subscribers; OTLP bodies at most 1 MiB and hook bodies
at most 256 KiB.

**SC-004:** Given a running server, when requests are sent with each refused
condition, when a ninth subscriber connects, and when the route table is listed,
then each is refused with its contract status and no state change, the socket is
bound to a loopback address only, and every route is read-only or an ingest route
that only appends events to memory.

Verification: [procedure_004](validation-plan.md#procedure_004); T016, T017.

### REQ-005 — Live host ingest with an attribute allowlist

The server accepts OTLP HTTP/JSON logs and metrics (Claude Code
`CLAUDE_CODE_ENABLE_TELEMETRY` export; Codex `[otel]` export), Claude Code HTTP
hook payloads and Codex `notify` or hook-shim posts. Only the attributes of the
canonical allowlist in the
[UI, security and privacy contract](contracts/ui-security-privacy.md#data-minimization)
keep their values. Identifiers are replaced by values salted per server session.
Prompt text, message text, tool input, tool output and file content are dropped
before storage. The names (never values) of dropped attributes are kept in a
bounded in-memory inventory for host verification. An unrecognized shape yields
`observation.gap` `shape-unpinned` instead of a guess.

**SC-005:** Given recorded payload fixtures for each host shape, including payloads
carrying prompt text, tool output and unknown attributes, when they are posted,
then only allowlisted attributes keep values in events, no dropped value is present
in the store, in any response or in any export, unknown attribute names appear only
in the names inventory, identifiers differ between two server sessions, and unknown
shapes produce a `shape-unpinned` gap.

Verification: [procedure_005](validation-plan.md#procedure_005); T018, T019.

### REQ-006 — Replay and live delivery

The same viewer consumes a recorded loom file (`--replay`) and the live store.
Server-Sent Events resume from `Last-Event-ID`; evicted events are announced by a
`ring-evicted` gap; `/snapshot` returns the current state. Artifact directories
named with `--watch` are polled with fixed bounds: at most 8 roots, 4 096 files,
16 MiB read per file, known artifact names only, every 500 ms.

**SC-006:** Given a replay file, a watched fixture directory and a live store fed
by fixtures, when a client connects, disconnects and resumes with `Last-Event-ID`,
when the ring overflows, and when a watched root exceeds a bound, then the client
receives every retained event exactly once in `seq` order, receives a gap for
evicted ranges, the exceeded bound yields a `stream-truncated` gap, and the replay
and live views of the same events produce identical viewer models.

Verification: [procedure_006](validation-plan.md#procedure_006); T015, T017.

### REQ-007 — Ephemeral effort and explicit recording

Effort data (tokens, cost, durations) lives in process memory, is labeled
`basis: host-estimate`, uses relative monotonic time and is never written to the
SPEC-047 telemetry store or to a repository. `serve` writes nothing unless the user
passes `--record FILE`, which writes the loom stream to a new private file outside
repositories (destination rules of REQ-008); effort events are recorded only with
the additional flag `--record-effort`.

**SC-007:** Given a session with effort samples, when the server stops after runs
without `--record`, with `--record` and with `--record --record-effort`, then the
first run created or modified no file, the second wrote only the named file without
effort events, the third wrote effort events labeled `host-estimate`, and the
telemetry store is byte-identical in all three.

Verification: [procedure_007](validation-plan.md#procedure_007); T019, T021.

### REQ-008 — Explicit, minimal export

`agent-braid view export --from FILE --to PATH` reads a recorded or replay loom
file and writes to a new private destination outside repositories, refusing
existing, symlinked, repository or public destinations as in SPEC-043. By default
it omits `effort.sample` events and absolute paths. Output is deterministic for
the same input.

**SC-008:** Given a recording with effort and path-bearing events, when export runs
twice to fresh destinations and once to each refused destination, then the two
outputs are byte-identical, contain no effort event and no absolute path, and each
refused destination is left untouched with a nonzero exit.

Verification: [procedure_008](validation-plan.md#procedure_008); T021.

### REQ-009 — Comparative effort evidence pack

With `--include-effort` and two or more `--arm NAME=FILE` recordings made with
`--record-effort`, export adds per-strand and per-phase effort, a summary and a
static HTML/SVG rendering without scripts or remote resources. Comparisons are
pairwise between a named baseline arm and each other arm. The pack records how each
arm was selected, states that arms are unmatched unless the owner records a
matching, and compares only fields present in both arms. Comparison rows use the
row shape of `agent-braid harness compare` (`field`, `left`, `right`), with
`identical` and `unlistedChange` at comparison level. Every figure is labeled
`host-estimate` and `empirical` and carries no compatibility class; the pack
states that it is not a speedup, saving or causal claim. Registering the pack as
a Braid Harness record kind is a HAR decision outside VIS.1. The contract is in
[contracts/effort-evidence-pack.md](contracts/effort-evidence-pack.md).

**SC-009:** Given three recorded arms, when the pack is exported with one baseline,
then it holds two pairwise comparisons in the harness row shape, every figure
carries its labels and no class, fields missing from an arm are listed and not
zero-filled, the arm selection notes and the unmatched statement are present, the
HTML contains no script element and no remote URL, and the summary contains the
non-claim statement.

Verification: [procedure_009](validation-plan.md#procedure_009); T022.

### REQ-010 — Web viewer bound to facts

The viewer renders strands, crossings, waves, grants, gates, hazards, effort and
gaps following the visual grammar in [research.md](research.md#visual-grammar).
Every visible element maps to one event; selecting it shows the event, its
compatibility class as a categorical label, shared resources, evidence method,
coverage, reasons, constraints, the report's uncertainty and limits, and the
`evidenceRef`. Only `independent-candidate` pairs are drawn as strand swaps;
ordered, conflicting and unknown pairs have their own glyphs and never look like a
clean swap; strands that pass between non-adjacent lanes are drawn as visibly
uncrossed bridges. Classes are shown categorically, never as a safety ordering, and
the legend states that a class is not a guarantee. Counters show only measures the
events support: conflicts flagged, ordered pairs, independent candidates, unknown
pairs, planned wave width against the serial fallback (advisory, not verified
safe), hazards, gaps, gates and grants. No counter shows speedup. Lane ordering is
a layout choice and never a braid simplification. Three.js is vendored at a pinned
version with a hash manifest; first-party files reference no remote origin and the
bundle performs no remote load. A text table view of the same model is available
without WebGL.

**SC-010:** Given the example loom file, when the viewer model is built and the
bundle is checked, then every rendered element has exactly one source event, every
event of a rendered kind has an element or a table row, no non-independent pair is
drawn as a swap, the vendored files match the manifest hashes, first-party files
contain no remote URL, `eval(` or `new Function`, no import, `src`, `href` or fetch
targets a remote origin, the CSP allows only `'self'` plus the hash of the single
import map, and the table view lists the same facts.

Verification: [procedure_010](validation-plan.md#procedure_010); T023–T026.

### REQ-011 — Configurable surfaces and pure frame rendering

`--surface web` is implemented in VIS.1; `mod`, `tui` and `mcp-app` are accepted
names that report "planned" without effect. A pure layout function produces the
same model as text (ASCII and braille), SVG and RGBA frames for later surfaces,
escaping terminal control characters. The host and surface matrix with statuses
`planned`, `hv-pending`, `verified` and `unobserved` is in
[contracts/surfaces-matrix.json](contracts/surfaces-matrix.json).

**SC-011:** Given the example model, when each frame format is rendered twice and
when an event carries control characters, then outputs are deterministic, control
characters are escaped, the SVG has no script, and planned surfaces exit with the
planned message and no side effect.

Verification: [procedure_011](validation-plan.md#procedure_011); T027, T028.

### REQ-012 — Command line and host configuration guidance

`agent-braid view` offers `serve` (with `--replay`, `--watch`, `--port`,
`--surface`, `--record` and `--record-effort`), `export` (with `--from`, `--to`,
`--include-effort`, `--arm` and `--baseline`), `validate` and `env`. `view env --host
claude|codex` prints the configuration a user may paste (OpenTelemetry endpoint,
HTTP hook entries, `[otel]` TOML) and writes nothing.

**SC-012:** Given each subcommand, when it runs with valid, invalid and missing
arguments, then exit codes and messages are stable, `env` writes no file, and the
printed configuration targets only the loopback endpoint with the session token
placeholder.

Verification: [procedure_012](validation-plan.md#procedure_012); T028.

### REQ-013 — Repository and governance boundaries

Viewer code lives in `agent_braid/view_*.py` and `integrations/agent-braid-view/`.
Network code exists only in `view_serve.py`. The plugin package and its tests are
unchanged. A validation rule `activity-viewer` classifies the new paths. The
vendored Three.js license is recorded in `LICENSE`, `LICENSES/` and
`docs/development/THIRD_PARTY.md` under ADR 0033.

**SC-013:** Given the change set, when governance, plugin package and validation
profile tests run, then they pass unchanged except for the added rule and its test,
no socket or HTTP import appears outside `view_serve.py`, every new path has
`activity-viewer` among its classifier matches with no unknown path, and the full
escalation set of each new path is recorded.

Verification: [procedure_013](validation-plan.md#procedure_013); T011, T029.

### REQ-014 — Host verification recorded separately

Before the documentation claims a host path works, an owner-run observation records
the Claude Code OpenTelemetry attribute names of the installed version, the Codex
`[otel]` export shape, loading of the loopback viewer in the Claude desktop browser
pane, and whether Codex Desktop renders MCP Apps (`unobserved` is a valid outcome).

**SC-014:** Given an owner-authorized probe per host, when it runs, then a receipt
records version, command, outcome and limits, and the surfaces matrix status changes
only from that receipt.

Verification: [procedure_014](validation-plan.md#procedure_014); T030–T033.

### REQ-015 — Documentation

English documentation (`docs/tooling/VIEWER.md`, tooling index, track pages)
describes installation, privacy, limits, host configuration, export and the
non-claims, and links the contract.

**SC-015:** Given the documentation, when it is searched, then it states loopback
only, read-only, ephemeral effort, default-minimal export, `host-estimate` labels,
no speedup claim and the HV status of each host, and every link resolves.

Verification: [procedure_015](validation-plan.md#procedure_015); T034.

## Scientific boundaries and compatibility

*Analogy*: the braid picture is a representation. Crossings encode only computed
pairwise classifications (Article 11); the picture adds no semantics and no braid
relation is applied. *Hypothesis* H-VIS1 (not a requirement): seeing the braid
shortens the time an operator needs to find a hazard or a conflicting pair compared
with reading the JSON receipt. It is the SPEC-043 comprehension hypothesis, still
unobserved; an optional owner-run observation is described in the validation plan,
and a null or inconclusive result is valid. *Empirical*: effort figures are host
estimates. *Formal*: none.

Domain: local machine, loopback, Agent Braid artifacts of the current contracts,
Claude Code and Codex telemetry shapes recorded in fixtures. Not covered in VIS.1:
transcripts, cloud sessions, IDE extensions, other hosts.

Compatibility: new contract `agent-braid-loom/v0.1`; new optional command group
`view`; no change to existing contracts, the plugin, the telemetry store or frozen
evidence. Python standard library only; Three.js is vendored static content, not a
Python dependency.

## Evidence and unresolved questions

Planned procedures are not obtained evidence; see [validation-plan.md](validation-plan.md)
and `assurance.json`. A throwaway spike (scratchpad only, 2026-10-31) produced 87
events from real repository computations and rendered them; it is design input in
[research.md](research.md), not evidence. Open decisions are listed in
[plan.md](plan.md#human-review-and-unresolved-decisions).
