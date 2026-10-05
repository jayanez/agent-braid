# M4 alpha implementation review packet

G0 was approved on frozen 0de9d31 and canonical ADR 0020 adopted on 2026-10-04. Historical scope provenance is preserved in founder-review.json and accepted-assurance-0de9d31.json. SPEC-020 acceptance remains intact. M4 remains open.

## 1. Implemented scope

C1: verified policy pipeline and one-use operator grants outside model tools. C2: dependency-ready isolated preparation, fixed text patches only, exclusive serial coordinator publication, live effects and independent consumer verification. C3: pinned 2025-11-25 stdio MCP with analyze, prepare, status, execute, recover and verify; no grant-creation tool. Bounds, exclusions and observed-state semantics follow G1 and c2-execution-contract.md.

## 2. Candidate and actual checks

Implementation source candidate: `9108a20`; Codex and measurement candidate: `67b8b52`; Claude host candidate: `d46fc52`; PR evidence baseline/head before T013 reconciliation: `f5d6b21`. Fresh Darwin and hosted Linux checkout/process reproductions passed 61 alpha/core tests with no skips. The historical local PR profile on `41ee2b6` remains bound in `c4-evidence/pr-validation.txt`. On baseline `f5d6b21`, the local PR profile passed 372 tests with four skips, and both GitHub validation runs passed 372 tests with five audited skips; their selected Spec Kit integration matrix was skipped. T013 was reviewed at `b1d602e` and published with its closure record at `5159fa1`; that final record-only candidate passed the local sensitive profile (372 tests, four skips), the GitHub push suite (372 tests, five skips), and the GitHub pull-request suite (385 tests, five skips). The selected Spec Kit integration matrix remained skipped in both runs, and tracking audit run `37301937147` passed. See the T013 reconciliation for baseline identities and the current PR checks above for closure-candidate results.

## 3. Actual host evidence

Installed Codex 0.159.0-alpha.12.1 used its actual MCP tool bridge for all six tools, missing-grant refusal, verified interruption prefix, resume, read-only retry and abort. Actual Claude Code 2.1.236, authenticated through Claude.ai Max with usage credits disabled by operator confirmation, used a strict temporary MCP config on an owned fixture. It prepared and verified a plan, was refused for a missing grant, executed after a separate local grant, disconnected at the controlled prefix after operation `a`, resumed with a new grant, independently verified the completed expected tree, and did not redispatch the consumed grant. Incomplete tool arguments were safely rejected before the valid calls. The candidate and fixture source remained unchanged; no persistent host MCP configuration or API/provider fallback was used. Full transcript and provenance are in `host-evidence/claude.json`.

## 4. Measurement and limitations

Six paired two-edit trials, both admitted orders, yielded matching independently verified final trees in every pair. Median serial/parallel total wall ratio: 0.5581; outcome: negative-or-null-descriptive. Full evidence production, grants, rehearsal, verification and cleanup are included. Raw ratios and costs are in c4-evidence/measurement.json. This small descriptive corpus does not establish population benefit; overlap does not prove simultaneous CPU execution. Scratch is sampled; there is no hard child-memory cap or hostile same-UID isolation claim.

## 5. G4 status

T010 actual-host capture and T013’s six-row evidence/authority reconciliation are complete. Luna reviewed `b1d602e1b96591fe693b0f9112b43bb4b98baaaa` with no findings; the review record SHA-256 is `b5e7b3bb9d0c4bc098b3b4770e26a4f3334b4e200c3c947f174dd121557d26f2`. The founder recorded a G4 NO-GO on usefulness under the current evidence on 2026-10-05; the decision is bound in `g4-decision.json`. It does not accept whole M4 or close the M4 milestone. The conditional Spec Kit integration matrix remains skipped, and the governed remote tracking apply remains pending its own authorization.

## 6. Approval boundaries

Implementation was authorized by G0. Historical founder-review.json records G0 publication and merge as false. Subsequent explicit authorization permits PR publication, Linux dispatch and included-only Claude use; see execution-authorization.json. PR #201 is open and Linux has passed. The founder’s G4 NO-GO records that current evidence does not support accepting M4 as a useful speedup capability. The M4 milestone remains open; merge and remote tracking apply remain separate actions requiring their applicable authorization.

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

The sanitized request/result transcript, raw log hash, host identity, candidate/input bindings and independent verifier results are in `host-evidence/claude.json`. T010 is complete. T013’s consolidated evidence and authority map is `t013-reconciliation.json` (SHA-256 `d1d670a91cee8e0e862c01554298e2528323954cbf9ef2d814d8b1323779ca24`). Fresh independent Luna review of `b1d602e1b96591fe693b0f9112b43bb4b98baaaa` found no actionable findings; see `t013-luna-review.json` (SHA-256 `b5e7b3bb9d0c4bc098b3b4770e26a4f3334b4e200c3c947f174dd121557d26f2`). The founder’s G4 NO-GO on usefulness is now recorded; T014 remains open for the separately authorized tracking apply. PR #201 remains open and unmerged; no whole-M4, scientific or production closure is claimed.

## 10. G4 decision packet and founder outcome

| Exit row | Evidence assembled | Candidate/platform binding | Remaining boundary |
| --- | --- | --- | --- |
| MCP and host-runtime adapters | SC-011–014; actual Codex and Claude host transcripts and independent verification | Codex `67b8b52` and Claude `d46fc52`, both Darwin arm64 | Only these two clients and the pinned protocol are observed |
| Transactional/isolation policies | SC-003–006; grant, footprint, scheduling, private worker and serial agreement checks | Core source `9108a20`; six-pair measurement source `67b8b52` | Fixed ordinary-text patches; no hard child-memory cap or hostile same-UID isolation claim |
| Live effect verification | SC-007–008; observed path/mode/blob effects and tamper/consumer refusal controls | Bound source and input digests in `assurance.json` | Tracked-tree evidence does not establish semantic correctness |
| Replay and recovery | SC-009–010 plus actual Codex/Claude interruption, resume and retry checks | Codex `67b8b52`, Claude `d46fc52`, and Linux reproduction `9108a20` | Process-interruption boundary only; no power-loss guarantee |
| CI and policy gates | Local PR profile, fresh Darwin/Linux reproductions, GitHub runs `37303046833` (372 tests, five skips) and `37303052926` (385 tests, five skips) | Decision-time PR head `3b776ea` (before this G4 record); Linux x86_64 / Python 3.12.14; Darwin arm64 / Python 3.13.11 | Conditional Spec Kit integration matrix was skipped in both runs; the G4 documentation delta still needs its own CI |
| Portability across agent environments | Actual Codex and Claude observations on Darwin; independent Linux core/protocol reproduction | Host candidates above; Linux run 37197461233 on `9108a20` | No other host/platform combinations are claimed |

Six paired trials produced equivalent verified trees in every pair. The median
serial/parallel total-wall ratio is `0.5581`, so this descriptive sample measured
serial at about 56% of parallel wall time (parallel about 1.79x serial). The corpus
is small and uncontrolled; this is not a population estimate or general speedup
claim. On 2026-10-05, the founder recorded **NO-GO for accepting SPEC-021 as a
useful speedup capability under the current evidence**. Six paired trials produced
equivalent verified trees, but the median serial/parallel total-wall ratio was
`0.5581`; the small, uncontrolled sample did not demonstrate useful acceleration.
This rejects the current utility case only. It does not establish that parallelism
is generally unhelpful, validate M4 scientifically or formally, or close the M4
milestone. The conditional Spec Kit integration matrix was skipped in the current
PR workflows and remains an unexecuted check. SPEC-021 and M4 remain open. The
decision source, candidate bindings and limits are recorded in
`g4-decision.json`; remote tracking apply and merge remain separate.
