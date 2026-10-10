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
| A006 | Minor | README.md; architecture, contributor, strategy, portfolio and adoption navigation | M4.5 had no public entry guide; README/portfolio still counted 38 specs. Added a guide and links, updated inventory to 44 specs, and identified six draft packages and proposed registration separately from current runtime support | Articles 13/14/20; public evidence boundaries |
| R001 | P1 | Integration provenance; six assurance records | Luna Latest found that mandatory merge-commit ancestry conflicts with develop's required linear history. Use current draft snapshots for source integration; freeze the integrated develop candidate before later human acceptance | Spec Kit current/historical modes; branch protection |
| R002 | P2 | SPEC-040 resource contract and validation | Defined digest-bound chunk URIs, byte ranges, response metadata, sequential retrieval and reconstruction/refusal controls | Full-result parity; bounded owned resources |
| R003 | P2 | SPEC-044 interpretation procedure | Added explicit missing-required-cost controls that suppress positive utility claims despite otherwise passing completion thresholds | Prospective evaluation protocol; evidence limits |
| R004 | P2 | SPEC-044 tasks T005–T010 and validation procedures | Corrected the evaluation dependency chain: 108-arm comparison consumes the registered stable 040–043 candidate; cost instrumentation precedes actual attempts while complete accounting follows them; human scoring follows complete denominators/cost availability; validation precedes the review packet; packet readiness is distinct from the later founder decision and closure record | SPEC-039 portfolio dependencies; SPEC-044 evaluation protocol and evidence boundaries |

## Pending boundary findings

| ID | Severity | Location | Open boundary and required action |
|---|---|---|---|
| G001 | Gate | ADR 0021; six plan.md review sections | Architecture/API adoption and consumed-contract review are pending before governed implementation acceptance |
| G002 | Gate | SPEC-044 evaluation-protocol.md | Exact host/model builds, source rights, numeric paid/provider/resource caps and frozen registration precede actual capture |
| G003 | Gate | SPEC-044 acceptance decision | No actual host, clean-room or human scoring receipt exists; the decision packet and independent review remain future gates, and packet preparation does not constitute the founder's decision; source review does not satisfy product acceptance |
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

Develop requires linear history. Integrate this source PR using an allowed squash
or rebase method after exact-candidate validation and review. The six unapproved
draft records use current authority/evidence snapshots with null commit identities,
complete authority hashes and empty obtained evidence. Their CI gate checks the
actual candidate tree; no feature-branch SHA must survive the integration.

After source integration, freeze a clean develop candidate before a later human
acceptance review. Package its historical snapshots and any actual review record
through the normal reviewed source path; the frozen candidate is then already an
ancestor of develop. A changed authority or evidence candidate needs fresh review.
Technical source review does not approve feature assurance or adopt ADR 0021.
Do not change branch protections or immutable export manifests for this workflow.
