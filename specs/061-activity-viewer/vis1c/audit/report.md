<!-- Provenance: faithful English translation (2026-11-26) of report.es.md, the UX audit of 2026-11-04 written in Spanish.
The Spanish file stays the source evidence; this file is a reading copy and adds no findings. Line references were
valid for develop at e8060ac5 and may have moved. Synthetic fixture only; no owner data. Not an approval. -->

# UX audit of the "Loom" activity viewer (SPEC-061 VIS.1a)

Branch `develop` @ e8060ac5. Read-only: the repo was not touched. Own instance on `127.0.0.1:8791` with a synthetic
replay (`fixture/rich.jsonl`, 34 events, 9 lanes; generator `fixture/gen.py`; validated with `agent-braid view validate`).
The owner's viewer (`:8765`) was not used: its opening code is single-use.
Screenshots are in `screenshots/`. Code paths are relative to `integrations/agent-braid-view/web/` unless stated otherwise.

**How each finding was established**: [M] measured in the browser, [C] read in code, [I] inferred from screenshots.
**Lenses applied**: ui-ux-review (conductor; small app, <15 UI files, so no subagents: a11y, ux, system, measure and aesthetic applied in a single pass),
dataviz (encoding, legend, colour, 2D timeline design) and Context7 for Three.js r186. The lists from web-design-guidelines,
design:accessibility-review, emil-design-eng and apple-design were applied from memory as checklists (they were not loaded as separate Skills);
the motion review is from code, not from a video capture. **It was not tested with a real screen reader or with real owner data.**

## 1. Executive summary

The viewer is faithful to the contract (every element = one event, nothing claims guarantees) but it is designed from the model, not from the user's question.
The user asks "which agent did what, when, how long did it take and where did it collide". The page answers "which compatibility classes does each pair have".
Root causes, in order of impact:

1. **The X axis is not readable time.** The model compresses every gap >5 s to 0.5 s (`agent_braid/view_model.py:118-146`), the 3D view rescales everything to 24 units
   (`braid-scene.js:36,130`) and the web page **never shows** `axis.compressions` (grep: zero uses). 10 s and 500 ms look the same. There is no duration anywhere. [M][C]
2. **The camera and the scene are unreadable on opening.** The gate/grant rings have a radius the size of the whole scene and dominate the framing; the labels
   (sprites with `depthTest:false`) overlap in the event cluster. Zoom and orbit have no limits, no inertia and no keyboard. [M] (`01`, `03`, `05`)
3. **Key information is missing**: the agent that is active now, state (running/waiting/finished), duration per agent, conflict in human language. Part of the data exists
   (`strand.update.state/toolName`, open/close with `relMs`, `parentStrandId`) but the UI does not use it. [C]
4. **Wrong page hierarchy**: 4200 px tall, a long legal notice on top, evidence in a non-fixed column that is lost when selecting in the 3D view, a legend
   in text only (no colour/shape samples), 34/34 events marked "unverified" (the alert loses its signal). [M]
5. **Keyboard/screen-reader accessibility**: the canvas is not focusable, there are no keys, and the wheel over the canvas traps page scroll. [M]

Recommendation: (a) fix the 3D camera/labels/legend as a quick patch (Phase 1), (b) add a **2D timeline view in SVG** as the default view
(Phase 2), with shared state and filters, and (c) keep the 3D view as a secondary "spatial" view. The 2D view is possible without touching dependencies or the CSP (section 6).
This **contradicts the ADR 0033 decision** ("2D SVG... not as the primary surface the owner chose"): it needs an explicit owner decision.

## 2. Findings

### P0 (block understanding or using the view)

**P0-1. Time and duration cannot be read.** [M][C]
- Evidence: `view_model.py:118-146` compresses gaps; `loom.js` does not reference `axis`; `timeText` only shows raw `relMs` (`loom.js:160-163`: "114000 ms").
  In `04-scene-orbit.png` the events from 100 s to 115 s (analysis, waves) are stacked in ~1 unit while the first 95 s take up half the scene.
- Impact: it does not answer "how long did it take". A 6-minute gap is invisible. Risk of misreading (it looks simultaneous).
- Fix: proportional axis by default with a visible, labelled axis break ("−6 min 20 s", using `axis.compressions`); `m:ss` formatting; lane duration = close − open; for open lanes, duration up to "now" (see data gaps).

**P0-2. The initial framing and dominant objects break the scene.** [M][C]
- Evidence: `01-desktop-light-initial.png`: the red hexagon (gate `hazards-found`) and the blue/grey rings take up >60 % of the canvas and are cut by the edge; the real lanes
  end up in a minimal strip. Code: ring radius = `max(1.25, spanZ/2+1.0)` (`braid-scene.js:476`), `fit()` frames *everything*, including that (695-719).
  The rings are a plane perpendicular to time, so from the initial view they look like "walls".
- Impact: the first impression is chaos; the user does not find the agents.
- Fix: frame only lanes+events (Box3 of the "agents" group), render gates/grants as markers on a top "Governance" lane instead of giant rings; see section 4.

**P0-3. Unreadable, overlapping labels.** [M][C]
- Evidence: `05-scene-zoom.png` ("Edit README", "Edit ROADMAP", "class 0", "wave 0 started" overlapping); sprites with `depthTest:false`, size in world units (`braid-scene.js:536-572, 205-211`), cap of 400 with no collision handling.
  Zoomed out the text is microscopic (`04`), zoomed in it is enormous (`05`).
- Fix: HTML labels (CSS2DRenderer) with fixed size in px and anti-collision; lane label anchored to the left edge and always visible; the rest only on hover/selection.

**P0-4. No answer to "which agent is active / what happened / what collided".** [C]
- Evidence: `strand.update` (`state: running|waiting|idle`, `toolName`) only appears as a grey bead (`drawBead`, `braid-scene.js:496-507`); a lane without a close is drawn up to
  `TIME_LENGTH` (`braid-scene.js:234`), so *in progress* is indistinguishable from *lasted the whole time*; the conflict is a 0.2-unit toroidal knot labelled "class 0" (jargon).
- Fix: per-lane state (chip + "now" cursor), conflict with text "Edit ROADMAP and Second ROADMAP edit touch ROADMAP.md" (uses `sharedResources`, `reasons`).

### P1

**P1-1. Camera: no inertia, no limits, no keyboard, the wheel hijacks scroll.** [M][C]
- `new OrbitControls(camera, canvas)` with only `screenSpacePanning=true` (`braid-scene.js:615-616`): no `enableDamping`, `minDistance/maxDistance`, `maxPolarAngle`, `zoomToCursor`, `listenToKeyEvents`, `touches`. Measured: wheel over the canvas -> `scrollY` 165→165 (page trapped); `touch-action:none` (`style.css`) also traps touch scroll on mobile.
- One click on "Reset view" is the only support; no controls help; `userMoved` disables re-framing on resize (mobile: scene cropped, `09-light-mobile-scene.png`).
- Fix: see the table in section 4.

**P1-2. Legend in text only, no samples.** [C] `loom.js:62-76` and `renderLegend` (224-235): 13 long paragraphs, "Grey shapes", "Amber wire octahedron"; zero swatches. The colour per host (`HOST_COLORS`, `braid-scene.js:69`: blue/orange/green) appears in no coloured legend, and "Replay file / Hook and telemetry ingest" is implementation jargon.
- Fix: compact legend with SVG icons identical to those in the scene; clickable legend filter; the long text moves to a "Help" panel.

**P1-3. The detail (evidence) is not next to the selection.** [M] `aside` is `position:static`, page of 4200 px; hover state is painted below the canvas (`#scene-hover`, `index.html:42`), not next to the cursor. Selecting in 3D does not scroll to or highlight the panel; you have to scroll.
- Fix: sticky detail panel (or bottom sheet on mobile), tooltip next to the cursor, "Esc" deselects.

**P1-4. Ambiguous lane labelling with subagents of the same type.** [C] `view_hooks.py:196-198`: label = `agent_type` (e.g. "track-runner"); two equal subagents -> two lanes with the same name. Lane order is made by crossing pairs (`view_model.py:71`) and loses the parent/child hierarchy even though `parentStrandId` exists.
- Fix: label "track-runner #2" computed in the UI (ordinal by type and open time; no new data), lanes grouped under their parent.

**P1-5. "Unverified" alert with no signal.** [M] 34/34 elements with a dashed amber border and an amber octahedron in 3D (`02-desktop-light-full.png`); in replay and hooks *everything* is unverified, so the mark does not discriminate.
- Fix: verification mark at source level ("Source: hooks, not verified" once, in the filter bar) and a per-event mark only for the exception (verified or derived). Keep REQ-010 (distinct marker on crossing and gate): use a small icon, not a 3D octahedron.

**P1-6. 8-column table overflows (1266 px in 916) and 34 row tab stops.** [M] `table-wrap` scrolls horizontally; no sorting, no search; the subject of "strand state" events is an opaque id. Mobile `08-dark-mobile.png`.
- Fix: default columns Time, Agent, Event, State, Duration; the rest in the detail; cards on mobile; arrow-key navigation (roving tabindex) instead of one button per row.

**P1-7. Live: there is no "now".** [C] `scale = TIME_LENGTH/rawMax` (`braid-scene.js:129-131`) rescales the scene on every event; the model does not expose a server clock. The user cannot see that something is still running or for how long.

### P2

- **P2-1. Playback does not play time.** It advances 1 event every 700 ms (`loom.js:79`) even if the timeline is real; the note admits it ("does not replay real timing"). Offer a "real time x N" mode in addition to "by events".
- **P2-2. The no-claim notice takes the first fold** (`index.html:20-21`) with three technical chips (`executionAuthorization: false`). Keep it (governance) but as a one-line strip + "About".
- **P2-3. Permanent pulsing** (`braid-scene.js:656-669`) runs a continuous rAF while any pulsing material is visible; it respects `prefers-reduced-motion` (good) but costs battery. Pulse only on selection/hover.
- **P2-4. Dark theme is correct but canvas labels are rebuilt** with `rebuild()` on theme change (`:838`); the camera is not lost if `fitted` is already true, but it does cause flicker. Low impact.
- **P2-5. `title=` on 97 nodes** as the only carrier of meaning (tooltips do not exist on touch). Move to a visible legend/help.
- **P2-6. Motion density:** no transitions on selection (the selection box appears abruptly), no easing on "Reset view" (it jumps). Animate the camera towards the target over 200-300 ms with `easeOutCubic`; respect reduced motion.

### P3
- System font, no typographic hierarchy (everything 13.6-16 px); `--muted` contrast is fine (#5a5a55 on white ≈ 6.9:1; not a problem).
- `h2` "Braid scene (3D)": "braid" is internal jargon; rename to "3D spatial map".
- Interface texts are in English; the owner works in Spanish. Ask whether to internationalise.

### What is good (keep)
Every element tied to an event; table as a textual alternative; no-guarantee notice; hiding a source != absent; 3 px visible focus; `prefers-reduced-motion` and `forced-colors` handled; buttons >=36 px; no page horizontal scroll at 390 px; strict CSP; object cap.

## 3. What the 3D view does and why it confuses (mental model)
X axis time, Z one lane per strand, Y almost nothing. Crossings are geometry in the plane; classes are polygons with 3+n sides in the same colour; gates/grants are perpendicular rings. It is a vocabulary of ~13 shapes that the user must memorise (`loom.js:62-76`) and only one of them (conflict) answers a user question. The third axis (Y) encodes nothing: the 3D view adds no information that a 2D view lacks, it only costs camera and occlusion. Keeping it as a secondary spatial view is reasonable; it should not be the decision view.

## 4. Recommendations for the 3D view (mapped to Three.js r186)
Capabilities confirmed with Context7 (r186) and in the vendored file: `OrbitControls` has `enableDamping/dampingFactor`, `minDistance/maxDistance`, `maxPolarAngle`, `zoomToCursor` (:306), `listenToKeyEvents` (:585), `keyPanSpeed`, `saveState/reset`, `cursorStyle`, `touches`. `MapControls` is not vendored (adding it requires a manifest); it is not needed.

| Need | Three.js API | Note |
|---|---|---|
| Inertia and limits | `controls.enableDamping=true; dampingFactor=0.08; minDistance/maxDistance` derived from the `Box3`; `maxPolarAngle=Math.PI*0.49` | with damping `controls.update()` must be called in the loop (mind the on-demand rAF model: request frames while `controls` is moving) |
| Zoom to cursor, natural pan | `zoomToCursor=true`, `screenSpacePanning=true`, `mouseButtons={LEFT:ROTATE,MIDDLE:DOLLY,RIGHT:PAN}`, `touches={ONE:ROTATE,TWO:DOLLY_PAN}` | |
| Do not trap page scroll | `controls.enableZoom` only with Ctrl/Cmd+wheel or after focus/click; `touch-action:pan-y` on mobile with a "lock scene" mode | override with a `wheel` listener `passive:false` and conditional `preventDefault` |
| Keyboard | `listenToKeyEvents(canvas)` + `canvas.tabIndex=0`, `role="application"` or better `role="group"` with `aria-describedby` to the help; F = frame, Esc = clear selection | |
| Auto-framing | `new THREE.Box3().setFromObject(agentsGroup)`; `getBoundingSphere`; distance = `radius / sin(fov/2)` (or adjust by aspect); animate `camera.position` and `controls.target` with a 250 ms tween (easeOutCubic), respecting reduced motion | replaces the 120-iteration `fit()` (`braid-scene.js:695-719`); exclude rings/slabs (use `Layers`: layer 1 = frameable) |
| Guided views | Side (looking -Z, horizontal time = almost 2D), Top, Isometric presets; buttons | the side view is what the user expects |
| Readable labels | `CSS2DRenderer` (`three/addons/renderers/CSS2DRenderer.js`, **new vendored file**: manifest+hash, `BUNDLE_FILES`, import map -> changes the CSP hash; ADR 0033 amendment) or, without touching vendor, an **own HTML overlay** positioned with `vector.project(camera)` | the own overlay avoids widening the vendor boundary; cost: about 40 lines |
| Selection/hover | `Raycaster` already exists (`:775-786`); add `raycaster.layers`, a thicker invisible hit-target per lane (cylinder radius 0.25; `visible=false` does not work: use `material.visible=false` but raycastable via a `Mesh` with `colorWrite=false`) | HTML tooltip next to the cursor; `Esc` clears |
| Lines visible at any zoom | `Line2/LineMaterial` (fat lines, new addons) or keep `TubeGeometry` with a radius that depends on distance | optional |
| Performance | `InstancedMesh` for beacons/beads/cones (today one `Mesh` per element, cap 12000 objects); `renderer.setAnimationLoop` only while there is inertia/pulse | |
| Resize | `ResizeObserver` already exists; also re-frame after interaction if the user presses "Frame" | remove the dependency on `userMoved` |

Content changes for the 3D view: lanes grouped by parent, governance (grants/gates) as markers on a top lane, conflict with a large red icon + text, "now" as a translucent plane, duration labels at the end of the lane.

## 5. Proposal for a new 2D view (timelines, SVG)
Wireframes: `wireframes/01-layout-desktop.txt`, `02-timeline-2d.txt`, `03-3d-overlay.txt`, `04-timeline-2d.svg`.

**Screen model.** Top bar with a one-line summary (duration, no. of agents, no. of conflicts, no. of gaps), view selector (2D | 3D), filters and sources; main view; sticky detail panel; playback control; tabs (Table, Summary, Legend, Help).

**Shared state (a single source of truth)** — today it already exists partially in `loom.js` `state`; it is extended to:
`{ model, cursorMs, playing, speedMode, selectedSeq, hoveredSeq, hiddenSources, filters:{agent,status,onlyProblems,kind}, viewport:{t0,t1}, view:'2d'|'3d' }` + `derived` (`strands[]` with `{id,label,ordinal,parent,host,role,openMs,closeMs|null,state,durationMs,outcome,tools[],gaps[]}`; `conflicts[]` with the two strands, resources, reasons). Views are pure functions `render(state, derived)`; the 3D view receives `visibleSeqs` as now. A `deriveStrands(model)` function is the only new logic code and is tested in Python-JS parity with `view_model` (or moved to the server, see gaps).

**Encoding (dataviz).**
- X axis = proportional time (m:ss). Explicit axis breaks labelled with the omitted time (`axis.compressions`). "Nice" ticks (5/10/30 s, 1/5 min).
- One lane per strand; children indented under the parent (`parentStrandId`); fixed label on the left with the ordinal.
- Bar = [open, close]; solid fill = finished, hatched = in progress (right end "▶ now"), dotted = unobserved close/gap; result (`outcome`) as an icon at the end (✓ ok, ✕ error, ? unknown, ⊘ cancelled).
- Colour = host (3 categorical tones, fixed order, validate with `validate_palette.js` in light and dark) and **never** state/risk; state and conflict = shape + text + red/amber colour only in icons (state colours are reserved; do not use them for series). Text labels in ink, not in series colour.
- Thin marks inside the bar for `strand.update` (tool, `waiting` hatched) to see "what it is doing now".
- Crossings: a vertical line between two lanes at the event instant with an icon: ✕ conflict (+ text in the tooltip with shared resources), ⇄ independent candidate, → ordered, ? unknown; same REQ-010 rules (only independent = "swap"; an unknown is never painted as clean).
- Governance (planned/executed waves, grants, gates): fixed top lane "Governance"; planned waves = translucent bands "advisory plan, not a measurement"; gates/grants = icons with the state label.
- Hazards = triangle over the strand's lane (filled if observed; dashed outline if "not observed", as today).
- Observation gaps = dashed grey stroke on the lane with a ▯ icon and the reason on hover.
- Hover = tooltip (agent, state, start–end, duration, no. of tools); click = detail; arrow keys navigate events; `aria-label` per bar (`role="listbox"` pattern or synchronised table).
- Legend: one line with real samples (identical SVG), clickable to filter.
- Table and 2D share rows: the table is the textual alternative (WCAG) and is synchronised with the cursor.

**Interaction.** X zoom with wheel+Ctrl/pinch, pan by dragging, double click = frame, brush on the ruler, vertical playback cursor; a "live" mode that follows "now" with a "Back to now" button if the user scrolls away.

**Performance.** SVG up to ~300 lanes x 2000 elements; above that, virtualise by viewport or switch to Canvas 2D. Batch updates with rAF.

**Constraints it meets.** No dependencies: SVG created with `createElementNS` and presentation attributes; CSP `style-src 'self'` blocks the `style=` attribute but allows CSSOM (`el.style.x=`), CSS classes and SVG attributes (`fill`, `x`, `width`, `transform`); Trusted Types does not affect `createElementNS`/`textContent`; all text as a text node. New file `timeline.js` (and at most `timeline.css` or extending `style.css`) -> add to `BUNDLE_FILES` (`view_cli.py:51`) and to the bundle tests. No import-map change if it is loaded with dynamic `import()` like `braid-scene.js`.

## 6. Data / contract gaps
| UI need | State in `loom/v0.1` | Proposal |
|---|---|---|
| Duration of an agent | derivable: `strand.open`/`strand.close` with `relMs` (kept by the privacy contract: "Sub-day relative time") | derive on the client or `model.lanes[].openMs/closeMs/durationMs`. It does not violate privacy (it is not effect/cost) |
| "Now" / agent in progress | `axis.maxMs` = last event, not a server clock | add `axis.nowMs` (server monotonic clock) to the snapshot; no event schema change |
| Current state of an agent | `strand.update.state` (running/waiting/idle) and `toolName` | UI only; note: hooks only emit `PostToolUse`, so "running" is inferred from last activity (threshold) — label it "inferred" |
| Tool duration | no (the `PostToolUse` hook is not in the allowlist with duration; `tool_use_id` is discarded) | ask the owner whether a duration field is allowed (not content). Without it, only point marks |
| Agent result | hooks always close with `outcome:"unknown"` (`view_hooks.py:23,209`) | show an honest "?"; do not invent success |
| Conflict at execution time | only `crossing.classified: conflicting` (prior analysis, **prediction**); there is no real collision event (merge conflict, write rejection, ownership) | decide whether VIS.1b adds `conflict.observed` from `ownership-receipt`; until then label "conflict detected by analysis", not "occurred" |
| Wait/queue between agents | there is no "waiting for X" event (only `state: waiting` with no reference) | optional: `waitingOn` (strand id) — salted identifiers, already allowed |
| Distinct labels per agent | `label`=`agent_type` | ordinal on the client; no new data |
| Effort (tokens/cost) per agent | `effort.sample` exists, **is not drawn** and is ephemeral (REQ-007) | in the 2D view, an optional in-memory column, labelled `host-estimate`, never exported by default |
| Agent prompt/objective text | **forbidden** (message/prompt content is not retained) | do not propose; use `agent_type` + ordinal |
| Paths/files | only relative `evidenceRef` and `sharedResources` (analysis resource ids) | show as is; never absolute paths (the page uses `root N`) |
| Absolute timestamp | forbidden | use relative "X ago" only from the viewer's clock |

Privacy: the 2D view needs no field that violates `ui-security-privacy.md`; the suggested extensions (`nowMs`, `waitingOn`, tool duration) must go through the same allowlist and an owner decision.

## 7. Constraints the redesign must respect
- stdlib server (`view_serve.py`), loopback only, no outbound network, no new dependencies (ADR 0032).
- Web files: only those in `BUNDLE_FILES` (`view_cli.py:51`) plus `vendor/` by manifest with sha256 (ADR 0033; owner 2026-11-02: "only what is in the manifest"). Adding `CSS2DRenderer`/`Line2`/`MapControls` = new vendor -> receipt, manifest, hash, possible ADR amendment; prefer an own HTML overlay.
- CSP: `default-src 'self'; script-src 'self' 'sha256-<importmap>'; style-src 'self'; require-trusted-types-for 'script'` (`view_serve.py:353-366`): no `style=` in HTML and no inline `<style>`, no `innerHTML`; a second import map is forbidden.
- Every event value as a text node; no `eval`/`Function`/remote URL (`tests/test_view_web_bundle.py`).
- No claim of guarantee, safety order or speedup; `executionAuthorization:false` visible; classes = categorical labels, not ordered (REQ-010); unknown/unobserved is never painted as clean (REQ-003); colour is never the only carrier of meaning.
- Effort ephemeral and in memory only; minimal exports; no absolute timestamps or absolute paths.
- Table = complete textual alternative; without WebGL the page is still useful.
- The panel must work if an agent sees it in an embedded browser (the page text enters its context; avoid sensitive data).

## 8. Phased plan with acceptance criteria
**Phase 0 — Decisions (0.5 d).** Owner: 2D by default (ADR 0033 amendment), language, execution-time conflict gap, `nowMs`.
**Phase 1 — Quick 3D + page patch (2-3 d).** Camera (damping, limits, zoomToCursor, keyboard, page scroll not trapped, side/top views, agents-only framing, animation), HTML labels without collisions, legend with samples, sticky detail panel and tooltip, `?` help, "Frame", re-framing on resize.
 Acceptance: on opening the `rich.jsonl` fixture the 9 lanes fit and are readable without touching anything at 1440x900 and 390x844; no lane label overlaps; the wheel over the page scrolls the page except Ctrl+wheel; Tab reaches the canvas and F/arrows work; "Frame" restores the view in <400 ms; `tests/test_view_web_*` green.
**Phase 2 — Derived model + 2D view (4-6 d).** `deriveStrands`, `timeline.js`, shared state, axis break, duration and state per lane, crossings/conflicts with text, shared filters/sources, synchronised panel and table, playback by events and in time.
 Acceptance: with `rich.jsonl`, each bar shows exact start-end-duration (verified against `relMs`); the 10 s gap appears as a labelled break; the ROADMAP conflict is located in <5 s (test with 3 users or owner review); same selection in 2D/3D/table; dark mode and 390 px without horizontal scroll; axe/a11y without critical errors; keyboard focus to each bar; no `style=` or CSP violations in the console.
**Phase 3 — Live data (1-2 d, needs a decision).** `axis.nowMs`, "in progress" state, "now" tracking, `waitingOn`/`conflict.observed` if approved.
 Acceptance: an open agent grows in real time; when it closes it is fixed; "in progress" vs "finished" distinguishable in black and white.
**Phase 4 — Polish (2 d).** Compact table/mobile cards, micro-animations (200-300 ms, reduced-motion), reduction of the unverified chip, i18n, performance (InstancedMesh, on-demand pulse), visual regression tests with screenshots.
 Acceptance: Lighthouse a11y >=95 in both themes; 60 fps with 2000 elements in the 3D view; review with a real screen reader (VoiceOver) of the "select conflict" flow.

## 9. Open questions for the owner
1. Does the 2D timeline view become the **default view** (ADR 0033 amendment, which said the 3D view was the primary surface chosen)?
2. What does "conflict" mean to you: the analysis prediction (`conflicting`), or a real collision during execution? Today only the first exists.
3. Do we approve `axis.nowMs` and a wait field `waitingOn` and, if the hook offers it, tool duration (without content)?
4. Interface language: Spanish, English or both?
5. Can you share a screenshot/description of what you see on `:8765` (hooks only vs. hooks + analysis)? I could not open your session.
6. Do you accept widening the vendor boundary (CSS2DRenderer/Line2) or do we prefer own overlays only?
7. Do you want the long governance texts to stay always visible or move them to "About"?

## 10. Files
- Screenshots: `screenshots/01..09` (initial, full page, initial scene, orbit, zoom with overlapping labels, after click, dark desktop, dark mobile, light mobile).
- Fixture: `fixture/gen.py`, `fixture/rich.jsonl`. Wireframes: `wireframes/`.
