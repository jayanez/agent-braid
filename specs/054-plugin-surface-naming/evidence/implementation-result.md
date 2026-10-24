# SPEC-054 implementation result (T002–T008)

Observed on 2026-10-24, macOS arm64, CPython 3.13.11 in an isolated virtual
environment with `mcp==2.3.0` and `jsonschema`. Source: branch built on
`origin/develop` `14bab864`. The work of T002–T004, T007 and T008 was reviewed and
merged as pull requests [#688](https://github.com/jayanez/agent-braid/pull/688)
(T002, T004), [#687](https://github.com/jayanez/agent-braid/pull/687) (T003, T007)
and [#686](https://github.com/jayanez/agent-braid/pull/686) (T008) into the
`claude/spec-plugin-naming-4f32e1` integration branch, each with successful
checks (the remaining checks were skipped), and reached `develop` through
[#684](https://github.com/jayanez/agent-braid/pull/684).

## Commands and outcomes

Every command is `python -m unittest <modules>` from the repository root.

| Task | Modules | Outcome |
| --- | --- | --- |
| T002, T004 | `tests.test_plugin_skill_naming tests.test_plugin_package` | 22 tests OK (1 skipped) |
| T003 | `tests.test_plugin_mcp` | 17 tests OK |
| T005 | `tests.test_tooling_mcp tests.test_tooling_mcp_acceptance tests.test_installed_tooling tests.test_tooling_install tests.test_tooling_hosts tests.test_tooling_assets tests.test_plugin_legacy` | 106 tests OK, unchanged |
| T006, T007 | `tests.test_plugin_update_rollback tests.test_plugin_registry tests.test_tooling_telemetry` | 53 tests OK |

A single combined run of all thirteen distinct modules above reported 198 tests OK,
1 skipped.

## Per-task evidence

- **T002**: `check_package_names` in `scripts/build_native_plugin.py` pins plugin,
  marketplace, server-key and tool names; negative controls in
  `tests/test_plugin_skill_naming.py` (tampered server key, tampered plugin and
  marketplace names, renamed directory) fail as required.
- **T003**: the plugin MCP server advertises no prompts and publishes
  `agent-braid-plugin/v0.2`; `tests/test_plugin_mcp.py` uses the SDK client.
- **T004**: packaged skills are `analyze`, `plan`, `evidence`, `execute`, `recover`
  and `setup`; bodies equal the canonical bodies after the declared substitutions;
  an unmapped prefixed reference fails.
- **T005**: the portable server and legacy install suites pass without edits to the
  tests or the code under test.
- **T006**: `VERSION` is `0.1.0-alpha.4`. `tests/test_plugin_update_rollback.py`
  builds an alpha.3-equivalent prefixed package beside a v0.2 registry and a result
  file in owned fixtures, applies the alpha.4 package files built with the real
  packaging transform, then restores alpha.3. The registry and results SHA-256
  digests are identical at every step and both packages verify. The release,
  migration and rollback note is in `docs/tooling/NATIVE_PLUGINS.md`.
- **T007**: the telemetry tests pass unchanged; the `mcp` operation enum and batch
  contract were not modified.
- **T008**: `docs/tooling/NATIVE_PLUGINS.md` shows `/agent-braid:<skill>` for Claude
  Code and the skill-selection form for Codex; a search found no claim that Codex
  displays MCP prompts.

## Limits

Fixture and unit evidence only. Nothing was installed in a native Codex or Claude
Code profile (T009 stays open), the Codex qualified skill name is unobserved, the
owner review of the policy (T001) is pending, and no release, tag or
`plugin-dist` change was made. Alpha.4 is an unpublished candidate.
