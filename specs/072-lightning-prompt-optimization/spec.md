# SPEC-072: Lightning prompt optimization

**Milestone:** BL.2 — Lightning prompt optimization (GitHub milestone created by
the reviewed tracking reconciliation after merge).

**Status:** draft. Owner decisions L1–L5 of 2026-11-08 apply (see the
[program](../070-braid-lightning-foundations/program.md)). OD-1 and OD-2 are
decided. `human_review` is pending (T001 owner review recorded 2026-11-11); this specification grants no execution
authority and promotes nothing. Implementation converged on 2026-11-13 (T012):
T001–T013 are done and the preregistered held-out evaluation gave a **negative
result** (H1 not supported); see [Outcome and convergence](#outcome-and-convergence-t012-2026-11-13).
Convergence is not a human review and does not freeze this specification.

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

Constitution clause zero and Articles 9, 12, 13, 14, 19, 20, 21 and 23;
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

- **P1 — Development only, content-free reflection.** The optimizer sees only
  development prompts and, until BL.4 (SPEC-074) exists, only the content-free
  reward vector, `score_case` reasons, refusal codes and the candidate text
  itself; it never sees transcripts. Transcript-based reflection is an optional
  later mode gated on SPEC-074 consent `redacted`. BL.2 therefore depends on
  BL.1 only. Held-out prompts are run once per arm after the protocol hash is
  frozen.
- **P2 — Scalar for selection.** APO and GEPA select by the mean of
  `d4FirstAttempt` over the minibatch, with `schemaValid` mean as tie-breaker;
  GEPA's Pareto front uses per-prompt `d4FirstAttempt`. The reward vector is
  stored in full.
- **P3 — Candidate scope.** A candidate replaces the whole body of the analyze
  skill below its front matter; the front matter is fixed.
- **P4 — Shared optimizer host.** The optimizer host is `optimizer.host` from
  the configuration; rollouts run in every configured host.

Owner decisions:

- **OD-1 — Held-out size (decided 2026-11-11).** Keep the frozen SPEC-069
  held-out set: 10 cases × 3 repetitions. D4 is a binary rule; the low power
  of the descriptive sign test is a declared limit. No new FREEZE version.
- **OD-2 — Required hosts (decided; Amendment 1 approved 2026-11-13).** Required
  hosts were fixed as `claude-code` and `opencode`; Codex is a declared limit
  in SPEC-069. Protocol Amendment 1 (draft, 2026-11-13) reduces them to
  `claude-code`: `opencode` reports no subscription credential source, so the
  SPEC-071 runner refuses it as `route-unverified` (SPEC-071 OD-2), and it
  becomes a declared limit. The same amendment makes A0 the current `develop`
  guidance (SPEC-069 T008 rewrite) with a new development baseline run, model
  pinned to `claude-sonnet-5-5`. The preregistered primary arm is GEPA (A2);
  APO (A1) is secondary and descriptive only.

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
  reflection over the parent's minibatch reward vectors, `score_case` reasons,
  refusal codes and the parent text (no transcripts before BL.4; transcript
  reflection is an optional later mode gated on SPEC-074 consent), accepts a
  child only if its minibatch score exceeds the parent's, and then evaluates it
  on the full development set. The implementation cites the paper and vendors
  no code.
- **REQ-006 — Contamination controls.** Before every optimizer call the
  algorithm hashes the full optimizer input and refuses
  (`holdout-contamination`) if it contains any held-out prompt text, held-out
  case id, or the held-out canary; held-out prompts are loaded only by the
  held-out evaluation command; SPEC-071 canaries remain active; any refusal
  stops the run. Every optimizer call runs in the SPEC-071 disposable profile
  and OS sandbox with no readable path to `held-out.json`, the scoring sources
  or `.git`.
- **REQ-007 — Budgets and stopping.** Runs stop at `budget.maxRollouts`,
  `budget.maxOptimizerCalls`, `algorithm.rounds`, a SPEC-071 quota stop (which
  ends the run; the same run id resumes only by an explicit
  `agent-braid lightning run --resume <run-id>`), or
  when the development score has not improved for 2 consecutive rounds; APO is
  capped at 3 rounds by default (ProTeGi overfitting beyond about 3 steps); the
  stop reason is recorded. Budgets are per arm run: each arm is a separate
  `lightning run` with its own `budget.maxRollouts`, and the preregistered
  algorithm parameters in the protocol's feasibility table override the
  configuration defaults where these exceed one arm budget.
- **REQ-008 — Held-out evaluation and analysis.** After the freeze, each arm
  (A0 baseline guidance, A1 best APO, A2 best GEPA) runs once on the held-out
  set in every required host (`claude-code`; `opencode` is a declared limit
  per protocol Amendment 1) with the protocol's
  repetitions; the report gives, per host and arm, the D4 verdict, Wilson 95 %
  intervals, and paired per-prompt comparisons against baseline as specified
  in the protocol. H1 is supported if and only if, in every required host, A0
  misses D4 on held-out and the primary arm A2 (GEPA) meets D4; if A0 meets D4
  in a required host, H1 is `not assessable` for that host. A1 (APO) is
  secondary and descriptive only. A null or negative result is reported as the
  outcome.
- **REQ-009 — Boundaries.** No BL.2 code writes to the repository skill file,
  calls `harness_promotion`, `execute`, `recover` or grant paths, exposes an MCP
  tool, or adds a runtime dependency; the best candidate is reported by hash
  only, for SPEC-073.
- **REQ-010 — Replay.** Every run records configuration digest, seeds, candidate
  lineage, optimizer prompt hashes, optimizer transcript hashes and SPEC-071
  attempt-result (`braid-lightning-attempt-result/v0.1`) record hashes, so that re-scoring the stored content-free parsed attempts
  (SPEC-071 REQ-011) reproduces every selection decision.
- **REQ-011 — SPEC-049 evaluation pair.** The held-out report emits a SPEC-049
  `Registration` and `EvaluationRecord` pair in the formats of
  `agent_braid/harness_promotion.py` and `agent_braid/harness_evaluation.py`
  (`REGISTRATION_FORMAT`, `REPORT_FORMAT`), with arm A = A0 baseline and arm
  C = the preregistered primary arm (A2 GEPA), recording the H1 outcome per
  required host, so that SPEC-073 can call `harness_promotion.decide()` on it.
  BL.2 only writes the pair; it never calls `decide()`.

## Success criteria

Each requirement has one acceptance scenario (SC-001 to SC-011) in
`assurance.json`, with its procedure in [validation-plan.md](validation-plan.md).
Milestone exit: SC-001 and SC-008 obtained; the result may be null. Both are
obtained (2026-11-13); the result is negative.

## Outcome and convergence (T012, 2026-11-13)

Assessed against [assurance.json](assurance.json) and the committed evidence.
Protocol adherence and the result are reported separately.

**Protocol adherence.** Amendment 1 was approved before any development
rollout; the protocol was frozen by hash
([protocol-freeze.json](evidence/protocol-freeze.json)) before the held-out set
was opened; each arm ran once on the held-out set (90 rollouts, `claude-code`
2.1.311, model `claude-sonnet-5-5`, subscription route, no stop, no refusal,
0 canary hits, clean teardown). Two build defects stopped A0 and then A1 with
`arm-error` before their first held-out rollout (#1356, #1357); they were fixed
without touching the protocol, A0's 30 completed rollouts were kept, and the
command resumed. No rollout was repeated or discarded.

**Development phase (T009, descriptive;
[development-arms.json](evidence/development-arms.json)).** A0 (current
guidance) 27/30 first attempt on the development set; best APO candidate
`39ae1856…` 0.233 on the full development set (9 optimizer calls, 60
rollouts); best GEPA candidate `623c55c3…` 0.967 (3 optimizer calls, 45
rollouts).

**Held-out result (T010; [heldout-arms.json](evidence/heldout-arms.json)) —
negative.** A0 25/30 first attempt (8/10 prompts, Wilson 0.66–0.93), A1 APO
23/30 (7/10), A2 GEPA 24/30 (7/10, Wilson 0.63–0.90); every arm misses D4 in
`claude-code`. Paired per prompt against A0: A2 1 improved, 8 unchanged,
1 worsened; A1 1, 7, 2 (exact sign test p = 1.0 for both). By the
preregistered rule A0 misses and A2 misses, so **H1 is not supported**. The
SPEC-049 pair ([registration](evidence/heldout-registration.json),
[evaluation record](evidence/heldout-evaluation-record.json); A = A0, C = A2)
records the same outcome. The A2 drop from 0.967 on development to 24/30 on
held-out is observed, not explained; no claim about overfitting is made.

**Hand-off to SPEC-073.** Best GEPA candidate (A2, primary)
`623c55c39d31799f7d89e5dac9401062ce2eaed2b6bca01589d7c531f3e8b966`; best APO
candidate (A1, descriptive)
`39ae18565806b6dd3b2e8181dc223dd70b735c1e18ed371c17233382602057fd`. Neither
met D4 on held-out, so BL.2 offers **no candidate for promotion**; the hashes
are recorded for traceability only.

| Status | Items |
|---|---|
| Satisfied (obtained evidence) | SC-001 to SC-011, each by its procedure record in `evidence/` |
| Negative (research outcome) | H1 not supported (SC-008, SC-011) |
| Failed | none |
| Inconclusive | none; A1 is descriptive by design |
| Pending | exploratory arms E1/E2 (Amendment 1 item 6, development only, descriptive) have not been run, so the descriptive table of analysis step 7 does not exist; they cannot change H1. Human review of this specification and its freeze remain the owner's |
| Declared limits | one required host (`opencode` route-unverified, Codex a SPEC-069 limit); one model; one held-out pass of 10 prompts × 3 repetitions (low power); fake hosts for the pipeline procedures |

## Compatibility

Additive. No existing output changes; the shipped skill is untouched. Records
use `braid-lightning-candidate/v0.1` (new `lightning_store.KINDS` entry
`candidate`) and the SPEC-071 record schemas.
