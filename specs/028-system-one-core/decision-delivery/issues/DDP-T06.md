# [SPEC-031][DDP-T06] Bind extracted decisions to read-only preparation consumers

<!-- dedup-key: jayanez/agent-braid:system-one-decision-delivery:DDP-T06:v1 -->
Status: draft, never remote-created. Target repository: https://github.com/jayanez/agent-braid (local origin verified). Proposed parent: https://github.com/jayanez/agent-braid/issues/303. Milestone: S1.3. No new remote issue number allocated.

## Scope and acceptance

DDP-REQ-06 / DDP-SC-06; maps to SPEC-031/REQ-004, SPEC-031/REQ-005, SPEC-031/REQ-006.

Implement separate adapter calling existing core prepare and ToolingService through approved interfaces plus real stdio tests. Port exact T025 handoff/tree logic without changing its research files or default tool registry.

- [ ] Core/service/real-stdio parity receipts, exact expected tree, cleanup and source-immutability checks. T024 corpus replay only if separately authorized as software integration regression; never new accuracy.
- [ ] Negative controls: Tampered choice/tree/source/prefix/payload, cross-consumer packet replay, frame/cancellation failures and rejected-k0; zero execute/recover/grant/persistent-run effects; evidence chunks checked completely.
- [ ] Compatibility, source immutability and no authority escalation retained.

## Assignment and dependencies

Owner: agent-B. Dependency keys: DDP-T05, T025 completed engineering receipt checked by coordinator. State: prepared-conditional. Parent T025 result is not assumed complete. No agent is assigned/launched by this draft.

Owned files:

- `agent_braid/system_one_verified_consumer.py`
- `tests/test_system_one_verified_consumer.py`
- `tests/test_system_one_verified_stdio.py`

## Verification and evidence

Use focused standard-library unittest modules named by owned tests after implementation, then coordinator validate_change quick/pr under repository policy. No checks were executed by this draft.

Required receipt: candidate/source/contract hashes, actual commands and exit status, environment, input fixture identities, raw logs, observed negative outcomes, changed-file list, limitations and unresolved findings. A test plan is not obtained evidence. Core/service/real-stdio parity receipts, exact expected tree, cleanup and source-immutability checks. T024 corpus replay only if separately authorized as software integration regression; never new accuracy.

## Deduplication and boundary

The local 55-issue receipt and original task snapshot were reviewed. Original parent and task issues are retained. This is a proposed extraction/robustening supplement, not another implementation of the old task. Related original identities: SPEC-031/T001 https://github.com/jayanez/agent-braid/issues/304, SPEC-031/T002 https://github.com/jayanez/agent-braid/issues/305, SPEC-031/T003 https://github.com/jayanez/agent-braid/issues/306, SPEC-031/T004 https://github.com/jayanez/agent-braid/issues/307, SPEC-031/T005 https://github.com/jayanez/agent-braid/issues/308, SPEC-031/T006 https://github.com/jayanez/agent-braid/issues/309, SPEC-031/T007 https://github.com/jayanez/agent-braid/issues/310, SPEC-031/T008 https://github.com/jayanez/agent-braid/issues/311.

No exact DDP key exists in the inspected receipt. Local absence is not proof of remote absence; before any future authorized publish, search exact marker/title and extension tasks in current tracking, then update an existing issue if semantically equivalent. This chat did not inspect remote states. Do not publish automatically, bulk reconcile, close original issues or infer authority from historical publication authorization.

EUR 0; local CPU; no experiments, model runs, training, calibration, activation, remote writes or T025 edits.


## Refined scope and cost acceptance — 2026-10-20

Implement separate adapter calling existing core prepare and ToolingService through approved interfaces plus real stdio tests. Port exact T025 handoff/tree logic without changing its research files or default tool registry. Require explicit decision, acquisition and end-to-end prepare budgets plus bounded per-stage telemetry receipts per latency-and-budgets.md. Measure repeated revalidation/native checks and cleanup separately; do not disable checks or infer speedup.

Negative controls: Tampered choice/tree/source/prefix/payload, cross-consumer packet replay, frame/cancellation failures and rejected-k0; zero execute/recover/grant/persistent-run effects; evidence chunks checked completely. Decision expiry prevents prepare; remaining prepare budget cannot reset; cancellation suppresses late result and proves cleanup/termination or records enforcement unsupported; stale observation/proof reuse refuses.

Closure/evidence: Core/service/real-stdio parity receipts, exact expected tree, cleanup and source-immutability checks. T024 corpus replay only if separately authorized as software integration regression; never new accuracy. Local bounded stage receipts include acquisition, IR, verifier, selection, tree build, revalidation, fresh native proof, prepare/reverification, transport/evidence validation and cleanup, with measured outer total and null unknowns. Numeric envelope and enforcement mode must be explicit before closure. No cache reuse without separately reviewed freshness/binding/invalidation contract.

See [budget boundary](../latency-and-budgets.md) and [whole-program scope](../program-map.md). This amendment governs any broader earlier deadline wording in this draft. The initial three T025 case preparations reported by coordinator at 8.5–15.1 seconds are preliminary; final results remain pending. No speedup or product deadline is asserted.

## T025 dependency meaning — final clarification

“T025 completed engineering receipt checked by coordinator” means the T025 engineering work is completed, its actual commands/results, exact candidate and changed-file/interface bindings are recorded, and the coordinator has checked that receipt. It does not mean human review, scientific admission, representative product acceptance, promotion or activation. Those gates remain pending and independent.

DDP-T01 may begin once that engineering dependency is satisfied and the coordinator explicitly assigns it. No additional human/product acceptance is implied as a prerequisite for this bounded implementation assignment. Later tasks retain their own dependencies, governance and acceptance boundaries. A preflight pass or unfinished preliminary T025 timing is insufficient to satisfy this receipt dependency.

