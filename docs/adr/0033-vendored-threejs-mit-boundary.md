# ADR 0033: MIT boundary for vendored Three.js

- **Status:** accepted by explicit founder decision on 2026-11-01 (founder's answer, verbatim: "Aceptar ambas, r186"), with the pin moved from the proposed r182 to r186; amended 2026-11-04 (2D timeline as the default view, no vendor change), accepted by the owner (answer, verbatim: "Aceptar (Recommended)")
- **Date:** 2026-10-31
- **Deciders:** Juan Antonio Yáñez García (founder)
- **Constitutional articles:** 21
- **Specification:** [SPEC-061](../../specs/061-activity-viewer/spec.md) (track VIS.1)

## Context

The activity viewer (ADR 0032) renders a three-dimensional braid in the browser.
Three.js is the established WebGL/WebGPU library for this and is distributed under
the MIT license. The repository has no Node toolchain and loads no remote resources
in the viewer, so the library must be vendored as static files. `GOVERNANCE.md`
requires an explicit founder decision and a permanent record for a license
boundary change; ADR 0012 is the precedent for MIT material.

## Decision

Vendor exactly these prebuilt ES module files from the npm package `three` at
the pinned version r186 (`0.186.0`, published 2026-09-08), unmodified:

- `build/three.module.js`
- `build/three.core.js` (imported by `three.module.js` in r186)
- `examples/jsm/controls/OrbitControls.js`

Any other file, including post-processing addons, needs an amendment of this
decision.

They live under `integrations/agent-braid-view/web/vendor/three/` with the
upstream `LICENSE` file. `integrations/agent-braid-view/web/vendor/manifest.json`
records package name, version, tarball URL, tarball SHA-512 integrity, and the
SHA-256 of every vendored file. The license text is added as
`LICENSES/three-MIT.txt`; `LICENSE` gains a paragraph naming the directory as
MIT-covered third-party material; `NOTICE`, the license markers in
`scripts/validate_repository.py` and `docs/development/THIRD_PARTY.md` gain
entries, as for ADR 0012. An owner-run provenance receipt records that the
registry integrity of the pinned tarball matches the manifest and that the
extracted files match the vendored bytes; a hash test alone cannot detect a change
that edits both a file and the manifest. Updates repeat the manifest and the
receipt and require review; no other third-party web code is vendored under this
decision, and inlining these files elsewhere (for example in an MCP App) needs an
amendment.

## Alternatives considered

- **CDN import.** Rejected: remote resource, privacy and offline use.
- **npm and a bundler.** Rejected: adds Node to the toolchain and CI.
- **Hand-written WebGL.** Rejected: large maintenance cost for no semantic gain.
- **SVG-only 2D viewer.** Kept as the frame and table fallback, not as the primary
  surface the owner chose. Superseded for the 2D view only by the amendment of
  2026-11-04 below: the 2D view is the default surface and Three.js stays vendored.

## Consequences

- Positive: reproducible, offline viewer with a reviewable byte boundary.
- Negative: about 2.2 MB of third-party JavaScript (the three files at r186) in the repository; updates need
  manual review.
- Compatibility: the license map gains one MIT directory; AGPL and CC-BY-SA
  boundaries are unchanged.
- Security: hash manifest test plus a provenance receipt, no remote load, no
  `eval` in first-party code, CSP restricted to self plus one import-map hash.

## Validation

`tests/test_view_web_bundle.py` checks the vendored files by manifest hash only
(upstream files legitimately contain namespace URIs and links in comments), checks
first-party files for remote URLs, `eval` and `new Function`, checks that no import,
`src`, `href` or fetch in first-party files or the import map targets a remote
origin, and checks the CSP, which also blocks remote loads at runtime. Because
`OrbitControls.js` imports the bare specifier `three`, `index.html` carries one
inline import map allowed by its SHA-256 in the CSP; the vendored files stay
unmodified. A version update is a reviewed change with a new manifest.

## Amendment 2026-11-04: 2D timeline as the default view, no vendor change

- **Date:** 2026-11-04
- **Deciders:** Juan Antonio Yáñez García (owner)
- **Specification:** [SPEC-061](../../specs/061-activity-viewer/spec.md) VIS.1c amendment
  (REQ-017, REQ-018); drafted in
  [the amendment draft](../../specs/061-activity-viewer/vis1c/adr-0033-amendment-draft.md)
- **Owner decisions (2026-11-04, verbatim):** D7 "Sí, 2D por defecto (Recommended)" to
  "¿La vista 2D pasa a ser la vista por defecto del visor?"; D10 "No, overlays HTML
  propios (Recommended)" for vendoring; G2 "Aceptar (Recommended)" for this amendment.

### Context

A UX audit of the shipped viewer found that the third axis encodes no information the
2D lanes lack, that the camera and labels hide the agents, and that the owner cannot
answer "which agent is active, what conflicted, how long" from the 3D scene. The owner
chose the 2D timeline as the default.

### Decision

1. **Default surface.** (Takes effect with tasks T057 and T059 of the implementation.) The primary and default view is a first-party 2D SVG timeline
   (one lane per agent, proportional time axis). The 3D scene becomes the secondary
   "spatial map", selectable and linked to the same state. A deep link or a stored
   choice may still open the 3D view.
2. **Alternatives line.** The line above that kept the SVG-only 2D viewer as a
   fallback is superseded for the 2D view only. Three.js remains vendored and
   supported for the secondary view. Nothing is removed.
3. **No vendor change.** The vendored file list stays exactly `build/three.module.js`,
   `build/three.core.js` and `examples/jsm/controls/OrbitControls.js`. The 2D view
   adds no third-party code. `CSS2DRenderer`, `Line2`/`LineMaterial` and `MapControls`
   are not vendored; HTML labels are first-party and positioned by `Vector3.project`.
   Any future addon still needs a separate amendment.
4. **First-party code boundary.** New first-party files (`state.js`, `timeline.js`,
   `strings.js`) are listed in the served bundle (`BUNDLE_FILES`) and in the package.
   They follow the existing first-party rules: no remote URL, no `eval` or
   `new Function`, no `innerHTML`, all values as text nodes, no `style=` markup, one
   import map only.
5. **CSP unchanged.** `default-src 'self'; script-src 'self' 'sha256-<importmap>';
   style-src 'self'; require-trusted-types-for 'script'`. SVG is created with
   `createElementNS`; dynamic values use CSSOM property assignment, which
   `style-src 'self'` permits. The import-map hash does not change unless the map does.
6. **Fallback preserved.** The table remains the complete text alternative; the
   timeline works without WebGL, and 3D loads by dynamic `import()` only when chosen.

### Consequences

- Positive: the first screen answers the user's questions; the default surface has no
  WebGL dependency; no new vendored file to review.
- Negative: two views to keep consistent (one shared state model and one glyph set);
  3D investment slows after the redesign (open decision OD-V6, accepted: fixes only).
- Compatibility: SPEC-061 REQ-010 ("the Three.js scene") is superseded only for its
  default-view clause; its fact-binding, vocabulary and no-claim rules apply to the 2D
  view unchanged. REQ-013 and the vendor manifest tests are unaffected. No license-map
  change.
- Security: unchanged boundary (loopback, strict CSP, no remote load).

### Validation

`tests/test_view_web_bundle.py` covers the new first-party files (no remote URL,
`eval`, `innerHTML` or `style=`; vendor manifest hashes unchanged; CSP header
unchanged); the web folder ships whole in the package (`build_support.py`), and `BUNDLE_FILES` lists the new files.

## References

- https://github.com/mrdoob/three.js/blob/dev/LICENSE
- https://threejs.org/manual/en/webgpurenderer
- [ADR 0012](0012-vendored-python-skills-license-boundary.md)
- [ADR 0032](0032-activity-viewer-companion.md)
