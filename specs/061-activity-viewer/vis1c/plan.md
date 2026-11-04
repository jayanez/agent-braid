# VIS.1c plan

Plan only. Requirements are REQ-016 to REQ-023 in the "VIS.1c amendment" section of
[spec.md](../spec.md); tasks T050 to T066 in [tasks.md](../tasks.md). Constitution
gates: claim level stays "inspiration" (Article 17); the braid is a representation
(Article 18); evidence limits as in [README.md](README.md#evidence-boundary).

## Summary of the technical approach

1. **One state, three views.** `state.js` holds the state and the pure derivations
   (`deriveLanes`, conflicts, overlaps, concurrency, visibility); `loom.js` becomes the
   shell (fetch, SSE, routing, playback, panels). `timeline.js` renders 2D;
   `braid-scene.js` renders 3D from `visibleSeqs` as today; the table renders from the
   same state. No view keeps private selection or filters.
2. **2D first-class, default after acceptance.** The 2D timeline ships behind a view
   switch (T057) and becomes the default only after ADR gate G2 (T059).
3. **3D repaired, not extended.** Camera, framing, labels, legend and help
   ([three-d-fixes.md](three-d-fixes.md)); no new vendor file.
4. **Design system and copy** ([design-system.md](design-system.md)) applied to the
   whole page: tokens, one glyph set, one vocabulary, sticky detail panel, compact
   table and cards, a toolbar, help and about.
5. **Contract v0.2** ([draft](contract-v0.2-amendment-draft.md)) only after privacy
   review (G3); the UI degrades honestly when fields are absent.

## Phases

| Phase | Tasks | Delivers | Needs |
|---|---|---|---|
| 0 Decisions | T051, T052, T053 | owner review of this plan and open decisions; ADR 0033 amendment decision; contract v0.2 privacy review (gate G3, then the schema and validator code of T052); owner-run probe of the hook payload for a duration member | owner |
| 1 3D and page patch | T055, T056 | guided camera, framing, HTML labels, legend with glyphs, help overlay, reset | T051 |
| 2 State and 2D | T054, T057, T058, T059 | shared state, timeline, page structure, copy, i18n, detail panel, table compact; 2D default | T051; T059 also G2 |
| 3 Live and new data | T060, T061, T062 | `axis.nowMs` and live mode, `waitingOn`, tool duration | G3 (T052); T062 also T053 |
| 4 Differential and polish | T063, T064, T065 | observed collision, accepted differential fields, bundle/CSP/a11y/visual tests, `VIEWER.md` | owner decisions OD-V3, OD-V5 |
| Closure | T066 | pre-PR reviews, evidence, freeze, owner review, VoiceOver pass | all |

Estimates carried over from the audit as planning sizes, not commitments: Phase 1 two
to three days, Phase 2 four to six, Phase 3 one to two (plus gate time), Phase 4 two.

## File ownership (for parallel tracks)

| Files | Owner task(s) |
|---|---|
| `integrations/agent-braid-view/web/braid-scene.js` | T055, T056 only |
| `integrations/agent-braid-view/web/state.js`, `timeline.js`, `strings.js` (new) | T054, T057, T058 |
| `integrations/agent-braid-view/web/loom.js`, `index.html`, `style.css` | T058 integrates; T056 touches only the 3D HUD container hooks and must land first or hand its hooks to T058 in writing |
| `agent_braid/view_cli.py` (`BUNDLE_FILES`), packaging lists | T057 (adds files) |
| `agent_braid/view_model.py`, `view_hooks.py`, `view_serve.py`, contract files | T060, T061, T062 after G3 |
| `tests/test_view_web_bundle.py`, `test_view_web_behaviour.py`, `test_view_model.py`, `test_view_docs.py` | the task that changes the behaviour; T065 consolidates |
| `docs/tooling/VIEWER.md` | T065 |

`loom.js`, `index.html` and `style.css` are shared by Phases 1 and 2, so the safe
split is: Phase 1 track owns `braid-scene.js` only; Phase 2 track owns the shell. Run
`analyze-work` (Agent Braid plugin) on the track footprints before running two tracks
at once; two concurrent tracks maximum, as always.

## Validation approach

- Unit: JS derivations tested through the existing behaviour-test mechanism
  (`tests/test_view_web_behaviour.py`) with parity against `view_model.build_model`
  on the audit fixture and existing fixtures; contract validators for v0.2 (T052).
- Bundle: extend `tests/test_view_web_bundle.py` to the new files (no remote URL, no
  `eval`, no `innerHTML`, no `style=`), CSP unchanged, vendor manifest unchanged
  (a failing manifest hash is a stop, not a manifest edit).
- Strings: `es`/`en` key parity test; no hard-coded user-facing text outside
  `strings.js` except event values.
- Browser evidence (owner-run or local, recorded as receipts, not as proofs): captures at
  1440 x 900 and 390 x 844, light and dark, replay of `audit/fixture/rich.jsonl`;
  console free of CSP and Trusted Types violations; keyboard-only walkthrough;
  automated accessibility scan; contrast re-measure of the palette; frame-time
  measurement at 2000 elements. These support, but do not establish, usability.
- Human: owner review of the "find the ROADMAP conflict" task (audit target: under
  5 s), VoiceOver pass of "select a conflict", owner acceptance at closure.
- Repository gates: `python3 -m scripts.validate_spec_kit`, the CI `validate`
  aggregate, `validate_change --profile pr` for this planning change.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| 2D default reads as stronger claims ("timeline = what happened") | descriptive wording, the boundary strip, predicted versus observed vocabulary, "(inferido)" labels, no zero counter for unobservable things |
| Time compression misread | breaks always drawn and labelled; toggle for true span |
| Hook-only sessions give thin data (no close outcome, no waiting) | honest `?` and inferred labels; F2/F3 degrade; do not synthesize |
| Two views drift apart | one state model, one glyph set, parity tests, one copy module |
| `deriveLanes` in JS diverges from the model | parity test; fallback of moving the derivation into `view_model.py` additively |
| Label collision cost per frame | measure once per text change, greedy pass only while moving, cap about 40 labels |
| A tool-duration probe finds no member | T062 degrades to "intervalo entre eventos"; no contract change needed beyond optional member |
| Scope creep into effort (VIS.1b) | F4 explicitly depends on T035 and VIS.1b |
| i18n doubles review surface | single `strings.js`, key-parity test, English fallback per key |
| Rewriting hashes of pinned evidence | none planned; no edits to pinned authority files in this change; ADR and contract changes are separate reviewed changes after acceptance |

## Out of scope

Anything VIS.1b (OTLP ingest, effort, recording, export, frames), VIS.2 to VIS.4, a
canvas or WebGL renderer for the timeline, new vendored code, mod pane, any write path
or control that changes what the host does.
