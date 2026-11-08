# Third-party inventory — Braid Lightning (SPEC-070 REQ-002)

Upstream: [microsoft/agent-lightning](https://github.com/microsoft/agent-lightning),
Copyright (c) Microsoft Corporation, MIT License. The license text is identical on
both pinned commits and is retained in
[`LICENSES/Agent-Lightning-MIT.txt`](../../LICENSES/Agent-Lightning-MIT.txt).

| Pin | Commit |
|---|---|
| `main` (v1.0.3) | `bc3a9e80417d731744040df5d37117f9cc48005f` |
| `v0.x` (0.3.1) | `6db3c73dc0af2e50fe80e56873a57c1703f1b2a7` |

Complete original file hashes (SHA-256) of every upstream file an Agent Braid
module adapts or will adapt. Later BL specs extend this table before porting
further files.

| Upstream file | SHA-256 | Agent Braid module | Spec |
|---|---|---|---|
| main `LICENSE` | `8f71659370c5268d9a1dc962a46232540e8fca63462586d8efaa95aab492a208` | `LICENSES/Agent-Lightning-MIT.txt` (verbatim) | 070 |
| main `agentlightning/schemas.py` | `7bb7eafaba1af249668592042a5de7a0dea191a6dd3160383b8a723ffb15c674` | `agent_braid/lightning_schema.py` | 070 |
| main `agentlightning/verl/config.yaml` | `c3719129a7be8e40cf8f4021f26eaa91fa97fcacd3ce04065740ab0258edf23a` | `agent_braid/lightning_config.py` | 070 |
| v0.x `agentlightning/trainer/trainer.py` | `a1a4df0553b35b13974c5c0e27761411889c2fd633ebc26dc6ef6ad6c3b5159d` | `agent_braid/lightning_config.py` (keyword surface only) | 070 |
| main `agentlightning/server/store.py` | `685c500977a9dfbea2fc1836139a73fd2752082739008ecda8842871ccc44efd` | `agent_braid/lightning_store.py` | 070 |
| v0.x `agentlightning/store/base.py` | `d9a642313c6e07190bb46db95c903d3447f32b70a0363f32a6a2c40c7238207e` | `agent_braid/lightning_store.py` | 070 |
| v0.x `agentlightning/store/memory.py` | `5af8bba052ea731943f93d3589f7ec29f011874e83837f6478770079f81a2fd5` | `agent_braid/lightning_store.py` | 070 |
| main `agentlightning/hooks.py` | `21c7fe9474f05efe8403b0b583e14b13a9510efce3a1dc3c793c883036bce95b` | `agent_braid/lightning_hooks.py` (planned) | 071 |
| main `agentlightning/controller/local_reconciler.py` | `c49f21804830b8cc37374bf26a849f062dd346820d98e757d3914c92da50685d` | `agent_braid/lightning_runner.py` (planned) | 071 |
| v0.x `agentlightning/emitter/reward.py` | `ef9e08da2a41ca1ce40005a3896e79a369159d19271122c0d4823b118bb88955` | `agent_braid/lightning_reward.py` (planned) | 071 |
| v0.x `agentlightning/algorithm/base.py` | `b8a6282a59067906c80238ea131d91d1ee7ac39d7e52197e4c0fee891100ce1d` | `agent_braid/lightning_algorithm.py` (planned) | 072 |
| v0.x `agentlightning/algorithm/apo/apo.py` | `afe4ff80714957ce4d001025fc23b3675db00500254c9dcd2c94b6d21bce42e2` | `agent_braid/lightning_apo.py` (planned) | 072 |
| v0.x `agentlightning/types/resources.py` | `fc7bcbd2cd5a261225ffe9c4a80c5071a7c13244ad3bc683b0c385ab7e76896c` | `agent_braid/lightning_resources.py` (planned) | 072 |
| v0.x `agentlightning/adapter/triplet.py` | `1772ea02c36e2c1d0a97a310515e413ad382c64e7f147ef60d7a835e9c029cf4` | `agent_braid/lightning_adapter.py` (planned) | 074 |
| v0.x `agentlightning/adapter/messages.py` | `e06dafc58d3dfae5711819c816473b4b04750e8a8015f270783021c3271024b4` | `agent_braid/lightning_adapter.py` (planned) | 074 |
| main `agentlightning/server/proxy.py` | `6fc6ff8478584c91ed2de08e2e7bb874764441698e1f32ff294ca81c5341baa4` | `agent_braid/lightning_proxy.py` (deferred) | 076 |

Not imported: verl, vLLM, torch, Ray, Hydra, FastAPI, Kubernetes manifests and
the `kr8s` controller, AgentOps/OTel tracers, `.poml` tooling (APO prompts are
converted to plain Markdown templates in SPEC-072), examples, datasets,
documentation, dashboard and branding. GEPA (SPEC-072) is implemented from its
paper; no GEPA code is vendored.
