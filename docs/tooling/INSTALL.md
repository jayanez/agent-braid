<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Installing Agent Braid

Start with the [native plugin installation guide](NATIVE_PLUGINS.md) for
user-scoped Codex and Claude Code plugins, bundled runtime, automatic skill
discovery, repository suggestions, setup, diagnostics, update and removal.
It includes the optional curl installer and clearly separates local candidates
from public distribution readiness.

## Python installation and legacy lifecycle

The source integration adds default-off local telemetry at these legacy
portable MCP and analyzer CLI boundaries. It does not change the installed
native plugin configuration or create consent for that product. The
[integration record](../../specs/047-local-technical-telemetry/integration-review.md)
pins the reviewed telemetry source and current base. This integration is not a
new installation or native-host observation; pilot **NO-GO**, T017/T018/T010 open.

Select Python 3.12+ before creating an isolated environment. Activate that
environment when contributor commands launch bare `python3` workers, so parent
and worker processes use the same interpreter.

The M4.5 implementation candidate adds an optional stdio MCP server, five bounded
workflow skills, receipt-owned installation and deterministic presentations.
ADR 0021 remains proposed. Local controls do not establish actual Codex/Claude
acceptance, Linux reproduction, utility or milestone closure.

Build a wheel/sdist using an isolated development environment. Install the wheel
in a user-owned virtual environment, selecting the optional `tooling` extra for
MCP (`mcp==2.3.0`). Core analysis has no runtime dependencies. Both artifacts
contain canonical skills and host metadata; installed lookup uses package
resources and works outside a source checkout. The legacy
`python -m agent_braid.mcp_runtime` endpoint retains its six-tool contract.

```sh
python3 -m venv /absolute/private/tooling-environment
/absolute/private/tooling-environment/bin/python -m pip install '/absolute/artifacts/agent_braid-0.1.0a2-py3-none-any.whl[tooling]'
/absolute/private/tooling-environment/bin/agent-braid tooling --help
```

Portable server prompts (SPEC-060, ADR 0031; implemented; package `0.1.0a2` is a
candidate, publication pending): the surface contract `agent-braid-tooling/v0.2` names the
three MCP prompts `analyze`, `plan` and `evidence`; the host adds its own server
key as a prefix. Tool envelopes stay `agent-braid-tooling/v0.1`. The former names
`agent-braid-analyze`, `agent-braid-plan` and `agent-braid-evidence` remain as
DEPRECATED aliases with identical text for two releases and are removed only in
`agent-braid-tooling/v0.3`, after an owner decision and a repository search; if
the second release has not shipped within 180 days of the first, the owner records
a new decision. See the
[v0.2 delta](../../specs/060-portable-prompt-names/contracts/interface-delta.md)
and [ADR 0031](../adr/0031-portable-prompt-names.md).

The candidate carrier version is `0.1.0a2` (publication pending); no plugin release accompanies it,
because the plugin publishes no prompts. Updating needs no host configuration
edit: update the package and reconnect the host. To roll back, reinstall the
earlier package; it lists only the prefixed names.

Key collision: if the portable server is registered under the key `agent-braid` next to
the native plugin, Claude Code's slash menu shows its prompt `/agent-braid:analyze (MCP)` and
the plugin skill `/agent-braid:analyze` with the same slash text. They remain two distinct
entries, told apart by the `(MCP)` suffix, the `*` marker and the description, with no
conflict warning and nothing breaks. Under a distinct key such as `portable-braid` the
prompts appear as `/portable-braid:analyze (MCP)` and the texts differ, so prefer a distinct
key (owner captures, see the SPEC-060
[interactive result](../../specs/060-portable-prompt-names/evidence/interactive-slash-result.md)).
Codex lists no MCP prompts, so this affects Claude Code only.

These example paths are placeholders. Select existing canonical source and
private result directories outside each other. The default catalog contains
`analyze-work`, `analyze` and consultative `prepare`. Execution/recovery and run
inspection require `--enable-runtime --grant-store /absolute/private/grants.json`.
The store must be outside source and result roots. Installation never creates a
grant, changes an approval policy, or launches a host/provider session.

Cancellation signals the existing runtime and waits for its worker to settle.
Git subprocesses have core deadlines and process-group cleanup. A filesystem
system call stalled below Python has no separate hard deadline; cancellation can
remain pending in that case. Do not replay an interrupted operation merely
because its caller stopped waiting. Inspect its existing run before recovery.

```sh
agent-braid tooling install --host codex --scope user \
  --source-root /absolute/repository --result-root /absolute/private/results
```

The command previews exact destinations, executable/argument arrays, tools,
version, hashes and `previewDigest`; it writes nothing. Apply the selected
transaction by repeating those arguments with `--apply --preview-digest DIGEST`.
A changed destination or digest refuses before replacement. Use a distinct
`--name` for a second source root; a skill bundle does not widen server roots.
`--destination /absolute/isolated/host` selects an alternate config/skills/receipt
root for tests. `--source-checkout-assets` is explicit development-only lookup;
it is unnecessary and unavailable in a relocated installation.

Ownership refusals that have a safe comparison scope return a bounded structured
JSON record on stderr (exit 2; stdout stays empty). The record gives a coalesced
current-to-proposed byte-range change and hashes for skill files and Claude's
selected JSON server entry. Codex TOML diagnostics compare the canonical selected
server mapping and label that representation; they do not compare the whole config
file to one server block. If TOML formatting or table-boundary drift prevents a
raw owned-block comparison, the record reports semantic equality or the selected
mapping difference and says raw byte ranges are unavailable. Content and absolute
target paths are withheld. A content match without a receipt is still reported as
unowned and is not adopted.

Codex user config respects `CODEX_HOME` (otherwise `~/.codex/config.toml`);
user skills use `~/.agents/skills`. Codex project config/skills use
`.codex/config.toml` and `.agents/skills` in the selected repository. Claude user
config/skills use `~/.claude.json` and `~/.claude/skills`; opt-in project config is
`.mcp.json` with `.claude/skills`. Project trust and interactive host approvals
remain actual host decisions. Selected builds must confirm these conventions.

`configure` manages only the server entry. `install` also copies the five skills.
`update` requires an active matching receipt and refuses user edits. `uninstall`
removes only matching owned entry/files, retains modified/shared bytes and reports
residuals; empty shared config containers and persistent private backups remain.
Repeat unchanged installation/update/removal is idempotent. TOML edits append an
owned block; JSON edits preserve untouched member bytes. Ambiguous, duplicate,
malformed, symlink or unowned colliding entries refuse. Configuration and receipts
use atomic replacement, a scope lock and rollback; a failed rollback reports
residuals for inspection. Preview hashes and private backups are part of ownership
tracking, not permission for unrelated writes.

`doctor` performs separate read-only static checks. It distinguishes unavailable
SDK/assets/host/permissions from pending protocol, schema, fixture, authentication
and interactive host observations. Its Python/package observations describe the
doctor interpreter; it does not assume a different selected executable has the
same environment. It never starts a paid session or dispatches runtime operations.
Actual stdio discovery and fixture controls produce separate candidate receipts.

`tooling present INPUT --format text|json|graph` formats an already obtained value.
JSON preserves the complete inline core result; referenced artifacts must first
be reconstructed and hash-verified. `--export-directory` requires a new directory
under a private user-owned parent and an explicit evidence-reference selection.
Exports keep complete sensitive evidence separate from sanitized human views.
See [presentation](../ai-tooling-presentation.md) and
[evaluation](EVALUATION.md) for the independent observation and acceptance gates.

## Local telemetry consent, update and removal

The SPEC-047 candidate adds optional local aggregate telemetry to the same installed package with no extra dependency. It is off by default. Direct `analyze` / `analyze-git` calls choose `--telemetry off|local` per invocation; the portable MCP service chooses it per configured server. The legacy endpoint and five skills do not enable collection.

For a telemetry-enabled server installation, preview either selected host using the existing lifecycle:

```sh
agent-braid tooling install --host codex --scope user \
  --source-root /absolute/repository --result-root /absolute/private/results \
  --telemetry local
agent-braid tooling install --host claude --scope user \
  --source-root /absolute/repository --result-root /absolute/private/results \
  --telemetry local
```

Choose one host and repeat its exact previewed arguments with `--apply --preview-digest DIGEST` only when installing intentionally. Preview binds mode, retention and no-upload policy; application records the mode and server arguments in its receipt. Neither step launches a host or creates metrics. `configure` can manage the server alone. `update --telemetry local` retains the explicit choice; a previewed `update --telemetry off` disables it for the next server launch. Omitting the option selects off. Restart an existing configured server separately when authorized. `doctor` distinguishes requested mode from statically configured mode without reading/creating telemetry or launching hosts.

`uninstall` preserves local aggregates. Use `agent-braid telemetry purge` explicitly to clear them; exported copies/backups remain user-managed. The [telemetry guide](TELEMETRY.md) documents the exact private path, 30-day on-access retention, 10 MiB total bound, coverage, failures, report/export/merge/purge commands, batch deduplication and privacy limits. The [current alignment](M45_ALIGNMENT.md) separates historical acceptance from the changed candidate; installation commands documented here are not a claim of new installed/native observation.
