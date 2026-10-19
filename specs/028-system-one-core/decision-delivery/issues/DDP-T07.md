# [SPEC-029][DDP-T07] Verify integrated compatibility and adversarial boundaries

<!-- dedup-key: jayanez/agent-braid:system-one-decision-delivery:DDP-T07:v1 -->
Status: draft, never remote-created. Target repository: https://github.com/jayanez/agent-braid (local origin verified). Proposed parent: https://github.com/jayanez/agent-braid/issues/284. Milestone: S1.1. No new remote issue number allocated.

## Scope and acceptance

DDP-REQ-07 / DDP-SC-07; maps to SPEC-029/REQ-005, SPEC-029/REQ-006, SPEC-028/REQ-006.

Independently test old defaults/new opt-in and adversarial boundary coverage; coordinator runs required validation profiles on stable candidate. Review agent launch needs separate authorization and Luna Latest.

- [ ] Focused tests plus quick during work and pr once stable with exact commands/SHA/environment/skips; findings resolved or explicit blockers. Luna review pending until actually authorized/performed.
- [ ] Negative controls: Changed old stdlib response, neural module load on core import, unsupported input accepted, omitted evidence chunk, forged authorization and non-cleaned scratch fail the suite.
- [ ] Compatibility, source immutability and no authority escalation retained.

## Assignment and dependencies

Owner: agent-C / later Luna reviewer. Dependency keys: DDP-T06. State: prepared-conditional. Parent T025 result is not assumed complete. No agent is assigned/launched by this draft.

Owned files:

- `tests/test_system_one_verified_compatibility.py`
- `specs/029-system-one-evaluation/evidence/decision-delivery/software-validation.json`

## Verification and evidence

Use focused standard-library unittest modules named by owned tests after implementation, then coordinator validate_change quick/pr under repository policy. No checks were executed by this draft.

Required receipt: candidate/source/contract hashes, actual commands and exit status, environment, input fixture identities, raw logs, observed negative outcomes, changed-file list, limitations and unresolved findings. A test plan is not obtained evidence. Focused tests plus quick during work and pr once stable with exact commands/SHA/environment/skips; findings resolved or explicit blockers. Luna review pending until actually authorized/performed.

## Deduplication and boundary

The local 55-issue receipt and original task snapshot were reviewed. Original parent and task issues are retained. This is a proposed extraction/robustening supplement, not another implementation of the old task. Related original identities: SPEC-029/T001 https://github.com/jayanez/agent-braid/issues/285, SPEC-029/T002 https://github.com/jayanez/agent-braid/issues/286, SPEC-029/T003 https://github.com/jayanez/agent-braid/issues/287, SPEC-029/T004 https://github.com/jayanez/agent-braid/issues/288, SPEC-029/T005 https://github.com/jayanez/agent-braid/issues/289, SPEC-029/T006 https://github.com/jayanez/agent-braid/issues/290, SPEC-029/T007 https://github.com/jayanez/agent-braid/issues/291, SPEC-029/T008 https://github.com/jayanez/agent-braid/issues/292, SPEC-029/T009 https://github.com/jayanez/agent-braid/issues/293.

No exact DDP key exists in the inspected receipt. Local absence is not proof of remote absence; before any future authorized publish, search exact marker/title and extension tasks in current tracking, then update an existing issue if semantically equivalent. This chat did not inspect remote states. Do not publish automatically, bulk reconcile, close original issues or infer authority from historical publication authorization.

EUR 0; local CPU; no experiments, model runs, training, calibration, activation, remote writes or T025 edits.
