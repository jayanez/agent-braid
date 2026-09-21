# M0 closure readiness

**Status:** M0 closed by explicit founder decision on 2026-09-18. This document
remains an inventory; see the [closure record](M0_CLOSURE.md) for the decision.

## Completed executable controls

- Foundation, link, JSON, licensing, and constitutional validators.
- Bounded integer semantics, schedule enumeration, certificate verification, and
  negative controls CE1–CE5/S3.
- Shared Spec Kit structural gates for Codex and Claude Code.
- Versioned schemas and finite corpus checks.

## Completed documentary controls

- Clause zero and Articles 1–25 remain the normative authority.
- Operational semantics, claim discipline, AIM, certificate, assurance, and
  governance documents are linked and versioned.
- Research hypotheses, references, counterexamples, and proof boundaries are
  explicit.

## Completed human controls

- The certificate-verifier pilot has an approved founder scientific review.
- Sequential Codex and Claude Code reviews of the same candidate commit are
  recorded and compatible.
- The founder separately approved M0 closure.

The founder's scientific review of the pilot and the M0 closure decision are
separate records. Automated validation did not make either decision.

## Gates assigned to later milestones

- Under the policy later adopted in ADR 0009, clean internal reproduction and
  founder review are required before a research-preview proposal. Independent
  validation is invited and reported, but is not a publication gate.
- Clean reproduction of the analyzer corpus and real Git/worktree benchmarking
  belongs to M1; it must not be described as independent when founder-supervised.
- Privacy and security review becomes blocking before accepting third-party
  traces. M0 uses local synthetic fixtures and accepts no external trace data.

## Claims explicitly not made

- No production-safety or autonomous-execution guarantee.
- No general confluence result for AI-agent systems.
- No general Yang–Baxter result, theorem, or validated universal exchange class.
- No proof that the market proxies represent capturable demand.

## Research-preview decision gate

After M0 closure, a frozen clean internal reproduction and the remaining M0.5
review gates, the repository may be proposed for public **research preview**
visibility. Its independent validation status remains visible under ADR 0009.
Changing repository visibility is an external action and is not authorized by
this inventory, a passing CI run, or an implementation pull request.
