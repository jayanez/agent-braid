# ADR 0023: Preserve historical contracts after the second history correction

- **Status:** proposed; founder integration decision pending
- **Date:** 2026-10-16
- **Constitutional articles:** 0, 7, 13, 14

## Context

The owner directed a second public history rewrite on 2026-10-16. The rewritten
`develop` tip is `5302d0bd26dd1ccdd245d87ffbb8346994cddb31`. Existing approved
records still name their original objects. The immutable ADR 0022 mapping points
to intermediate identities and retained annotated tags now have new objects.
Restoration and publication checks correctly refuse those mismatches, including
on the base branch before the FC.1 change in PR #532.

## Proposed decision

Preserve ADR 0022, its mapping, founder reviews, assurance snapshots, closure
anchors and addenda byte for byte. Add a separate immutable canonical
[2026-10-16 correction record](../releases/publication/history-rewrite-equivalence-20261016.json).
Compose the original closed mapping with this second closed mapping only when
their recorded trees agree. Never infer a route from a locally present old object,
an arbitrary tag, an approximate file match or a runtime search of equal trees.

The proposed record binds 29 intermediate/public identities and ten retained
annotated tags. Candidate generation inspected the rewritten public refs and
compared exact trees to the previous fixed pins. Named retained tags determine
their candidate identities; otherwise a unique matching `develop` ancestor
determines the identity. One mapped candidate is an ancestor of an exact retained
tooling tag. The resulting finite table, not the discovery heuristic, is the
validator trust input and is subject to this PR's review and founder integration.

Two intermediate legacy targets (`d8e6c673788c4453ab4f52e7123e1009ae468dee`
and `e0ee9009e6609ed3603152f2be7af5d408c9f3fa`) have no exact published tree
match in the inspected refs. They are not guessed or substituted: their legacy
routes remain unchanged and fail closed if requested. This does not claim to
restore every historical citation or admit previously unavailable evidence.

Tag names retain their historical spelling. Only a listed old tag object and
peeled candidate can map to the exact new annotated object and candidate, with
the same tree. Recreated/lightweight/wrong-object tags remain invalid. Approved
review/assurance bytes retain their original SHA-256 commitments; pending drafts
remain pending. A new identity never supplies a missing human review.

Both mapping files must remain canonical and unchanged since their respective
introductions. Reject duplicate/ambiguous keys, cycles, mismatched trees,
contradictory tag bindings, absent records after introduction, and targets outside
the current canonical HEAD or exact retained-tag ancestry. Ignore replace refs
and grafts as before. Unlisted identities retain their previous route.

## Alternatives

- Editing the first mapping or original approval records: rejected; destroys
  provenance and changes the approved bytes.
- Republishing old branches/tags or force-pushing: rejected; reintroduces the old
  history and violates the owner's synchronization instruction.
- Accepting any same-tree/local tag or skipping restoration checks: rejected;
  would weaken the closed identity and public-ancestry contracts.

## Validation and integration boundary

Focused tests must exercise both mapping layers, record immutability/removal,
tree mismatch, tag forgery, ancestor refusal, pending-draft preservation and
unchanged original approval files. Review precedes pushing this separate PR and
therefore precedes new CI. CI success is technical validation, not adoption of
this proposal or of FC.1/FC.2's real gates. No model, VM, new package, experiment,
new original approval, tag publication or history rewrite is authorized here.

The branch starts at the rewritten public base, contains only new owner-attributed
commits, and must integrate through the normal linear PR flow. After integration,
consumer PRs need a forward update and current checks; no old-history push or
automatic merge of #532 is implied.
