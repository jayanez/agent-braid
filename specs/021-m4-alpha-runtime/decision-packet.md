# M4 alpha implementation review packet

G0 was approved on frozen 0de9d31 and canonical ADR 0020 adopted on 2026-10-04. Historical scope provenance is preserved in founder-review.json and accepted-assurance-0de9d31.json. SPEC-020 acceptance remains intact. M4 remains open.

## 1. Implemented scope

C1: verified policy pipeline and one-use operator grants outside model tools. C2: dependency-ready isolated preparation, fixed text patches only, exclusive serial coordinator publication, live effects and independent consumer verification. C3: pinned 2025-11-25 stdio MCP with analyze, prepare, status, execute, recover and verify; no grant-creation tool. Bounds, exclusions and observed-state semantics follow G1 and c2-execution-contract.md.

## 2. Candidate and actual checks

Implementation/capture candidate: implementation-equivalent source `9108a20`; current PR head `d46fc52`. Local sensitive profile passed 372 tests with four skips (three SPEC-019 deferred implementation, one unavailable private-history test). Fresh Darwin and hosted Linux checkout/process reproductions passed 61 alpha/core tests with no skips. Two independent gpt-6-luna implementation reviewers reported no findings; raw reports are retained. PR profile passed on preserved implementation-equivalent local candidate 41ee2b6: 368 passed, four explicitly audited skips. Record-only packaging checks remain separate; see c4-evidence/pr-validation.json and skip-audit.json.

## 3. Actual host evidence

Installed Codex 0.159.0-alpha.12.1 used its actual MCP tool bridge for all six tools, missing-grant refusal, verified interruption prefix, resume, read-only retry and abort. Actual Claude Code 2.1.236, authenticated through Claude.ai Max with usage credits disabled by operator confirmation, used a strict temporary MCP config on an owned fixture. It prepared and verified a plan, was refused for a missing grant, executed after a separate local grant, disconnected at the controlled prefix after operation `a`, resumed with a new grant, independently verified the completed expected tree, and did not redispatch the consumed grant. Incomplete tool arguments were safely rejected before the valid calls. The candidate and fixture source remained unchanged; no persistent host MCP configuration or API/provider fallback was used. Full transcript and provenance are in `host-evidence/claude.json`.

## 4. Measurement and limitations

Six paired two-edit trials, both admitted orders, yielded matching independently verified final trees in every pair. Median serial/parallel total wall ratio: 0.5581; outcome: negative-or-null-descriptive. Full evidence production, grants, rehearsal, verification and cleanup are included. Raw ratios and costs are in c4-evidence/measurement.json. This small descriptive corpus does not establish population benefit; overlap does not prove simultaneous CPU execution. Scratch is sampled; there is no hard child-memory cap or hostile same-UID isolation claim.

## 5. Remaining acceptance gates

T010 actual-host capture is complete. Final combined evidence/authority reconciliation (T013) and the separate founder whole-M4 decision plus governed tracking update (T014) remain open. G4 requires all six exit rows and an explicit utility go/no-go, including negative or inconclusive outcomes. No scientific, production or whole-M4 closure follows from these tests.

## 6. Approval boundaries

Implementation was authorized by G0. Historical founder-review.json records G0 publication and merge as false. Subsequent explicit authorization permits PR publication, Linux dispatch and included-only Claude use; see execution-authorization.json. PR #201 is open and Linux has passed. Merge, remote tracking apply and whole-M4 acceptance remain separate. Full M4 acceptance follows the outstanding evidence and a separate exact-candidate G4 decision.

## 7. Published observation views and preservation

Codex transcript and measurement records replace local temporary paths and ephemeral host thread identifiers with stable placeholders. Original observed digests refer to original bytes, not pseudonymized paths; these published views are not runnable grants or independent replay inputs. Each view retains the raw record hash, and originals remain operator-local outside the repository. The publication branch starts from the capture candidate and contains only sanitized packaging; the earlier local packaging branch is preserved without rewriting or deleting its history. Raw measurement quantities, outcomes and all bound source inputs are unchanged.

Independent packaging re-review passed at a54f9d6. The P2 transcript-redaction finding is resolved; raw final report is retained in packaging-review.json. Final metadata packaging preserves all bound implementation inputs.

## 8. Authorized publication and obtained Linux addendum (2026-10-04 snapshot)

The founder explicitly authorized PR publication, Linux reproduction and included-subscription-only Claude use. PR #201 is open on the reviewed implementation candidate 9108a20. Execution authorization is recorded separately from historical G0; merge and whole-M4 acceptance remain unapproved.

GitHub run 37197461233 reproduced that exact clean candidate on fresh hosted Linux x86_64 (Python 3.12.14, Git 2.55.0): 61 tests, no skips. The auxiliary workflow commit ab9107d uses the already registered manual workflow and restricts its input to 9108a20, leaving the reviewed PR workflow/candidate untouched during execution. Candidate/input/log hashes and actual run provenance passed local verification.

PR CI run 37197290307 completed successfully: 367 passing tests and five audited skips among 372 tests; its selected integration matrix was skipped. This is distinct from Darwin’s four skips and Linux reproduction’s zero skips. This snapshot recorded T011/T012 obtained and T010/T013/T014 open; the later Claude capture is recorded below.

At this snapshot Claude Code 2.1.236 had no signed-in subscription and no model call had occurred. The access and usage-credit gates were satisfied later as recorded below. No API fallback was authorized.

The prior implementation assurance at 9108a20 is archived unchanged with its historical source/evidence binding. This new draft updates evidence and the tracking test’s expected task states, without changing runtime, schemas or frozen experiment inputs. Record-only checks and independent packaging review cover this delta.

## 9. Actual Claude host addendum (2026-10-05)

The operator signed in with Claude.ai Max and confirmed Usage credits were disabled before any model-backed test. Claude Code 2.1.236 negotiated MCP 2025-11-25 through a one-server temporary config with `--strict-mcp-config`; built-in tools were disabled and API/provider environment overrides were removed. The owned two-edit fixture produced plan digest `sha256:27e444c1435f5872ef25e51036b77bbe83a86e9a6fd8ee4790ce727c03faca5d`, with writes limited to `a.txt` and `b.txt` and no execution authority in preparation. An empty grant store refused execute without allocating a run. After operator review, a local one-use grant authorized execution; the host was deliberately interrupted after `a`, its prefix independently verified, and the same Claude session resumed with a new local grant. Recovery completed `a` and `b`; final tree `f4b354863caa9cea99b95422c9dab70465757d87` matched the expected tree, and retrying the consumed grant returned `not-repeated`. Initial incomplete tool arguments were rejected without side effects and corrected in the same session.

The sanitized request/result transcript, raw log hash, host identity, candidate/input bindings and independent verifier results are in `host-evidence/claude.json`. T010 is complete. T013 still needs final independent evidence/authority reconciliation; T014 still needs the founder's separate G4 utility/go-no-go decision and an authorized tracking apply. PR #201 remains open and unmerged; no whole-M4, scientific or production closure is claimed.
