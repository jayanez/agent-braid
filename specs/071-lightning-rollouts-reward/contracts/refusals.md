# Contract: BL.1 refusal and stop codes

Closed vocabulary. Messages carry the code and a fixed sentence, never
environment values or secrets.

| Code | Raised when | Effect |
|---|---|---|
| `paid-route-refused` | child environment has a `*_API_KEY` or a denied variable (REQ-004) | run not started |
| `route-unverified` | host key source missing or outside `SUBSCRIPTION_KEY_SOURCES` | rollout failed, run stopped |
| `credential-leak` | a registered secret appears in any output | run stopped, artifact not written |
| `isolation-failed` | `probe_isolation` reads a protected path or the canary | run not started |
| `canary-hit` | canary token seen in a rollout | rollout recorded, D4 zeroed |
| `holdout-hash-mismatch` | held-out file hash differs from FREEZE | run not started |
| `scoring-hash-mismatch` | scoring file hash differs from FREEZE | reward refused |
| `rollout-timeout` | `rollout.timeoutSeconds` exceeded | tree killed, rollout failed |
| `straggler-process` | process left after teardown | run stopped |
| `hook-failed` | a hook raised | rollout failed |
| `unit-cap`, `five-hour-headroom`, `weekly-stop`, `window-reset`, `window-reset-imminent` | budget stops (names from `harness_hosts._BUDGET_STOPS`) | run stopped, resumable by new command |
| `config-*` | configuration refusals of SPEC-070 | run not started |
