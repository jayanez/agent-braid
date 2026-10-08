<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Experimental local AI tooling

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
/absolute/private/tooling-environment/bin/python -m pip install '/absolute/artifacts/agent_braid-0.1.0a1-py3-none-any.whl[tooling]'
/absolute/private/tooling-environment/bin/agent-braid tooling --help
```

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
