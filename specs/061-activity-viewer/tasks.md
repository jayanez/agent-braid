# SPEC-061: Tasks

Stable task IDs. Completion requires obtained evidence; completing a task does not
imply host verification, release or founder acceptance. Parallelizable does not
authorize concurrent agents. No task is started by the specification change.
T010–T022 and T027–T029 need ADR 0032 accepted (T002); T023–T026 also need
ADR 0033 accepted (T003); T030–T033 need per-probe owner authorization.

## Governance and tracking

- [ ] T001 (all REQ): Owner review of the specification, plan, contracts and open
  decisions OD-3 to OD-6. Dependencies: T008. Files: `spec.md`, `plan.md`,
  `contracts/`. Evidence: review record in this directory.
- [ ] T002 (REQ-004, REQ-013): Decide ADR 0032 (activity viewer companion).
  Dependencies: none. Files: `docs/adr/0032-activity-viewer-companion.md`.
  Evidence: ADR status change merged.
- [ ] T003 (REQ-010, REQ-013): Founder decision on ADR 0033 (vendored Three.js,
  MIT boundary). Dependencies: none. Files:
  `docs/adr/0033-vendored-threejs-mit-boundary.md`. Evidence: ADR status change merged.
- [ ] T004 (REQ-015): Add the VIS track to ROADMAP, STATUS, the milestone index,
  the AI tooling program, GitHub tracking source and validation profile notes.
  Dependencies: none. Files: `ROADMAP.md`, `docs/STATUS.md`,
  `docs/development/SPEC_MILESTONE_INDEX.md`,
  `specs/039-ai-tooling-program/program.md`,
  `docs/development/github-tracking.json`, `docs/development/GITHUB_TRACKING.md`,
  `docs/tooling/README.md`. Verification: `python3 scripts/sync_github_tracking.py
  source`. Evidence: merged change and source output.
- [ ] T005 (REQ-015): After merge to `develop`, publish VIS.1 tracking: `audit`,
  review, `apply --confirm-repository jayanez/agent-braid --plan-sha256 <digest>`,
  record the milestone number, re-audit to zero operations, set the parent issue
  to Review pending in Project 6. Dependencies: T004 merged. Evidence: audit and
  apply outputs, milestone number in `github-tracking.json`.
- [ ] T006 (REQ-011): Record derived tracks VIS.2–VIS.4 with scope, sources,
  gates and open questions. Dependencies: none. Files: `tracks.md`. Evidence:
  owner review in T001.
- [ ] T007 (REQ-014): Review the host-verification runbook. Dependencies: none.
  Files: `host-verification-runbook.md`. Evidence: owner review in T001.
- [ ] T008: Freeze the specification candidate with
  `python3 -m scripts.validate_spec_kit freeze specs/061-activity-viewer`.
  Dependencies: T004, T006, T007. Evidence: historical snapshot in `assurance.json`.
- [ ] T009 (REQ-015): Keep STATUS, ROADMAP, the milestone index, tracking source
  and Project 6 current at each VIS.1 closure. Dependencies: T005. Evidence: audit
  with zero operations after each closure.

## Contract and adapters

- [ ] T010 (REQ-001 / SC-001): `view_loom.py`: constants, limits, strict JSON,
  `validate_event`, canonical bytes; schema parity test. Tests first. Files:
  `agent_braid/view_loom.py`, `tests/test_view_loom.py`, `tests/fixtures/view/loom/`.
  Verification: procedure_001.
- [ ] T011 (REQ-013 / SC-013): `activity-viewer` rule in
  `scripts/validate_change.py`, test in `tests/test_validation_profiles.py`,
  paragraph in `docs/development/VALIDATION_PROFILES.md`. Verification:
  procedure_013.
- [ ] T012 (REQ-002 / SC-002): Adapters for analysis reports, Git replay plans,
  scheduler preparations, grants and runtime state. Files:
  `agent_braid/view_adapters.py`, `tests/test_view_adapters.py`,
  `tests/fixtures/view/artifacts/`. Dependencies: T010. Verification: procedure_002.
- [ ] T013 (REQ-002 / SC-002; REQ-003 / SC-003): Adapters for ownership notices
  and receipts (JSON only), workflow-gate results and absence cases. Dependencies:
  T012. Verification: procedure_002, procedure_003.
- [ ] T014 (REQ-002 / SC-002): Host stream adapters (`claude -p` stream-json,
  `codex exec --json`) and the example replay `examples/view/loom-replay.jsonl`
  generated from owned fixtures. Dependencies: T012. Verification: procedure_002.

## Store, server and ingest

- [ ] T015 (REQ-006 / SC-006): `view_store.py` ring, seq, caps, eviction gaps,
  bounded subscriber queues. Files: `agent_braid/view_store.py`,
  `tests/test_view_store.py`. Dependencies: T010. Verification: procedure_006.
- [ ] T016 (REQ-004 / SC-004): `view_serve.py` loopback bind, token, `Host` and
  `Origin` checks, headers, body limits, route table. Files:
  `agent_braid/view_serve.py`, `tests/test_view_serve.py`. Dependencies: T015.
  Verification: procedure_004.
- [ ] T017 (REQ-004 / SC-004; REQ-006 / SC-006; REQ-007 / SC-007): SSE with
  `Last-Event-ID`, `/snapshot`, replay mode, `view_tail.py` bounded polling,
  `--record`/`--record-effort` writing capped at 50 000 events. Dependencies: T016,
  T020. Verification: procedure_004, procedure_006, procedure_007.
- [ ] T018 (REQ-005 / SC-005): `view_otlp.py` OTLP HTTP/JSON logs and metrics,
  allowlist, salting, `shape-unpinned`. Files: `agent_braid/view_otlp.py`,
  `tests/test_view_otlp.py`, `tests/fixtures/view/otlp/`. Dependencies: T015.
  Verification: procedure_005.
- [ ] T019 (REQ-005 / SC-005; REQ-007 / SC-007): `view_hooks.py` Claude HTTP
  hooks and Codex notify or hook shim; dropped-attribute names inventory;
  ephemeral effort handling. Dependencies: T015. Verification: procedure_005,
  procedure_007.

## Model, export and frames

- [ ] T020 (REQ-003 / SC-003; REQ-010 / SC-010): `view_model.py` pure model:
  lanes, adjacent swap decomposition, `relMs` axis with gap compression, waves,
  serial fallback, counters. Files: `agent_braid/view_model.py`,
  `tests/test_view_model.py`. Dependencies: T010. Verification: procedure_003,
  procedure_010.
- [ ] T021 (REQ-007 / SC-007; REQ-008 / SC-008): `view_export.py` minimal export
  from a recorded or replay file (`--from`) with SPEC-043 destination rules. Files: `agent_braid/view_export.py`,
  `tests/test_view_export.py`. Dependencies: T020. Verification: procedure_007,
  procedure_008.
- [ ] T022 (REQ-009 / SC-009): Effort evidence pack: `--arm`, `--arm-note`,
  `--baseline`, pairwise comparisons in the harness comparison shape. Dependencies: T021, T027.
  Verification: procedure_009.
- [ ] T027 (REQ-011 / SC-011): `view_render.py` ASCII, braille, SVG and RGBA
  frames; `/frame.svg` and `/frame.txt`. Files: `agent_braid/view_render.py`,
  `tests/test_view_render.py`. Dependencies: T020. Verification: procedure_011.

## Web viewer

- [ ] T023 (REQ-010 / SC-010; REQ-013 / SC-013): Vendor Three.js r182 prebuilt
  modules (`three.module.js`, `three.core.js`) and OrbitControls with
  `manifest.json`; add `LICENSES/three-MIT.txt`, the
  LICENSE paragraph and the THIRD_PARTY section. Dependencies: T003. Files:
  `integrations/agent-braid-view/web/vendor/**`, `LICENSE`, `LICENSES/`,
  `docs/development/THIRD_PARTY.md`. Verification: procedure_010.
- [ ] T024 (REQ-010 / SC-010): Web bundle: scene, playback, table view, hashed
  import map and CSP.
  Files: `integrations/agent-braid-view/web/*`. Dependencies: T023, T020.
  Verification: procedure_010.
- [ ] T025 (REQ-010 / SC-010): Evidence panel, legend with "not a guarantee",
  Article 19 counters. Dependencies: T024. Verification: procedure_010.
- [ ] T026 (REQ-010 / SC-010): `tests/test_view_web_bundle.py` (hashes, no remote
  URL, no `eval`, CSP). Dependencies: T024. Verification: procedure_010.

## Command line and boundaries

- [ ] T028 (REQ-011 / SC-011; REQ-012 / SC-012): `view_cli.py` with `serve`,
  `export`, `validate`, `env`, `--surface`; registration in `agent_braid/cli.py`.
  Files: `agent_braid/view_cli.py`, `agent_braid/cli.py`, `tests/test_view_cli.py`.
  Dependencies: T016, T021. Verification: procedure_011, procedure_012.
- [ ] T029 (REQ-013 / SC-013): Boundary tests (`tests/test_view_boundaries.py`)
  and regression run of governance, plugin package and validation profiles.
  Dependencies: T028. Verification: procedure_013.

## Host verification (owner-run)

- [ ] T030 (REQ-014 / SC-014): Claude Code OpenTelemetry attribute names.
- [ ] T031 (REQ-014 / SC-014): Codex `[otel]` export shape.
- [ ] T032 (REQ-014 / SC-014): Claude desktop browser pane loads the viewer.
- [ ] T033 (REQ-014 / SC-014): Codex Desktop MCP Apps rendering (`unobserved` valid).

## Documentation and closure

- [ ] T034 (REQ-015 / SC-015): `docs/tooling/VIEWER.md`,
  `integrations/agent-braid-view/README.md`, tooling index. Dependencies: T028.
  Verification: procedure_015.
- [ ] T035 (optional, H-VIS1): Owner-run comprehension observation.
  Dependencies: T034. Verification: procedure_hvis1.
- [ ] T036: Pre-PR reviews (code review, quality, simplification),
  `validate_change --profile pr` on the stable candidate, `/speckit-converge`.
  Dependencies: T010–T029, T034.
- [ ] T037: Record obtained evidence in `assurance.json`, freeze, owner review of
  VIS.1 closure. Dependencies: T036.
