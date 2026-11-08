# SPEC-070 implementation plan

## Technical context and scope

Agent Braid is Python 3.12+ with a standard-library core (`pyproject.toml`
`dependencies = []`). Plugin state lives under `plugin_registry.home_path()`
with owner-only modes, symlink refusal and preview/apply digests
(`plugin_registry.plan_setup`/`apply`). Optional consent keys follow the
`systemOne` pattern: absent means off, explicit off is never stored, the key
enters `configuration_digest` only when not off. Upstream agent-lightning is
Python too; its v1 data model, v1 Hydra configuration and v0.x store/trainer
surface are adapted here (see [third-party-inventory.md](third-party-inventory.md)).

## Constitution check before research

- Clause zero: engineering only; no algebraic or performance claim.
- Article 12: the store serializes writers with an exclusive lock; runs default to `parallel = 1`.
- Article 13: rewards and configuration values are never presented as guarantees.
- Article 14: records are canonical, hashable and replayable.
- Article 16: new public surfaces are versioned (`braid-lightning-config/v0.1`, `-rollout/v0.1`, `-event/v0.1`).
- Articles 19 and 20: advisory only; `executionAuthorization` false; no execution path.
- Articles 23 and 25: the laboratory feeds research back into engineering without freezing semantics.

No MUST contradiction found. No SHOULD deviation proposed.

## Research and alternatives

See [research.md](research.md). Rejected: depending on the `agentlightning`
package (non-stdlib dependencies), porting Kubernetes and the FastAPI gateway
(no need on one owner machine; network surface), Hydra YAML (dependency and
open-ended overrides), and reusing telemetry for traces (ADR 0025 boundary).

## Design

| Module | Upstream origin | Responsibility |
|---|---|---|
| `agent_braid/lightning_schema.py` | main `schemas.py` | records, state machine, canonical bytes |
| `agent_braid/lightning_config.py` | main `verl/config.yaml`, v0.x `Trainer` kwargs | profile, validation, digest, wizard preview/apply |
| `agent_braid/lightning_store.py` | main `server/store.py`, v0.x `store/` | private per-run JSONL, lock, sweep, purge |
| `agent_braid/lightning_cli.py` | — | `lightning init`, `validate`, `status`, `purge` |
| `agent_braid/plugin_registry.py`, `plugin_cli.py` | — | `lightning` consent key and `--lightning` flag |
| `schemas/0.3.0-experimental/lightning-config.schema.json` | — | published configuration schema |

## Constitution check after design

Unchanged: no network, no process launch, no MCP tool, stdlib only, explicit
consent, private state. Earlier plugin versions refuse a registry that stores
`lightning: lab`, stated in the setup effects.

## Phases

1. Governance: ADRs 0039–0042, license, inventory (T001, T002).
2. Model and configuration: schema, config, wizard (T003–T005).
3. Store and setup (T006, T007).
4. Boundaries, tracking and convergence (T008–T010).

## Risks

- Registry compatibility with older plugins (mitigated by never storing off).
- The owner may reject ADR 0039 or 0040; then BL code stays unreleased and SPEC-071+ do not start.
- Pre-existing `develop` preflight failure (SPEC-066 stale evidence after #1155) is outside this feature.
