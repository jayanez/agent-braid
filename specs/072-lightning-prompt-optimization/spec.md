# SPEC-072: Lightning prompt optimization

**Milestone:** BL.2 — Lightning prompt optimization (GitHub milestone created by
the reviewed tracking reconciliation after merge).

**Status:** draft. Owner decisions L1–L5 of 2026-11-08 apply (see the
[program](../070-braid-lightning-foundations/program.md)). OD-1 and OD-2 are
open. `human_review` is pending; this specification grants no execution
authority and promotes nothing.

## Purpose and scope

The SPEC-069 T010 baseline missed D4 in Claude Code and OpenCode (16/30
first-attempt successes each, development set). This specification is a
research protocol: it asks whether reward-driven optimization of the
`agent-braid-analyze` guidance text, using the SPEC-071 runner and reward,
meets D4 on the frozen held-out set. It delivers the algorithms, a versioned
candidate record, and a preregistered evaluation in
[evaluation-protocol.md](evaluation-protocol.md). A null or negative result
completes the protocol.

In scope:

- `agent_braid/lightning_resources.py`: versioned prompt candidates (text,
  sha256, parent, origin skill);
- `agent_braid/lightning_algorithm.py`: port of upstream `Algorithm` base and
  `Baseline`;
- `agent_braid/lightning_apo.py`: port of upstream APO beam search with textual
  gradients; `.poml` prompts converted to plain Markdown templates in
  `agent_braid/lightning_prompts/`;
- `agent_braid/lightning_gepa.py`: GEPA implemented from arXiv 2507.19457, no
  code vendored;
- the optimizer LLM invoked only through the SPEC-071 runner host CLI on the
  subscription route;
- contamination controls, budgets, stopping rules, and the preregistered
  held-out evaluation with its analysis.

Exclusions:

- Promotion of any candidate or editing the shipped skill (SPEC-073).
- Weight training (SPEC-076), dataset export (SPEC-075).
- Changing the SPEC-069 prompt sets, FREEZE, D4 or scoring code.
- Optimizing tool descriptions, schemas or any target other than
  `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md`.
- Any paid route, LLM judge, or claim beyond the observed hosts, models and
  prompt sets.

## Authorities

Constitution clause zero and Articles 0, 9, 12, 13, 14, 19, 20, 21 and 23;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md) (EUR 0
spend); [ADR 0034](../../docs/adr/0034-system-one-shadow-advisory-boundary.md);
ADR 0039 (Braid Lightning boundary) and ADR 0040 (MIT vendoring into AGPL),
both Proposed by SPEC-070. Precedents:
[SPEC-049](../049-harness-evaluation-learning/spec.md) (human-only promotion),
[SPEC-069](../069-aim-request-authoring/spec.md) (prompt sets, D4, FREEZE),
[SPEC-070](../070-braid-lightning-foundations/spec.md),
[SPEC-071](../071-lightning-rollouts-reward/spec.md). Research basis:
[SPEC-070 research](../070-braid-lightning-foundations/research.md) and
[research.md](research.md).

## Clarifications

Owner decisions L1 (optimizer through the host CLI on the subscription, EUR 0),
L2 (first target: the `analyze-work` authoring guidance, verifiable reward),
L3 (no weight RL), L4 and L5 apply.

Design decisions recorded here:

- **P1 — Development only.** The optimizer sees only development prompts,
  their rewards and transcripts. Held-out prompts are run once per arm after
  the protocol hash is frozen.
- **P2 — Scalar for selection.** APO and GEPA select by the mean of
  `d4FirstAttempt` over the minibatch, with `schemaValid` mean as tie-breaker;
  GEPA's Pareto front uses per-prompt `d4FirstAttempt`. The reward vector is
  stored in full.
- **P3 — Candidate scope.** A candidate replaces the whole body of the analyze
  skill below its front matter; the front matter is fixed.
- **P4 — Shared optimizer host.** The optimizer host is `optimizer.host` from
  the configuration; rollouts run in every configured host.

Open decisions:

- **OD-1 — Held-out size.** The SPEC-069 held-out set has 10 cases; whether to
  keep 10 cases × 3 repetitions (power limited) or extend it before freezing
  the protocol (requires a new FREEZE version under SPEC-069 rules). Blocks
  T009.
- **OD-2 — Required hosts.** Whether H1 is evaluated in Claude Code and
  OpenCode only (Codex is a declared limit in SPEC-069) or waits for Codex.
  Blocks T009.

## Requirements

- **REQ-001 — Owner review and protocol freeze.** The owner reviews the spec,
  plan, contracts and `evaluation-protocol.md`; the protocol's sha256 is
  recorded in `evidence/protocol-freeze.json` before any held-out rollout; the
  held-out command refuses if the protocol file hash differs.
- **REQ-002 — Candidate resource.** `lightning_resources` stores each candidate
  per [contracts/candidate.md](contracts/candidate.md): text, sha256 of the
  UTF-8 bytes, parent sha256 or null, origin path, algorithm, round, and the
  optimizer call ids that produced it; the record is immutable and
  canonical-JSON round-trips byte-identically.
- **REQ-003 — Algorithm base and baseline.** `lightning_algorithm` provides the
  upstream `Algorithm` interface (run over a task set with a resource store and
  runner) and `Baseline`, which evaluates the seed candidate unchanged; Baseline
  on fake hosts reproduces the SPEC-071 fake-host summary exactly.
- **REQ-004 — APO.** `lightning_apo` implements beam search with textual
  gradients per upstream v0.x `apo.py`: `beamWidth`, `branchFactor`, `rounds`,
  `minibatch` from configuration; critique and edit prompts are the Markdown
  templates in `agent_braid/lightning_prompts/` converted from the upstream
  `.poml` files with recorded hashes; every optimizer call goes through the
  SPEC-071 runner on the subscription route.
- **REQ-005 — GEPA.** `lightning_gepa` maintains a Pareto front of candidates
  over per-prompt reward vectors, selects a parent from the front with
  probability proportional to the number of prompts it dominates on, mutates by
  reflection over the parent's minibatch transcripts and rewards, accepts a
  child only if its minibatch score exceeds the parent's, and then evaluates it
  on the full development set. The implementation cites the paper and vendors
  no code.
- **REQ-006 — Contamination controls.** Before every optimizer call the
  algorithm hashes the full optimizer input and refuses
  (`holdout-contamination`) if it contains any held-out prompt text, held-out
  case id, or the held-out canary; held-out prompts are loaded only by the
  held-out evaluation command; SPEC-071 canaries remain active; any refusal
  stops the run.
- **REQ-007 — Budgets and stopping.** Runs stop at `budget.maxRollouts`,
  `budget.maxOptimizerCalls`, `algorithm.rounds`, a SPEC-071 quota stop, or
  when the development score has not improved for 2 consecutive rounds; APO is
  capped at 3 rounds by default (ProTeGi overfitting beyond about 3 steps); the
  stop reason is recorded.
- **REQ-008 — Held-out evaluation and analysis.** After the freeze, each arm
  (baseline guidance, best APO, best GEPA) runs once on the held-out set in
  every required host with the protocol's repetitions; the report gives, per
  host and arm, the D4 verdict, Wilson 95 % intervals, and paired per-prompt
  comparisons against baseline as specified in the protocol; H1 is accepted or
  rejected exactly by the preregistered rule, and a null or negative result is
  reported as the outcome.
- **REQ-009 — Boundaries.** No BL.2 code writes to the repository skill file,
  calls `harness_promotion`, `execute`, `recover` or grant paths, exposes an MCP
  tool, or adds a runtime dependency; the best candidate is reported by hash
  only, for SPEC-073.
- **REQ-010 — Replay.** Every run records configuration digest, seeds, candidate
  lineage, optimizer prompt hashes, optimizer transcript hashes and rollout
  record hashes, so that re-scoring the stored transcripts reproduces every
  selection decision.

## Success criteria

Each requirement has one acceptance scenario (SC-001 to SC-010) in
`assurance.json`, with its procedure in [validation-plan.md](validation-plan.md).
Milestone exit: SC-001 and SC-008 obtained; the result may be null.

## Compatibility

Additive. No existing output changes; the shipped skill is untouched. Records
use `braid-lightning-candidate/v0.1` and the SPEC-071 record schemas.
