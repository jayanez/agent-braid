# Native plugin release acceptance — alpha.5

`0.1.0-alpha.5` is published on `plugin-dist` and annotated tag
`agent-braid--v0.1.0-alpha.5` (tag object `961c656bd8f4576ce05affe81b8578f6da0de549`),
both resolving to commit `07e5973fe819591854e6df8bca169b5ec82eae05` (a fast-forward
of `ac2c4982`), built from develop `88eccace1092f03cd012c8933472da42127c4085`. It
adds opt-in System One shadow mode (SPEC-066, ADR 0034) and is the build for the
owner's SC-006 shadow week. Hashes, file count and tag object were re-derived from a
fresh public clone; see [evidence/release-alpha5.json](evidence/release-alpha5.json).

| Artifact | SHA-256 |
| --- | --- |
| `plugins/agent-braid/package-inventory.json` | `41d62be2f596023a9bfd68f971d805c02ecb75783904bf3ba4d81b7c0a4b5f94` |
| `plugins/agent-braid/provenance.json` | `896a853e110a0490004fd57fd13b175bfe3113e1b6f4f6e6380d3279a014170b` |
| `sources/agent-braid-0.1.0-alpha.5-source.tar.gz` | `143b43d5999300ac8b6743c645622733ac3d168a360459f68de5dd971c9cd688` |

## Observations obtained

macOS arm64, agent-operated:

- Clean release build; `verify_package` passed.
- The bundled launcher previews `plugin setup --system-one shadow` against an empty
  private home without writing, and warns that earlier plugin versions refuse a
  registry with System One consent.
- Byte-identical fresh public clone of the tag; bundled doctor verified 7,902 files.

## Not observed

- A native Claude Code or Codex install or update of alpha.5. The owner's update for
  the SC-006 week is the next observation.
- `reproduce_native_plugin` for this release.
- Interactive skill use, Codex sign-in and Linux execution (built only).
- A rollback to alpha.4 (documented in the native plugin guide, not executed).

## Rollback

alpha.4 refuses a registry that records System One consent (`Unknown registry
schema`). Preview and apply `plugin setup --system-one off` first, then reinstall
`0.1.0-alpha.4` from tag `agent-braid--v0.1.0-alpha.4`. The shadow store stays until
`system-one purge`.

These are agent-operated engineering observations. They are not a human usability
rating, official directory approval or scientific acceptance, and shadow mode makes
no accuracy, calibration or promotion claim.
