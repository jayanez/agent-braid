# SPEC-072 implementation plan

## Technical context and scope

SPEC-071 provides a subscription-only runner, rollout records and a verifiable
reward vector. The target is the body of
`integrations/agent-braid/skills/agent-braid-analyze/SKILL.md`. The optimizer
LLM is a host CLI call through the same runner (L1). The runtime stays
standard-library only. Scope follows REQ-001 to REQ-010.

## Constitution check before research

- Clause zero, Article 0: a measured hypothesis about prompt text; no algebraic
  claim.
- Article 9: the protocol must be able to produce a counterexample; a null
  result is a valid outcome.
- Articles 13, 14: rewards are empirical; lineage and hashes are recorded.
- Article 19: the problem is the T010 negative baseline.
- Article 20: no execution, no promotion.
- Article 21: research value (preregistered comparison) and engineering value
  (reusable optimizer) are both stated.
- Article 23: laboratory phase.

No MUST contradiction found. No SHOULD deviation proposed.

## Research and alternatives

See [research.md](research.md).

## Design

| Upstream source | New module | Notes |
|---|---|---|
| v0.x `agentlightning/types/resources.py` (`PromptTemplate`) | `agent_braid/lightning_resources.py` | sha256, parent, origin |
| v0.x `agentlightning/algorithm/base.py` | `agent_braid/lightning_algorithm.py` | synchronous interface |
| v0.x `agentlightning/algorithm/fast.py` (`Baseline`) | `agent_braid/lightning_algorithm.py` | seed evaluation |
| v0.x `agentlightning/algorithm/apo/apo.py` | `agent_braid/lightning_apo.py` | beam search, textual gradients |
| v0.x `agentlightning/algorithm/apo/prompts/*.poml` | `agent_braid/lightning_prompts/*.md` | plain templates, hashes recorded |
| arXiv 2507.19457 (paper only) | `agent_braid/lightning_gepa.py` | no code vendored |

Optimizer call path: algorithm builds input from development data only,
contamination check (REQ-006), runner call on `optimizer.host`, parse the
candidate text, record the candidate, evaluate through rollouts.

Held-out path: a separate CLI command (`agent-braid lightning report
--holdout`) checks the protocol freeze and FREEZE hashes, runs arms A0–A2, and
writes the analysis.

## Constitution check after design

Unchanged. Promotion stays outside the design.

## Phases

1. P0 — owner review and decisions OD-1, OD-2 (T001).
2. P1 — resources, algorithm base, baseline (T002–T003).
3. P2 — APO, GEPA, contamination, budgets, replay (T004–T008).
4. P3 — development runs and protocol freeze (T009).
5. P4 — held-out evaluation and analysis (T010).
6. Closing — boundaries check and converge (T011–T012).

## Risks

- Overfitting to 10 development prompts: rounds capped, held-out untouched.
- Optimizer output not a valid skill body: refused and counted as a failed call.
- Quota exhaustion: runs pause; budgets are per arm.
- Low power: decision rule fixed in advance; intervals reported.
- Host model updates between arms: arms run in the same window; versions
  recorded; mismatch reported as a limit.
