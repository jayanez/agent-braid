# SPEC-019 protocol decision review — P019-02…04

**Status:** decision packet for founder review; no option is adopted by this
document. The current workload protocol and annotation rubric remain
unapproved candidates. Do not register a prospective window, open labels, fit
weights or evaluate a real holdout until the selected decisions and the full
protocol have been reviewed and frozen.

This packet records the concrete choices needed to resolve P019-02 through
P019-04. Recommendations preserve the candidate protocol's scope and existing
thresholds. A decision may be recorded by its option ID; a custom alternative
must state the changed rule and its consequence.

## P019-02 — temporal cutoff and blinded annotation

**Current candidate:** each family uses one contiguous 14-day UTC window,
starting at 00:00 UTC, registered successfully at least 24 hours before its
start. Enumerate every session and every eligible pair in the window. Freeze
the inventory, source commitments, exclusions, pair order and family splits
before labels are opened. Attempt both independent labels on every admitted
pair, including holdout; hide model scores, baseline priority, split, verifier
verdict and other reviewers' judgments. Keep holdout labels sealed from
feature selection, fitting, calibration, ranking and protocol changes.

| Option | Rule | Consequence |
|---|---|---|
| **A (recommended)** | Keep the 14-day UTC windows and 24-hour registration lead. Freeze the complete inventory and splits at window close; complete policy-blind annotation for all pairs before scoring; release holdout labels only after both ranked outputs and verifier results are committed. | Preserves the prospective census and blinding while allowing one fixed, auditable analysis order. Any missing label remains unknown; no extension or quota-driven sampling. |
| B | Freeze the inventory and splits at window close, but allow holdout labels to be opened before scoring once both reviewer attempts are complete. | Easier operational review, but increases the risk that analyst choices after seeing labels affect ranking or evaluation. Requires stronger access separation and an immutable pre-score analysis commitment. |
| C | Use another cutoff or disclosure order. | Requires exact UTC/event cutoff, who can see each field and when, and a justification before any registration. Any change to window duration or label exposure revises the candidate protocol. |

**Decision fields to freeze:** cutoff source and timestamp semantics; inventory
seal time; reviewer-visible context; concealed fields; adjudication cutoff;
holdout-label release condition; and immutable commitments captured before
scoring.

## P019-03 — pair orientation and duplicate grouping

**Current candidate:** the population is unordered same-base insert pairs.
Inventory order is frozen from source event ID and operation ID. The adapter
currently derives feature positions from proposal event order, while the
synthetic evaluator rejects duplicate unordered request pairs. This leaves a
meaningful order-dependence risk because `firstLength` and `secondLength` are
separate features.

| Option | Rule | Consequence |
|---|---|---|
| **A (recommended)** | Canonicalize each pair by ascending stable operation ID before feature extraction and request construction. Define duplicate groups before partitioning using the immutable base plus the unordered operation identities/content commitment; keep every member of a duplicate/near-duplicate group in one partition. | Removes arbitrary event-order influence from first/second features and prevents duplicate leakage. May reduce usable sample counts; report every grouped/excluded item. |
| B | Preserve source event order for feature extraction, but assign the whole exact/near-duplicate group to one partition and test both orientations as a metamorphic invariant. | Retains source chronology but permits the learned score to vary when event ordering changes. Would need a frozen rule for which orientation is used in evaluation. |
| C | Defer orientation and duplicate semantics. | T001 remains unresolved; no training or partition freeze can begin. |

**Decision fields to freeze:** canonical orientation key; exact duplicate
identity; near-duplicate rule and review method; whether duplicate members are
excluded or grouped; and the rule for counting groups in split coverage.

## P019-04 — primary metric, baseline, calibration and complete cost

**Current candidate:** compare the native ranker with the fixed rule baseline
(`propose-swap` before `keep-order`) on the same frozen inventory and unchanged
verifier. Use floor-based budgets at 25%, 50% and 100%; 50% is the primary
comparison. The primary quantity is assessed-useful verified proposal yield.
Report known-label precision/recall, unknown-label bounds, abstentions,
disagreement, coverage and per-family results. Calibration is descriptive
only when both classes and non-degenerate scores allow it; otherwise omit
probability and Brier claims. Include extraction, scoring, ranking, verifier
calls and result serialization in total analysis time; report training and
annotation separately. A null, negative or inconclusive result is valid.

| Option | Rule | Consequence |
|---|---|---|
| **A (recommended)** | Retain the current primary metric, 50% budget, fixed baseline, floor rounding, calibration grid and full end-to-end cost boundary. Treat 25%/100% as sensitivity checks. | Preserves current thresholds and makes any direction-of-effect statement depend on verified usefulness and complete analysis cost. Existing synthetic timing cannot satisfy the end-to-end cost requirement. |
| B | Make known-label precision at 50% the primary metric; retain all other metrics as descriptive and keep full cost reporting. | Easier to interpret for selected pairs but discards useful yield as the principal target and can obscure abstentions and coverage. This changes the scientific question and requires protocol revision. |
| C | Review an itemized metric/cost table before choosing a primary endpoint. | No endpoint is frozen yet; T001 and training remain gated. The table must define denominators, unknown-label bounds, abstention treatment, timing boundaries and decision rule before any fit. |

**Decision fields to freeze:** primary endpoint and denominator; baseline
priority; budget rounding; tie and abstention behavior; unknown-label bounds;
calibration eligibility and failure behavior; timing start/stop boundaries;
repetition and summary statistic; and the condition for any directional claim.

## Recommended decision record

The recommended packet response is **P019-02 A, P019-03 A, P019-04 A**. This
selects existing temporal, blinding, baseline, budget, calibration and cost
boundaries, while resolving canonical orientation and duplicate leakage. It
does not authorize sources, collection, annotation, fitting, holdout access,
or closure. After a founder decision, update the existing protocol and rubric
in place, preserve this packet as decision history, and request the required
human scientific review before treating the protocol as frozen.
