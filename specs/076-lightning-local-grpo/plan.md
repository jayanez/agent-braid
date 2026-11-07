# SPEC-076: Plan

**Status:** deferred; this plan is ready for a reopen decision, not for work.

## Technical context and scope

Core stays standard library only. The GPU path lives behind optional extra
`lightning-gpu` (verl, vllm, torch pinned to the versions `scripts/setup_verl.sh`
uses upstream), installed only in an isolated virtual environment. Local
process tree on one machine with a CUDA GPU. State in the SPEC-070 store.

## Constitution check before research

| Article | Check | Status |
|---|---|---|
| 13 | no improvement claim before preregistered evaluation | pass |
| 14 | events keep token IDs and hashes for replay | pass |
| 15–16 | budget and limits declared | pass |
| 19 | trains only on SPEC-075 consented exports | pass |
| 20 | `executionAuthorization` false; weights never a System One backend | pass |
| 23–24 | founder go/no-go and ADR 0042 gates | pending (deferred) |

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions: a local CUDA GPU with enough memory
for a small open model (OD-4); vLLM supports token-ID return for the chosen
model (OD-3).

## Design and compatibility

| Upstream file (v1.0.3) | New module | Port |
|---|---|---|
| `agentlightning/server/proxy.py` | `agent_braid/lightning_proxy.py` | concepts on `view_serve` helpers |
| `agentlightning/server/app.py`, `routes/` | `agent_braid/lightning_proxy.py` (routes `/v1/chat/completions`, `/pause`, `/resume`) | minimal |
| `agentlightning/server/store.py` | SPEC-070 `agent_braid/lightning_store.py` | `model_request` events |
| `agentlightning/verl/entrypoint.py` | `agent_braid/lightning_train.py` (extra only) | local runner, no Hydra |
| `agentlightning/verl/agl_rollout_manager.py` | `agent_braid/lightning_train.py` | local workers only |
| `agentlightning/verl/rollout_adapter.py` | SPEC-075 `agent_braid/lightning_export.py` + token-ID merge | reuse |
| `agentlightning/verl/rollout_level_advantage.py` | `agent_braid/lightning_advantage.py` (stdlib reference + torch path) | port |
| `agentlightning/verl/per_rollout_loss.py` | `agent_braid/lightning_train.py` | port |
| `agentlightning/verl/config.yaml` | `training` section proposal | see contract |
| `scripts/setup_verl.sh` | `pyproject.toml` extra `lightning-gpu` | pins only |

Contracts: [token-proxy.md](contracts/token-proxy.md),
[training-config-proposal.md](contracts/training-config-proposal.md).
Compatibility: additive; configuration v0.1 unchanged.

## Validation strategy

Stdlib tests with fake backends and synthetic rewards in CI; GPU procedures run
only in the isolated environment on the owner's machine.

## Constitution check after design

Unchanged; Articles 23–24 remain pending until T001.

## Phases

- P0: T001 founder go/no-go (blocks all).
- P1 (stdlib, CI): T002 extra, T003–T006 proxy, T008 advantage, T010 filters,
  T013 boundary.
- P2 (GPU): T007 runner, T009 aggregation, T011 async, T012 hacking controls.
- P3: T014 budget/config review, T015 evaluation and converge.

## Risks

| Risk | Mitigation |
|---|---|
| GPU cost exceeds estimate | budget cap in `training`; stop at cap |
| Reward hacking | REQ-012 controls; canaries |
| Advantage collapse | difficulty filtering |
| Dependency drift | pinned extra; isolated env |
| Weights leak into System One | REQ-013 boundary test |

## Human review and unresolved decisions

OD-1 to OD-4 open; see [deferral.md](deferral.md).
