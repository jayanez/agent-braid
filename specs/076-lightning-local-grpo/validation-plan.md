# SPEC-076: Validation plan

Status: deferred; no procedure has obtained evidence. Stdlib procedures use fake
backends in CI; GPU procedures run only in the isolated `lightning-gpu`
environment.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | founder decision record | go/no-go with evidence per criterion | go recorded with a criterion unmet |
| procedure_002 | SC-002 | proxy bind/token tests | non-loopback bind and missing token refused | 0.0.0.0 accepted |
| procedure_003 | SC-003 | fake backend tests | both fields forced; `token-ids-missing` recorded | response without token IDs accepted |
| procedure_004 | SC-004 | event tests with retries | correct rollout/attempt keys; replay matches | attempt mislabelled |
| procedure_005 | SC-005 | pause/resume tests | 503 + `Retry-After`; drain; resume | call accepted while paused |
| procedure_006 | SC-006 | import boundary, metadata | core imports no GPU package | `import torch` in core |
| procedure_007 | SC-007 | fake-GPU runner | clean start/stop; no k8s | orphan child process |
| procedure_008 | SC-008 | synthetic reward tests | GRPO/RLOO values match hand computation | token-mean loss weights |
| procedure_009 | SC-009 | token-ID merge tests | prefix merge; overlong counted | mismatched prefix merged |
| procedure_010 | SC-010 | filter tests | zero-variance groups dropped; cap respected | all-pass group kept |
| procedure_011 | SC-011 | async staleness tests | staleness ≤ bound | bound exceeded silently |
| procedure_012 | SC-012 | planted hack rollouts | blocked or detected, reward zero | `.git` readable |
| procedure_013 | SC-013 | System One import scan | no Lightning weight reference | planted reference detected |
| procedure_014 | SC-014 | review record | sourced figures; every retained key mapped | unsourced figure |
| procedure_015 | SC-015 | preregistered held-out evaluation; converge | intervals reported; null valid | held-out item in training set |
