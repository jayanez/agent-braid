<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Agent Braid activity viewer (web bundle)

The first-party web bundle of the read-only activity viewer
([SPEC-061](../../specs/061-activity-viewer/spec.md)). It is a companion to the native
plugin, not part of it: the plugin tree `integrations/agent-braid/` contains no viewer
code. The user guide is [docs/tooling/VIEWER.md](../../docs/tooling/VIEWER.md).

## Contents

| Path | Role |
|---|---|
| `web/index.html` | Page shell with the single inline import map the server hashes for its policy |
| `web/loom.js` | Page shell: event stream client, header, toolbar, filters, detail panel, playback, tabs (events table, summary, legend, help) |
| `web/state.js` | Shared state and derived model (agents, crossings, axis, overlaps, filters, URL hash); no DOM, no network |
| `web/strings.js` | Every user-facing string in Spanish and English, with language detection (manual choice, browser or desktop-app locale, server hint, English) |
| `web/braid-scene.js` | Three.js braid scene bound to the same model and evidence panel as the table |
| `web/style.css` | Styles |
| `web/vendor/` | Vendored Three.js r186 (MIT) with its licence and `manifest.json` of SHA-256 hashes ([ADR 0033](../../docs/adr/0033-vendored-threejs-mit-boundary.md)) |

## Rules this bundle follows

- Served only by `agent-braid view serve` on loopback; the page makes no request to
  another origin, uses no `eval` and no remote script, style, font or image.
- Read-only: it has no control that runs, schedules, grants or writes anything. The
  page shows `executionAuthorization: false` and never shows a path (watched roots are
  `root 1` to `root 8`).
- Vendored files are not edited; their hashes are checked against the manifest
  (`tests/test_view_web_bundle.py`, `tests/test_view_boundaries.py`).

## Source checkout and wheel

From a source checkout the server reads this directory directly. The build copies it,
including `web/vendor/`, into the wheel as `agent_braid/view_assets/web` (`build_support.py`),
and `view serve` falls back to that copy when no checkout is present. Both paths are
checked by `tests/test_view_packaging.py`.

## Changing it

Edit the first-party files only. A second inline import map in `index.html` is refused by the
server at start, and a remote reference or code evaluation is refused by the bundle tests. Keep
every user-visible statement within the non-claim of the viewer: a rendered shape, label
or class is not a guarantee, and no shape ranks one class as safer than another.
