# Contract: scope map and build check

The scope map is a closed table in `agent_braid/lightning_promote.py`.

| Scope | Target path | Text limit |
|---|---|---|
| `lightning.skill.analyze` | `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md` | 32 KiB |
| `lightning.skill.plan` | `integrations/agent-braid/skills/agent-braid-plan/SKILL.md` | 32 KiB |

Entries are proposals pending OD-1; paths are confirmed against the plugin
source tree in T002.

Build check (`plugin_package`): for each scope with a registry, the packaged
file's SHA-256 must equal `ProfileRegistry.active`. Mismatch message:
`lightning-promotion-mismatch: <scope> expected <sha> actual <sha>`. A scope
whose registry has no active candidate requires the file to equal the
baseline digest recorded at its first `record`.
