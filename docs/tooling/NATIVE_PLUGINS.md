<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Native AI plugins (SPEC-046)

The native plugin is installed once **per user, per local host** and reused across
repositories. Supported package targets are macOS arm64 and Linux x86_64 (glibc 2.28 or newer; no musl compatibility claim). Codex,
Claude Code or OpenCode (from `0.1.0-alpha.7`, see
[OpenCode](#opencode-from-010-alpha7)) and Git must already be installed. The package includes CPython
3.12.15 and hash-locked dependencies; Python, pip, uv, Node and Docker are not
consumer prerequisites. The Python installation remains available below.

## Published experimental marketplace

The own GitHub marketplace is published on `plugin-dist`, with version
`0.1.0-alpha.7` pinned by tag `agent-braid--v0.1.0-alpha.7`; it adds the OpenCode
native plugin (see the [OpenCode](#opencode-from-010-alpha7) section, the
[alpha.7 release record](../../specs/068-opencode-native-integration/release-acceptance-alpha7.md)
and the [readiness record](../../specs/068-opencode-native-integration/release-readiness-alpha7.md));
its Claude Code and Codex host installs have not been observed.
The previous `0.1.0-alpha.6` is pinned by tag `agent-braid--v0.1.0-alpha.6` at
`78cc45a3f1c5dbc7b43e0ce5024fc5d1c5da053e` and is the rollback target; it adds registry
quarantine, the `telemetry-audit` skill and `pluginVersion` in `plugin-status` (see the
[alpha.6 record](../../specs/046-native-ai-plugins/release-acceptance-alpha6.md)).
The Python package version (`0.1.0a2`) is a separate line from the plugin version
(see the version update notes under local telemetry consent).
The earlier `0.1.0-alpha.5` is pinned by tag `agent-braid--v0.1.0-alpha.5` at
`07e5973fe819591854e6df8bca169b5ec82eae05`; it adds opt-in
System One shadow mode (see the
[alpha.5 record](../../specs/046-native-ai-plugins/release-acceptance-alpha5.md)).
The earlier `0.1.0-alpha.4` is pinned by tag `agent-braid--v0.1.0-alpha.4` at
`ac2c49825c963bf7daf3fd0851f28d9651580efa`. For alpha.4, native macOS arm64
observations cover the isolated alpha.3 → alpha.4 update and a public Git-tag install
with Claude Code 2.1.292, and a Codex CLI 0.164.0 install, remove and reinstall;
a Linux container and interactive skill use were not observed. The
[alpha.4 acceptance record](../../specs/046-native-ai-plugins/release-acceptance-alpha4.md)
states these limits. The
[alpha.3 record](../../specs/046-native-ai-plugins/release-acceptance-alpha3.md)
(tag `agent-braid--v0.1.0-alpha.3`, `8ed7838a`) documents the previous release. The earlier
[alpha.2 record](../../specs/046-native-ai-plugins/release-acceptance.md)
distinguishes interactive observations, emulated Linux controls and public remote
installation from official directory approvals and human acceptance.

## Install for your user

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
existing canonical bundle; `setup` owns onboarding and `telemetry-audit` the read-only
host-log versus local-telemetry audit (from `0.1.0-alpha.6`; alpha.5
has six skills), both independently of that bundle.

Plugin skills are unprefixed. In Claude Code invoke `/agent-braid:analyze`,
`/agent-braid:plan`, `/agent-braid:evidence`, `/agent-braid:execute`,
`/agent-braid:recover`, `/agent-braid:setup` or `/agent-braid:telemetry-audit`; in Codex select the skill from the Agent Braid
plugin (`$` or `/skills`); its qualified name is expected to be
`agent-braid:analyze` and has not yet been observed in a native Codex session. The legacy global install keeps `agent-braid-*`.
Skills and docs reference tools by bare MCP name (for example `analyze-work`):
Claude Code keeps the hyphens in its host tool ids and Codex rewrites them to
underscores. Codex does not display MCP prompts and the plugin publishes none.

Key collision: if the portable server is registered under the key `agent-braid` next to
the native plugin, Claude Code's slash menu shows its prompt `/agent-braid:analyze (MCP)` and
the plugin skill `/agent-braid:analyze` with the same slash text. They remain two distinct
entries, told apart by the `(MCP)` suffix, the `*` marker and the description, with no
conflict warning and nothing breaks. Under a distinct key such as `portable-braid` the
prompts appear as `/portable-braid:analyze (MCP)` and the texts differ, so prefer a distinct
key (owner captures, see the SPEC-060
[interactive result](../../specs/060-portable-prompt-names/evidence/interactive-slash-result.md)).
Codex lists no MCP prompts, so this affects Claude Code only.

The plugin is unchanged by the portable prompt rename (SPEC-060, ADR 0031): no plugin
release is planned for it, and it still publishes no prompts or aliases.

The optional shell entrypoint delegates to exactly these native commands:

```sh
curl -fsSL https://raw.githubusercontent.com/jayanez/agent-braid/develop/install.sh \
  -o agent-braid-install.sh
sh agent-braid-install.sh --host all --dry-run
sh agent-braid-install.sh --host all
```

For a direct pipe, choose the host explicitly (the pipe cannot answer a prompt):

```sh
curl -fsSL https://raw.githubusercontent.com/jayanez/agent-braid/develop/install.sh \
  | sh -s -- --host codex
```

Use `--host claude`, `--host opencode` or `--host all` (every supported host found
on `PATH`: Codex, Claude Code and OpenCode; absent hosts are skipped with a notice
and none found is refused) as appropriate. `--host opencode` refuses when
`opencode` is absent. `--host both` remains a deprecated alias for `codex` +
`claude` only and never touches OpenCode. A reviewed source commit can
replace `develop` in the download URL; `--ref TAG` pins the distribution ref.
`--marketplace /absolute/local/catalog` supports an unpublished local candidate.
The installer needs curl only for fetching this script and never downloads a
Python environment, uses sudo, starts a provider session or modifies repository
configuration. Every selected host is preflighted before the first mutation.
If a native manager fails after an earlier operation succeeds, inspect its
output and rerun the same selection; native managers own idempotency.

## OpenCode (from 0.1.0-alpha.7)

**Status.** The OpenCode package is published from `0.1.0-alpha.7` (2026-11-04);
`0.1.0-alpha.6` and earlier have no OpenCode `package.json`, so the command below needs
alpha.7 or later. Everything here comes from the SPEC-068
[surface contract](../../specs/068-opencode-native-integration/contracts/opencode-surface.md),
its tests, a disposable-profile host matrix (T002), the
[T010 native observation](../../specs/068-opencode-native-integration/evidence/native-observation.json)
(interactive skill and command use, tool calls, update and removal) and a
post-publication install from the `github:` source. All of it used OpenCode 2.1.4 on
macOS arm64 in a disposable profile. Linux and call-time behaviour on Linux are
**unobserved**, as is the OpenCode session identifier in request `_meta`.

Install (user-global; `opencode plugin add` writes only the global configuration):

```sh
opencode plugin add 'github:jayanez/agent-braid#plugin-dist::path:plugins/agent-braid'
```

The installer runs this string (`--ref TAG` replaces `plugin-dist`):
`sh install.sh --host opencode`, or `--host all` with `opencode` on `PATH`.

What the plugin registers: one MCP server named `agent-braid` (tools appear as
`agent-braid_<tool>`, with `codemode: false` and `protocol: legacy` set
explicitly), the seven skills `analyze`, `plan`, `evidence`, `execute`, `recover`, `setup` and
`telemetry-audit`, and two commands, `agent-braid-setup` and `agent-braid-reconnect`. It
publishes no MCP prompts, makes no network call or file write (the commands send
a message into the session), writes no `permission` configuration, and runs no hook. Tool names, schemas and results are the
`agent-braid-plugin/v0.2` contract, unchanged. OpenCode permissions are host
approvals, not Agent Braid grants; execution still needs an operator grant created
outside every tool, skill and command.

**Update, remove and reconnect** (observed with a branch-pinned local Git source):

- `opencode plugin update` reinstalls a branch-pinned source (the default
  `plugin-dist`) into a new cache directory under `$XDG_CACHE_HOME/opencode/npm/`;
  the configuration string is unchanged and the old directory stays on disk. A
  tag-pinned source reports no update.
- `opencode plugin remove` needs the **exact** source string from the
  configuration. The plugin id and the package name `agent-braid` answer "not
  configured" with exit status 0. Removal edits the global configuration and
  leaves the cache directory; Agent Braid's registry and results are untouched.
- `opencode reload` re-runs the plugin and restarts the stdio MCP server, which is
  how you pick up a new registry (`agent-braid-reconnect` sends a prompt asking the agent to relay these steps and
  performs no reload; running the commands is unobserved). Plugin loading after a reload is asynchronous: `opencode plugin
  list` can show nothing for a few seconds. Whether a reload switches a **running
  session** to a newly installed plugin version is not observed for OpenCode (it
  did not for Claude Code with `0.1.0-alpha.6`, per SPEC-068 T010), so observe each candidate in a
  new session.

**Collisions.** OpenCode does not namespace plugin skills: a user or project
skill with the same id silently wins, and the plugin cannot see discovered skills
while it registers its own. Run the read-only diagnosis described in
[SKILLS.md](SKILLS.md#opencode-skill-collisions). The entry never replaces an
existing `agent-braid` MCP entry; OpenCode would otherwise override it without a
warning. `plugin doctor --host opencode` reports it as `server-collision`. If you
also installed the legacy profile (`agent-braid tooling install --host opencode`),
it uses the same server key by default and shadows the plugin's server; the
legacy preview and `doctor` warn with `native_plugin_shadowed`
([INSTALL.md](INSTALL.md#opencode-legacy-profile)).

**Host approval defaults.** In the observed profile no default permission rule
mentioned MCP tools: the default rule sets started from allow-all, with a few
exceptions such as asking before reading `.env` files and some deny rules; rule evaluation order is unobserved. A user `permission` entry can
target `agent-braid_*`. Whether OpenCode prompts when a model calls these tools was
not observed (it needs a model turn).

## Setup and repository suggestions

Open Agent Braid onboarding in Codex (select the Agent Braid `setup` skill), or invoke `/agent-braid:setup` in Claude
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
It also reports two independent versions: `version` is the Python package the
bundled runtime was built from and `pluginVersion` is this native plugin release
(from 0.1.0-alpha.6; `null` outside a package).
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

### Registry changes and running connections

A `plugin setup --apply` (or `plugin workspaces --remove`) from any session or
from the CLI changes the shared registry, so it can invalidate connections that
are already running in other sessions. A connection compares the *effective
configuration* (telemetry consent and the normalized workspace rows) with the
one it snapshotted at start. An idempotent re-apply, a reordering or a raw
byte-level rewrite is not a change; an added, removed or changed workspace,
grant or consent is.

When a connection is stale:

1. Delegated tools and resource reads refuse with the code `reconnect-required`
   and a summary that names the reconnect step. They never act on the old or
   the new configuration.
2. `plugin-status` and `workspaces` keep answering. `plugin-status` reports
   `reconnectRequired: true` plus path-free `baselineDigest` (the configuration
   this connection started with) and `currentDigest` (the registry now). Equal
   digests mean no reconnect is needed.
3. Reconnect MCP with the host's native reconnect/restart operation, then read
   `plugin-status` again: the digests must match and `reconnectRequired` must be
   `false`. The new connection snapshots the new workspaces and consent.

With consent `local`, the plugin router counts these refusals like any other call (surface `mcp`, outcome `refused`) and records only a closed `refusal-reason` bucket for each (`reconnect-required`, `workspace-unregistered`, `admission-busy`, `inventory-full`, `arguments-invalid` and the others in the [telemetry contract](TELEMETRY.md)); no message, path or workspace identifier is stored. A stale connection therefore shows up as `refused` with reason `reconnect-required`, which tells it apart from other failures.

Registration is not execution authority and the stale connection keeps its
original immutable roots and grants until it is replaced.

Scope: SPEC-046 T016–T019 and the registry quarantine below are a bounded defect fix after the 2026-10-19 owner
disposition. They do not reopen T014/T015 candidacy, builds, size work or
publication.

### Deleted worktrees and unsafe registrations

Worktree roots are often ephemeral (for example agent worktrees). The registry
treats each row on its own so one stale entry never disables the plugin:

- A registered worktree root that no longer exists is *stale*. It is reported by
  `plugin doctor`, `plugin workspaces` and `plugin-status` as `staleWorktreeRoots`
  (workspace id, root index and `reason: "missing"`, no paths), is not given to
  the workspace service and is excluded from the configuration digest. If a
  registered worktree is deleted while a connection is running, that connection
  keeps serving, because a deleted root is still declared in the registry and
  only removes reach. `plugin-status` can therefore show `reconnectRequired: true`
  (the effective configuration differs from the snapshot) while calls still
  succeed; reconnect to pick the change up. Removing a root from the registry
  (for example `setup` with a different `--worktree-root` list), swapping it for
  a symlink, or a stale root that reappears is not a deletion: delegated calls
  refuse with `reconnect-required` until you reconnect.
- A workspace whose row is genuinely unsafe (a worktree root that overlaps the
  plugin state directory or is a symbolic link or not an absolute path, a
  mismatched identity, an unknown shape) is quarantined: it is reported as
  `unsafeWorkspaces` (row index, workspace id when well formed and a path-free
  reason that names the root index) and is not served, while every other
  workspace keeps working. Structural problems (unknown schema, duplicate keys or
  workspace ids, a non-private or oversized file) still refuse the whole registry.
- `plugin setup` refuses to register a worktree root that does not exist.
  `plugin setup --prune-stale` previews (and, with `--apply --preview-digest`,
  applies) removal of stale roots and of quarantined workspace registrations;
  without it, setup keeps stale roots registered but inactive and refuses to
  rewrite a registry that holds unsafe rows; the preview lists each dropped
  workspace id and reason and warns that its `runtimeEnabled`/`grantStore`
  configuration is removed and cannot be restored except from a backup.
  `plugin doctor` and setup read the
  registry tolerantly, so diagnosis and repair work in these states.
- A registered workspace whose source repository was deleted still has a valid
  row, but its service cannot start. It is isolated and reported as
  `unavailableWorkspaces` (`workspaceId`, `reason: "configuration rejected"`)
  while other workspaces keep serving. Repair it with
  `plugin workspaces --remove WORKSPACE_ID` (preview, then apply the exact
  digest), which unregisters it and preserves results.

## Optional Claude-only gate workflow (unreleased)

[SPEC-052](../../specs/052-claude-workflow-gate/spec.md) specifies an optional
`braid-gate` workflow, a component distinct from the skills. It is **unreleased**:
no published plugin version contains it, and a build that includes it before the
ADR 0024 amendment is adopted is an engineering artifact only. It is Claude-only;
Codex is expected to ignore it (intended, not observed). The five product skills
and the `setup` skill are unchanged. By design it reaches no network, writes no
source state (only a temporary scratch directory), issues no grant and reports
`executionAuthorization: false`; enforcement depends on a host permission
allowlist that is unverified (HV-5). No Claude Code version has been observed
running it, and host behaviors remain unverified. See the
[recipe](CLAUDE_WORKFLOWS.md) for use, the required host permission allowlist, the
refusal of runtime-enabled registrations and the operator steps that happen
outside the workflow.

## Local telemetry consent

Plugin MCP telemetry is **off by default**. To persist local consent, preview and
apply it like any other setup change, then reconnect MCP:

```sh
"/installed/plugin/launch" plugin setup --home "REGISTRY_HOME" --telemetry local
# Inspect the preview, then repeat with:
# --apply --preview-digest THE_EXACT_PREVIEW_DIGEST
"/installed/plugin/launch" telemetry status --format json
"/installed/plugin/launch" telemetry report
```

Use `--telemetry off` the same way to stop future collection. The consent is one
global key in the user registry; each MCP connection snapshots it at startup, and
`plugin-status` / `plugin doctor` report the configured and active modes. Skills
and environment variables never enable it. Delegated workspace calls are recorded
as surface `mcp` under the [local telemetry](TELEMETRY.md) contract; export, merge
and purge stay manual.

Version 0.1.0-alpha.3 moves the registry to schema v0.2. After updating from
alpha.2, `plugin-status` reports `migration-required` until you preview and apply
`plugin setup --telemetry off` (or `local`). No v0.1 backup is kept and earlier
plugin versions refuse v0.2; after a rollback, remove `registry.json` from the
Agent Braid home (results are kept) and register repositories again.

Version 0.1.0-alpha.4 (SPEC-054, ADR 0030) removes the plugin MCP prompts
(`agent-braid-plugin/v0.2`) and renames the packaged skills to unprefixed names, so
skill invocations change for Claude Code. The Codex app-server skill listing reports
them as `agent-braid:analyze` and so on; interactive Codex invocation has not been
observed. The registry stays
`agent-braid-plugin-registry/v0.2` and registered workspaces, results and telemetry
consent are untouched, so no migration step is needed after updating from alpha.3.
Tool ids and permission rules are unchanged, and no aliases for the old skill names
are provided. To roll back, reinstall `0.1.0-alpha.3` from tag
`agent-braid--v0.1.0-alpha.3`; the registry and results are accepted unchanged.

If a Git/tag marketplace was already added for a different source, run
`claude plugin marketplace remove agent-braid` before adding the alpha.3 tag again;
otherwise Claude refuses ("source doesn't match its extraKnownMarketplaces entry")
and reinstalls alpha.4. Removing the marketplace also uninstalls the plugin, so
add the alpha.3 tag and install again afterwards. Observed with Claude Code 2.1.292
on macOS; the Codex rollback has not been observed.

Version 0.1.0-alpha.5 (SPEC-066, ADR 0034) adds opt-in System One shadow mode: one
structural decision episode is recorded beside each successful `analyze-work`
result, outputs are unchanged, and nothing leaves the machine. It stays `off` until
you preview and apply `plugin setup --system-one shadow` and reconnect; see
[System One shadow mode](SYSTEM_ONE_SHADOW.md). Registered workspaces, results and
telemetry consent are untouched, so no migration step is needed after updating from
alpha.4. Rollback needs one step first: alpha.4 refuses a registry that carries the
`systemOne` member, so preview and apply `plugin setup --system-one off` (which
removes it) before reinstalling `0.1.0-alpha.4` from tag `agent-braid--v0.1.0-alpha.4`.
The shadow store is not removed by that step; run `system-one purge` first if you
want it gone.

Version 0.1.0-alpha.6 is published on `plugin-dist` (tag `agent-braid--v0.1.0-alpha.6`);
its native host install has not yet been observed. It
bundles four changes after alpha.5 and adds no registry migration:

- **Registry quarantine** (SPEC-046): a deleted worktree root or an unsafe
  registration no longer refuses the whole registry. Stale roots and unsafe rows
  are reported as `staleWorktreeRoots` and `unsafeWorkspaces`, a workspace whose
  repository is gone as `unavailableWorkspaces`, and every other workspace keeps
  serving. `plugin setup --prune-stale` previews removing them
  ([details](#deleted-worktrees-and-unsafe-registrations)).
- **Refusal reasons and serve-start telemetry** (SPEC-047 T011): with consent
  `local`, each refused call or refused start adds one closed `refusal-reason`
  bucket and each start adds one `serve-start`. Exports now write batch schema
  `agent-braid-local-telemetry-batch/v2`; merge accepts v1 and v2. The store format is unchanged, so
  an alpha.5 or older build still writes to and reports the same store, but it
  refuses v2 batches and cannot export a store that holds v2 cells; export and
  merge with a current build ([TELEMETRY.md](TELEMETRY.md#refusal-reasons-and-plugin-starts)).
- **`telemetry-audit` skill and `telemetry audit-logs`** (SPEC-047 T012): a
  read-only comparison of the plugin's host MCP logs with the local store; the
  skill is a seventh packaged skill, so the skill listing changes
  (`/agent-braid:telemetry-audit`).
- **`pluginVersion`** in `plugin-status`: `version` stays the Python package
  (`0.1.0a2`) and `pluginVersion` is the native plugin release (`0.1.0-alpha.6`).

Registered workspaces, results and telemetry consent are untouched, so no migration
step is needed after updating from alpha.5. To roll back, reinstall `0.1.0-alpha.5` from tag
`agent-braid--v0.1.0-alpha.5`; the registry and results are accepted unchanged
(alpha.6 adds no registry member). Alpha.5 does not know `unavailableWorkspaces`
or the `telemetry-audit` skill, and it refuses a registry holding a deleted
worktree root or an unsafe row, so run `plugin setup --prune-stale` (preview, then
apply) first if `plugin doctor` reports either. Telemetry cells written by alpha.6
stay in the store; see the compatibility note above for the older build's limits.

Version 0.1.0-alpha.7 (SPEC-068, ADR 0037) adds OpenCode as a third native host and
adds no registry migration. After alpha.6 it bundles:

- **OpenCode native plugin**: one dependency-free ES module (`opencode/index.js`,
  `package.json`) registers the `agent-braid` MCP server, the seven skills `analyze`,
  `plan`, `evidence`, `execute`, `recover`, `setup` and `telemetry-audit`, and the commands
  `agent-braid-setup` and `agent-braid-reconnect`. Tool names, schemas and results
  are unchanged (`agent-braid-plugin/v0.2`); it writes no `permission`
  configuration and runs no hook ([OpenCode](#opencode-from-010-alpha7)).
- **`plugin doctor --host opencode [--project DIR]`**: read-only diagnosis of skill-id
  collisions, a colliding `agent-braid` server key (`server-collision`), duplicate
  guidance and `opencode.json` next to `opencode.jsonc`; without `--host` the output is unchanged
  ([SKILLS.md](SKILLS.md#opencode-skill-collisions)).
- **`install.sh --host opencode` and `--host all`**: `opencode` runs
  `opencode plugin add` with a `github:` source (`--ref TAG` pins it); `--host all`
  installs every supported host found on `PATH`, skips absent ones with a notice and
  refuses when none is found; auto-detection also falls back to OpenCode when it is the
  only host. `--host both` stays `codex` + `claude`.
- **Legacy profile**: `agent-braid tooling install --host opencode` writes a local
  `tooling serve` entry into `opencode.json` or `opencode.jsonc` (comments and trailing
  commas preserved by the standard-library `agent_braid.jsonc` reader) and copies the
  prefixed `agent-braid-*` skills into the OpenCode skills directory of the scope. It
  shares the server key `agent-braid` with the plugin and then shadows it; preview and
  `doctor` report `native_plugin_shadowed` when the plugin entry is in the same
  configuration file (`opencode plugin add` writes the global one); use `--name` for
  another key
  ([INSTALL.md](INSTALL.md#opencode-legacy-profile)).

Migration notes: Codex and Claude Code installs need nothing beyond the update.
If you tried the legacy OpenCode profile and now add the plugin, either remove the
legacy entry or give it another key, and check `plugin doctor --host opencode`.
Registered workspaces, results and telemetry consent are untouched.

Known limits and unobserved: Linux, the OpenCode session identifier in request `_meta`
(T010 row 23) and the native host install of alpha.6 and alpha.7 in Claude Code and
Codex were not observed. OpenCode behaviour was observed with OpenCode 2.1.4 on macOS
arm64 only, in a disposable profile (T010 in
[release-acceptance-alpha7.md](../../specs/068-opencode-native-integration/release-acceptance-alpha7.md)).
Under default permissions OpenCode showed no approval prompt for `plugin-status` or
`analyze-work` (the owner's report from the desktop app, not stored in the session
export). The `analyze-work` input schema does not describe the AIM request shape, so a
model needs an example (for instance `examples/analysis/file-edits.json`) to build a
valid request; a schema description is tracked in issue #1080 for a later release.

Fixes from the T010 observation: `analyze-work` with kind `aim` now returns the
analyzer's fixed validation message (for example "expected AIM record or nonempty AIM
array") instead of a generic refusal, and the OpenCode entry registers
`telemetry-audit`, so OpenCode exposes seven skills like Claude Code and Codex.

To roll back, reinstall `0.1.0-alpha.6` from tag `agent-braid--v0.1.0-alpha.6`
for Claude Code and Codex (`install.sh --host codex` or `--host claude` with `--ref`;
not `--host all`, which would try OpenCode), and for OpenCode remove the plugin with the exact source string
from the configuration (`opencode plugin remove`), since alpha.6 has no OpenCode
package. The registry and results are accepted unchanged by alpha.6.

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
remain for reinstall/migration. Inspect `codex plugin --help`,
`claude plugin --help` and `opencode plugin --help` for commands supported by your
exact host version. OpenCode's own cache behavior is described in the OpenCode section above.

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
for both native interactive journeys, the version-changing update and clean
public Git/curl installation. The historical expired Claude login was resolved
through native login before publication; no API fallback was used.
