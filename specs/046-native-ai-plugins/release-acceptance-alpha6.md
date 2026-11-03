# Native plugin release acceptance — alpha.6

`0.1.0-alpha.6` is published on `plugin-dist` and annotated tag
`agent-braid--v0.1.0-alpha.6` (tag object `6dac99565e7d74b4dc0ac0f2b87e89a7bf208a87`),
both resolving to commit `78cc45a3f1c5dbc7b43e0ce5024fc5d1c5da053e` (a fast-forward
of `07e5973f`), built from develop `ce40f2b6761aca3c2e4106b0ba7a26531214fe2a`
(release-preparation PR #1006). It adds registry quarantine (SPEC-046 T020), refusal
reasons, serve-start telemetry and the read-only `telemetry-audit` skill (SPEC-047
T011–T012), and `pluginVersion` in `plugin-status` (SPEC-046 T021). It adds no registry
migration. Hashes, file count and tag object were re-derived from a fresh public clone;
see [evidence/release-alpha6.json](evidence/release-alpha6.json). Publication ran
under the owner's decisions recorded in
[owner-authorization-20261103.md](owner-authorization-20261103.md).

| Artifact | SHA-256 |
| --- | --- |
| `plugins/agent-braid/package-inventory.json` | `b1ab5356ed436a13800d0c11583b1ecd1ff17e06bd5d601f6a6732a8180bf969` |
| `plugins/agent-braid/provenance.json` | `d3e30493f8766b2d9aea32a21d9d15b734505f06537416b1980dd01a4f76e041` |
| `sources/agent-braid-0.1.0-alpha.6-source.tar.gz` | `3e02e10de56a5248ffbdfd26eb146bf404f0a99999f8b3e4ab4b75505fea47b1` |

## Observations obtained

macOS arm64, agent-operated:

- Release PR #1006 merged with all required CI checks green (the Spec Kit solo/dual
  matrix was skipped by design).
- Clean release build from a fresh clone at the detached develop commit
  (`sourceDirty` false) with Python 3.12.13; `verify_package` passed on the built
  plugin (7,970 files).
- The bundled launcher's `plugin doctor`, run against an empty private home, reported
  `pluginVersion` `0.1.0-alpha.6`, package `version` `0.1.0a2`, a verified package of
  7,970 files, and System One and telemetry both `off`. This ran on the local
  distribution commit before the push and again on a fresh public clone of the tag.
- The fresh public clone of the tag is byte-identical to the build output (excluding
  `.git` and the root README).

## Not observed

- A native Claude Code or Codex install or update of alpha.6. The native host
  observation is pending and is the next step after this record.
- `reproduce_native_plugin` for this release.
- A `plugin setup` preview or apply against the bundled launcher.
- Interactive skill use (including `telemetry-audit`), Codex sign-in and Linux
  execution (built only).
- A rollback to alpha.5 (documented in the native plugin guide, not executed).

## Rollback

Alpha.6 adds no registry member, so the registry and results are accepted unchanged by
alpha.5. If `plugin doctor` reports `staleWorktreeRoots` or `unsafeWorkspaces`, preview
and apply `plugin setup --prune-stale` first (alpha.5 refuses such a registry), then
reinstall `0.1.0-alpha.5` from tag `agent-braid--v0.1.0-alpha.5`. Telemetry cells
written by alpha.6 stay in the store; alpha.5 cannot export a store that holds batch
v2 cells.

These are agent-operated engineering observations. They are not a human usability
rating, official directory approval or scientific acceptance.
