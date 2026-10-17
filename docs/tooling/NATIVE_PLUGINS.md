<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Native AI plugins (SPEC-046)

The native plugin is installed once **per user, per local host** and reused across
repositories. Supported package targets are macOS arm64 and Linux x86_64 (glibc 2.28 or newer; no musl compatibility claim). Codex
or Claude Code and Git must already be installed. The package includes CPython
3.12.15 and hash-locked dependencies; Python, pip, uv, Node and Docker are not
consumer prerequisites. The Python installation remains available below.

## Candidate and publication status

The source implementation and local distribution candidates are experimental.
The owner authorized publication of `plugin-dist` once both native interactive
journeys and the version-changing update pass. The update and Codex journey have
passed; the actual Claude journey is blocked by expired native authentication.
No public distribution has been pushed. Until that gate passes, build a local
marketplace using the instructions below and pass its absolute path to the native
manager. See the [release acceptance record](../../specs/046-native-ai-plugins/release-acceptance.md).

## Install for your user

After the reviewed distribution is published:

```sh
codex plugin marketplace add https://github.com/jayanez/agent-braid.git --ref plugin-dist
codex plugin add agent-braid@agent-braid
```

Or, for Claude Code:

```sh
claude plugin install agent-braid \
  --marketplace 'https://github.com/jayanez/agent-braid.git#plugin-dist' --scope user
```

The host's plugin interface offers the equivalent marketplace and installation
operations. Skills are discovered from the installed plugin; no copying to global
skills folders or `npx skills add` is needed. Five product skills come from the
existing canonical bundle; a sixth, `setup`, owns onboarding independently.

The optional shell entrypoint delegates to exactly these native commands:

```sh
curl -fsSL https://raw.githubusercontent.com/jayanez/agent-braid/develop/install.sh \
  -o agent-braid-install.sh
sh agent-braid-install.sh --host both --dry-run
sh agent-braid-install.sh --host both
```

For a direct pipe, choose the host explicitly (the pipe cannot answer a prompt):

```sh
curl -fsSL https://raw.githubusercontent.com/jayanez/agent-braid/develop/install.sh \
  | sh -s -- --host codex
```

Use `--host claude` or `--host both` as appropriate. A reviewed source commit can
replace `develop` in the download URL; `--ref TAG` pins the distribution ref.
`--marketplace /absolute/local/catalog` supports an unpublished local candidate.
The installer needs curl only for fetching this script and never downloads a
Python environment, uses sudo, starts a provider session or modifies repository
configuration. Both selected hosts are preflighted before the first mutation.
If a native manager fails after an earlier operation succeeds, inspect its
output and rerun the same selection; native managers own idempotency.

## Setup and repository suggestions

Open Agent Braid onboarding in Codex, or invoke `/agent-braid:setup` in Claude
Code. The setup skill first checks the bundled CLI, Git and configuration. It
suggests the current repository and registered repositories. It can search project
folders **you select**, to a bounded depth and entry count, without following
symlinks. Git worktrees are recognized. Canonical paths are deduplicated.
Empty discovery, unreadable folders or cancellation do not register anything;
you can always enter a repository path manually.

Choose multiple repositories and review the exact JSON preview and digest before
applying once. The initial workspace mode is analysis. Registering a repository
does not authorize execution or issue a grant. Runtime opt-in and an existing
operator grant store are separate explicit configuration choices.

The bootstrap `plugin-status` MCP tool returns `bundledCli` and `registryHome`.
Pass that `registryHome` explicitly as `--home` on CLI setup/discovery operations
to keep storage consistent when a host filters environment variables. Use that absolute
launcher path for the following commands (shell quotes are required for spaces):

```sh
"/installed/plugin/launch" plugin doctor
"/installed/plugin/launch" plugin discover --current /absolute/repository \
  --search-root /absolute/projects --max-depth 4 --max-entries 2000
"/installed/plugin/launch" plugin setup --source-root /absolute/repo-a \
  --source-root '/absolute/repo b'
# Inspect the preview, then repeat the same roots with:
# --apply --preview-digest THE_EXACT_PREVIEW_DIGEST
"/installed/plugin/launch" plugin workspaces
"/installed/plugin/launch" plugin workspaces --remove WORKSPACE_ID
# Inspect and apply that removal using its digest in the same way.
```

After a registry change, reconnect MCP using the host's native reconnect/restart
operation. Each connection keeps immutable workspace bindings and refuses stale
configuration. Every delegated call identifies `workspaceId`; callers cannot
supply arbitrary source or result roots. Resource URIs are workspace-scoped.
The legacy stdio MCP endpoint retains its existing contract.

## Storage, updates and removal

Both hosts share Agent Braid's registry and results outside plugin caches:

- macOS: `~/Library/Application Support/AgentBraid`.
- Linux: `$XDG_DATA_HOME/agent-braid`, or `~/.local/share/agent-braid`.
- Override: `AGENT_BRAID_HOME`, or an explicit `plugin ... --home PATH`.
  A native host must forward custom environment variables to its MCP process
  for an environment override to take effect there; inspect the returned
  `registryHome` instead of assuming a shell variable survived host filtering.

The home and registry are private, owned paths. Each workspace has a stable ID,
explicit canonical source root and its own fixed result root. No global active
repository or implicit filesystem permission is introduced. Removing a workspace
only changes the registry; source files and results survive.

Use each host's native plugin update and uninstall commands or UI. Removing the
plugin removes its installed files; shared Agent Braid configuration and results
remain for reinstall/migration. Inspect `codex plugin --help` and
`claude plugin --help` for commands supported by your exact host version.

For a legacy Python installation, setup offers receipt discovery and an explicit
migration preview:

```sh
"/installed/plugin/launch" plugin legacy --host codex
"/installed/plugin/launch" plugin legacy --host codex --receipt /absolute/receipt.json
# Repeat with --apply --preview-digest DIGEST only after inspecting the preview.
```

Legacy removal delegates to the existing receipt-owned lifecycle. Matching owned
entries/skills are removed; modified/shared bytes and results are retained and
reported. Registration in the new plugin is a separate preview. Unreceipted
configuration is not adopted. Existing Python environments can remain installed.

## Build a local distribution (maintainers)

Use an isolated **Python 3.12** development environment with the build requirements, a clean
source commit and an output outside the checkout:

```sh
.venv/bin/python scripts/build_native_plugin.py \
  --output /absolute/private/plugin-candidate --cache /absolute/private/runtime-cache
```

The build downloads only pinned runtime archives and hash-locked wheels. It emits
both host catalogs, one plugin with both runtime targets, a complete file
inventory, dependency/license metadata and corresponding source archive. Build
outputs and executables belong in a dedicated reviewed distribution branch with
versioned tags, never in development branches. `--allow-dirty` explicitly labels
an engineering artifact and cannot establish clean release provenance.

Use the resulting absolute catalog path with the commands above, omitting `--ref`
for local directories. Installed diagnostics verify file inventory and executable
modes; that detects drift, not publisher authenticity. Verify the release/ref and
provenance before installing. See [submission readiness](plugin-submissions/README.md)
for official ecosystem constraints and [SPEC-046](../../specs/046-native-ai-plugins/spec.md)
for requirements, validation boundaries and remaining acceptance.


For offline reproduction, run `scripts/reproduce_native_plugin.py` using the
candidate's bundled Python with an explicit new state root, fixture, output and
native host executable paths. The script restricts PATH to Git and shell utilities,
creates disposable host profiles, runs actual native install/reinstall/remove and
Claude component inventory, then exercises both MCP protocols and simultaneous
workspace connections. It never starts a model/provider session. Linux container
observations must be labelled as such; they do not establish physical Linux or
interactive host acceptance. Record source, inventory/provenance hashes, exact
host versions and retained state. A version-changing native upgrade remains a
separate release test; repeating installation cannot substitute for it.


The generated Git marketplace includes a root `.gitattributes` that preserves
runtime/wheel bytes without text or filter conversion. All bundled Python sources
are precompiled with checked-hash caches; this keeps the complete inventory stable
when an existing core subprocess invokes the interpreter after relocation. Test
the committed distribution via a new Git clone, not only the build directory.
For container reproduction, the disposable plugin-cache filesystem must allow
execution (for example `--tmpfs /tmp:rw,exec,mode=1777`); a noexec mount should
refuse native MCP startup and must not be reported as plugin acceptance.

The alpha.2 release candidate materializes validated, contained CPython aliases
before inventory creation so native host caches retain every required file.
Reproduction checks `doctor` in each host's actual installed cache as well as in
the source package. See the [current release acceptance record](../../specs/046-native-ai-plugins/release-acceptance.md)
for the observed version-changing update, native Codex interaction and Claude
authentication blocker. Public distribution and the remote curl install remain
pending that final interactive gate.
