# SPEC-061: Read-only local activity and concurrency viewer

**Track:** VIS.1 — Activity viewer (independent track; never a gate of the core,
of M4.x or of HAR)

**Status:** draft specification. The owner requested the direction and the
decisions below in the planning session of 2026-10-31. They are recorded here for
review and become accepted only through owner review T001; no separate approval
record exists yet. [ADR 0032](../../docs/adr/0032-activity-viewer-companion.md)
(companion boundary) and [ADR 0033](../../docs/adr/0033-vendored-threejs-mit-boundary.md)
(vendored third-party code, Three.js pinned at r186) were accepted on 2026-11-01,
so the ADR gates for implementation and vendoring are met. Nothing is implemented
by this change.

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
   where every visible element is bound to one event, and an element is shown as
   a verified fact only when the viewer itself re-hashed its source artifact;
4. keeps effort data (tokens, cost, durations) in memory, records it only on
   explicit request, and exports it only as a comparative evidence pack.

Claim level (Article 17): inspiration. The braid picture is a structural analogy
(Article 18) used as a representation; it is neither a formalism nor a theorem
claim. This is engineering work with one recorded open question (Q-VIS1) that is
not an acceptance condition. VIS.1 covers the contract, adapters, ingest, server, replay,
web viewer, export and pure text/SVG frame rendering, in two deliveries (below).
Later tracks are planned in [tracks.md](tracks.md); each may be re-scoped or closed
as Deferred only by an owner decision recorded at a checkpoint: VIS.2 (SPEC-062, Claude Code mod
pane), VIS.3 (SPEC-063, Codex hooks and `notify`, a Codex MCP App and a terminal
UI) and
VIS.4 (SPEC-064, other hosts such as Cursor, OpenCode and Pi).

Exclusions: no execution, scheduling, grant issuance, retry, cancellation or any
write to a repository, registry, run directory or host configuration; no change to
the analyzer, runtime, ownership commands, plugin package (`integrations/agent-braid/`),
portable MCP contract or SPEC-047 telemetry store; no remote service, upload,
account or network listener outside loopback; no claim of speedup, cost saving or
safety; no reading of prompts, messages or transcripts in VIS.1 beyond the
allowlisted usage and identifier fields of host stream events; no participation in
any host permission or tool decision.

## Deliveries and checkpoint

VIS.1 is one milestone with two deliveries:

- **VIS.1a — coordination slice:** owner-run host probes and an artifact census
  first, then the contract, coordination adapters (analysis, plans, scheduler,
  grants, runtime, ownership, workflow gate), store, loopback server, Server-Sent
  Events, `--watch` and replay, observational Claude Code hooks, the table view
  and evidence panel, the Three.js scene (with ADR 0033), `serve`, `validate` and
  `env --host claude`. REQ-001 to REQ-004, REQ-006, REQ-010, REQ-013 to REQ-015,
  the hook part of REQ-005 and the matching parts of REQ-011 and REQ-012.
- **VIS.1b — effort, recording, export and frames:** host stream adapters, OTLP
  ingest, recording, export, the effort evidence pack and text, braille, SVG and
  RGBA frames. REQ-007 to REQ-009, the OTLP part of REQ-005, the host stream part
  of REQ-002 and the remaining parts of REQ-011 and REQ-012.

After VIS.1a the owner holds a go/no-go checkpoint (T035) by a date set in T001:
the census result against a threshold set in T001, a descriptive Q-VIS1
observation on real or census sessions, and a recorded decision to keep,
re-scope or close as Deferred VIS.1b and VIS.2–VIS.4. If the date passes without a
VIS.1a slice, VIS.1 closes as Deferred. An ingest path whose host probe does not
match its documentation is removed from VIS.1 and marked `not-matching`.

## Authorities

Constitution clause zero and Articles 6, 11, 13, 14, 17, 18, 19, 20, 21, 22 and
24;
[GOVERNANCE.md](../../GOVERNANCE.md) (license boundary, public contract change);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md); ADR 0012, ADR 0021,
ADR 0024 and ADR 0029 (no hooks, mods, monitors, agents or channels in the plugin
package); ADR 0032 and ADR 0033 (accepted 2026-11-01); SPEC-039
[program](../039-ai-tooling-program/program.md) route "Embedded visual
interaction"; SPEC-043 presentation layer; SPEC-047
[data contract](../047-local-technical-telemetry/data-contract.md) and
[telemetry policy](../../docs/tooling/TELEMETRY.md); the SPEC-057 never-collect
list, which is scoped to telemetry about the SPEC-057 commands. This viewer writes
no telemetry, but it does not follow the same minimization: it holds several
never-collect categories in memory and, on explicit request, on disk. Each
deviation is listed in the
[deviation table](contracts/ui-security-privacy.md#deviations-from-the-never-collect-list).

## Owner decisions requested (pending T001)

| ID | Decision requested on 2026-10-31 |
|---|---|
| D1 | The viewer is an opt-in companion inside this repository, never inside the `agent-braid` plugin package. |
| D2 | First surface: web 3D with Three.js on loopback. The Claude Code mod pane, a terminal UI and a Codex MCP App are planned; the surface is selectable by configuration; the design stays host-agnostic for Cursor, OpenCode, Pi and others. Vendoring Three.js is conditional on ADR 0033; without it VIS.1 ships the table view and SVG frames only. |
| D3 | Live-capable from VIS.1: contract, loopback server, Server-Sent Events, `--watch`, observational Claude Code HTTP hooks, replay and the web viewer in VIS.1a; OTLP/JSON ingest for Claude Code and Codex in VIS.1b (amended 2026-10-31 after the counterfactual review). |
| D4 | Effort data is ephemeral in memory. Export omits it by default; `--include-effort` builds, in VIS.1b, a comparative evidence pack aligned with `agent-braid harness compare`, so recorded sessions can be compared as host estimates. Presenting a pack as evidence of Agent Braid's effect is a public claim under GOVERNANCE.md. |
| D5 | Track documentation (ROADMAP, STATUS, milestone index, program, GitHub tracking) is updated from the start. |
| D6 | Tracking as independent track VIS.1–VIS.4, with GitHub milestone, issues and Project 6 entries created through the reviewed tracking reconciliation after merge. VIS.1 is one milestone with deliveries VIS.1a and VIS.1b and a go/no-go checkpoint between them (amended 2026-10-31). |

## Requirements and acceptance scenarios

### REQ-001 — Versioned event contract

Every event is one JSON object per line with `schemaVersion`
`agent-braid-loom/v0.1`, a strictly increasing integer `seq`, a `kind` from a
closed list, a relative monotonic time `at` (`relMs`, `basis`), a `source`
(`adapter`, `evidenceRef`, `host`, `verification`), an `assurance` block
(`compatibilityClass`, `notAGuarantee: true`) and `executionAuthorization`
fixed to `false`. `compatibilityClass` is the Article 13 class declared by the
per-pair analysis fact a crossing carries, `0` for workflow-gate results (their
source declares `0-heuristic`) and `null` for every other kind. `verification`
(`rehashed`, `unverified`, `derived`) is assigned by the viewer when it ingests an
event and is never trusted from a file or a post. Free-text fields reject C0 and
C1 control characters, DEL and bidirectional overrides. Source identifiers such as `sha256:` analysis and plan
digests are carried verbatim. The closed kinds are `session.origin`,
`analysis.report`, `strand.open`, `strand.update`, `strand.close`,
`crossing.classified`, `wave.planned`, `wave.started`, `wave.finished`,
`grant.issued`, `grant.consumed`, `grant.expired`, `grant.refused`,
`hazard.noticed`, `gate.phase`, `gate.result`, `runtime.phase`, `effort.sample`
and `observation.gap`. Status, mode, action and phase values are copied verbatim
from their source contracts (for example the six Git runtime phases). Lines are at
most 16 KiB. A file with more than 50 000 events is refused; the live in-memory ring instead evicts old events and
announces each evicted range (REQ-006). The schema and an illustrative example are
in [contracts/](contracts/).

**SC-001:** Given the schema and a corpus of valid and seeded invalid events, when
each line is validated, then valid lines pass and every line with an unknown kind,
a missing or non-false `executionAuthorization`, a crossing without an integer
class, a gate result with a class other than 0, an effort event with a class, a
status, action or phase outside its source enum, free text with a control or
bidirectional-override character,
an `evidenceRef` path that is absolute, has a drive prefix or contains `..`,
`notAGuarantee` false, a non-increasing `seq`,
duplicate JSON members, a non-finite number or an oversized line is refused with a
stable reason and no partial acceptance.

Verification: [procedure_001](validation-plan.md#procedure_001); T010.

### REQ-002 — Artifact adapters bound to evidence

Deterministic adapters translate, without recomputing or reinterpreting them:
analysis reports (report-level summary, uncertainty and limits; per pair the
classification, shared resources, reasons, constraints, evidence method, coverage,
rule set and compatibility class), Git replay plans, scheduler preparations (waves
and workers), runtime grants and phases, ownership pre-flight notices and receipts
read as JSON files, workflow-gate phases and results (gate pairs carry no
per-pair evidence block and are not drawn as crossings) and host stream events
(`claude -p` stream-json, `codex exec --json`) through a field allowlist that
keeps only usage counts, model and identifiers. Each event carries an
`evidenceRef` (artifact path relative to its declared root, plus a SHA-256 of the
artifact bytes) and `verification: rehashed`. Events the viewer derives rather
than reads (a grant expiry observed after its recorded validity) carry
`derived: true` and `verification: derived`. Each adapter lists the source schema
versions it supports; another version yields a `source-unsupported` gap instead
of a guess. Grants keep the source `action`;
hazards keep every unit they name; runtime phases keep the `manifestDigest`;
scheduler waves keep the `scheduleDigest` and are joined to a Git plan only where
an artifact records the join. A pair whose shared resources, reasons or
constraints exceed the per-field caps is not emitted; a `stream-truncated` gap
names its report instead. Viewer modules do not import
`agent_braid.ownership` and contain no ownership command name.

**SC-002:** Given the owned fixtures for each artifact family, when each adapter
runs twice, then both outputs are byte-identical, every crossing equals one pair of
the source analysis with the same classification, shared resources, evidence block
and class, every oversized pair is replaced by a `stream-truncated` gap, every
status, action and phase equals its source value, every hazard keeps all its units,
host stream messages, prompts and tool data are absent, every event's `evidenceRef` hash
matches the artifact, and a static import check finds no ownership import in any
viewer module.

Verification: [procedure_002](validation-plan.md#procedure_002); T012–T014.

### REQ-003 — Absence never looks clean

`unknown` classifications, `not-observed` hazards, partial coverage, unparsed host
shapes, truncated streams and ring eviction are carried as events and rendered
distinctly from independent or clean results. `observation.gap` reasons form a
closed list: `subagent-usage-unattributed`, `stream-truncated`, `shape-unpinned`,
`source-unsupported`, `ring-evicted`, `host-unverified`, `not-observed`.

**SC-003:** Given fixtures with each absence case, when they are adapted and the
viewer model is built, then each produces its event or gap, no absence case is
counted as independent, clean or conflict-free, and the counters report it
separately.

Verification: [procedure_003](validation-plan.md#procedure_003); T013, T020.

### REQ-004 — Loopback server boundary

`agent-braid view serve` binds only to `127.0.0.1` (or `::1`) and uses two
per-session credentials with separate rights: a one-time open code, printed at
start, that the browser exchanges once for an `HttpOnly`, `SameSite=Strict`
session cookie granting read routes only; and an ingest token, written to a new
owner-only file and sent by host exporters as an `Authorization: Bearer` header,
granting ingest routes only. No credential remains in a URL after the exchange,
in an access log or in printed host configuration. Requests with a `Host` other
than the bound loopback names, a foreign `Origin`, a cross-site `Sec-Fetch-Site`,
a missing or wrong credential, an oversized body, a missing `Content-Length`, a
content encoding other than identity, a wrong content type, duplicate JSON members
or non-finite numbers are refused with the statuses in the
[UI, security and privacy contract](contracts/ui-security-privacy.md#refusal-statuses).
Responses carry the contract's Content Security Policy with no remote origins.
Every response to a hook route has an empty body. The server exposes no route
that executes, schedules, grants, writes to a repository or changes host
configuration. Limits: 256 strands, 4 096 crossings, 64 waves, 1 024 grants,
8 concurrent subscribers, 32 concurrent connections and a 10-second socket
timeout; OTLP bodies at most 1 MiB and hook bodies at most 256 KiB. Input beyond a per-kind cap (for example a report with more than
4 096 pairs) is not stored and is announced by a `stream-truncated` gap.

**SC-004:** Given a running server, when requests are sent with each refused
condition, when a ninth subscriber connects, when the open code is reused, when the
read cookie is used on an ingest route and the ingest token on a read route, and
when the route table is listed, then each is refused with its contract status and
no state change, every hook response body is empty, no access log line is
written, the socket is bound to a loopback address only, and every route is
read-only or an ingest route that only appends events to memory.

Verification: [procedure_004](validation-plan.md#procedure_004); T016, T017.

### REQ-005 — Live host ingest with an attribute allowlist

The server accepts OTLP HTTP/JSON logs and metrics (Claude Code
`CLAUDE_CODE_ENABLE_TELEMETRY` export; Codex `[otel]` export) and Claude Code HTTP
hook payloads for observational events only (`SessionStart`, `SessionEnd`,
`SubagentStart`, `SubagentStop`, `PostToolUse`). Decision events such as
`PreToolUse`, `PermissionRequest`, `UserPromptSubmit` and `Stop` are refused, and
the viewer never takes part in a host decision. Codex `notify` and command hooks
need a local shim and belong to VIS.3. Only the attributes of the canonical
allowlist in the
[UI, security and privacy contract](contracts/ui-security-privacy.md#data-minimization)
keep their values, at every OTLP level (resource, scope, record and data point);
log bodies are dropped and only the event name is kept; kept values are
length-bounded and follow the free-text rule. Identifiers are replaced by values salted per server session.
Prompt text, message text, tool input, tool output and file content are dropped
before storage. The names (never values) of dropped attributes are kept in a
bounded in-memory inventory for host verification. An unrecognized shape yields
`observation.gap` `shape-unpinned` instead of a guess.

**SC-005:** Given recorded payload fixtures for each host shape, including payloads
carrying prompt text, tool output and unknown attributes, when they are posted,
then only allowlisted attributes keep values in events, decision hook events are
refused with an empty body, log bodies are absent, no dropped value is present
in the store, in any response or in any export, unknown attribute names appear only
in the names inventory, identifiers differ between two server sessions, and unknown
shapes produce a `shape-unpinned` gap.

Verification: [procedure_005](validation-plan.md#procedure_005); T018, T019.

### REQ-006 — Replay and live delivery

The same viewer consumes a recorded loom file (`--replay`) and the live store.
Server-Sent Events resume from `Last-Event-ID`; evicted events are announced by a
`ring-evicted` gap; `/snapshot` returns the current state. Artifact directories
named with `--watch` are polled with fixed bounds: at most 8 roots, 4 096 files,
16 MiB read per file, known artifact names only, regular files opened without
following symbolic links and resolving inside their root, every 500 ms. Replayed
events and adapter events whose artifact cannot be re-hashed are marked
`unverified` and rendered with a distinct unverified marker.

**SC-006:** Given a replay file, a watched fixture directory and a live store fed
by fixtures, when a client connects, disconnects and resumes with `Last-Event-ID`,
when the ring overflows, and when a watched root exceeds a bound, then the client
receives every retained event exactly once in `seq` order, receives a gap for
evicted ranges, the exceeded bound yields a `stream-truncated` gap, a symbolic link
in a watched root is not read, every replayed event is `unverified`, and the replay
and live views of the same events produce identical viewer models.

Verification: [procedure_006](validation-plan.md#procedure_006); T015, T017.

### REQ-007 — Ephemeral effort and explicit recording

Effort data (tokens, cost, durations) lives in process memory, is labeled
`basis: host-estimate`, uses relative monotonic time and is never written to the
SPEC-047 telemetry store or to a repository. `serve` writes nothing unless the user
passes `--record FILE`, which writes the loom stream to a new private file outside
repositories (destination rules of REQ-008); effort events are recorded only with
the additional flag `--record-effort`. A recording holds at most 49 999 events
followed by one `stream-truncated` gap, so every recording stays replayable and
exportable. Recording files are created exclusively, without following a symbolic
link, with owner-only permissions.

**SC-007:** Given a session with effort samples, when the server stops after runs
without `--record`, with `--record` and with `--record --record-effort`, then the
first run created or modified no file, the second wrote only the named file without
effort events, the third wrote effort events labeled `host-estimate`, and the
telemetry store is byte-identical in all three.

Verification: [procedure_007](validation-plan.md#procedure_007); T039, T021.

### REQ-008 — Explicit, minimal export

`agent-braid view export --from FILE --to PATH` reads a recorded or replay loom
file and writes to a new private destination outside repositories, refusing
existing, symlinked, repository or public destinations as in SPEC-043, and creates
the destination exclusively with owner-only permissions. By default it omits
`effort.sample` events and replaces absolute-path-like values in every string
field with a fixed marker. Output is deterministic for the same input.

**SC-008:** Given a recording with effort and path-bearing events, when export runs
twice to fresh destinations and once to each refused destination, then the two
outputs are byte-identical, contain no effort event and no absolute path in any
field (including paths seeded in free-text fields), and each
refused destination is left untouched with a nonzero exit.

Verification: [procedure_008](validation-plan.md#procedure_008); T021.

### REQ-009 — Comparative effort evidence pack

With `--include-effort`, a `--baseline NAME` and two or more `--arm NAME=FILE`
recordings made with `--record-effort`, each with an `--arm-note NAME=TEXT`
selection note, export adds effort totals per arm, strand, host and model, a
summary and a static HTML/SVG rendering without scripts or remote resources. Arm
names match `[A-Za-z0-9_-]{1,32}`. All text in HTML, SVG and Markdown outputs is
escaped, `index.html` carries a restrictive meta Content Security Policy, and
`summary.md` contains no link or image syntax. The non-claim statement and the
`host-estimate` label appear in `index.html` and in every SVG chart as well as in
`summary.md` and `manifest.json`. Comparisons are
pairwise between the baseline arm and each other arm. The pack records how each
arm was selected and states that arms are unmatched unless the owner records a
matching. Each comparison uses the shape of `agent-braid harness compare`: a
`differences` list of `{field, left, right}` rows, where a field absent from one
arm appears as `null` on that side and never as zero, and comparison-level
`identical` and `unlistedChange`. Every figure is labeled
`host-estimate` and `empirical` and carries no compatibility class; the pack
states that it is not a speedup, saving or causal claim. Registering the pack as
a Braid Harness record kind is a HAR decision outside VIS.1. The contract is in
[contracts/effort-evidence-pack.md](contracts/effort-evidence-pack.md).

**SC-009:** Given three recorded arms, when the pack is exported with one baseline,
then it holds two pairwise comparisons in the harness comparison shape, every
figure carries its labels and no class, fields missing from an arm appear as
`null` and never as zero, the arm selection notes and the unmatched statement are
present, for a corpus of hostile text inputs the HTML and SVG contain no script
element, event-handler attribute, `javascript:` URL or remote URL and the Markdown
renders the text inertly, and the summary, `index.html` and every SVG chart
contain the non-claim statement.

Verification: [procedure_009](validation-plan.md#procedure_009); T022.

### REQ-010 — Web viewer bound to facts

The viewer renders strands, crossings, waves, grants, gates, hazards, effort and
gaps following the visual grammar in [research.md](research.md#visual-grammar).
Every visible element maps to one event; selecting it shows the event, its
compatibility class as a categorical label, shared resources, evidence method,
coverage, reasons, constraints, the report's uncertainty and limits, the
`evidenceRef` and its verification status. Unverified crossings and gate results
carry a distinct unverified marker. Only `independent-candidate` pairs are drawn as strand swaps;
ordered, conflicting and unknown pairs have their own glyphs and never look like a
clean swap; strands that pass between non-adjacent lanes are drawn as visibly
uncrossed bridges. Classes are shown categorically, never as a safety ordering, and
the legend states that a class is not a guarantee. Counters show only measures the
events support: conflicts flagged, ordered pairs, independent candidates, unknown
pairs, planned wave width shown alone and labeled "advisory plan, not a runtime
measurement", hazards, gaps, gates and grants. No counter shows speedup or a ratio
against serial execution. Lane ordering is
a layout choice and never a braid simplification. Three.js is vendored at a pinned
version with a hash manifest; first-party files reference no remote origin and the
bundle performs no remote load. If ADR 0033 is not accepted, the table view and
SVG frames are the VIS.1 surface. A text table view of the same model is available
without WebGL.

**SC-010:** Given `contracts/loom-event.example.jsonl`, when the viewer model is built and the
bundle is checked, then every rendered element has exactly one source event, every
event of a rendered kind has an element or a table row, no non-independent pair is
drawn as a swap, the vendored files match the manifest hashes, first-party files
contain no remote URL, `eval(` or `new Function`, no import, `src`, `href` or fetch
in first-party files or the import map targets a remote origin, the CSP names no
remote origin and allows no inline script other than the hash of the single import
map, unverified elements carry the unverified marker, and the table view lists the
same facts.

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
`--include-effort`, `--arm`, `--arm-note` and `--baseline`), `validate` and `env`.
`view env --host claude|codex` prints configuration a user may paste into
user-level host settings (OpenTelemetry endpoint with an `Authorization` header
read from the ingest-token file at shell start, observational HTTP hook entries for
Claude Code, `[otel]` TOML for Codex) and writes nothing. The printed
configuration never contains a credential value and is never meant for repository
settings.

**SC-012:** Given each subcommand, when it runs with valid, invalid and missing
arguments, then exit codes and messages are stable, `env` writes no file, and the
printed configuration targets only the loopback endpoint, contains no credential
value and names no decision hook event.

Verification: [procedure_012](validation-plan.md#procedure_012); T028.

### REQ-013 — Repository and governance boundaries

Viewer code lives in `agent_braid/view_*.py` and `integrations/agent-braid-view/`.
Network code exists only in `view_serve.py`. The plugin package and its tests are
unchanged. A validation rule `activity-viewer` classifies the new paths. The
vendored Three.js license is recorded in `LICENSE`, `LICENSES/` and
`docs/development/THIRD_PARTY.md` under ADR 0033.

**SC-013:** Given the change set, when governance, plugin package and validation
profile tests run, then they pass unchanged except for the added rule and its test,
no socket or HTTP import appears outside `view_serve.py`, every new viewer code,
test, asset and documentation path has `activity-viewer` among its classifier
matches with no unknown path (license files and evidence receipts keep their
existing classification), and the full escalation set of each new path is
recorded.

Verification: [procedure_013](validation-plan.md#procedure_013); T011, T029.

### REQ-014 — Host verification recorded separately

Owner-run probes run before the matching ingest code is written, with a throwaway
listener and no viewer code; an ingest path whose probe does not match is removed
from VIS.1 and marked `not-matching`. Before the documentation claims a host path
works, an owner-run observation records
the Claude Code OpenTelemetry attribute names of the installed version, the Codex
`[otel]` export shape, loading of the loopback viewer in the Claude desktop browser
pane, that empty-bodied HTTP hook responses are non-blocking in the installed
Claude Code version, and whether Codex Desktop renders MCP Apps (`unobserved` is a
valid outcome).

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

Verification: [procedure_015](validation-plan.md#procedure_015); T034, T035.

## Scientific boundaries and compatibility

*Analogy* (Article 18; claim level inspiration under Article 17): the braid
picture is a representation. Crossings encode only computed pairwise
classifications (Article 11); the picture adds no semantics and no braid relation
is applied. A drawn swap or wave is not permission to interleave (Article 6).
*Open question* Q-VIS1 (neither a hypothesis nor a requirement): does seeing the
braid shorten the time an operator needs to find a hazard or a conflicting pair
compared with reading the JSON receipt? It restates the SPEC-043 comprehension
question, has no falsification condition yet and supports no claim; an optional
owner-run descriptive observation is described in the validation plan, and a null
or inconclusive result is valid. *Empirical*: effort figures are host
estimates. *Formal*: none.

Domain: local machine, loopback, Agent Braid artifacts of the current contracts,
Claude Code and Codex telemetry shapes recorded in fixtures. Not covered in VIS.1:
transcripts, Codex hooks and `notify`, cloud sessions, IDE extensions, other
hosts.

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
