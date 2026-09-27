# M2 internal closure decision draft

**Status:** awaiting a separate founder milestone-closure decision

**Candidate:** `efc4b4c1f9c1eb82088c5bdff0d1ea9b84a26074`

The founder approved the bounded adversarial scientific review on 2026-09-27
for the earlier frozen candidate `a5f7d08`. The develop-lineage candidate above
retains the same implementation and scientific-source bytes; its assurance and
task records changed. It requires an explicit ratification
of that approval against its own clean-room record. The
[founder review](../../specs/017-m2-closure/founder-review.json) keeps both
decisions pending for this candidate.

## Evidence available for the closure decision

- The [internal clean-room record](../../specs/017-m2-closure/reproduction.json)
  contains 17 successful observations from a fresh clone and environment,
  with clean initial and final states and exact input hashes.
- Four M2 exit criteria are supported only within their bounded fixed-patch Git
  and read-only preparation domains. The approved radar review and
  [adversarial scientific review](../../research/reviews/2026-09-27-m2-adversarial-science.md)
  retain the claim limits.
- The accepted SPEC-013 retest covers two registered 30-pair batches. Its
  observed gains concern parallel patch preparation; both schedulers selected
  the same wave in that corpus.
- SPEC-016 remains a private syntactic experiment. Its oracle is regenerated
  and checked using the same replay implementation; uncertain paths block
  interchange.

## Limits retained if M2 closes

`tracked-tree-v1` is weaker than contextual or semantic equivalence. This
evidence establishes neither general confluence nor a Yang-Baxter result,
production performance, live-agent safety or authorization to execute or
promote refs. Independent external validation remains `pending`.

After a separate founder approval, the final record must state the decision
date and rationale, then reconcile the six M2 spec parents, SPEC-017 tasks and
GitHub milestone and Project. No closure status or tracking change is implied
by this draft.
