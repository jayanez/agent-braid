# Anchored sequence exchange, version 1

**Claim level:** executable finite model and a candidate mathematical class.
ADR 0017 remains proposed. This document defines a restricted operational
semantics; its general mathematical statement has not received proof review.

Let the base be a sequence `B=(b1,...,bm)` of distinct IDs, with root `$root`
before `b1`. Let an operation be `I=(opId, anchorId, newId, value)`, where the
anchor is the root or an ID in the immutable base and `newId` is globally fresh.
All inserted IDs are pairwise distinct. Values are bounded strings. An
admissible state maps each base/root anchor to a set of inserted `(ID,value)`
pairs. Flatten by writing the root's inserted elements in ascending ID order,
then each base element followed by its inserted siblings in ascending ID order.
Applying `I` adds its pair to its anchor's set and records its index in the
new flattened sequence as the context-dependent residual `rho_S(I)`.

For a prefix state `S`, the adjacent exchange `s_i` replaces the two scheduled
logical inserts at positions `i,i+1` by the opposite order and recomputes both
residuals from `S`. It is defined only for validated inserts in this finite
domain. Composition is left to right. The pair comparison checks the final
flattened ordered ID/value sequence, not equality of chronological traces.
For three inserts the executable paths are `s0;s1;s0` and `s1;s0;s1`.
Both should end with reversed logical order and equal final observation.

The candidate argument is elementary: each insert adds a distinct member to
one anchor set; set union is order independent, and deterministic flattening
then has the same result. This argument concerns this model only and is
presented for review, not as an accepted formal theorem. It says nothing about
deletes, nested anchors, failed preconditions, hidden effects, Git patches,
transactional serializability, concurrent interleaving or quantum YB.

Evidence records contain each intermediate schedule, physical residual index,
before/after hashes and terminal sequence. The verifier regenerates all these
fields using the same implementation and rejects missing or altered material.
`verified-bounded` means only that the regenerated finite paths agree under the
declared observation. `inconclusive` includes malformed, incomplete or
unsupported inputs. Raw trace order is intentionally retained as a difference.

The exhaustive protocol fixes ID names and values, then enumerates base sizes
0–3, operation counts 2–4, every assignment of base/root anchors and all
permutations of each operation set. It does not quantify over arbitrary values,
ID alphabets, external workloads or unbounded lengths. Same-anchor pairs are
the overlapping positive controls; unsupported deletes, unknown/nested anchors,
duplicate IDs and tampered evidence are negative controls. A zero false-certificate
count is an empirical statement confined to that finite corpus.
