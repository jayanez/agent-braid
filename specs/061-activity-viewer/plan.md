# SPEC-061 implementation plan

## Technical context and scope

- Python 3.12+, standard library only (`http.server.ThreadingHTTPServer`,
  `json`, `hmac`, `secrets`, `queue`, `threading`, `time.monotonic_ns`).
- Static web bundle (HTML, ES modules, CSS) with vendored Three.js r182 prebuilt
  modules and `OrbitControls`, loaded through an import map. No Node, npm or
  bundler in the repository or CI.
- Tests: `unittest`, owned fixtures under `tests/fixtures/view/`.
- Scope is VIS.1 as defined in [spec.md](spec.md). VIS.2–VIS.4 are in
  [tracks.md](tracks.md).

### Layout

```
agent_braid/
  view_loom.py      contract constants, limits, strict JSON, validate_event, canonical bytes
  view_adapters.py  artifacts -> events (analysis, plan, scheduler, grants, runtime,
                    ownership JSON, workflow gate, host streams)
  view_otlp.py      OTLP HTTP/JSON logs and metrics -> events (allowlist, salting)
  view_hooks.py     Claude Code HTTP hooks, Codex notify and hook shim -> events
  view_tail.py      bounded polling of artifact directories
  view_store.py     in-memory ring, seq assignment, eviction gaps, fan-out
  view_model.py     pure viewer model and Article 19 counters
  view_render.py    pure frames: ASCII, braille, SVG, RGBA
  view_export.py    minimal export and effort evidence pack
  view_serve.py     loopback server, token, headers, routes, SSE (only network module)
  view_cli.py       add_parser()/run() registered in cli.py like telemetry
integrations/agent-braid-view/
  README.md
  web/index.html, web/loom.js, web/braid-scene.js, web/table.js, web/style.css
  web/vendor/three/three.module.js, web/vendor/three/addons/controls/OrbitControls.js
  web/vendor/manifest.json
examples/view/loom-replay.jsonl
docs/tooling/VIEWER.md
tests/test_view_*.py, tests/fixtures/view/**
```

`view_model.py` and `view_export.py` are additions to the layout of the approved
plan: the model is shared by the web viewer (`/snapshot`), frames and export, and
keeping it pure avoids duplicating counter logic.

## Constitution check before research

| Article | Obligation | Design response |
|---|---|---|
| 0 | Hypotheses, analogy, evidence separated | braid picture is representation; H-VIS1 is a hypothesis |
| 11 | Visual metaphor without semantics is not a contribution; simplification preserves semantics | every element has one source event; no braid relation applied; lane order is layout |
| 13 | Compatibility class on every analysis result; confidence is not a guarantee | `assurance.compatibilityClass` required for crossings; `notAGuarantee: true`; legend |
| 14 | Expose evidence | evidence panel with reasons, constraints and `evidenceRef` hash |
| 19 | Success measured by conflicts prevented, safe parallelism recovered, replay, diagnostics, overhead | counters show only what events support (conflicts flagged, planned wave width marked advisory and not verified safe, gaps); no speedup |
| 20 | Analysis and execution separate | read-only routes; `executionAuthorization: false` |
| 21, 22 | Practical value; mathematics not ornamental | the viewer shows coordination facts; no decorative braid claim |
| 24 | Semantics precede production implementation | adapters translate existing semantics only |

No MUST conflict found. SHOULD deviation: none.

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions: hosts keep exporting OTLP HTTP/JSON;
the Claude desktop browser pane loads loopback pages; users run the viewer on the
same machine as the hosts. No empirical data is collected; H-VIS1 is optional and
owner-run.

## Design and compatibility

1. **Contract.** [loom-event.schema.json](contracts/loom-event.schema.json). The
   validator in `view_loom.py` implements the same rules without a schema library;
   a test checks parity against the example and seeded violations.
2. **Adapters.** Pure functions `events_from_<family>(document, *, root, seq_start)`
   returning event lists; hashing artifact bytes for `evidenceRef`. Ownership
   outputs are parsed as JSON by schema version string, without importing
   `agent_braid.ownership`.
3. **Store.** Ring of 50 000 events; eviction emits one `ring-evicted` gap per
   evicted range; per-kind caps from REQ-004; subscribers get a bounded queue and
   are dropped (not blocked) when slow, with a `stream-truncated` gap on resume.
4. **Server.** Loopback bind, token, header checks and routes from the
   [UI, security and privacy contract](contracts/ui-security-privacy.md).
5. **Ingest.** OTLP JSON is parsed field by field against the allowlist; unknown
   shapes yield `shape-unpinned`. Hooks map `SubagentStart/Stop`, `PreToolUse`,
   `PostToolUse` to strand events without tool input or output.
6. **Model and frames.** One pure model (strands, lanes reordered to keep
   classified pairs adjacent, swaps only for `independent-candidate`, bridges for
   non-adjacent pairs, waves, gates, hazards, gaps, counters) feeds `/snapshot`,
   frames and export. Time axis uses `relMs` with gap compression; `seq` breaks
   ties.
7. **Web viewer.** Three.js WebGL2 renderer, OrbitControls, clipping-plane
   playback, evidence panel, legend, counters, table view. OrbitControls imports
   the bare specifier `three`, so `index.html` carries one inline import map whose
   SHA-256 is the only inline hash the CSP allows. Bloom and particles are allowed
   only where bound to an event.
8. **Export.** Minimal export and [effort evidence pack](contracts/effort-evidence-pack.md),
   reusing SPEC-043 destination rules.
9. **CLI.** `agent-braid view serve [--replay FILE] [--watch DIR ...] [--port N]
   [--surface web|mod|tui|mcp-app] [--record FILE [--record-effort]]`,
   `view export --from FILE --to PATH [--include-effort --arm NAME=FILE ...
   --baseline NAME]`, `view validate FILE`, `view env --host claude|codex`.
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
| REQ-006 | SC-006 | `tests/test_view_store.py`, `tests/test_view_serve.py` | procedure_006 |
| REQ-007 | SC-007 | `tests/test_view_hooks.py`, `tests/test_view_export.py` | procedure_007 |
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
| OD-1 | Accept ADR 0032 (companion boundary) | Accept | Owner |
| OD-2 | Accept ADR 0033 (vendored Three.js MIT boundary, pinned r182) | Accept | Founder |
| OD-3 | Public name: keep "Loom" as working name; command `agent-braid view` | Keep command; decide name before VIS.1 release notes | Owner |
| OD-4 | Run the optional H-VIS1 observation (T035) | Defer until VIS.1 is usable | Owner |
| OD-5 | Renderer: WebGL2 now, WebGPU later | WebGL2 | Owner |
| OD-6 | Default port: OS-assigned | OS-assigned, `--port` optional | Owner |

Implementation tasks T010–T022 and T027–T029 start after OD-1; T023–T026 also
need OD-2. Host verification tasks T030–T033 need per-probe owner authorization.
