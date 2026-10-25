# Native plugin release acceptance — alpha.4

`0.1.0-alpha.4` is published on `plugin-dist` and annotated tag
`agent-braid--v0.1.0-alpha.4` (tag object `00f34c51cd746b459684e9146b7700d832c27b50`),
both resolving to commit `ac2c49825c963bf7daf3fd0851f28d9651580efa` (a fast-forward
of `8ed7838a`), built from develop `8e2c3759e6bd809e907654895b103bf8b151db50`. It
implements SPEC-054 / ADR 0030: no plugin MCP prompts (`agent-braid-plugin/v0.2`) and
unprefixed skills. Hashes, file count and tag object were re-derived from a fresh
public clone; see [evidence/release-alpha4.json](evidence/release-alpha4.json).

| Artifact | SHA-256 |
| --- | --- |
| `plugins/agent-braid/package-inventory.json` | `956fe4e155d1834899b68a5555f7fb425f2c589c1938cb0b1c50ccb95d95d11b` |
| `plugins/agent-braid/provenance.json` | `f1565500fe87b70a543d6bdcfcf8752d45e1d868140f374f75bea440b5a541aa` |
| `sources/agent-braid-0.1.0-alpha.4-source.tar.gz` | `6909c2197fcb0021a8c4db740fb42316cb0d39097dca5122ed9015b22bd96268` |

## Observations obtained

Native macOS arm64, Claude Code 2.1.292 and codex-cli 0.164.0:

- Clean release build; bundled doctor verified 7,834 files.
- Plugin MCP server: no prompts capability, tools unchanged, schema `agent-braid-plugin/v0.2`.
- Packaged skills `analyze, evidence, execute, plan, recover, setup`; no prefixed token.
- `reproduce_native_plugin` `native-mac` with both hosts: 28 commands passed.
- Isolated Claude Code update from alpha.3: registry and results unchanged.
- Public Git-tag install of alpha.4 in an isolated Claude Code profile verified.
- Byte-identical fresh public clone of the tag.
- Candidate-stage Claude Code and Codex records are under `specs/054-plugin-surface-naming/evidence/`.

## Not observed

- Interactive skill use and Codex sign-in.
- Linux execution (built only).
- A Codex plugin update across versions.
- Telemetry and migration journeys.

These are agent-operated engineering observations. They are not a human usability
rating, official directory approval or scientific acceptance.
