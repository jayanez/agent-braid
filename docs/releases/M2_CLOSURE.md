# M2 internal closure decision draft

**Status:** awaiting a separate founder milestone-closure decision

**Candidate:** `61e731aeb1cb631b9c0d083f71d38ca620cc4742`

The founder approved the bounded adversarial scientific review for `a5f7d08`
and ratified it with an internal M2 closure decision for `efc4b4c`. A tracking
test correction required another develop-lineage candidate. The new clean-room
record retains all 53 input hashes and the same scientific limits, but this
exact SHA still requires explicit ratification of both decisions. The
[founder review](../../specs/017-m2-closure/founder-review.json) keeps them
pending for this candidate.

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
