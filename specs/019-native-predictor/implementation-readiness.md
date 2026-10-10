# SPEC-019 implementation readiness

**Historical plan (2026-10-05):** the opening work breakdown retains its
prospective scope. Dated continuations below record later synthetic increments;
the current implementation and experimental boundary are summarized here.

**Current status (2026-10-10):** T002/#182 synthetic trainer/inference and
T004/#184 verifier-boundary software are complete. T006/T008/T009/T010 are also
closed. T001/#181, T007/#188, T003/#183 and T005/#185 remain open, as do #180
and milestone 9. Zero real pairs are admitted. Training/inference/evaluation
are synthetic-only; no CLI integration or real-feed adaptation is delivered.
The [software completion record](software-completion.md) is the compact source
for the remaining experimental gates.

| Step | Task | Required output | Completion or stop condition |
|---|---|---|---|
| Source ownership and rights | T007 | Owner/participant/data-rights/privacy decision per family, before opening payloads | Absent permission leaves family excluded; patient, clinical, athlete/customer and private payloads remain outside this repository |
| Authoring-boundary feasibility | T007 | Contemporaneous immutable shared-base receipts, all sessions/pairs and primary exclusion ledger | Git history alone is insufficient; absent eligible pairs is a feasibility result |
| Protocol preparation | T001/T009 | Candidate source window, rubric, blinding/adjudication, split and class-coverage readiness report | No window extension or population change after labels; no approval inferred from machine checks |
| Scientific preregistration | T001 | Human-reviewed and frozen existing workload protocol/rubric with source admission | Five eligible families, train/calibration/three holdout split and declared label/class coverage remain required before fitting |
| Offline interfaces | T010 | Feature/artifact serialization, abstention and test doubles using synthetic inputs only | No fitted weights, calibration, real data or benefit claim; declare all fixtures synthetic |
| Trainer and inference | T002 | Actual trainer, fixed calibration and versioned inference tests/results | Real fit starts only after T001/T007 gates and frozen protocol; reject leakage or unavailable prediction-time features |
| Held-out evaluation | T003 | Known/unknown label bounds, disagreement, coverage and complete costs | Negative/inconclusive results are valid; do not tune on holdout |
| Consumer boundary | T004 | Unchanged deterministic verifier and authorization-denial controls | Predictor score never supplies a certificate or execution grant |
| Review | T005 | Candidate-bound evidence and human M3.5 decision | Tests, synthetic readiness and filtered lab sync cannot close real-source feasibility |

T009 targets a standard-library `scripts/check_predictor_readiness.py` that reads explicitly synthetic or metadata-only manifests, produces missing prerequisite reasons, and never opens a source or changes admission state. `tests/test_predictor_readiness.py` must cover missing rights, zero yield, family leakage, insufficient classes, unapproved rubric and hash drift. All real eligibility thresholds come from the existing proposed workload protocol; machine checks cannot grant approval.

T010 targets `agent_braid/native_predictor.py` and `tests/test_native_predictor.py` for feature extraction, versioned artifacts, deterministic ranking/ties and fail-closed abstention with hand-authored synthetic test doubles. Fitting weights or calibration, even to synthetic labels, remains outside this preparation task until the protocol gate permits the relevant experiment. No raw sensitive source content is committed.

Run proportional validation after implementation and bind actual evidence separately. The planned filenames/commands above are future targets; they do not exist or pass by virtue of this document.

## Offline preparation interfaces

T009 now provides `python -m scripts.check_predictor_readiness manifest.json`.
It reads only that explicitly supplied JSON manifest and prints a deterministic
report to stdout. Exit 0 means its *claimed metadata* satisfies the proposed
prerequisites; exit 1 means prerequisites are missing; malformed input exits 2.
It neither opens referenced source files nor changes admission, training or
review state. No manifest can produce training or execution authorization;
`humanApprovalVerified` is always false. Commitments detect differences between
supplied recorded/current hashes; they do not authenticate their issuer or
verify the true current protocol. Rights and approval flags remain unverified
claims. `realPairsAdmitted` remains zero because this checker admits no data.

The strict `m35-readiness-metadata-v1` manifest contains:

- `sourceKind`: `synthetic` or `metadata-only`. Neither permits source payloads.
- `protocol` and `rubric`: each contains `recordedHash`, `currentHash` (lowercase
  SHA-256 strings) and boolean `approved` claim.
- `families`: records with unique opaque `familyId`, one `partition` (`train`,
  `calibration`, `holdout`), boolean `eligible`, `windowFrozen`,
  `completenessReviewed`, `policyBlind` and `holdoutSealed` claims, and a `rights`
  object containing boolean `owner`, `participants`, `data`, `privacy` claims.
  Aggregate nonnegative integer `admittedPairs`, `positive`, `negative`,
  `unknown`, and `annotationAttempts` record accounting without source context
  or individual labels. Positive + negative + unknown must equal admitted;
  known labels cannot exceed attempts and attempts cannot exceed admitted.
  `sessionIds` and `duplicateGroupIds` contain opaque identifiers used to
  reject cross-partition leakage. They are not source paths or actor identities.

Unknown fields, unsupported sources, malformed identifiers/hashes, duplicate
families and inconsistent counts are errors. Unknown utility stays unknown and
cannot satisfy positive/negative coverage. The checker uses the existing
candidate five-family, 1/1/3 split, 100-known-label and holdout 20/20 thresholds;
it does not establish statistical power or approve those candidates. Supply no
patient, clinical, athlete/customer or private payloads. The complete synthetic
manifest generator in `tests/test_predictor_readiness.py` is a test fixture,
not a real cohort or permission record.

T010 provides imports from `agent_braid.native_predictor` only; it is not wired
into the shared CLI, source capture, scheduling or deterministic verifier.
`extract_features(request, source_kind="synthetic")` validates an existing M3
request with exactly two inserts and returns versioned features plus the input
hash. Anchor distance is absolute index distance in the immutable base, with
root index -1. Lengths preserve supplied operation order; lexical overlap is
Jaccard overlap of whitespace tokens after Unicode case folding, or zero for
an empty union. No repository, path, participant, label or verifier result is
an input feature.

A strict `m35-synthetic-ranker-v1` artifact contains `featureVersion`, `modelId`,
`weights` for exactly `baseSize`, `sameAnchor`, `anchorDistance`, `firstLength`,
`secondLength`, `lexicalOverlap`, a finite `bias`, and `provenance` containing
`kind: synthetic-hand-authored` plus an opaque `fixtureId`. This T010
hand-authored test-double interface has no trainer or calibration function;
`serialize_artifact` requires a separately supplied SHA-256 pin and returns
canonical JSON bytes without writing a file.
`propose` also requires pinned artifact hash, expected model ID and expected
input hash. Invalid fields, versions, provenance, nonfinite numbers, unknown
features, identity drift and arithmetic overflow return explicit abstention
with no score. Hashes bind the supplied commitments; they are not signatures
or proof of true source/feature provenance. The supplied feature vector is a
synthetic test double, not trusted real data. This T010 interface has no
trainer or calibration function; those are implemented separately under T002.

The current adapter does not model proposal-resolution events or construct an
annotator context ending at the selected second-proposal cutoff. Unsupported
event kinds fail closed, but that behavior does not prove feed completeness or
implement the cutoff. Resolution taxonomy, linkage to proposal identity, and
cutoff-context tests remain prerequisites before pair-level experimental
admission or annotation.

T002 provides a synthetic-only deterministic trainer and local scorer in
`agent_braid.native_predictor_training`. Weight normalization uses train rows
only; calibration receives only calibration-partition rows. The versioned
artifact binds exact train/calibration commitments, optimizer parameters and
calibration status. Its negative-control path permutes only train labels with
seed 0, refits through that same trainer, verifies the resulting input
commitments, scores holdout features without labels, and reports deterministic
verifier outcomes plus unknown-label bounds. Training/calibration/holdout pair,
family, session and duplicate-group identities must be disjoint; every trainer
and evaluator row now requires an opaque `duplicateGroupId` and rejects a group
that spans partitions. The upstream canonical grouping rule remains subject to
protocol review: the synthetic adapter derives provisional exact-pair/session
components only; those IDs do not authenticate real lineage, and pair IDs alone
must not replace duplicate grouping. The
founder selected one predeclared calibration family, pending independent
review; synthetic artifacts mark this as
`single-family-rows-founder-selected-pending-review`. This marker does not
prove preselection, which remains a separate preregistration gate. Any
multi-family aggregation requires an explicit protocol revision before
real-data fit. Missing classes or malformed inputs fail closed. The evaluator
accepts synthetic inventories only. These
synthetic tests validate software behavior, not real-data readiness, model
benefit or authorization to fit a workload candidate.

`rank` accepts `pairId`, `inputHash`, `vector` records in the caller's frozen
inventory order. It ranks decreasing raw scores, preserves that order on ties,
and retains abstentions at the end. It cannot prove the caller froze inventory
before labels; duplicate identities are rejected. Scores remain heuristic and
uncalibrated. All proposals and abstentions contain no certificate and deny
execution authorization. Even a high score does not invoke or bypass the M3
verifier. The synthetic T004 software-boundary controls passed; the merged
implementation and final post-merge reliability evidence are summarized in the
[2026-10-10 delivery record](../../docs/development/m35-project-alignment.md).
This software evidence does not imply human scientific review. T001/T007,
real-data training/calibration, held-out evaluation and experiment review remain
pending.

Focused verification command (Python 3.12+ in an isolated environment):

```sh
python -m unittest tests.test_predictor_readiness tests.test_native_predictor -v
```

Actual focused results are reported separately; quick/PR profiles and Luna
review remain separate from these interfaces and from scientific approval.

## Synthetic T002–T004 implementation candidate — 2026-10-09

The separate `agent_braid.native_predictor_training` module implements an
in-memory deterministic trainer for caller-declared synthetic rows (origin is
not authenticated), request-bound feature
preparation/scoring, versioned artifact validation and the fixed calibration
grid. Weight normalization and optimization use training rows only; calibration
uses the calibration partition only; holdout labels are prohibited. Trainer
and evaluator rows require opaque `duplicateGroupId` values and reject a
duplicate group spanning partitions. The synthetic adapter derives a
provisional deterministic group from normalized base/insert content and the
same session, ignoring ephemeral IDs and mapping anchors to base positions.
Its canonical encoding and source lineage are not independently authenticated;
it does not detect semantic near-duplicates or establish that a session
declaration is complete. Real use still requires a reviewed, source-bound
group/lineage manifest before partition assignment.
The candidate requires exactly one calibration family, matching the founder's
2026-10-09 selection to preselect one family before registration. The selection
remains subject to human scientific review; the artifact's
`single-family-rows-provisional` marker remains explicit until the protocol is
approved.

The adapter's `project_trainer_rows` recomputes requests and feature vectors,
accepts training and calibration label maps separately, and always projects
holdout labels as unknown. It accepts only synthetic inventories. The adapter
requires pair-level family IDs to match their enclosing inventory and rejects
a synthetic mutation that would disguise one family across partitions. The
envelope and pair metadata remain mutable caller declarations: joint rewrites
of family IDs and changes to partition or source-lineage declarations are not
detected. No verified cohort manifest binds those fields to source events and
requests. The adapter rejects prospective input because there is no
independently verified registration, rights, completeness and admission path.
Hash commitments and caller declarations detect limited tampering but do not
authenticate source provenance or grant permission. No private journal,
context or participant mapping is accessed or stored by this implementation.
For each synthetic pair it records the sequence of the later proposal and a
commitment to the global input-event prefix through that pair-specific cutoff.
These hashes do not prove feed completeness or that this prefix is sufficient
annotation context. Resolution-event taxonomy and proof that a pair was
unresolved at cutoff remain unspecified, so the synthetic adapter cannot
produce real annotation records or establish P019-02 eligibility.
Separate `auditOnlySessionCommitments` include each full session's opening and
closing event hashes, so they can cover post-cutoff events. They are audit
metadata only, distinct from each pair's cutoff commitment, and must be omitted
from any future annotator view.

The evaluator supports an optional synthetic-only source-extraction callback,
measures that callback symmetrically by policy/budget/repetition, and allocates
shared final report serialization equally between the policy arms. The
allocation remains provisional. Without the hook, reports explicitly mark
source extraction incomplete. No admitted-journal extractor or real end-to-end
measurement exists. Synthetic contract tests exercise the verifier boundary,
but no score supplies a verifier verdict, certificate or execution grant.

These controls complete only the software portions T002/T004; they do not
close T001/T007/T003/T005 or the experimental P019-01…04 gates. Source permission,
method decisions, human labels, a valid cohort, real fit/evaluation, candidate
evidence review and the founder's final decision remain outstanding.

The readiness CLI reads at most 1 MiB, rejects duplicate JSON members,
nonfinite JSON constants and nesting beyond 32 levels. Each manifest is limited
to 1,000 families, each opaque ID list to 4,096 entries, and each aggregate count
to 1,000,000. Invalid CLI diagnostics omit supplied paths, source fragments and
exception payloads. Synthetic ranking is limited to 4,096 candidates; enormous
integer weights produce deterministic validation failure rather than an
uncaught numeric-conversion error.

Current closure boundary and bounded remaining work: [software completion](software-completion.md).
