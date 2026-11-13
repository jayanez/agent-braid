# Native plugin release acceptance — alpha.8

`0.1.0-alpha.8` (SPEC-069, `analyze-work` request authoring; closes #1080) is published
on `plugin-dist` and annotated tag `agent-braid--v0.1.0-alpha.8` (tag object
`c4c7e37ec0d913f40fa5c85e974eea3416586e48`), both resolving to commit
`7f914ae5ce04ac3294237da71a48276e014e68a8` (a fast-forward of `8f19b1b7`, the alpha.7
distribution). It was built from `c0271812fc0c81032e2621881e543cabc500881e` on release
PR #1342, which merged into `develop` as `f923f73f`. A GitHub pre-release with the
[release notes](../../docs/tooling/NATIVE_PLUGINS.md#release-notes-for-010-alpha8) points
at the tag. It adds no registry migration. Hashes, checks and the owner's words are in
[evidence/release-alpha8.json](evidence/release-alpha8.json). The candidate record,
including the 3-host smoke, is
[evidence/procedure_012-candidate.json](evidence/procedure_012-candidate.json).

| Artifact | SHA-256 |
| --- | --- |
| `plugins/agent-braid/package-inventory.json` | `18f62e54e515f850fa741601dc5bb6dc7aafb1396c9e2be302ec4ffeeb5d8fe7` |
| `plugins/agent-braid/provenance.json` | `b6b162fb066963496872ae2ea9ff964af77504347dd5106ef0c743c3ddcc2677` |
| `sources/agent-braid-0.1.0-alpha.8-source.tar.gz` | `10c55f76fd7e410c6fecaabbd11452b83b9a86e9496af206a54e86e2ce1f642d` |

The tag tree holds 8,113 files (excluding `.git`); the package inventory lists 8,107.

## Owner decision

On 2026-11-13 the owner answered the parent session's questions:
- **Publish:** "Yes, publish (Recommended)".
- **Builder home path in the package:** "Fix first".
- **Release page:** "Tag + Release page".
- **Console scripts:** "Remove them (Recommended)".
- **Third-party `/Users/runner` strings:** "Leave them (Recommended)".
- **#1080:** "Close + new D4 issue (Recommended)".
- **Checks before publishing:** "CI + 3-host smoke (Recommended)".

## Observations obtained

macOS arm64, agent-operated:

- **Build-path fix.** The first candidate (`a741c5a1`) shipped the builder's home path in
  12 unused `site-packages/bin` console scripts and 2 `direct_url.json` files, as alpha.4
  to alpha.7 did. The build now removes them and stops if a packaged file contains the
  checkout, build folder or build virtualenv path (`tests/test_native_plugin_build.py`).
  No file in the published tree contains the builder's home path.
- **Clean build.** The build ran from a fresh clone at `c0271812` (`git status --porcelain`
  empty) with Python 3.12.13. `scripts/build_native_plugin.py` reported status built,
  version `0.1.0-alpha.8`, platforms `macos-arm64` and `linux-x86_64`, with provenance
  `sourceDirty` false.
- **Smoke on the build output.** Claude Code 2.1.311, OpenCode 2.1.4 and Codex
  0.167.0-alpha.4.1 exposed `analyze-work`, sent `aim` and `units` requests as JSON
  objects, and were served the built definition. Total cost was about 0.08 USD. The tree
  manifest `f54fdfc8…` was unchanged after the smoke and immediately before publication.
- **Source drift after the candidate.** After `c0271812`, the PR branch changed only
  `specs/069-aim-request-authoring/` and `docs/tooling/NATIVE_PLUGINS.md`, neither of which
  is in the plugin tree.
- **The `plugin-dist` commit.** Its message is `dist: Agent Braid 0.1.0-alpha.8 (source
  c027181)`. The root `README.md` was kept unchanged; it names no version. The branch and
  the annotated tag were pushed without force, and the tag did not exist on origin before
  the push.
- **Verification.** `plugin doctor` ran with an empty canonical home on the `plugin-dist`
  commit. It reported `pluginVersion` `0.1.0-alpha.8`, package `0.1.0a2` and a verified
  package of 8,107 files.
- **Public clone.** A fresh public clone of the tag is identical to the build output under
  `diff -r`, except the root `README.md`, which exists only on `plugin-dist`.

## Deviation

GitHub closed #1080 automatically when PR #1342 merged, a few minutes before the tag push.
procedure_012 asks for closure after publication. The evidence comment was posted after
publication.

## Not observed

- A native install or update from the published tag on any host; the smoke ran on the
  build output.
- Linux x86_64 execution (built only).

## Follow-ups

- #1343: D4 not met (Codex 7/10 prompts; HELD-04 fails on every host).
- Develop at `f923f73f` already holds harness and lab changes that other PRs merged after
  the candidate branch point. They are not in alpha.8.
