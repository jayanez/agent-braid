# SPEC-060 implementation result (T002-T006)

Obtained on the candidate branch `spec060-i1-portable-prompts`, based on develop
`a1d5c476`. Scope B (owner decision OD-1): only the surface is versioned. Nothing
here is a release, tag, publication or native-host observation. Tasks and
`assurance.json` are not ticked by this record.

## Environment

- Python 3.13 (Homebrew) with `mcp==2.3.0` and `jsonschema` in a scratch venv; Darwin.
- Baseline for goldens and byte comparisons: a detached checkout of develop `a1d5c476`.

## Changed behaviour (code)

| File | Change |
|---|---|
| `agent_braid/tooling_mcp.py` | `SURFACE_VERSION = agent-braid-tooling/v0.2` added; `SCHEMA_VERSION` (v0.1) kept for envelopes, output schemas and provenance. `_PROMPT_TEXT` replaced by the ordered registry `_PROMPTS` (analyze, plan, evidence, then the three `agent-braid-*` aliases) with `_prompt_listing` and `_prompt_get`. `capabilities()` reports `schemaVersion` v0.2, `envelopeSchemaVersion` v0.1, `prompts` (canonical only) and `deprecatedPrompts`. |
| `agent_braid/plugin_mcp.py` | `WorkspaceService.capabilities` pops `prompts`, `deprecatedPrompts`, `envelopeSchemaVersion` and restores the v0.1 `schemaVersion`. No prompt handler is registered (unchanged). |

Unchanged by construction: tool names, input/output schemas, resources, telemetry,
legacy skill install, host configuration, System One verifier, package version.

## Search record (T004)

Commands run from the repository root; results are the complete hit lists (docs
and `specs/` excluded as instructed for T007 and frozen evidence).

1. `grep -rn "agent-braid-tooling/v0\.1" tests agent_braid scripts integrations examples`
   - `agent_braid/tooling_mcp.py:29` the envelope constant (kept).
   - `tests/test_tooling_mcp.py:61` live envelope equality (unchanged, scope B).
   - `tests/test_tooling_present.py:17,220`, `tests/test_tooling_presentation_acceptance.py:13`,
     `tests/test_tooling_skills_acceptance.py:112` synthetic envelope input (unchanged).
   - New assertions added by this change: `tests/test_tooling_mcp.py` (SurfaceVersionTests),
     `tests/test_plugin_mcp.py` (alpha.4 golden tests).
   - `agent_braid/system_one_verified_tooling.py:31` compares the envelope stamp with
     `tooling_mcp.SCHEMA_VERSION`; both stay v0.1, so the System One verifier and its tests
     are unchanged.
2. `grep -rnE "agent-braid-(analyze|plan|evidence)\b" tests agent_braid scripts integrations examples`
   split by meaning:
   - Prompt expectations, changed: `tests/test_tooling_mcp.py` (SDK roster, now six names),
     `tests/test_tooling_mcp_acceptance.py` (registry set), `tests/test_plugin_mcp.py`
     (registry size 6; plugin refuses both name sets).
   - Skill names (legacy skill install, hosts, assets, receipts, plugin skill naming), unchanged:
     `agent_braid/tooling_assets.py`, `agent_braid/tooling_hosts.py`,
     `scripts/run_m45_engineering_readiness.py`, `tests/test_tooling_install.py`,
     `tests/test_tooling_assets.py`, `tests/test_tooling_hosts.py`,
     `tests/test_plugin_skill_naming.py`, `tests/test_tooling_lifecycle_acceptance.py`,
     `tests/test_plugin_legacy.py`, `tests/test_validation_profiles.py`.
   - Fake SDK client returning the three old names, unchanged and still valid:
     `tests/test_installed_tooling.py:151`.
   - **Open item, not changed:** `scripts/verify_installed_tooling.py:564-565` is the
     installed-package probe. It asserts the three v0.1 prompt names and requests
     `agent-braid-evidence`. Its SHA-256 (`e88e0307...f1ce431`) is recorded in frozen
     evidence (`specs/042-ai-tooling-packaging/evidence/sc-001.json`, `sc-008.json`,
     `docs/tooling/evidence/preparation-20261010.json`, System One capsules), so it was
     left byte-identical. Run against a v0.2 candidate it would stop at "prompt roster";
     a new probe revision needs an owner decision (T008/T009 scope).
   - `examples/tooling/prompts.json` holds fixture prompts (`m45-prompt-*`), unrelated.

## Byte-comparison evidence

Goldens in `tests/fixtures/spec060/` were captured from develop `a1d5c476` before any
behaviour change; run ids, artifact ids, the path-dependent `sourceIdentity` and the
candidate version are replaced by placeholders (`tests/spec060_golden.py`).

| Fixture | SHA-256 |
|---|---|
| `plugin-capabilities.json` (alpha.4 plugin capabilities resource) | `fb7ac0317dafc84186468047df3d4136d0465d209dcfe7133e09863e733b3a26` |
| `plugin-analyze-work-envelope.json` | `3243a8c796741fab017c8b59995f8134feac233a199b7095e12a2a86ac9cddd8` |
| `core-capabilities-v01.json` (v0.1 portable capabilities, for key diff) | `bd5fddd377b80624ded3fd1cc907bbbbf3ef3093f0bf814b2183313d3c51c36b` |
| `core-analyze-work-envelope.json` | `75f1c2e2f030f355e6e51ebe054d6f90e50cf01a383cf4d193e5d1cb17d95eb5` |
| `core-analyze-envelope.json` | `e3b641f5cb026c71e17f28578d7bed71964c92566edfa6d74188c0b1264c4847` |

- Portable envelopes (`analyze-work`, `analyze`) of the candidate equal the v0.1 goldens
  byte for byte after normalization (`SurfaceVersionTests`); output-schema const and
  `provenance.schemaVersion` stay v0.1.
- Plugin capabilities resource equals the alpha.4 golden exactly, including through a real
  SDK client in `auto` and `legacy` modes (workspace id substituted); plugin tool envelope
  equals the alpha.4 golden.
- Host configuration preview (`tooling_install.plan(...).preview()`, codex and claude, fixed
  paths, same interpreter), baseline versus candidate, byte-identical:
  `preview-codex.json` `4f21461996445636050dbcc1302068bcfbe95db17343f08f78dd73b1e7be344a`,
  `preview-claude.json` `6cfdff03c1302b5a04dc558e6bd55fb6230bac641facb0d976f54aa11dcb2a7a`.
  (`tooling_install.py` and `tooling_hosts.py` are unmodified; hashes below.)

## Unchanged-file hashes (candidate equals baseline)

| File | SHA-256 |
|---|---|
| `agent_braid/tooling_install.py` | `ba1856d30e7848e194b3f317bd913b9743fd2a906f10a86dd155fd93dca9aa78` |
| `agent_braid/tooling_hosts.py` | `762654b04d8dca3aece3dbc09938f0fb95468db8d8e45d0d673061cf7337bf09` |
| `agent_braid/tooling_telemetry.py` | `15519d927103868b51772569ba43d842feb55f3f3c8b90c0306d43c9355775b5` |
| `agent_braid/system_one_verified_tooling.py` | `128aed194149f648d0a579b9fff7d85e121c10339df7552e1e488363c744d04e` |
| `scripts/verify_installed_tooling.py` | `e88e030718c87fb080f091e7179636e02d416b48a85e2353a00928eecf1ce431` |

Changed code files: `agent_braid/tooling_mcp.py` baseline `4d35b94b...b17194`,
`agent_braid/plugin_mcp.py` baseline `836577af...f1d64`; candidate hashes are in the commit.

## Test results

Negative controls (each fails when the defect is injected): changed canonical text,
missing canonical name, unmarked alias, alias listed under `prompts`, missing
`deprecatedPrompts`, v0.2 stamp on an envelope, changed golden byte, unstripped core
capabilities in the plugin, each leaked key in the plugin capabilities. Test-first order:
each task's new tests were run red before the implementation.

- Targeted: `tests.test_tooling_mcp`, `tests.test_tooling_mcp_acceptance`, `tests.test_plugin_mcp`
  pass with the SDK installed.
- T006 regression set, run unchanged apart from the prompt/capabilities expectations listed
  above: telemetry (`test_tooling_telemetry`, `test_forecast_telemetry`), legacy install and
  lifecycle (`test_tooling_install`, `test_tooling_lifecycle_acceptance`, `test_plugin_legacy`,
  `test_installed_tooling`, `test_plugin_skill_naming`), hosts (`test_tooling_hosts`),
  presentation and skills acceptance, assets, plugin installer/package/registry/update-rollback,
  `test_reproduce_native_plugin`: 218 tests run with the SDK present, all pass, 1 skipped
  (the four reported import errors in that run were the System One modules, which import
  sibling test modules as top-level names).
- System One verified suites (`test_system_one_verified_*`, run with `tests` on `PYTHONPATH`
  as the repository runner does): 133 tests, OK.
- New regression tests: telemetry enum and batch version unchanged; listing and getting all six
  prompts records nothing with `--telemetry local` while a tool call does (positive control);
  installer, host and asset modules do not reference the prompt registry; host preview is
  deterministic and prompt-free.

## Limits

No native Claude Code or Codex observation (T009). The alpha.4 golden is the in-repo behaviour
of develop `a1d5c476`, not a re-download of a published wheel. The package version is
unchanged (T008). Documentation is not updated (T007).
