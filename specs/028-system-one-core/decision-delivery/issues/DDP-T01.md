# [SPEC-028][DDP-T01] Freeze additive contracts and migration map

<!-- dedup-key: jayanez/agent-braid:system-one-decision-delivery:DDP-T01:v1 -->
Status: draft, never remote-created. Target repository: https://github.com/jayanez/agent-braid (local origin verified). Proposed parent: https://github.com/jayanez/agent-braid/issues/275. Milestone: S1.0. No new remote issue number allocated.

## Scope and acceptance

DDP-REQ-01 / DDP-SC-01; maps to SPEC-028/REQ-001, SPEC-028/REQ-002, SPEC-031/REQ-002.

Freeze exact field sets, canonicalization, limits, error taxonomy and T024/T025 version mapping; document old-version refusal and no authority escalation.

- [ ] Contract vectors and migration table reviewed against exact T025 candidate; affected public API/architectural decisions remain proposed until governance review.
- [ ] Negative controls: Malformed/unknown versions, missing pins and probability/coercion attempts are rejected by planned vectors; compare every proposed bound to T024 source.
- [ ] Compatibility, source immutability and no authority escalation retained.

## Assignment and dependencies

Owner: coordinator. Dependency keys: T025 completed engineering receipt checked by coordinator. State: prepared-conditional. Parent T025 result is not assumed complete. No agent is assigned/launched by this draft.

Owned files:

- `specs/028-system-one-core/contracts/verified-plan-v1.md`
- `specs/031-system-one-integration/contracts/verified-plan-consumer-v1.md`
- `specs/029-system-one-evaluation/verified-plan-conformance.md`

## Verification and evidence

Use focused standard-library unittest modules named by owned tests after implementation, then coordinator validate_change quick/pr under repository policy. No checks were executed by this draft.

Required receipt: candidate/source/contract hashes, actual commands and exit status, environment, input fixture identities, raw logs, observed negative outcomes, changed-file list, limitations and unresolved findings. A test plan is not obtained evidence. Contract vectors and migration table reviewed against exact T025 candidate; affected public API/architectural decisions remain proposed until governance review.

## Deduplication and boundary

The local 55-issue receipt and original task snapshot were reviewed. Original parent and task issues are retained. This is a proposed extraction/robustening supplement, not another implementation of the old task. Related original identities: SPEC-028/T001 https://github.com/jayanez/agent-braid/issues/276, SPEC-028/T002 https://github.com/jayanez/agent-braid/issues/277, SPEC-028/T003 https://github.com/jayanez/agent-braid/issues/278, SPEC-028/T004 https://github.com/jayanez/agent-braid/issues/279, SPEC-028/T005 https://github.com/jayanez/agent-braid/issues/280, SPEC-028/T006 https://github.com/jayanez/agent-braid/issues/281, SPEC-028/T007 https://github.com/jayanez/agent-braid/issues/282, SPEC-028/T008 https://github.com/jayanez/agent-braid/issues/283.

No exact DDP key exists in the inspected receipt. Local absence is not proof of remote absence; before any future authorized publish, search exact marker/title and extension tasks in current tracking, then update an existing issue if semantically equivalent. This chat did not inspect remote states. Do not publish automatically, bulk reconcile, close original issues or infer authority from historical publication authorization.

EUR 0; local CPU; no experiments, model runs, training, calibration, activation, remote writes or T025 edits.


## Refined scope and cost acceptance — 2026-10-20

Freeze exact field sets, canonicalization, limits, error taxonomy and T024/T025 version mapping; document old-version refusal and no authority escalation. Freeze separate decision/acquisition/end-to-end prepare budget semantics, nested absolute deadlines, enforceability labels and explicit unsupported/refusal behavior; do not reuse the classifier deadline for prepare.

Negative controls: Malformed/unknown versions, missing pins and probability/coercion attempts are rejected by planned vectors; compare every proposed bound to T024 source. Reject budget reset/enlargement, implicit prepare caps and false hard-termination guarantees.

Closure/evidence: Contract vectors and migration table reviewed against exact T025 candidate; affected public API/architectural decisions remain proposed until governance review.

See [budget boundary](../latency-and-budgets.md) and [whole-program scope](../program-map.md). This amendment governs any broader earlier deadline wording in this draft. The initial three T025 case preparations reported by coordinator at 8.5–15.1 seconds are preliminary; final results remain pending. No speedup or product deadline is asserted.

## T025 dependency meaning — final clarification

“T025 completed engineering receipt checked by coordinator” means the T025 engineering work is completed, its actual commands/results, exact candidate and changed-file/interface bindings are recorded, and the coordinator has checked that receipt. It does not mean human review, scientific admission, representative product acceptance, promotion or activation. Those gates remain pending and independent.

DDP-T01 may begin once that engineering dependency is satisfied and the coordinator explicitly assigns it. No additional human/product acceptance is implied as a prerequisite for this bounded implementation assignment. Later tasks retain their own dependencies, governance and acceptance boundaries. A preflight pass or unfinished preliminary T025 timing is insufficient to satisfy this receipt dependency.

