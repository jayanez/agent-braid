# 2026-10-13 co-author attribution correction

## What happened

Public commits included the co-author identity
`1456524+jayanez@users.noreply.github.com`. GitHub resolves the numeric prefix to an
unrelated account, so those commits were attributed to a third party. On 2026-10-13 at
about 11:49 UTC the founder force-pushed corrected history for 18 branches, including
`develop`. Trees were preserved; commit identities changed. `main`, the public root and
all annotated tags were not rewritten.

## Impact

- Portable validation failed: the M2 closure anchor and the public-export addenda name
  commits that are no longer ancestors of `develop`. CI failed on `develop` and on open
  pull requests. The push-event base commit of the force-push was unavailable to CI.
- Five annotated tags still contained the misattributed identity.
- No tree, record, evidence or approval byte changed.

## Remedy

[ADR 0022](../../adr/0022-attribution-correction-history-equivalence.md) keeps the
corrected history. It corrects the five tags with the same deterministic rules and
introduces a closed, tree-verified equivalence record for frozen identities. The
original tags are removed only after the decision is merged.

## Outside the repository

GitHub-retained pull-request refs and cached commit views may still show the original
identity. Removing them requires a GitHub Support request by the repository owner.

## Limits

This note records an attribution correction. It does not approve any feature, release,
experiment or scientific claim, and it does not constitute independent validation.
