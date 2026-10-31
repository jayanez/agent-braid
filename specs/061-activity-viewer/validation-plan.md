# SPEC-061 validation procedures

Each procedure records the command, candidate commit and artifact hashes,
environment, expected and actual outcome, negative controls and limits. None has
been run; this specification change only plans them. Owner-run host observations
stay separate from automated checks.

## procedure_001

Validate `contracts/loom-event.example.jsonl` and an owned corpus with
`view_loom.validate_event` and, as parity check, with the JSON schema. Negative
controls: unknown kind; `executionAuthorization` true or missing; crossing without
an integer class; effort or `analysis.report` event with a class; a gate status or
phase name outside the SPEC-052 enums; an evidence coverage value outside
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
shared resources, evidence block and class; one `analysis.report` per report with
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
requests without the token, with a wrong token, a foreign `Host`, a foreign
`Origin`, a wrong content type, an oversized body, duplicate members or `Infinity`
are refused with the contract status and the store is unchanged; a ninth SSE
subscriber gets 503; the route table equals the contract table; every response
carries the contract headers. Negative control: binding `0.0.0.0` is refused by the
constructor. Command: `python3 -m unittest tests.test_view_serve -v`.

## procedure_005

Post recorded OTLP JSON logs and metrics fixtures (Claude Code and Codex shapes),
Claude hook payloads and Codex notify payloads, including prompt text, tool input,
tool output and unknown attributes. Assert only allowlisted attributes keep values;
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
`stream-truncated` gap. Command: `python3 -m unittest tests.test_view_store
tests.test_view_serve -v`.

## procedure_007

With a temporary `HOME` and telemetry store, run a session with effort samples
three times: without `--record`, with `--record FILE`, and with `--record FILE
--record-effort`; then feed 50 001 events to a recording and assert it stops at
50 000 with a `stream-truncated` gap and stays replayable. Snapshot the file system before and after. Assert no file
changes in the first run, only the named file in the others, effort events only in
the third (labeled `host-estimate`), and identical telemetry store bytes. Command:
`python3 -m unittest tests.test_view_serve tests.test_view_export -v`.

## procedure_008

Export a recording twice to fresh private destinations and once each to an existing
path, a symlink, a path inside a Git repository and a group-readable parent. Assert
byte-identical outputs without effort events or absolute paths, and untouched
refused destinations with nonzero exit. Command:
`python3 -m unittest tests.test_view_export -v`.

## procedure_009

Export a pack with three recorded arms, one baseline and arm notes. Assert two
pairwise comparisons whose `differences` rows carry only `field`, `left` and
`right`, with `identical` and `unlistedChange` at comparison level; every effort
figure carries `host-estimate` and `empirical` and no class; fields absent from an
arm are `null` and never zero;
selection notes and the unmatched statement are present; `index.html` and
`braid.svg` contain no `<script` and no `http:` or `https:` URL; `summary.md`
contains the non-claim statement verbatim. Command:
`python3 -m unittest tests.test_view_export -v`.

## procedure_010

Build the model from `contracts/loom-event.example.jsonl`; assert a bijection between rendered
elements and source events of rendered kinds, that only `independent-candidate`
pairs become swaps, that non-adjacent pairs become bridges, that classes are
categorical labels, and that the table view lists the same facts. Check the
bundle: vendored files match `manifest.json` hashes (vendored content is checked by
hash only); first-party files contain no remote URL, `eval(`, `new Function` or
inline script other than the import map; no import, `src`, `href` or fetch in
first-party files or the import map targets a remote origin; the served CSP allows only `'self'` and the import-map hash.
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
codes and messages; assert `view env` writes nothing (file system snapshot) and
prints only loopback endpoints with a token placeholder. Command:
`python3 -m unittest tests.test_view_cli -v`.

## procedure_013

Run `python3 -m unittest tests.test_orchestration_governance tests.test_plugin_package
tests.test_validation_profiles tests.test_view_boundaries -v` and
`python3 scripts/validate_change.py --base develop --profile quick`. Assert the
plugin package is unchanged, no socket, HTTP or `urllib` import exists outside
`view_serve.py`, every new path has `activity-viewer` among its classifier matches,
and record the full escalation set of each new path (for example
`docs/tooling/VIEWER.md` also matches the AI tooling and contributor documentation
rules, and `examples/view/**` also matches the examples rule).

## procedure_014

Owner-run probes, one receipt each in `evidence/hv-*.json`, following
[host-verification-runbook.md](host-verification-runbook.md): Claude Code
OpenTelemetry attribute names (T030), Codex `[otel]` shape (T031), Claude desktop
browser pane loads the loopback viewer (T032), Codex Desktop MCP Apps rendering
(T033). Each receipt records host version, command, outcome, limits and the
surfaces-matrix status change it justifies. Command: the runbook steps; validation
of each receipt with `python3 -m scripts.validate_spec_kit`.

## procedure_015

Search the documentation for the required statements (loopback only, read-only,
ephemeral effort, explicit recording, minimal default export, `host-estimate`, no
speedup claim, HV status per host) and check every relative link resolves.
Command: `python3 -m unittest tests.test_view_docs -v` and
`python3 scripts/validate_repository.py`.

## procedure_hvis1 (optional, H-VIS1)

Owner-run, after VIS.1 is usable. On at least three recorded sessions with known
hazards or conflicting pairs, the owner times locating each one with the viewer and
with the JSON receipt, alternating order. Report raw times, order and limits.
Small, unblinded and self-observed: descriptive only; a null or inconclusive
result is valid and is not a VIS.1 acceptance condition. Command: none (manual
timing record in `evidence/hvis1-<yyyymmdd>.md`).
