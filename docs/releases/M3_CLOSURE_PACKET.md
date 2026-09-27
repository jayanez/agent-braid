# M3 internal closure decision packet

**Prepared:** 2026-09-27  
**Status:** evidence assembled for review; M3 closure is not approved.  
**Merged starting revision:** `d567958dbe5d93583456ec33c3a0da4e8e29874c` (`develop`).  
**Reviewed experiment candidate:** `2656924e51cccf4017a31563ae044c47efcc395d` (`spec-018-reviewed-2656924`).

The founder approved [ADR 0017](../adr/0017-bounded-structured-exchange.md)
and [SPEC-018](../../specs/018-structured-exchange/spec.md) as a bounded M3
experiment in [the recorded review](../../specs/018-structured-exchange/founder-review.json).
That decision did not close M3 or authorize execution. This packet presents the
remaining milestone question against the exact merged candidate. M3.5 is a
separate track.

## Exit criteria and claim limits

| M3 criterion from [ROADMAP.md](../../ROADMAP.md) | Available evidence | Limit |
| --- | --- | --- |
| A precisely defined nontrivial exchange class | `anchored-sequence-v1` fixes immutable base/root anchors, fresh IDs and canonical sibling order. Same-anchor inserts overlap: residual physical indices depend on the prefix, yet terminal ID/value sequences agree. | Pure inserts only. Deletes, nested or unknown anchors, arbitrary Git patches and effects are excluded. |
| Reproducible convention-explicit braid tests | The [model](../theory/STRUCTURED_EXCHANGE.md) defines the adjacent crossings; the [finite corpus](../../specs/018-structured-exchange/finite-corpus.json) covers 484 anchor topologies, including 100 triple cases. A separately written rank-key oracle checks 19,806 replay orders with zero mismatches. | Both implementations have the same author and machine. The producer and verifier share their replay engine; the oracle checks that engine but does not supply independent scientific validation or a universal braid proof. |
| Empirical, finite and proved claims distinguished | The [specification](../../specs/018-structured-exchange/spec.md), [counterexample catalog](../../specs/018-structured-exchange/counterexample-catalog.md) and founder review explicitly bound observation to the final ordered sequence and retain chronological traces. | The candidate mathematical argument has not had independent formal review. No general OT, contextual equivalence, Yang–Baxter, arbitrary edit confluence or safe parallel execution claim follows. |
| Runtime consequences quantified | The finite report records 1,776 serial replay steps and 35,904 all-order replay steps; one local run took 3.971942 seconds and reached 93,807 tracked bytes on Python 3.13.11. | These are workload counts and one local measurement, not a speedup or production capacity result. There is no execution runtime. |

The temporary Git serialization [witness](../../specs/018-structured-exchange/git-witness.json)
has equal tree IDs for the two same-anchor terminal sequences. It is not an
M2 fixed-patch certificate. Every bounded result retains
`executionAuthorization: false`.

## Reproduction on merged `develop`

A fresh full clone at the merged starting revision was clean before and after
the read-only commands below. An isolated Python 3.13.11 environment used the
repository's `requirements-dev.txt`. `python3 scripts/validate_spec_kit.py`
passed before this reproduction. Exact commands and local outputs:

| Command from repository root | Result | SHA-256 of stdout artifact |
| --- | --- | --- |
| `python -m scripts.crosscheck_m3_oracle` | 484 fixed topologies, 1,000 seeded cases, 19,806 orders, zero mismatches; byte-identical to the reviewed oracle artifact. | `d6b1f5f80bdc55ea5430692f3587b3d87f6a36e3fbb968ce5c350835c07e2b10` |
| `python -m scripts.run_m3_experiment` | 484 cases, 10 overlapping pair cases, zero false certificates. | `aa7c81e492fcc34837dbb02b8a256795fc790895fbe9927d4d86e96387943ce0` |
| `python -m scripts.run_m3_git_witness specs/018-structured-exchange/fixtures/same-anchor.json` | Both temporary Git trees equal. | `32424947a0ff2f9b688e8c737d9175138fa04f24e40d3bcf4fcdd91bd2a2759d` |

The experiment artifact includes elapsed time and peak memory and therefore
does not have to match the earlier run byte for byte. Its input hashes and
structural counts do match the reviewed domain. The oracle and Git witness
artifacts match their reviewed files byte for byte. This reproduction is
internal and on one machine; external independent validation remains pending.

## Decision boundary

The founder may approve, request changes to, or reject **internal M3 closure**
for the bounded `anchored-sequence-v1` deliverable and the claim limits above.
The decision must name the merged revision and this packet. Approval would not
authorize execution, production performance claims, broader mathematical
claims, M3.5 training, or M3.5 closure. Update the M3 tracking source and
GitHub milestone only after an explicit closure decision and a fresh tracking
audit; Project custom status remains a separate UI check.
