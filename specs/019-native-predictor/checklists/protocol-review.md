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
- [ ] **P019-02 — human label construct (high).** The
  [rubric](../annotation-rubric.md) must be reviewed with examples and reviewer
  instructions before labels are opened. Record both dimensions, two blinded
  judgments per pair, third-reviewer adjudication, disagreement and unknowns.
  Keep this proxy separate from the M3 verifier and observed outcomes.
- [ ] **P019-03 — comparison validity (high).** Freeze the family split and
  attempt annotation of every admitted holdout pair independently of both
  policies. Record failed attempts, coverage, class counts and missing-label
  bounds by family. Seal holdout labels from fitting and tuning; treat the
  first three-family comparison as descriptive.
- [ ] **P019-04 — rules and cost (medium).** Review the baseline's
  `keep-order` handling, the fixed calibration method and infeasibility rule,
  abstention, full time boundary and sparse reliability bins in the
  [protocol](../workload-protocol.md). Inspect actual bin sizes before any
  calibrated interpretation. Report training and annotation costs separately.

**Gate:** If P019-01 remains unmet, only feasibility findings can be reported.
No task checkbox, generated skill, structural validator or PR merge substitutes
for consent, scientific review or founder approval of the revised protocol.
