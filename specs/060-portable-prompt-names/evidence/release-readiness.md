# SPEC-060 release readiness (T008, procedures 006 and 008)

**Nothing was released.** No tag, no wheel or sdist for distribution, no upload, no
GitHub release, no plugin build or release, no remote issue. This record is
preparation for a later owner release decision.

Observed 2026-10-26/27 on macOS arm64, CPython 3.13 with `mcp==2.3.0` and
`jsonschema` in a scratch venv, on branch `spec060-i3-release-prep` built on
develop `6d659943` and then merged with develop `0560a338`.

## Versions and surfaces

| Item | Before | Candidate | Note |
|---|---|---|---|
| Python package (`pyproject.toml`, `agent_braid.__version__`, `serverInfo.version`) | 0.1.0a1 | 0.1.0a2 | OD-3 |
| Portable surface contract | `agent-braid-tooling/v0.1` | `agent-braid-tooling/v0.2` | scope B |
| Envelope schema, output schemas, provenance | v0.1 | v0.1 | unchanged |
| Plugin release (`VERSION` in `scripts/build_native_plugin.py`) | 0.1.0-alpha.4 | 0.1.0-alpha.4 | not bumped; asserted by test |
| `integrations/agent-braid/hosts.json` `version` | 0.1.0a1 | 0.1.0a1 (unchanged) | see below |
| `scripts/verify_installed_tooling.py` | sha256 `e88e0307...f1ce431` | identical | asserted by test |

`hosts.json` versions the host-asset metadata (its hash is recorded in install
asset provenance and frozen evidence); the assets did not change, so it does not
track the package and was left alone. A test pins this so the decision stays visible.

## Changed files (release preparation)

`pyproject.toml`, `agent_braid/__init__.py`, `README.md` (package version line);
new `scripts/verify_installed_tooling_v2.py`, `docs/tooling/INSTALLED_VERIFIERS.md`
(which verifier applies to which contract), `tests/test_spec060_release.py`,
`specs/060-portable-prompt-names/release-notes-0.1.0a2.md`; bookkeeping: tasks,
assurance, pinned M4.5 task counts (131 tasks, 99 checked, 32 open).

Pins of `0.1.0a1` searched in `tests scripts agent_braid integrations docs
examples`: live assertions that follow the package version: none other than the
two declarations above (no test compared `__version__` to a literal). Left
unchanged on purpose: `scripts/verify_installed_tooling.py:391` (frozen v0.1
verifier), `tests/spec060_golden.py` `GOLDEN_CANDIDATE_VERSION` (the golden
captured from 0.1.0a1; normalization maps the candidate version to it),
`tests/test_tooling_capture.py`, `test_tooling_sessions.py`,
`test_tooling_evaluation.py` (synthetic candidate values),
`tests/test_linux_tooling_reproduction.py` and `docs/tooling/linux-reproduction/`
(reproduce the frozen 0.1.0a1 wheel), `docs/tooling/TECHNICAL_STATUS.md`,
`docs/tooling/evidence/**`, `docs/tooling/installed-core-summary-20261010.json`,
`examples/tooling/*registration-draft*.json` (registration fixtures for the
evaluated candidate), `docs/system-one/**` and `specs/**/evidence/**` (frozen).

## Migration and rollback fixtures (procedure_006)

`tests/test_spec060_release.py::MigrationAndRollbackTests`, owned temporary homes,
no network, for hosts codex and claude:

- install with `tooling_install.plan/apply` (source-checkout bundle), snapshot every
  file under the host destination (configuration, skills, receipt);
- upgrade to the candidate: repeat `install` and `update` plan no change and apply
  reports `unchanged`; all bytes identical;
- rollback to the earlier roster: `update` plans no change; all bytes identical;
- the candidate resolves canonical names and aliases with identical text and
  refuses unknown names; with the registry reduced to the v0.1 roster the three
  old names resolve and the three new names are refused;
- a real SDK client starts the server from the written configuration and lists
  `analyze, plan, evidence, agent-braid-analyze, agent-braid-plan, agent-braid-evidence`;
- the unchanged v0.1 verifier probe accepts the earlier roster and rejects the
  candidate roster at "prompt roster"; the v0.2 probe accepts the candidate roster
  and rejects the v0.1 roster, a missing canonical name and an unmarked alias
  (negative controls); the v0.2 adapter refuses if the v0.1 probe text changes;
  the v0.2 metadata check accepts 0.1.0a2 and refuses 0.1.0a1.

Limits: the "earlier package" is the candidate registry reduced to the v0.1 roster,
not an installed earlier wheel. Installer, host and receipt sources are
byte-identical to the earlier package, which is why they are not swapped.

## Not verified

- No wheel or sdist was built: the environment has no `setuptools` or `build`
  installed and `pyproject.toml` requires `setuptools>=68` in an isolated build,
  which would download. Owner chose "prepare only"; metadata checks of a built
  artifact are therefore untested beyond the synthetic wheel metadata in the test.
- The verifiers were not run against a real installed wheel (`--execute-installed`).
- The native plugin was not rebuilt. Its tool envelopes and status carry the core
  `candidateVersion`/`version` string, which now reads 0.1.0a2; the alpha.4 golden
  comparison normalizes that value. A plugin rebuild would embed the new wheel and
  is a separate owner decision.
- No native Claude Code or Codex observation (T009); no owner review (T001); no
  owner release decision; T011 deferred.
- How portable users obtain the package (local wheel versus a public index) is not
  established by the repository; the release notes name no channel.

## Results

Targeted run after merging develop `0560a338`: 253 tests OK (1 skipped) over
`test_spec060_release`, `test_tooling_mcp`, `test_tooling_mcp_acceptance`,
`test_plugin_mcp`, `test_installed_tooling`, `test_tooling_install`,
`test_tooling_hosts`, `test_tooling_telemetry`, `test_validation_profiles`,
`test_linux_tooling_reproduction`, `test_reproduce_native_plugin`,
`test_plugin_package`. The `--profile pr` receipt is in `pr-profile-result.md`.
