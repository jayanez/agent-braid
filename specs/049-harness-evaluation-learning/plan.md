# Implementation plan — SPEC-049

## Technical context and scope

Determine separately whether harness refinement improves long-task continuity and agent coordination, then retain only scoped evidence-supported lessons and make explicit human or future automatic promotion decisions.

Adapt selected upstream code and scaffolding according to [the reuse map](../048-harness-variant-laboratory/upstream-adaptation.md), preserving provenance and applicable notices. Use standard-library Python for portable contracts and deterministic controls. Reuse existing analyzer/trace/session/evidence seams where contracts match; do not wrap the fixed-patch runtime around arbitrary host commands. Proposed modules in tasks.md are ownership boundaries to verify for collisions before implementation, not existing APIs. Core runtime dependencies stay unchanged.

## Constitution check before research

Constitution clause zero and Articles 1, 2, 3, 5, 6, 7, 9, 12, 13, 14, 15, 19, 20, 21, 23, 24, 25; GOVERNANCE.md; operational semantics; claim discipline; accepted ADRs 0019/0020 and applicable proposed ADRs 0021/0024/0025. The feature-local ADR proposal changes no canonical authority.

Articles 5–7/12 require effects, preserved semantics and inspectable decision boundaries; Articles 9/13/14/19 require counterexamples, honest observation scope and measurable utility. Articles 20/24 preserve analysis independence and semantics before runtime adoption. No MUST exception or amendment is proposed.

## Research, assumptions and alternatives

See [source audit](../../research/harness2-source-audit.md), [agreed idea](../../docs/ideas/harness-improvement.md) and [program](../048-harness-variant-laboratory/program.md). Considered: advisory-only changes; task-level contrastive probes; scoped lessons; checkpoint recovery; interaction-aware coordination; unrestricted recursive rewriting. Select small probes with separately evaluated reusable lessons. Existing System 1/FC.1/M4.5 work supplies applicable seams, never inherited acceptance.

## Design and compatibility

The flow is immutable source/base manifest → protected candidate import → independent admission/containment → bounded proposal/probe/composition → independent verification and base retention → journal/evidence → quarantined experience → exact human promotion. Interface proposal: [contracts/interface.md](contracts/interface.md). The three milestones share one [ADR proposal](../048-harness-variant-laboratory/adr-proposal.md); keeping it feature-local avoids silently invalidating existing current authority snapshots.

Planning choices: automatic isolated trials, human initial promotion, two co-primary outcomes, deterministic scenarios allowed, optional future automatic promotion explicitly evaluated but disabled. Proposed first algorithm budget is one round; its numerical execution/resource limits must be frozen at T001/T002 as applicable before implementation/native admission. Model-backed subscription use has a separate fresh zero-spend feasibility gate.

## Validation strategy

Every requirement maps to a Given/When/Then scenario, prospective procedure, task and empty obtained-evidence list. Execute relevant future unit modules with adversarial controls and real fixture process interruptions, then required quick/pr profiles. Source/yield, frozen task-family splits/rubrics/margins and native admission precede native evaluation. Keep full cost and failure denominators. See validation-plan.md and SPEC-049 evaluation-protocol.md.

## Constitution check after design

The proposed laboratory is separate from existing runtime execution; source promotion and permission issuance remain external. Protected layers cannot be mutated by the improver. Evidence classes and temporal scopes remain explicit. No known constitutional conflict was introduced by this proposal; executable effects still require architecture/security review and a qualified implementation.

## Human review and unresolved decisions

Human review remains pending. Keep negative utility and infeasibility as valid outcomes. Candidate freeze, independent Luna review when authorized, founder architectural adoption and per-capability activation are separate gates. No calendar dates or effort estimates are invented.

## Expanded capability coverage

The [coverage matrix](../048-harness-variant-laboratory/capability-coverage.md) supersedes the original compact twenty-task count. HAR.1 has fifteen tasks, HAR.2 thirteen and HAR.3 twelve. Context, observations, individual host adapters, CLI codecs, independent verifiers, complete costs and reversible promotion now have explicit implementation ownership. Advanced component/search/product capabilities belong to SPEC-050. The product and lifecycle name is Braid Harness; upstream Harness² identifies provenance only.
