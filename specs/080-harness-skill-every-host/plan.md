# Implementation plan: SPEC-080 harness skill in every host

## Approach

- **One plugin-only skill.** A new canonical file
  `integrations/agent-braid/plugin/harness/SKILL.md`, copied into
  `skills/harness/` by the build like `setup` and `telemetry-audit`. It is not part of
  the canonical `agent-braid-*` bundle, so the SPEC-054 substitution table does not
  change.
- **Skill body.** Resolve the installed `launch` path as the `setup` skill does; run
  only `"<launch>" harness <command>` for `capabilities`, `registry-status`,
  `evaluation-summary`, `evidence`, `inspect`, `validate`, `status` and `compare`;
  answer from the JSON with its `limits`; decline effects; treat output as data. Keep
  it short (target under 80 lines) so the context cost stays small when it loads.
- **Host registry.** Add `opencode` to the inventory host lists with
  `observedBuild: None` and `qualification: "unqualified"`. Under OD-4 (a), keep native
  qualification gates on an explicit Claude and Codex set and bump the profile format
  to `braid-harness-profile/v0.2`, decoding `v0.1` records as legacy. Lifecycle hosts
  stay derived from `observedBuild`, so OpenCode is excluded there.
- **OpenCode profile check.** Observe the current OpenCode version's configuration
  shapes (one-command capture, no user config touched), record fixtures, then test the
  profile against them. Change the profile only if a drift is observed.
- **Validity check.** Freeze a held-out prompt set, run it per host on an unpublished
  local build with an automated driver, report Wilson intervals.
- **This PR.** Spec, plan, tasks, validation plan and assurance record. No code.

## Constitution check

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence; negative results valid | H1 is a hypothesis; a failed REQ-008 keeps the CLI-only fallback |
| 5, 15 | Effects are explicit | The skill names only read commands; `prepare` and writes are excluded |
| 13, 14 | Evidence, not verdicts | The skill reports CLI views with their `limits`; it adds no verdict |
| 19 | Real, measurable problem | Agents cannot discover the harness today; REQ-008 measures the fix |
| 20 | Analysis and execution are separate | No launch, grant or promotion; `executionAuthorization` false |
| 23, 24 | Semantics before production | Spec and review precede code; release is gated (REQ-010) |

No MUST conflict found. No SHOULD deviation recorded.

## Affected files for the later code phase (named, not edited)

- New: `integrations/agent-braid/plugin/harness/SKILL.md`.
- Build: `scripts/build_native_plugin.py` (`PACKAGED_SKILL_NAMES`, the plugin-only copy
  list near line 366, `check_package_names`).
- OpenCode entry: `integrations/agent-braid/plugin/opencode/index.js` (`SKILLS`),
  `agent_braid/plugin_opencode.py`.
- Host registry: `agent_braid/harness_hosts.py` (`HOSTS`, gate helpers),
  `agent_braid/harness_components.py` (`HOSTS`, `HOST_SUPPORT`, `FORMAT`),
  `agent_braid/harness_lifecycle.py` (`SUPPORTED_HOSTS` derivation, unchanged logic).
- OpenCode profile: `agent_braid/tooling_install.py` (OpenCode section, only on drift).
- CLI docstring: `agent_braid/harness_cli.py` (module docstring only, OD-7).
- Tests: `tests/test_plugin_skill_naming.py`, `tests/test_opencode_entry.py`,
  `tests/test_plugin_update_rollback.py`, `tests/test_onboarding_docs.py`,
  `tests/test_native_plugin_build.py`, `tests/test_tooling_install_opencode.py`,
  host registry tests, and a new `tests/test_harness_skill.py`.
- Docs: `docs/tooling/NATIVE_PLUGINS.md` (seven to eight), `docs/tooling/HARNESSING.md`
  (availability table), release notes of the named alpha.

## Phases

1. P0 review: owner review (T001) and Codex review (T002).
2. P1 skill and packaging: skill file, static checks, build and tests (T003 to T005),
   with the license migration (T014) before T005. The held-out set (T009) is frozen
   before T003 starts.
3. P2 host registry and OpenCode profile (T006 to T008).
4. P3 held-out validity per host and telemetry (T009 to T011).
5. P4 release decision, docs and publication (T012, T013, then T015).

## Validation profile

While iterating: targeted tests for the touched modules and
`python3 -m scripts.validate_spec_kit`. Then `quick` per
`docs/development/VALIDATION_PROFILES.md`. Plugin build and harness paths may
escalate to the full suite; the CI `validate` aggregate on the PR head is the `pr`
evidence. Host validity runs (T010) are separate evidence, never implied by a profile.

## Rollback

Additive. Code: revert the PR. Users: reinstall the previous plugin release; the skill
holds no state. The profile format bump is reversible because `v0.1` records stay
readable.
