# SPEC-068 T011 — release readiness for native plugin 0.1.0-alpha.7

**Status: released on 2026-11-04.** `0.1.0-alpha.7` is published on `plugin-dist`
(commit `8f19b1b7`) and tag `agent-braid--v0.1.0-alpha.7`; the outcome is in
[release-acceptance-alpha7.md](release-acceptance-alpha7.md),
[evidence/release-alpha7.json](evidence/release-alpha7.json) and
[owner-authorization-20261104.md](owner-authorization-20261104.md). Below is the
preparation record as written before publication, with the checklist states, the
publication commands (two defects found during publication corrected) and the owner
authorization table brought up to date. No GitHub release was created and no
`validate_spec_kit freeze` was run. This file is the release-readiness record that
SPEC-068 T011 asks for. It states what the release-preparation PR changed and the
commands the owner ran. The Python package keeps its own version line (`0.1.0a2`); only
the plugin moves to `0.1.0-alpha.7`.

Template and base: alpha.6 is the published base and the rollback target (release PR
#1006, record PR #1012, tag `agent-braid--v0.1.0-alpha.6` at `78cc45a3`; see
[release-acceptance-alpha6.md](../046-native-ai-plugins/release-acceptance-alpha6.md)).

## What `0.1.0-alpha.7` carries

OpenCode native plugin (entry module, seven skills including `telemetry-audit`, and the commands `agent-braid-setup` and
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

All three held on 2026-11-04 before the commands below were run.

## Checklist

| Item | State |
| --- | --- |
| Plugin version bumped; focused tests updated | done in this PR |
| Release notes, migration, limits, rollback written | done in this PR |
| README, STATUS, INSTALL, NATIVE_PLUGINS pins moved; README OpenCode qualifier dropped | done in this PR |
| ADR 0037 Accepted; T001 `[x]`; assurance snapshots refreshed for ADR 0037 only | done in this PR |
| `--profile pr` on the final candidate | CI `validate` aggregate green on the PR head |
| `validate_spec_kit freeze` for SPEC-068 | not run; no frozen-commit binding |
| T010 native observation (`evidence/native-observation.json`, `t010-runbook.md`) | done: 20 of 23 rows observed (19 before publication, row 21 after), row 14 fixed in this release, rows 22-23 declared limits |
| Owner final yes | done, 2026-11-04 ("Sí, publicar") |
| Clean build from the merged `develop` commit (`sourceDirty` false) | done |
| Bundled launcher `plugin doctor` on an empty private home reports `pluginVersion` `0.1.0-alpha.7`, `version` `0.1.0a2` | done (build output, distribution commit, tag clone, github-installed copy) |
| Fresh clone of the tag byte-identical to the build output | done (except the root README.md) |
| `plugin-dist` root README updated for OpenCode in the publication commit (it is not build output) | done, owner-approved diff |
| Record PR (`release-acceptance-alpha7.md`, `evidence/release-alpha7.json`, authorization note) | done in the record PR |

Unobserved at preparation time, since resolved: the T010 interactive rows (observed) and
the `github:` transport against `plugin-dist` (row 21, observed after publication).
Still unobserved: Linux, T010 row 23, and native host installs of alpha.7 in Claude Code
and Codex.

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

## Publication commands (run on 2026-11-04; two runbook defects corrected)

The first draft of these commands had two defects, found and worked around during
publication: an unanchored `--exclude README.md` also excluded
`plugins/agent-braid/README.md` (`plugin doctor` then refused with "Plugin package
inventory changed"), and `--home "$(mktemp -d)"` on macOS gave a symlinked `/var` path
that doctor refuses. The commands below carry the fixes.

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
# doctor refuses symlinked homes (on macOS mktemp -d gives a /var symlink), so resolve it:
H=$(cd "$(mktemp -d)" && pwd -P)
"$OUT/plugins/agent-braid/launch" plugin doctor --home "$H"
# expect: pluginVersion 0.1.0-alpha.7, version 0.1.0a2, package verified

# 3. plugin-dist commit (its root README.md is kept; it is not build output)
git clone --branch plugin-dist https://github.com/jayanez/agent-braid.git ~/agent-braid-dist/plugin-dist
cd ~/agent-braid-dist/plugin-dist
# anchor the excludes: a bare README.md would also drop plugins/agent-braid/README.md
rsync -a --delete --exclude /.git --exclude /README.md "$OUT"/ ./
# Edit the root README.md here: add the OpenCode command (`opencode plugin add 'github:jayanez/agent-braid#plugin-dist::path:plugins/agent-braid'`) and mention OpenCode as a third host.
git add -A
git commit -m "dist: Agent Braid 0.1.0-alpha.7 (source ${MERGE_SHA:0:7})" \
  -m "Built from develop $MERGE_SHA (clean source) with scripts/build_native_plugin.py."
./plugins/agent-braid/launch plugin doctor --home "$H"     # again, on the distribution commit

# 4. Annotated tag and push (no force)
git log --oneline -2          # parent must be 78cc45a3 (fast-forward)
git ls-remote --tags origin agent-braid--v0.1.0-alpha.7   # must print nothing
git tag -a agent-braid--v0.1.0-alpha.7 -m "Agent Braid 0.1.0-alpha.7"
git push origin plugin-dist agent-braid--v0.1.0-alpha.7

# 5. Verify from a fresh public clone of the tag
git clone --branch agent-braid--v0.1.0-alpha.7 https://github.com/jayanez/agent-braid.git ~/agent-braid-dist/verify
diff -r --exclude .git "$OUT" ~/agent-braid-dist/verify   # only the root README.md (it exists only on plugin-dist) may differ

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

## Owner authorization

Filled on 2026-11-04 from the owner's decisions relayed by the coordinator; the full
record is [owner-authorization-20261104.md](owner-authorization-20261104.md).

| Field | Value |
| --- | --- |
| Decision | Publish `0.1.0-alpha.7` ("Sí, publicar") |
| Date | 2026-11-04 |
| Source commit authorized | `0eb75d84b6ad5cbe156b5d0c4ff967833f416205` |
| T010 interactive rows reviewed, contradictions found | Rows 01-13 and 15-20 observed; row 14 contradicted the observed candidate and was fixed in #1030 (`96f30b7c`, not re-observed); rows 22-23 unobserved, declared as limits; row 21 observed after publication |
| CI result on the release PR | `validate` aggregate green on head `4405c898` |
| Scope | publication of this plugin version only: `plugin-dist` commit, annotated tag `agent-braid--v0.1.0-alpha.7`, record PR |
| Excluded | native host acceptance, official directory submissions, any further release, any scientific claim |

The conditional authorization of 2026-11-03 was not a final decision; the final decision
is the one in the table above.
