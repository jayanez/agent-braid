# Native plugin release acceptance — alpha.3

`0.1.0-alpha.3` is published on `plugin-dist` and annotated tag
`agent-braid--v0.1.0-alpha.3` (tag object `4579ac71b48a3a8e98a8376d6c1a88e428c52d00`),
both resolving to commit `8ed7838a9b12c2dc1684a5e7c1e7cada7543c663`. Hashes,
the file count and the tag object were re-derived from a fresh public clone; see
[evidence/release-alpha3.json](evidence/release-alpha3.json).

| Artifact | SHA-256 |
| --- | --- |
| `plugins/agent-braid/package-inventory.json` | `61a4dcdafebb3a7f6c3495783532df0c1a4a14b6c0ddd5f3d6891e206c3a37d7` |
| `sources/agent-braid-0.1.0-alpha.3-source.tar.gz` | `60ca57b10c03718749c3f5ac7bdb1296bae84bd1b86a1d8655bb9158dcfc1502` |

## Observations obtained

Native macOS arm64, Claude Code 2.1.292:

- `reproduce_native_plugin` `native-mac`: 19 commands passed.
- An isolated alpha.2 to alpha.3 update passed.
- The installed package doctor verified.
- Installation of alpha.3 from the public marketplace verified.
- Local telemetry consent was off by default.

## Not observed

- Codex CLI.
- A Linux container.
- Interactive skill use.

These are owner-reported engineering observations recorded here; the commands were
not re-run for this record. They are not a human usability rating, official
directory approval or scientific acceptance.
