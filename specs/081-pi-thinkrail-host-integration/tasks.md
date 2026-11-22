# SPEC-081: Tasks

Stable task IDs. Completion requires obtained evidence; task completion does not
imply native-host, release or founder acceptance. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.
No task here grants execution authority, starts a native harness session, writes the
owner's real host configuration or publishes before T012. Every advisory output
keeps `executionAuthorization` false.

## Phase P0 — review

- [ ] T001 (REQ-001 / SC-001): Owner review of spec, plan (and ADR if any); decide or defer OD-1 to OD-7 and name the authorized tasks.
  Dependencies: none. Target files: `spec.md`, `plan.md`, a new dated owner record.
  Verification: procedure_001. Planned evidence: `evidence/t001-owner-review.md`;
  obtained: none.
- [ ] T002 (REQ-001 / SC-001): Run the Codex review of this spec on the merged candidate; record raw output and triage.
  Each finding is confirmed, fixed or rejected with a reason. Independent model
  review, not human review. Dependencies: this PR merged. Target files:
  `review/codex-spec-review.md` (packet). Verification: procedure_001. Planned
  evidence: `evidence/t002-codex-review.json` and its raw output; obtained: none.

## Phase P1 — observation

- [ ] T003 (REQ-002 / SC-002): Write the one-command Pi and ThinkRail capture script with a dry-run mode and a disposable profile.
  Modelled on `scripts/har_codex_capture.py` (#1421): pinned binary hash and
  version, owner sign-in in their own terminal, environment built from scratch,
  raw output private (mode 0700), redacted shape summary with hashes. Tests use a
  fake binary. Dependencies: T001. Target files: `scripts/pi_host_capture.py`,
  `tests/test_pi_host_capture.py`. Verification: procedure_002, then `quick`.
  Planned evidence: `evidence/t003.json`; obtained: none.
- [ ] T004 (REQ-002 / SC-002 SC-003): Owner runs the capture; commit the redacted Pi and ThinkRail matrix and amend the spec where a row contradicts it.
  Rows: `pi install` from npm, Git and local path; skill and extension loading; Pi
  core `mcp.json` support; configuration and session paths; session JSONL shape;
  ThinkRail package install, MCP per-call approval and skill import. Unobserved rows
  stay `unobserved`. A missing Pi core MCP reader selects OD-3. Dependencies: T003.
  Target files: `evidence/pi-capture/`, `spec.md`. Verification: procedure_002,
  procedure_003. Planned evidence: `evidence/pi-capture/summary.json`; obtained: none.

## Phase P2 — design

- [ ] T005 (REQ-003 / SC-004 REQ-004 / SC-005): Draft the Pi surface contract and the Pi surface ADR (OD-6) from the T004 matrix; owner review.
  Dependencies: T004. Target files: `contracts/pi-surface.md`, a new ADR under
  `docs/adr/`. Verification: procedure_004, procedure_005. Planned evidence:
  `evidence/t005-owner-review.md`; obtained: none.

## Phase P3 — build

- [ ] T006 (REQ-003 / SC-004): Add the Pi package target to the plugin build with the packaged skills (eight with SPEC-080) and byte-identity checks for the other hosts.
  Dependencies: T005, OD-1, OD-2, OD-4. Target files:
  `scripts/build_native_plugin.py`, plugin build tests. Verification:
  procedure_004, then `quick`. Planned evidence: `evidence/t006.json`; obtained: none.
- [ ] T007 (REQ-004 / SC-005): Register the unchanged `agent-braid` server in Pi's `mcp.json` through the bundled launcher, or implement the OD-3 fallback.
  Explicit `workspaceId`, `reconnect-required` kept; differential test against the
  Codex and Claude results. Dependencies: T005, T006, OD-3. Target files:
  `scripts/build_native_plugin.py`, `agent_braid/tooling_install.py`, tests.
  Verification: procedure_005. Planned evidence: `evidence/t007.json`; obtained: none.
- [ ] T008 (REQ-005 / SC-006): Add the `pi` installer profile and Pi to the host lists; add Pi to the harness host registry as unqualified, offline only.
  Receipt-owned edits only; a modified owned entry refuses with a stable code.
  Coordinate the registry change with SPEC-080 (OpenCode). Dependencies: T005, OD-5.
  Target files: `agent_braid/tooling_install.py`, `agent_braid/tooling_cli.py`,
  `agent_braid/plugin_cli.py`, `install.sh`, `integrations/agent-braid/hosts.json`,
  `agent_braid/harness_hosts.py`, `agent_braid/harness_components.py`,
  `agent_braid/harness_lifecycle.py`, tests. Verification: procedure_006, then
  `quick`. Planned evidence: `evidence/t008.json`; obtained: none.
- [ ] T009 (REQ-006 / SC-007): Implement the read-only `plugin doctor --host pi` diagnosis for skill and server collisions, ThinkRail-imported duplicates and Gentle AI rewrites.
  Runs under a write monitor in tests; one mutation control per finding kind.
  Dependencies: T004, T008. Target files: `agent_braid/plugin_pi.py`,
  `agent_braid/plugin_cli.py`, `tests/test_plugin_pi.py`. Verification:
  procedure_007, then `quick`. Planned evidence: `evidence/t009.json`; obtained: none.
- [ ] T010 (REQ-007 / SC-008): State in setup and docs that Pi has no permission layer and that Agent Braid adds no execution authority; check that no packaged text issues a grant.
  Dependencies: T006. Target files: setup skill text,
  `docs/tooling/NATIVE_PLUGINS.md`, `docs/tooling/INSTALL.md`,
  `docs/tooling/HOSTS.md`, plugin tests. Verification: procedure_008. Planned
  evidence: `evidence/t010.json`; obtained: none.

## Phase P4 — candidate and release

- [ ] T011 (REQ-008 / SC-009): Run the native observation runbook on the built candidate in disposable Pi and ThinkRail profiles.
  Each row observed, contradicted or `unobserved`; a contradiction blocks release.
  Dependencies: T006 to T010. Target files: `t011-runbook.md`,
  `evidence/native-observation.json`. Verification: procedure_009. Planned
  evidence: `evidence/native-observation.json`; obtained: none.
- [ ] T012 (REQ-008 / SC-009): Record the owner release decision for the first alpha after alpha.10 that carries Pi (OD-7), or a no-go.
  Dependencies: T011, green CI on the release candidate. Target files:
  `release-acceptance.md`. Verification: procedure_009. Planned evidence:
  `evidence/release.json`; obtained: none.
