# SPEC-025 research decisions

| Decision | Basis | Alternative/limit |
|---|---|---|
| Explicit finite suffix set | Operational semantics contextual safety and integration F2/F4 | Terminal projection cannot establish universal congruence |
| Replay prefixes of one fixture | Exact reachable source binding | Trusting supplied states hides unreachable context |
| <=6 original ops; <=720 suffix schedules; 20,000 checks/120,000 steps | Existing finite model plus visible total caps | Truncation is inconclusive |
| Retain all results/versions/events and enabledness | T1/T2 premises and event chronology gap | Final values alone cannot authorize rewrites |
| Distinct candidate/proof/finite statuses | Claim discipline and Article 17 | Test success is not an accepted theorem |
| Review handwritten proof first | `research/proofs/README.md` admits delimited proofs | Mechanization optional only with concrete value |
| Preserve anchored conventions and scope | ADR 0017/structured exchange | Delete/nested/nondeterminism require a distinct model |
| CoAgent research-only feasibility | AT-2026-005 in adoption triage | No artifact execution or reproduced measurement assumed |

## Premise inventory to implement

T1: deterministic atomic transitions, jointly initially enabled incomparable
instances, complete data/control/predicate reads, disjoint read/write intersections,
version/guard stability, result preservation, declared local-event equivalence and
absence of external effects. Prove enabledness preservation separately. State
whether exact event chronology diverges; never drop it silently.

T2: finite partial order and termination, connected linear extensions, valid
adjacent swaps in every reachable context, preserved dependencies and enabledness,
T1/pair premise at each swap, observational congruence under the remaining suffix.
Initial pair tests and decreasing pending count alone cannot establish the whole
statement. Avoid invoking Newman's lemma without termination and quotient premises.

Anchored class: explicit carrier and valid paths, immutable base/root anchors,
fresh IDs, canonical sibling flattening, residual recomputation, preserved logical
insert intent and final-sequence results, closure/involutivity, far/adjacent path
relations, distinction between abstract statement and bounded executable mapping.
Its raw chronological observations are retained rather than declared equal.

## External and tool feasibility protocols

CoAgent primary reference is the versioned entry in `research/REFERENCES.md`;
T006 must recheck artifact availability, license and exact version before any
proposal. Its existing research-only disposition grants no artifact rights or
execution permission. Compare typed semantics/premises first; mismatches or absent
artifacts are valid results. A future executable comparison needs isolated source/
license review, pinned inputs, resource budget and separately authorized protocol.

T005 compares handwritten review with optional proof-assistant/tool approaches for
one named unsolved obligation. Record soundness/trusted base, model mapping,
maintenance, reproducibility and license cost. Report no-tool/infeasible outcomes;
no automatic download/install or dependency adoption. Adoption requires ADR/founder.

## Evidence status

No new proof, counterexample experiment, external artifact or tool was executed
for this planning delivery. Finite data, candidate statements, independent proof
review and mechanized developments must each have separate provenance/status.
