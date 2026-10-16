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
Resolve only these explicitly listed cases, with strict canonical parsing of
recordVersion 0.1.0 and the exact adr/entries/tags/reason/limits fields:

1. If an identity is listed in ADR 0022, resolve its first-layer target and then
   the exact second-layer entry for that intermediate identity. Require the first
   and second recorded trees to agree. An absent required second-layer target
   retains the existing fail-closed gate; do not silently call it migrated.
2. For a legacy identity not listed as an ADR 0022 source, allow direct second-map
   lookup ONLY if it is explicitly listed there. This includes the seven frozen
   restore/review candidates 0974739ae4dc6784ff3c21a34745655a38dd4943,
   2656924e51cccf4017a31563ae044c47efcc395d,
   853df7432dd4700aa411f1f13b324a0b7beecd02,
   bb2e0322fdf0fe3eabc6e28fec4864c9cfc954df and
   c30e8bcfb572afba4447767fc2b51dd2c3320766,
   5b6ecff16f2328c1b514517d8332ce2179d5bd1d and
   7f679797784b5fc85503075e5c477c9b2d7b14e4. Their exact new objects/trees,
   and retained annotated tag bindings where applicable, are closed trust inputs
   in this record; they are not inferred from a tag name at validation time.
3. Identities unlisted in both records retain their previous route and checks;
   this adds no general fallback. Conflicting source keys, cycles, inconsistent
   trees, ambiguous composition and out-of-domain destinations are rejected.

Never infer a route from a locally present old object, an arbitrary tag, an
approximate file match or a runtime search of equal trees. Tree/object/ancestry
and exact approval-byte verification remain required after lookup.

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
