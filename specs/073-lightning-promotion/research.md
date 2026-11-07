# SPEC-073: Research

Shared research: [SPEC-070 research](../070-braid-lightning-foundations/research.md)
(upstream agent-lightning, APO and GEPA literature, derived decisions).

Spec-specific decisions:

- **Registry reuse.** `agent_braid/harness_promotion.py` already provides
  `decide()` and `ProfileRegistry.record/begin/commit/abort/rollback/revoke_evidence`
  with a replayable journal, `COHORTS = ("synthetic", "native")` and
  `AUTOMATIC_PROMOTION = False`. Rejected alternative: a Lightning-specific
  registry (a duplicate state machine and a second audit trail).
- **Size boundary.** `harness_experience.MAX_LESSON = 512` makes the experience
  store unsuitable for whole skill texts; it remains the carrier for short
  reflections, with its quarantine and poison screening.
- **Upstream.** agent-lightning v0.x updates versioned "resources" in its store
  (`agentlightning/store/base.py`) and serves the latest version to runners
  automatically. That automatic hot-swap is not ported; promotion is a human,
  journaled, reversible step.
- **Build integrity.** `agent_braid/plugin_package.py` already inventories file
  hashes (`file_hash`, `inventory`, `verify_package`); the new check compares
  mapped entries against the registry instead of adding a second hashing path.
