# Data model and contracts

Request: model=anchored-sequence-v1, base list of {id,value}, operations list
of {id,kind:insert,anchorId,newId,value}. Base length is 0–3; operations 2–4.
Anchors name $root or a base ID; new and operation IDs are unique. Values are
strings up to 256 characters. CLI evidence accepts 2–3 operations; four are
used in the private exhaustive corpus. Unsupported requests fail closed.

Replay steps contain operation ID, anchor, inserted ID, physical index after
insertion and before/after sequence hashes. Pair evidence contains forward and
exchanged replay. Braid evidence contains each schedule on both crossing paths.
SHA-256 uses canonical compact sorted-key JSON. Verification compares complete
regenerated records, not only a reported hash.

Advisor proposes a swap for repeated anchors and keeps order for distinct
anchors in the pair case. Three-operation braid evidence receives review rather
than an ambiguous swap proposal. This is conservative policy; distinct-anchor
final observations may still agree. Invalid input goes to manual review. No
record authorizes execution.

## Versioning and migration

This is an additive experimental 0.3.0 contract. Existing 0.1.0-alpha Git
replay, advisory plan, AIM and certificate records have no migration step and
are not accepted as structured-exchange evidence. Consumers opt in by naming
anchored-sequence-v1 and structured-exchange-evidence-v1 explicitly. Unknown
versions fail closed. A future contract change requires a new version and an
explicit migration decision.
