# ADR 0033 amendment (draft): 2D timeline as the default view; no vendor change

- **Status:** Proposed. Drafted 2026-11-04 for owner acceptance. **Not accepted, not
  applied.** `docs/adr/0033-vendored-threejs-mit-boundary.md` is unchanged by this
  change; on acceptance a separate reviewed change edits it (or issues an ADR that
  amends it) and records the owner's answer verbatim.
- **Date:** 2026-11-04
- **Deciders:** Juan Antonio Yáñez García (owner)
- **Constitutional articles:** 21 (as ADR 0033)
- **Specification:** [SPEC-061](../spec.md) VIS.1c amendment (REQ-017, REQ-018)
- **Owner decisions this draft depends on (2026-11-04, verbatim):** D7 "Sí, 2D por
  defecto (Recommended)" to "¿La vista 2D pasa a ser la vista por defecto del visor?";
  D10 "No, overlays HTML propios (Recommended)" for vendoring.

## Context

ADR 0033 accepted Three.js r186 and listed, among the alternatives considered:
"SVG-only 2D viewer. Kept as the frame and table fallback, not as the primary surface
the owner chose." The VIS.1a viewer therefore opens on the 3D scene. A UX audit of
the shipped viewer (2026-11-04, [audit](audit/report.es.md)) found that the third axis
encodes no information the 2D lanes lack, that the camera and labels hide the
agents, and that the owner cannot answer "which agent is active, what conflicted, how
long" from the 3D scene. On 2026-11-04 the owner chose the 2D timeline as the default.

## Decision (proposed)

1. **Default surface.** The primary and default view is a first-party 2D SVG timeline
   (one lane per agent, proportional time axis). The 3D scene becomes the secondary
   "spatial map", selectable and linked to the same state. A deep link or stored choice
   may still open the 3D view.
2. **Alternatives table.** The ADR 0033 line "SVG-only 2D viewer ... not as the
   primary surface the owner chose" is superseded by this decision for the 2D view
   only: the 2D view is the default surface, **and Three.js remains vendored and
   supported** for the secondary view. Nothing is removed.
3. **No vendor change.** The vendored file list stays exactly `build/three.module.js`,
   `build/three.core.js` and `examples/jsm/controls/OrbitControls.js`. The 2D view
   adds **no third-party code**. `CSS2DRenderer`, `Line2`/`LineMaterial` and
   `MapControls` are not vendored; HTML labels are first-party and positioned by
   `Vector3.project` (owner decision D10). Any future addon still needs a separate
   amendment, as ADR 0033 already states.
4. **First-party code boundary.** New first-party files (`state.js`, `timeline.js`,
   `strings.js`) are added to the served bundle list (`BUNDLE_FILES`) and to the package
   (T043 mechanism). They fall under the existing first-party rules: no remote
   URL, no `eval` or `new Function`, no `innerHTML`, all values as text nodes, no
   `style=` markup, one import map only.
5. **CSP unchanged.** `default-src 'self'; script-src 'self' 'sha256-<importmap>';
   style-src 'self'; require-trusted-types-for 'script'` stays as is. SVG is created
   with `createElementNS`; dynamic values use CSSOM property assignment, which
   `style-src 'self'` permits. The import-map hash does not change unless the map does
   (it does not).
6. **Fallback preserved.** The table remains the complete text alternative; the
   timeline works without WebGL, and 3D loads by dynamic `import()` only when chosen.

## Alternatives considered

| Option | Verdict |
|---|---|
| Keep 3D as the default and only fix the camera | Rejected by the owner (D7); fixes still ship for the secondary view |
| Add `CSS2DRenderer` for labels | Rejected by the owner (D10): new vendored file, new manifest, receipt and amendment for about 40 lines of first-party code |
| Remove 3D | Rejected: the owner keeps it as a spatial view; freezing it after Phase 2 is open decision OD-V6 |
| Canvas 2D for the timeline | Deferred: SVG covers about 300 lanes by 2000 elements with accessible structure; virtualize first, Canvas only if measurement requires it |

## Consequences

- Positive: the first screen answers the user's questions; the default surface has no
  WebGL dependency; one fewer reason to review vendor changes.
- Negative: two views to keep consistent (mitigated by one shared state model and one
  glyph set); the 3D investment slows after Phase 2 if OD-V6(b) is chosen.
- Compatibility: SPEC-061 REQ-010 ("the Three.js scene") is superseded only for the
  default-view clause; its fact-binding, vocabulary and no-claim rules apply to the
  2D view unchanged. REQ-013 (repository boundaries) and the vendor manifest tests are
  unaffected. No license-map change.
- Security: unchanged boundary (loopback, strict CSP, no remote load); new code is
  first-party and covered by the same bundle tests.

## Validation

`tests/test_view_web_bundle.py` extended to the new files (no remote URL, `eval`,
`innerHTML`, `style=`; manifest hash unchanged for vendor files; CSP header unchanged);
`tests/test_view_packaging.py` checks the new files ship; the vendored manifest test
must pass with no manifest change. Acceptance of the amendment itself is a human
decision and is not implied by any test.

## Acceptance record (to be filled by the owner)

Owner answer (verbatim): _pending_. Date: _pending_. Applied to ADR 0033 by: _pending_.
