# SPEC-061 validation procedures

Each procedure records the command, candidate commit and artifact hashes,
environment, expected and actual outcome, negative controls and limits. None has
been run; this specification change only plans them. Owner-run host observations
stay separate from automated checks.

## procedure_001

Validate `contracts/loom-event.example.jsonl` and an owned corpus with
`view_loom.validate_event` and, as parity check, with the JSON schema. Negative
controls: unknown kind; `executionAuthorization` true or missing; crossing without
an integer class; effort or `analysis.report` event with a class; a gate result
with a class other than 0; a gate status or phase name outside the SPEC-052 enums;
a runtime phase outside the six Git runtime phases; a grant action outside
`execute`, `resume`, `abort`; free text with a C0 or C1 control character, DEL or
a bidirectional override; a missing `source.verification`; an evidence coverage value outside
`complete`, `partial`, `unknown`; an identifier that is neither a short ID nor a
`sha256:` digest; an `evidenceRef` path that is absolute, has a drive prefix or contains `..`;
`notAGuarantee` false; repeated or decreasing `seq`; duplicate members; `NaN`; a
16 KiB + 1 line; a file with 50 001 events. Each is refused with a stable reason;
no prefix of a refused stream is accepted as complete.
Command: `python3 -m unittest tests.test_view_loom -v`.

## procedure_002

Run every adapter twice on owned fixtures (analysis of
`examples/analysis/file-edits.json`, a Git replay plan, scheduler preparations
built as in `tests/test_m4_alpha_scheduler.py`, an operator grant, runtime
`state.json`, ownership pre-flight notice and receipt JSON from SPEC-057 fixtures,
SPEC-052 gate results, stream-json and `codex exec --json` fixtures). Assert
byte-identical output; one crossing per analysis pair with equal classification,
shared resources, evidence block and class, or a `stream-truncated` gap for a pair
over the per-field caps; no crossing from gate results; every hazard unit kept;
grant actions, runtime phases and `manifestDigest` equal to their sources; no
message, prompt or tool field from host streams; `verification: rehashed` on
adapter events; one `analysis.report` per report with
its uncertainty and limits; statuses and modes equal to their source values; and
matching `evidenceRef` hashes. An AST check asserts no viewer module imports
`agent_braid.ownership` or contains an ownership command name. Negative controls: a
tampered artifact byte changes the hash; a reclassified pair or a remapped status
fails. Command: `python3 -m unittest tests.test_view_adapters -v`.

## procedure_003

Adapt fixtures with an `unknown` pair, a `partial-coverage` and a `not-observed`
hazard, an unparsed host line, a truncated stream and an overflowing ring. Assert
each yields its event or gap and that model counters count none of them as
independent or clean. Negative control: a model that drops gaps fails.
Command: `python3 -m unittest tests.test_view_adapters tests.test_view_model -v`.

## procedure_004

Start the server on an OS-assigned port. Assert the bound address is loopback;
requests without a credential, with a wrong credential, a reused open code, the
read cookie on an ingest route, the ingest token on a read route, a foreign `Host`,
a foreign `Origin`, a cross-site `Sec-Fetch-Site`, a wrong content type, a gzip
content encoding, a missing `Content-Length`, an oversized body, duplicate members,
`Infinity`, `1e400` or 10 000 nested arrays are refused with the contract status
and the store is unchanged; the open code exchange sets an `HttpOnly`,
`SameSite=Strict` cookie and redirects to a URL without the code; no access log
line is written; `/web/` serves only manifest-listed files; a ninth SSE
subscriber gets 503; the route table equals the contract table; every response
carries the contract headers. Negative control: binding `0.0.0.0` is refused by the
constructor. Command: `python3 -m unittest tests.test_view_serve -v`.

## procedure_005

Post recorded OTLP JSON logs and metrics fixtures (Claude Code and Codex shapes,
with sentinel values in resource, scope, record and data-point attributes and in
log bodies) and Claude hook payloads for observational and decision events,
including prompt text, tool input, tool output, `transcript_path` and unknown
attributes. Assert every hook response body is empty; decision events are refused
with 403; only allowlisted attributes keep values; no log body is kept;
a search of the store, `/snapshot`, `/events`, recordings and exports for the
sentinel values finds none; unknown attribute names appear only in the names
inventory; identifiers differ across two server sessions; unknown shapes produce
`shape-unpinned`. Negative control: a fixture with a new attribute name keeps no
value. Command: `python3 -m unittest tests.test_view_otlp tests.test_view_hooks -v`.

## procedure_006

Replay `examples/view/loom-replay.jsonl`; connect, read N events, disconnect,
resume with `Last-Event-ID`. Assert exactly-once, ordered delivery and a
`ring-evicted` gap after overflow; assert the replay model equals the live model fed
the same events. Watch a fixture root, then exceed each `--watch` bound and assert a
`stream-truncated` gap; place a symbolic link to a file outside the root under a
known artifact name and assert it is not read; assert every replayed event is
`unverified`. Command: `python3 -m unittest tests.test_view_store
tests.test_view_serve tests.test_view_tail -v`.

## procedure_007

With a temporary `HOME` and telemetry store, run a session with effort samples
three times: without `--record`, with `--record FILE`, and with `--record FILE
--record-effort`; then feed 50 001 events to a recording and assert it holds
49 999 events plus one `stream-truncated` gap and stays replayable; assert the
recording file has owner-only permissions and that a symbolic link placed at the
destination is refused. Snapshot the file system before and after. Assert no file
changes in the first run, only the named file in the others, effort events only in
the third (labeled `host-estimate`), and identical telemetry store bytes. Command:
`python3 -m unittest tests.test_view_serve tests.test_view_export -v`.

## procedure_008

Export a recording twice to fresh private destinations and once each to an existing
path, a symlink, a path inside a Git repository and a group-readable parent. Seed
absolute paths in labels, shared resources and reasons. Assert byte-identical
outputs without effort events or absolute paths in any field, owner-only
permissions, and untouched refused destinations with nonzero exit. Command:
`python3 -m unittest tests.test_view_export -v`.

## procedure_009

Export a pack with three recorded arms, one baseline and arm notes. Assert two
pairwise comparisons whose `differences` rows carry only `field`, `left` and
`right`, with `identical` and `unlistedChange` at comparison level; every effort
figure carries `host-estimate` and `empirical` and no class; fields absent from an
arm are `null` and never zero;
selection notes and the unmatched statement are present; an arm name outside
`[A-Za-z0-9_-]{1,32}` is refused. With a hostile corpus in labels, reasons and arm
notes (`<script>`, `<img src=x onerror=...>`, `<svg onload=...>`, `javascript:`,
`<meta http-equiv=refresh>`, Markdown links and images, bidirectional overrides),
`index.html` and `braid.svg` contain no script element, event-handler attribute,
`javascript:` URL or `http:`/`https:` URL, `index.html` carries the meta policy,
and `summary.md` renders every payload as inert text; `summary.md` contains the
non-claim statement verbatim. Command:
`python3 -m unittest tests.test_view_export -v`.

## procedure_010

Build the model from `contracts/loom-event.example.jsonl`; assert a bijection between rendered
elements and source events of rendered kinds, that only `independent-candidate`
pairs become swaps, that non-adjacent pairs become bridges, that classes are
categorical labels, that unverified crossings and gate results carry the
unverified marker, that no counter shows a ratio against serial execution, and
that the table view lists the same facts. Check the
bundle: vendored files match `manifest.json` hashes (vendored content is checked by
hash only); first-party files contain no remote URL, `eval(`, `new Function` or
inline script other than the import map; no import, `src`, `href` or fetch in
first-party files or the import map targets a remote origin; the served CSP names
no remote origin, allows no inline script other than the import-map hash and
requires trusted types.
Command: `python3 -m unittest tests.test_view_model tests.test_view_web_bundle -v`.
Manual check, recorded separately: open the replay in a browser and confirm that
selecting each element shows its event and `evidenceRef`, with no CSP violation
(screenshot plus notes; not a substitute for tests).

## procedure_011

Render ASCII, braille, SVG and RGBA frames twice from the example model; assert
determinism, escaped control characters, no script in SVG; run `--surface mod`,
`tui` and `mcp-app` and assert the planned message, exit code and no side effect.
Command: `python3 -m unittest tests.test_view_render tests.test_view_cli -v`.

## procedure_012

Run each `view` subcommand with valid, invalid and missing arguments; assert exit
codes and messages; assert `view env` writes nothing (file system snapshot),
prints only loopback endpoints, contains no credential value (the ingest token is
read from its file by the printed shell snippet) and names no decision hook
event. Command:
`python3 -m unittest tests.test_view_cli -v`.

## procedure_013

Run `python3 -m unittest tests.test_orchestration_governance tests.test_plugin_package
tests.test_validation_profiles tests.test_view_boundaries -v` and
`python3 scripts/validate_change.py --base develop --profile quick`. Assert the
plugin package is unchanged, no socket, HTTP or `urllib` import exists outside
`view_serve.py`, every new viewer code, test, asset and documentation path has
`activity-viewer` among its classifier matches (license files and evidence
receipts keep their existing classification),
and record the full escalation set of each new path (for example
`docs/tooling/VIEWER.md` also matches the AI tooling and contributor documentation
rules, and `examples/view/**` also matches the examples rule).

## procedure_014

Owner-run probes before the matching code, one receipt each in
`evidence/hv-*.json`, following
[host-verification-runbook.md](host-verification-runbook.md): Claude Code
OpenTelemetry attribute names and non-blocking empty hook responses (T030), Codex
`[otel]` shape (T031), Claude desktop browser pane loads a static loopback fixture
page (T032), Codex Desktop MCP Apps rendering (T033). A `not-matching` receipt
removes that ingest path from VIS.1. The end-to-end viewer is opened in the pane
again at the T035 checkpoint (manual part of procedure_010). Each receipt records host version, command, outcome, limits and the
surfaces-matrix status change it justifies. Command: the runbook steps; the
owner reviews each receipt and `tests/test_view_docs.py` checks that every
receipt has the required fields and that matrix statuses match receipts.

## procedure_015

Search the documentation for the required statements (loopback only, read-only,
ephemeral effort, explicit recording, minimal default export, `host-estimate`, no
speedup claim, HV status per host) and check every relative link resolves.
Command: `python3 -m unittest tests.test_view_docs -v` and
`python3 scripts/validate_repository.py`.

## procedure_census (T038)

Owner-run before T012. Count, for the owner's sessions and run directories of the
last four weeks, those that contain each coordination artifact kind (analysis
report, plan, scheduler preparation, grant, ownership notice or receipt, gate
result). Record counts and kinds only, no content or paths, in
`evidence/census-<date>.json`, with the OD-8 threshold and whether it was met. A
result below the threshold is reported at T035 and may re-scope VIS.1 to replay of
curated artifacts.

## procedure_hvis1 (Q-VIS1, at the T035 checkpoint)

Owner-run, after the VIS.1a slice, on real or census sessions. On at least three recorded sessions with known
hazards or conflicting pairs, the owner times locating each one with the viewer and
with the JSON receipt, alternating order. Report raw times, order and limits.
Small, unblinded and self-observed: descriptive only; a null or inconclusive
result is valid and is not a VIS.1 acceptance condition. The checkpoint record
`evidence/checkpoint-<date>.md` adds the census result and the owner's decision
(keep, re-scope or close as Deferred) for VIS.1b and VIS.2–VIS.4. Command: none (manual
timing record in `evidence/hvis1-<yyyymmdd>.md`).
