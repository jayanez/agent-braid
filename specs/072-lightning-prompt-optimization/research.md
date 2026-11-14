# SPEC-072: Research

The upstream analysis and literature review are in
[SPEC-070 research](../070-braid-lightning-foundations/research.md). This file
records decisions specific to BL.2.

- **APO source.** Upstream v0.x `agentlightning/algorithm/apo/apo.py` (commit
  `6db3c73d`): beam initialization, parent sampling, textual gradient over a
  minibatch, apply-edit, beam evaluation and selection. Its prompts
  (`text_gradient_variant01–03.poml`, `apply_edit_variant01–02.poml`) become
  Markdown templates with `{placeholders}`; POML rendering is not ported.
- **Algorithm base.** v0.x `algorithm/base.py` and `algorithm/fast.py`
  (`Baseline`); async methods become synchronous calls through the runner.
- **Resources.** v0.x `types/resources.py` `PromptTemplate`; extended with
  sha256 and parent lineage (Article 14).
- **GEPA.** arXiv 2507.19457: reflective prompt evolution with a Pareto front
  over per-instance scores, parent sampling weighted by front membership,
  minibatch acceptance before full evaluation. Reported to beat GRPO with up to
  35× fewer rollouts and to outperform MIPROv2. Implemented from the paper's
  description only; no code from the GEPA or DSPy repositories is vendored.
- **ProTeGi overfitting.** arXiv 2305.03495 reports gains that flatten or
  reverse after about 3 optimization steps; hence the APO cap of 3 rounds and
  the 2-round no-improvement stop.
- **Power.** 10 held-out prompts × 3 repetitions gives wide intervals (the T010
  interval at 16/30 is [0.361, 0.698]); the protocol therefore decides by the
  D4 rule, not by interval separation (OD-1).
- **Alternatives rejected.** TextGrad (more calls per step, no Pareto
  diversity); MIPROv2 (needs few-shot demonstration slots the skill lacks);
  optimizing on the held-out set (contamination).
- **Outcome (T010, 2026-11-13).** On `claude-code` with `claude-sonnet-5-5`,
  GEPA raised the development score from 0.900 to 0.967 and APO did not
  (best 0.233), but on the frozen held-out set neither A2 GEPA (24/30) nor
  A1 APO (23/30) met D4, and neither beat A0 (25/30; paired sign test
  p = 1.0). H1 is not supported. This is a single-host, single-model,
  low-power observation of these prompt sets; it does not show that APO or
  GEPA cannot help elsewhere. On the development set the current guidance
  (A0, 27/30) already scored far above the SPEC-069 T010 guidance (16/30)
  that motivated this specification, so less headroom remained than the
  purpose assumed; this is context, not an explanation of the result.
