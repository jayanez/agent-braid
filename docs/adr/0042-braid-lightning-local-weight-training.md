# ADR 0042: Local weight training for Braid Lightning (deferred)

- **Status:** proposed and deferred; deferral confirmed by the founder on 2026-11-08 ([founder decisions](../development/FOUNDER_DECISIONS_20261108.md), decision 3); reopened only by founder go/no-go
- **Date:** 2026-11-08
- **Deciders:** Juan Antonio Yáñez García (founder)
- **Constitutional articles:** 0, 13, 19, 23
- **Specification:** [SPEC-076](../../specs/076-lightning-local-grpo/spec.md) (milestone Deferred)

## Context

Agent Lightning v1.0 reports SWE-bench Verified 41.8% to 56.4% for a 9B open
model with GRPO, rollout-level advantage and rollout-level loss normalization.
That requires a self-hosted model that returns token IDs, CUDA GPUs, verl and
vLLM. ADR 0039 excludes weight training from BL.0–BL.5.

## Decision (proposed)

If the founder reopens it: weight training runs only on a local open model whose
license permits it, behind a loopback token-ID proxy, through an optional
`lightning-gpu` extra installed in an isolated environment, with a local runner
and no Kubernetes. Trained weights never become a System One backend and confer
no execution authority. Hosted-model outputs are used for training only after a
recorded usage-terms review (SPEC-075).

## Reopen criteria

Founder go/no-go; SPEC-075 delivered; a local CUDA GPU; a base model and license
chosen; this ADR accepted.

## Consequences

Until reopened, no GPU dependency, proxy or training code exists in the repository.
