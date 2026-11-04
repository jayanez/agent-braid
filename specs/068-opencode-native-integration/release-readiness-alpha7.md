# SPEC-068 T011 — release readiness for native plugin 0.1.0-alpha.7

**Status: prepared, not released.** Nothing is tagged, pushed to `plugin-dist`,
published as a GitHub release or milestone, and no `validate_spec_kit freeze` has been
run. This file is the release-readiness record that SPEC-068 T011 asks for. It states
what the release-preparation PR changed, what is still open, and the exact commands the
owner runs after authorizing publication. The Python package keeps its own version line
(`0.1.0a2`); only the plugin moves to `0.1.0-alpha.7`.

Template and base: alpha.6 is the published base and the rollback target (release PR
#1006, record PR #1012, tag `agent-braid--v0.1.0-alpha.6` at `78cc45a3`; see
[release-acceptance-alpha6.md](../046-native-ai-plugins/release-acceptance-alpha6.md)).

## What `0.1.0-alpha.7` carries

OpenCode native plugin (entry module, seven skills including `telemetry-audit`, `agent-braid-setup` and
`agent-braid-reconnect`), `plugin doctor --host opencode`, `install.sh --host opencode`
and `--host all`, the legacy `tooling install --host opencode` profile, the
standard-library `agent_braid.jsonc` reader, and no registry migration. Release notes
(features, migration, known limits, rollback) are in
[NATIVE_PLUGINS.md](../../docs/tooling/NATIVE_PLUGINS.md) under "Version
0.1.0-alpha.7". This PR also includes the held SPEC-068 installer, OpenCode card, docs
and T008 regression (#1027), records the owner's acceptance of ADR 0037 (2026-11-03)
and marks T001 done.

T010 native observation fixes (rows 16 and 17): `analyze-work` with kind `aim` returns
the analyzer's fixed validation message instead of the generic refusal (Git analysis
errors stay masked because they can carry git output), and the OpenCode entry
registers `telemetry-audit` (seven skills; `plugin doctor` collision ids updated). The
`analyze-work` schema still does not describe the AIM request shape; that is a known
limit planned for a later release.

Version locations moved to `0.1.0-alpha.7`: `VERSION` in
`scripts/build_native_plugin.py` (it stamps both host manifests, the marketplace
entries, the OpenCode `package.json`, `provenance.json` and `package-inventory.json`),
and the pins in `tests/test_plugin_package.py`, `tests/test_plugin_update_rollback.py`,
`tests/test_plugin_mcp.py` and `tests/test_spec060_release.py`. Published pins in
`README.md`, `docs/STATUS.md`, `docs/tooling/INSTALL.md` and
`docs/tooling/NATIVE_PLUGINS.md` now name alpha.7 with alpha.6 as the rollback target.

## Conditions before publication (owner's conditional authorization, 2026-11-03)

The owner gave a conditional authorization. Publication happens only when **all** hold:

1. SPEC-068 T010 interactive rows show no contradiction of what the docs claim.
2. CI is green on the release PR (required `pr` profile checks).
3. The owner gives a final explicit yes after seeing 1 and 2.

Until then nothing below is run. Merge this PR only together with the owner's decision to
publish, because the pins on `develop` already read "published".

## Checklist

| Item | State |
| --- | --- |
| Plugin version bumped; focused tests updated | done in this PR |
| Release notes, migration, limits, rollback written | done in this PR |
| README, STATUS, INSTALL, NATIVE_PLUGINS pins moved; README OpenCode qualifier dropped | done in this PR |
| ADR 0037 Accepted; T001 `[x]`; assurance snapshots refreshed for ADR 0037 only | done in this PR |
| `--profile pr` on the final candidate (`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile pr`) | CI result on the PR; owner re-runs on the merge commit |
| `validate_spec_kit freeze` for SPEC-068 | **open**: owner candidate step after T010; needs a clean commit |
| T010 native observation (`evidence/native-observation.json`, `t010-runbook.md`) | **open**: interactive rows pending; unobserved items stay open |
| Owner final yes | **open** |
| Clean build from the merged `develop` commit (`sourceDirty` false) | open, owner or authorized operator |
| Bundled launcher `plugin doctor` on an empty private home reports `pluginVersion` `0.1.0-alpha.7`, `version` `0.1.0a2` | open, part of the commands below |
| Fresh clone of the tag byte-identical to the build output | open |
| `plugin-dist` root README updated for OpenCode in the publication commit (it is not build output) | open, owner or operator |
| Record PR (`release-acceptance-alpha7.md`, `evidence/release-alpha7.json`, authorization note) | open, after publication |

Still unobserved at preparation time: the T010 interactive rows, the `github:` transport
against `plugin-dist`, Linux, call-time approval prompts, and native host installs of
alpha.6 and alpha.7 in Claude Code and Codex.

## Rollback to alpha.6

1. Claude Code and Codex: reinstall `0.1.0-alpha.6` from tag
   `agent-braid--v0.1.0-alpha.6` (`install.sh --host codex` or `--host claude` with
   `--ref agent-braid--v0.1.0-alpha.6`, never `--host all`, which would try OpenCode;
   or the host's marketplace commands pinned to that tag). The registry and results are accepted
   unchanged; alpha.7 adds no registry member.
2. OpenCode: run `opencode plugin remove` with the exact source string from the
   configuration (the plugin id and `agent-braid` answer "not configured"), then
   `opencode reload`. Alpha.6 has no OpenCode package. The cache directory and Agent
   Braid's registry and results stay.
3. A legacy `tooling install --host opencode` entry is independent: `tooling uninstall
   --host opencode` removes only what it owns.
4. `plugin-dist` itself is rolled back by the owner only, by pushing a new commit that
   restores the alpha.6 tree (never a force-push); the alpha.7 tag is then retired by the
   owner's decision.

## Owner publication commands (run only after the conditions above)

Set `MERGE_SHA` to the merge commit of the release PR on `develop`. Use Python 3.12 and
keep all paths outside the checkout. The convention (commit message, tag name, root
README kept on `plugin-dist`) follows the alpha.6 publication.

```sh
# 1. Clean source at the merged commit
MERGE_SHA=<merge commit on develop>
git clone https://github.com/jayanez/agent-braid.git ~/Repos/Personal/agent-braid-release
cd ~/Repos/Personal/agent-braid-release
git checkout --detach "$MERGE_SHA"
git status --short            # must print nothing
python3.12 -m venv .venv && .venv/bin/python -m pip install build

# 2. Build (downloads pinned runtime archives and hash-locked wheels)
OUT=$HOME/agent-braid-dist/alpha7-out; CACHE=$HOME/agent-braid-dist/runtime-cache
[ -n "$MERGE_SHA" ] || exit 1; rm -rf "$OUT"   # the build refuses an existing output
.venv/bin/python scripts/build_native_plugin.py --output "$OUT" --cache "$CACHE"
grep -n '"sourceDirty"' "$OUT/plugins/agent-braid/provenance.json"   # must be false
"$OUT/plugins/agent-braid/launch" plugin doctor --home "$(mktemp -d)"
# expect: pluginVersion 0.1.0-alpha.7, version 0.1.0a2, package verified

# 3. plugin-dist commit (its root README.md is kept; it is not build output)
git clone --branch plugin-dist https://github.com/jayanez/agent-braid.git ~/agent-braid-dist/plugin-dist
cd ~/agent-braid-dist/plugin-dist
rsync -a --delete --exclude .git --exclude README.md "$OUT"/ ./
# Edit the root README.md here: add the OpenCode command (`opencode plugin add 'github:jayanez/agent-braid#plugin-dist::path:plugins/agent-braid'`) and mention OpenCode as a third host.
git add -A
git commit -m "dist: Agent Braid 0.1.0-alpha.7 (source ${MERGE_SHA:0:7})" \
  -m "Built from develop $MERGE_SHA (clean source) with scripts/build_native_plugin.py."
./plugins/agent-braid/launch plugin doctor --home "$(mktemp -d)"     # again, on the distribution commit

# 4. Annotated tag and push (no force)
git log --oneline -2          # parent must be 78cc45a3 (fast-forward)
git ls-remote --tags origin agent-braid--v0.1.0-alpha.7   # must print nothing
git tag -a agent-braid--v0.1.0-alpha.7 -m "Agent Braid 0.1.0-alpha.7"
git push origin plugin-dist agent-braid--v0.1.0-alpha.7

# 5. Verify from a fresh public clone of the tag
git clone --branch agent-braid--v0.1.0-alpha.7 https://github.com/jayanez/agent-braid.git ~/agent-braid-dist/verify
diff -r --exclude .git --exclude README.md "$OUT" ~/agent-braid-dist/verify   # no output expected

# 6. Values the record PR needs
cd ~/agent-braid-dist/verify
git rev-parse HEAD agent-braid--v0.1.0-alpha.7            # distribution commit, tag object
shasum -a 256 plugins/agent-braid/package-inventory.json plugins/agent-braid/provenance.json sources/agent-braid-0.1.0-alpha.7-source.tar.gz
find . -path ./.git -prune -o -type f -print | wc -l       # file count
```

Then open the **record PR** on `develop`, mirroring #1012: `release-acceptance-alpha7.md`,
`evidence/release-alpha7.json` (published distribution commit, previous distribution
`78cc45a3`, tag object, source commit, inventory, provenance and source-archive hashes,
observations, not-observed list, limits), an owner-authorization note, and the filled
authorization below. Abort at any hash, doctor or diff failure and report.

## Owner authorization (to be completed by the owner; no approval is written here)

| Field | Value |
| --- | --- |
| Decision | _owner fills: publish `0.1.0-alpha.7` / do not publish_ |
| Date | _owner fills_ |
| Source commit authorized | _owner fills (`MERGE_SHA`)_ |
| T010 interactive rows reviewed, contradictions found | _owner fills_ |
| CI result on the release PR | _owner fills_ |
| Scope | publication of this plugin version only: `plugin-dist` commit, annotated tag `agent-braid--v0.1.0-alpha.7`, record PR |
| Excluded | native host acceptance, official directory submissions, any further release, any scientific claim |

The conditional authorization of 2026-11-03 (conditions above) is not a final decision;
this table stays empty until the owner completes it.
