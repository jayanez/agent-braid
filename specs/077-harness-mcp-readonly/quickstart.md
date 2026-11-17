# Quickstart: SPEC-077 validation

Draft stage: only the structural checks run; the tests named below do not exist yet.

```sh
python3 -m scripts.validate_spec_kit snapshot specs/077-harness-mcp-readonly
python3 -m scripts.validate_spec_kit
```

Expected: the snapshot records `current` authority hashes; validation passes, or, in a
worktree that shares a Git object store, fails only with `public repository contains
unreachable objects` and passes in a fresh full clone (see `docs/development/SPEC_KIT.md`).

Codex contract review (read-only, from the worktree root):

```sh
"/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex" exec -s read-only -C "$PWD" \
  --output-schema specs/077-harness-mcp-readonly/review/codex-contract-20261116.schema.json \
  -o specs/077-harness-mcp-readonly/review/codex-contract-20261116.out.json \
  "$(cat specs/077-harness-mcp-readonly/review/codex-contract-20261116.md)"
```

Expected: one JSON object matching the schema; findings are triaged under T002.

After implementation (T003–T005):

```sh
.venv-speckit/bin/python -m unittest tests.test_harness_mcp -v
.venv-speckit/bin/python -m unittest discover -s tests -p "test_harness*.py" -v
```

Expected: all pass; each mutation control in `evidence/t004.json` fails when its
guard is removed.
