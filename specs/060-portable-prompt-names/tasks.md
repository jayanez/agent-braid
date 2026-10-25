# SPEC-060: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply native-host, release or founder acceptance. Parallelizable does not
authorize concurrent agents. No task is started by the specification change:
T002-T008 need ADR 0031 adoption and an explicit implementation authorization.

- [ ] T001 (REQ-001 / SC-001; REQ-002 / SC-002; REQ-007 / SC-007): Owner review of
  the specification, the contract delta, ADR 0031 and the open decisions OD-1 to
  OD-8, including the alias exception. Dependencies: none. Files:
  `contracts/interface-delta.md`, `plan.md`, `docs/adr/0031-portable-prompt-names.md`.
  Verification: procedure_001 (review part). Evidence: owner review record and the
  ADR decision.

- [ ] T002 (REQ-001 / SC-001): Add the surface-version constant, the ordered
  prompt registry and the canonical prompts with byte-equal text. Tests first.
  Dependencies: T001. Files: `agent_braid/tooling_mcp.py`, `tests/test_tooling_mcp.py`.
  Verification: procedure_001. Evidence: SDK client test output with negative controls.

- [ ] T003 (REQ-002 / SC-002): Publish the three deprecated aliases with the
  deprecation marking, list order and `deprecatedPrompts` capabilities entries.
  Dependencies: T002. Files: `agent_braid/tooling_mcp.py`, `tests/test_tooling_mcp.py`.
  Verification: procedure_002. Evidence: SDK client test output; alias-in-`prompts`
  and unmarked-alias negative controls.

- [ ] T004 (REQ-003 / SC-003; REQ-005 / SC-005): Keep the envelope stamp, output
  schemas and provenance at v0.1 (or apply the OD-1 decision), report both
  identifiers in capabilities, enumerate every pinned v0.1 occurrence by search and
  change only prompt and capabilities assertions. Dependencies: T002. Files:
  `agent_braid/tooling_mcp.py`, the four pinning test modules, System One verifier
  tests. Verification: procedure_003, procedure_005. Evidence: byte comparison of
  v0.1 and v0.2 envelopes on identical inputs, search record, test output.

- [ ] T005 (REQ-004 / SC-004): Strip the new capabilities keys in the plugin
  facade, restore its capabilities `schemaVersion`, and add a golden alpha.4 byte
  comparison for the plugin resource and envelopes. Dependencies: T002, T003.
  Files: `agent_braid/plugin_mcp.py`, `tests/test_plugin_mcp.py`. Verification:
  procedure_004. Evidence: plugin SDK client test output.

- [ ] T006 (REQ-005 / SC-005): Regression-check telemetry (prompts uncounted, enum
  and batch/store versions unchanged), the legacy receipt install, the host
  configuration preview and the System One verifier. Dependencies: T003, T004.
  Files: existing telemetry, install, hosts and System One tests. Verification:
  procedure_005. Evidence: unchanged test results and a byte-equal configuration
  preview.

- [ ] T007 (REQ-009 / SC-009): Update English documentation: new names primary,
  aliases deprecated, the contract link, the removal criterion, the key-collision
  caveat and the forward pointer from the SPEC-054 policy row. Dependencies: T003,
  T004. Files: `docs/tooling/HOSTS.md`, `docs/tooling/INSTALL.md`,
  `docs/tooling/SKILLS.md`, `docs/tooling/NATIVE_PLUGINS.md`,
  `specs/040-portable-mcp-surface/contracts/interface.md` (pointer only).
  Verification: procedure_009. Evidence: documentation diff and search record.

- [ ] T008 (REQ-006 / SC-006; REQ-008 / SC-008): Prepare release readiness:
  package version per OD-3, release notes (new names, aliases, removal contract,
  rollback), migration and rollback fixtures that reinstall the earlier package
  against a v0.1-written host configuration. Dependencies: T002-T007. Verification:
  procedure_006, procedure_008. Evidence: update/rollback fixture record and the
  release-readiness record stating that nothing was released.

- [ ] T009 (REQ-010 / SC-010): Observe the candidate natively in a Claude Code
  profile, alone and next to the native plugin, and record that Codex lists no
  prompts. Dependencies: T008. Verification: procedure_010. Evidence: native
  observation record with environment, versions and limits (owner-run or
  separately authorized).

- [ ] T010 (REQ-008 / SC-008; REQ-011 / SC-011): Run `--profile pr` on the stable
  candidate, verify that no frozen path changed, record results and request the
  owner release decision. Dependencies: T002-T009. Verification: procedure_008,
  procedure_011. Evidence: profile receipt and path comparison. Release,
  tagging and publication remain separate owner decisions.

- [ ] T011 (REQ-007 / SC-007): Remove the aliases under a new contract
  `agent-braid-tooling/v0.3` once every removal criterion holds. Dependencies:
  T010, two published window releases and an owner removal decision. Files: to be
  specified by the v0.3 amendment. Verification: procedure_007. Evidence: criterion
  checklist with release notes and repository search. Deferred by design; not part
  of the v0.2 candidate.
