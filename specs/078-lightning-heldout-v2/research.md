# SPEC-078 research notes

## Decisions

- **Repair before optimizing.** A prompt with success probability 0 makes D4
  unreachable for every guidance, so BL.2 could not give a positive result.
  The pattern is known in agent evaluation: a sustained 0 % usually signals a
  broken task, and rigid graders have rejected correct solutions in public
  benchmarks (Anthropic, "Demystifying evals for AI agents"; OpenAI on
  SWE-bench Verified). Gate 0 checks the instrument without rollouts.
- **Guidance fix, not scorer fix (owner D1).** The research report recommended an
  optional `read` in the scorer; the owner kept the scorer frozen and narrowed
  the guidance. Alternative recorded, not adopted.
- **Size.** McNemar at α = 0.05 and power 0.8 needs about 107 paired prompts to
  detect 83 % → 93 % and about 77 for 75 % → 88 % (report's own calculation).
  Test = 100 prompts (OD-2).
- **Statistics.** Paired per-prompt differences and prompt-clustered standard
  errors (Miller, arXiv 2411.00640); Wilson rather than CLT intervals for small
  n (Bowyer et al., arXiv 2503.01747).
- **Splits.** Separate reflection (feedback) and selection (validation) sets
  as in GEPA (arXiv 2507.19457), and an eyes-off test pass per arm, to limit
  winner's-curse selection on a small set (BL.2's A2 fell from 0.967 on
  development to 24/30 on held-out; observed, not explained).
- **Gate 2 method.** Bounded section edits kept only on strict validation
  improvement (SkillOpt, arXiv 2605.23904); incremental edits avoid the
  brevity bias and context collapse of whole rewrites (ACE, arXiv 2510.04618).
  APO is dropped.
- **Reward-hacking guards.** The `independent-candidate` share of each split
  (it is what an "always partial coverage" edit fails), negative `unknown` cases
  against over-declaration, a length cap, fixed front matter, a skill-loaded check (skills are not always invoked; Vercel agent
  evals), no LLM judge.

## Alternatives considered

- Turn v1 into a regression suite without v2: rejected, v1 has no power and a
  known broken item history.
- Keep D4 as the primary rule: rejected, a single broken item decides it.
- Weight-level RL: out of scope (SPEC-076, BL.6 deferred).

## Limits

The cited figures come from the 2026-11-20 research report and its sources; this
repository does not reproduce them. Power figures assume independent prompts.
