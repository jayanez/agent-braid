# SPEC-076: Lightning local GRPO

**Milestone:** Deferred.

**Status:** deferred. Fully specified; no implementation task may start until
every reopen criterion in [deferral.md](deferral.md) holds. Program position:
BL.6, after BL.5 ([SPEC-075](../075-lightning-dataset-export/spec.md)).

## Purpose and scope

Specify, ahead of time, how weight-level reinforcement learning (GRPO or RLOO)
of a local open model would run on Agent Braid rollouts, so that a reopen
decision can be made on a concrete design and budget. Hosted Claude Code and
OpenCode expose neither weights nor token IDs; weight RL therefore needs a
local model behind a token-ID proxy (research §3, decision 1 and 4).

In scope (when reopened):

- `agent_braid/lightning_proxy.py`: OpenAI-compatible loopback proxy, port of
  upstream v1 `agentlightning/server/proxy.py` onto `agent_braid/view_serve.py`
  helpers;
- a local open model served by vLLM on a local CUDA GPU;
- optional extra `lightning-gpu` in `pyproject.toml` (verl, vllm, torch pinned),
  installed only in an isolated environment per AGENTS.md;
- a local runner only (no Kubernetes);
- GRPO/RLOO with rollout-level advantage, `per_rollout_mean` loss, trajectory
  aggregation, difficulty filtering, `max_ppo_update_times`, optional async
  rollout;
- reward-hacking controls; budget estimate; a proposed `training` section for
  `lightning.json`.

Exclusions:

- Any use of trained weights as a System One backend or decision model
  (ADR 0034); trained weights are laboratory artifacts only.
- Kubernetes, remote clusters, paid GPU rental or any cash spend (ADR 0021,
  EUR 0) unless a new owner decision changes the budget.
- Training on host-model output without the SPEC-075 terms gate (OD-1).
- Hydra; the `training` section stays outside configuration v0.1.
- Automatic promotion; promotion stays human (SPEC-073).

## Authorities

- [CONSTITUTION.md](../../CONSTITUTION.md), Articles 13–16, 19, 20, 23, 24.
- [Program](../070-braid-lightning-foundations/program.md) fixed boundaries;
  [SPEC-070](../070-braid-lightning-foundations/spec.md) REQ-001 (ADR 0042
  proposed, deferred to BL.6).
- [Research](../070-braid-lightning-foundations/research.md) §3.
- ADR 0021, ADR 0034; SPEC-034 to SPEC-037 "no fine-tuning" statements, scoped
  to forecasting and requiring the ADR 0042 carve-out.
- [contracts/token-proxy.md](contracts/token-proxy.md),
  [contracts/training-config-proposal.md](contracts/training-config-proposal.md).

## Clarifications

Design decisions (proposed; decided only after reopening):

- **G1 — Proxy base.** Reuse `view_serve` loopback rules (`LOOPBACK_HOSTS`,
  bind refusal, owner token files, `parse_json_body`, bounded body reads). No
  new HTTP framework.
- **G2 — Forced fields.** The proxy sets `return_token_ids: true` and
  `logprobs: true` on every forwarded request; a backend response without token
  IDs is a recorded failure, not silently accepted.
- **G3 — Runner.** One local process tree: vLLM server, proxy, rollout
  workers, verl trainer. No Kubernetes job template (upstream `k8s` key dropped).
- **G4 — Algorithm defaults.** GRPO, `enable_rollout_level_advantage: true`,
  `loss_mode: per_rollout_mean`, trajectory aggregation, as upstream defaults.
- **G5 — Isolation.** The `lightning-gpu` extra is never installed in the
  default or CI environment.

Open decisions:

- **OD-1 — Founder go/no-go** on reopening (T001).
- **OD-2 — ADR 0042 acceptance** (fine-tuning carve-out).
- **OD-3 — Base model and licence** of the local open model.
- **OD-4 — Hardware** (local CUDA GPU class and memory).

## Requirements and acceptance scenarios

### REQ-001 — Reopen gate

No implementation before founder go, ADR 0042 accepted, a local CUDA GPU
available and SPEC-075 delivered.

**SC-001:** Given the reopen criteria, when T001 runs, then a founder record
states go or no-go with each criterion's evidence; on no-go the spec stays
deferred. Verification: procedure_001; T001.

### REQ-002 — Loopback proxy

`lightning_proxy` binds 127.0.0.1 or ::1 only and requires an owner bearer token.

**SC-002:** Given the proxy, when asked to bind 0.0.0.0 or called without the
token, then it refuses. Verification: procedure_002; T003.

### REQ-003 — Token IDs and logprobs

Forwarded requests carry `return_token_ids` and `logprobs`; responses lacking
token IDs are recorded as `token-ids-missing`.

**SC-003:** Given a fake backend, when a chat completion passes through, then
the forwarded body has both fields and a response without token IDs yields the
failure record. Verification: procedure_003; T004.

### REQ-004 — Event recording

Every call is recorded as a `model_request` event keyed by rollout and attempt
in the Lightning store, with prompt and response token IDs and hashes. This
adds the event schema `braid-lightning-event/v0.2`: host `local-vllm` and, in
`model_request`, `promptTokenIdsSha256` and `responseTokenIdsSha256`.
`braid-lightning-event/v0.1` records stay readable unchanged. ADR 0042 records
this schema change.

**SC-004:** Given two rollouts with retries, when calls pass through, then each
event carries the right rollout and attempt IDs and replay rebuilds the
sequence. Verification: procedure_004; T005.

### REQ-005 — Pause and resume

The proxy pauses for weight updates (503 with `Retry-After`), drains in-flight
calls, then resumes.

**SC-005:** Given in-flight calls, when pause is requested, then new calls get
503, in-flight calls finish, and resume restores service. Verification:
procedure_005; T006.

### REQ-006 — Optional isolated extra

`lightning-gpu` pins verl, vllm and torch; core imports never require them.

**SC-006:** Given the default environment, when the core test modules run and
the package metadata is read, then nothing imports torch/vllm/verl and the extra
is optional. Verification: procedure_006; T002.

### REQ-007 — Local runner only

One CLI command starts and stops the local process tree; no Kubernetes path.

**SC-007:** Given a fake-GPU mode, when the runner starts and is interrupted,
then every child exits and no Kubernetes code or key exists. Verification:
procedure_007; T007.

### REQ-008 — GRPO/RLOO objective

Rollout-level advantage with group normalization and `per_rollout_mean` loss.

**SC-008:** Given synthetic grouped rewards, when advantages and loss weights
are computed, then they match hand-computed values for GRPO and RLOO.
Verification: procedure_008; T008.

### REQ-009 — Trajectory aggregation

Training uses SPEC-075 trajectory aggregation with token-ID prefix merge and
length bounds.

**SC-009:** Given recorded token IDs, when aggregated, then merged prompts match
the prefix and overlong records are dropped and counted. Verification:
procedure_009; T009.

### REQ-010 — Difficulty filtering and update cap

Groups with zero reward variance are filtered; `max_ppo_update_times` caps
updates per batch.

**SC-010:** Given groups all-pass, all-fail and mixed, when filtered, then only
mixed groups remain and the update count never exceeds the cap.
Verification: procedure_010; T010.

### REQ-011 — Async rollout option

An `asyncRollout` option overlaps rollout and training with a bounded staleness.

**SC-011:** Given async enabled, when a step completes, then recorded staleness
never exceeds the bound; disabled, rollouts and updates alternate.
Verification: procedure_011; T011.

### REQ-012 — Reward-hacking controls

Rollout workspaces hide `.git`, deny network egress except the proxy, and carry
canaries; a canary read or test-file edit zeroes the reward and is logged.

**SC-012:** Given planted hacks (reading `.git`, editing tests, network call),
when rollouts run, then each is blocked or detected and rewarded zero.
Verification: procedure_012; T012.

### REQ-013 — No System One backend

Trained weights are never loaded by System One or the MCP server.

**SC-013:** Given the code base, when a boundary test scans imports and
configuration, then no System One path references Lightning weights.
Verification: procedure_013; T013.

### REQ-014 — Budget and configuration proposal

A budget estimate (hundreds to thousands of GPU-hours) and the proposed
`training` section are recorded and reviewed.

**SC-014:** Given the literature and upstream defaults, when the estimate and
proposal are reviewed, then each figure has a source and the proposal maps every
retained upstream key. Verification: procedure_014; T014.

### REQ-015 — Preregistered evaluation and converge

A held-out evaluation is preregistered before training; artifacts converge.

**SC-015:** Given a frozen held-out set, when the trained model and base are
evaluated, then results with intervals are reported, a null result is valid,
and `speckit-converge` passes. Verification: procedure_015; T015.

## Scientific boundaries and compatibility

Hypothesis (deferred): GRPO on verifiable Agent Braid rewards may raise a local
model's held-out pass rate; untested. Additive optional extra and modules; no
change to core or MCP surfaces. One schema change: the new event schema
`braid-lightning-event/v0.2` (REQ-004, recorded by ADR 0042); v0.1 events stay
readable.

## Evidence and unresolved questions

None obtained. Open: OD-1 to OD-4.
