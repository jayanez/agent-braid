# SPEC-069: Validation plan

Status (2026-11-05, draft): no procedure has obtained evidence. Deterministic
procedures run in CI and locally with `.venv-speckit/bin/python -m unittest …`.
Native procedures run only through the automated driver of REQ-013 in disposable
profiles; no procedure requires pasting prompts or answers by hand. Passing
deterministic procedures does not establish native behaviour; that is
procedure_010.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | `speckit-analyze` report, ADR 0038, `contracts/analyze-work-request.md` | requirements, tasks and procedures agree; unchanged contracts listed | missing gate; contract change not listed |
| procedure_002 | SC-002 | `evidence/divergence-inventory.json` produced by the inventory script | every schema keyword and validator check enumerated; every divergence has input, both verdicts, decision | any of the three 2026-11-05 divergences absent; adapter bounds missing; a row resolved by deleting a case |
| procedure_003 | SC-003 | envelope schema test over `examples/analysis/` and corpus | schema verdict equals runtime verdict | envelope with extra field accepted; empty `operations` accepted |
| procedure_004 | SC-004 | differential corpus test (`tests/test_spec069_differential.py`, planned) | equal verdicts on structural cases; recorded runtime refusal on batch cases | relax one schema keyword; relax one validator check; each must fail |
| procedure_005 | SC-005 | plugin `list_tools` unit test + recording stdio proxy per host + named-tokenizer size | top level plain object; per-kind schemas inside `request`; every tool listed; bytes identical per host connection; size under cap; host acceptance recorded | top-level `oneOf` (must fail); size over cap; schema drift from published file |
| procedure_006 | SC-006 | `units` construction tests + golden fixtures | constructed AIM equals golden bytes, replay identical, `conflicting` + `serialize-or-isolate`, coverage `partial` | `./README.md` alias; claimed `complete`; disjoint units never `independent-candidate`; `..`/absolute/case-only paths; 33 units; 257-byte id; duplicate id; unknown dependency; unsupported kind |
| procedure_007 | SC-007 | refusal tests through the MCP service | structural: pointer + expected form; semantic: fixed code; ≤1024 chars; no request values | secret-shaped unknown key echoed; git path unmasked; missing vs outside path distinguishable |
| procedure_008 | SC-008 | drift test over skill, tool description, examples, docs | every embedded request validates and analyzes as documented | renamed schema field without guidance update |
| procedure_009 | SC-009 | replay of alpha.7-accepted requests | byte-identical report (except the REQ-015 label); schema notes list tightened keywords | any new runtime refusal; changed report bytes |
| procedure_010 | SC-010 | `evidence/native-runs.json` written by the driver, scored by pre-fixed rules | baseline (P2) and final runs; three repetitions; held-out set; ablation arm; per host ≥8/10 first attempt and 10/10 within one retry; intervals reported | tool not called counted as valid; empty declaration counted as valid; inferred observation; shortfall hidden |
| procedure_011 | SC-011 | documentation checks + review | statements backed by tests or observations; links resolve | unobserved behaviour claimed |
| procedure_012 | SC-012 | release record and owner authorization | publication only after recorded explicit yes; package equals candidate | publish without yes; #1080 closed before evidence |
| procedure_013 | SC-013 | driver run (`scripts/spec069_native_runs.py`, planned) + `--fake-hosts` self-test in CI | unattended completion; tools allowlisted; OS sandbox denies real config; evidence redacted and hashed; clean teardown; manual-step list matches | leaked real path stopped; planted secret absent from evidence; denied tool refused; leftover profile or process detected |
| procedure_014 | SC-014 | telemetry and shadow tests for `units`; normalization tests in macOS and Linux CI | defined outcome key per request; no swallowed exception | `units` request with no telemetry record |
| procedure_015 | SC-015 | report label tests | declared-only `independent-candidate` labelled; other fields byte-identical to alpha.7 | label present with `replay` evidence; classification changed |

Repository validation for every change: `quick` after an increment; the CI
`validate` aggregate on the PR head is the `pr`-profile evidence. Native runs
are a separate boundary command and are never inferred from CI.
