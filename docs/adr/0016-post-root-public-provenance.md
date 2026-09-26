# ADR 0016: Post-root public provenance supplement

## Status

Accepted by explicit founder decision on 2026-09-26 for the local provenance
supplement and portable validation boundary. The
[decision record](../releases/publication/adr-0016-founder-decision.json) binds
the reviewed proposal bytes and approval scope. This does not approve a release,
remote history operation, SPEC-014/015 review or scientific claim.

## Context

ADR 0010's public export manifest binds the immutable clean root. Subsequent
public commits added authorities and evidence for M2. Several reviewed Spec Kit
records still name source-branch commits that are absent from a fresh clone of
`develop`, although their published file representations are present. Replacing
the root would also require rewriting `main`, the published tag and other refs.
The existing portable validator incorrectly requires all inherited historical
references to appear in the original root inventory.

## Decision

Keep the root commit and `docs/releases/public-export.json` byte-identical. Add a
canonical, immutable supplement for the finite set of post-root paths needed by
historical records whose reviewed commits are unavailable from `develop`. The
supplement binds each path, SHA-256 and byte length to one exact, reachable public
commit and tree. It also binds the original manifest digest and states its limits.
A later public commit introduces the supplement; its bytes cannot subsequently
change. Additional snapshots require a distinct, reviewed supplement.

Portable validation uses a historical commit directly only when it is an ancestor
of the checked `HEAD`. Otherwise it resolves root paths from the original
manifest and post-root paths from the supplement's snapshot. It verifies Git
ancestry, every listed blob, canonical ordering, uniqueness, prohibited-text
patterns and the unchanged supplement. A locally present but unrelated commit
cannot silently change which validation path runs.

## Limits and consequences

This proves that selected file representations existed in the stated public
commit. It does not reconstruct private source ancestry, authenticate the
founder, reproduce earlier experiments, validate scientific claims or approve a
new feature candidate. Historical evidence input hashes whose original private
bytes are unavailable remain declared limits. Existing branch and tag identities
are preserved; publication of this repair follows normal review and approval.
