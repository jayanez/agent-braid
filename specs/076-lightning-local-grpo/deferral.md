# SPEC-076: Deferral record

**Status:** deferred (milestone "Deferred").

## Why deferred

- Hosted hosts expose no weights or token IDs; weight RL needs a local model
  and a CUDA GPU the project does not have today.
- Cost: hundreds to thousands of GPU-hours for meaningful GRPO runs on coding
  agents (research §2 and §3); incompatible with EUR 0 unless local hardware
  exists.
- Governance: SPEC-034 to SPEC-037 exclude fine-tuning for forecasting; any
  weight training needs the ADR 0042 carve-out.
- Prompt optimization (BL.2) may deliver the gain without weights; a null or
  positive result there informs this decision.

## Reopen criteria (all required)

1. Founder go recorded (T001).
2. ADR 0042 accepted.
3. A local CUDA GPU available, class recorded (OD-4).
4. SPEC-075 delivered, including the terms gate for any host-derived data.

## What is ready now

- This specification, plan, tasks, validation plan and contracts.
- Upstream reference v1.0.3 (`bc3a9e80`) mapped file by file in the plan.
- The proposed `training` section ([contract](contracts/training-config-proposal.md)),
  outside configuration v0.1.
- Reusable foundations: `view_serve` loopback helpers, the SPEC-070 store,
  SPEC-071 rewards, SPEC-075 trajectory export.
