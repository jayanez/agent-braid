# Native System 1 implementation program

Status: six draft Spec Kit records, not implementation acceptance. Source date:
2026-10-05. The [reference analysis](reference-analysis.md) gives the evidence,
architecture comparison and limits; [reference-sources.json](reference-sources.json)
pins source identity. The original inspected base is recorded there; publication is rebased as described in [publication-context.md](delivery/publication-context.md).

The proposed order adopts Strands' narrow decision interface first, compares native
model architectures second and adds Laya-like product features selectively. The
result is a native Agent Braid capability, with neither upstream project integrated.
Architecture selection is conditional on the common evaluation, including rules
and the existing linear predictor. Starting order is a delivery choice, not evidence
that decoder models are better than encoder models.

| Milestone | Spec | Delivery and exit gate | Dependencies |
|---|---|---|---|
| S1.0 — Decision contracts | [028](spec.md) | Typed local API, rule backend, provenance, refusal, no authority escalation; reviewed offline boundary evidence | Existing verifier/runtime contracts |
| S1.1 — Decision evaluation | [029](../029-system-one-evaluation/spec.md) | Permissioned source/yield, blind labels, grouped splits, calibration and paired cost harness; report infeasibility if needed | 028 contracts; model comparison follows 030 prototypes |
| S1.2 — Native decision model | [030](../030-system-one-model/spec.md) | Own decoder/pointer and compact encoder prototypes; reproducible own artifacts; evidence-based architecture go/no-go | 029 pre-fit gate, then 029 common evaluation |
| S1.3 — Advisory integration | [031](../031-system-one-integration/spec.md) | Per-stage advisory adapters, same verifier/grants, separate read-only transport and complete chain costs | 028; rules can support engineering before model selection |
| S1.4 — Product capabilities and promotion | [032](../032-system-one-product/spec.md), [033](../033-system-one-promotion/spec.md) | Accept/defer CPU/language/schema/catalogue/lifecycle features independently; shadow, drift, rollback and exact-capability founder decision | 029/030/031; optional 032 features are not promotion prerequisites |

There are 36 requirements, 36 Given/When/Then acceptance scenarios and 49 implementation
tasks. Each spec contains spec, plan, research, data model, interface contract,
quickstart, task list, quality checklist, prospective validation and assurance record.
Stable IDs use SPEC-nnn / REQ-nnn / SC-nnn / Tnnn. Every implementation checkbox is
pending. Five milestones and 55 issues (six parents + 49 tasks) are published; drafts were generated
from the repository's existing tracking format. Issue closure never implies approval.

## Critical path and work ordering

1. Review 028 contract/budgets; implement the rule-backed core and negative controls.
2. Register source rights/yield and blind rubric; freeze grouped partitions, candidate
   roster and the deployment/cost envelope before model fitting (029 T001–T008).
3. Implement small offline native model fixtures, cache correctness and export checks
   (030 T001–T005), then train only within approved source and compute boundaries.
4. After the pre-fit decision (029 T008), either execute common paired evaluation
   with trained candidates (029 T009 additionally requires 030 T006), then choose/no-go
   the model (030 T008), or record pre-fit infeasibility directly in 029 T009. The
   infeasibility exit does not require training; blocked model tasks stay pending.
   Both dependency branches are acyclic. A feasibility report does not accept an
   architecture or promote a capability.
5. Integrate rules and model advice behind explicit capability switches (031). Actual
   neural traffic stays shadow/pending until 033 exact-capability promotion. Read-only
   advice does not create grants or expand current fixed-patch execution.
6. Select advanced features at 032/T001 before model selection; implement and evaluate
   only selected branches. Schema compilation and core hooks can proceed without a
   learned model. Deferred tasks stay pending; 032/T008 requires only the selected
   branches and cannot imply whole-spec acceptance. Promote only eligible capabilities
   with full chain evidence, immutable manifests and rollback (033). Preserve negative
   utility findings and unsupported devices/languages as explicit limits.

No calendar due dates or effort estimates are invented without workload/hardware and
staffing inputs. Core and integration engineering need not wait for a successful ML
experiment; source infeasibility can stop learned adoption while rules remain useful.
Tasks do not authorize concurrent agents or unreviewed source collection/training.

## Architecture and break-even hypothesis

Proposed data flow: immutable context → strict envelope/capability validation →
bounded backend → typed distribution + provenance → calibrated/domain-aware
abstention policy → advisory consumer → unchanged semantic verifier/operator boundary.
Trace the entire chain, including refusals, disagreement, fallback and observed cost.

Keep System 1 advice distinct from System 2 planning, semantic checking and execution.
A correct fast classifier is insufficient if rendering, loading, fallback or
verification dominates total time. If C1 is fast-path overhead, a is accepted coverage,
and C2 is existing decision cost, a first approximation for savings is
C1 + (1-a)C2 < C2, or C1 < a*C2. Extra verifier/review/retrieval costs must be added
to the left side. The equation is an accounting hypothesis, not a benchmark result.
Measure at matched risk/coverage and actual supported outcome, not inference alone.

## Spec Kit journey executed and scope limits

- Specify: pinned create_new_feature helper originally used for 022–027, and rerun
  for 028–033 after upstream assigned the earlier numbers. The publication checkout
  is planning/native-system-one; feature selector names do not imply implementation.
- Clarify: user scope incorporated; architecture intentionally open; actual sources,
  hardware, budgets and promotion remain explicit pre-fit/operational gates.
- Plan: setup_plan helper used; research, alternatives, model and contract proposals
  drafted with Constitution checks before/after design.
- Tasks: setup_tasks and prerequisite helpers used; ordered IDs, evidence and cross-spec
  dependencies established. No task implemented or marked complete.
- Checklist: requirements-quality assessment separates drafting from pending source,
  annotation, test, human-review and promotion evidence.
- Analyze: read-only cross-artifact assessment recorded in analysis.md; structural
  checks and dependency/coverage inspection do not establish scientific correctness.
- Taskstoissues: 55 repository-scoped issue drafts generated from the existing tracking
  source inventory with stable markers; remote publication was authorized on 2026-10-06 for this
  exact repository and scope and must preserve unrelated tracking.
- Constitution: existing authority checked; no amendment needed or performed.
- Implement/converge: deferred to future implementation; treating this planning packet
  as completed implementation would misrepresent all 36 acceptance scenarios.

Current upstream Context7 documents were consulted for workflow discovery. The
repository's pinned 1.0.7 source, shared overrides and local helpers govern this work;
no upstream workflow, extension, preset or scaffold regeneration was introduced.

## Handoff and tracking

See [quickstart.md](quickstart.md) for local validators and planning-only limitations.
The tracking mapping includes open new specs/milestones and review-pending parents;
existing milestone numbers, issue identities and checkbox history are retained.
Current titles follow the canonical tracking convention. GitHub's governed
sync apply requires reviewed records on clean develop after merge. Pre-merge drafts
must link the proposal candidate, not pretend the files already exist on develop.
Do not run a whole-repository apply to publish this scope: it can reconcile historical
items outside the System 1 program. Publication receipts must list the actual new URLs.

Implementation review must bind the exact candidate and obtain source/model rights,
deployment budgets and capability acceptance. Later canonical ADR adoption changes
authority inventory and requires visible drift review for current assurance snapshots.
Neither a merged planning PR nor open issues accept the architecture or reopen M4.

The current architecture/status clarification is editorial. Historical assurance
snapshots remain bound to their frozen authority bytes; implementation review must
check the current authority inventory and any intervening changes explicitly.
The dependency/quickstart corrections do not grant feature acceptance.

Scoped publication completed in [PR #274](https://github.com/jayanez/agent-braid/pull/274).
All five milestones, six parents and 49 linked tasks remain open.
The [publication receipt](delivery/publication.json) records actual URLs and readback
verification. Private user-Project verification was blocked by integration access;
the published spec/task labels support its existing automatic workflows.
