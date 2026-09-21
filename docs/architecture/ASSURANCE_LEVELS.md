# Assurance Compatibility Classes

These historical labels are not a total order of safety. The proposed Article 13
amendment separates property, method, domain, assumptions, observation and
execution contracts, and independently computed verification status. A producer
claim is never authorization. See [draft 0.2](DRAFT_0_2.md).

## Level 0 — Heuristic

Evidence such as different file names, model judgment, naming conventions, or historical likelihood. Useful for prioritization; insufficient for a correctness guarantee.

## Level 1 — Syntactic

Verified non-overlap in text ranges, AST regions, or other syntax-level resources. Aliasing, generated artifacts, configuration, and semantic dependencies may remain.

## Level 2 — Semantic

Dependency, data-flow, type, invariant, or domain-specific reasoning. Soundness is bounded by the analyzer and model completeness.

## Level 3 — Transactional

Declared and observed read/write/effect sets with version or isolation checks. External side effects and instrumentation gaps remain explicit.

## Level 4 — Confluence

Alternative schedules are joined or shown observationally equivalent by an exhaustive procedure, sound proof rule, or formal derivation over a stated domain. Finite replay alone remains empirical unless the domain is the finite set tested.

## Level 5 — Yang–Baxter

Well-defined exchange operators satisfy a stated Yang–Baxter equation or equivalent braid coherence condition in the specified structure. The result names its convention, equality notion, assumptions, and proof.

## Promotion rule

Each property and evidence method requires independently satisfied obligations.
Changing a compatibility class is not an automatic promotion in safety. Combining
many weak signals does not create a formal guarantee, and a referenced proof
remains unverified until a supporting checker validates it and its premises.
