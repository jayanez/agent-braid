# [SPEC-031][DDP-T03] Extract bounded observed-effect acquisition

<!-- dedup-key: jayanez/agent-braid:system-one-decision-delivery:DDP-T03:v1 -->
Status: draft, never remote-created. Target repository: https://github.com/jayanez/agent-braid (local origin verified). Proposed parent: https://github.com/jayanez/agent-braid/issues/303. Milestone: S1.3. No new remote issue number allocated.

## Scope and acceptance

DDP-REQ-03 / DDP-SC-03; maps to SPEC-031/REQ-002, SPEC-029/REQ-005.

Extract read-only pinned source acquisition into the frozen snapshot envelope. Reuse current local Git helpers without editing them; keep declaration/observation channels.

- [ ] Pinned local fixture source/hash manifest, scratch cleanup receipt and no-write assertions; no corpus study.
- [ ] Negative controls: Source drift, path escape, wrong revision, non-LF/binary/missing-newline, unsupported mode/rename, incomplete effects and deadline exhaustion refuse; source refs/files remain identical.
- [ ] Compatibility, source immutability and no authority escalation retained.

## Assignment and dependencies

Owner: agent-B. Dependency keys: DDP-T01. State: prepared-conditional. Parent T025 result is not assumed complete. No agent is assigned/launched by this draft.

Owned files:

- `agent_braid/system_one_verified_acquisition.py`
- `tests/test_system_one_verified_acquisition.py`

## Verification and evidence

Use focused standard-library unittest modules named by owned tests after implementation, then coordinator validate_change quick/pr under repository policy. No checks were executed by this draft.

Required receipt: candidate/source/contract hashes, actual commands and exit status, environment, input fixture identities, raw logs, observed negative outcomes, changed-file list, limitations and unresolved findings. A test plan is not obtained evidence. Pinned local fixture source/hash manifest, scratch cleanup receipt and no-write assertions; no corpus study.

## Deduplication and boundary

The local 55-issue receipt and original task snapshot were reviewed. Original parent and task issues are retained. This is a proposed extraction/robustening supplement, not another implementation of the old task. Related original identities: SPEC-031/T001 https://github.com/jayanez/agent-braid/issues/304, SPEC-031/T002 https://github.com/jayanez/agent-braid/issues/305, SPEC-031/T003 https://github.com/jayanez/agent-braid/issues/306, SPEC-031/T004 https://github.com/jayanez/agent-braid/issues/307, SPEC-031/T005 https://github.com/jayanez/agent-braid/issues/308, SPEC-031/T006 https://github.com/jayanez/agent-braid/issues/309, SPEC-031/T007 https://github.com/jayanez/agent-braid/issues/310, SPEC-031/T008 https://github.com/jayanez/agent-braid/issues/311.

No exact DDP key exists in the inspected receipt. Local absence is not proof of remote absence; before any future authorized publish, search exact marker/title and extension tasks in current tracking, then update an existing issue if semantically equivalent. This chat did not inspect remote states. Do not publish automatically, bulk reconcile, close original issues or infer authority from historical publication authorization.

EUR 0; local CPU; no experiments, model runs, training, calibration, activation, remote writes or T025 edits.
