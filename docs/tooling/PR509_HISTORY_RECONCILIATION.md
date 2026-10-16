# PR 509: history reconciliation and evidence boundaries

## Source identities

This integration starts exclusively from the rewritten public PR head
`062fa41f18a77d5e968df9bfb77efc8b3c6813f6` (tree
`fa8e3d72615bd4d258ff6af9325e8ea231bdebb3`) and rewritten develop
`5302d0bd26dd1ccdd245d87ffbb8346994cddb31`. No old branch or private
pre-rewrite commit is imported. The tracking conflict keeps the PR's bounded
M4.5 status (55 checked / 24 pending tasks) and develop's FC.2 entry. All other
merged develop content retains its own scope.

The source branch is updated by a normal fast-forward push of its reconciliation
commit. Final integration into develop must use a linear PR method; a source-branch
merge does not authorize a merge commit on develop or a force push.

## Historical evidence is not new-head approval

Historical macOS/Linux reproduction receipts, failed attempts, scoped SC-004
findings and the A/SPEC-044-T004 bounded closure remain immutable and retain their
original candidate identities and limits. They are not repeated or reopened.

A previously recorded dependency manifest identifies these unchanged source bytes:

| Path | SHA-256 at the historical source and rewritten PR head |
| --- | --- |
| agent_braid/tooling_registration_v6.py | 75772c8faf8c788ffc0fa549ca44c02a537bbb0b7d27c264debdd65c510d6e83 |
| agent_braid/tooling_interface_observer.py | 3004e67b14efd68446f5d5fa5698f7ccbc9077989e4a93633a18ce4f45303713 |
| agent_braid/tooling_receipt_instruments.py | 44921298b9232d71166497de94beb728291e4c5f89da0340178f0910f09c5e17 |

This bounded comparison establishes only those three files' byte identity. It
does not establish complete commit/tree equivalence, the transitive dependency
closure, execution-process identity, source freshness or native admission.
Earlier validation is historical; the integrated candidate needs its own gates.

The separately reviewed local telemetry candidate, its one completed local
CLI/direct-handler pilot and five authorized documentary incorporation files
remain in their existing private evidence and separate checkout. They are not
part of this PR's source tree and are not transplanted from old history here.
That pilot never supplied native discovery/loading/use or acceptance. The
T017/T018 joint private proposal remains unadopted and unadmitted.

## History-provenance gate remains blocking

In a fresh independent clone, restore_public_spec_history.py rejects the
rewritten SPEC-016 reviewed tag because its published object no longer matches
the pinned identity. The fetched tag object is
`e869bb35133ea7edbd648b53f16313b5636f3057`; the restore contract pins
`5d6744217595027df87d56fa307a069941af1263` for that reviewed tag.
Spec Kit preflight independently stops with a history-equivalence tree error
for `61e731aeb1cb631b9c0d083f71d38ca620cc4742`. This is a provenance-gate
failure, not evidence that a scientific result changed or that a test passed.

ADR 0022 permits only its immutable 2026-10-13 equivalence inventory and requires
a new record and ADR for a different correction. The 2026-10-16 rewrite has no
reviewed second equivalence decision consumed by the existing validators. Do not
change frozen assurance/review bytes, replace old hashes with new ones, weaken
tag/tree/ancestry checks, or import old misattributed history to make it green.

The minimum safe prerequisite is an exact second-rewrite provenance inventory,
a dedicated reviewed immutable mapping and founder-approved ADR/disposition,
then only the restore/pin mechanism changes authorized by that decision. Fresh
candidate validation must follow. This PR stays draft/unmerged while the gate
is blocked; a conflict-free source tree is insufficient for acceptance.

## Preserved scope

No host/model/provider launch, new reproduction, registration activation or
additional spend is authorized by this reconciliation. Original task criteria,
108 intended attempts, 36 human-operated CLI baseline journeys, native gates,
deferred human review, A/SPEC-044-T004 and milestone closure remain separate.
No registered slot is consumed. Full-profile completion must not be claimed
when its provenance predecessor refuses.
