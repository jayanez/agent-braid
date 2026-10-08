# SPEC-019 protocol decision packet — 2026-10-08

**Status:** decision aid only. Nothing in this packet freezes P019-02…04,
authorizes source access, admits data, or permits annotation or training.
The workload protocol and rubric remain candidates pending explicit review.

This packet isolates methodological decisions that affect labels, partition
integrity, measured utility, and calibrated claims. Recommendations are
proposals for founder review, not accepted protocol text. If a recommendation
is rejected, revise the protocol and rerun analysis before any data are
opened.

## P019-02 — Annotation point, permissible context, and absent records

**Question:** What point in the editing record defines the ex-ante question,
and when can reviewers label a dimension `no` rather than `unknown`?

| Option | Rule | Consequence |
|---|---|---|
| **A — Pre-decision cutoff (recommended)** | Freeze the cutoff immediately after the later of the two proposal events in a validated total event sequence. Exclude the pair, with a fixed reason, if a resolution event for either proposal occurs before or at the second proposal event, or if the feed cannot totally order the events. Show only the complete source prefix through the cutoff; hide all later context, scores, priorities, partition, verifier status, and other judgments. Label `no` only when the admitted feed is complete through the cutoff and the rubric's evidence for absence is observable; otherwise use `unknown`. | Tests usefulness at a reproducible point when both proposals exist and neither is already resolved. Requires an authoritative total sequence, complete prefix, and resolution-event taxonomy. |
| B — Full-session review with masked outcomes | Show the whole session but mask direct verdicts and model fields. | Easier to review, but later actions can reveal the decision and contaminate an ex-ante usefulness judgment. |
| C — Fixed elapsed-time cutoff | Use a fixed duration after the second proposal, with a preregistered duration and the same masking rule as A. | Reproducible, but the duration can truncate a pending decision or include unrelated work; a new domain choice is needed. |

**Recommended freeze if A is chosen:** version the resolution-event taxonomy;
use the feed's unique sequence index, not timestamps alone, to define the
cutoff; exclude a pair if either proposal's resolution precedes the second
proposal, or if completeness/order cannot be proved. If events share a
timestamp, the validated sequence index must order them uniquely; otherwise
exclude the pair. Store one immutable cutoff record
per pair and expose no event after it that encodes the outcome. Each reviewer
labels both rubric dimensions independently. An absent decision is `no` only
when a complete observable prefix supports that absence; missing or ambiguous
context remains `unknown`.

## P019-03 — Duplicate grouping and pair orientation

### Duplicate or near-duplicate groups

| Option | Rule | Consequence |
|---|---|---|
| **A — Conservative same-base grouping (recommended)** | Canonicalize the base as its ordered element values after Unicode NFKC, casefold, and whitespace collapse; omit base element IDs and map anchors to element positions (`$root` stays `$root`). For a matching base-content hash, group every pair from that base across sessions/workflows, regardless of operation values, kinds, anchors, or per-event IDs. Keep every group in one partition. This uses no labels, features, scores, or verifier outcomes. | Reproducible and prevents leakage among edits against identical normalized base content, including reissued IDs. It can merge unrelated pairs and does not catch paraphrased/near-duplicate bases; if group links defeat the required split, report infeasibility. |
| B — Fixed near-content similarity | Normalize base and operation values with Unicode NFKC, casefold and whitespace collapse; omit base and operation IDs and map anchors to base positions. Require equal base length and same operation-kind/anchor-position structure. Compare base elements positionally and operation values under both possible pair matchings; group if every aligned string has character 5-gram multiset Sørensen–Dice similarity ≥0.90. For strings shorter than five characters use the whole normalized string as one gram; empty/empty is 1 and empty/nonempty is 0. Form connected components before splitting. | Covers near copies across sessions/workflows with reissued IDs, but the proposed threshold may over- or under-group. Freeze the algorithm before labels; 0.90 is a protocol choice, not an empirically validated boundary. |

### Canonical orientation

| Option | Rule | Consequence |
|---|---|---|
| **A — Sequence-first orientation (recommended when available)** | Require a unique monotonic event sequence and orient by sequence index. For two operations in the same event sequence, use canonical operation-payload hash and then operation ID as deterministic tie-breaks; explicitly label this tie case arbitrary, not chronological. Validate uniqueness and monotonicity before admission. | Gives `firstLength`/`secondLength` temporal meaning only when sequence indices differ; same-event ties remain deterministic but non-temporal. If a source lacks a validated sequence, use B. |
| B — Canonical payload order | Orient by lexicographic hash of each canonical operation record and explicitly describe `first`/`second` as an arbitrary canonical convention, not chronology. | Independent of source clocks and reproducible, but has no temporal interpretation. |

**Recommended freeze if A/A are chosen:** form structural groups before
splitting; assign every linked family and group wholly to one partition; then
derive pair orientation from the validated source sequence, using the stated
arbitrary tie-break for same-event pairs. If a group links families assigned
to different partitions, report the split infeasible rather than changing the
split after labels. No feature, label, score, or verifier result is used in
either decision.

## P019-04 — Verifier-call unit and primary metric denominators

### Baseline treatment of `keep-order`

| Option | Rule | Consequence |
|---|---|---|
| **A — Preserve current baseline (recommended)** | Rank `propose-swap` before `keep-order`; keep-order remains eligible for verifier work and is neither a veto nor a negative verdict. | Retains the current advisory meaning and ensures the baseline can spend its verifier budget on either proposal type. |
| B — Exclude keep-order from verifier work | Treat `keep-order` as an abstention for the baseline and spend calls only on `propose-swap`. | Changes the evaluated policy and can make costs/yield incomparable; would require revising the baseline and preregistration before labels. |

| Option | Rule | Consequence |
|---|---|---|
| **A — Call-level assessed-usefulness (recommended)** | One budget unit is one invocation of the unchanged deterministic verifier for one unordered pair; that invocation evaluates both prescribed orders. Only `verified-bounded` and known-positive utility count as a primary success. `divergent` and `inconclusive` consume the call and are non-successes. Define primary `useful verified yield per call` as known-positive `verified-bounded` pairs divided by all calls; its bounds place unknown-label `verified-bounded` pairs in the numerator as zero or one, respectively. Define secondary call-level precision over calls with known labels, and conditional precision over known-label `verified-bounded` calls. Recall denominator: all known-positive holdout pairs. Abstentions make no call, consume no budget, are counted separately, and the policy continues down its frozen ranking. | Ties the primary yield to total verifier work and gives missing labels explicit bounds. The two precision measures retain distinct, named denominators. |
| B — Conditional precision as primary | Use the same call unit, but calculate primary precision only among `verified-bounded` results with known utility labels; report call-level yield as secondary. | Answers utility conditional on verifier success, but may favor a policy with more divergent or inconclusive calls. All status counts and costs remain visible. |

Under A, the primary yield denominator is always all verifier calls, including
calls whose utility label is unknown. Call-level precision is known-positive
`verified-bounded` calls divided by all calls with known utility labels; the
conditional precision denominator is only `verified-bounded` calls with known
utility labels. Brier and reliability bins use known labels only and report
their label coverage. Unknown-label
`verified-bounded` results contribute zero to the primary lower-bound
numerator and one to its upper-bound numerator; other statuses remain
non-successes. Do not claim a directional advantage if bounds reverse the
comparison. Report verifier statuses, label coverage, abstentions, actual
calls, and unused call ceiling for each policy and budget.

## P019-04 — Calibration reporting for the first cohort

This is fixed by the accepted task plan and is not an open choice in this
packet: preserve the current fixed calibration grid. Fit only on the calibration
partition when both known classes are present, scores have nonzero variance,
and fitting succeeds; otherwise report no probabilities and omit Brier. Report
Brier and the five equal-frequency bins on known labels when calibration
succeeds, with each bin's known-label count; bins under ten known labels are
explicitly too sparse for interpretation. Keep all calibration output descriptive. Any additional
numeric coverage floor or suppression of an otherwise estimable calibration is
a new protocol change and needs separate review before labels are opened.

## P019-04 — Full cost boundary and infeasibility rule

| Decision | Proposed rule | Consequence |
|---|---|---|
| **Cost A — Required end-to-end total (recommended)** | Measure source-to-request extraction, policy-specific preparation, scoring, ranking, verifier calls, and serialization by phase and as one end-to-end operational total on the same environment. Charge each policy only for work it performs. Report one-time fitting and annotation separately. | Preserves an end-to-end primary comparison while avoiding charging predictor-only features to the rule baseline or hiding common ingestion/verification work. |
| Cost B — End-to-end plus phase sensitivity | Retain every Cost A measure, and additionally report shared and policy-specific phase subtotals separately; do not replace or suppress the required end-to-end total. | Adds diagnostic attribution without changing the primary cost comparison. |

| Decision | Proposed rule | Consequence |
|---|---|---|
| **Infeasibility A — Preserve strict gate (recommended)** | Require all current family and label thresholds, both classes in train/calibration, complete approved windows, and sealed holdout before fitting. If any condition fails, record the result as infeasible/inconclusive; do not fit, tune on holdout, crop sessions, extend windows, or reduce thresholds. | Preserves the current scientific claim and makes missing yield a valid feasibility result. |
| Infeasibility B — Add an earlier stop | Keep every current threshold and no-fit rule, and add a pre-label stop as soon as the audited eligible-family inventory proves the five-family split impossible. | Avoids unnecessary annotation effort without changing the minimum evidence requirement. |

The current strict gate is at least five eligible families with at least one
training, one calibration, and three holdout families; at least 100 known
labels overall; at least 20 positive and 20 negative holdout labels; and both
known classes in training and calibration. Preserve the current fixed
calibration grid, tie-breaking, abstention, and sparse-bin reporting.

## Decisions to record

Record the founder's selected option for each decision above before changing
the protocol or opening any labels. A selection approves only the methodological wording
and the next protocol review; it does not approve sources, rights, windows,
registration, annotation, training, or holdout access.
