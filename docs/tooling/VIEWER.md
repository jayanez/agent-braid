<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Activity viewer

**Status:** SPEC-061 VIS.1a, a read-only viewer of Agent Braid coordination
artifacts and Claude Code hook events. It is a companion that ships with this
repository and its Python package; the native plugin (`integrations/agent-braid/`)
contains none of its code. See [SPEC-061](../../specs/061-activity-viewer/spec.md),
[ADR 0032](../adr/0032-activity-viewer-companion.md) and
[ADR 0033](../adr/0033-vendored-threejs-mit-boundary.md). The viewer reports what was
observed or declared. A shape, label, counter or compatibility class on the page is
**not a guarantee**, not a safety ordering and not permission to run, schedule or
interleave work: every event carries `executionAuthorization: false`.

## What it is and is not

- **Loopback only.** `view serve` binds `127.0.0.1` and no command-line option chooses
  another address. It makes no outbound connection and keeps no access log.
- **Read-only.** No page, route or key runs, schedules, grants or writes anything. It
  never writes to a repository, a plugin registry, a run directory or host
  configuration. The one file it writes is its own ingest token, in a private runtime
  directory, removed again when it stops.
- **Observational hooks.** It answers Claude Code hooks with an empty body and never
  takes part in a host decision.
- **No effort measurement yet.** Codex and OpenTelemetry ingest, token and effort
  views, recording and export are **VIS.1b** and are not available. When they arrive,
  effort stays ephemeral (held in memory only), recording is explicit (`--record`),
  the default export is minimal, effort figures are labelled `host-estimate`, and no
  page or export claims a speedup. None of that exists in this release.

## Install

From a source checkout the viewer reads its web bundle from
`integrations/agent-braid-view/web`:

```bash
python3 -m agent_braid view serve
```

From a built wheel the build ships the same bundle, with the vendored Three.js files
and their manifest, inside the package (`agent_braid/view_assets/web`), so
`agent-braid view serve` works without a checkout:

```bash
python3 -m pip install /absolute/artifacts/agent_braid-0.1.0a2-py3-none-any.whl
agent-braid view serve
```

The viewer needs Python 3.12 or newer and uses only the standard library. A browser
with WebGL2 is needed for the 3D scene; the table works without it. Three.js r186 is vendored under
`integrations/agent-braid-view/web/vendor/` with its licence and a hash manifest; the
page never loads code from another origin.

## Commands

```text
agent-braid view serve    [--replay FILE] [--watch DIR ...] [--no-discover]
                          [--port N] [--surface web] [--runtime-dir DIR]
agent-braid view validate FILE
agent-braid view env      --host claude [--port N] [--runtime-dir DIR]
```

### `view serve`

Starts the viewer and prints, once, the loopback address to open
(`http://127.0.0.1:<port>/open?code=...`), the owner-only ingest token file and any
watched roots. Open the printed address in a browser; the single-use code is
exchanged for a read-only session cookie named `braid_view_<port>`, so two viewers on
loopback keep separate sessions. Stop it with Ctrl-C or SIGTERM; the token
file is removed.

| Option | Effect |
|---|---|
| `--replay FILE` | Load a recorded loom JSONL stream (`agent-braid-loom/v0.1`) before serving. A stream that does not validate is refused with exit code 1 and nothing starts. Replayed events are shown as unverified. |
| `--watch DIR` | Poll a directory for known artifacts (repeatable, at most 8 roots). Replaces automatic discovery. |
| `--no-discover` | Without `--watch`, do not look for roots in the plugin registry. |
| `--port N` | Loopback port, 0 to 65535. The default `0` lets the operating system choose one. (`view env --port` takes 1 to 65535: the port `serve` printed.) |
| `--runtime-dir DIR` | Absolute path of the private directory (mode 0700) for the ingest token. The default is `$XDG_RUNTIME_DIR/agent-braid-view`, else `~/.local/share/agent-braid-view`. |
| `--surface S` | `web` is the only implemented surface. `mod`, `tui` and `mcp-app` report that they are planned and start nothing. |

**Watched artifacts.** `--watch` and discovery read only files with these exact names,
anywhere under a root: `analysis.json`, `git-replay-plan.json`,
`scheduler-preparation.json`, `operator-grant.json`, `state.json`, `hazard-notice.json`,
`ownership-receipt.json` and `gate-result.json`. Every other name is ignored. Each
artifact is read through its adapter and re-hashed (shown as verified by this session).
A symbolic link, a non-regular file or a path leaving its root is never read. The
watcher polls every 500 ms and is bounded: 4,096 directory entries per scan, 16 MiB per
file. When a bound is exceeded the viewer stores a visible gap instead of failing.

**Automatic discovery.** When neither `--watch` nor `--no-discover` is given, `serve`
reads the plugin registry (read-only, no lock, no write) and watches the private result
root of each registered workspace, so the viewer shows the plugin's `analyze-work`
reports without configuration. Only existing directories private to the user are kept.
A missing or invalid registry, or a result root that does not exist yet (restart the
viewer after the first analysis), is a note at start, never a failure.

**Private report copies.** Each successful `analyze-work` call of the plugin keeps a
local copy of its report in the workspace's result root as `analysis-<utc stamp>-<id>/analysis.json`,
for the viewer's watcher. Copies are private to the user (directories 0700, files 0600),
never uploaded, removed after 30 days, and removed oldest first beyond 64 MiB or 1,500
copies. The viewer reads copies newest first, so when a store limit is reached the oldest
copies are the ones left out, and a `stream-truncated` gap says so. A failure to write a copy never changes the `analyze-work` result. See
[plugin privacy](PLUGIN_PRIVACY.md).

**Root labels.** The page never shows a path. Each watched root gets a stable label,
`root 1` to `root 8`, in start order, and the start banner lists the mapping so you can
tell which directory a label stands for:

```text
Watching result roots discovered from the plugin registry (read-only); the page shows only these labels:
  root 1: /absolute/path/of/the/first/result/root
  root 2: /absolute/path/of/the/second/result/root
```

**Hooks.** `serve` accepts Claude Code HTTP hooks at `/hook/claude` for
`SessionStart`, `SessionEnd`, `SubagentStart`, `SubagentStop` and `PostToolUse` only.
Decision events are refused. The viewer keeps an allowlist of payload field names and
drops every other field.

### `view validate FILE`

Checks a recorded loom stream against the event contract and writes nothing. It prints
`ok: N events` on success.

### `view env --host claude`

Prints observational HTTP hook settings for you to merge into your user-level Claude
Code settings (`~/.claude/settings.json`). **It writes nothing**, contains no credential
(the token is read from its owner-only file by the printed `export` line) and names only
the observational hook events above. Start `view serve` first and pass its port with
`--port`; with the viewer stopped, another process on that port would receive the
payloads. The ingest token is new at every `serve` start but your shell reads it once, so after
restarting the viewer restart Claude Code (or export the variable again), otherwise its hooks are refused
without any visible symptom. `--host codex` is accepted and reports that it is not available yet.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | A stream was read but is invalid (`validate`, or `serve --replay`). |
| 2 | Usage error, refusal or unavailable resource: a bad option, a planned `--surface`, a missing file, an unusable bundle or runtime directory, a port that cannot be bound. A refusal leaves nothing behind. |

## Reading the page

The page shows a Three.js braid scene and, as its complete text alternative, a table
of the same events with a playback control and an evidence panel. Playback reveals events
in model order and does not replay real timing. Counters and absence markers always
cover every retained event (at most 50,000, with evicted ranges shown as gaps).

**Source checkboxes.** One checkbox per source of events filters the scene and the
table: one per watched root (`root 1`, `root 2`, ...), then watched artifacts whose
root is not named, replay file, hook ingest and events derived by the viewer. Hidden
events are counted below the checkboxes and stay in the counters, so a hidden source
never looks like an absent one.

**Legend.** The legend lists what each shape, class badge and mark means. It states that
a badge is a categorical label, not a guarantee and not a safety ordering, and the
page repeats that statement at the top.

## Host verification status

The surfaces matrix ([contract](../../specs/061-activity-viewer/contracts/surfaces-matrix.json))
changes status only from an owner-run host-verification receipt
([runbook](../../specs/061-activity-viewer/host-verification-runbook.md)). Current
VIS.1 rows:

| Host | Client | Surface | Status |
|---|---|---|---|
| claude-code | desktop | web | verified |
| claude-code | terminal | web | verified |
| codex | cli | web | hv-pending |
| codex | desktop | mcp-app | hv-pending |

`verified` here is narrow: Claude Code 2.1.292 delivered hooks and OpenTelemetry under
`claude -p` only, and the desktop browser pane loaded a loopback fixture page; the real
viewer is opened again at the T035 checkpoint. Codex remains pending: its token-usage
names are unobserved, and MCP Apps rendering may record `unobserved`.

## Limits

The viewer makes no claim about what a host did beyond the events it received, and a
missing event is not evidence that nothing happened. Local unit tests and a fresh-clone
validation back this guide; they do not replace the owner's check of the viewer on real
sessions (the T035 go/no-go checkpoint for VIS.1b).
