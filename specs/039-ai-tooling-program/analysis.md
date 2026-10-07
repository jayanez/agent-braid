# Spec Kit cross-artifact analysis

**Date:** 2026-10-08. **Scope:** SPEC-039–044 source packet.
This is author analysis, not an independent reviewer result or human approval.
Final structural validation receipts belong in delivery-status.md.

## Coverage

Six specs each contain eight stable requirements and scenarios, ten task IDs,
named prospective procedures, scope/authorities/compatibility/hypotheses and empty
obtained evidence. The program sequences consumed contracts; issue drafts preserve
source task IDs, dependencies, targets and evidence. Future targets are identified
as future, not executable existing commands.

## Findings addressed during drafting

| ID | Severity | Location | Finding and resolution | Authority |
|---|---|---|---|---|
| A001 | Major | SPEC-040 contracts/interface.md tool table | Initial shorthand used run IDs for legacy status/recover/verify; corrected to existing plan/grantId/action inputs. Resource run IDs remain separate | Existing RuntimeTools/catalog, ADR 0020 |
| A002 | Major | SPEC-040 data-model.md AnalyzeWorkRequest | A shared Git common directory alone could admit sibling worktrees beyond selected roots; added explicit canonical worktree allowlist and default root-only scope | Articles 5/12/15; configured-root contract |
| A003 | Minor | SPEC_MILESTONE_INDEX.md | New rows must remain in the table and counts distinguish registered from proposed milestones; corrected | GITHUB_TRACKING.md |
| A004 | Minor | Six tasks.md files | Replaced undifferentiated feature-wide targets with bounded target slices for T001–T008 | Spec Kit task/evidence traceability |

| A005 | Minor | issue-drafts.md and six validation-plan.md files | Complete source-diff check exposed trailing blank lines at EOF; normalized endings and checked against develop | Validation whitespace gate |

## Pending boundary findings

| ID | Severity | Location | Open boundary and required action |
|---|---|---|---|
| G001 | Gate | ADR 0021; six plan.md review sections | Architecture/API adoption and consumed-contract review are pending before governed implementation acceptance |
| G002 | Gate | SPEC-044 evaluation-protocol.md | Exact host/model builds, source rights, numeric paid/provider/resource caps and frozen registration precede actual capture |
| G003 | Gate | SPEC-044 acceptance decision | No actual host, clean-room, human scoring or independent review receipt exists in this source packet |
| G004 | Gate | program.md delivery section | Remote milestone/issues require reviewed source integration and scoped digest; private Project status is a separate check |

Gates remain visible. No MUST contradiction is intentionally proposed; a newly
found authority conflict blocks that slice and requires explicit resolution.
An empirical hypothesis is not rewritten into a required favorable result.

## Convergence assessment

Source preparation covers the selected planning outcome. Product implementation,
all 60 tasks, actual host observations and milestone closure are pending. Empty
evidence and pending human review are deliberate truthful states. Structural
passes cannot change these states.

## Integration provenance

The frozen source candidate must remain in public ancestry. Use a merge commit
for this source PR (repository permits it); squash/rebase would discard the
frozen commit ancestry while these draft records remain review-pending. Do not
repair immutable export manifests to hide that provenance problem.
