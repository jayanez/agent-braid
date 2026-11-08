# Research record — Braid Lightning (SPEC-070 to SPEC-076)

Recorded 2026-11-08. This file is the shared source record for the BL track.
It distinguishes upstream facts (read from pinned sources), literature findings
(with an evidence grade), and Agent Braid decisions. Nothing here is an
Agent Braid empirical finding; BL.1 and BL.2 produce those.

Evidence grades: **A** replicated across papers or peer-reviewed venues with
ablations; **B** one strong paper or several consistent preprints; **C** a
single preprint, a blog post, or an extrapolation to Agent Braid's setting.

## 1. Upstream: microsoft/agent-lightning

License: MIT on both branches (`LICENSE`, `pyproject.toml` `license = "MIT"`).
Language: Python. Pinned sources:

| Branch | Version | Commit | Role for Agent Braid |
|---|---|---|---|
| `main` | v1.0.3 (tag object `db1532b0`, released 2026-11-03) | `bc3a9e80417d731744040df5d37117f9cc48005f` | Data model, hooks, local reconciler, proxy, trainer configuration, aggregation |
| `v0.x` | 0.3.1 (last tag v0.3.0) | `6db3c73dc0af2e50fe80e56873a57c1703f1b2a7` | Store, emitters, adapters, resources, Algorithm base, APO, Baseline |

v1.0 was a complete rewrite ("harnessed agentic RL"). The v1 package has three
services: an API gateway (`agentlightning/server/`, FastAPI, in-memory state,
an OpenAI-compatible reverse proxy that forces `return_token_ids`/`logprobs`
and records a `model_request` event per call), a rollout controller
(`agentlightning/controller/`, `local_reconciler.py` subprocesses or
`k8s_reconciler.py` one Kubernetes Job per rollout) and a customized verl
trainer (`agentlightning/verl/`, rollout-level advantage, `per_rollout_mean`
loss, trajectory or transition trace aggregation). Configuration is Hydra YAML
layered on verl's `ppo_trainer` (`agentlightning/verl/config.yaml`). Rewards are
`reward` events POSTed to `AGL_EVENT_URL`; agents read `AGL_OPENAI_BASE_URL`,
`AGL_EVENT_URL` and `AGL_KEY`. Core dependencies: fastapi, uvicorn, pydantic,
httpx, hydra-core, omegaconf, structlog, jinja2, kr8s, pyyaml. verl, vLLM,
torch and flash-attn are installed separately and require CUDA.

Where Kubernetes appears (v1): only as the default rollout runner, to isolate
agent dependencies in one Job per rollout. Ray appears only inside verl.
**Agent Braid decision:** no Kubernetes; the local subprocess reconciler is
sufficient for one owner machine and already matches the SPEC-069 driver.

v0.x provides the abstractions most useful without GPUs: `LitAgent` and
`@rollout`, `Trainer` (kwargs `n_runners`, `max_rollouts`, `initial_resources`,
`tracer`, `adapter`, `store`, `runner`, `strategy`, `algorithm`, `llm_proxy`,
`hooks`), `LightningStore` (in-memory, Mongo, client/server; SQLite is a stub),
tracers (AgentOps, OTel), adapters (`TracerTraceToTriplet`, `TraceToMessages`),
emitters (`emit_reward` and lookups `find_final_reward`), `Resources`
(`PromptTemplate`, `LLM`), `Algorithm`, `Baseline` and **APO**
(`agentlightning/algorithm/apo/apo.py`, 895 lines; textual-gradient beam search;
defaults `gradient_batch_size=4`, `val_batch_size=16`, `beam_width=4`,
`branch_factor=4`, `beam_rounds=3`; prompts in `apo/prompts/*.poml`; requires
an `AsyncOpenAI` client and the `poml` package).

Upstream configuration surface that Braid Lightning mirrors, simplified:

| Upstream (v1 Hydra key / v0.x kwarg) | Braid Lightning `lightning.json` |
|---|---|
| `actor_rollout_ref.model.path` | `target` (the skill or prompt artifact; no model weights) |
| `run_ppo(train_dataset, val_dataset)` | `data.train`, `data.holdout`, `data.freezeSha256` |
| `agentlightning.local.{agent_class, env_map}`, `rollout_timeout_seconds` | `rollout.hosts`, `rollout.timeout`, `rollout.maxTurns` |
| `n_runners`, `strategy` | `rollout.parallel` (default 1) |
| `algorithm` (APO/VERL) | `algorithm.name` (`gepa`, `apo`, `baseline`) and its bounded parameters |
| APO `gradient_model`, `apply_edit_model` | `optimizer.host` on the subscription route |
| `reward_fillna_value`, `RewardData` | `reward.components`, `reward.gate` |
| `max_rollouts` | `budget.maxRollouts`, `budget.maxOptimizerCalls`, `budget.eurCap = 0` |
| `tracer`, `adapter`, `trace_aggregator.level` | `traces.sources`, `traces.contentConsent`, `export.level` |
| `hooks` | `lightning_hooks` (code, not configuration) |
| `k8s.job_template_path`, gateway/controller ports | not offered |

## 2. Literature

**Agent Lightning, Luo et al. 2025** (arXiv 2508.03680). POMDP where an action
is one LLM call's full output; runs reduce to transitions `(input_t, output_t,
r_t)`; LightningRL gives each action the episode return, then a single-turn
algorithm (GRPO/PPO/REINFORCE++) assigns token credit; training-agent
disaggregation; Automatic Intermediate Rewarding; "Component of Interest"
(any component, including a prompt template). Results are reward curves on
Llama-3.2-3B for text-to-SQL, RAG and math; no baseline tables. Grade **B** for
the data interface, **C** for the credit scheme.

**Agent Lightning v1.0, He et al. 2026** (arXiv 2608.17528). Harnessed agentic
RL: the harness (Claude Code, OpenCode, Codex, OpenHands, mini-SWE-agent) owns
the loop; the trainer sees request/response pairs through a proxy. Four issues:
retokenization drift (best-effort token-prefix merging), rollout-level
advantage, rollout-level token-mean loss, scheduling with rollout and group
IDs. Qwen3.5-9B on filtered SWE-smith: SWE-bench Verified 41.8% to 56.4%; the
ablation favours rollout-level advantage plus rollout-level normalization
(38.2% validation reward vs 35.0% / 33.1%). Observed reward hacking: reading git
history for the gold commit, fetching upstream with wget/curl/pip/urllib; fixed
by hiding `.git` and blocking egress. Grade **B**.

**vLLM blog, "No More Retokenization Drift"** (2025-10-22). Non-unique BPE
splits, tool-call re-rendering and chat-template differences make retokenized
traces unsafe for on-policy RL; `return_token_ids` fixes it. Grade **B**.

**Trajectory-level aggregation blog** (2025-12). Trajectory mode merges a
session when token prefixes match; merge failures are a tracked metric. Grade **C**.

**APO / ProTeGi, Pryzant et al. 2023** (arXiv 2305.03495, EMNLP). Minibatch
errors produce a natural-language "gradient"; edits plus paraphrase; beam
search with bandit selection (UCB best). Up to +31% over the initial prompt on
four classification tasks; overfits after about three steps. API calls only.
Grade **B** for classification, **C** for coding agents.

**TextGrad, Yuksekgonul et al. 2024** (arXiv 2406.07496). Textual
backpropagation through a computation graph; GPQA 51% to 55% (GPT-4o); keeps a
single best candidate. Grade **B**.

**GEPA, Agrawal et al. 2025** (arXiv 2507.19457, ICLR 2026 oral). Reflection on
full trajectories, prompt mutation, Pareto-front parent selection over
instances. Qwen3-8B: +9.62 aggregate vs +3.68 for GRPO (24,000 rollouts) with
1,839–7,051 rollouts, matching GRPO's best validation in 243–1,179; lost on
AIME. GPT-4.1-mini: +12–13 over MIPROv2, TextGrad and Trace. Prompts transferred
Qwen to GPT (+9%) on QA. Grade **B** for compound QA and math; **C** for
long-horizon coding sessions.

**GRPO, DeepSeekMath, Shao et al. 2024** (arXiv 2402.03300). Group-normalized
advantage, no critic; GSM8K 82.9% to 88.2%. Zero gradient when a group has
identical rewards (advantage collapse), hence difficulty filtering. Grade **A**.

**PPO, Schulman et al. 2017** (arXiv 1707.06347). Clipped ratio with critic and
GAE; critic memory roughly doubles cost. Grade **A**.

**HybridFlow / verl, Sheng et al. 2024** (arXiv 2409.19256). Hybrid
single/multi-controller RL infrastructure; 1.53–20.57x throughput over prior
systems on 8–128 GPUs. Infrastructure, not an algorithm. Grade **A** for
throughput claims in its setting.

**Related agent RL.** ArCHer (2402.19446; utterance-level critic), RAGEN/StarPO
(2504.20073; "Echo Trap" reward-variance collapse), Search-R1 (2503.09516; mask
tool output, outcome reward suffices), ReTool (2504.11536; SFT cold start then
RL), SkyRL-Agent (2511.16108; 24.4% to 39.4% SWE-bench Verified in 4,601
H100-hours), GiGPO (2505.10978; anchor-state step groups), dense turn rewards
(2505.11821), SWE-Gym (2412.21139; 491 trajectories gave +13.6 points; a
verifier raised best-of-k to 32.0%), R2E-Gym (2504.07164; hybrid verifiers 51%).

**Judges as rewards (Consensus).** Single tokens can fool LLM judges (Zhao et
al. 2025); reference-free self-judging inflates pass rates (Zhou 2026);
trajectory-level reward models degrade on long horizons (Plan-RewardBench,
Wang et al. 2026); a production report found optimizers reading cached answer
keys and argues for deterministic guardrails, frozen holdouts and canaries
(Wahi 2026). Grade **B (negative)** for judge-only rewards on long coding
trajectories.

PubMed was queried and returned only biomedical applications; it is not
relevant to this topic. Medium posts (Tinker x Agent Lightning, SQL agents)
blocked automated reading; only their titles are recorded.

## 3. Decisions derived for Agent Braid

1. Hosted Claude Code and OpenCode expose neither weights nor token IDs. Weight
   RL on them is impossible; their traces can feed prompt optimization and,
   subject to terms of use, supervised datasets only (v1.0, vLLM blog).
2. What is justified without GPUs, in order: a trace and reward store keyed by
   rollout, attempt, group and task (B); verifiable rewards first (A);
   anti-reward-hacking controls from day one (B); reflective prompt
   optimization with Pareto selection, GEPA ahead of APO (B, C for coding);
   judges advisory only (B negative).
3. The first target is an Agent Braid artifact with a verifiable reward and an
   existing negative baseline: the guidance host models use to author
   `analyze-work` requests (SPEC-069 T010 missed D4). This keeps rollouts short
   and cheap compared to full coding sessions, the main risk identified for GEPA
   in this domain.
4. Weight RL (GRPO with rollout-level advantage and normalization, verl, a
   local open model behind a token-ID proxy) is deferred to BL.6 with its own
   ADR and founder decision. Expected cost: hundreds to thousands of GPU-hours.
5. Before any export of host-model outputs for training, check the host
   provider's usage terms (legal question, not scientific; SPEC-075 gate).

## 4. Source URLs

- https://github.com/microsoft/agent-lightning (README "Articles" section)
- https://microsoft.github.io/agent-lightning/stable/20-trainer-configuration/
- https://arxiv.org/abs/2508.03680, https://arxiv.org/abs/2608.17528
- https://blog.vllm.ai/2025/10/22/agent-lightning.html
- https://agent-lightning.github.io/posts/trajectory_level_aggregation/
- https://arxiv.org/abs/2305.03495, https://arxiv.org/abs/2406.07496,
  https://arxiv.org/abs/2507.19457, https://arxiv.org/abs/2402.03300,
  https://arxiv.org/abs/1707.06347, https://arxiv.org/abs/2409.19256
- https://arxiv.org/abs/2402.19446, https://arxiv.org/abs/2504.20073,
  https://arxiv.org/abs/2503.09516, https://arxiv.org/abs/2504.11536,
  https://arxiv.org/abs/2511.16108, https://arxiv.org/abs/2505.10978,
  https://arxiv.org/abs/2505.11821, https://arxiv.org/abs/2412.21139,
  https://arxiv.org/abs/2504.07164
