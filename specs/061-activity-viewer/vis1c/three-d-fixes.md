# 3D map fixes mapped to Three.js r186 (REQ-018, REQ-019)

The 3D view becomes the secondary "Mapa espacial 3D" (D7). Owner direction: guided
camera, auto-framing, legend, legible labels, controls with a help overlay and a reset
button. Decision D10: no new vendor file; ADR 0033 allows exactly `three.module.js`,
`three.core.js` and `OrbitControls.js`, all of which already expose what is needed.

API availability was checked against Three.js r186 documentation through Context7
(OrbitControls `enableDamping`, `dampingFactor`, `minDistance`, `maxDistance`,
`maxPolarAngle`, `screenSpacePanning`, `mouseButtons`, `touches`, `listenToKeyEvents`,
`cursorStyle`; `Vector3.project` for aligning HTML to 3D) and, per the audit, against
the vendored file (`zoomToCursor`, `listenToKeyEvents`, `keyPanSpeed`, `saveState`,
`reset`). T055 must re-confirm each name against the vendored bytes before use; a
missing API is a stop, not a reason to vendor another file.

## Problem to fix mapping

| Audit finding | Fix | Three.js r186 API and notes |
|---|---|---|
| P0-2 framing dominated by rings and slabs; hexagon gate cut by the canvas | Frame only lanes and events; draw governance as markers in a top lane or small planes at the lane origin instead of scene-sized rings | `new THREE.Box3().setFromObject(agentsGroup)`, `box.getBoundingSphere(sphere)`; distance `= sphere.radius / Math.sin(THREE.MathUtils.degToRad(camera.fov) / 2)` widened by aspect for narrow canvases; put frameable objects in `Layers` channel 1 or in one `agentsGroup` so gates, slabs and rings never enter the box; replaces the 120-iteration `fit()` |
| P1-1 no inertia, limits, keyboard; wheel traps page scroll; reset jumps | Damping, distance and polar limits, cursor-centred zoom, key support, scroll-friendly wheel, animated reset | `controls.enableDamping = true; dampingFactor = 0.08`; `minDistance = sphere.radius * 0.4`, `maxDistance = sphere.radius * 6`; `maxPolarAngle = Math.PI * 0.49`; `zoomToCursor = true`; `screenSpacePanning = true`; `mouseButtons = { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN }`; `touches = { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN }`; `controls.listenToKeyEvents(canvas)` with `canvas.tabIndex = 0` (arrows pan, `keyPanSpeed` tuned) |
| Page scroll trapped by wheel and touch | Wheel zooms only with Ctrl/Cmd or after the canvas has focus; otherwise the page scrolls. Touch: `touch-action: pan-y` by default, "Bloquear mapa" toggle enables one-finger orbit | `controls.enableZoom` toggled by a non-passive `wheel` listener (`preventDefault` only when allowed); `canvas` CSS `touch-action` via a class; never `user-scalable=no` |
| Damping needs frames (render-on-demand loop) | Request frames while the camera moves or damping has not settled | listen to `controls` `change`; keep `requestAnimationFrame` running until `controls.update()` returns false (r186 returns whether the camera changed) or a tween ends; stop afterwards. Pulsing materials only for hovered or selected objects (audit P2-3) |
| "Guided camera" | Preset buttons Lateral (looking along -Z, time horizontal, the near-2D view the user expects), Cenital, Isométrica and "Encuadrar (F)"; each is a tween of `camera.position` and `controls.target` | tween 220 ms, `--ease-out`, interruptible: a new input cancels and retargets from the current pose; `prefers-reduced-motion` sets position directly; `controls.saveState()` after framing so `controls.reset()` is available as the browser-style reset; the pose also restores on resize if the user never moved (keep, but the "Encuadrar" button always works and no longer depends on `userMoved`) |
| P0-3 labels illegible, overlapping, size in world units | HTML labels with fixed pixel size, projected each frame, with collision handling; lane labels pinned at the left edge | own overlay (D10): one `<div>` container above the canvas, `const v = new THREE.Vector3(); v.copy(anchor).project(camera); x = (v.x * 0.5 + 0.5) * clientWidth; y = (-v.y * 0.5 + 0.5) * clientHeight;` apply with `el.style.transform = "translate(...)"` (CSSOM, allowed by `style-src 'self'`); hide when `v.z > 1` (behind camera); `textContent` only; roughly 40 lines plus collision pass |
| Label collision | Priority list: selected, hovered, lane labels, conflicts, others on demand; greedy placement with rectangle overlap test, at most about 40 visible labels; the rest appear on hover or selection | collision computed in CSS pixels after projection, once per frame while moving; no per-frame layout reads: measure label sizes once per text change and cache |
| Raycast targets | Thicker invisible hit volume per lane so thin tubes are selectable | `Mesh` with `material.colorWrite = false; depthWrite = false` (still raycastable, unlike `visible = false`); `raycaster.layers` to restrict; tooltip anchored by the same projection helper; `Esc` clears selection |
| P1-2 legend text only | Compact legend line with the same SVG glyph symbols the 2D and table use; clickable to filter; long text moves to "Ayuda" | HTML/SVG outside the canvas; shares `visibleSeqs` filters with 2D (REQ-019) |
| 3D content | lanes grouped under their parent; conflicts as a large glyph plus text (predicted and observed distinct, [timeline-2d.md](timeline-2d.md#conflict-vocabulary)); "now" as a translucent plane in live mode; duration label at the lane end; unverified as source-level statement, per-event icon only for exceptions | geometry reuse, not new APIs; `InstancedMesh` for beads, cones and badges (phase polish) replaces one mesh per element under the existing 12,000-object cap |
| Resize | `ResizeObserver` already present; also refit on "Encuadrar" | unchanged API |
| Controls discoverability | Persistent small HUD (view presets, Encuadrar, Ayuda) and an overlay opened by `?`: Drag = orbit, right drag or Shift+drag = pan, Ctrl+wheel = zoom, arrows = pan, `F` = frame, `Esc` = deselect, two-finger = pan and zoom | help overlay component in [design-system.md](design-system.md#components); `controls.cursorStyle = "grab"` |
| Accessibility of a WebGL canvas | Canvas is not the only way in | the canvas has `role="group"`, an accessible name and `aria-describedby` to the help text; the table and timeline carry the full content; selection is mirrored to a live region |

## Not in scope (kept out on purpose)

- `CSS2DRenderer`, `Line2`/`LineMaterial`, `MapControls`, post-processing: each would
  be a new vendored file and an ADR 0033 amendment (decision D10: no). Constant-width
  lines at any zoom are therefore approximated by choosing tube radius from camera
  distance, and are optional.
- Any change to what a shape means beyond the vocabulary above; classes stay
  categorical badges.
- New third-party code of any kind; Node tooling.

## Acceptance (REQ-018, measured in T055/T056 and recorded as evidence)

At 1440 x 900 and 390 x 844 with `audit/fixture/rich.jsonl`: all nine lanes fit and
no lane label overlaps another without interaction; "Encuadrar" restores the view in
under 400 ms; wheel over the page scrolls the page unless Ctrl/Cmd is held or the
scene is locked; Tab reaches the canvas and arrows, `F`, `?`, `Esc` work; no console
CSP or Trusted Types violation; `tests/test_view_web_*` stay green. Performance
target 60 fps at 2000 elements is a measurement to record, not a promise.
