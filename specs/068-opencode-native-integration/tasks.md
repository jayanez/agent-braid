# SPEC-068: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply native-host, release or founder acceptance. Parallelizable is a dependency
property and does not authorize concurrent agents. No task is started by the
specification change. ADR 0037 is Proposed; no implementation task is authorized
until the owner adopts it and authorizes the tasks (T001). T010 and T011 need
separate owner decisions.

Commands run from the clean clone; `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

- [ ] T001 (REQ-001 / SC-001): Owner review of the specification, plan, research,
  both contracts and ADR 0037. OD-9 and OD-10 are decided (D12, D13; SC-010
  amended on 2026-11-03); record ADR adoption and which of T002–T009 are
  authorized. Dependencies: none. Files:
  `spec.md`, `plan.md`, `contracts/`, `docs/adr/0037-opencode-native-plugin.md`,
  a new owner review record. Verification: procedure_001 (`speckit-analyze` report,
  no change to existing contracts). Evidence: owner review record bound to a frozen
  commit (`validate_spec_kit freeze`).

- [x] T002 (REQ-002 / SC-002): Observe the OpenCode host matrix in a disposable
  profile (`XDG_CONFIG_HOME` and `XDG_DATA_HOME` in temporary directories, never the
  user's configuration) for the installed version: dependency-free module load;
  order of plugin transforms versus discovered skills; override of a user
  `agent-braid` MCP entry; tool approval prompts for plugin-registered MCP;
  `plugin add` from `github:…#<ref>::path:plugins/agent-braid` (executable bits,
  line endings, `.gitattributes`, size); `plugin list/update/remove`; command
  listing; `--standalone`; global and project configuration paths on macOS and
  Linux (`XDG_CONFIG_HOME` handling, `opencode.json` versus `opencode.jsonc` when
  both exist); host approval behaviour for plugin and legacy MCP tools; a write-free
  host-visible warning channel for the entry (D13); how an installed native plugin
  appears in configuration, so the legacy preview can detect it. Rows not observed stay `unobserved`. Gate: a Git-install
  failure stops D3 and returns to the owner; any contradiction of research R1–R7
  returns the affected decision to the owner before T003–T007. Dependencies: T001.
  Files: `evidence/opencode-host-matrix.json`, `research.md` (status of each R item).
  Verification: procedure_002. Evidence: matrix with version, command, output digest
  and limits per row. Negative controls: user configuration digest unchanged before
  and after; altered mode or bytes detected.
  Done 2026-11-03 on OpenCode 2.1.4 / macOS arm64: obtained evidence
  `evidence/opencode-host-matrix.json`, findings in `research.md` (T002 findings).
  Rows 04b, 05b (`github:` transport), 09b (Linux) and 12b stay `unobserved`.

- [ ] T003 (REQ-003 / SC-003, stdio part; the real host is T010): Write the OpenCode entry module
  per the surface contract: three transforms only, root from `import.meta.url`, no
  removal or update of a skill it can see, no replacement of a foreign `agent-braid` server
  (semantic-field comparison), no throw, no network,
  writes, child processes or event subscriptions. Tests first: a Python test parses
  the source for forbidden APIs and checks the registered values; an MCP stdio
  fixture checks `workspaces` and `analyze-work` against the Codex/Claude results
  for the same input. Dependencies: T002. Files:
  `integrations/agent-braid/plugin/opencode/index.js`, `tests/test_plugin_opencode.py`.
  Verification: procedure_003, `quick`. Evidence: test output with negative controls
  (unknown workspace ID, arbitrary root, execution without grant, forbidden API
  inserted into a copy of the source).

- [ ] T004 (REQ-003 / SC-003; REQ-010 / SC-010): Extend the native build: write
  `package.json` (no dependencies), copy `opencode/index.js`, extend
  `check_package_names`, provenance (`hosts`) and inventory. Tests first: build
  fixture compares host-read Codex/Claude files with a build without the OpenCode
  target, per D12. Dependencies: T003. Files:
  `scripts/build_native_plugin.py`, `scripts/reproduce_native_plugin.py` if the
  reproduction check lists files, `tests/test_native_plugin_build.py`.
  Verification: procedure_010, `quick`. Evidence: build record and diff. Negative
  controls: wrong `package.json` name, declared dependency, drift in a host-read
  Codex/Claude file.

- [ ] T005 (REQ-004 / SC-004; REQ-005 / SC-005): Add `plugin doctor --host opencode
  [--project <dir>]`: read-only scan of the documented discovery locations with
  `collision`, `duplicate-guidance` and `server-collision` findings; output without
  `--host` unchanged. Extend the existing doctor report rather than adding a
  parallel one: the OpenCode findings sit beside the `pluginVersion`,
  `staleWorktreeRoots`, `unavailableWorkspaces` and `unsafeWorkspaces` fields
  shipped in `0.1.0-alpha.6` (SPEC-046 T020), and stale roots keep using
  `setup --prune-stale`. Add the `agent-braid-setup` and `agent-braid-reconnect`
  commands to the entry module; reconnect performs no reload. Tests first with
  fixture skill trees and a fake registry. Dependencies: T003 (commands); T007's
  JSONC scanner for reading explicit `skills` entries and the `agent-braid` server
  entry (the directory scan has no dependency and may land first).
  Files: `agent_braid/plugin_opencode.py`, `agent_braid/plugin_cli.py`,
  `integrations/agent-braid/plugin/opencode/index.js`, `tests/test_plugin_opencode.py`.
  Verification: procedure_004, procedure_005, `quick`. Evidence: test output.
  Negative controls: shadowing `analyze` in `.opencode/skills`; prefixed legacy
  skills reported as collision; any grant path; automatic reload.

- [ ] T006 (REQ-007 / SC-007; REQ-006 / SC-006, native install, update and remove commands): Add `opencode` to `install.sh --host` and to `--host
  all` (skipped with a notice when absent; `--host opencode` refuses when absent);
  `both` stays a deprecated alias for Codex and Claude only; README quick start
  gains the OpenCode row. Tests first with fake host executables. Dependencies: T004
  (install string and tag layout) and the merge of
  [jayanez/agent-braid#983](https://github.com/jayanez/agent-braid/pull/983), which
  introduces `--host all`. Parallelizable with T007 (disjoint files).
  Files: `install.sh`, `tests/test_plugin_installer.py`, `README.md`.
  Verification: procedure_007, `quick`. Evidence: test output. Negative controls:
  absent OpenCode under `--host opencode`; changed Codex or Claude command output;
  sudo or Python invoked.

- [ ] T007 (REQ-008 / SC-008; REQ-006 / SC-006): Add the `opencode` host to the
  legacy lifecycle per the legacy profile contract: per-host table in
  `tooling_install.py`, JSONC span scanner used only for `opencode`, paths, default
  server name `agent-braid` with the `native_plugin_shadowed` warning (D13), refusal codes, `hosts.json` and `asset_provenance`; tooling
  CLI `--host` choices. Include `plugin legacy` migration from an OpenCode receipt:
  `plugin legacy --host` choices (`plugin_cli.py`) and the receipt directory in
  `plugin_legacy.inventory`, which hard-codes the Codex and Claude paths today.
  Tests first on isolated destinations. Dependencies: T001 (T002 only for the
  configuration-path rows). Parallelizable with T003, T004 and T006 (disjoint files); shares `plugin_cli.py` with T005, so T005 and T007 run in series. Files:
  `agent_braid/tooling_install.py`, `agent_braid/plugin_legacy.py`,
  `agent_braid/plugin_cli.py`,
  `integrations/agent-braid/hosts.json`, tooling CLI module,
  `tests/test_tooling_install_opencode.py`. Verification: procedure_006,
  procedure_008, `quick`. Evidence: test output. Negative controls: comment or
  foreign key changed; repeat apply writes; unowned entry overwritten;
  `ambiguous_configuration`; failed write without rollback; Codex/Claude preview,
  receipt or diagnostic bytes changed.

- [ ] T008 (REQ-009 / SC-009; REQ-010 / SC-010): Regression: SPEC-046, 047, 054,
  060 and 066 contracts unchanged; envelopes and stores byte-identical with and
  without an OpenCode `_meta` session identifier; no stored artifact contains it;
  SPEC-047 T011/T012 surfaces (router-owned measurement, closed `refusal-reason`
  buckets, `lifecycle/serve-start`, batch schema v2, `telemetry audit-logs`)
  record OpenCode calls with no new field or bucket;
  Codex/Claude artifacts compared per D12. Dependencies: T004–T007. Files:
  `tests/test_plugin_mcp.py` and existing contract tests. Verification:
  procedure_009, procedure_010, `quick`. Evidence: test output and artifact diff.

- [ ] T009 (REQ-011 / SC-011): Update English documentation: README quick start,
  `docs/tooling/NATIVE_PLUGINS.md`, `INSTALL.md` (OpenCode legacy profile; route
  marked frozen fallback for all hosts), `SKILLS.md` (collisions and duplicate
  guidance), `HOSTS.md`, `PLUGIN_PRIVACY.md` (session identifier), `docs/tooling/README.md`,
  `docs/development/SPEC_KIT.md` (OpenCode column), SPEC-039 `program.md`
  (additive route note). Only behaviour recorded by T002 or tests is described as
  fact. Dependencies: T008. Files: as listed. Verification: procedure_011,
  repository documentation checks in `quick`. Evidence: documentation diff and a
  search record for unobserved claims.

- [ ] T010 (REQ-012 / SC-012; REQ-003 / SC-003 and REQ-006 / SC-006, real-host part): Native observation in a clean OpenCode profile by
  the owner or an operator: install from a candidate tag, skill and command listing,
  `agent-braid_analyze-work` on a registered workspace, reconnect, removal, on each
  available target platform. Each candidate version is observed in a new OpenCode
  session: reconnecting MCP in a running session does not switch it to a newly
  installed plugin version (observed for Claude Code with `0.1.0-alpha.6`; the
  OpenCode behaviour is a T002 row). Unobserved items stay open. Dependencies: T009 and an
  owner decision. Files: `evidence/native-observation.json`. Verification:
  procedure_012. Evidence: observation record with versions and limits.

- [ ] T011 (REQ-001…REQ-012): Stable candidate: `--profile pr`, `validate_spec_kit
  freeze`, release notes for `0.1.0-alpha.7` (D11), and the owner's release
  decision. Base: published `0.1.0-alpha.6` (release PR #1006, record PR #1012,
  tag `agent-braid--v0.1.0-alpha.6`), which stays the rollback target. Follow the
  SPEC-046 alpha.6 records as template (`release-acceptance-alpha6.md`,
  `evidence/release-alpha6.json`, `owner-authorization-20261103.md`) and move the
  published pins in `README.md`, `docs/STATUS.md`, `docs/tooling/INSTALL.md` and
  `docs/tooling/NATIVE_PLUGINS.md` to `0.1.0-alpha.7`. The Python package keeps
  its own version line (`0.1.0a2` at alpha.6). Dependencies: T010. Verification: `--profile pr` output and frozen
  snapshots. Evidence: release-readiness record stating whether anything was
  released; tag, `plugin-dist` publication and remote tracking only on explicit
  authorization.

## Limits

Engineering tasks; no hypothesis and no scientific claim. Host facts are
documented until T002 or T010 records them. Passing tests prove neither native
behaviour, nor safety in production, nor owner approval.
