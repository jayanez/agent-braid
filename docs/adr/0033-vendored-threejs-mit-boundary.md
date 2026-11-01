# ADR 0033: MIT boundary for vendored Three.js

- **Status:** accepted by explicit founder decision on 2026-11-01 (founder's answer, verbatim: "Aceptar ambas, r186"), with the pin moved from the proposed r182 to r186
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
  surface the owner chose.

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

## References

- https://github.com/mrdoob/three.js/blob/dev/LICENSE
- https://threejs.org/manual/en/webgpurenderer
- [ADR 0012](0012-vendored-python-skills-license-boundary.md)
- [ADR 0032](0032-activity-viewer-companion.md)
