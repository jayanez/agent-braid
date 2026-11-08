<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Getting started with Agent Braid tooling

A short path for a developer who has not used Agent Braid before. It covers
first steps, diagnostics, reading the raw evidence behind any summary, and what
to do when a host cannot render a result. It targets Codex and Claude Code;
the commands are the same runtime in both. Below, `agent-braid` means the Python install (`pip`); with the native plugin run the same arguments through the `bundledCli` launcher path that `plugin-status` returns. Codex behavior is expected to match Claude Code but has not been observed in a native session.

This page is documentation only. It is not actual-host observation, and it does
not satisfy the SPEC-043 T008 reopen criteria (both hosts must show onboarding,
diagnostics, raw-evidence access and rendering fallback in observed sessions).

## 1. Try it first without any host

Before connecting a host, run the owned synthetic journey (needs a source clone and its `.venv`; the plugin bundle does not ship it). It uses a temporary
Git fixture, no network, no model and no project of yours:

```sh
.venv/bin/python examples/journey/run_journey.py --output journey-receipt.json
```

The receipt lists each step (install, discovery, analysis, plan, grant refusal,
interrupted execution, recovery, verification, export, uninstall) and its
outcome. See the [offline journey](JOURNEY.md) for what each step proves and
does not prove.

## 2. Install and register a repository

Follow [Native AI plugins](NATIVE_PLUGINS.md) for the Codex and Claude Code
plugins, or the [Python installation](INSTALL.md) fallback
(`agent-braid tooling install`). The Python install and repository registration
(`plugin setup`) only preview until you repeat the command with the exact
`--apply --preview-digest` value; the host's own plugin install command acts at once. Installing, registering a
repository and enabling the runtime never issue a grant; execution stays off
until you configure it and issue a grant yourself.

In either host, ask for the `setup` skill first, then `analyze` (read only), then
`plan`. A plan is advisory: it names an order and the authority that is still
missing before anything may run.

## 3. Diagnostics

| Question | Command or tool | Reads or changes |
|---|---|---|
| Is the plugin runtime reachable, and which versions? | MCP tool `plugin-status` | read only; reports `version`, `pluginVersion`, `registryHome` |
| Which repositories are registered? | MCP tool `workspaces`, or `plugin workspaces` | read only |
| Is the installation healthy? | `plugin doctor` (native) or `tooling doctor --host ... --scope ... --source-root ... --result-root ...` (Python install) | static, read only; starts no host or provider session |
| Were calls refused or lost? | `telemetry-audit` skill | read only |

Use the launcher path that `plugin-status` returns as `bundledCli` for the
`plugin` commands (see [Native AI plugins](NATIVE_PLUGINS.md)). A refused call is
an answer, not a crash: the envelope carries `status: refused` and the reason,
for example a missing or unissued grant.

## 4. Raw evidence behind a summary

Every human-readable summary is derived from a complete result envelope. To see
the underlying data rather than the summary:

```sh
agent-braid tooling present ENVELOPE.json --format json
agent-braid tooling present ENVELOPE.json --export-directory NEW_PRIVATE_DIR
```

`--format json` prints the complete inline core result. `--export-directory`
needs a new absolute path under a private (owner-only) parent you own. It writes a sanitized
summary and graph, an HTML view and a receipt binding the files to the envelope bytes, plus
`evidence.json`, the complete and possibly sensitive envelope; select
evidence objects with `--evidence-ref`. Complete envelopes can contain local
paths, so keep them private. The `evidence` skill explains the verified, failed
and inconclusive records of a run.

## 5. When a host cannot render a result

Hosts differ in what they display; some show no graph or HTML. The result is
unchanged, only its presentation. Choose a simpler format:

```sh
agent-braid tooling present ENVELOPE.json --format text
agent-braid tooling present ENVELOPE.json --format graph
```

`text` is plain, ASCII-safe and meaningful without color. `graph` is an ASCII
rendering of the explicit operation dependencies. If even that is not shown,
read the result with `--format json`. Nothing in these formats grants
authority or changes your repository.
