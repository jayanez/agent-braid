# Contract: scope map and build check

The scope map is a closed table in `agent_braid/lightning_promote.py`.

| Scope | Target path | Text limit |
|---|---|---|
| `lightning.skill.analyze` | `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md` | 32 KiB |

The single entry is the OD-1 decision (T001); any other scope is refused with
`unknown-scope`. The path exists in the plugin source tree.

Build check (`plugin_package`): for each scope with a registry, the packaged
file's SHA-256 must equal `ProfileRegistry.active`. Mismatch message:
`lightning-promotion-mismatch: <scope> expected <sha> actual <sha>`. A scope
whose registry has no active candidate requires the file to equal the
baseline digest recorded at its first `record`.

Severity (OD-2): a release build refuses on mismatch; a local developer build
prints the same message as a warning and continues.

Registry source (OD-3): the working registry is
`<plugin home>/lightning-promotion/registry.json`; release builds read the
committed export `integrations/lightning-promotion/registry-export.json`.
