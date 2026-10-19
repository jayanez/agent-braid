# [SPEC-028][DDP-T04] Implement static domain verifier registry

<!-- dedup-key: jayanez/agent-braid:system-one-decision-delivery:DDP-T04:v1 -->
Status: draft, never remote-created. Target repository: https://github.com/jayanez/agent-braid (local origin verified). Proposed parent: https://github.com/jayanez/agent-braid/issues/275. Milestone: S1.0. No new remote issue number allocated.

## Scope and acceptance

DDP-REQ-04 / DDP-SC-04; maps to SPEC-028/REQ-005, SPEC-031/REQ-001.

Implement immutable allowlisted registry and dispatch validation against a stub data-only verifier result; defer concrete IR import to DDP-T05.

- [ ] Registry identity vectors and bounded negative dispatch tests; no general-domain support claim.
- [ ] Negative controls: Unknown domain/version/observation, forged digest, mutable entry and dynamic plugin/callable dispatch refuse; exact supported registration passes.
- [ ] Compatibility, source immutability and no authority escalation retained.

## Assignment and dependencies

Owner: agent-C. Dependency keys: DDP-T01. State: prepared-conditional. Parent T025 result is not assumed complete. No agent is assigned/launched by this draft.

Owned files:

- `agent_braid/system_one_verified_registry.py`
- `tests/test_system_one_verified_registry.py`

## Verification and evidence

Use focused standard-library unittest modules named by owned tests after implementation, then coordinator validate_change quick/pr under repository policy. No checks were executed by this draft.

Required receipt: candidate/source/contract hashes, actual commands and exit status, environment, input fixture identities, raw logs, observed negative outcomes, changed-file list, limitations and unresolved findings. A test plan is not obtained evidence. Registry identity vectors and bounded negative dispatch tests; no general-domain support claim.

## Deduplication and boundary

The local 55-issue receipt and original task snapshot were reviewed. Original parent and task issues are retained. This is a proposed extraction/robustening supplement, not another implementation of the old task. Related original identities: SPEC-028/T001 https://github.com/jayanez/agent-braid/issues/276, SPEC-028/T002 https://github.com/jayanez/agent-braid/issues/277, SPEC-028/T003 https://github.com/jayanez/agent-braid/issues/278, SPEC-028/T004 https://github.com/jayanez/agent-braid/issues/279, SPEC-028/T005 https://github.com/jayanez/agent-braid/issues/280, SPEC-028/T006 https://github.com/jayanez/agent-braid/issues/281, SPEC-028/T007 https://github.com/jayanez/agent-braid/issues/282, SPEC-028/T008 https://github.com/jayanez/agent-braid/issues/283.

No exact DDP key exists in the inspected receipt. Local absence is not proof of remote absence; before any future authorized publish, search exact marker/title and extension tasks in current tracking, then update an existing issue if semantically equivalent. This chat did not inspect remote states. Do not publish automatically, bulk reconcile, close original issues or infer authority from historical publication authorization.

EUR 0; local CPU; no experiments, model runs, training, calibration, activation, remote writes or T025 edits.
