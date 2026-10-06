# Tasks

G0 is recorded; bounded implementation, actual host capture and C4 reproductions are obtained. T013 reconciliation and independent review are complete. The founder recorded G4 NO-GO on utility under current evidence; whole-M4 acceptance was not granted. T014's administrative tracking work and merged-source reconciliation are complete; its issue closed on 2026-10-06 after PR #220 merged. This document assigns dependencies, not concurrent-agent authority.
Implementation evidence below is separate from the historically approved scope proposal.

Each implementation task runs `.venv-speckit/bin/python -m scripts.validate_change
--base develop --profile quick` after a coherent increment and updates actual
test/evidence references. Stable candidates run `--profile pr` once before review.
Fresh reproduction and human gates remain separate.

- [x] T001: G0 Record exact-candidate founder scope and ADR 0020 decision before expanded implementation.
  - Trace: all. Dependencies: none.
  - Targets: `specs/021-m4-alpha-runtime/founder-review.json; docs/adr/0020-bounded-m4-alpha-runtime.md`.
  - Verification/evidence: Founder decision plus explicit authority-drift review; preserve SPEC-020 acceptance.

- [x] T002: G1 Pin host versions, common protocol/schema, grant policy, numeric budgets and optional SDK/license choice.
  - Trace: REQ-002,003,006,007. Dependencies: T001.
  - Targets: `specs/021-m4-alpha-runtime/research.md; contracts and pyproject.toml if justified`.
  - Verification/evidence: Document compatibility probes and explicit host-fixture access/cost boundary before execution.

- [x] T003: C1 Implement unified verified policy pipeline and separate versioned contracts.
  - Trace: REQ-001 / SC-001,002. Dependencies: T002.
  - Targets: `agent_braid/runtime_policy.py; schemas/0.1.0-alpha/runtime-policy.schema.json`.
  - Verification/evidence: Actual pipeline tests reject forged/missing evidence; preserve legacy analysis authorization false.

- [x] T004: C1 Implement operator grants outside model tools and idempotent run admission.
  - Trace: REQ-002 / SC-003,004. Dependencies: T003.
  - Targets: `agent_braid/runtime_policy.py; agent_braid/cli.py; grant schema`.
  - Verification/evidence: Actual tests cover stale/expired/consumed grants, changed manifests/destinations and retries.

- [x] T005: C2 Define adapter-verified reads/writes/shared resources and private worker isolation.
  - Trace: REQ-003 / SC-005,006. Dependencies: T004.
  - Targets: `agent_braid/runtime_scheduler.py; reviewed execution contract`.
  - Verification/evidence: Actual isolation/footprint tests; unknown reads cannot qualify for parallel admission.

- [x] T006: C2 Implement dependency-ready bounded waves and exclusive coordinator publication.
  - Trace: REQ-003 / SC-005,006. Dependencies: T005.
  - Targets: `agent_braid/runtime_scheduler.py; agent_braid/git_runtime.py`.
  - Verification/evidence: Actual overlap and all supported schedule comparisons against serial reference; zero unsafe admissions.

- [x] T007: C2 Verify observed effects and consumer certificates before reporting completion.
  - Trace: REQ-004 / SC-007,008. Dependencies: T006.
  - Targets: `agent_braid/git_runtime.py; runtime report contracts`.
  - Verification/evidence: Actual drift/forgery/partial-state tests; independent consumer rejects unsupported completion.

- [x] T008: C2 Extend crash/cancellation/abort recovery to owned worker state.
  - Trace: REQ-005 / SC-009,010. Dependencies: T007.
  - Targets: `agent_braid/runtime_scheduler.py; agent_braid/git_runtime.py`.
  - Verification/evidence: Fresh-process kill/abort/resume and duplicate delivery tests; retain verified prefix without duplicate steps.

- [x] T009: C3 Implement pinned bounded stdio MCP adapter with no authorize tool.
  - Trace: REQ-006 / SC-011,012. Dependencies: T004,T008.
  - Targets: `agent_braid/mcp_runtime.py; optional package metadata; tests/test_m4_alpha_mcp.py`.
  - Verification/evidence: Deterministic protocol peer tests for lifecycle, errors, message budgets, cancellation and identity preservation.

- [x] T010: C3 Capture actual Codex and Claude Code owned-fixture exercise records.
  - Trace: REQ-007 / SC-013,014. Dependencies: T009.
  - Targets: `host launch recipes; specs/021-m4-alpha-runtime/host-evidence/`.
  - Verification/evidence: Both actual clients perform prepare, authorized execute, refusal and disconnect/recovery; independently verify results. Claude record is bound to candidate `d46fc52` in `host-evidence/claude.json`.

- [x] T011: C4 Add deterministic CI policy/transport checks and fresh Darwin/Linux reproduction.
  - Trace: REQ-008 / SC-015,016. Dependencies: T009.
  - Targets: `scripts/reproduce_m4_alpha.py; .github/workflows/m4-alpha-reproduction.yml`.
  - Verification/evidence: Execute reproductions; bind source/candidate/version/platform/output hashes; CI uses no live-model credentials.

- [x] T012: C4 Freeze measurement protocol and capture bounded safety/utility/cost comparisons.
  - Trace: REQ-003,008 / SC-005,006,015,016. Dependencies: T008,T011.
  - Targets: `specs/021-m4-alpha-runtime/measurement-protocol.md; measurement evidence`.
  - Verification/evidence: Freeze corpus, repeats and cold/warm policy before runs. Measure overlap, conflicts, diagnostics and full cost; retain null/inconclusive outcomes.

- [x] T013: C4 Complete independent Luna review and evidence/authority reconciliation.
  - Trace: all. Dependencies: T010,T011,T012.
  - Targets: `specs/021-m4-alpha-runtime/assurance.json; t013-reconciliation.json; t013-luna-review.json; decision-packet.md`.
  - Verification/evidence: PR profile and current PR checks passed on head `f5d6b21`; record-only delta passed the planner-selected sensitive profile (372 tests, four audited skips). Fresh independent gpt-6-luna review of `b1d602e1b96591fe693b0f9112b43bb4b98baaaa` found no findings and verified all 56 path/hash references across 13 unique files. Reconciliation SHA-256 `d1d670a91cee8e0e862c01554298e2528323954cbf9ef2d814d8b1323779ca24`; review record SHA-256 `b5e7b3bb9d0c4bc098b3b4770e26a4f3334b4e200c3c947f174dd121557d26f2`. T014 remains separate.

- [x] T014: G4 Record separate founder whole-M4 alpha decision and governed tracking update.
  - Trace: REQ-008 / SC-015,016. Dependencies: T013.
  - Targets: `specs/021-m4-alpha-runtime/g4-decision.json; ROADMAP.md; docs/development/github-tracking.json`.
  - Verification/evidence: Founder NO-GO remains recorded in `g4-decision.json`; SPEC-021 and M4 remain open. The separately authorized merged-source tracking apply completed 42 reviewed operations, followed by `operations: []`; all three private Project views and the four mapped Review pending entries were verified at that captured baseline. The non-normative operations receipt is `docs/experiments/evidence/autonomous-delivery-2026-10-06/tracking-receipt.json`; interpretation and source/issue boundaries are recorded in `docs/development/autonomous-delivery.md`. PR #220 merged at `d53314706d065247735ae09d5deed60a1365bbbb`; issue T014 #218 closed at `2026-10-06T13:12:34Z`. Administrative closure grants no new founder or whole-milestone acceptance.

## Obtained progress and remaining gates

T010: actual Codex six-tool/refusal/disconnect/recovery capture passed with zero model calls. Actual Claude Code 2.1.236 on Claude.ai Max completed prepare, missing-grant refusal, authorized execute, controlled disconnect after `a`, resumed recovery, final verification, and non-repeat retry on frozen candidate `d46fc52`; usage credits were disabled by operator confirmation. The MCP server rejected incomplete argument attempts without allocating a run; the corrected calls passed. No source or candidate changes occurred.
T011: workflow and actionlint passed; fresh Darwin and hosted Linux checkout/process reproductions each passed 61 tests without skips; Linux evidence and CI are obtained.
T012: frozen measurement protocol executed, six paired trials captured; Linux prerequisite obtained; the founder later recorded G4 NO-GO on utility under the current evidence.
T013: complete. The six-row reconciliation `specs/021-m4-alpha-runtime/t013-reconciliation.json` (SHA-256 `d1d670a91cee8e0e862c01554298e2528323954cbf9ef2d814d8b1323779ca24`) was independently reviewed with no findings at commit `b1d602e1b96591fe693b0f9112b43bb4b98baaaa`; review record `specs/021-m4-alpha-runtime/t013-luna-review.json` (SHA-256 `b5e7b3bb9d0c4bc098b3b4770e26a4f3334b4e200c3c947f174dd121557d26f2`).
T014: complete. G4 NO-GO was recorded on 2026-10-05; the separately authorized governed tracking apply and Project verification completed on 2026-10-06. The source amendment merged in PR #220 at `d53314706d065247735ae09d5deed60a1365bbbb`, followed by closure of issue #218. M4 acceptance was not granted. The historical publication and Linux execution authorizations remain separate from this administrative closure.
