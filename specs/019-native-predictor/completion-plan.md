# SPEC-019 completion execution plan

**Goal:** implement the remaining SPEC-019 work, run a valid descriptive
experiment, capture reproducible evidence, obtain required human review and
close M3.5. Insufficient source yield/labels leaves this goal pending; a valid
negative or null experiment can complete it. The 2026-10-08 implementation
request adopts this delivery direction, not missing source-specific permission
or scientific approval. Public records are English.

## Priorities and existing tracker identities

| Priority | Task / issue | Dependencies and acceptance |
| --- | --- | --- |
| P0 | T009 / #222; T010 / #223 | Reconcile completed synthetic preparation against existing evidence with milestone-9 audit/apply; do not reopen training claims. |
| P0 | T007 / #188 | Review the five proposed natural workflows, distinctness, owner/participant/data rights, privacy, custody, source allowlists and independent completeness controls before source access. |
| P0 | T001 / #181 | Review protocol/rubric, model interfaces, reviewers and ADR-extension proposal. Freeze each approved source's window before capture and freeze split/label/model rules before fitting. |
| P1 | T007; T001 | Successful registration at least 24h before each midnight-start 14-day UTC window; enumerate/reconcile all sessions/pairs and obtain human source admission. Attempt blinded labels on every admitted pair and seal holdout. |
| P2 | T002 / #182 | Requires completed T001/T007 gates: deterministic offline trainer, versioned artifact, calibration and negative controls. |
| P2 | T004 / #184 | Requires actual predictor/consumer candidate: independent verifier and execution-denial controls. |
| P3 | T003 / #183 | Requires frozen model/calibration and untouched holdout: matched-budget evaluation, unknown-label bounds and full operational costs. |
| P4 | T005 / #185; parent #180; milestone 9 | Candidate-bound evidence, clean-room reproduction, technical review and explicit human/founder decision; source-backed tracking states and zero-operation audit. |

Existing task IDs/checkmarks and completed history are preserved. The review
packet is preparatory work within T001/T007; delivering it cannot check either
task. No new tracker task, experiment permission, model fit or source window is
created implicitly. GitHub Issues is the task target; do not duplicate an
unrelated plan under a new global task list.

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

Implement and review the metadata packet/checker first; source and training
work remains gated. Run focused unittest controls with Python 3.12+ in an
isolated environment, quick validation per coherent increment and one stable
PR profile. Capture exact commands, outputs, hashes and limitations. Freeze a
clean candidate before requesting human review, retaining historical completed
evidence and distinguishing it from the new preparation evidence.

After real experiment implementation, replace deferred acceptance anchors with
actual tests and reproduce the frozen experiment independently of ordinary CI.
A blocked/skipped CI job is not a passing result. Technical Luna review does
not replace human utility labels or scientific/founder approval. Keep independent
validation status explicit; no model adoption or public scientific claim follows
automatically from milestone closure.

Integrate reviewed increments through pull requests. Change parent/milestone
states only after their explicit closure decision and evidence-backed source
records are merged. Reconcile only milestone 9 and verify no remaining audit
operations. M4, System One, forecasting, release publication and confirmatory
cohorts remain outside this goal.
