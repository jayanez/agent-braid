# Native plugin release acceptance — alpha.7

`0.1.0-alpha.7` (SPEC-068, OpenCode as the third native host) is published on
`plugin-dist` and annotated tag `agent-braid--v0.1.0-alpha.7` (tag object
`4057a71cf5df27cc37b2001d55ceb4d8057455dd`), both resolving to commit
`8f19b1b7a806ee88d8adb38145491abbfac376b5` (a fast-forward of `78cc45a3`, the alpha.6
distribution), built from develop `0eb75d84b6ad5cbe156b5d0c4ff967833f416205`
(release PR #1030). It adds the OpenCode native plugin, `plugin doctor --host
opencode`, `install.sh --host opencode` and `--host all`, and the legacy `tooling
install --host opencode` profile; it adds no registry migration. Hashes, file counts and
the tag object were re-derived from a fresh public clone; see
[evidence/release-alpha7.json](evidence/release-alpha7.json). Publication ran under the
owner's decisions recorded in
[owner-authorization-20261104.md](owner-authorization-20261104.md). The preparation
record is [release-readiness-alpha7.md](release-readiness-alpha7.md).

| Artifact | SHA-256 |
| --- | --- |
| `plugins/agent-braid/package-inventory.json` | `a71a3847409f91ea5419c2980efb1f8dde44ea0524ec2a173e55638922d55a45` |
| `plugins/agent-braid/provenance.json` | `3e00f4b0050f8ceafa917a342c72f31d8866e954db96795471f6c59c4a61f64f` |
| `sources/agent-braid-0.1.0-alpha.7-source.tar.gz` | `f2a07b59ada8f10d82eea4e37ea7eff056c086cdd66712cbada544ccdc029f7c` |

The tag tree holds 8,004 files (excluding `.git`); the package inventory lists 7,998.

## Observations obtained

macOS arm64, agent-operated:

- Release PR #1030 squash-merged as `0eb75d84` (head before merge
  `4405c898ff3ccbeae05526f3f686d8f3b35b5de4`, CI `validate` aggregate green). The
  T010 evidence PR #1031 merged as `11e5bf762bddc4ce8b8182be22214664a7e6b9a5`.
- Clean release build from a fresh clone at the merge commit (`git status --short`
  empty) with Python 3.12.13: `scripts/build_native_plugin.py` reported status built,
  version `0.1.0-alpha.7`, platforms `macos-arm64` and `linux-x86_64`, provenance
  `sourceDirty` false.
- `plugin-dist` commit `8f19b1b7` carries the message `dist: Agent Braid 0.1.0-alpha.7
  (source 0eb75d8)`. Its root `README.md` is not build output; it was edited by hand
  with a diff the owner approved: OpenCode as a third host, the `opencode plugin add`
  command, installer `--host all`, and the OpenCode reconnect step.
- The branch and the annotated tag were pushed without force.
- The bundled launcher's `plugin doctor`, run against an empty canonical private home on
  the build output, on the `plugin-dist` commit, on a fresh public clone of the tag and
  on the github-installed copy, reported `pluginVersion` `0.1.0-alpha.7`, package
  `version` `0.1.0a2` and a verified package of 7,998 files. On the github-installed
  copy `plugin doctor --host opencode` reported no findings.
- A fresh public clone of the tag is identical to the build output under `diff -r`
  except the root `README.md`, which exists only on `plugin-dist` by design.
- T010 row 21, a post-publication smoke in a disposable OpenCode 2.1.4 profile:
  `opencode plugin add 'github:jayanez/agent-braid#plugin-dist::path:plugins/agent-braid'`
  reported the plugin installed and added; `opencode plugin list` showed `agent-braid`
  at `8f19b1b` with that source (the first list on a cold profile said "No plugins
  found"; a repeat after about 6 seconds listed it); `opencode plugin remove` with the
  exact source string left the configuration as `{"plugins": []}`.

## Not observed

- A native Claude Code or Codex install or update of alpha.7.
- Linux x86_64 execution, including call-time behaviour (built only); T010 row 22.
- T010 row 23 (whether the OpenCode session identifier in request `_meta` is ever
  stored). Rows 22 and 23 are declared limits of this release.
- A model session against the github-installed OpenCode copy.
- `reproduce_native_plugin` for this release, and `validate_spec_kit freeze` for SPEC-068.
- A rollback from alpha.7 to alpha.6 (documented, not executed).

## Known limits

- T010 finding F1: the `analyze-work` input schema does not describe the AIM request
  shape. Tracked in issue #1080; F2 and F3 were fixed in #1030.
- Release-readiness runbook defects found during publication and fixed in
  [release-readiness-alpha7.md](release-readiness-alpha7.md): `rsync --exclude
  README.md` also excluded `plugins/agent-braid/README.md`, so `plugin doctor` refused
  with "Plugin package inventory changed"; `--home "$(mktemp -d)"` on macOS yields a
  symlinked `/var` path that doctor refuses.

## Rollback

Alpha.7 adds no registry member, so alpha.6 accepts the registry and results unchanged.
Reinstall `0.1.0-alpha.6` from tag `agent-braid--v0.1.0-alpha.6` for Claude Code and
Codex (`install.sh --host codex` or `--host claude` with `--ref
agent-braid--v0.1.0-alpha.6`, not `--host all`). Alpha.6 has no OpenCode package: for
OpenCode run `opencode plugin remove` with the exact source string, then reload. The
full steps are in the readiness record. Rolling back `plugin-dist` is the owner's step
and never a force-push.

These are agent-operated engineering observations. They are not a human usability
rating, official directory approval or scientific acceptance.
