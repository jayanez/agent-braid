# Tasks

G0 is recorded; C1/C2/C3 implementation tasks passed local validation. Full Claude host and whole-M4 gates remain open. This document assigns dependencies, not concurrent-agent authority.
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

- [ ] T010: C3 Capture actual Codex and Claude Code owned-fixture exercise records.
  - Trace: REQ-007 / SC-013,014. Dependencies: T009.
  - Targets: `host launch recipes; specs/021-m4-alpha-runtime/host-evidence/`.
  - Verification/evidence: Both actual clients perform prepare, authorized execute, refusal and disconnect/recovery; independently verify results.

- [x] T011: C4 Add deterministic CI policy/transport checks and fresh Darwin/Linux reproduction.
  - Trace: REQ-008 / SC-015,016. Dependencies: T009.
  - Targets: `scripts/reproduce_m4_alpha.py; .github/workflows/m4-alpha-reproduction.yml`.
  - Verification/evidence: Execute reproductions; bind source/candidate/version/platform/output hashes; CI uses no live-model credentials.

- [x] T012: C4 Freeze measurement protocol and capture bounded safety/utility/cost comparisons.
  - Trace: REQ-003,008 / SC-005,006,015,016. Dependencies: T008,T011.
  - Targets: `specs/021-m4-alpha-runtime/measurement-protocol.md; measurement evidence`.
  - Verification/evidence: Freeze corpus, repeats and cold/warm policy before runs. Measure overlap, conflicts, diagnostics and full cost; retain null/inconclusive outcomes.

- [ ] T013: C4 Complete independent Luna review and evidence/authority reconciliation.
  - Trace: all. Dependencies: T010,T011,T012.
  - Targets: `specs/021-m4-alpha-runtime/assurance.json; implementation-review.json; decision-packet.md`.
  - Verification/evidence: Run pr once on stable implementation; independent gpt-6-luna review; resolve findings and freeze exact candidate.

- [ ] T014: G4 Record separate founder whole-M4 alpha decision and governed tracking update.
  - Trace: REQ-008 / SC-015,016. Dependencies: T013.
  - Targets: `closure record/anchor; ROADMAP.md; docs/development/github-tracking.json`.
  - Verification/evidence: All six obtained-evidence rows complete; disclose utility outcome and unresolved gates. Remote tracking/publication needs its own authorized apply.

## Obtained progress and remaining gates

T010: actual Codex six-tool/refusal/disconnect/recovery capture passed with zero model calls; Claude full exercise pending.
T011: workflow and actionlint passed; fresh Darwin and hosted Linux checkout/process reproductions each passed 61 tests without skips; Linux evidence and CI are obtained.
T012: frozen measurement protocol executed, six paired trials captured; Linux prerequisite obtained; founder G4 utility decision remains separate.
T013: two independent Luna implementation reviews report no findings; remaining full Claude host dependency stays open. The stable PR profile passed; final record-only binding checks are separate.
T014: whole-M4 founder decision and remote apply remain pending; publication and Linux execution were explicitly authorized separately; merge remains unapproved.
