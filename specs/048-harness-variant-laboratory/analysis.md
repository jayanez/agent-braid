# Cross-artifact planning analysis

Status: primary-session assessment of the planning artifacts, followed by the
recorded editorial corrections. No independent Luna or human review is claimed.
Implementation, native qualification and architectural adoption remain pending.

## Coverage and source consistency

Each of SPEC-048 and SPEC-049 has eight unique requirements and eight unique
Given/When/Then scenarios. Every identifier appears in its spec, assurance record,
prospective validation and at least one task. Each feature has ten unchecked
implementation/gate tasks and no obtained feature acceptance evidence. Source
tracking emits exactly two parents and twenty open tasks for this scope.

## Findings and disposition

| ID | Severity | Location | Basis and disposition |
|---|---|---|---|
| ANA-001 | Blocking for native execution | 048/contracts/interface.md, 048/T001/T008 | The accepted runtime excludes arbitrary code. The plan introduces a separate proposed laboratory contract and qualified containment; native dispatch remains refused until its review/admission gates. This is an explicit pending implementation boundary, not a waived conflict. |
| ANA-002 | Editorial, corrected | Both spec.md procedure links | Repository validation found underscore/hyphen anchor mismatch. Links now target the actual procedure headings; no validator was changed. |
| ANA-003 | Structural, corrected | Both assurance.json scenario planned_evidence fields | The checker requires nonempty strings. Draft entries now match the owning format; obtained evidence stays empty. |
| ANA-004 | Review gate | 049/evaluation-protocol.md; 049/T002 | Source yield, numerical operating caps, evaluation size/margins and full-label coverage must be frozen before dependent native outcomes. They are ordered tasks rather than fabricated measurements. |
| ANA-005 | Review gate | 049/promotion-policy.md; 049/T008 | Automatic promotion is assessed offline and disabled. Initial promotion remains human; any automatic activation requires separate adoption and applicable evidence. Synthetic qualification cannot establish native utility. |

## Dependency and feasibility review

048/T009 and 049/T003 allow deterministic engineering without native T008/T004.
049/T005 has a minimum no-library comparison and an optional later library
ablation depending on T006; T006 does not depend on T005. Native comparison adds
T004 rather than relabeling the deterministic cohort. 049/T008 does not require a
positive T007 promotion. These branches are acyclic. A valid negative/infeasible
assessment does not complete any blocked native implementation task or adopt a
capability. Full milestone closure retains explicit owner disposition of open
branches.

## Authority and evidence

The ADR proposal stays feature-local. Canonical authorities and existing assurance
records were preserved. New records use current authority snapshots and
draft/pending review. Upstream tests and source probes support the research audit
only. Passing planning validators cannot supply containment qualification, native
host behavior, economic utility, founder adoption or independent review.

## Remaining gates

Independent Luna review when separately authorized; exact human/founder decisions;
frozen-candidate implementation/reproduction; eligible native sources and trusted
route/containment observations; both-axis utility and complete costs. These remain
tasks, not fulfilled claims in the planning packet.
