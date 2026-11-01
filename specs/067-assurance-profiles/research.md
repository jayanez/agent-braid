# SPEC-067: Research

Sources: repository specs and documents read on 2026-11-01 and the owner's
description of current practice. No harness code was run and nothing was
measured for this specification.

## R1 Current practice is prose

`quick`, `pr` and `sensitive` validation are documented in
`VALIDATION_PROFILES.md`. The three pre-PR reviews, serial squash-merge by an
orchestrator, the standing auto-merge authorization with conditions (owner,
2026-10-31), release only with owner approval and no AI attribution live in
owner memory, global instructions and session briefs, not in the repository. None
is a checkable artifact, so adherence is invisible and depths cannot vary by risk.

## R2 Patterns to reuse

- SPEC-058 REQ-006 (draft) and its settings implementation
  `ownership.resolve_settings`: scalar mode ladder, scope precedence, one floor
  (`block` at repository or user scope), recorded refusal of lowering. Followed as
  precedent; the per-checkpoint floors and two-dimensional resolution are new.
- SPEC-057: operator-owned settings resolver and policy-profile schema; the
  compiled profile follows the same advisory, `executionAuthorization: false`
  shape.
- SPEC-049 `harness_promotion`: journal of begin/commit/rollback steps for
  evaluated decisions; its pattern is followed, the module is not reusable for
  assurance profiles (no evaluation candidate).
- SPEC-050 T002, T006, T009, T011: registry, orchestration policies,
  auto-promotion (disabled by default) and lifecycle; the checkpoint catalog
  fits the lifecycle, and `harness-self-change` stays human-only.
- `scripts/validate_change.py`: `quick`/`pr`/`sensitive` and `classify()`, an
  existing deterministic raise-only path classifier (ADR 0011); the `pre-commit`
  and `ci` gates exist and this specification records their receipts.
- `agent_braid/harness_quota.py`: plan-usage readings, a cost proxy for H1.

## R3 Alternatives rejected

- Extending SPEC-058's guard to enforce review depths: couples process policy to
  hook enforcement and changes a spec outside this track.
- Encoding practice only in CI: cannot see pre-PR reviews or HITL modes and
  would change shared tooling.
- A single global strictness knob: cannot express floors or per-checkpoint HITL.
- Letting the agent pick its depth: violates operator ownership (REQ-008).

## R4 Known limits

Review agents are fallible and correlated; a receipt shows a review ran, not that
it was right. Path-based risk classification misses semantic risk. The
effect of depths on outcomes is unknown (H1).
