# M4 alpha implementation review packet

G0 was approved on frozen 0de9d31 and canonical ADR 0020 adopted on 2026-10-04. Historical scope provenance is preserved in founder-review.json and accepted-assurance-0de9d31.json. SPEC-020 acceptance remains intact. M4 remains open.

## 1. Implemented scope

C1: verified policy pipeline and one-use operator grants outside model tools. C2: dependency-ready isolated preparation, fixed text patches only, exclusive serial coordinator publication, live effects and independent consumer verification. C3: pinned 2025-11-25 stdio MCP with analyze, prepare, status, execute, recover and verify; no grant-creation tool. Bounds, exclusions and observed-state semantics follow G1 and c2-execution-contract.md.

## 2. Candidate and actual checks

Implementation/capture candidate: 67b8b521d0d18ebe679a905c3ed559d2f4a0119a. Local sensitive profile passed 372 tests with four skips (three SPEC-019 deferred implementation, one unavailable private-history test). Fresh Darwin checkout/process passed 61 alpha/core tests with no skips, using existing isolated Python. Two independent gpt-6-luna implementation reviewers reported no findings; raw reports are retained. PR profile passed on preserved implementation-equivalent local candidate 41ee2b6: 368 passed, four explicitly audited skips. Record-only packaging checks remain separate; see c4-evidence/pr-validation.json and skip-audit.json.

## 3. Actual host evidence

Installed Codex 0.159.0-alpha.12.1 used its actual MCP tool bridge for all six tools, missing-grant refusal, verified interruption prefix, resume, read-only retry and abort. Source and candidate inputs remained unchanged. Zero model calls; no persistent host configuration changes. Claude Code 2.1.236 has G1 handshake evidence only. Full Claude tool/refusal/disconnect/recovery evidence remains pending the requested consumption boundary. No model budget answer is inferred.

## 4. Measurement and limitations

Six paired two-edit trials, both admitted orders, yielded matching independently verified final trees in every pair. Median serial/parallel total wall ratio: 0.5581; outcome: negative-or-null-descriptive. Full evidence production, grants, rehearsal, verification and cleanup are included. Raw ratios and costs are in c4-evidence/measurement.json. This small descriptive corpus does not establish population benefit; overlap does not prove simultaneous CPU execution. Scratch is sampled; there is no hard child-memory cap or hostile same-UID isolation claim.

## 5. Remaining acceptance gates

Full actual Claude exercise and fresh Linux x86_64 core/protocol reproduction are still required. The manual Linux workflow is prepared and actionlint passed, but no remote dispatch is claimed. T010–T014 remain open with partial progress documented. G4 requires all six exit rows and an explicit utility go/no-go, including negative or inconclusive outcomes. No scientific, production or whole-M4 closure follows from these tests.

## 6. Approval boundaries

Implementation was authorized by G0. PR publication, remote tracking apply, Linux remote dispatch and merge require their separate authority; founder-review.json records publication and merge as false. The next review can authorize publication of this bounded implementation and the manual Linux evidence run. That does not accept M4 as complete. Full M4 acceptance follows the outstanding evidence and a separate exact-candidate G4 decision.

## 7. Published observation views and preservation

Codex transcript and measurement records replace local temporary paths and ephemeral host thread identifiers with stable placeholders. Original observed digests refer to original bytes, not pseudonymized paths; these published views are not runnable grants or independent replay inputs. Each view retains the raw record hash, and originals remain operator-local outside the repository. The publication branch starts from the capture candidate and contains only sanitized packaging; the earlier local packaging branch is preserved without rewriting or deleting its history. Raw measurement quantities, outcomes and all bound source inputs are unchanged.

Independent packaging re-review passed at a54f9d6. The P2 transcript-redaction finding is resolved; raw final report is retained in packaging-review.json. Final metadata packaging preserves all bound implementation inputs.
