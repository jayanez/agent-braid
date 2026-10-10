# SPEC-019 protocol decision packet — 2026-10-08

**Status:** selected clauses recorded below; protocol remains a candidate.
Founder selected P019-02 A, P019-03 duplicate-grouping A, P019-04b A,
P019-04c A, and retained mandatory full-cost accounting under 04d on
2026-10-09. On 2026-10-09 the founder reconfirmed P019-02 A, selected
P019-03 duplicate-grouping A, and selected the P019-04 evaluation package
with fixed-budget useful yield at 50%, complete operational costs, and
descriptive calibration on calibration data only. These choices do not freeze unresolved clauses or approve the
protocol as a whole. Nothing in this packet admits data or permits source
access, registration, annotation, or training.
The workload protocol and rubric remain candidates pending explicit review.
Revised 2026-10-09 to correct the primary endpoint, calibration approval
status, decision identifiers, and cutoff semantics; selected clauses are now
recorded below, while the full protocol remains unapproved.

This packet isolates methodological decisions that affect labels, partition
integrity, measured utility, and calibrated claims. Recommendations are
proposals for founder review, not accepted protocol text. If a recommendation
is rejected, revise the protocol and rerun analysis before any data are
opened.

## Current disposition — 2026-10-10

The selections below are adopted candidate wording. The founder additionally
selected explicit linked `proposal-resolved` events with outcome and valid
sequence (ambiguous records excluded), and a base/proposals/anchors-only
annotation view with identity, time, order, policy/verifier metadata and later
context hidden. The private complete prefix is eligibility-audit material,
not annotation display. See the controlling [candidate protocol](workload-protocol.md).
Older option tables and review recommendations below are historical deliberation;
statements that call unit, display choice or calibration family are undecided
are superseded by the recorded selections. Rendering, outcome vocabulary,
source completeness, canonical bytes/lineage and timing/bin rules remain
pending experiment preparation. No protocol, sources or real experiment is
approved or frozen here.

## P019-02 — Annotation point, permissible context, and absent records

**Question:** What point in the editing record defines the ex-ante question,
and when can reviewers label a dimension `no` rather than `unknown`?

| Option | Rule | Consequence |
|---|---|---|
| **A — Pre-decision cutoff (recommended)** | Freeze the cutoff immediately after the later of the two proposal events in a validated total event sequence. Exclude the pair, with a fixed reason, if a resolution event for either proposal occurs at or before the second proposal event, or if the feed cannot totally order the events. Show only the selected base/proposals/anchors projection available through the cutoff; hide all later context, scores, priorities, partition, verifier status, and other judgments. Label `no` only when the admitted feed is complete through the cutoff and the rubric's evidence for absence is observable; otherwise use `unknown`. | Tests usefulness at a reproducible point when both proposals exist and neither is already resolved. Requires an authoritative total sequence, complete prefix, and resolution-event taxonomy. |
| B — Full-session review with masked outcomes | Show the whole session but mask direct verdicts and model fields. | Easier to review, but later actions can reveal the decision and contaminate an ex-ante usefulness judgment. |
| C — Fixed elapsed-time cutoff | Use a fixed duration after the second proposal, with a preregistered duration. Exclude a pair if either proposal is resolved at or before that cutoff; show no post-cutoff context. | Reproducible, but the extra delay can exclude many resolved pairs, truncate a pending decision or include unrelated work. It changes the eligible population and needs a new domain justification before registration. |

**Recommended freeze if A is chosen:** version the resolution-event taxonomy;
use the feed's unique sequence index, not timestamps alone, to define the
cutoff; exclude a pair if either proposal's resolution is at or before the second
proposal, or if completeness/order cannot be proved. If events share a
timestamp, the validated sequence index must order them uniquely; otherwise
exclude the pair. Store one immutable cutoff record
per pair and expose no event after it that encodes the outcome. Each reviewer
labels both rubric dimensions independently. An absent decision is `no` only
when a complete observable prefix supports that absence; missing or ambiguous
context remains `unknown`. Labels concern only evidence available at the
cutoff: later events cannot establish a positive or negative label. A missing
decision record in a prefix is not itself evidence for `no` unless the
approved feed is complete and the rubric identifies an observable basis for
absence.

## P019-03 — Duplicate grouping and pair orientation

### Duplicate or near-duplicate groups

| Option | Rule | Consequence |
|---|---|---|
| **A — Pair-level duplicate grouping (recommended)** | Normalize the ordered base values and both operation records using Unicode NFKC, casefold and whitespace collapse; omit per-event IDs and represent anchors by base position (`$root` stays `$root`). Group pairs with the same normalized base and the same unordered pair of normalized pure-insert operations. Independently keep records from the same source session/lineage in one component. Do not link otherwise distinct pairs solely because they share a base. | Prevents exact pair/session leakage without merging every unrelated edit on a common base. It may miss semantically similar or paraphrased pairs; report that limitation and make no claim of semantic duplicate detection. |
| B — Conservative same-base grouping | Canonicalize the base as its ordered element values after Unicode NFKC, casefold, and whitespace collapse; omit base element IDs and map anchors to element positions. For a matching base-content hash, group every pair from that base across sessions/workflows, regardless of operation values, kinds, anchors, or per-event IDs. Keep every group in one partition. | Reduces leakage among edits against identical normalized base content but can merge unrelated pairs and connect workload families. If components defeat the required split, report infeasibility; do not reassign after labels. |
| C — Fixed near-content similarity | Normalize base and operation values with Unicode NFKC, casefold and whitespace collapse; omit base and operation IDs and map anchors to base positions. Require equal base length and same operation-kind/anchor-position structure. Compare base elements positionally and operation values under both possible pair matchings; group if every aligned string has character 5-gram multiset Sørensen–Dice similarity ≥0.90. For strings shorter than five characters use the whole normalized string as one gram; empty/empty is 1 and empty/nonempty is 0. Form connected components before splitting. | Covers near copies across sessions/workflows with reissued IDs, but the proposed threshold may over- or under-group. Freeze the algorithm before labels; 0.90 is a protocol choice, not an empirically validated boundary. |

### Canonical orientation

| Option | Rule | Consequence |
|---|---|---|
| **A — Sequence-required orientation with canonical tie fallback (founder-selected)** | Require a unique monotonic event sequence as an eligibility gate and orient by sequence index. If two operation records have no distinct validated event order, use canonical operation-payload hash and then operation ID only as a deterministic orientation convention; mark it arbitrary, not chronological. This tie rule does not admit a pair whose source lacks a validated total sequence. Equal timestamps do not create an event tie: sequence may order them, but they must not be described as having distinct wall-clock times. | Gives `firstLength`/`secondLength` sequence-order meaning when indices differ; a tie fallback labels only representation and never supplies missing temporal evidence. |
| B — Canonical payload order | Orient by lexicographic hash of each canonical operation record and explicitly describe `first`/`second` as an arbitrary canonical convention, not chronology. | Independent of source clocks and reproducible, but has no temporal interpretation. It is not an alternative admission path. |

**Recommended freeze if duplicate A and orientation A are chosen:** form
structural groups before splitting; assign every linked family and group
wholly to one partition; then
derive pair orientation from the validated source sequence, using the stated
arbitrary tie-break only for orientation when a pair is otherwise eligible. A
hash ordering never admits a pair without a validated total sequence. If a group links families assigned
to different partitions, report the split infeasible rather than changing the
split after labels. No feature, label, score, or verifier result is used in
either decision.

## P019-04a — Baseline treatment of `keep-order`

| Option | Rule | Consequence |
|---|---|---|
| **A — Preserve current baseline (recommended)** | Rank `propose-swap` before `keep-order`; keep-order remains eligible for verifier work and is neither a veto nor a negative verdict. | Retains the current advisory meaning and ensures the baseline can spend its verifier budget on either proposal type. |
| B — Exclude keep-order from verifier work | Treat `keep-order` as an abstention for the baseline and spend calls only on `propose-swap`. | Changes the evaluated policy and can make costs/yield incomparable; would require revising the baseline and preregistration before labels. |

## P019-04b — Primary endpoint and verifier-call accounting

The controlling workload-protocol candidate defines the primary comparison
as the number of assessed-useful `verified-bounded` proposals under the
prespecified 50% verifier-call ceiling `floor(0.5 * N)`, with lower and upper
bounds for unknown labels. It does not define yield per actual call as the
primary endpoint. Report actual calls, unused ceiling and useful yield per
actual call as secondary efficiency measures. Compare both policies on the
same frozen `N`; abstentions do not consume calls and the policy continues
down its frozen ranking. Divergent and inconclusive calls count against the
ceiling but are not useful verified proposals. Do not let a per-call ratio
substitute for the fixed-budget useful count: abstentions or early exhaustion
could return fewer useful proposals while improving a ratio.

For secondary metrics, known-label precision is the number of selected
`verified-bounded` pairs with label 1 divided by selected
`verified-bounded` pairs with known utility labels. Known-label recall is the
number of selected `verified-bounded` pairs with label 1 divided by all
holdout pairs with known label 1. Report divergent and inconclusive calls
separately, along with label coverage and unknown bounds; do not count a
verifier status as a utility label.

| Option | Rule | Consequence |
|---|---|---|
| **A — Fixed-budget useful count (recommended)** | Primary endpoint is the count of known-positive assessed-usefulness labels among `verified-bounded` proposals at the 50% ceiling; lower/upper counts treat unknown labels on `verified-bounded` proposals as not useful/useful. Report actual calls and per-call ratios secondarily. | Matches the protocol's stated target and cannot reward lower output solely through a smaller call denominator. |
| B — Useful yield per actual call | Make the bounded count divided by actual verifier calls the primary endpoint. | Measures efficiency per call but changes the estimand and can favor a policy that returns fewer useful proposals or uses less of the fixed ceiling. Requires protocol revision and review before labels. |

### P019-04c — Calibration reporting for the first cohort

The current fixed grid is a **candidate in the workload protocol**, not an
accepted task-plan decision. The founder's implementation plan retains this
candidate method and descriptive limits, subject to required human scientific
review. No calibration or fit is authorized by this packet.

| Option | Rule | Consequence |
|---|---|---|
| **A — Descriptive fixed-grid calibration (recommended)** | Keep the candidate grid in `workload-protocol.md`; fit only on calibration rows when both known classes are present, scores have nonzero variance and fitting succeeds. Otherwise report no probabilities and omit Brier. Report descriptive Brier and five equal-frequency bins only on known labels, show each known-label count and mark bins below ten as too sparse. | Preserves the founder's implementation plan while accurately marking the statistical method as pending human scientific review and preventing unsupported calibrated claims. |
| B — No probabilities in the first cohort | Do not fit calibration parameters or report Brier/reliability bins for the first cohort; retain raw scores and all utility metrics. | Avoids weak calibration interpretation but changes the current candidate plan. Record as a protocol revision before any fit. |

**Selected subdecision — one calibration family.** The workload
protocol describes one calibration family, and the synthetic trainer now
refuses multi-family calibration. Its artifact records
`single-family-rows-founder-selected-pending-review`; this implements the
selected one-family candidate without implying complete protocol approval.

| Option | Rule | Consequence |
|---|---|---|
| **A — One calibration family (recommended)** | Preselect exactly one eligible calibration family before registration and fit the fixed grid on all known calibration labels in that family. | Matches the candidate split's minimum and avoids an unreviewed cross-family weighting rule; it may leave less calibration data. |
| B — Pool by row | Combine all calibration-family rows and give each labeled pair equal weight. | Larger calibration set, but families with more pairs dominate the objective. Requires an explicit protocol statement and family-level reporting. |
| C — Equal family weight | Compute a fixed-grid objective within each calibration family and average family objectives equally under a frozen rule. | Prevents large families from dominating, but requires enough known examples per family and a precisely specified aggregation and failure rule. |

### P019-04d — Full cost boundary

The implementation plan already requires source-to-request extraction,
scoring, ranking, verifier work and serialization; three warm-ups and twenty
alternating measured repetitions on the same pinned environment; and separate
training and annotation effort. These are required boundaries, not optional
scope choices. The default synthetic timing omits source extraction and its
first implementation did not allocate final report serialization; it cannot
establish the real cost result. Phase subtotals may be reported in addition to
the complete total, not instead of it.

The current synthetic runner can measure a supplied source-extractor callback
symmetrically for both policies and allocates shared comparison-report
serialization equally across the two policy arms. The equal allocation is
provisional and is not yet frozen for the real experiment. Without a real
admitted-journal extractor and a frozen cost allocation rule, T003 cost
evidence remains incomplete.

### P019-04e — Infeasibility handling

| Option | Rule | Consequence |
|---|---|---|
| **A — Keep strict gate and stop early when impossible (recommended)** | Preserve all current family/class/label thresholds and no-fit rules. Once the metadata-only eligibility audit proves the five-family partition infeasible, stop before annotation and record the evidence; otherwise continue only after all rights and approvals. | Saves unnecessary annotation when the required coverage cannot be met and never relaxes a threshold or authorizes fitting. |
| B — Keep strict gate without an early stop | Preserve the same thresholds, but complete the authorized label-attempt plan before declaring infeasibility. | May collect more feasibility information but adds annotation effort when the required split is already impossible. |

The current strict gate is at least five eligible families with at least one
training, one calibration, and three holdout families; at least 100 known
labels overall; at least 20 positive and 20 negative holdout labels; and both
known classes in training and calibration. Preserve the current fixed
calibration grid, tie-breaking, abstention, and sparse-bin reporting.

## Decisions to record

**Recorded selections (2026-10-09):** P019-02 A (cutoff after the second
proposal in a validated total event sequence); P019-03 duplicate grouping A
(normalized identical pairs plus common source session/lineage remain linked);
P019-03 orientation A with the recommended B fallback constrained to
deterministic orientation only (a validated total sequence remains an
eligibility gate; a hash must not admit a pair without it); P019-04a A
(`keep-order` remains verifier-eligible and is neither a veto nor a negative);
P019-04b A (fixed-budget useful count, with unknown-label bounds, at the 50%
ceiling); P019-04c A (descriptive fixed-grid calibration only on calibration
data, with no probability/Brier when unavailable) and one preselected
calibration family; 04d (complete cost boundary mandatory); and 04e A (preserve
all thresholds and stop before annotation when the metadata audit shows the
five-family split is infeasible). The protocol remains a candidate pending
full scientific review.

**Remaining implementation/review:** neutral rendering and audit sidecar for the selected display; canonical
duplicate encoding/linkage details; resolution-event
taxonomy and source-completeness proof; deterministic reliability-bin
allocation; and cost clock/cache/shared-cost rules. P019-01 source/rights
feasibility is also unmet. The synthetic adapter now records
orientation method, both event-sequence indices, `sameEventTie`,
`sameTimestamp`, and annotator visibility. Its input gate requires a unique
global event sequence, so equal timestamps do not create an event-order tie;
the canonical hash fallback is not used to admit or orient an otherwise
unsequenced pair. This synthetic metadata does not prove a real feed's order.
The selections approve only wording for the next scientific review; they do
not approve the protocol as a whole, sources, rights, windows, registration,
annotation, training, or holdout access.

**Subsequent founder decisions (2026-10-09):** P019-04e A preserves all
thresholds and stops before annotation when metadata-only review establishes
the five-family partition is infeasible. The bounded owner-only source review
currently has zero eligible families and zero admitted pairs; this does not
prove future sources unavailable. The founder also selected the evaluator call
unit: one non-abstaining unordered pair equals one submitted production plus
one verifier invocation, including verifier-side evidence regeneration;
divergent and inconclusive outcomes consume the unit, abstentions do not.
These decisions do not authorize source access or annotation.

## Independent adversarial review — 2026-10-09

Luna Latest (medium) reviewed this packet, the workload protocol, annotation
rubric, review checklist, specification and model-interface plan. This was a
documentary review only; it did not inspect source payloads, labels or runtime
results and is not scientific or founder approval. Its recommendation is to
choose P019-02 A, P019-03 duplicate A and orientation A with B fallback,
P019-04a A, 04b A, 04c A and 04e A, while retaining 04d as mandatory. The
protocol must remain unfrozen until the following details are resolved:

1. **Call unit.** The candidate evaluator treats one unordered pair as one
   call: one submitted `produce` plus one `verify` invocation, with the
   verifier's evidence regeneration included in that unit. Divergent and
   inconclusive results consume the unit; abstentions do not. The implementation
   now reports submitted production, verifier invocation and verifier-side
   regeneration counts, and separates submitted-production from verifier-call
   time. Confirm this accounting against the selected evaluator before freezing
   the protocol.
2. **Annotation display.** The founder selected base, proposals and anchors; exact neutral rendering remains unimplemented. A
   decision packet must identify the approved base and both operation payloads,
   how anchors are rendered, and any preceding context needed to judge the
   rubric. Hide sequence, timestamps, IDs, outcome proxies, later events and
   session-close details unless a separately justified field is essential.
   Keep ordering and source provenance in an audit sidecar unavailable to
   annotators. Source completeness must be established by an approved feed,
   not inferred from an absent local record.
3. **Duplicate canonicalization.** The trainer and evaluator now require opaque
   duplicate-group IDs and reject a group crossing partitions. The synthetic adapter derives provisional exact-pair/session components;
   it does not authenticate real lineage. Before real fitting, freeze the included base/operation
   fields, excluded identifiers/provenance, anchor mapping, operation ordering,
   canonical byte encoding and connected-component linkage for session/lineage.
4. **Orientation ties.** Store an explicit same-event-tie indicator and
   orientation provenance. Length features under an arbitrary tie-break must
   not be interpreted as temporal; alternatively, version a symmetric feature
   rule before fitting.
5. **Calibration.** The founder selected exactly one calibration family; multi-family
   aggregation is outside the candidate. The
   synthetic trainer fail-closes on multiple families until selected. Define
   deterministic quantile/bin allocation for equal-frequency reliability bins.
6. **Cost measurement.** Define clock start/stop, whether warm-ups are per
   policy, treatment of shared extraction and serialization, cache state, and
   a symmetric input-preparation boundary for both policies. The synthetic
   evaluator exercises extraction only through a supplied callback and assigns
   half of comparison-report serialization to each policy arm; both facts are
   reported and remain subject to protocol review. Real source extraction and
   final report serialization must be measured in the admitted run.

These clarifications are review recommendations, not adopted decisions. No
protocol text, source authority, data access, registration, labeling or model
fit is authorized by this review.

## Follow-up adversarial regression review — 2026-10-09

Luna Latest (medium) independently reviewed the pair-cutoff adapter change,
its regression tests and the selected protocol clauses. Its 27 adapter tests
passed. No code defect was found in the synthetic scope: each unordered pair
uses its later proposal as its own cutoff; the adapter requires a contiguous
validated total event sequence; and canonical hashing does not admit
unsequenced pairs. The reviewer identified and this revision resolves one P2
document inconsistency: the earlier option table said to use hash ordering
when a source lacked a validated sequence, contrary to the founder's selected
eligibility gate. The table now makes the hash a tie-orientation rule only.

The review also confirmed that missing resolution-event taxonomy, independent
source-completeness proof, annotation display fields and real source-backed
context remain blockers rather than synthetic implementation defects. The
adapter commits only the synthetic global event prefix and cannot establish
that this is sufficient real annotation context. An earlier review's statement that
the adapter did not derive duplicate groups records that prior candidate; the
current adapter derives only provisional synthetic groups, not source-bound
lineage. The adapter separately exposes full-session audit commitments, which
can include post-cutoff close events; the code names and documentation mark
these audit-only and exclude them from pair cutoff records. They are not
annotator context or cutoff evidence. This documentary/code review is not scientific or founder approval and
does not authorize data access, capture, annotation, training or holdout review.

## Evaluator label-integrity adversarial review — 2026-10-09

Luna Latest (medium) performed read-only adversarial review of the synthetic
trainer, evaluator, adapter and verifier boundary. The first review found that
an independent metric-label map could contradict annotation/adjudication
fields. Follow-up reviews found missing explicit attempt records, repeated
reviewer/adjudicator IDs, empty failure reasons, and contradictory adjudication
states. The evaluator now derives/checks metric labels against reviewer
consensus or an explicit third-review record; requires both review attempts,
pairwise-distinct opaque IDs for two reviewers and any adjudicator, and
nonempty reasons for unknown outcomes; and refuses disagreement without an
adjudication attempt. The final follow-up found no further bypass in this
synthetic validation boundary; its 91 focused tests passed.

These checks close software-consistency defects only. Reviewer IDs, labels,
attempts and rationales are still caller-supplied synthetic values and do not
authenticate identity, independence, authorization, blinded context or source
provenance. A trusted roster and auditable source-bound annotation package are
required before real evaluation. This review did not inspect private sources,
labels or human records and is not scientific approval or founder approval.
