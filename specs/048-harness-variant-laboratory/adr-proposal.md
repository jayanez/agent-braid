# ADR proposal: Braid Harness — Bounded native harness improvement

- **Status:** proposed; owner confirmed planning scope on 2026-10-20, not architectural adoption
- **Date:** 2026-10-20
- **Decider:** Juan Antonio Yáñez García, for any future adoption
- **Constitutional articles:** 0, 1–3, 5–7, 9, 12–15, 19–21, 23–25
- **Intended canonical identity:** next available ADR sequence at adoption
  (0026 was available during drafting; no canonical number is reserved here)

## Context

The owner wants both long-task continuity and precise, efficient coordination to
become central capabilities. Harness² provides contrastive harness refinement
and experience reuse; its default execution/selection assumptions do not match
Agent Braid's currently admitted fixed-patch runtime. Existing grants exclude
arbitrary host execution. Provider subscriptions and local worktrees alone do
not establish isolation, complete costs or native qualification.

## Decision

Adapt selected Harness² software and architectural seams rather than requiring
independent reimplementation of every mechanism. Bind each adapted portion to
the inspected upstream revision and file-specific license, preserve required
notices, and document modifications under Agent Braid's third-party policy.
Use the [adaptation map](upstream-adaptation.md) to make those choices reviewable.
Reference prose remains original English; upstream logos and infographics are
excluded from deliverables.

Propose an opt-in laboratory with immutable authorities, tools, verifier,
permissions and admission policy. The initial editable surface contains bounded
task-local guidance and context-packaging choices. It cannot introduce executable
scripts, hooks, plugins or global host configuration. A separate adopted
execution contract and independently enforced operator envelope must govern any
native probing; existing runtime grants never acquire broader semantics.

Use bounded general/task-specific proposals, observed probes and composition.
Preserve the static base and explicit inconclusive/refused outcomes. Record
complete candidate/source/context/host/policy identity and durable attempted
state. Store proposed lessons in quarantine with applicability, evidence and
revocation. Both continuity and coordination are measured independently, with
correctness/authority constraints before optimization and all chain costs.

Automatic isolated trials and initial exact-candidate human promotion are the
selected planning direction. Synthetic scenarios qualify their stated controls;
native utility needs permissioned native observations. An optional offline
automatic-promotion policy can be evaluated, but activation needs a separately
adopted low-risk domain, independent checks, canary/rollback, incident stops and
fresh operator authority. Extra cash spend remains EUR 0.

## Alternatives considered

1. Advisory-only analysis: cheapest and remains useful when native gates fail;
   insufficient alone to observe effects of a changed harness on a task.
2. Integrate Harness² wholesale: brings useful mechanisms but unnecessary
   benchmark dependencies, execution assumptions and license domains.
3. Extend the existing fixed-patch runtime to launch hosts: would silently change
   an accepted operation language and is rejected by this proposal.
4. Unrestricted self-modification and automatic promotion: broadens authority
   faster than evidence supports; retain only the future bounded assessment.
5. Train a model or add a hosted memory service first: not necessary for the
   initial hypothesis and conflicts with the minimal zero-new-spend direction.

## Consequences

The analyzer remains independently useful. A laboratory can be refused or remain
deterministic-only while host containment/source/route gates are unresolved.
Extra probes and human review may make the approach uneconomic; negative results
must be reported. Source data, credentials and untrusted evidence need enforced
containment and injection-aware consumer boundaries. Hashes bind bytes, not
reviewer identity or permission. Existing public contracts and evidence remain
unchanged; new public surfaces need conservative versioning/migration review.

This proposal stays outside docs/adr until adoption so it does not quietly alter
the authority inventory for other current assurance records. Adoption must name
the exact candidate, review canonical authority drift and update affected current
records through fresh review. No amendment is currently proposed.

## Validation

SPEC-048/049/050 map 28 scenarios to prospective procedures and ordered tasks. Test
protected mutations, symlinks, stale identities, containment failures, leakage,
retries/duplicate effects, incomplete costs, unsafe parallelization and baseline
regressions. Use actual fixture-process interruptions and separately qualified
native hosts. Freeze evaluation source/splits/rubrics/budgets before outcomes.
Per-axis no-go, mixed, infeasible and inconclusive findings are valid. Candidate
validation, independent Luna review when authorized, human approval and activation
are separate records.

## References

- [Constitution](../../CONSTITUTION.md)
- [ADRs 0019](../../docs/adr/0019-bounded-local-git-runtime.md) and
  [0020](../../docs/adr/0020-bounded-m4-alpha-runtime.md)
- [Pinned Harness² audit](../../research/harness2-source-audit.md)
- [Harness² paper](https://arxiv.org/html/2610.14224v1)
- [Program](program.md), [evaluation protocol](../049-harness-evaluation-learning/evaluation-protocol.md)

## Full capability program and name

The Agent Braid product/lifecycle name is **Braid Harness**. Harness² remains an attributed source reference. HAR.1 starts with task-local guidance/context; HAR.2 owns measurement, scoped experience and reversible human promotion; HAR.3 owns advanced component profiles and the operational lifecycle. A future profile may include skills, qualified helpers, hooks or delegated roles only after its separate effect/adoption review. The initial immutable-surface rule is not silently widened. Automatic-policy software can be implemented disabled, with native activation governed by its own exact adopted policy. See [coverage](capability-coverage.md) and [SPEC-050](../050-braid-harness-adaptation/spec.md).
