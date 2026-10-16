# T005/T006: integrated paired policy rehearsal

This is the bounded **synthetic software phase** of SPEC-036/T005 and T006,
following the frozen evaluation in #530 and decision mapping in #531. Original
checkboxes, predecessors, prospective registration and acceptance criteria remain
pending. It does not repeat model/VM measurements or recover historical costs.

## Interfaces and execution boundary

`forecast_experiment.rehearse_frozen_policy_arms` delegates to
`forecast_pairs.rehearse_paired_policies`. Inputs are the exact synthetic recipes,
evaluation, frozen policy and complete decision report from #531, plus caller-owned
grant fixtures. The report is recomputed and compared using exact JSON digests
before any arm is rehearsed. Later labels are never forwarded to the executor;
the executor consumes only frozen decisions and candidate manifests.

The implementation has an in-memory executor only. There is no executor callback,
subprocess, directory creation, worker, Docker, VM, model, or runtime execution.
The older `paired_synthetic_episode` measured Git harness is unchanged. Its
placeholder plans, serial baseline and historical costs are **not** upgraded into
registered experimental evidence by this new entry point.

`synthetic_grant_fixtures(report)` creates simulation-only tokens for the caller.
These are not independent operator grants. At use, each token must exactly match
the decision, arm, episode and plan; omission, copying, re-signing altered fields,
or setting execution authorization refuses that arm before execution phases.
These checks rehearse the boundary but do not establish real grant acceptance.
Actual grants and runtime plan validation remain external and pending.

Each origin retains all three intended arms: serial, the independently selected
non-model reference, and the forecast choice. Actions and plan identities come
from the frozen report, including shadow disagreement and fallback. Existing
candidate admission, causal splits and economic mapper tests are reused, not
reimplemented. The result records forecast status and advice reasons explicitly.

Treatment order is a deterministic rotation of the arm roster using the supplied
seed and origin index, fixed before outcomes. Three consecutive origins balance
each arm across all positions. This is a simulation convention, not a reviewed
real-experiment randomization/registration. Each arm gets a distinct logical
scope digest; these are not fresh physical run directories or verified isolation.

## Faults, results and costs

The finite fixture fault vocabulary is timeout, cancellation and verification
mismatch. These are simulated state transitions, not signals or live failures.
A cancellation stops the remaining arms of that origin, retaining them as
`not-run-after-cancellation`; later origins remain visible. Other failed/refused
arms do not disappear. Every such origin stays inconclusive in the summary.
Cleanup and export phases are retained after an attempted arm fails.

Each row says `executionKind: in-memory-fixture`. A simulated result digest
asserts the shared canonical fixture manifest: serial and parallel candidate
plans share that manifest. Verification compares the simulated produced value
against that fixture assertion, including a corruption control. This is not Git
effect acquisition, runtime enabledness, actual result-tree verification,
observational equivalence or evidence of confluence (Constitution Articles 2–7).

The ledger uses one **synthetic tick** per reached phase. Intervals are contiguous
and sum exactly from simulated data preparation through cleanup/export. It
rehearses inclusion and reconciliation only; ticks are neither nanoseconds nor
CPU/memory measurements and do not estimate deployment cost or utility. Rejected
decisions have no attempted phases. Missing full deployment costs stay null with
`not-measured-no-runtime-executed`; no provisioning, cold/resident cost, historical
gap or FC.2/T007 criterion is silently satisfied.

`validate_paired_rehearsal` recomputes the entire receipt from the same inputs and
controls. Re-signing a changed ledger, roster or result does not validate it.
Checksums and fixture tokens provide no approval or dispatch authority.

## Validation and remaining obligations

The focused unittest module is `tests/test_forecast_pairs.py`. It covers balanced
order and complete rosters, frozen reference/choice parity, distinct logical
scopes, shadow disagreement, unavailable-forecast fallback, already-refused
unknown-effect decisions, bad grants, expiry boundary, timeout, cancellation,
result corruption, clean replay and exact JSON receipt binding. The retained
receipt is [evidence/t005-t006-paired-rehearsal.json](evidence/t005-t006-paired-rehearsal.json).
Technical review is by Luna Latest; review provenance is separate from owner or
scientific acceptance. The evidence records only checks actually obtained.

Outputs retain `executionAuthorization=false`, `utilityAccepted=false` and
`realWorkloadEvidence=false`. No CLI/MCP/root exports, existing versioned runtime
contracts, grants, default-off behavior or historical assurance are changed.

Still pending for original T005/T006: actual reviewed measurement-contract
integration; independently granted, fresh owned physical run directories;
registered order and complete observed deployment costs; runtime authority,
enabledness, failure/recovery and verifier evidence in the admitted domain.
SPEC-034/T005 and FC.2/T007 remain `not_planned` with unmet original criteria.
Their cancellation does not satisfy downstream predecessors. Source/resource/
model admission, real launch, interpretation, ADR, bridge and promotion remain
separate pending gates. This document and its tests do not close those tasks.
