# Proposal: extend SPEC-019 source-family review

**Status: proposed; not adopted.** This document is a review aid under
`specs/019-native-predictor/`. It is not a canonical ADR, approval record, or
change to accepted ADR 0018.

## Proposal

Retain the existing Kinetiq evidence-pipeline and SmartNotes non-clinical
architecture/Spec Kit candidates for source-specific review under the exact
boundaries already described by ADR 0018. Ask reviewers to assess three
additional, distinct natural Agent Braid engineering workflows listed in
[`source-candidates.json`](source-candidates.json): public interface design,
validation-method decisions for existing changes, and release-evidence review
for existing changes. The three candidates must be rejected, merged, or
retained based on documented evidence that their workflows occur naturally
and are distinct; their presence in this proposal does not establish any of
those facts.

No issue, task, code change, test, release review, or participant activity may
be created solely to produce study observations. No workflow may be split or
renamed just to meet the five-family threshold. Preserve zero observed real
pairs until a source-specific prospective window is actually reviewed and
completed.

## Decisions this proposal does not make

The founder's accepted decision covers bounded preparation for Kinetiq and
SmartNotes only. It does not approve capture in either repository and does not
authorize Agent Braid as a source. Any retained Agent Braid family or any
broader source expansion requires a new explicit founder decision covering
its owner, participant/data rights, privacy, capture permission, exact
content/file allowlist, credentials and services. No deploy key, application,
lab, or registration should be created under this proposal.

Every family still needs its own reviewed permission record, a completeness
control, immutable base and independent proposal receipts, a fixed 14-day UTC
window, successful remote registration at least 24 hours before that window,
and review of the complete session/pair and exclusion ledger. Local journal
custody and backup/deletion handling must follow an approved privacy decision;
the proposed maximum is 90 days after documented review. Remote artifacts
remain metadata-only.

The complete workload protocol and annotation rubric remain pending review.
Two blinded reviewers and a third adjudicator are proposed; disagreement and
unknown outcomes must remain visible. The proposed five-family, family-split,
100-known-label, and holdout 20/20 thresholds remain candidates, not a quota
or proven power calculation. A failure to obtain valid natural data is an
inconclusive feasibility result; it cannot be repaired by manufacturing
decisions, extending a window, or changing population after labels.

## Review route if advanced

Review the candidate inventory and packet with the source owners, participants
and privacy/scientific reviewers. If they recommend expanding the source set,
prepare a separately scoped ADR and permission decision through the repository
governance path. Until that decision is explicitly accepted, this proposal
remains non-operative and the only previously accepted preparation scope is
the bounded Kinetiq/SmartNotes work recorded in ADR 0018.
