# Harness improvement implementation program

Status: draft planning; owner direction confirmed on 2026-10-20. This program
plans capability implementation, not execution admission or architectural
adoption. See the [agreed idea](../../docs/ideas/harness-improvement.md),
[pinned audit](../../research/harness2-source-audit.md) and
[ADR proposal](adr-proposal.md).

Reference documentation uses original English prose for Agent Braid and excludes
upstream logos and infographics. The owner explicitly authorized adapting useful
upstream code, architecture, scaffolding and key mechanisms to Agent Braid's
existing semantics. The [adaptation map](upstream-adaptation.md) names source
symbols, target modules and required changes. Reused software portions must retain
their applicable provenance, notices and modification history.

| Milestone | Spec | Deliverable and exit | Dependencies |
|---|---|---|---|
| HAR.1 — Harness variant laboratory | [048](spec.md) | Strict manifests/surface, separate admission, deterministic refinement, durable recovery, full limits/evidence and an explicit native host qualification disposition | Existing analysis/evidence primitives; new execution contract before native effects |
| HAR.2 — Harness evaluation and learning | [049](../049-harness-evaluation-learning/spec.md) | Two-axis registered comparison, scoped experience, human promotion/no-go and an offline future automatic-promotion decision | Deterministic engineering from 048; native cohorts separately require qualified 048/T008 and 049/T004 |

Two specs contain 16 requirements/scenarios and 20 pending implementation/gate
tasks. No implementation checkbox is completed by this planning packet. No dates,
speedup estimates, accuracy percentages or native acceptance are invented.

## Delivery order and branch conditions

1. Review the proposed contract and threat/effect boundary (048/T001). Freeze
   numerical resource/session caps and protected paths before implementing effects.
2. Build manifest/import/admission and deterministic runner (048/T002–T005), then
   contrastive refinement and durable recovery (T006/T007). Run adversarial
   integration and package the engineering result (T009/T010).
3. In parallelizable dependency terms only, register both-axis cases and a
   prospective comparison (049/T001/T002). This does not authorize concurrent
   agents. Deterministic evaluation (049/T003) depends on 048/T009, not on native
   admission, native source yield, training or positive utility.
4. Qualify native host containment/route separately (048/T008); admit sources and
   exact pilot runs only through 049/T004. If infeasible, retain the native tasks
   pending and report the reason. Do not weaken containment or the EUR 0 cap.
5. Implement quarantined experience (049/T006). Evaluate each cohort without a
   library first; add the chronological-library ablation only after T006. Report
   per-axis results and complete cost (049/T005), including negative findings.
6. Prepare human candidate/profile promotion or no-go (049/T007). Evaluate optional
   automatic promotion offline (T008); this can produce a deferred/no-go decision
   without positive human promotion. Integrate read-only experimental evidence
   (T009) and publish a bounded disposition (T010). Native ordinary-use activation
   additionally requires applicable native evidence and the exact human decision.

T005's minimum executable slice excludes its optional library ablation until
T006 exists; T006 does not depend on T005, so this is acyclic. No task needs a
positive research result merely to report a valid negative/inconclusive outcome.
Finishing an assessment task does not accept the assessed capability. Milestones
remain open until their explicitly stated implementation and review scope is met;
pending native branches must be separately completed or owner-dispositioned.

## Organic fit and differentiation hypothesis

Agent Braid already owns effects, interaction analysis, evidence, fixed-patch
recovery and advisory boundaries. Reuse those primitives; the new object is the
bounded harness variant and the experiment that decides whether to retain it.
An improver never grants itself permissions, changes the semantic verifier or
relabels missing evidence as success. Useful parallelism must be supported by
effects and preserved semantics rather than by agent count.

Harness² motivates general/task-specific contrastive proposals and experience
reuse. GEPA and ACE show that generic reflection and evolving context are already
established research directions; the proposed differentiation is inspectable,
effect-constrained refinement with abstention and complete-cost decisions. This
requires measurement and does not establish novelty or formal safety.

## Evidence and adoption boundaries

The audit's five upstream deterministic tests support only those upstream
controls. Our feature scenarios have no obtained implementation evidence.
Synthetic controls, actual native observations, human ratings and economic
acceptance retain independent identity. No FC.1, System 1, M4.5 or telemetry gate
is closed, inherited or reopened by this program. No model training is needed.

The ADR stays feature-local and proposed. Moving an adopted ADR into docs/adr
requires explicit authority-inventory impact review of current assurance records;
historical approvals are never rebound. A future automatic-promotion contract
must follow the same review and adoption path before activation.

## Spec Kit and tracking

The repository's pinned create_new_feature and setup_plan helpers created 048 and
049; their selector names are not evidence of a Git branch switch. Work occurs in
the independent recovery clone on `research/harness2-assessment`.
Specify/clarify/plan/tasks/checklist/analyze and scoped issue preparation are
planning steps; implement/converge are future work. The initial shared-object-store
preflight failure and documented recovery appear in the audit.

Source tracking adds only these two specs/milestones; existing states and task
checkboxes are preserved. Publish exactly two parents and 20 task issues with
stable markers and parent links in `jayanez/agent-braid`, under the owner's request
to populate this project's milestones/issues/tasks. Pre-merge issue bodies must
identify proposal sources rather than claim that files already exist on develop.
Private Project visibility/status is a separate observation from issue creation.
