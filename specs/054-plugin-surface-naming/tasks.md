# SPEC-054: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply native-host, release or founder acceptance. Parallelizable does not
authorize concurrent agents.

- [ ] T001 (REQ-001 / SC-001): Review the naming policy and research record.
  Dependencies: none. Files: `contracts/naming-policy.md`, `research.md`,
  `docs/adr/0030-native-plugin-surface-naming.md`. Verification: procedure_001.
  Evidence: owner review record and ADR decision.

- [x] T002 (REQ-002 / SC-002): Add a package check that pins plugin, marketplace,
  server-key and tool names. Dependencies: T001. Files:
  `scripts/build_native_plugin.py`, plugin package tests. Verification:
  procedure_002. Evidence: test output with negative controls.

- [x] T003 (REQ-003 / SC-003): Remove prompts from the plugin MCP server and
  publish `agent-braid-plugin/v0.2`. Dependencies: T001. Files:
  `agent_braid/plugin_mcp.py`, `tests/test_plugin_mcp.py`. Verification:
  procedure_003. Evidence: SDK client test output.

- [x] T004 (REQ-004 / SC-004): Package unprefixed plugin skills with recorded
  substitutions. Dependencies: T001. Files: `scripts/build_native_plugin.py`,
  plugin inventory tests. Verification: procedure_004. Evidence: built package
  inventory and test output.

- [x] T005 (REQ-005 / SC-005): Regression-check the portable server and legacy
  install. Dependencies: T003, T004. Files: existing tooling MCP and install
  tests. Verification: procedure_005. Evidence: unchanged test results.

- [x] T006 (REQ-006 / SC-006): Set version `0.1.0-alpha.4`, write release notes
  and the migration/rollback note, and exercise update from alpha.3 in owned
  fixtures. Dependencies: T002–T005. Verification: procedure_006. Evidence:
  update/rollback fixture record.

- [x] T007 (REQ-007 / SC-007): Confirm telemetry operations and contracts are
  unchanged. Dependencies: T003. Files: telemetry tests. Verification:
  procedure_007. Evidence: test output.

- [x] T008 (REQ-008 / SC-008): Update English documentation and the SPEC-046
  interface contract to plugin interface v0.2. Dependencies: T003, T004.
  Verification: procedure_008. Evidence: documentation diff and search record.

- [x] T009 (REQ-009 / SC-009; REQ-006 / SC-006): Observe the candidate natively in
  Codex and Claude Code user profiles, including update from alpha.3.
  Dependencies: T006, T008. Verification: procedure_009. Evidence: native
  observation record with environment and limits: [Claude Code](evidence/native-claude-alpha4.md) and [Codex](evidence/native-codex-alpha4.md). Closed with bounded scope by owner decision of 2026-10-25: CLI and loader observation on macOS arm64 against a local directory marketplace; interactive skill invocation, sign-in, Linux and a published Git ref were not observed.

- [x] T010 (all): Run `--profile pr` on the stable candidate, record results and
  request owner release decision. Dependencies: T002–T009. Evidence: profile
  receipt. Release and publication remain separate owner decisions.
