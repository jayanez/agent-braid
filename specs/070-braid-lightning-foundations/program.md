# Braid Lightning program (track BL)

**Owner decisions of 2026-11-08** (asked interactively with options, risks and a
recommendation; the owner chose the recommended option each time):

- **L1 — Optimizer backend.** The optimizer LLM (textual critique and prompt
  rewrite) runs through the host CLI in headless mode on the owner's
  subscription (Claude Code, OpenCode). Extra cash spend stays EUR 0 (ADR 0021).
  No paid API route is used by default.
- **L2 — First target.** Agent Braid's own guidance that host models use to
  author `analyze-work` requests (SPEC-069; the T010 baseline missed D4). The
  reward is verifiable: schema validity plus the D4 criteria.
- **L3 — Weight RL.** GRPO through verl on a local open model is a deferred
  milestone (BL.6), an optional extra, local runner only, no Kubernetes. Until
  then Braid Lightning exports supervised and trajectory datasets.
- **L4 — Name.** "Braid Lightning"; CLI `agent-braid lightning`; modules
  `agent_braid/lightning_*`; roadmap track BL. Upstream provenance is credited
  to microsoft/agent-lightning (MIT).
- **L5 — Definition depth.** All BL specs are fully specified now; BL milestones
  and task issues are created through the reviewed tracking reconciliation
  after merge (owner request of 2026-11-08).

## What Braid Lightning is

An optimization layer that improves the text artifacts Agent Braid owns
(skills, tool descriptions, request templates) from recorded rollouts and
verifiable rewards, and that prepares datasets for later weight training of
open models. It is advisory: it never executes work, never holds grants, never
promotes a candidate without a human decision, and it is off by default.

The research basis is in [research.md](research.md). Hosted Claude Code and
OpenCode expose neither weights nor token IDs, so "reinforcement learning" in
BL.0–BL.5 means reward-driven optimization of Agent Braid's own prompts with
recorded evidence; weight-level RL is BL.6.

## Milestones

| Milestone | Spec | Capability | Exit criterion | Depends on |
|---|---|---|---|---|
| BL.0 — Braid Lightning foundations | [SPEC-070](spec.md) | ADRs, vendoring provenance, data model, configuration, wizard, store, setup flag | ADRs reviewed; tests and Spec Kit gates pass | — |
| BL.1 — Lightning rollouts and verifiable reward | [SPEC-071](../071-lightning-rollouts-reward/spec.md) | subscription-only rollout runner and reward vector | fake-host pipeline passes; one real baseline reported against SPEC-069 T010 as a `route-changed comparison` (both proportions, Wilson intervals, route/model/version differences); zero paid-route observations | BL.0, SPEC-069 freeze |
| BL.2 — Lightning prompt optimization | [SPEC-072](../072-lightning-prompt-optimization/spec.md) | APO and GEPA over the analyze guidance | preregistered held-out evaluation completed; a null result is valid | BL.1 |
| BL.3 — Lightning promotion | [SPEC-073](../073-lightning-promotion/spec.md) | human promotion through the HAR profile registry, rollback | approved candidate shipped by hash; rollback tested | BL.2, SPEC-049 |
| BL.4 — Lightning trace consent | [SPEC-074](../074-lightning-trace-consent/spec.md) | consent, redaction, retention, trace adapters | no content without consent; secret canaries caught; purge tested | BL.0 |
| BL.5 — Lightning dataset export | [SPEC-075](../075-lightning-dataset-export/spec.md) | supervised and rollout datasets with manifests | deterministic manifests; canary corpus clean; terms-of-use gate recorded | BL.4 |
| Deferred | [SPEC-076](../076-lightning-local-grpo/spec.md) | local GPU GRPO behind a token-ID proxy | founder go/no-go and ADR 0042 | BL.5 |

The order is a dependency order, not a schedule. Milestone and issue state do
not establish acceptance, scientific validity or human review.

## Fixed boundaries for every BL spec

- `executionAuthorization` is always false; no BL code calls `execute`,
  `recover` or grant paths (Article 20).
- Promotion is human only; automatic promotion is not offered (SPEC-049 REQ-007,
  `harness_promotion.AUTOMATIC_PROMOTION = False`).
- Extra cash spend EUR 0: the only model route is the host subscription; any
  `*_API_KEY` in a rollout environment is refused.
- Rewards are empirical measurements, never guarantees or equivalence classes
  (Article 13); every rollout keeps candidate, transcript and reward hashes for
  replay (Article 14).
- Frozen held-out sets are never shown to the optimizer; canaries detect leaks.
- The MCP server never starts Braid Lightning runs; runs start only from the CLI.
- System One episodes may be read as a trace source; nothing in BL feeds a
  decision model into System One (ADR 0034).
- The core stays standard-library only. GPU dependencies exist only in the
  deferred optional extra.
