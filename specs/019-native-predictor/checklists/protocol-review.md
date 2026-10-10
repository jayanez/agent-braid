# SPEC-019 protocol quality review

These questions track the four adversarial findings against the proposed
[workload protocol](../workload-protocol.md). A checked document rule is not
evidence that a real source or valid result exists. The founder approved only
source feasibility work; the full protocol needs a new review.

Use the [protocol decision packet](../protocol-decision-packet-2026-10-08.md)
to record founder selections for P019-02…04. On 2026-10-09 the founder selected
P019-02 A; P019-03 duplicate grouping A and sequence-first orientation with
hash-only tie fallback, keeping total sequence as an eligibility gate;
P019-04a keep-order eligible; 04b fixed-budget count A; 04c descriptive
fixed-grid calibration A with one preselected calibration family; and the
mandatory full-cost boundary. On 2026-10-09 the founder also selected P019-04e
A: preserve all thresholds and stop before annotation when the metadata audit
shows the five-family split is infeasible. These clauses remain candidate text
pending human scientific review; remaining methodological and operational
choices are still open.

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
  **Selected candidate:** cutoff immediately after the second proposal in a
  validated total sequence; only context at or before cutoff is eligible for the selected projection.
  The founder selected explicit linked `proposal-resolved` events and a
  base/proposals/anchors-only annotator view. The outcome vocabulary, rendered
  neutral fields, implementation and approved completeness source still need
  review; the complete prefix is audit-only, not annotator context. The synthetic adapter now records a pair-specific
  cutoff and prefix commitment; this does not establish real-feed completeness
  or provide an annotation packet. Full-session audit commitments may cover
  later close events and must stay out of every annotator view.
- [ ] **P019-03 — comparison validity (high).** Freeze the family split and
  attempt annotation of every admitted holdout pair independently of both
  policies. Record failed attempts, coverage, class counts and missing-label
  bounds by family. Define a reproducible duplicate/near-duplicate grouping
  rule across sessions and related workflows before partitioning. Define and
  freeze a canonical orientation for each unordered pair before extracting
  the order-sensitive `firstLength`/`secondLength` features. Seal holdout
  labels from fitting and tuning; treat the first three-family comparison as
  descriptive.
  **Selected duplicate candidate:** normalized exact pair plus common
  session/lineage grouping. The synthetic helper now derives exact-pair and
  same-family session components and rejects partition-crossing groups; it is
  not a verified source-bound grouping manifest. Canonical bytes and lineage
  inputs remain open. Synthetic orientation metadata is implemented and tested:
  a unique global event sequence is required, equal timestamps do not create an
  event-order tie, and hash ordering is deterministic orientation only, never
  an admission fallback. A real source's total order remains unproven.
- [ ] **P019-04 — comparison unit, rules and cost (medium).** Review the
  baseline's `keep-order` handling and state whether one verifier call consumes
  one unordered pair (including both deterministic paths), how
  `verified-bounded`/`divergent`/`inconclusive` contribute to the primary
  assessed-useful count under the fixed 50% call ceiling, and whether
  abstentions consume budget. Per-actual-call yield is secondary unless a
  revised protocol explicitly changes the estimand. Review the candidate
  calibration grid as pending human approval, its descriptive coverage or
  explicit no-probability rule, the strict infeasibility gate, full end-to-end
  time boundary and sparse reliability bins in the
  [protocol](../workload-protocol.md). Inspect actual bin sizes before any
  calibrated interpretation. Report training and annotation costs separately.
  **Selected candidate:** fixed-budget useful count at 50%, descriptive
  calibration only in calibration data, full operational cost accounting, and
  early stop before annotation if the strict family gate is infeasible. One
  non-abstaining unordered pair consumes one unit (production plus verification
  and verifier-side evidence regeneration); divergent and inconclusive results
  consume it, while abstentions do not. Reliability-bin allocation and
  timing/cache/shared-cost details remain open.

**Gate:** If P019-01 remains unmet, only feasibility findings can be reported.
No task checkbox, generated skill, structural validator or PR merge substitutes
for consent, scientific review or founder approval of the revised protocol.
