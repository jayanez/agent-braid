# SPEC-071: Validation plan

Status (2026-11-08, draft): no procedure has obtained evidence. Deterministic
procedures run in CI and locally with targeted `.venv-speckit/bin/python -m
unittest tests.<module>` runs. The real baseline (procedure_014) runs only
through the runner on the subscription route. Passing deterministic procedures
does not establish native behaviour.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record bound to a commit | spec, plan, contracts reviewed; OD-1 recorded as open or decided | review without a commit |
| procedure_002 | SC-002 | existing SPEC-069 driver tests and before/after fake-run evidence | tests pass; evidence bytes identical | changed parser output detected |
| procedure_003 | SC-003 | `tests/test_lightning_runner.py` (planned) | timeout kills the tree; at most `parallel` concurrent; states follow SPEC-070 | straggler process; invalid transition |
| procedure_004 | SC-004 | environment gate tests | `paid-route-refused` before launch; `keySource` recorded; `oauth` accepted | `FOO_API_KEY`, `ANTHROPIC_BASE_URL`, key source `apiKey`, missing `apiKeySource` each refused |
| procedure_005 | SC-005 | secret scan over the run directory | synthetic token absent from all files; `credentialPresent` true | token planted in a transcript is caught |
| procedure_006 | SC-006 | budget stop tests | stop name in `_BUDGET_STOPS`; run ends; same run id resumes only with `--resume <run-id>` | unknown stop name refused; automatic resume refused |
| procedure_007 | SC-007 | hook tests | upstream order; an exception fails the rollout only | hook mutating a record refused |
| procedure_008 | SC-008 | reward tests over SPEC-069 fixtures | vector matches `score_case`; deterministic; no model call | changed scoring hash refused; uncalled tool scored valid |
| procedure_009 | SC-009 | isolation and canary tests | `.git` unreadable; egress denied; canary hit zeroes D4 | planted canary read; held-out hash mismatch |
| procedure_010 | SC-010 | CLI tests | dry-run launches nothing; fake-hosts labelled `pipeline-only`; report has intervals | dry-run spawning a process |
| procedure_011 | SC-011 | replay test | reward recomputed from stored parsed attempts is byte-identical | edited parsed attempt changes the hash; transcript replay without consent refused |
| procedure_012 | SC-012 | boundary tests (imports, sockets, MCP tool list) | no execute path, no listener, no new dependency | import of a non-stdlib module |
| procedure_013 | SC-013 | `tests/test_lightning_pipeline.py` (planned) in CI | full fake pipeline passes | each negative variant yields its code |
| procedure_014 | SC-014 | real baseline evidence | both proportions, Wilson intervals and route/model/version differences, labelled `route-changed comparison`; zero paid-route observations | API key present; outside interval reported as a difference |

Repository validation for every change: `quick` after an increment; the CI
`validate` aggregate on the PR head is the `pr`-profile evidence.
