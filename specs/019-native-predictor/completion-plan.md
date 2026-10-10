# SPEC-019 completion execution plan

**Goal:** implement the remaining SPEC-019 work, run a valid descriptive
experiment, capture reproducible evidence, obtain required human review and
close M3.5. Insufficient source yield/labels leaves this goal pending; a valid
negative or null experiment can complete it. The 2026-10-08 implementation
request adopts this delivery direction, not missing source-specific permission
or scientific approval. Public records are English.

## Current software completion and deferred experiment — 2026-10-10

The founder adopted [software-completion.md](software-completion.md): integrate
synthetic trainer, adapter, evaluator and executable contracts, obtain technical
review and reproduction, and close only T002/#182 and T004/#184. T002 has no
real-fit prerequisite for this synthetic software deliverable. All fitting on
admitted workloads remains gated by T001/T007 and the reviewed protocol.
T006/T008/T009/T010 keep their completed history. T001/T007/T003/T005, #180 and
milestone 9 remain open. No new tracking IDs or capture permissions are created.

The single compact remaining-work register is software-completion.md. The
operational gates below remain future experiment prerequisites, not work to
perform during this software-only increment.

## Concrete review and operational gates

Review [source-review-packet.md](source-review-packet.md), its metadata-only
[candidate inventory](source-candidates.json), the non-operative
[ADR-extension proposal](adr-extension-proposal.md), the existing workload
protocol/rubric and [model interfaces](model-interface-plan.md) as one package.
Capture exact bytes with the read-only packet checker. A passing packet check
means preparatory inputs are structurally present; it authenticates no human.

Reject, merge or retain proposed families based on genuine workflow evidence,
not desired counts. Record actual source-file pins and permission decisions
privately before opening new payloads. Obtain two human blinded reviewers and a
third adjudicator. Do not freeze guessed dates, reviewer identities, partitions,
or approval flags. A subsequent concrete operational packet must name these
details before collection, labels or fit can advance.

Collection windows may overlap once separately approved. Require at least five
eligible families with one train, one calibration and three untouched holdout
families; at least 100 known labels overall, holdout 20/20 and both classes in
train/calibration. Preserve unknowns and every exclusion. Missing registration,
insufficient yield/classes, leakage or unreviewed source context stops the
affected phase without manufacturing data or weakening the protocol.

## Validation and delivery

Integrate and review the synthetic software and current candidate clauses;
real-source capture, annotation, fitting and evaluation remain gated. Run focused unittest controls with Python 3.12+ in an
isolated environment, quick validation per coherent increment and one stable
PR profile. Capture exact commands, outputs, hashes and limitations. Freeze a
clean candidate before requesting human review, retaining historical completed
evidence and distinguishing it from the new preparation evidence.

The former contract anchors now execute synthetic software checks. A future
real experiment still requires its own frozen reproduction independently of CI.
A blocked/skipped CI job is not a passing result. Technical Luna review does
not replace human utility labels or scientific/founder approval. Keep independent
validation status explicit; no model adoption or public scientific claim follows
automatically from milestone closure.

Integrate reviewed increments through pull requests. Change parent/milestone
states only after their explicit closure decision and evidence-backed source
records are merged. Reconcile only milestone 9 and verify no remaining audit
operations. M4, System One, forecasting, release publication and confirmatory
cohorts remain outside this goal.
