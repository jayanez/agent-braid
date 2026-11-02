# Spec Kit provenance and adaptations

Source: [GitHub Spec Kit v1.0.7](https://github.com/github/spec-kit/tree/v1.0.7),
commit `fe1d00e3ccaf495880aaf90fb0e17679e82f065b`, copyright GitHub, Inc.
The full [MIT notice](../../LICENSES/Spec-Kit-MIT.txt) is retained.

Unmodified `.specify/scripts/python/` and `.specify/scripts/bash/` helpers and
the base checklist template are copied from the pinned official scaffolding.
Integration state and skill frontmatter are produced with its official adapters.
Other base templates are generated copies of our overrides. Commands are complete
Agent Braid replacements with shared gates inserted before command actions; no
upstream constitution-editing workflow is retained. The bundled automated workflow
is not installed. No third-party trademark license or endorsement is implied.

Our generator/validators/tests are AGPL-3.0-only. Our editorial overrides and
generated policy bodies are CC-BY-SA-4.0 under the repository license map.
Copyright © 2026 Juan Antonio Yáñez García. Generated metadata's `github-spec-kit`
identifies adapter provenance, not authorship of our command instructions.
`generation.json` records the exact source/output hashes. Regenerate rather than
editing generated outputs; preserve upstream MIT notices on redistribution.

## Market trends report template

An earlier private revision of `reports/agent-braid-market-trends-2026.pptx` was
derived from **Market Industry Trends Report**, distributed in OpenAI Templates
plugin 0.1.1 with a `Proprietary` plugin license. The source template was not
copied into this repository, but the derivative remains in historical Git objects.
This notice records provenance; it does not grant additional rights or imply
OpenAI endorsement.

The current PPTX and PDF were recreated from a blank presentation with an
independently designed visual system and no template layouts or metadata. Their
cover artwork was generated specifically for Agent Braid. They are governed by
the repository license map. This replacement does not by itself authorize
redistribution of the earlier historical derivative.

Until applicable rights are documented or a separately approved history
operation resolves the historical object, public research-preview distribution
must use the clean-export procedure in
`docs/releases/RESEARCH_PREVIEW_PROPOSAL.md`. The existing private repository
must not be made public merely because the current tree is redistributable.

## Braid Harness offline foundations

Pinned source: `google-research/harness2` at
`1cfe254e8d25b15f37048c3730134686abe60335`, Copyright 2026 Google LLC,
Apache-2.0. The complete upstream license is retained in
[`LICENSES/Harness2-Apache-2.0.txt`](../../LICENSES/Harness2-Apache-2.0.txt).
The inspected root source tree has no NOTICE file. Preserve applicable upstream
notices on adapted source portions and prominent changed-file notices. File-level
Apache terms are exceptions under the existing repository license map, not a
relicensing of unrelated Agent Braid code or documentation.

The [reviewed inventory](../../specs/048-harness-variant-laboratory/kickoff-decision.md)
binds complete original file hashes. Selected seams are `core/spec.py` typed
views and `core/runmark.py` fingerprint/completion identity for
`agent_braid/harness_manifest.py`; `core/tree.py` bounded surface/import structure
for `harness_surface.py`; and `core/ledger.py` stage/accounting concepts for
`harness_admission.py`. Adaptations replace upstream assumptions with full
SHA-256 manifests, positive inventories, protected layers, zero-launch offline
limits and operator-owned reservation semantics. Each module identifies its
actual adaptation; task evidence records the implemented portions and deltas.
Original project tests retain their stated project license.

No benchmark stack, bundled dataset, third-party runner patch, bypass launcher,
upstream documentation/artwork or branding is imported. Other upstream assets
have no rights or execution clearance from this bounded inventory.

## Three.js (activity viewer)

Pinned source: npm package `three` 0.186.0 (r186), tarball
`https://registry.npmjs.org/three/-/three-0.186.0.tgz`, registry integrity
`sha512-cr/fIM2ddMSVbYVgkfD4jLJv7Fh/8ZTjvo+7gQeSVGUZHxpx9FDwoL5iC7hUz/LiRA8wMbqfnb90xKfm1/HHkQ==`,
Copyright © 2010-2026 three.js authors, MIT. The upstream license is retained in
[`LICENSES/three-MIT.txt`](../../LICENSES/three-MIT.txt) and next to the files.
Decision: [ADR 0033](../adr/0033-vendored-threejs-mit-boundary.md).

Exactly three prebuilt ES module files are vendored, byte-identical to the
tarball, under `integrations/agent-braid-view/web/vendor/three/`: `three.module.js`
and `three.core.js` (from `build/`) and `addons/controls/OrbitControls.js` (from
`examples/jsm/controls/`), plus `LICENSE`. `OrbitControls.js` keeps the bare
specifier `three`, resolved by the import map that T025 adds to the viewer page. The
SHA-256 of every file is in `integrations/agent-braid-view/web/vendor/manifest.json`;
the provenance receipt
[`specs/061-activity-viewer/evidence/vendor-threejs-20261102.json`](../../specs/061-activity-viewer/evidence/vendor-threejs-20261102.json)
records that the tarball matches the registry integrity and that the vendored
bytes equal the extracted files. Other upstream files, post-processing addons and
other third-party web code are not vendored; updates repeat the manifest and the
receipt and require review.
