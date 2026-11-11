# SPEC-069: Validation plan

Status (2026-11-06, draft): procedures 002, 003, 004, 007, 009 and 015 have
obtained local evidence (`evidence/procedure_*.json`, written by
`scripts/spec069_capture_p1_evidence.py`; CI `validate` on each pull request is the
`pr`-profile evidence). Procedure 001 has the owner's review record
(`reviews/owner-t001-adr-contract-20261107.md`); procedure 013 has obtained evidence (driver self-test and real runs on two hosts; Codex a declared limit); procedures 005, 006, 008, 010, 011, 012, 014 have none. Deterministic
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

## T010 development-set ablation and Codex baseline (2026-11-11)

Driver runs, development set (10 prompts x 3 repetitions per host and arm), pinned `claude-sonnet-5-5` for Claude Code
(subscription token) and OpenCode (via OpenRouter); Codex on its host default model `gpt-6.1-sol` (read from the disposable
Codex session logs; the Codex stream does not name the model) with the owner's subscription sign-in. The held-out set was not run.
First-attempt valid trials (Wilson 95% interval) and valid within one refusal-guided retry:

| Host | Arm | First attempt | Within one retry | Prompts first/retry (of 10) |
| --- | --- | --- | --- | --- |
| Claude Code | baseline, API key (earlier evidence) | 16/30 (0.36-0.70) | 16/30 | 4 / 4 |
| Claude Code | `final` | 12/30 (0.25-0.58) | 15/30 (0.33-0.67) | 2 / 3 |
| Claude Code | `final-no-schema` | 17/30 (0.39-0.73) | 17/30 | 5 / 5 |
| OpenCode | baseline, direct API (earlier evidence) | 16/30 (0.36-0.70) | 16/30 | 5 / 5 |
| OpenCode | `final` (OpenRouter) | 16/30 (0.36-0.70) | 16/30 | 5 / 5 |
| OpenCode | `final-no-schema` (OpenRouter) | 16/30 (0.36-0.70) | 16/30 | 5 / 5 |
| Codex | baseline | 0/30 (0.00-0.11) | 0/30 | 0 / 0 |
| Codex | `final` | 9/30 (0.17-0.48) | 9/30 | 3 / 3 |
| Codex | `final-no-schema` | 0/30 (0.00-0.11) | 0/30 | 0 / 0 |

- **D9 ablation rule:** schema delivery improves first-attempt validity in at least one host (Codex, 0/30 to 9/30,
  non-overlapping intervals). It does not in OpenCode (equal) and is nominally worse in Claude Code (12/30 against 17/30,
  overlapping intervals). Every host-arm still misses the D4 threshold (8/10 prompts first attempt): negative results, reported as observed.
- Codex failures are request-shape errors, not missing calls: it calls `analyze-work` (92 calls in the baseline) with invalid
  shapes (definition digest, git `source`, `readVersions`), and in `final` it sends `units` where `aim` was expected in 20 trials
  ("accepted but wrong, so no retry is credited").
- **Access paths:** Claude Code runs by subscription token (`auth: oauth-token-env`, cost reported is notional); OpenCode by
  OpenRouter (`route: openrouter`, no cost reported); the earlier baseline used the direct API. The Anthropic-baseline comparison
  across paths is therefore indicative only (runbook, comparability).
- **Declared limits and driver fixes:** a first Codex pass was invalid (the plugin server did not see the registered workspace;
  fixed by registering at the default state root under `HOME`), and a second stopped on Codex's read-only MCP resource listing
  (now a discovery helper). Both fixes are committed with tests; the invalid evidence is not shipped. The re-run of the Codex
  `final-no-schema` arm hit the ChatGPT usage limit (until 2026-11-12 01:59); the shipped `final-no-schema` Codex evidence is the
  earlier complete run on source commit `2a74fe3d`, which differs from the other Codex arms only by the helper classification
  (same driver hash, same plugin build inputs).
- **Spend:** about 3.8 USD notional on Claude Code (plus 0.09 smoke), OpenRouter runs a few tenths of a dollar by the earlier
  per-run price (cost not reported), Codex on the subscription: far below the 60 USD cap.
- **Not done:** the held-out final run, so T010 stays open.
