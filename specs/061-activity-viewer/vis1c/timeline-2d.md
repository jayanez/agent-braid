# 2D timeline view (default view, REQ-017)

Purpose: answer "which agent did what, when, for how long, and where did it conflict"
without learning the 3D vocabulary. Same facts as the 3D map and the table, drawn on a
readable time axis. Wireframes and the audit's encoding proposal are in
[audit/wireframes/](audit/wireframes/); this document is the normative version.

## Shared state model (REQ-016)

One state object and one derived model feed 2D, 3D and the table. Views are pure
functions of `(state, derived)` and never keep their own selection, filter or cursor.

```text
state = {
  model,                       // snapshot from the server, unchanged contract
  view: "timeline" | "map3d",  // default "timeline" after T059
  cursorMs, playing, speedMode: "events" | "real", speed,
  selectedSeq, hoveredSeq,
  hiddenSources: Set,          // existing semantics: hidden is counted, never absent
  filters: { agents: Set, status: Set, onlyProblems: bool, kinds: Set },
  viewport: { t0, t1 },        // 2D zoom window in axis time
  live: { following: bool }    // "Ir a ahora" resets following
}
derived = {
  lanes[]:     { laneIndex, strandId, label, ordinal, parentLane, host, role, declared,
                 openMs, closeMs | null, state: running|waiting|finished|unknown (+ inferred flag),
                 durationMs | null, outcome, toolMarks[], waitSpans[], gaps[] },
  conflicts[]: { kind: "predicted" | "observed", lanes: [a, b], resources[], reasons[], seq },
  overlaps[]:  { lanes: [a, b], fromMs, toMs },        // F1, derived
  concurrency: [{ tMs, open }],                         // F1, derived
  axis:        { mode, ticks[], breaks[], nowMs | null },
  visibleSeqs: Set                                      // already passed to the 3D scene
}
```

- `deriveLanes(model)` is the only new logic. It uses the model's per-event times and
  `strandId`/`parentStrandId` as emitted today. It is a pure function in a separate
  module (`state.js`), unit-testable without a browser, and tested for parity against
  `view_model.build_model` output on `audit/fixture/rich.jsonl` and on the existing
  test fixtures (REQ-016 acceptance). If parity proves brittle, move the derivation to
  `view_model.py` and add `lanes[].openMs/closeMs/durationMs` additively to the model
  (not the event contract); decide in T054.
- State mapping: schema `strand.update.state` `running` and `waiting` map to running and waiting; `idle` maps to "inactivo" (open, no recent activity, shown as running with a lighter hatch and the label "(inferido)"); a lane with a `strand.close` is finished with its `outcome` (`ok`, `error`, `unknown`, `cancelled`); a lane with no state and no close is unknown.
- Label disambiguation (audit P1-4): lanes with the same `agent_type` get an ordinal by
  opening time ("track-runner #2"). No new data.
- Hierarchy: a child lane is drawn indented under its parent by `parentStrandId`;
  orphan children go under "Sin padre conocido" and are never attached by guesswork.
- Deep link: `view`, `selectedSeq`, `viewport` and filters serialize to the URL hash so
  a state can be reopened or shared on the same machine. The hash never contains event
  values, only ids already in the page.

## Time axis

| Rule | Detail |
|---|---|
| Default | proportional to real elapsed time in the model's `relMs` basis, format `m:ss` (`h:mm:ss` over one hour); ticks at 1/5/10/30 s or 1/5/10 min chosen so 6 to 10 labels fit |
| Breaks | the model compresses every gap above 5 s to 0.5 s (`view_model._time_axis`, `axis.compressions[]`). The 2D draws a visible zigzag break at the compressed position and labels the omitted span ("Tiempo omitido: 6 min 20 s") from `compressions[].spanMs`. A break is never silent. |
| Proportional-without-breaks | toggle "Mostrar tiempo omitido" renders the true span (scrolls horizontally inside the view); breaks are the default so a quiet hour does not flatten a busy minute |
| Sequence-only events | the model gives them their predecessor's time; they are drawn at that time with a dotted outline and the tooltip says "sin hora propia" |
| Zoom and pan | wheel with Ctrl or Cmd, pinch and the `+`/`-` keys zoom in X around the pointer or cursor; drag pans; double-click or `0` frames all; a brush on the ruler selects a window; `Home`/`End` jump to start and end; buttons duplicate every gesture |
| Playback cursor | one vertical line across all lanes at `cursorMs`, same position the 3D and the table use; arrow keys step it by event, `Shift`+arrow by tick |
| Now | in live mode the axis has a "ahora" marker at `axis.nowMs` (REQ-022); running bars extend to it; if the user scrolls away a button "Ir a ahora" returns. Without `nowMs` (today) running state is drawn up to the last event and labelled "(inferido)". |

Absolute timestamps are never shown (privacy rule); only elapsed time in the session
and, in live mode, "hace 12 s" computed by the viewer's own clock.

## Lanes and bars

| Element | Encoding |
|---|---|
| Lane label | left edge, fixed while panning; main session first, then each parent followed by its children; status icon, name, ordinal; duration right-aligned in `tabular-nums` |
| Bar span | `[openMs, closeMs]`; running lane extends to now (or the last event) with an open arrow end |
| Bar fill | host colour token plus pattern: solid = finished, hatched = running, dotted outline = end not observed, light hatch segments = waiting |
| Bar text | the lane label if it fits, otherwise none; text in ink colour, never white on series colour |
| Outcome glyph at the end | finished ok `✓`, error `✕`, unknown `?`, cancelled `⊘`; hooks currently always close with outcome unknown, so the glyph is `?` and no success is invented |
| Tool marks | thin ticks inside the bar for each `strand.update` or `PostToolUse` with the tool name in the tooltip; tool *duration* shown only when REQ-022 provides it (otherwise the tooltip says "intervalo hasta el siguiente evento", labelled as such) |
| Governance lane | fixed top lane "Gobierno": planned waves as translucent bands (labelled "plan asesor, no medición"), runtime wave markers framed, grants as ring glyphs, gates as polygon glyphs with the state word |
| Hazards | triangle on the lane; filled = observed, dashed outline = not observed (existing semantics) |
| Observation gaps | grey dashed stretch plus `▯` and the reason in the tooltip |
| Unverified | one source-level statement in the toolbar when everything from a source is unverified ("Fuente: hooks, no verificada"); a per-element marker only for the exception (a rehashed or derived element), per audit P1-5. REQ-010 still requires a distinct marker on crossings and gate results: a small icon, not a 3D octahedron |

## Conflict vocabulary

Two meanings, never merged (owner decision D8). Each has its own glyph, word and
colour treatment; both carry the word, so colour is never alone.

| | Predicted conflict | Observed collision |
|---|---|---|
| Source | analysis `crossing.classified` with class `conflicting` (available) | two agents touched the same resource during the session (needs new data, T063) |
| es / en | "Posible conflicto" / "Possible conflict" | "Colisión observada" / "Observed collision" |
| Glyph | hollow `✕` in a dashed circle | solid `✕` in a filled rounded square |
| Where | vertical connector between the two lanes at the crossing's event position, dashed stroke | connector at the time the second touch was observed, solid stroke, plus a shaded band over the overlapping period |
| Tooltip | "según el análisis; no implica que ocurriera" plus shared resources and reasons | what was touched and by whom, relative times |
| Never | drawn as "happened"; counted together with observed ones | inferred from the prediction; shown without a source event |
| Counter | "posibles conflictos" | "colisiones observadas" (absent, not zero, until the source exists) |

Absence rule: until observed collisions can be produced, the counter and legend entry
for them do not render a zero. A zero would read as "none happened"; the summary says
"no se detectan colisiones: este visor aún no las observa" (REQ-003).

Other crossings: independent candidate `⇄` in `--state-ok`, ordered `→`, unknown `?`
with dashed link; only an independent candidate may be drawn as a swap or bridge
(REQ-010); a class is a categorical label with no ordering.

## Interaction and keyboard

- Hover or focus: tooltip (agent, state, start to end, duration, tool count). Click or
  Enter: select; the detail panel shows lane, parent, events, conflicts, verification,
  evidence reference, and a "Campos del modelo" disclosure.
- Lanes are one tab stop (`role="listbox"`, roving `tabindex`): `Up`/`Down` move between
  lanes, `Left`/`Right` between that lane's events, `Enter` selects, `Esc` deselects,
  `?` opens help, `f` or `0` frames all, `+`/`-` zoom, `Home`/`End`. Keyboard
  navigation does not animate (frequent action); pointer-driven zoom eases for 160 ms
  and is interruptible.
- The "Eventos" table is the text alternative and stays in sync (row selected = bar
  selected, and the reverse); on mobile it renders as cards.
- Filters (sources, agent, status, problems only, kinds) act on 2D, 3D and table
  identically through `visibleSeqs`; hidden events remain counted in the summary.

## Rendering constraints and performance

- SVG built with `document.createElementNS` and presentation attributes
  (`x`, `width`, `fill`, `transform`); classes from `style.css`; CSSOM assignment only
  where a value is dynamic. No `style=` markup, no `innerHTML`, all text as text
  nodes (existing `tests/test_view_web_bundle.py` rules). Glyphs are `<symbol>`/`<use>`
  defined once.
- One `<g>` per lane with its own transform; only `transform` and `opacity` animate.
- Budget: up to 300 lanes by 2000 elements in SVG; above that the view virtualizes by
  viewport and lane (draw only visible rows and the elements in `[t0, t1]`), with the
  existing object cap and truncation notice (`stream-truncated`) unchanged. Updates are
  batched in one `requestAnimationFrame`; live updates append and retarget rather than
  rebuild.
- Without WebGL and without any 3D file loaded, the timeline works (3D is loaded by
  dynamic `import()` only when selected, as `braid-scene.js` is today); no second import
  map. New files `state.js`, `timeline.js`, `strings.js` join `BUNDLE_FILES`
  (`agent_braid/view_cli.py`) and the packaging list (T043 mechanism).

## What is deliberately absent

No effort or token columns until VIS.1b data exists (F4); no prompt, goal or message
text; no absolute path or time; no success/failure inference from silence; no ranking
of lanes, classes or agents; no speedup, efficiency or "parallelism achieved" claim:
the concurrency band (F1) is a count of open lanes, nothing more.
