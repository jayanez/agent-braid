<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Native plugin release acceptance — alpha.9

`0.1.0-alpha.9` (SPEC-066 T404 and T405: System One DP-1 rule advice, merge-outcome join and
automatic rollback; reproducible build) is published on `plugin-dist` and annotated tag
`agent-braid--v0.1.0-alpha.9` (tag object `2e11071e51b146ae5ef8061ddd8b538f92a71d72`), both
resolving to commit `fb6db542f547db28df41ea34e7bbe997ed09c81a` (a fast-forward of `7f914ae5`,
the alpha.8 distribution). It was built from `1b9e15c9157efe97f269378991a84a42f20d28de`, the
merge of release PR #1394. A GitHub pre-release with the
[release notes](../../docs/tooling/RELEASE_NOTES_ALPHA9.md) points at the tag. It adds no
registry migration. Hashes, checks and the owner's words are in
[evidence/release-alpha9.json](evidence/release-alpha9.json).

| Artifact | SHA-256 |
| --- | --- |
| `plugins/agent-braid/package-inventory.json` | `1ff8db7421110eca97398491d39a5ea966a20e3afdbd5a8b77411636326befe6` |
| `plugins/agent-braid/provenance.json` | `f3da41b955db8fc4d94e598a20747b3a3cad9db12b341adf9b2c585102683530` |
| `sources/agent-braid-0.1.0-alpha.9-source.tar.gz` | `294e487f552d11e8343b1097f6c543dd021075f6edd214b2c70f7660e13cd6d0` |

The tag tree holds 8,141 files (excluding `.git`); the package inventory lists 8,135.

## Owner decision

On 2026-11-16 the owner answered the orchestrator's questions: "Sí, prepara alpha.9", "Sí,
fusiona y construye" and "Publicar como pre-release (Recomendada)". On 2026-11-17 the owner
asked the orchestrator to install the release for the owner's user and to record it.

## Observations obtained

macOS arm64, agent-operated:

- **Reproducible build.** Two builds of `1b9e15c` at different paths were byte-identical, so
  the package is independent of the builder's checkout (#1349). No file in the published tree
  contains the builder's home path.
- **The `plugin-dist` commit.** Its message is `dist: Agent Braid 0.1.0-alpha.9 (source
  1b9e15c)`. Branch and tag were pushed without force; the tag did not exist on origin before
  the push. The first push hung up on the 257 MB pack before changing the remote and succeeded
  with a larger HTTP buffer.
- **Public clone.** A fresh public clone of the tag is identical to the build output under
  `diff -r`, except the root `README.md`, which exists only on `plugin-dist`.
- **Verification.** `plugin doctor` ran on the published package with a 0700 canonical home.
  It reported `pluginVersion` `0.1.0-alpha.9`, package `0.1.0a2`, status `setup-required` for
  the empty home and a verified package of 8,135 files.
- **Install and update on the owner's machine (Claude Code 2.1.311, 2026-11-17).**
  `claude plugin marketplace update agent-braid` and `claude plugin update
  agent-braid@agent-braid --scope user` moved the user scope from `0.1.0-alpha.8` to
  `0.1.0-alpha.9`. `plugin doctor` on the installed root verified 8,135 files. System One
  stayed `shadow` (configured `shadow`, reason `configured`) and the promotion registry has no
  record, so DP-1 advice stays off the output until an owner go exists. The running session
  needs a restart to serve the new version.

## Model-driven smoke on the published tag (2026-11-20)

`scripts/spec069_native_runs.py --probe-schema` ran one prompt per host against a clone of tag
`agent-braid--v0.1.0-alpha.9` (`plugins/agent-braid`), in disposable profiles under the OS
sandbox, with the owner's saved credentials injected into the child environment only
(Claude Code OAuth token and OpenCode via OpenRouter from the keychain; Codex from the
dedicated sign-in profile). Evidence:
[claude-code and opencode](evidence/smoke-alpha9-claude-opencode.json) and
[codex](evidence/smoke-alpha9-codex.json). Teardown was clean on both runs (no leftover
processes, profiles removed).

| Host | Version | Model | Tool loading | `aim` / `units` accepted | Served bytes = build fingerprint |
| --- | --- | --- | --- | --- | --- |
| Claude Code | 2.1.311 | `claude-sonnet-5-5` | deferred | yes / yes | yes |
| OpenCode | 2.1.4 | `openrouter/anthropic/claude-sonnet-5-5` | helper before call | **no** / yes | yes |
| Codex | 0.171.0-alpha.13 | host default | eager | yes / yes | yes |

Every host exposed `analyze-work`, sent `aim` and `units` requests as JSON objects, and was
served the definition that equals the build fingerprint. On OpenCode the model's first `aim`
request was refused by the validator and its `units` request was accepted; that is
model-authored request validity (the D4 follow-up #1343 already tracks it), not a package
defect. Claude Code's cost was about 0.08 USD. This is a one-prompt probe, so it does not
re-measure request validity.

## Not observed

- An update from alpha.8 on Codex or OpenCode (the smoke above installed the published tag
  into a disposable profile on each host).
- More than one prompt per host: the smoke is a schema probe (one prompt), not the held-out
  measurement.
- Linux x86_64 execution (built only).
- A joined merge outcome from the owner's own work: none existed at publication, so the
  false-independence bound is not yet informative.

## Follow-ups

- T406: owner decision packet on 2026-11-28; `advise` live on 2026-11-30 only on a recorded
  go; mandatory review on 2026-12-31 (the go expires then).
- Model-driven smoke on the three hosts once the owner's sessions run alpha.9.
- A defect found in the published tag is fixed by `0.1.0-alpha.10`; a published tag is not
  retracted.
