# SPEC-061: Tasks

Stable task IDs. Completion requires obtained evidence; completing a task does not
imply host verification, release or founder acceptance. Parallelizable does not
authorize concurrent agents. No task is started by the specification change.

VIS.1 is delivered in two increments inside one milestone: **VIS.1a**
(coordination slice) and **VIS.1b** (effort, recording, export and frames). VIS.1b
starts only if the T035 checkpoint records "keep" or a re-scope that includes it.
Implementation tasks need ADR 0032 accepted (T002); T023 and T025 also need
ADR 0033 accepted (T003). Owner-run probes and the census (T030–T033, T038) need
per-probe owner authorization but no ADR, and run first.

## Governance and tracking

- [x] T001 (all REQ): Owner review of the specification, plan, contracts and open
  decisions OD-3 to OD-7. Dependencies: T008. Files: `spec.md`, `plan.md`,
  `contracts/`. Evidence: review record in this directory that also records the
  requested decisions D1–D6, the never-collect deviations (OD-7), the census
  threshold and the checkpoint date (OD-8). Done 2026-11-01:
  [owner-review-20261101.json](owner-review-20261101.json).
- [x] T002 (REQ-004, REQ-013): Decide ADR 0032 (activity viewer companion).
  Dependencies: none. Files: `docs/adr/0032-activity-viewer-companion.md`.
  Evidence: ADR status change merged.
- [x] T003 (REQ-010, REQ-013): Founder decision on ADR 0033 (vendored Three.js,
  MIT boundary). Dependencies: none. Files:
  `docs/adr/0033-vendored-threejs-mit-boundary.md`. Evidence: ADR status change merged.
- [x] T004 (REQ-015): Add the VIS track to ROADMAP, STATUS, the milestone index,
  the AI tooling program, GitHub tracking source and validation profile notes.
  Dependencies: none. Files: `ROADMAP.md`, `docs/STATUS.md`,
  `docs/development/SPEC_MILESTONE_INDEX.md`,
  `specs/039-ai-tooling-program/program.md`,
  `docs/development/github-tracking.json`, `docs/development/GITHUB_TRACKING.md`,
  `docs/tooling/README.md`. Verification: `python3 scripts/sync_github_tracking.py
  source`. Evidence: merged change and source output.
- [x] T005 (REQ-015): After merge to `develop`, publish VIS.1 tracking: `audit`,
  review, `apply --confirm-repository jayanez/agent-braid --plan-sha256 <digest>`,
  record the milestone number, re-audit to zero operations, set the parent issue
  to Review pending in Project 6. Dependencies: T004 merged. Evidence: audit and
  apply outputs, milestone number in `github-tracking.json`. Done 2026-11-01:
  milestone #25 (PR #808), parent #810 in Review pending, scoped re-audit with no
  operations.
- [x] T006 (REQ-011): Record derived tracks VIS.2–VIS.4 with scope, sources,
  gates and open questions. Dependencies: none. Files: `tracks.md`. Evidence:
  owner review in T001.
- [x] T007 (REQ-014): Review the host-verification runbook. Dependencies: none.
  Files: `host-verification-runbook.md`. Evidence: owner review in T001.
- [x] T008: Freeze the specification candidate with
  `python3 -m scripts.validate_spec_kit freeze specs/061-activity-viewer`.
  Dependencies: T004, T006, T007. Evidence: historical snapshot in `assurance.json`.
- [ ] T009 (REQ-015): Keep STATUS, ROADMAP, the milestone index, tracking source
  and Project 6 current at the T035 checkpoint and at each delivery closure.
  Dependencies: T005. Evidence: audit
  with zero operations after each closure.

## VIS.1a — Probes before code (owner-run)

- [x] T030 (REQ-014 / SC-014): Claude Code probe with a throwaway standard-library
  listener and no Loom code: record the names (never values) of the OTLP HTTP/JSON
  attributes the installed version emits, and whether empty-bodied HTTP hook
  responses, and a stopped listener, leave tool calls unaffected. Dependencies:
  none. Evidence: `evidence/hv-t030-<date>.json`. A path that does not match is
  removed from VIS.1 and marked `not-matching`. Done 2026-11-01:
  `evidence/hv-t030-20261101.json` (verified; two field-level checks not matching).
- [ ] T031 (REQ-014 / SC-014): Codex probe: record the names emitted by the
  `[otel]` export of the installed version with the same throwaway listener.
  Dependencies: none. Evidence: `evidence/hv-t031-<date>.json`. A path that does
  not match is removed from VIS.1 and marked `not-matching`. Partial 2026-11-01:
  `evidence/hv-t031-20261101.json` (logs and traces verified; token-usage names
  unobserved, Codex usage limit until 2026-11-23); rerun before closing.
- [x] T032 (REQ-014 / SC-014): Claude desktop browser pane loads a static loopback
  fixture page served with the contract headers, without CSP violation or outbound
  request. Dependencies: none. Evidence: `evidence/hv-t032-<date>.json`. Done
  2026-11-01: `evidence/hv-t032-20261101.json` (console errors unobserved;
  rechecked at T035).
- [ ] T033 (REQ-014 / SC-014): Codex Desktop MCP Apps rendering with a minimal
  fixture without Agent Braid data (`unobserved` valid). Dependencies: none.
  Evidence: `evidence/hv-t033-<date>.json`.
- [x] T038 (REQ-002, REQ-006): Artifact census: count the owner's sessions and run
  directories of the last four weeks that contain analysis reports, plans,
  scheduler preparations, grants, ownership notices or receipts, or gate results
  (counts and artifact kinds only, no content). Dependencies: none. Evidence:
  `evidence/census-<date>.json` compared with the OD-8 threshold (at least 5
  sessions or run directories with at least one coordination artifact, and at
  least 3 of the 6 kinds overall). Done 2026-11-01: `evidence/census-20261101.json` (met:
  48 sessions, 11 outside synthetic corpora, 5 of 6 kinds; no grants).

## VIS.1a — Coordination slice

- [ ] T010 (REQ-001 / SC-001): `view_loom.py`: constants, limits, strict JSON,
  `validate_event`, canonical bytes; schema parity test. Tests first. Files:
  `agent_braid/view_loom.py`, `tests/test_view_loom.py`, `tests/fixtures/view/loom/`.
  Verification: procedure_001.
- [ ] T011 (REQ-013 / SC-013): `activity-viewer` rule in
  `scripts/validate_change.py`, test in `tests/test_validation_profiles.py`,
  paragraph in `docs/development/VALIDATION_PROFILES.md`; assert that changes to
  the source modules and schemas the adapters read already escalate to the full
  tests, and add their patterns to the rule if not. Verification: procedure_013.
- [ ] T012 (REQ-002 / SC-002): Adapters for analysis reports first, then Git
  replay plans, scheduler preparations, grants and runtime state, each with a table
  of supported source schema versions and a `source-unsupported` gap otherwise.
  Files: `agent_braid/view_adapters.py`, `tests/test_view_adapters.py`,
  `tests/fixtures/view/artifacts/`. Dependencies: T010. Verification: procedure_002.
- [ ] T013 (REQ-002 / SC-002; REQ-003 / SC-003): Adapters for ownership notices
  and receipts (JSON only, every hazard unit kept), workflow-gate phases and
  results (no gate crossings), oversized pairs and absence cases. Files:
  `agent_braid/view_adapters.py`, `tests/test_view_adapters.py`,
  `tests/fixtures/view/artifacts/`. Dependencies: T012. Verification:
  procedure_002, procedure_003.
- [ ] T015 (REQ-006 / SC-006): `view_store.py` ring, seq, caps, eviction gaps,
  bounded subscriber queues. Files: `agent_braid/view_store.py`,
  `tests/test_view_store.py`. Dependencies: T010. Verification: procedure_006.
- [ ] T016 (REQ-004 / SC-004): `view_serve.py` loopback bind, one-time open code
  and read cookie, ingest token file and bearer check, `Host`, `Origin` and
  `Sec-Fetch-Site` checks, headers, body, connection and timeout limits, access
  logging off, route table. Files: `agent_braid/view_serve.py`,
  `tests/test_view_serve.py`. Dependencies: T015. Verification: procedure_004.
  The OTLP allowlist drops the names each probe receipt lists in
  `findingsForAllowlist`.
- [ ] T017 (REQ-004 / SC-004; REQ-006 / SC-006): SSE with `Last-Event-ID`,
  `/snapshot`, replay mode with `unverified` marking, `view_tail.py` bounded
  `--watch` polling without following symbolic links. Files:
  `agent_braid/view_serve.py`, `agent_braid/view_tail.py`,
  `tests/test_view_serve.py`, `tests/test_view_tail.py`. Dependencies: T016,
  T020. Verification: procedure_004, procedure_006.
- [ ] T019 (REQ-005 / SC-005): `view_hooks.py` observational Claude Code HTTP
  hooks with empty responses and refusal of decision events; dropped-attribute
  names inventory. Files: `agent_braid/view_hooks.py`, `tests/test_view_hooks.py`,
  `tests/fixtures/view/hooks/` (built from the T030 receipt). Dependencies: T016,
  T030 (`verified`). Verification: procedure_005. Per the T030 receipt, attribute
  subagents from hook `agent_id` (OpenTelemetry has none), do not depend on an HTTP
  `SessionStart`, and re-pin the `ui-security-privacy.md` allowlist in this change.
- [ ] T020 (REQ-003 / SC-003; REQ-010 / SC-010): `view_model.py` pure model:
  lanes, adjacent swap decomposition, `relMs` axis with gap compression, waves,
  verification markers, counters. Files: `agent_braid/view_model.py`,
  `tests/test_view_model.py`. Dependencies: T010. Verification: procedure_003,
  procedure_010.
- [ ] T024 (REQ-010 / SC-010): Web bundle without third-party code: table view,
  evidence panel, legend with "not a guarantee", Article 19 counters, unverified
  markers, playback controls and CSP. Files:
  `integrations/agent-braid-view/web/*`. Dependencies: T020, T017.
  Verification: procedure_010.
- [ ] T023 (REQ-010 / SC-010; REQ-013 / SC-013): Vendor Three.js r186 prebuilt
  modules (`three.module.js`, `three.core.js`) and OrbitControls with
  `manifest.json`; add `LICENSES/three-MIT.txt`, the LICENSE paragraph, the NOTICE
  entry, the license marker in `scripts/validate_repository.py` and the
  THIRD_PARTY section; record an owner-run provenance receipt comparing the
  registry integrity of the pinned tarball with the vendored bytes. Dependencies:
  T003. Files: `integrations/agent-braid-view/web/vendor/**`, `LICENSE`,
  `LICENSES/`, `NOTICE`, `scripts/validate_repository.py`,
  `docs/development/THIRD_PARTY.md`, `specs/061-activity-viewer/evidence/`.
  Verification: procedure_010.
- [ ] T025 (REQ-010 / SC-010): Three.js braid scene with the hashed import map,
  bound to the same model and evidence panel as the table view. Files:
  `integrations/agent-braid-view/web/*`. Dependencies: T023, T024. Verification:
  procedure_010.
- [ ] T026 (REQ-010 / SC-010): `tests/test_view_web_bundle.py` (first-party: no
  remote URL, no `eval`, CSP, import map; vendored: manifest hashes once T023
  exists). Dependencies: T024. Verification: procedure_010.
- [ ] T028 (REQ-011 / SC-011; REQ-012 / SC-012): `view_cli.py` with `serve`
  (`--replay`, `--watch`, `--port`, `--surface`), `validate` and `env --host
  claude` (observational hooks); registration in `agent_braid/cli.py`. VIS.1b
  tasks add their own flags and tests. Files: `agent_braid/view_cli.py`,
  `agent_braid/cli.py`, `tests/test_view_cli.py`. Dependencies: T017, T019.
  Verification: procedure_011, procedure_012.
- [ ] T029 (REQ-013 / SC-013): Boundary tests (`tests/test_view_boundaries.py`)
  and regression run of governance, plugin package and validation profiles; rerun
  at the VIS.1b closure. Dependencies: T010–T013, T015–T017, T019, T020,
  T024, T026, T028. Verification: procedure_013.
- [ ] T034 (REQ-015 / SC-015): `docs/tooling/VIEWER.md`,
  `integrations/agent-braid-view/README.md`, tooling index and
  `tests/test_view_docs.py`; updated for VIS.1b at its closure. Dependencies:
  T028. Verification: procedure_015.
- [ ] T035 (REQ-015; Q-VIS1): Go/no-go checkpoint after the VIS.1a slice, by
  2027-01-31 (OD-8): the owner opens the viewer on census or real sessions, records a
  descriptive Q-VIS1 observation (procedure_hvis1) and the census result, and
  decides keep, re-scope or close as Deferred for VIS.1b and VIS.2–VIS.4. If the
  date passes without a slice, VIS.1 closes as Deferred. Dependencies: T029,
  T034, T038. Evidence: `evidence/checkpoint-<date>.md`.

## VIS.1b — Effort, recording, export and frames

- [ ] T014 (REQ-002 / SC-002): Host stream adapters (`claude -p` stream-json,
  `codex exec --json`) with the usage and identifier field allowlist, and the
  example replay `examples/view/loom-replay.jsonl` generated from owned fixtures.
  Files: `agent_braid/view_adapters.py`, `tests/test_view_adapters.py`,
  `tests/fixtures/view/streams/`, `examples/view/loom-replay.jsonl`.
  Dependencies: T035 (keep), T012. Verification: procedure_002.
- [ ] T018 (REQ-005 / SC-005): `view_otlp.py` OTLP HTTP/JSON logs and metrics for
  each host whose probe is `verified`, allowlist at every level, log bodies
  dropped, salting, `shape-unpinned`; `env` output for OpenTelemetry. Files:
  `agent_braid/view_otlp.py`, `tests/test_view_otlp.py`,
  `tests/fixtures/view/otlp/` (built from the T030 and T031 receipts).
  Dependencies: T035 (keep), T016, T030, T031. Verification: procedure_005.
- [ ] T039 (REQ-007 / SC-007): `--record`/`--record-effort` exclusive writing
  capped at 49 999 events plus one gap; ephemeral effort handling. Files:
  `agent_braid/view_serve.py`, `agent_braid/view_cli.py`,
  `tests/test_view_serve.py`. Dependencies: T035 (keep), T017, T018.
  Verification: procedure_007.
- [ ] T021 (REQ-007 / SC-007; REQ-008 / SC-008): `view_export.py` minimal export
  from a recorded or replay file (`--from`) with SPEC-043 destination rules,
  exclusive creation and absolute-path replacement; `export` subcommand. Files:
  `agent_braid/view_export.py`, `agent_braid/view_cli.py`,
  `tests/test_view_export.py`. Dependencies: T020, T039. Verification:
  procedure_007, procedure_008.
- [ ] T027 (REQ-011 / SC-011): `view_render.py` ASCII, braille, SVG and RGBA
  frames; `/frame.svg` and `/frame.txt`. Files: `agent_braid/view_render.py`,
  `tests/test_view_render.py`. Dependencies: T035 (keep), T020. Verification:
  procedure_011.
- [ ] T022 (REQ-009 / SC-009): Effort evidence pack: `--arm`, `--arm-note`,
  `--baseline`, pairwise comparisons in the harness comparison shape, escaped
  HTML, SVG and Markdown with a hostile-text corpus, non-claim statement and
  `host-estimate` labels inside `index.html` and every SVG chart. Files:
  `agent_braid/view_export.py`, `tests/test_view_export.py`. Dependencies: T021,
  T027. Verification: procedure_009.

## Closure (each delivery)

- [ ] T036: Pre-PR reviews (code review, quality, simplification),
  `validate_change --profile pr` on the stable candidate, `/speckit-converge`, at
  the VIS.1a and VIS.1b closures. Dependencies: the delivery's tasks.
- [ ] T037: Record obtained evidence in `assurance.json`, freeze, owner review of
  each delivery closure. Dependencies: T036.
