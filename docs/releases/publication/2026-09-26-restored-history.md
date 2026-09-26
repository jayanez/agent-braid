# Restored public history and M2 review boundary

The founder-approved internal SPEC-014/015 review was bound to the clean-export
candidate `6bba071dc887f298deeb45affaf8180993e2da8a`. That candidate used
new root `5a89ed5090d4275c793521ff58102a6f7289baa9`. After the remote
cutover exposed two public Git roots across retained refs, the founder selected
restoration of `develop` to `47917a906aa6af851899c8d1ff1c9d67bd1b035b`.
The previous review records are retained verbatim in each feature directory as
`prior-cutover-founder-review.json`.

Those archived reviews also name
`docs/releases/publication/reproduction.json` at SHA-256
`a4284ac86d1519705b2a51d6c26655c40bacb18e61d20ce3f48dfa97c2f4bb23`.
The exact reviewed bytes are retained as
`docs/releases/publication/reproduction-6bba071-archived.json`. The current
file at the original path is an earlier public reproduction with different
bytes; the archive mapping does not treat it as the reviewed artifact.

The earlier approval applies to its exact reviewed commit and evidence. The
restored-history feature records may reuse the unchanged test evidence captured
on `47917a9` when input digests still match, but their current `human_review`
remains `pending` until a new exact candidate is reviewed. Publication integrity,
internal feature review and independent external validation are separate.
External validation remains pending and M2 remains open.

The new internal clean-room reproduction for the repaired-history candidate
`613b529b7eab20f42d6e9d7eb0480ef1748a80d2` is stored separately as
`docs/releases/publication/reproduction-613b529.json` (SHA-256
`a3333be99e003a3330586ce97e35770df64097809efe5672b5b3be106e4c4d73`).
Its twelve recorded commands passed in a fresh clone and Python environment.
This run has not received a new founder result review.
