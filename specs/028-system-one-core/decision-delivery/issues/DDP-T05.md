# [SPEC-028][DDP-T05] Deliver deterministic verified-plan selection

<!-- dedup-key: jayanez/agent-braid:system-one-decision-delivery:DDP-T05:v1 -->
Status: draft, never remote-created. Target repository: https://github.com/jayanez/agent-braid (local origin verified). Proposed parent: https://github.com/jayanez/agent-braid/issues/275. Milestone: S1.0. No new remote issue number allocated.

## Scope and acceptance

DDP-REQ-05 / DDP-SC-05; maps to SPEC-028/REQ-003, SPEC-028/REQ-004, SPEC-031/REQ-003.

Bind acquisition, IR and registry; verify complete offered plans then select stable eligible goal-reaching option or defer. Report technical refusal separately; preserve shared deadline.

- [ ] A local vertical-slice receipt from pinned source to verified decision, full per-option consequences and all negative controls. No model invocation.
- [ ] Negative controls: No eligible plan, tie, duplicate/omitted option, stale snapshot/registry, unmet dependency, changed goal and exhausted budget; selected result has no probability or authority.
- [ ] Compatibility, source immutability and no authority escalation retained.

## Assignment and dependencies

Owner: agent-A. Dependency keys: DDP-T02, DDP-T03, DDP-T04. State: prepared-conditional. Parent T025 result is not assumed complete. No agent is assigned/launched by this draft.

Owned files:

- `agent_braid/system_one_verified_decision.py`
- `tests/test_system_one_verified_decision.py`

## Verification and evidence

Use focused standard-library unittest modules named by owned tests after implementation, then coordinator validate_change quick/pr under repository policy. No checks were executed by this draft.

Required receipt: candidate/source/contract hashes, actual commands and exit status, environment, input fixture identities, raw logs, observed negative outcomes, changed-file list, limitations and unresolved findings. A test plan is not obtained evidence. A local vertical-slice receipt from pinned source to verified decision, full per-option consequences and all negative controls. No model invocation.

## Deduplication and boundary

The local 55-issue receipt and original task snapshot were reviewed. Original parent and task issues are retained. This is a proposed extraction/robustening supplement, not another implementation of the old task. Related original identities: SPEC-028/T001 https://github.com/jayanez/agent-braid/issues/276, SPEC-028/T002 https://github.com/jayanez/agent-braid/issues/277, SPEC-028/T003 https://github.com/jayanez/agent-braid/issues/278, SPEC-028/T004 https://github.com/jayanez/agent-braid/issues/279, SPEC-028/T005 https://github.com/jayanez/agent-braid/issues/280, SPEC-028/T006 https://github.com/jayanez/agent-braid/issues/281, SPEC-028/T007 https://github.com/jayanez/agent-braid/issues/282, SPEC-028/T008 https://github.com/jayanez/agent-braid/issues/283.

No exact DDP key exists in the inspected receipt. Local absence is not proof of remote absence; before any future authorized publish, search exact marker/title and extension tasks in current tracking, then update an existing issue if semantically equivalent. This chat did not inspect remote states. Do not publish automatically, bulk reconcile, close original issues or infer authority from historical publication authorization.

EUR 0; local CPU; no experiments, model runs, training, calibration, activation, remote writes or T025 edits.


## Refined scope and cost acceptance — 2026-10-20

Bind acquisition, IR and registry; verify complete offered plans then select stable eligible goal-reaching option or defer. Report technical refusal separately; preserve the declared decision deadline and any explicitly enclosing acquisition deadline.

Negative controls: No eligible plan, tie, duplicate/omitted option, stale snapshot/registry, unmet dependency, changed goal and exhausted budget; selected result has no probability or authority.

Closure/evidence: A local vertical-slice receipt from pinned source to verified decision, full per-option consequences and all negative controls. No model invocation.

See [budget boundary](../latency-and-budgets.md) and [whole-program scope](../program-map.md). This amendment governs any broader earlier deadline wording in this draft. The initial three T025 case preparations reported by coordinator at 8.5–15.1 seconds are preliminary; final results remain pending. No speedup or product deadline is asserted.
