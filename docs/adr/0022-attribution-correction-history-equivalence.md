# ADR 0022: Attribution-correction history equivalence

- **Status:** proposed
- **Date:** 2026-10-13
- **Deciders:** Juan Antonio Yáñez García (`@jayanez`, founder)
- **Constitutional articles:** 0, 7, 13, 14

## Context

Public commits carried a co-author identity, `1456524+jayanez@users.noreply.github.com`,
whose numeric GitHub identifier belongs to an unrelated account. GitHub therefore
attributed authorship to a third party. On 2026-10-13 the founder rewrote 18 public
branches to replace that identity, and a former work address, with
`7823750+jayanez@users.noreply.github.com`, the founder's own identity. GitHub-generated
signatures were removed because they cannot survive a rewrite.

Every tree is unchanged. Commit identities changed from the first post-preview commit
onwards; the public root and `main` are unchanged. Frozen records still name the
original commits: the M2 closure anchor, the public-export addenda, assurance snapshots
and reviewed tags. As a result, portable validation fails on ancestry. Five annotated
tags were not rewritten and still publish the incorrect identity:
`m45-tooling-candidate-8df6c9f`, `m45-autonomous-candidate-20261011`,
`spec-039-reviewed-e94497b`, `spec-040-reviewed-5888737` and
`spec-042-reviewed-6eedc5f`.

[ADR 0010](0010-clean-publication-provenance.md) records that history rewriting changes
evidence-bound identities. [ADR 0016](0016-post-root-public-provenance.md) preserves
existing branch and tag identities. Neither anticipated a correction that removes an
attribution to a third party.

## Decision

1. Keep the corrected history. Restoring the original history would republish the
   misattribution.
2. Apply the same deterministic correction to the five affected tags. Publish new
   annotated tags under new names and delete the original tags after this decision is
   merged. Tags that do not contain the identity are unchanged.
3. Add one immutable, canonical
   [equivalence record](../releases/publication/history-rewrite-equivalence-20261013.json).
   It lists each frozen identity that validation dereferences, with its published
   equivalent and tree, plus the original and corrected tag identities. Its bytes cannot
   change after introduction. A different correction requires a new record and ADR.
4. Validation resolves a frozen identity through `scripts/history_equivalence.py` only
   when that identity is listed. The equivalent must have the recorded tree and, where
   the record carries one, the anchor or snapshot tree. It must also be an ancestor of
   the checked `HEAD` or of a listed corrected annotated tag. Membership in the record
   alone decides the route; a locally present original object never changes it.
   Unlisted identities and every other check are unchanged.
5. Frozen records, founder reviews, closure anchors and addenda keep their bytes and
   their original identities. Reviewed identities are still compared against the
   original identity; only Git object access uses the equivalent.
6. Original objects are not retained in any public ref.

## Alternatives considered

- **Restore the original history.** Rejected: it republishes the misattribution.
- **Edit the pinned identities in place.** Rejected: closure anchors must equal their
  first recorded entry, addenda must be unchanged since introduction, and reviewed
  bytes are pinned by SHA-256. Editing them would invalidate the approval chain.
- **Retain the original history under a tag.** Rejected: it republishes the
  misattribution.

## Consequences

- Portable validation returns to its pre-correction state without editing frozen
  records or repeating experiments; trees are identical.
- The validator gains one closed, reviewed trust input. The mapping from an original
  identity to its equivalent rests on this decision and the private audit evidence,
  not on public objects. Tree equality and public reachability of each equivalent remain
  machine-checked.
- Old identities that are cited informatively in documentation no longer resolve
  publicly. They remain historical citations.
- GitHub-retained `refs/pull/*` and cached views may still expose the original
  identity until GitHub Support removes them. That request is outside the repository.
- Pending branches must be rebased on the corrected `develop`.

## Validation

- The correction rules reproduce byte for byte all 18 published rewritten branch tips
  from their original tips.
- Corrected tags have the original trees and no occurrence of the misattributed identity.
- Tests cover listed and unlisted identities, tree mismatch, non-ancestor targets,
  altered or non-canonical records, recreated or lightweight tags, and locally present
  unrelated originals.
- Full PR and sensitive profiles pass in a fresh clone without the original objects.

## References

- [Founder decision](../releases/publication/adr-0022-founder-decision.json)
- [Incident note](../releases/publication/2026-10-13-attribution-correction.md)
- [ADR 0010](0010-clean-publication-provenance.md), [ADR 0016](0016-post-root-public-provenance.md)
