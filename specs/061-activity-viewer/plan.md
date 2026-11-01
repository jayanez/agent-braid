# SPEC-061 implementation plan

## Technical context and scope

- Python 3.12+, standard library only (`http.server.ThreadingHTTPServer`,
  `json`, `hmac`, `secrets`, `queue`, `threading`, `time.monotonic_ns`).
- Static web bundle (HTML, ES modules, CSS) with vendored Three.js r186 prebuilt
  modules and `OrbitControls`, loaded through an import map. No Node, npm or
  bundler in the repository or CI.
- Tests: `unittest`, owned fixtures under `tests/fixtures/view/`.
- Scope is VIS.1 as defined in [spec.md](spec.md), delivered as VIS.1a
  (coordination slice: probes and census first, then contract, coordination
  adapters, server, `--watch`, replay, Claude hooks, table view, Three.js scene)
  and VIS.1b (host streams, OTLP, recording, export, effort pack, frames), with the
  T035 go/no-go checkpoint between them. VIS.2–VIS.4 are in [tracks.md](tracks.md).
- Order: owner-run probes (T030–T033) and the artifact census (T038) need no ADR
  and run first; their receipts become the ingest fixtures, so parsers are not
  tested only against documentation. The first visible result is the table view
  and evidence panel on replay (T024), which needs no third-party code.

### Layout

```
agent_braid/
  view_loom.py      contract constants, limits, strict JSON, validate_event, canonical bytes
  view_adapters.py  artifacts -> events (analysis, plan, scheduler, grants, runtime,
                    ownership JSON, workflow gate, host streams)
  view_otlp.py      OTLP HTTP/JSON logs and metrics -> events (allowlist, salting)
  view_hooks.py     observational Claude Code HTTP hooks -> events (empty responses)
  view_tail.py      bounded polling of artifact directories
  view_store.py     in-memory ring, seq assignment, eviction gaps, fan-out
  view_model.py     pure viewer model and Article 19 counters
  view_render.py    pure frames: ASCII, braille, SVG, RGBA
  view_export.py    minimal export and effort evidence pack
  view_serve.py     loopback server, open code and ingest token, headers, routes, SSE
                    (only network module)
  view_cli.py       add_parser()/run() registered in cli.py like telemetry
integrations/agent-braid-view/
  README.md
  web/index.html, web/loom.js, web/braid-scene.js, web/table.js, web/style.css
  web/vendor/three/three.module.js, web/vendor/three/three.core.js,
  web/vendor/three/addons/controls/OrbitControls.js
  web/vendor/manifest.json
examples/view/loom-replay.jsonl
docs/tooling/VIEWER.md
tests/test_view_*.py, tests/fixtures/view/**
```

`view_model.py` and `view_export.py` are additions to the layout of the planning
session's proposal: the model is shared by the web viewer (`/snapshot`), frames and export, and
keeping it pure avoids duplicating counter logic.

## Constitution check before research

| Article | Obligation | Design response |
|---|---|---|
| 0 | Hypotheses, analogy, evidence separated | braid picture is representation; Q-VIS1 is an open question, not a hypothesis |
| 6 | Interaction properties drive scheduling; sequential commutation alone does not justify interleaving | a drawn swap or wave is labeled advisory and is never permission to interleave |
| 11 | Visual metaphor without semantics is not a contribution; simplification preserves semantics | every element has one source event; no braid relation applied; lane order is layout |
| 13 | Compatibility class on every analysis result; confidence is not a guarantee | `assurance.compatibilityClass` required for crossings; `notAGuarantee: true`; legend |
| 14 | Expose evidence | evidence panel with reasons, constraints, `evidenceRef` hash and verification status; replayed and host-reported events marked unverified |
| 17, 18 | State the claim level; analogy is a hypothesis generator | claim level inspiration stated in the spec, ROADMAP and viewer documentation |
| 19 | Success measured by conflicts prevented, safe parallelism recovered, replay, diagnostics, overhead | counters show only what events support (conflicts flagged, planned wave width alone, labeled advisory plan and not a runtime measurement, gaps); no speedup or serial ratio |
| 20 | Analysis and execution separate | read-only routes; `executionAuthorization: false`; hook routes accept only observational events and answer with empty bodies |
| 21, 22 | Practical value; mathematics not ornamental | the viewer shows coordination facts; no decorative braid claim |
| 24 | Semantics precede production implementation | adapters translate existing semantics only |

No MUST conflict found. Deviation recorded: the viewer holds several SPEC-057
never-collect categories outside telemetry, under owner decision D4; the
[deviation table](contracts/ui-security-privacy.md#deviations-from-the-never-collect-list)
lists them for review in T001.

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions: hosts keep exporting OTLP HTTP/JSON;
the Claude desktop browser pane loads loopback pages (documented, unverified until
T032); empty-bodied HTTP hook responses are non-blocking (documented, unverified
until T030); users run the viewer on the same machine as the hosts. No empirical
data is collected; the Q-VIS1 observation is optional and owner-run.

## Design and compatibility

1. **Contract.** [loom-event.schema.json](contracts/loom-event.schema.json). The
   validator in `view_loom.py` implements the same rules without a schema library;
   a test checks parity against the example and seeded violations. The example
   shows the `verification` values of a live session; a replay of it is
   `unverified` throughout.
2. **Adapters.** Pure functions `events_from_<family>(document, *, root, seq_start)`
   returning event lists; hashing artifact bytes for `evidenceRef`. Ownership
   outputs are parsed as JSON by schema version string, without importing
   `agent_braid.ownership`. Gate results yield `gate.phase` and `gate.result`
   only. Scheduler waves carry the `scheduleDigest`; no plan-to-schedule join is
   drawn unless an artifact records it. Oversized pairs become a
   `stream-truncated` gap.
3. **Store.** Ring of 50 000 events; eviction emits one `ring-evicted` gap per
   evicted range; per-kind caps from REQ-004; subscribers get a bounded queue and
   are dropped (not blocked) when slow, with a `stream-truncated` gap on resume.
4. **Server.** Loopback bind, one-time open code exchanged for a read cookie,
   ingest token in an owner-only file sent as a bearer header, header checks,
   connection and timeout limits, access logging off, and routes from the
   [UI, security and privacy contract](contracts/ui-security-privacy.md).
5. **Ingest.** OTLP JSON is parsed field by field against the allowlist at every
   level; log bodies are dropped; unknown shapes yield `shape-unpinned`. Hooks
   accept only `SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop` and
   `PostToolUse`, map them to strand events without tool input or output, and
   always answer with an empty body. Codex `notify` and hooks are VIS.3.
6. **Model and frames.** One pure model (strands, lanes reordered to keep
   classified pairs adjacent, swaps only for `independent-candidate`, bridges for
   non-adjacent pairs, waves, gates, hazards, gaps, counters) feeds `/snapshot`,
   frames and export. Time axis uses `relMs` with gap compression; `seq` breaks
   ties.
7. **Web viewer.** Three.js WebGL2 renderer, OrbitControls, clipping-plane
   playback, evidence panel, legend, counters, table view. OrbitControls imports
   the bare specifier `three`, so `index.html` carries one inline import map whose
   SHA-256 is the only inline hash the CSP allows. Bloom and particles are allowed
   only where bound to an event. Without ADR 0033 the table view and SVG frames
   are the surface.
8. **Export.** Minimal export and [effort evidence pack](contracts/effort-evidence-pack.md),
   reusing SPEC-043 destination rules with exclusive creation, escaping every
   text value and replacing absolute-path-like values.
9. **CLI.** `agent-braid view serve [--replay FILE] [--watch DIR ...] [--port N]
   [--surface web|mod|tui|mcp-app] [--record FILE [--record-effort]]`,
   `view export --from FILE --to PATH [--include-effort --baseline NAME
   --arm NAME=FILE ... --arm-note NAME=TEXT ...]`, `view validate FILE`, `view env --host claude|codex`.
10. **Validation rule.** `Rule("activity-viewer", (agent_braid/view_*.py,
    tests/test_view_*.py, tests/fixtures/view/**, integrations/agent-braid-view/**,
    examples/view/**, docs/tooling/VIEWER.md), ("full-tests",), True, boundary=...)`.

Compatibility: additive; new contract and command group; no existing output
changes. `cli.py` gains the `view` registration only.

## Validation strategy

| Requirement | Scenario | Test module | Procedure |
|---|---|---|---|
| REQ-001 | SC-001 | `tests/test_view_loom.py` | procedure_001 |
| REQ-002 | SC-002 | `tests/test_view_adapters.py` | procedure_002 |
| REQ-003 | SC-003 | `tests/test_view_adapters.py`, `tests/test_view_model.py` | procedure_003 |
| REQ-004 | SC-004 | `tests/test_view_serve.py` | procedure_004 |
| REQ-005 | SC-005 | `tests/test_view_otlp.py`, `tests/test_view_hooks.py` | procedure_005 |
| REQ-006 | SC-006 | `tests/test_view_store.py`, `tests/test_view_serve.py`, `tests/test_view_tail.py` | procedure_006 |
| REQ-007 | SC-007 | `tests/test_view_serve.py`, `tests/test_view_export.py` | procedure_007 |
| REQ-008 | SC-008 | `tests/test_view_export.py` | procedure_008 |
| REQ-009 | SC-009 | `tests/test_view_export.py` | procedure_009 |
| REQ-010 | SC-010 | `tests/test_view_model.py`, `tests/test_view_web_bundle.py` | procedure_010 |
| REQ-011 | SC-011 | `tests/test_view_render.py`, `tests/test_view_cli.py` | procedure_011 |
| REQ-012 | SC-012 | `tests/test_view_cli.py` | procedure_012 |
| REQ-013 | SC-013 | `tests/test_orchestration_governance.py`, `tests/test_plugin_package.py`, `tests/test_validation_profiles.py`, `tests/test_view_boundaries.py` | procedure_013 |
| REQ-014 | SC-014 | owner-run receipts | procedure_014 |
| REQ-015 | SC-015 | `tests/test_view_docs.py` | procedure_015 |

Negative controls are listed per procedure in [validation-plan.md](validation-plan.md).
`assurance.json` holds planned evidence only until implementation.

## Constitution check after design

Unchanged: no MUST conflict. The design adds no execution path, no telemetry write
and no remote network use. Article 11 risk (decorative effects) is controlled by
REQ-010's one-element-one-event test; effects without data (bloom, particles) are
allowed only when bound to an event or removed.

## Human review and unresolved decisions

| ID | Decision | Recommendation | Owner |
|---|---|---|---|
| OD-1 | Accept ADR 0032 (companion boundary) | Accepted 2026-11-01 | Owner |
| OD-2 | Accept ADR 0033 (vendored Three.js MIT boundary) | Accepted 2026-11-01, pinned r186 (`0.186.0`) | Founder |
| OD-3 | Public name: keep "Loom" as working name; command `agent-braid view` | Decided 2026-11-01 (T001): keep command; decide name before VIS.1 release notes | Owner |
| OD-4 | Q-VIS1 observation | Resolved 2026-10-31: descriptive observation at the T035 checkpoint after VIS.1a | Owner |
| OD-5 | Renderer: WebGL2 now, WebGPU later | Decided 2026-11-01 (T001): WebGL2 | Owner |
| OD-6 | Default port: OS-assigned | Decided 2026-11-01 (T001): OS-assigned, `--port` optional | Owner |
| OD-8 | Checkpoint date and census threshold for T035 and T038 | Decided 2026-11-01 (T001): checkpoint by 2027-01-31; census threshold at least 5 sessions or run directories of the last four weeks with at least one coordination artifact and at least 3 of the 6 artifact kinds overall; if the date passes without a VIS.1a slice, VIS.1 closes as Deferred | Owner |
| OD-7 | Accept the never-collect deviations (exact effort in `--record-effort` recordings, salted identifiers, relative paths and hashes) | Decided 2026-11-01 (T001): accepted as listed in the deviation table | Owner |

Implementation tasks start after OD-1; T023 and T025 also need OD-2. Probes
T030–T033 and the census T038 need per-probe owner authorization only. VIS.1b
tasks start only after T035 records keep.
