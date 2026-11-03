# SPEC-068: Validation quickstart

Run from the clean clone with the isolated environments. Commands marked
*planned* refer to tests that do not exist until their task lands.

## Spec Kit and repository gates

```bash
.venv-speckit/bin/python -m scripts.validate_spec_kit
```

Expected: `Spec Kit structural gates passed; semantic/human review remains separate.`

```bash
.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick
```

Expected: pass after each increment. `--profile pr` once on the candidate.

## Unit procedures (planned)

```bash
.venv/bin/python -m unittest tests.test_plugin_installer
```

procedure_007: `--host opencode`, `--host all`, `--dry-run`; absent OpenCode refuses.

```bash
.venv/bin/python -m unittest tests.test_tooling_install_opencode
```

procedure_008: JSONC comments and foreign servers preserved; idempotent repeat;
`ambiguous_configuration`, `unowned_collision`, `changed_digest`; rollback.

```bash
.venv/bin/python -m unittest tests.test_plugin_opencode
```

procedure_004: collision and duplicate-guidance findings on fixture trees; entry
source has no forbidden API.

```bash
.venv/bin/python -m unittest tests.test_native_plugin_build
```

procedure_010: OpenCode files in inventory and provenance; Codex/Claude host-read
files byte-identical to a build without the OpenCode target.

## Host matrix (T002, disposable profile)

```bash
export XDG_CONFIG_HOME="$(mktemp -d)" XDG_DATA_HOME="$(mktemp -d)"
opencode --version
opencode plugin add 'github:jayanez/agent-braid#<tag>::path:plugins/agent-braid'
opencode plugin list
opencode mcp list
```

Expected: rows of `evidence/host-matrix.json` filled with version, command and
result, or `unobserved`. User configuration is never touched.

## Native observation (T010, owner or operator)

Clean profile as above; record install, skill and command listing, an
`agent-braid_analyze-work` call on a registered workspace, reconnect and removal in
`evidence/native-observation.json`.
