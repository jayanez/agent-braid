# SPEC-077: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.
No task here launches a native host, issues a grant or publishes before T008.

## Phase P0 — review

- [ ] T001 (REQ-001 / SC-001): Owner review of spec, plan, contract and ADR 0043;
  decide or defer OD-1 to OD-6. Dependencies: none. Verification: procedure_001.
  Planned evidence: `evidence/t001-owner-review.md`; obtained: none.
- [x] T002 (REQ-001 / SC-001 REQ-003 / SC-003 REQ-005 / SC-005 REQ-008 / SC-008): Run the Codex contract review ([packet](review/codex-contract-20261116.md)) on the
  merged candidate; record the raw output and triage each finding (confirmed, fixed,
  rejected with reason). Dependencies: this PR merged. Verification: procedure_002.
  Planned evidence: `evidence/review/codex-contract-20261116.json`; obtained: that record
  (2026-11-17, candidate `af8d5683`, codex-cli 0.169.0-alpha.11.1; raw output
  `codex-contract-20261116.raw.json`). 19 findings: 14 confirmed, 5 partial, 0 rejected, each
  with a reason. Fixes are deferred by owner decision (2026-11-18): they are applied only
  after SPEC-049 T014 and only if D7 keeps the harness open, and they remain T003's
  prerequisite. Not human review.

## Phase P1 — implementation (unpublished)

- [ ] T003 (REQ-002 / SC-002 REQ-003 / SC-003 REQ-004 / SC-004 REQ-005 / SC-005): Implement the adapter and the four plugin-owned tools. Dependencies: T001 (OD-1,
  OD-3), T002 confirmed findings applied to the contract. Target files:
  `agent_braid/harness_mcp.py`, `agent_braid/plugin_mcp.py`. Frozen harness files
  untouched. `harness capabilities` keeps `pluginOrMcpSurface: "none"`.
  Verification: procedure_003. Planned evidence: `evidence/t003.json`.
- [ ] T004 (REQ-002 / SC-002 REQ-003 / SC-003 REQ-004 / SC-004 REQ-005 / SC-005 REQ-006 / SC-006 REQ-007 / SC-007 REQ-008 / SC-008): Tests: exact tool set, no effects,
  flat schema in description, path containment, CLI parity (differential), output
  bound, refusal pointer and redaction; one mutation control per guard. Target file:
  `tests/test_harness_mcp.py`. Dependencies: T003. Verification: procedure_004, then
  `quick`. Planned evidence: `evidence/t004.json`.
- [ ] T005 (REQ-002 / SC-002 REQ-007 / SC-007): Update installed verifiers and plugin
  tests that count plugin tools; telemetry names per OD-4. Dependencies: T003, OD-4.
  Verification: procedure_005. Planned evidence: `evidence/t005.json`.

## Phase P2 — host validity

- [ ] T006 (REQ-009 / SC-009): Author and freeze the held-out prompt set (10 prompts,
  at least two forbidden-effect prompts), its scoring rule and target (OD-2); record
  the SHA-256 before any run. Dependencies: T001. Verification: procedure_006.
  Planned evidence: `evidence/heldout-set.json`.
- [ ] T007 (REQ-009 / SC-009): Run the frozen set in Claude Code, Codex and OpenCode
  (10 × 3 per host) with the automated driver on an unpublished local build; report
  per-host validity with Wilson 95% intervals and failure signatures. A miss is a
  negative result. Dependencies: T004 T006. Verification: procedure_007. Planned
  evidence: `evidence/heldout-claude.json`, `evidence/heldout-codex.json`,
  `evidence/heldout-opencode.json`.

## Phase P3 — publication decision

- [ ] T008 (REQ-010 / SC-010): Record the publication decision against the gate:
  SPEC-049 T014 results, the D7 ADR outcome, T007, T002 and owner acceptance of the
  candidate. Publish in the release named under OD-5, or record "not published".
  Accept or reject ADR 0043 (OD-6). Dependencies: SPEC-049 T014; D7 ADR; T002 T007.
  Verification: procedure_008. Planned evidence: `evidence/t008-publication.json`.
- [ ] T009 (REQ-010 / SC-010): Only if T008 publishes: `pluginOrMcpSurface` reports
  `agent-braid-harness-mcp/v0.1`; update `docs/tooling/HARNESSING.md`,
  `docs/tooling/NATIVE_PLUGINS.md` and release notes. Dependencies: T008.
  Verification: procedure_009. Planned evidence: `evidence/t009.json`.
