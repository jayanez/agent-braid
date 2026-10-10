# SPEC-019 deferred tasks

The founder chose workload utility prioritization after the
[feasibility audit](feasibility-audit.md) and approved a limited
[source screen](source-audit.md). The [workload protocol](workload-protocol.md),
[annotation rubric](annotation-rubric.md) and actual data remain pending before
T001 can be completed. The bounded M3 experiment has founder review; no model
or M3.5 benefit is reported.

- [ ] T001 (REQ-001/002, SC-001..004): Complete source permission and
  prospective session/pair yield audit; review and freeze the sampling frame,
  human utility rubric, policy-blind holdout annotation, class coverage,
  features, family splits, baseline, calibration, cost rules and thresholds
  before training. The limited public screen is recorded; a consented source
  and eligible pair yield are still missing.
- [x] T006 (REQ-002, SC-006): Instrument an owned local flow with
  immutable base/operation events, stable IDs and provenance. Publish a
  deterministic synthetic capture and session/pair exclusion report, including
  invalid-base, unsupported-operation, invalid-anchor and missing-provenance
  cases. Record zero real admitted pairs; this demonstration cannot complete
  P019-01 or T001.
- [x] T008 (REQ-002, SC-007): Build a prospective local authoring sidecar,
  admission ledger and all-pairs adapter, plus exact-file filtered lab
  exporter and metadata-only remote seal validator. Exercise synthetic
  adversarial cases and document the two private lab and audit repositories.
  This completes tooling only: no real source window, admitted real pair,
  utility label or upstream completeness finding is asserted. The two
  read-only source deploy keys and lab Actions syncs were verified on actual
  runners on 2026-10-01; those operational results do not register a real
  source window or complete T001/P019-01.
- [ ] T007 (REQ-002, SC-003/004): In a later source-feasibility phase, audit
  existing session feeds only after exact source permission, participant/data
  rights and privacy review. On 2026-10-09 the founder confirmed owner/admin
  scope across Kinetiq, SmartNotes and Agent Braid, restricted candidate data
  to the founder's own authored content, excluded third-party material, and
  approved privacy/export review with explicit exclusions. That owner-level
  decision does not establish participant rights/notice, an immutable feed,
  completeness or pair yield, and does not authorize a capture window. The
  reviewed Kinetiq pins remain outside M3.5 scope; SmartNotes is only a
  nonclinical workflow lead; Agent Braid validation-method and release-evidence
  remain separate provisional categories, while its interface candidate is
  excluded. The bounded reviewed set has zero eligible families and pairs.
  Keep T007 open; do not broaden discovery or infer that another actor's
  proposal is owner-authored. First review the proposed local sidecar signals
  (`session-open`, actor `base-seen`, `insert-proposed`, `session-close`) against
  a real authoring boundary; verify shared-base independent intent from
  contemporaneous receipts and reconcile journal completeness with the source
  admission register. Version an adapter for all sessions, operations and
  unordered pairs with T008's prospective adapter rather than treating
  T006's exactly-two-operation synthetic CLI as a real feed. Preserve the
  separate repo-level feasibility records,
  fix a contiguous window only after all gates pass, enumerate all sessions
  and candidate pairs, report eligibility and exclusions by family, and reject
  Git-only histories that lack the shared-base event relation. SmartNotes
  patient and clinical payloads, Kinetiq athlete/customer data, and all
  private content stay excluded and outside this repository.
- [x] T002 (REQ-001, SC-001/002): Implement offline trainer and versioned
  local inference with negative controls.

T002's synthetic implementation now includes deterministic train-only weight
fitting, calibration-partition fitting, versioned artifact commitments and a
canonical seed-0 permuted-label refit/evaluation path. Its tests use invented
rows only; real-data fitting remains gated by T001/T007 and the frozen protocol.
See the [implementation readiness record](implementation-readiness.md) and
the synthetic trainer/evaluator tests.

- [ ] T003 (REQ-002, SC-003/004): Evaluate held-out calibration when feasible,
  abstention, assessed-useful proposals, missing labels, reviewer disagreement
  and total analysis cost against the rule baseline.
- [x] T004 (REQ-003, SC-005): Confirm verifier and execution boundaries.
- [ ] T005 (REQ-001..003): Capture evidence and request M3.5 review.

## Synthetic implementation increment — 2026-10-09

T002 now has an offline, in-memory trainer and request-bound scorer in
`agent_braid/native_predictor_training.py`. Callers must declare rows
synthetic, but the trainer cannot authenticate their origin and records that
provenance as unverified. It requires train/calibration/holdout separation by
family, session and duplicate-group identity derived by the provisional
synthetic adapter, fits weights from train rows, and records calibration
provenance in the artifact. The candidate requires exactly one calibration
family, matching the founder's selection to preselect one family before
registration. The adapter derives provisional groups
from normalized pair content and stable same-family session identity across
windows. The exact canonical encoding is pending review, and real source lineage
is not authenticated. No real fit, calibration or model result is claimed;
the software implementation task T002 is complete, while any real fit remains
gated by T001/T007 and the reviewed protocol.

The projection also requires every pair-level family identifier to equal the
enclosing inventory family. A synthetic regression proves that a shared
train/holdout family is rejected by the trainer and that rewriting holdout pair
families to disguise that leak is rejected at projection. This consistency
check does not authenticate the inventory envelope or source commitments.
Jointly rewriting an inventory envelope and its pair metadata, or changing
partition/session/group declarations before projection, is not detected by
this synthetic interface. A separately verified cohort manifest or seal must
bind those fields to source events and requests before any real-data use.

The local adapter in `agent_braid/native_predictor_adapter.py` validates
synthetic source-window records, enumerates pairs, derives provisional
duplicate components from normalized pair content and session identity, and projects separate
training/calibration labels into the trainer schema; holdout labels are not an
input. It rejects prospective adaptation because verified registration,
rights, completeness and admission gates do not exist. Caller manifests,
hashes and duplicate-group IDs do not establish provenance, source lineage,
completeness or permission. Real lineage manifests remain unreviewed. For each
pair it now records a synthetic cutoff after the later proposal and a
commitment to the global event prefix through the cutoff. This is not a
completeness proof or a reviewed annotation-context projection; resolution
taxonomy and unresolved-at-cutoff checks remain unimplemented pending protocol
review. A synthetic `proposal-resolved` event inserted between the first and
second proposals now fails the whole adapter input closed; this does not
interpret resolution semantics or implement the approved exclusion rule. It
orients pairs by the validated total event sequence; canonical hash fallback
never admits an unsequenced pair.
T001 and T007 remain open; no payload was opened or captured.

The synthetic evaluator now requires explicit attempts from two reviewers with
distinct opaque IDs for every evaluated pair. Unknown labels need a nonempty
reason; each reviewer disagreement needs a third-review attempt with a
distinct ID and either a rationale-backed adjudicated label or an explicit
unknown reason. Metric labels must agree with the row's consensus/adjudication,
and malformed or unattempted records fail closed. Luna adversarial review found
and regression-tested the label-map, missing-attempt, repeated-ID, adjudicator
and malformed-unknown bypasses. These controls validate synthetic record
consistency only: IDs are caller declarations, not an authenticated reviewer
roster, and no annotation context, identity, rights or independence is
verified. Real-source label provenance and the approved blinded annotation
package remain prerequisites; T003 stays open.

T003 has a synthetic comparison runner in
`agent_braid/native_predictor_evaluation.py`, including budget ranking,
abstention, verifier-status accounting, unknown-label bounds and a train-only
seed-0 permuted-label control. An optional source-extractor callback is timed
symmetrically on synthetic inputs and report-serialization time is allocated
provisionally across policy arms. There is no admitted-journal extractor and
no real end-to-end run; T003 remains open.

The contract tests exercise artifact/inference tampering, holdout evaluation
and separation from the deterministic verifier. They establish software
behavior only. This completes T004's verifier/execution-boundary task; T005
remains open because there is no real candidate, eligible holdout, human review
or founder decision. Current focused evidence is 92 tests under Python 3.13.11.
The earlier broad reliability run was interrupted and is not a pass.
The 2026-10-10 software completion runs quick and one stable PR profile under
the newly approved plan; their results are recorded separately and do not
retroactively validate the interrupted candidate. The runs and their limits are recorded in
[`synthetic implementation evidence`](../../docs/experiments/evidence/m35-native-predictor-synthetic-2026-10-09/README.md).

## Offline preparation follow-up

See [implementation readiness](implementation-readiness.md). These draft tasks preserve existing source/training gates and cannot complete T001 by synthetic demonstration.

- [x] T009 (REQ-002/SC-003,SC-004): Implement a read-only metadata/synthetic preregistration readiness checker that reports missing permissions, real yield, family/split/class coverage, blinding and rubric approval without admitting data or opening new source payloads.
  Dependencies: existing protocol/rubric candidates; human review before real-source use, T001/T007 before fit. Targets: `scripts/check_predictor_readiness.py`, `tests/test_predictor_readiness.py`, `implementation-readiness.md`. Verification/evidence: missing-rights, zero-yield, leakage, absent-class, unapproved-rubric and stale-hash controls; run quick then PR; obtained evidence stays empty until executed.
- [x] T010 (REQ-001,REQ-003/SC-001,SC-005): Prepare synthetic feature extraction, model-artifact serialization, deterministic ranking and abstention interfaces with hand-authored test doubles; do not fit weights, calibrate or report predictor benefit.
  Dependencies: T009 and review of unchanged prediction/verifier boundary; T001/T007 still gate fitting and T002 retains actual training ownership. Targets: `agent_braid/native_predictor.py`, `tests/test_native_predictor.py`. Verification/evidence: absent/unknown features, stale artifact versions, identity/hash mismatch, deterministic ties and verifier/authorization separation; record synthetic controls only.

Obtained T009/T010 evidence: 19 synthetic predictor/readiness controls passed,
Luna technical review and the shared stable PR profile passed (504 tests, four
documented skips). See `docs/experiments/evidence/autonomous-tracks-2026-10-06/`.
At that stage, no fit occurred. The 2026-10-09 continuation below records
synthetic-only trainer/evaluator tests; no real-workload fit occurred. Real-source fitting, evaluation, source admission and human review remain
pending; T002 and T004 are software-only completions.

## GitHub tracking reconciliation — 2026-10-09

Read-only verification found #222/T009 and #223/T010 already closed, #180
still open, and milestone 9 still open with seven open and four closed issues.
`python3 scripts/sync_github_tracking.py audit --milestone-number 9` returned
`operations: []`; no remote tracking mutation was needed. This reconciles the
T009/T010 bookkeeping only and does not change the then-pending T001–T005/T007,
parent issue or milestone state.

## Software closure and remaining experiment — 2026-10-10

T002 and T004 are closed only for synthetic trainer/inference and verifier
boundary implementation. SC-001/002/005 software checks are distinct from
real-source satisfaction of REQ-001/002. The three contract anchors execute;
no synthetic run supplies real labels, real fit or human scientific approval.
The [software completion record](software-completion.md) is the single compact
remaining-work register. T001, T007, T003, T005, #180 and milestone 9 remain open.
