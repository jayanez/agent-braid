# SPEC-048 T009 deterministic integration controls

Scope: `tests/test_harness_integration.py`. Every probe crosses the real boundaries in order:
operator-scoped admission and reservation (T004), bounded candidate import (T003), durable
journal start and terminal record (T007), a real fixture child process (T005), normalized
observation (T012), an independent test-side oracle, and the one-round selection (T006). The
decision is then passed through the record codec and the `harness inspect` command (T015).

**Deterministic success is not native qualification.** The backend is `SimulatedContainment`:
it bounds and settles the child but confines nothing. No host, model, provider, network, paid
route or native containment is involved; all manifests carry zero native/model/network/cash
limits and every produced record has `executionAuthorization: false`.

## Fixtures and oracles

| Fixture | Behaviour driven by candidate guidance | Independent oracle |
|---|---|---|
| task continuity | `resume-from-handoff` skips steps listed in a handoff taken from a reconciled journal attempt; otherwise the fixture redoes them | score = 1,000,000 − 400,000 per handed-off step redone, 0 if the last step is missing |
| coordination | `claim-by-owner` makes each worker write its own file; otherwise both write one shared file | score = 500,000 per distinct output − 250,000 per file written by more than one worker |

## Control → test map

| Control | Tests |
|---|---|
| Baseline vs candidate, keep-base, determinism | `TaskContinuityTests.test_resume_guidance_beats_the_restart_baseline_without_duplicate_effects`, `CoordinationTests.*`, `BaselineControlTests.*` |
| Input contamination | `ContaminationTests.*` (instruction/secret injection in guidance, protected and escaping paths, tampered and unlisted candidate bytes, forged context headers) |
| Shared-resource aliasing | `AliasingTests.*` (aliased, nested, symlinked and colliding roots; destination reuse; reservation and admission reuse; attempt-id reuse; open attempt; workspace isolation) |
| Unavailable observations | `UnavailableObservationTests.*` (no terminal, sequence gap, escaping path, crash, unobserved base/candidate, refused base, expired evidence and purge) |
| Full cleanup accounting | `CleanupAccountingTests.*` and the per-test `tearDown` workspace check (timeout with a grandchild process, failed import after the claim, four-attempt ledger: 12 journal records, 4 reservations spent once, every result settled and cleaned) |
| Not native qualification | `NotNativeQualificationTests.*` |

## Limits

- Single host, single UID, offline. The simulated backend does not enforce filesystem, process,
  network or credential effects, so "no leak" assertions cover only what the harness observes.
- Oracles and fixtures are test code written for these controls; they establish engineering
  correctness of the pipeline, not utility, task success rates, or any native behaviour.
- Scores are synthetic; no statistical or economic claim.
