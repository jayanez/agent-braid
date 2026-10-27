# SPEC-060 T009 addendum: cause of `failed` in print mode, Linux container run, slash-menu guide

Addendum to the frozen record [native-observation-0.1.0a2.md](native-observation-0.1.0a2.md); it
changes nothing in that record or in `tasks.md` / `assurance.json`. Machine-readable
companion: [native-observation-0.1.0a2-addendum.json](native-observation-0.1.0a2-addendum.json).
Observed on 2026-10-27 from `develop` `9f2fa184e1e3b2491f5a66b015906e7e7318d5e9` (the frozen SPEC-060
evidence commit is `f9329134`; later commits touch `agent_braid/ownership*.py` and `cli.py`, not the
prompt surface). Host: macOS 27.0.1 arm64, Claude Code 2.1.292, Docker Desktop 29.9.2 (aarch64),
uv 0.11.26. All Claude Code state used a disposable `HOME`, `CLAUDE_CONFIG_DIR` and
`AGENT_BRAID_HOME` (mode 700) under a private directory outside any repository and an emptied
environment. No login, no model or provider session; nothing was pushed, tagged, uploaded or
published. This is evidence only: it does not tick any task and is not a release decision.

## A. Why the plugin MCP server is `failed` in the `-p` init record while `claude mcp list` says Connected

**Cause (reproduced, Claude Code 2.1.292).** Claude Code keeps a short-lived failure cache,
`<CLAUDE_CONFIG_DIR>/mcp-needs-auth-cache.json`, keyed by server name
(`plugin:agent-braid:agent-braid`). After any failed connection of that server it writes an entry
`{timestamp, id}`. While the entry is younger than the cache window, a `claude -p` run does **not
attempt a connection at all** (zero `Starting connection` lines in `--debug-file`) and reports the
server as `failed` in the `system`/`init` record. `claude mcp list` performs its own health check,
shows Connected and does not clear the entry. The file is named after authentication but the entries
recorded here were ordinary start-up refusals.

Plugin used: the published `0.1.0-alpha.4` (tag `agent-braid--v0.1.0-alpha.4`, commit
`ac2c4982`, inventory `956fe4e1…`, provenance `f1565500…`), cloned from the public tag into a local
directory and added as a directory marketplace; `plugin setup` was applied first (one fixture
repository, registry `agent-braid-plugin-registry/v0.2`). It is **not** the unpublished local alpha.4
build of the SPEC-054 record (`12c9ab89…`, `2a123a46…`), which no longer exists on disk.

| Run (same profile) | Cache entry before | Connection attempted | init status |
| --- | --- | --- | --- |
| Clean cache, correct home (8 runs over two profiles, one of them with no registry yet) | none | yes, connected in 348-472 ms | `connected` |
| `AGENT_BRAID_HOME` mode 755 | none | yes, server exits | `failed` |
| next run, correct home (mode 700, registered) | written by the previous run | **no** | `failed` |
| `claude mcp list` in that state | present | n/a (own health check) | Connected; entry stays |
| next `-p` run | present | **no** | `failed` |
| entry deleted (file removed) | none | yes | `connected` |
| entry aged to 16 minutes | 16 min old | yes | `connected` (entry cleared) |
| entry aged to 14 minutes | 14 min old | **no** | `failed` |

The start-up refusals that seeded the entry were captured from the server's stderr in the debug log:
`plugin refused: Owned plugin state must be private to its user` (home mode 755) and, in a first run
with relative `..` components in `HOME`, `plugin refused: Use a canonical path without symlinks or
traversal`. The window is therefore between 14 and 16 minutes (consistent with the 15 minutes quoted
by Claude Code for cached failures); the exact constant was not read from source.

Hypotheses ruled out for the symptom:

- **Lazy start in print mode:** with a clean cache every `-p` run attempted the connection and reported
  `connected` in the same init record (the MCP connection is started asynchronously, yet had completed
  before init was written in all runs).
- **Timeout:** the connection budget is 30000 ms; successful connections took 348-472 ms and no run
  hit it.
- **Missing `plugin setup`:** a clean, empty mode-700 home (no registry) connected as well.
- **Handshake race:** none of the clean-cache runs was `failed`; failed runs never started a handshake
  (cache hit) or died on a stderr refusal.

**Limit.** The profile of the original SPEC-060 observation was not preserved, so which earlier failure
seeded its cache entries is an inference, not an observation. It is consistent with that record, which
says the plugin refused to start until `AGENT_BRAID_HOME` was mode 700 and `plugin setup` had run:
such refusals before the fix would have left a fresh cache entry for the next 15 minutes. Behavior of
other Claude Code versions was not examined. The plugin and its server are not at fault for the
symptom; no plugin or documentation change follows (`NATIVE_PLUGINS.md` and `INSTALL.md` make no
claim about print-mode status).

Practical consequence for observers: in a profile that has just had a failed start, wait 15 minutes
or delete `mcp-needs-auth-cache.json` in the disposable profile before reading the init record.

## B. Linux container run of the installed-package verifier

**Plainly: this is Linux inside a Docker Desktop container on an Apple-silicon Mac, not x86_64 CI
hardware.** The verifier supports only the targets `macos-arm64` and `linux-amd64`
(CPython 3.13.11, `uname -m` `x86_64`), and the repository has no Linux arm64 lock. So two runs were made
with `python:3.13.11-slim` (Debian, no bind mount of any real home; only a read-only input directory
and a scratch output directory were mounted):

| Container platform | `uname -m` | Result |
| --- | --- | --- |
| `linux/arm64` (native on this Mac) | `aarch64` | `pip download --require-hashes` of the lock succeeded (the lock lists every platform's hashes), then the verifier refused: `running interpreter does not match the selected target` (exit 2). Expected: not a failure of the candidate. |
| `linux/amd64` (emulated by Docker Desktop on arm64) | `x86_64` | **passed**: `status` `passed`, `target` `linux-amd64`, 28 packages, `--execute-installed`. |

Receipt of the passing run: `receipt.json`, schema `agent-braid-installed-tooling-probe/v1`, SHA-256
`2f5398fdc500f520636c2853b7290b196d7882f9d0197b230f77d6095d8f9716`; candidate version `0.1.0a2`,
Python 3.13.11, no grant issued, no runtime dispatched, no provider session. The receipt file itself is
kept outside the repository (it is a private-work-directory artifact).

Procedure and deviations:

- Candidate wheel: `agent_braid-0.1.0a2-py3-none-any.whl` built from clean `develop` `9f2fa184` with a
  CPython 3.12.13 `uv` venv and `python -m build --wheel`; SHA-256
  `d1aeb657d8c7c1bc2edfe3e0f5202bdace45c7120444f2419746b447f4cd7589`, passed as
  `--candidate-sha256`.
- Verifier `scripts/verify_installed_tooling_v2.py` SHA-256 `4799d7dc…fc3cca` and
  `scripts/verify_installed_tooling.py` SHA-256 `e88e0307…1ce431`, both unchanged from the frozen
  records. Only the v2 script was run.
- The wheelhouse is the 28 wheels of `mcp-2.3.0-cp313-linux-amd64.lock.txt`, fetched with
  `pip download --no-deps --only-binary :all: --require-hashes`. **A plain `pip download` on Debian
  trixie selects `cryptography-50.0.2-cp311-abi3-manylinux_2_34_x86_64`**, which is in the lock hash
  list but not in the manifest roster (`manylinux2014`), so the verifier refused with `wheelhouse
  roster mismatch`. The passing run constrained pip with `--platform manylinux2014_x86_64
  --python-version 3.13 --implementation cp --abi cp313 --abi abi3 --abi none`. If the method is meant to
  be repeatable, this flag set (or a glibc-2.17 baseline image) belongs in the procedure; it was not
  needed for macOS arm64.
- Reproducibility of the T009 wheel hash `bd282e61…632f16`: **mismatch**. The T009 wheel no longer exists,
  so no content comparison was possible. Rebuilds on this machine: `develop` `9f2fa184` gives `d1aeb657…`; the
  T009 commit `06d0313d` built twice from the same tree gives `ff7f2bb6…` and `0d067f2d…` (not equal
  to each other). The two `06d0313d` wheels have identical `RECORD` (same member hashes); wheel entries carry
  build-time timestamps and no `SOURCE_DATE_EPOCH` was set, so the archive hash is not stable across
  builds. Builds with `SOURCE_DATE_EPOCH` set to the commit time gave `ec1c536e…` (`06d0313d`) and
  `e3e2837f…` (`9f2fa184`); determinism under that variable was not re-tested.

Not observed: x86_64 hardware or GitHub Actions Linux, glibc baselines other than Debian trixie,
musl, Linux arm64 as a supported target (it is not one), the native plugin on Linux, and Claude Code or
Codex on Linux.

## C. Interactive slash menu: pending the owner's result

[interactive-slash-guide.md](interactive-slash-guide.md) gives the owner a five-step procedure in
Spanish (portable server under the key `agent-braid` with plugin alpha.4, and under another key; what
to note about `analyze`, `agent-braid-analyze`, `agent-braid:analyze`, the `(MCP)` suffix and duplicates)
and a paste-back template. **Status: PENDING OWNER RESULT.** Until it is returned, the key-collision
warning in `docs/tooling/INSTALL.md` and `docs/tooling/NATIVE_PLUGINS.md` is neither confirmed nor
refuted, as stated in the frozen record. Steps 1-3 of the guide were run headlessly in a disposable profile
(public alpha.4 tag install, `plugin setup`, `claude mcp add agent-braid ...`): both servers Connected,
init registry holds six `agent-braid:*` skills and six `mcp__agent-braid__*` prompts, as before.

## Limits

- Claude Code 2.1.292 only; macOS arm64 host; Codex is not installed on this machine, so nothing about Codex
  was re-observed.
- Part A explains the symptom by reproduction, not the exact original run (see the limit above).
- Part B is a container on arm64 hardware, emulated amd64 for the passing run; not a CI run and not
  evidence for the native plugin.
- Interactive slash-menu use and any model session remain unobserved (part C pending).
- No document claim changed, so `INSTALL.md` and `NATIVE_PLUGINS.md` are unchanged. An optional
  troubleshooting note about the failure cache is a possible follow-up, not part of this change.
