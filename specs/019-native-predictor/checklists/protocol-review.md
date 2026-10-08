# SPEC-019 protocol quality review

These questions track the four adversarial findings against the proposed
[workload protocol](../workload-protocol.md). A checked document rule is not
evidence that a real source or valid result exists. The founder approved only
source feasibility work; the full protocol needs a new review.

- [ ] **P019-01 — source and yield (high).** The
  [source register](../source-audit.md) must name a consented session feed,
  fixed collection window, complete session/pair counts and primary exclusion
  causes by family. The limited public screen admits zero real pairs. Do not
  lower the five-family or 100-known-label threshold or crop sessions to fill
  a quota without a newly reviewed domain decision. The synthetic capture
  demonstration checks accounting only and contributes zero real pairs.
- [ ] **P019-02 — human label construct and blinding (high).** The
  [rubric](../annotation-rubric.md) must define an ex-ante judgment with
  examples and reviewer instructions before labels are opened. Freeze a
  per-pair annotation cutoff and expose only context available before the
  decision/resolution being assessed; hide later decisions, accept/reject
  outcomes and `session-close` results in addition to scores, priority, split
  and verifier status. Specify when an absent record is `no` versus `unknown`.
  Record both dimensions, two blinded judgments per pair, third-reviewer
  adjudication, disagreement and unknowns. Keep this proxy separate from the
  M3 verifier and observed outcomes.
- [ ] **P019-03 — comparison validity (high).** Freeze the family split and
  attempt annotation of every admitted holdout pair independently of both
  policies. Record failed attempts, coverage, class counts and missing-label
  bounds by family. Define a reproducible duplicate/near-duplicate grouping
  rule across sessions and related workflows before partitioning. Define and
  freeze a canonical orientation for each unordered pair before extracting
  the order-sensitive `firstLength`/`secondLength` features. Seal holdout
  labels from fitting and tuning; treat the first three-family comparison as
  descriptive.
- [ ] **P019-04 — comparison unit, rules and cost (medium).** Review the
  baseline's `keep-order` handling and state whether one verifier call consumes
  one unordered pair (including both deterministic paths), how
  `verified-bounded`/`divergent`/`inconclusive` contribute to the primary
  assessed-useful yield and precision/recall denominators, and whether
  abstentions consume budget. Review the fixed calibration method and its
  minimum descriptive coverage or explicit no-probability rule, the
  infeasibility rule, full time boundary and sparse reliability bins in the
  [protocol](../workload-protocol.md). Inspect actual bin sizes before any
  calibrated interpretation. Report training and annotation costs separately.

**Gate:** If P019-01 remains unmet, only feasibility findings can be reported.
No task checkbox, generated skill, structural validator or PR merge substitutes
for consent, scientific review or founder approval of the revised protocol.
