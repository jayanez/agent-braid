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
- **Not done here:** the held-out final run, done later (see the held-out section below).

## T008 guidance rewrite, development-set re-run (2026-11-12)

Skill (`agent-braid-analyze`), `analyze-work` tool description and the git source refusal text were rewritten; a drift test
(`tests/test_spec069_guidance.py`) sends every annotated skill example through the real tool and checks the documented
classification, with negative controls. Same driver and arm (`final`, per-kind schema delivery), development set only, 10 prompts
x 3 repetitions per host, final source commit `731e238e`. The held-out set was not opened or run (D9). Tuning used only
development-set results, over seven rounds; the table is the last round on the exact shipped text.

| Host | Before (T010 `final`) | After, first attempt | After, within one retry | Prompts first/retry (of 10) | Verdict |
| --- | --- | --- | --- | --- | --- |
| Claude Code | 12/30 (0.25-0.58) | 28/30 (0.79-0.98) | 28/30 (0.79-0.98) | 8 / 8 (misses DEV-02, DEV-03) | misses |
| OpenCode | 16/30 (0.36-0.70) | 30/30 (0.89-1.00) | 30/30 (0.89-1.00) | 10 / 10 | meets |
| Codex | 9/30 (0.17-0.48) | 27/30 (0.74-0.97) | 27/30 (0.74-0.97) | 8 / 8 (misses DEV-01, DEV-04) | misses |

- **D4 reachability:** the pooled trial rate is above 8/10 on all three hosts; OpenCode meets the per-prompt criterion. Claude
  Code and Codex each miss two prompts (every repetition must be valid for a prompt to count), so D4 is not yet met on the
  development set. Remaining failures are non-systematic: `units` used for a parallelism question (valid call, classification
  `unknown`), the tool not called at all (Claude Code DEV-03 once), and an `aim` record the scorer rejects. Accepted calls are final
  (no retry credit), so within-retry equals first attempt. The gap looks like host variance over three repetitions, not a
  guidance defect, but this is unproven until the T010 held-out run.
- **Scoring change (frozen file, new FREEZE record):** `scripts/spec069_scoring.py` now accepts an accepted `units` call as the
  simple form of an `aim` case, with the same per-unit resource and dependency checks. `units` still never earns
  `independent-candidate` (coverage is always partial), so a case that expects that result stays unmet by `units`. Re-scoring the
  T010 evidence with this rule moves Codex `final` 9 to 15 and Claude Code `final` 12 to 13, so most of Codex's earlier misses
  were a scoring gap, not authoring errors. Negative controls in `tests/test_spec069_scoring.py`.
- **Spec deviation (REQ-008 "prefer units"):** the skill now routes parallelism or overlap questions to `aim` (the only kind that
  can report `independent-candidate`) and keeps `units` for conflict and ordering checks. Needs an owner decision to adopt
  formally; no contract changed.
- **Tuning iterations (first attempt, of 30; development set):** Claude Code 26, 24, 22, 30, 29, 30 (before the last wording
  trim), final 28; OpenCode 30, 30, 29, 30, 30, 30, final 30; Codex 9 (T010), 22 in round 5 (earlier description), final 27.
  Intermediate evidence files are not shipped. The run before this one for Codex (22/30) is in history at commit `11594ec9`.
- **Access paths unchanged:** Claude Code by subscription token, OpenCode by OpenRouter, Codex by subscription sign-in; Codex hit
  the usage limit once during tuning and was re-run after the reset.
- **D12:** compact `analyze-work` definition stays at or below 1500 tokens (test enforced).
- **Spend:** a few USD notional across the seven rounds; far below the 60 USD cap.
- **Not done here:** the held-out final run (T010); it was run afterwards, see the section below. T008 closed with accepted deviation (below).

## T010 held-out final run (2026-11-12)

Held-out set `spec069-held-out-v1` (10 prompts, frozen before the T008 rewrite, never opened by the T008 or T010 run sessions), arm
`final` (per-kind schema delivery) on source commit `f3648396` (clean checkout, includes the T008 guidance), 3 repetitions per prompt,
one run, no iteration afterwards. Same access paths as the development runs: Claude Code `claude-sonnet-5-5` by subscription token,
OpenCode `openrouter/anthropic/claude-sonnet-5-5` by OpenRouter, Codex on its host default model by subscription sign-in. Evidence:
`evidence/native-runs-t010-heldout-final.json` (Claude Code, OpenCode) and `evidence/native-runs-t010-heldout-final-codex.json`
(Codex), with redacted transcripts. All hosts ran, driver exit 0, teardown clean, secret scan passed. No driver or infrastructure failure,
so no case was re-run.

| Host | First attempt (trials, Wilson 95%) | Within one retry | Prompts first / retry (of 10) | Missed prompts | D4 verdict |
| --- | --- | --- | --- | --- | --- |
| Claude Code | 27/30 (0.74-0.97) | 27/30 (0.74-0.97) | 9 / 9 | HELD-04 | misses (first attempt meets 8/10; retry criterion 10/10 not met) |
| OpenCode | 27/30 (0.74-0.97) | 27/30 (0.74-0.97) | 9 / 9 | HELD-04 | misses (same) |
| Codex | 24/30 (0.63-0.90) | 24/30 (0.63-0.90) | 7 / 7 | HELD-02, HELD-04, HELD-05 | misses (first attempt and retry) |

- **Result:** D4 is not met on the held-out set in any host. Claude Code and OpenCode reach the first-attempt threshold (9 of 10 prompts)
  but D4 also needs 10/10 within one retry; accepted calls are final (no retry credit), so a wrong accepted call cannot be recovered.
  Codex reaches 7 of 10 prompts. Negative result, reported as observed.
- **Failure pattern (observed, not acted on):** HELD-04 fails in all 9 trials of all three hosts with the same signature: the models
  declare an extra `read src/db.py` in the unit that writes `docs/api.md`, where the scorer expects only a write. Whether this is a
  guidance gap or an ambiguity in the prompt or the scoring rule is not established here; the held-out set and scoring are frozen and
  were not changed. Codex also failed HELD-05 twice (constraint set differs from expectation: a validate-read-versions-at-use
  constraint is reported) and HELD-02 once (tool not called). Generalisation from development (28/30, 30/30, 27/30) to held-out
  (27/30, 27/30, 24/30) is a drop of 1, 3 and 3 trials; the intervals overlap.
- **Not run on the held-out set:** the `final-no-schema` ablation arm (the D9 ablation stays on the development set) and a
  baseline-arm held-out run.
- **Spend:** Claude Code 1.87 USD notional (subscription token); OpenCode via OpenRouter and Codex on the subscription report no cost.
  Cumulative with earlier T010/T008 rounds: well below the 60 USD cap.
- **Owner decision 2026-11-12 ("Aceptar desviación"):** the D4 shortfall is accepted as a documented deviation from REQ-010 and REQ-008, with
  the numbers above and the HELD-04 pattern as the stated limit. D4 is not met and is not claimed as met. T010 and T008 are closed with this
  deviation. The held-out set is consumed; any new guidance round needs a new, unseen held-out set and a new FREEZE record. The
  `final-no-schema` ablation was not run on the held-out set.

## T005 native host probe of the analyze-work schema (2026-11-13)

`python -m scripts.spec069_native_runs --probe-schema --arm final|final-no-schema`: same sandbox, access paths, redaction,
secret scan and teardown as the T010 runs. In each disposable installed copy, `launch` becomes `launch.real` behind a wrapper
that runs `scripts/spec069_stdio_proxy.py --keep-listing` for `plugin serve` only; one receipt per connection records the
negotiated protocol version, the raw `tools/list` line (saved next to the transcript) with its SHA-256, canonical hashes and,
for every `analyze-work` call, the `kind` and whether `request` was an object. One prompt per host asked for an `aim` call with
`examples/analysis/file-edits.json` and a `units` call (two units writing `README.md`). Models as in T010: `claude-sonnet-5-5`
(Claude Code by subscription token; OpenCode through OpenRouter), Codex default model by subscription sign-in. Per-kind arm =
committed build `62f83ff5`; description-only arm = the same commit with only the request schema regenerated (`sourceDirty:
true`, schema module SHA-256 `aa3afa4a...`).

| Host (protocol version) | Arm | Exposed | `aim` / `units` request at server | Served content = fingerprint | Loading |
| --- | --- | --- | --- | --- | --- |
| Claude Code 2.1.311 (2026-07-28, `server/discover`) | per-kind | yes (init list) | object / object | yes | deferred (ToolSearch first) |
| Claude Code 2.1.311 (2026-07-28) | description-only | yes | object / object | yes | deferred |
| Codex 0.167.0-alpha.4.1 (2025-06-18) | per-kind | yes (no `Failed to convert`) | object / object | yes | eager |
| Codex 0.167.0-alpha.4.1 (2025-06-18) | description-only | yes | object / object | yes | eager |
| OpenCode 2.1.4 (2025-11-25) | per-kind | yes | object / object | yes | eager, after the `execute` helper |
| OpenCode 2.1.4 (2025-11-25) | description-only | yes | object / object | yes | eager, after the `execute` helper |

- **Verdict:** procedure_005 passes (`evidence/procedure_005.json`, `native.passed: true`). No host hid or stringified the
  nested per-kind form, so no description-only fallback is declared for any host.
- **Byte identity:** the full `analyze-work` definition has one canonical hash per arm in every protocol version
  (per-kind `7f561415...`, description-only `607609df...`); the model-facing part (name, description, inputSchema, sorted keys)
  equals the fingerprint from `listed_sizes()` in every connection. The server's key order differs by protocol version (2025-06-18
  and 2025-11-25 against 2026-07-28), so raw lines and unsorted hashes differ across versions while content does not.
- **Limits:** one session per host and arm (observation, not a sample). Claude Code and Codex end the server with a signal, so
  their receipts are marked incomplete (`relay_failure`) after the listing and calls were recorded. Loading is read from the order
  of calls in the transcript. The Codex transcripts contain the local sign-in directory path in the `plugin-status` output, as in
  the T010 evidence. Claude Code 2.1.311 opens with `server/discover` instead of `initialize`; the relay now records its version.
- **Spend:** Claude Code 0.38 USD notional (subscription token: two development probes plus the two shipped runs); OpenCode via
  OpenRouter and Codex on the subscription report no cost. Cumulative SPEC-069 spend stays well below the 60 USD cap.

## T011 documentation check (2026-11-13)

`python -m unittest tests.test_spec069_docs tests.test_spec069_guidance` (21 tests, OK; `evidence/procedure_011.json`).
`tests/test_spec069_docs.py` reads the section "`analyze-work` request kinds (SPEC-069, unreleased)" of
`docs/tooling/NATIVE_PLUGINS.md` and checks:

- every relative link and anchor in the whole file resolves;
- every cited test, script or evidence path exists;
- the documented kinds equal the served enum;
- the held-out table equals the T010 evidence, and the claims about retries and D4 follow it;
- probe host versions and loading modes follow `procedure_005.json` `native`;
- the replay counts (103 and 214) follow `procedure_009.json`;
- the rollback refusal equals `compatibility.md`.

Negative controls detect a broken link or anchor, a changed number and a missing cited file. The other behavioural
statements were reviewed against the contract and the tests they cite; that part is a review, not a mechanical check.
The release-note draft is text only: no version bump, tag, publication or `plugin-dist` push (T012, owner's explicit yes).
