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
  least 3 of the 6 kinds overall). Done 2026-11-01:
  `evidence/census-20261101.json` (met: 48 sessions, 11 outside synthetic
  corpora, mostly self-development; 5 of 6 kinds; no grants).

## VIS.1a — Coordination slice

- [x] T010 (REQ-001 / SC-001): `view_loom.py`: constants, limits, strict JSON,
  `validate_event`, canonical bytes; schema parity test. Tests first. Files:
  `agent_braid/view_loom.py`, `tests/test_view_loom.py`, `tests/fixtures/view/loom/`.
  Verification: procedure_001. Done 2026-11-02: PR #950.
- [x] T011 (REQ-013 / SC-013): `activity-viewer` rule in
  `scripts/validate_change.py`, test in `tests/test_validation_profiles.py`,
  paragraph in `docs/development/VALIDATION_PROFILES.md`; assert that changes to
  the source modules and schemas the adapters read already escalate to the full
  tests, and add their patterns to the rule if not. Verification: procedure_013. Done 2026-11-02: PR #949.
- [x] T012 (REQ-002 / SC-002): Adapters for analysis reports first, then Git
  replay plans, scheduler preparations, grants and runtime state, each with a table
  of supported source schema versions and a `source-unsupported` gap otherwise.
  Files: `agent_braid/view_adapters.py`, `tests/test_view_adapters.py`,
  `tests/fixtures/view/artifacts/`. Dependencies: T010. Verification: procedure_002. Done 2026-11-02: PR #954.
- [x] T013 (REQ-002 / SC-002; REQ-003 / SC-003): Adapters for ownership notices
  and receipts (JSON only, every hazard unit kept), workflow-gate phases and
  results (no gate crossings), oversized pairs and absence cases. Files:
  `agent_braid/view_adapters.py`, `tests/test_view_adapters.py`,
  `tests/fixtures/view/artifacts/`. Dependencies: T012. Verification:
  procedure_002, procedure_003. Done 2026-11-02: PR #963.
- [x] T015 (REQ-006 / SC-006): `view_store.py` ring, seq, caps, eviction gaps,
  bounded subscriber queues. Files: `agent_braid/view_store.py`,
  `tests/test_view_store.py`. Dependencies: T010. Verification: procedure_006. Done 2026-11-02: PR #953.
- [x] T016 (REQ-004 / SC-004): `view_serve.py` loopback bind, one-time open code
  and read cookie, ingest token file and bearer check, `Host`, `Origin` and
  `Sec-Fetch-Site` checks, headers, body, connection and timeout limits, access
  logging off, route table. Files: `agent_braid/view_serve.py`,
  `tests/test_view_serve.py`. Dependencies: T015. Verification: procedure_004.
  The OTLP allowlist drops the names each probe receipt lists in
  `findingsForAllowlist`. Done 2026-11-02: PR #965.
- [x] T017 (REQ-004 / SC-004; REQ-006 / SC-006): SSE with `Last-Event-ID`,
  `/snapshot`, replay mode with `unverified` marking, `view_tail.py` bounded
  `--watch` polling without following symbolic links. Files:
  `agent_braid/view_serve.py`, `agent_braid/view_tail.py`,
  `tests/test_view_serve.py`, `tests/test_view_tail.py`. Dependencies: T016,
  T020. Verification: procedure_004, procedure_006. Done 2026-11-02: PR #969.
- [x] T019 (REQ-005 / SC-005): `view_hooks.py` observational Claude Code HTTP
  hooks with empty responses and refusal of decision events; dropped-attribute
  names inventory. Files: `agent_braid/view_hooks.py`, `tests/test_view_hooks.py`,
  `tests/fixtures/view/hooks/` (built from the T030 receipt). Dependencies: T016,
  T030 (`verified`). Verification: procedure_005. Per the T030 receipt, attribute
  subagents from hook `agent_id` (OpenTelemetry has none), do not depend on an HTTP
  `SessionStart`, and re-pin the `ui-security-privacy.md` allowlist in this change. Done 2026-11-02: PR #978.
- [x] T020 (REQ-003 / SC-003; REQ-010 / SC-010): `view_model.py` pure model:
  lanes, adjacent swap decomposition, `relMs` axis with gap compression, waves,
  verification markers, counters. Files: `agent_braid/view_model.py`,
  `tests/test_view_model.py`. Dependencies: T010. Verification: procedure_003,
  procedure_010. Done 2026-11-02: PR #961.
- [x] T024 (REQ-010 / SC-010): Web bundle without third-party code: table view,
  evidence panel, legend with "not a guarantee", Article 19 counters, unverified
  markers, playback controls and CSP. Files:
  `integrations/agent-braid-view/web/*`. Dependencies: T020, T017.
  Verification: procedure_010.
- [x] T023 (REQ-010 / SC-010; REQ-013 / SC-013): Vendor Three.js r186 prebuilt
  modules (`three.module.js`, `three.core.js`) and OrbitControls with
  `manifest.json`; add `LICENSES/three-MIT.txt`, the LICENSE paragraph, the NOTICE
  entry, the license marker in `scripts/validate_repository.py` and the
  THIRD_PARTY section; record an owner-run provenance receipt comparing the
  registry integrity of the pinned tarball with the vendored bytes. Dependencies:
  T003. Files: `integrations/agent-braid-view/web/vendor/**`, `LICENSE`,
  `LICENSES/`, `NOTICE`, `scripts/validate_repository.py`,
  `docs/development/THIRD_PARTY.md`, `specs/061-activity-viewer/evidence/`.
  Verification: procedure_010. Done 2026-11-02: PR #958. Receipt: `evidence/vendor-threejs-20261102.json`.
- [x] T025 (REQ-010 / SC-010): Three.js braid scene with the hashed import map,
  bound to the same model and evidence panel as the table view. Files:
  `integrations/agent-braid-view/web/*`. Dependencies: T023, T024. Verification:
  procedure_010.
- [x] T026 (REQ-010 / SC-010): `tests/test_view_web_bundle.py` (first-party: no
  remote URL, no `eval`, CSP, import map; vendored: manifest hashes once T023
  exists). Dependencies: T024. Verification: procedure_010.
- [x] T028 (REQ-011 / SC-011; REQ-012 / SC-012): `view_cli.py` with `serve`
  (`--replay`, `--watch`, `--port`, `--surface`), `validate` and `env --host
  claude` (observational hooks); registration in `agent_braid/cli.py`. VIS.1b
  tasks add their own flags and tests. Files: `agent_braid/view_cli.py`,
  `agent_braid/cli.py`, `tests/test_view_cli.py`. Dependencies: T017, T019.
  Verification: procedure_011, procedure_012.
- [x] T040 (REQ-006 / SC-006; amendment A2): the plugin keeps a private local
  copy of each `analyze-work` report in the workspace result root (owner-only
  permissions, never uploaded, retained 30 days, 64 MiB in total, oldest removed
  first). Files: `agent_braid/plugin_mcp.py` (or the tooling module it delegates
  to, plugin path only), `tests/test_plugin_mcp.py`. Dependencies: none.
  Verification: procedure_006.
- [x] T041 (REQ-006 / SC-006; amendment A1): `serve` discovers watch roots
  read-only from the registered plugin workspaces' result roots when `--watch` is
  absent; `--no-discover`. Files: `agent_braid/view_cli.py`,
  `tests/test_view_cli.py`. Dependencies: T028. Verification: procedure_006.
- [x] T042 (REQ-010 / SC-010; amendment A1): per-source checkboxes filtering the
  scene and table with a hidden-events count. Files:
  `integrations/agent-braid-view/web/*` (not `vendor/`),
  `tests/test_view_web_bundle.py`. Dependencies: T025. Verification:
  procedure_010. Done 2026-11-03 (#996) with all watched roots grouped under one
  checkbox; one checkbox per root is T044.
- [x] T043 (REQ-012 / SC-012; amendment A3): ship the web bundle and vendored
  files in the built package and resolve them from the installed package. Files:
  `build_support.py`, `pyproject.toml`, `agent_braid/view_cli.py` (bundle
  lookup only), `tests/test_view_packaging.py`. Dependencies: T028, T041 (shared
  `view_cli.py`). Verification: procedure_012. Done 2026-11-03: PR #1005.
- [x] T044 (REQ-010 / SC-010; amendment A1): one checkbox per watched root: a
  stable label per root that exposes no path, carried in the viewer model without
  changing the loom event contract. Files: `agent_braid/view_tail.py`,
  `agent_braid/view_model.py`, `integrations/agent-braid-view/web/loom.js`,
  `tests/test_view_tail.py`, `tests/test_view_model.py`,
  `tests/test_view_web_bundle.py`. Dependencies: T041, T042. Verification:
  procedure_010. Done 2026-11-03: PR #1003; the start banner maps each `root N`
  label to its path (VIS.1a closure PR).
- [x] T029 (REQ-013 / SC-013): Boundary tests (`tests/test_view_boundaries.py`)
  and regression run of governance, plugin package and validation profiles; rerun
  at the VIS.1b closure. Dependencies: T010–T013, T015–T017, T019, T020,
  T024, T026, T028, T040–T044. Verification: procedure_013. Done 2026-11-03:
  VIS.1a closure PR.
- [x] T034 (REQ-015 / SC-015): `docs/tooling/VIEWER.md`,
  `integrations/agent-braid-view/README.md`, tooling index and
  `tests/test_view_docs.py`; updated for VIS.1b at its closure. Dependencies:
  T028, T041, T043. Verification: procedure_015. Done 2026-11-03: VIS.1a closure
  PR.
- [ ] T035 (REQ-015; Q-VIS1): Go/no-go checkpoint after the VIS.1a slice, by
  2027-01-31 (OD-8): the owner opens the viewer on census or real sessions, records a
  descriptive Q-VIS1 observation (procedure_hvis1) and the census result, and
  decides keep, re-scope or close as Deferred for VIS.1b and VIS.2–VIS.4. If the
  date passes without a slice, VIS.1 closes as Deferred. Dependencies: T029,
  T034, T038. Evidence: `evidence/checkpoint-<date>.md`.

- [x] T045 (REQ-006 / SC-006; closure finding 1): the watcher walks directories
  newest name first, so the plugin's `analysis-<UTC stamp>-<id>` report copies load
  newest first and a store cap that is reached refuses the oldest copies (with its
  `stream-truncated` gap), never today's analysis. Files:
  `agent_braid/view_tail.py`, `tests/test_view_tail.py`. Dependencies: T040, T041.
  Verification: procedure_006. Done 2026-11-03: #1013.
- [x] T046 (REQ-004 / SC-004; closure finding 2): per-instance session cookie name
  `braid_view_<port>` (same `HttpOnly; SameSite=Strict; Path=/`), so two viewers on
  loopback no longer overwrite each other's session. Files:
  `agent_braid/view_serve.py`, `tests/test_view_serve.py`,
  `docs/tooling/VIEWER.md`, `specs/061-activity-viewer/contracts/ui-security-privacy.md`.
  Dependencies: T017. Verification: procedure_004. Done 2026-11-03: #1013.
- [x] T047 (closure review, VIS.1b follow-ups): findings 3 (hook strands never
  reopen after `SessionEnd`/`SubagentStop`; `_strands`/`_children` unbounded),
  4 (static bundle serves every non-dot file, not a manifest), 5 (slow-client
  timeout is per read), 7 (`IngestRefusal` and inventory limits live in
  `view_serve`), 8 (root labels in a module-level registry), 9 (behaviour tests
  for playback, SSE resume, evidence panel, scene fallback), 10 (simplifications:
  `_serve` split, ingest-token property, bundle path derivation, duplicated
  exception mapping and HTTP test helpers), 11 (copy pruning cost under lock,
  discovery once at start), 12 (wheel and sdist tests skipped without Python 3.12+
  and setuptools 68+). Source: `closure-packet-vis1a.md`. Dependencies: T036.
  Finding 3 design choice: a closed strand stays closed; later events for it leave a
  shape-unpinned gap, and reopening is deferred until a resumed-session contract exists.
  Done 2026-11-03 (#1025, #1026, #1029); closure findings 1, 2 and 6 were resolved earlier by #1013.

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

## VIS.1c — Viewer redesign (amendment of 2026-11-04)

Plan: [vis1c/](vis1c/README.md). Requirements REQ-016 to REQ-023. Nothing below is
started by the planning change. Gates G1 to G4 are owner decisions
([owner-decisions.md](vis1c/owner-decisions.md#gates-what-still-needs-a-human)); no
gate is implied by a passing test or a merged document. Parallelizable does not
authorize concurrent agents; run `analyze-work` on track footprints before two
concurrent tracks and see the file-ownership table in [vis1c/plan.md](vis1c/plan.md).

- [x] T050 (REQ-016 to REQ-023): VIS.1c planning package: spec amendment with
  verbatim owner decisions, plan, design system and copy guide, 2D timeline
  design, 3D fixes mapped to Three.js r186, contract v0.2 draft with privacy
  review, ADR 0033 amendment draft (Proposed), wireframes and audit artefacts.
  Files: `specs/061-activity-viewer/vis1c/`, `spec.md`, `tasks.md`. Evidence: merged in
  #1050 (ticked 2026-11-04). Does not implement the viewer and edits no ADR, schema or
  tracking source.
- [x] T051 (REQ-017, REQ-020): Owner review (G1) of the VIS.1c plan and open decisions
  OD-V1 to OD-V6, and decision (G2) on the ADR 0033 amendment draft; on acceptance a
  separate reviewed change applies it to `docs/adr/`. Dependencies: T050. Files:
  `vis1c/owner-decisions.md`, `vis1c/adr-0033-amendment-draft.md`,
  `docs/adr/0033-vendored-threejs-mit-boundary.md` (only after acceptance). Evidence:
  owner review record in this directory, ADR status change merged. Done
  2026-11-04: answers recorded verbatim in `vis1c/owner-decisions.md` and `spec.md`
  (G1 accepted with OD-V1 changed to detected language, G2 "Aceptar (Recommended)",
  OD-V3 F1 to F4); the amendment is applied to ADR 0033 with its hash updated in every
  `current` authority snapshot. G3 and G4 are authorised and scheduled (T052, T053).
- [x] T052 (REQ-022): Contract v0.2: privacy review (G3) of `axis.nowMs`, `waitingOn`
  and tool duration, then `loom-event.v0.2.schema.json`, the amendment of
  `ui-security-privacy.md`, `validate` support for both versions. Dependencies: T051.
  Files: `contracts/`, `agent_braid/view_model.py`, `agent_braid/view_cli.py`,
  `tests/test_view_loom.py`. Verification: SC-022. Done 2026-11-04: verdicts R1 to R15 in
  `vis1c/contract-v0.2-privacy-review.md`; v0.2 publishes optional `strand.update`
  members `toolDurationMs`, `waitingOn` and `waitingBasis` (v0.1 frozen and still
  accepted; `view validate` counts events per version; a replay drops `toolDurationMs`
  per OD-V4 (a)); `axis.nowMs` is written in the contract for T060; R12 is held (no
  allowlist change) and `collision.observed` (R13 to R15) is deferred to T063. No UI
  wiring; `view_model.py` needed no change.
- [x] T053 (REQ-014, REQ-022): Owner-run probe (G4) with a throwaway listener and no
  Loom code: record the names (never values) of the members the installed Claude Code
  sends for `PostToolUse` and `SubagentStop` hooks, specifically any duration member.
  Dependencies: T051. Files: `host-verification-runbook.md`, `evidence/`. Evidence:
  receipt in `evidence/`; a missing member is a valid result. Run 2026-11-04:
  receipt `evidence/hv-t053-20261104.json`, outcome `unobserved` (the
  disposable profile could not authenticate; no tool call ran); the T030 receipt already
  names `duration_ms` in `PostToolUse` on the same host version, type unrecorded.
  Closed 2026-11-04 by owner decision (no rerun): the T030 name evidence is accepted;
  T062 pins `PostToolUse.duration_ms` with a strict integer check and drops any other
  shape, and no duration member is assumed for `SubagentStop`.
- [x] T054 (REQ-016): Shared state and derived model: `state.js` with `deriveLanes`,
  conflicts, overlaps, concurrency and visibility; parity tests against
  `build_model` on the audit fixture and existing fixtures; decide whether lane
  fields move into `view_model.py`. Dependencies: T051. Files:
  `integrations/agent-braid-view/web/state.js`, `tests/test_view_web_behaviour.py`,
  `tests/test_view_model.py`. Verification: SC-016. Done 2026-11-04 (VIS.1c part A):
  the derivation stays in `state.js` (no field moved into `view_model.py`; parity is
  tested against `build_model` output on the audit fixture and the contract example in
  `tests/test_view_web_state.py`).
- [x] T055 (REQ-018): 3D camera: damping, limits, cursor zoom, keyboard, scroll not
  trapped, presets, "Frame all" with agent-only framing, tweened reset, reduced
  motion, pulse only on hover or selection. Dependencies: T051. Files:
  `integrations/agent-braid-view/web/braid-scene.js`. Verification: SC-018. Done 2026-11-04 (VIS.1c
  part B): damping, limits from the framed size, cursor zoom, keys, wheel only with Ctrl or
  Cmd (or focus, or lock), `pan-y` touch with a lock toggle, presets and an eased "Frame all"
  (agents only), pulse only on hover or selection. Deviation: the lateral preset is raised and
  the top view is the default, because agents lie along z and a view along -z stacks every lane.
- [x] T056 (REQ-018, REQ-019): 3D labels as first-party HTML overlay with collision
  handling, pinned agent labels, tooltip, help overlay, legend with glyphs. No
  vendor change. Dependencies: T055. Files:
  `integrations/agent-braid-view/web/braid-scene.js`, `tests/test_view_web_bundle.py`.
  Verification: SC-018, SC-019. Done 2026-11-04 (part B): HTML labels with collision handling and
  agent labels pinned at the left, hit volumes, a shared SVG glyph set, a legend line that filters
  every view and a help overlay. No floating 3D tooltip: the hover line and the labels carry it.
- [x] T057 (REQ-017): `timeline.js` 2D view behind the view switch: proportional axis
  with labelled breaks, lanes, bars, states, conflict vocabulary, tooltip, keyboard
  listbox, zoom and pan; add the new files to `BUNDLE_FILES` and packaging.
  Dependencies: T054. Files: `integrations/agent-braid-view/web/timeline.js`,
  `agent_braid/view_cli.py`, `tests/test_view_web_bundle.py`,
  `tests/test_view_packaging.py`. Verification: SC-017. Done 2026-11-04 (part B): `timeline.js` and
  `BUNDLE_FILES`. Deviations, none hidden: the "show omitted time" toggle is not built (breaks are always
  drawn); a lane with no close and no state is drawn with a dotted outline and no open arrow (more honest
  than "running"); no tooltip on keyboard focus (the row labels carry the facts); no polite live region; no
  bar text inside bars; planned waves are markers, not bands; no ruler brush, double-click frame, pinch or
  arrow-key cursor stepping in the timeline (buttons and keys 0, +, -, Home, End cover zoom and pan); gates,
  grants and waves have no keyboard path (the table is the text alternative); no forced-colors rules for
  the SVG; rows are 34 px, below 44 px on coarse pointers. These go to the T065 accessibility pass.
- [x] T058 (REQ-016, REQ-019, REQ-020, REQ-021): Page structure and design system:
  tokens, toolbar, sticky detail panel, summary and legend tabs, compact table and
  mobile cards, boundary strip and about panel, `strings.js` (es and en with key
  parity), URL hash state, palette validation in both themes. Dependencies: T054;
  integrates T056 hooks. Files: `integrations/agent-braid-view/web/loom.js`,
  `index.html`, `style.css`, `strings.js`, `tests/test_view_web_behaviour.py`.
  Verification: SC-016, SC-019, SC-020. Part A done 2026-11-04: page structure,
  tokens, toolbar and filters, sticky detail panel, tabs, boundary strip and help,
  `strings.js` with language detection (OD-V1 as accepted), URL hash state. Part B done
  2026-11-04: view switch, timeline and 3D HUD hooks. The dataviz palette validator was not run;
  contrast values stay as measured in the design system and the captures are receipts.
- [x] T059 (REQ-017): Make the 2D timeline the default view and 3D the secondary
  "spatial map". Dependencies: T057, T058, and ADR 0033 amendment accepted (G2).
  Files: `integrations/agent-braid-view/web/loom.js`. Verification: SC-017.
- [x] T060 (REQ-022): `axis.nowMs` and `axis.live` from the server clock, live "now"
  marker and growing running bars; replay `live=false`. Dependencies: T052, T057.
  Files: `agent_braid/view_model.py`, `agent_braid/view_serve.py`,
  `integrations/agent-braid-view/web/timeline.js`. Verification: SC-022. Done 2026-11-04:
  `build_model(now_ms=)` sets `axis.live` and `axis.nowMs` (clamped to the last event);
  `view serve` passes the hook ingest clock (same monotonic basis) unless `--replay` is given,
  so a replay is `live=false` with `nowMs` at the last event. The page advances now with its
  own clock between snapshots (once a second, paused while the pointer is over the
  timeline), draws a "now" line, runs open bars up to it (a long silence becomes a labelled
  break) and shows a live or replay badge in the header for both views; the 3D note states
  now. Deviation: no 3D now plane (the scene's x scale is fitted to events and clipped at the
  playback frontier). Receipts: `vis1c/evidence/t060-t062-live-timeline-es-1440.jpg`,
  `vis1c/evidence/t060-live-3d-es-1440.jpg`, from synthetic hook traffic on a private instance.
- [x] T061 (REQ-022): `waitingOn` and `waitingBasis` from scheduler, runtime and
  ordered-crossing sources, labelled declared or observed; waiting spans in the
  timeline. Dependencies: T052, T057. Files: `agent_braid/view_adapters.py`,
  `agent_braid/view_model.py`, `integrations/agent-braid-view/web/timeline.js`.
  Verification: SC-022. Done 2026-11-04: an analysis report's `ordered` pair whose operation
  lists the other in `dependencies` emits one v0.2 `strand.update` (`waiting`, `waitingOn` the
  other instance id, `waitingBasis` `declared`); a dependency naming no operation adds one
  `shape-unpinned` gap. The model carries the members as stated; the timeline outlines declared
  waits and its tooltip and the agent detail name the target and the basis. Deviation: scheduler
  preparations and runtime state carry no waiting signal (a later-wave worker opens when it
  starts), so they emit none; hooks emit none either (F2), so a hook-only session shows no wait
  and nothing is inferred. Receipt: `vis1c/evidence/t061-declared-wait-replay-en-1440.jpg`.
- [x] T062 (REQ-022): Tool duration end to end from the source T053 shows (or the
  OTLP `duration_ms` path if VIS.1b ships), retention per OD-V4, "time between
  events" fallback with its own label. Dependencies: T052, T053, T057. Files:
  `agent_braid/view_hooks.py`, `agent_braid/view_model.py`,
  `integrations/agent-braid-view/web/timeline.js`, `tests/test_view_hooks.py`.
  Verification: SC-022. Done 2026-11-04: `PostToolUse.duration_ms` is allowlisted for that
  event only (contract and privacy review R12 updated with the rationale); a JSON integer from
  0 to 86,400,000 becomes `toolDurationMs` on a v0.2 `strand.update`, and a bool, float, string,
  negative or oversize value is dropped with one `shape-unpinned` gap; no duration is assumed for
  `SubagentStop`. Memory only: a replay drops it, and no recorder or exporter exists. The timeline
  tooltip says "took N (stated by the host, shown live only)"; without a stated value it says the
  interval to the agent's next event, labelled as an interval; the agent detail sums the stated
  times. Receipt: `vis1c/evidence/t060-t062-live-timeline-es-1440.jpg`.
- [ ] T063 (REQ-023): Observed collision event and its timeline glyph, counter and
  tooltip, from the source chosen in OD-V5; boundary text in the contract. Dependencies:
  T052, T057, owner confirmation of OD-V5. Files: `agent_braid/view_adapters.py`,
  `agent_braid/view_model.py`, `integrations/agent-braid-view/web/timeline.js`.
  Verification: SC-023.
- [ ] T064 (REQ-023): Differential fields the owner accepts from OD-V3 (F1 lane
  parallelism and overlap, F2 waiting time, F3 prediction-versus-observation link,
  F4 effort per lane, F4 only after T035 and VIS.1b). Dependencies: T054, T057,
  owner acceptance per field. Files: `integrations/agent-braid-view/web/state.js`,
  `timeline.js`. Verification: SC-023.
  Added 2026-11-04 (owner request after real use): distinguishable lane labels. Every
  hook session lane currently reads "Claude session", so four sessions cannot be told
  apart. Give each lane a short, privacy-safe distinguishing label (for example a short
  salted session suffix, start time, or the basename of the working folder only if the
  allowlist review accepts it), shown in both views, the table and the detail panel.
- [ ] T065 (REQ-015, REQ-020, REQ-021): Bundle, CSP, key-parity and accessibility
  tests, contrast re-measure, captures at 1440 x 900 and 390 x 844 in both themes,
  keyboard-only walkthrough record, `docs/tooling/VIEWER.md` and `docs/tooling/`
  updates. Dependencies: T056, T057, T058, T059. Files: `tests/test_view_web_*.py`,
  `tests/test_view_docs.py`, `docs/tooling/VIEWER.md`. Verification: SC-020, SC-021.
  Added 2026-11-04 (owner request): also cover the lane-label disambiguation of T064 in
  the accessibility pass (labels read out distinctly by VoiceOver and keyboard focus).
- [ ] T067 (REQ-004): Open the viewer in another browser without restarting it. Today
  the one-time open code is per start, so once the integrated browser has used it, any
  other browser gets 404 until `view serve` restarts, which also drops the in-memory
  history. Owner request 2026-11-04: offer a new open link on demand, for example an
  `agent-braid view open` command that asks the running server (loopback, owner-only
  credential) for a fresh single-use code, and a "copy link for another browser"
  action in the page. Each code stays single-use and short-lived; existing cookies stay
  valid; nothing is logged. Dependencies: none. Files: `agent_braid/view_serve.py`,
  `agent_braid/view_cli.py`, web bundle, `contracts/ui-security-privacy.md`,
  `docs/tooling/VIEWER.md`, tests. Verification: a second browser opens the live view
  while the first stays connected, with no restart and no loss of history.
- [ ] T066 (all VIS.1c REQ): Closure: pre-PR reviews (code, quality, simplification),
  `validate_change --profile pr`, VoiceOver pass of "select a conflict", owner review
  of the "find the ROADMAP conflict" task, obtained evidence in `assurance.json`,
  freeze, owner closure review. Dependencies: every VIS.1c task the owner kept.

## VIS.1d — Dashboard relaunch (amendment of 2026-11-05)

Plan: [vis1d/README.md](vis1d/README.md), direction: [vis1d/direction.md](vis1d/direction.md).
Owner option recorded 2026-11-05: full dashboard and the redone 3D view (vis1d/README.md).
T063, T064, T065 and T067 stay open; VIS.1d folds their UI parts in where noted.

- [ ] T068 (REQ-024, REQ-027): Dashboard shell and tokens. Covers the app bar, the
  Now sentence, the KPI strip, the filter chips, the 12-column grid and its
  breakpoints, the tokens from direction.md in both themes, the help popover in
  place of the inline hint paragraphs, and the quiet read-only footer. es/en strings
  keep key parity. Files: `integrations/agent-braid-view/web/index.html`,
  `style.css`, `strings.js`, `loom.js`, `tests/test_view_web_*.py`.
  Verification: SC-024 (first-screen part), palette test.
- [ ] T069 (REQ-025, REQ-026): Live loom. Covers threads on a time axis, the running
  glow, waiting with its tether, finished lanes, subagent branches, tool beads, the
  now edge, the first-load draw-in, and the distinct lane labels (the T064 label
  part). Files: `timeline.js`, `state.js`, tests. Verification: SC-025 (loom part),
  SC-026.
- [ ] T070 (REQ-024, REQ-028): Details rail and its bottom-sheet form, KPI and noun
  selection, and playback docked in the hero with follow-now. Also T067
  `view open` (CLI, owner-only credential; the read cookie never mints codes), after
  the `contracts/ui-security-privacy.md` amendment (prerequisite). Files: `loom.js`, `index.html`,
  `agent_braid/view_serve.py`, `agent_braid/view_cli.py`, tests.
  Verification: SC-024, SC-028.
- [ ] T071 (REQ-025): Plan map and the collision and duration panels. The plan map
  has dependency columns, the three pair styles, hot nodes and a report selector.
  The collision panel lists predicted pairs, and observed ones only with a source
  (SC-023). The duration panel shows running and waiting per lane (F1, F2).
  Files: new first-party `planmap.js` (pinned in `BUNDLE_FILES`), `state.js`,
  tests. Verification: SC-025 (plan part).
- [ ] T072 (REQ-026, REQ-027): Explore 3D (the owner chose this option on
  2026-11-05, which reopens OD-V6). The tokens and thread styles of the loom, T064
  labels, plan-map glyphs in place of class text, eased camera presets,
  fly-to-selected, and reset and fit always visible. No new vendored file. Use
  Context7 for the Three.js r186 APIs. Files: `braid-scene.js`, tests.
  Verification: SC-026 (3D part), SC-027.
- [ ] T073 (REQ-024, REQ-027, T065 UI part): Audit and evidence. Run a Web
  Interface Guidelines audit; fix or waive each finding, with a reason. Take a
  keyboard-only walk and a VoiceOver pass of the lane labels (SC-026).
  Measure contrast again. Capture `vis1d/evidence/after-*.png` at 1440×900 and
  390×844 in dark and light, on the baseline instance data, in the four states.
  Update `docs/tooling/VIEWER.md`. Verification: SC-027.
- [ ] T074 (all VIS.1d REQ): Closure. Covers the pre-PR reviews, `validate_change
  --profile pr`, the owner review of the before and after captures, the obtained
  evidence in `assurance.json`, and the freeze. Dependencies: T068 to T073.

## Closure (each delivery)

- [ ] T036: Pre-PR reviews (code review, quality, simplification),
  `validate_change --profile pr` on the stable candidate, `/speckit-converge`, at
  the VIS.1a and VIS.1b closures. Dependencies: the delivery's tasks.
  VIS.1a part complete 2026-11-03: closure review #1011 (code, quality and
  simplification reviews), fixes #1013, and the pre-PR reviews and `pr` validation of
  the evidence and freeze PRs. The box stays open until the VIS.1b closure.
- [ ] T037: Record obtained evidence in `assurance.json`, freeze, owner review of
  each delivery closure. Dependencies: T036. VIS.1a: done 2026-11-03 (evidence #1017, which is the frozen
  candidate 62a44fb7; the owner closure approval record
  `owner-review-vis1a-closure-20261103.json` in the next PR). The box stays open until the VIS.1b closure.
