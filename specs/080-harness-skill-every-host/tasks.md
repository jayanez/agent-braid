# SPEC-080: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.
No task here launches a native harness session, issues a grant, changes user host
configuration or publishes before T015.

## Phase P0 — review

- [x] T001 (REQ-001 / SC-001): Owner review of spec, plan and ADR 0044; decide or defer OD-1..OD-7, and accept or reject ADR 0044.
  Dependencies: this PR merged. Target files: `evidence/t001-owner-review.md`.
  Verification: procedure_001. Planned evidence: `evidence/t001-owner-review.md`;
  obtained: that record (2026-11-23). All seven owner decisions were answered with the
  recommended option. ADR 0044 is Accepted. OpenCode joins the inventory with
  profile `v0.2`. Validity uses the SPEC-077 shape and requires all three hosts.
  Release is alpha.10.
- [x] T002 (REQ-001 / SC-001): Run the Codex review of this spec on the merged candidate; record raw output and triage each finding (confirmed, fixed, rejected with reason).
  Dependencies: this PR merged. Target files: `review/`, `evidence/review/`.
  Verification: procedure_001. Planned evidence:
  `evidence/review/codex-t002-20261123.json` and its raw output; obtained: both
  (2026-11-24, raw sha256 `d7a82a93…`). Six findings, all confirmed and applied to this
  spec (S80-001 to S80-006), adding T014 and T015. Not human review.

## Phase P1 — skill and packaging

- [x] T003 (REQ-002 / SC-002 REQ-003 / SC-003 REQ-004 / SC-004): Write the portable `harness` skill: four frontmatter fields (OD-2), launcher resolution as in `setup`, the eight read commands, decline rules and the untrusted-data rule.
  Dependencies: T001 (OD-1, OD-2), T002 confirmed findings applied, T009 (frozen
  before any skill text exists). Target files:
  `integrations/agent-braid/plugin/harness/SKILL.md`. Verification: procedure_003,
  procedure_004. Planned evidence: `evidence/t003.json`; obtained: that file (2026-11-24): the skill, written after the T009 freeze;
  eight read commands, decline and untrusted-data rules, no held-out overlap.
- [x] T004 (REQ-002 / SC-002 REQ-003 / SC-003 REQ-004 / SC-004): Static tests of the skill: frontmatter keys, name, command set equals the allowlist, no forbidden command, decline and untrusted-data rules; one mutation control per check.
  Dependencies: T003. Target files: `tests/test_harness_skill.py`. Verification:
  procedure_002, procedure_003, procedure_004, then `quick`. Planned evidence:
  `evidence/t004.json`; obtained: that file (2026-11-24): 14 tests, ten mutation controls; CI is the
  `pr` evidence (local `quick` stops at the environmental publication gate).
- [ ] T005 (REQ-005 / SC-005): Package eight skills for Claude Code, Codex and OpenCode: build list, OpenCode entry, plugin tests and docs move from seven to eight; byte-identical skill in every layout.
  Dependencies: T003, T014. Target files: `scripts/build_native_plugin.py`,
  `integrations/agent-braid/plugin/opencode/index.js`, `agent_braid/plugin_opencode.py`,
  `tests/test_plugin_skill_naming.py`, `tests/test_opencode_entry.py`,
  `tests/test_plugin_update_rollback.py`, `tests/test_onboarding_docs.py`,
  `tests/test_native_plugin_build.py`, `docs/tooling/NATIVE_PLUGINS.md`.
  Verification: procedure_005, then `quick`. Planned evidence: `evidence/t005.json`;
  obtained: none.

## Phase P2 — host registry and OpenCode profile

- [ ] T006 (REQ-006 / SC-006): Add `opencode` to the harness host registry as unqualified with no observed build, per OD-4; keep Claude and Codex rows and gates unchanged; derived lifecycle hosts exclude OpenCode.
  Classify every importer of the host lists or `HOST_SUPPORT` as inventory or gate set
  (`harness_hooks`, `harness_advisory`, `harness_lifecycle`, `harness_orchestration`,
  `harness_skills`, `harness_tools`, `harness_hosts_native`) and record the table in the
  evidence; hooks stay on the gate set; records written before the change still verify.
  `harness_hosts_native.py` and the SPEC-065 frozen files are not edited.
  Dependencies: T001 (OD-4). Target files: `agent_braid/harness_hosts.py`,
  `agent_braid/harness_components.py`, `agent_braid/harness_lifecycle.py`,
  `agent_braid/harness_hooks.py`, `agent_braid/harness_advisory.py`, their tests.
  Verification: procedure_006, then `quick`. Planned evidence:
  `evidence/t006.json`; obtained: none.
- [ ] T007 (REQ-007 / SC-007): Observe the current OpenCode configuration shapes with one command in a temporary home (version, `plugins`, `permissions`, `mcp.servers`, `skills`); record redacted fixtures; touch no user configuration.
  Dependencies: T001. Target files: `evidence/t007-opencode-schema.json`, test
  fixtures. Verification: procedure_007. Planned evidence:
  `evidence/t007-opencode-schema.json`; obtained: none.
- [ ] T008 (REQ-007 / SC-007): Test the OpenCode install profile against the T007 fixtures (install, doctor, remove); fix an observed drift or refuse with a stable code; no guessed shape; then confirm the observed OpenCode version, in the same temporary home, lists the installed server, or record `opencode-acceptance-unobserved`.
  Dependencies: T007. Target files: `agent_braid/tooling_install.py` (only on drift),
  `tests/test_tooling_install_opencode.py`. Verification: procedure_007, then `quick`.
  Planned evidence: `evidence/t008.json`; obtained: none.

## Phase P3 — host validity and telemetry

- [x] T009 (REQ-008 / SC-008): Author and freeze the held-out prompt set, the REQ-008 scoring rule, the fixed retry message and the target (OD-3), with at least two forbidden-effect prompts; record its SHA-256 before any run and before any skill text exists.
  Dependencies: T001 (OD-3). Target files: `evidence/heldout-set.json`.
  Verification: procedure_008. Planned evidence: `evidence/heldout-set.json`;
  obtained: that file (2026-11-24, sha256
  `83901c9bcccbd8dd77890aa71c1dea3a96e6675b3795c4fa93fa12c1ddbce8b7`, 5081 bytes), frozen at
  develop `af798c1f` with no harness skill text present: 10 prompts (8 relevant, 2
  forbidden-effect, 3 in Spanish), the REQ-008 scoring, the retry message and the
  OD-3 target.
- [ ] T010 (REQ-008 / SC-008): Run the frozen set in Claude Code, Codex and OpenCode with the automated driver on an unpublished local build; report per-host validity with Wilson 95 % intervals and failure signatures. A miss is a negative result.
  Dependencies: T005, T009. Target files: `evidence/heldout-claude.json`,
  `evidence/heldout-codex.json`, `evidence/heldout-opencode.json`. Verification:
  procedure_008. Before the first run, refuse any prompt that shares five or more
  consecutive words with `SKILL.md`. Planned evidence: those three files; obtained: none.
- [ ] T011 (REQ-009 / SC-009): Test telemetry: without a telemetry request no command carries `--telemetry local`; with one under OD-5 (a), `harness-*` counts rise by the calls made and store no record, path, hash or argument.
  Dependencies: T003, T001 (OD-5). Target files: `tests/test_harness_skill.py`.
  Verification: procedure_009. Planned evidence: `evidence/t011.json`; obtained: none.

## Phase P4 — release decision

- [ ] T012 (REQ-010 / SC-010): Record the release decision against the gate (T004, T005, T006, T008, T010 under OD-6, T002 findings, owner acceptance): "ship in the alpha named under OD-7" or "not shipped". Publishes nothing.
  Dependencies: T002, T004, T005, T006, T008, T010, T011. Target files:
  `evidence/t012-release.json`. Verification: procedure_010. Planned evidence:
  `evidence/t012-release.json`; obtained: none.
- [ ] T013 (REQ-010 / SC-010): Update docs for the T012 outcome: `HARNESSING.md` availability table, the `harness_cli.py` module docstring (OD-7) and release notes.
  Dependencies: T012. Target files: `docs/tooling/HARNESSING.md`,
  `agent_braid/harness_cli.py`, release notes. Verification: procedure_010. Planned
  evidence: `evidence/t013.json`; obtained: none.

## Phase P5 — added by the T002 review

- [ ] T014 (REQ-005 / SC-005): Move `license` into `metadata` in the seven existing skills (OD-2) and make `agent_braid/tooling_assets.py` and the build checks read `metadata.license`; a top-level `license` or a missing `metadata.license` fails, with one mutation control each.
  Dependencies: T001 (OD-2). Target files: `integrations/agent-braid/skills/*/SKILL.md`,
  `integrations/agent-braid/plugin/setup/SKILL.md`,
  `integrations/agent-braid/plugin/telemetry-audit/SKILL.md`,
  `agent_braid/tooling_assets.py`, `scripts/build_native_plugin.py`, their tests.
  Verification: procedure_005, then `quick`. Planned evidence: `evidence/t014.json`;
  obtained: none.
- [ ] T015 (REQ-010 / SC-010): Publish the skill in the alpha named under OD-7 only after a "ship" decision (T012) and the documentation check (T013); after "not shipped", record that nothing was published.
  Dependencies: T012, T013. Target files: `evidence/t015-publication.json`.
  Verification: procedure_010. Planned evidence: `evidence/t015-publication.json`;
  obtained: none.
