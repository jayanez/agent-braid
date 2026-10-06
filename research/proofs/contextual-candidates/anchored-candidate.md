# Anchored insertion candidate argument and mapping obligations

Status: **candidate argument, not accepted proof**. Specific independent proof
review and human scientific acceptance remain pending. The accompanying finite
mapping script cannot promote this status.

## Abstract carrier and observations

Let B be any finite ordered sequence of pairwise distinct base ID/value elements,
with a distinguished root ID outside those IDs. Let I be a finite family of typed
insert instances. Every instance identifies an immutable base/root anchor, a
new globally fresh ID outside B/root, a value and a distinct operation-instance
ID. IDs have a fixed total order. Each instance is applied once. The carrier
allows arbitrary finite sizes; the executable mapper separately restricts base
size 0–3, inserts 2–4, ID length <=64 and value length <=256.

A configuration contains B and one finite inserted-ID/value map per base/root
anchor. Applying instance i unions its fresh singleton into its anchor map.
Flattening emits root insertions in ID order, then each original B element in its
original order followed by its anchor's insertions in ID order. The candidate
observation is that flattened ordered ID/value sequence. Raw chronological
steps are distinct observations and are retained; they are not declared equal.

## Candidate derivation

Freshness makes each singleton union defined without replacing another payload.
An immutable anchor continues to exist after every insert. Thus any finite prefix
of distinct admitted instances remains within the carrier, establishing the
candidate closure invariant. For distinct instances i and j, their singleton
unions commute, whether their anchors agree or differ. Both application orders
have the same anchor maps, hence the same deterministic flattening. Their inserted
IDs, payloads and anchors are preserved as logical intent.

Define an adjacent exchange on an instance sequence as swapping its adjacent
entries and recomputing every physical insertion index from the resulting prefix
maps. Exchanging twice returns the same sequence. Exchanges at disjoint positions
commute. Three adjacent crossings 0,1,0 and 1,0,1 produce the same instance
permutation; both final map unions and flattening agree. Crossings act **left to
right** here. This is an involutive permutation action on the stated typed family,
not an inverse of actual external effects. It does not establish a literal
quantum-form Yang–Baxter theorem about agent tools.

Chronological before/after hashes and intermediate residual indices may differ.
Equality of those histories is not a consequence of final flattening equality.
No operation may inspect history or target a newly inserted/nested anchor in this
carrier. Delete, mutable base, duplicate IDs, retry, nondeterministic choice,
external effects and result-reading extensions require separate typed semantics.

## Mapping to source and open proof obligations

Source: `agent_braid/structured_exchange.py`, pinned in the feature's
[premise inventory](../../../specs/025-contextual-proof-obligations/premise-inventory.json).
`validate_request` enforces executable bounds, immutable base/root anchors and
fresh identities. `replay` adds each insertion, invokes `_flatten`, finds its
physical index and retains identified chronological steps. `_braid` applies
adjacent index crossings left to right. The finite oracle implements map union,
flattening and index computation independently rather than calling `_flatten`.

Open obligations for specific proof review:

1. Verify closure/freshness and the mathematical argument for **all finite valid
   abstract carriers**, independently of a finite test corpus.
2. Prove correspondence of source bucket insertion, lexical sibling sorting,
   prefix hashes and residual indexing with the abstract maps for every admitted
   bounded executable input.
3. State logical result preservation precisely. Source `replay` records insertion
   IDs, anchors, residual indices and final payloads; it does **not** expose a
   separate per-instance returned-result field. Preserved final payloads do not
   prove equality of unrepresented tool return values.
4. Verify exchange carrier, source indexing and relation conventions; scope every
   equivalence to flattened observation. No chronology quotient is accepted.
5. Validate excluded-model boundaries and independently review the handwritten
   derivation. No LLM technical review or finite source check supplies this gate.

The current three fixed mapping fixtures exercise 2, 3 and 4 instances, all their
orders, involutivity, adjacent/far permutations and raw chronology differences.
Four explicit exclusions exercise deletion, nested anchoring, reused base IDs and
nondeterminism. These are finite diagnostics, not exhaustive proof of the bounded
implementation or universal validity of the abstract argument.
