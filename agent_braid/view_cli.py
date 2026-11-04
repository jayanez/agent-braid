# SPDX-License-Identifier: AGPL-3.0-only
"""`agent-braid view`: the command line of the read-only activity viewer (SPEC-061 T028).

* `serve` wires the loopback `ViewServer` (T016/T017) to a `LoomStore`, the observational Claude Code
  hook ingest (T019, `/hook/claude` plus the dropped-names inventory), an optional `--replay` stream,
  optional `--watch` artifact directories (`ArtifactTail`, T020) and the first-party web bundle as the
  static root. Without `--watch`, `serve` discovers watch roots read-only from the `resultRoot` of each
  workspace in the Agent Braid plugin registry (T041; `--no-discover` turns it off, `--watch` replaces
  it): only existing directories private to the user are kept, they share the `ArtifactTail` bounds,
  and they are listed at start. A missing or invalid registry is a note, never a failure.
  `--surface web` is the only implemented surface; `mod`, `tui` and `mcp-app` report that they are
  planned and start nothing.
* `validate FILE` checks a recorded loom stream (v0.1 or v0.2), reports how many events of each
  contract version it read and writes nothing.
* `env --host claude` prints observational HTTP hook settings for the user to merge into user-level
  Claude Code settings. It writes nothing, contains no credential (the token is read from its file by
  the printed shell line) and names only observational hook events.

Exit codes: 0 success; 1 the stream was read but is invalid; 2 usage error, refusal or unavailable
resource. Nothing is left behind by a refusal: the runtime directory is created only after every
input was checked and is removed again when the port cannot be bound. The ingest token file is kept
when the server stops and reused at the next start while it is still a safe owner-only file, so hosts
that read it once keep working across restarts; `serve --rotate-token` replaces it (SPEC-061 amendment
2026-11-04). The web bundle is read from the source checkout
(`integrations/agent-braid-view/web`) when that directory exists, else from the installed package
(`agent_braid/view_assets/web`, shipped by the build, T043). Only the files named in `BUNDLE_FILES` are
served (T047); the vendored files come from the `vendor` directory of the resolved bundle. The viewer never writes host configuration. This module
imports no network code; the server modules are loaded only by the subcommands that need them.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shlex
import signal
import stat
import sys
from pathlib import Path
from typing import Any, Callable

from .view_paths import WEB_PACKAGE_DIR, WEB_SOURCE_DIR, vendor_dir_of

SURFACES = ("web", "mod", "tui", "mcp-app")
HOSTS = ("claude", "codex")
RUNTIME_DIR_NAME = "agent-braid-view"
TOKEN_ENV = "AGENT_BRAID_VIEW_TOKEN"
HOOK_TIMEOUT_SECONDS = 5
BUNDLE_DIR = WEB_SOURCE_DIR
# The only first-party files `/web/<file>` may serve (vendored files follow vendor/manifest.json). A new
# file of the bundle is added here; a test pins the list to the files of the source bundle.
BUNDLE_FILES = ("index.html", "style.css", "loom.js", "braid-scene.js", "state.js", "strings.js", "timeline.js")
MAX_BUNDLE_FILE_BYTES = 8 * 1024 * 1024
_IMPORT_MAP = re.compile(rb"<script\b[^>]*\btype\s*=\s*[\"']?importmap[\"']?[^>]*>(.*?)</script\s*>",
                         re.DOTALL | re.IGNORECASE)


class CliError(Exception):
    """A refusal with a stable one-line message and an exit code."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _port(text: str, minimum: int = 0) -> int:
    if not text.isascii() or not text.isdigit() or not minimum <= int(text) <= 65535:
        raise argparse.ArgumentTypeError(f"--port is a number between {minimum} and 65535")
    return int(text)


def _printed_port(text: str) -> int:
    return _port(text, 1)  # `serve` may ask the OS for a port (0); `env` needs the one `serve` printed


def add_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("view", help="read-only activity viewer: serve, validate, env")
    commands = parser.add_subparsers(dest="view_command", required=True)
    serve = commands.add_parser("serve", help="serve the viewer on loopback")
    serve.add_argument("--replay", type=Path, metavar="FILE", help="a recorded loom JSONL stream to load")
    serve.add_argument("--watch", type=Path, action="append", default=[], metavar="DIR",
                       help="a directory of known artifacts to poll (repeatable); replaces discovery")
    serve.add_argument("--no-discover", action="store_true",
                       help="without --watch, do not discover watch roots from the plugin registry")
    serve.add_argument("--port", type=_port, default=0, help="loopback port (default: OS-assigned)")
    serve.add_argument("--surface", choices=SURFACES, default="web",
                       help="web is implemented; the others report that they are planned")
    serve.add_argument("--runtime-dir", type=Path, metavar="DIR",
                       help="private directory for the ingest token (default: per-user location)")
    serve.add_argument("--rotate-token", action="store_true",
                       help="replace the ingest token instead of reusing it (then restart the hosts that read it)")
    validate = commands.add_parser("validate", help="check a recorded loom stream")
    validate.add_argument("file", type=Path)
    env = commands.add_parser("env", help="print host configuration; writes nothing")
    env.add_argument("--host", choices=HOSTS, required=True)
    env.add_argument("--port", type=_printed_port, help="the port printed by `view serve` (default: a placeholder)")
    env.add_argument("--runtime-dir", type=Path, metavar="DIR", help="as for `serve`")


def default_runtime_dir() -> Path:
    """`$XDG_RUNTIME_DIR/agent-braid-view` when that is an absolute path, else under `~/.local/share`."""
    xdg = os.environ.get("XDG_RUNTIME_DIR", "")
    base = Path(xdg) if xdg and os.path.isabs(xdg) else Path.home() / ".local" / "share"
    return base / RUNTIME_DIR_NAME


def _runtime_dir(args: argparse.Namespace) -> Path:
    path = args.runtime_dir if args.runtime_dir is not None else default_runtime_dir()
    if not path.is_absolute():
        raise CliError("view: runtime-dir: the runtime directory is an absolute path")
    return path


def _ensure_private_directory(path: Path) -> list[Path]:
    """Create the runtime directory (and missing parents) with mode 0700; return what was created."""
    created = [candidate for candidate in reversed((path, *path.parents)) if not candidate.exists()]
    try:
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
    except OSError as exc:
        raise CliError(f"view: runtime-dir: cannot create the runtime directory: {exc.strerror}") from exc
    return created


def _remove_created(created: list[Path]) -> None:
    """Best effort: take back directories this run created (deepest first), leaving any that gained content."""
    for directory in reversed(created):
        try:
            directory.rmdir()
        except OSError:
            return


def _private_directory(path: Path) -> bool:
    """True for an existing directory (not a link) owned by this user with no group or other access."""
    try:
        info = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o077


def discover_watch_roots(home: Path | None = None) -> tuple[list[Path], list[str]]:
    """Result roots of the registered plugin workspaces, read-only: `(roots, notes)`; never raises.

    The registry is only read through its tolerant loader (no lock, no write); a row it quarantines is
    skipped. Only existing directories private to the user are kept. `notes` explain anything left out
    without naming a path.
    """
    from .plugin_registry import RegistryError, inspect_registry
    try:
        found = inspect_registry(home)
    except (RegistryError, OSError, RuntimeError) as exc:
        reason = str(exc) if isinstance(exc, RegistryError) else "it could not be read"
        return [], [f"the plugin registry cannot be used ({reason}); nothing was discovered"]
    notes: list[str] = []
    workspaces = found["value"]["workspaces"]
    roots = [root for root in (Path(row["resultRoot"]) for row in workspaces) if _private_directory(root)]
    if found["quarantined"]:
        notes.append(f"{len(found['quarantined'])} registered workspace{'s' * (len(found['quarantined']) != 1)}"
                     " skipped as unsafe")
    if len(roots) < len(workspaces):
        skipped = len(workspaces) - len(roots)
        notes.append(f"{skipped} registered result root{'s' * (skipped != 1)} skipped: "
                     "missing, not a directory or not private to the user (restart the viewer once the first "
                     "analysis has created it)")
    if not workspaces and not found["quarantined"]:
        notes.append("no plugin workspace is registered; nothing was discovered")
    return roots, notes


def resolve_bundle_dir() -> Path:
    """The web bundle directory: the source checkout when it has a bundle, else the installed package's copy.

    The installed copy lives beneath the `agent_braid` package (`view_assets/web`, written by `build_support.py`).
    When neither has an `index.html` the source-checkout path is returned so `load_bundle` refuses it.
    """
    for candidate in (BUNDLE_DIR, WEB_PACKAGE_DIR):
        if (candidate / "index.html").is_file():
            return candidate
    return BUNDLE_DIR


def load_bundle(directory: Path) -> tuple[dict[str, bytes], str | None]:
    """The listed first-party bundle files (`BUNDLE_FILES`) and the SHA-256 (base64) of the inline import map.

    Any other file of the directory, a hidden file, a link or a subdirectory (vendored code) is not read.
    """
    files: dict[str, bytes] = {}
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    for name in BUNDLE_FILES:
        path = directory / name
        try:
            if not stat.S_ISREG(os.lstat(path).st_mode):
                continue
            with os.fdopen(os.open(path, flags), "rb") as stream:
                content = stream.read(MAX_BUNDLE_FILE_BYTES + 1)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CliError(f"view: bundle: cannot read the web bundle: {exc.strerror}") from exc
        if len(content) > MAX_BUNDLE_FILE_BYTES:
            raise CliError(f"view: bundle: {name} is larger than the bundle file bound")
        files[name] = content
    if "index.html" not in files:
        raise CliError("view: bundle: the web bundle has no index.html")
    index = files["index.html"]
    maps = _IMPORT_MAP.findall(index)
    if not maps and b"importmap" in index.lower():
        raise CliError("view: bundle: index.html has an import map the viewer cannot hash for its policy")
    if len(maps) > 1:
        raise CliError("view: bundle: index.html carries more than one inline import map")
    digest = base64.b64encode(hashlib.sha256(maps[0]).digest()).decode("ascii") if maps else None
    return files, digest


def run(args: argparse.Namespace, *, on_ready: Callable[[Any], None] | None = None) -> int:
    """Dispatch a parsed `view` command. `on_ready(server)` is called once `serve` is listening."""
    try:
        if args.view_command == "serve":
            return _serve(args, on_ready)
        if args.view_command == "validate":
            return _validate(args)
        return _env(args)
    except CliError as refusal:
        print(refusal.message, file=sys.stderr)
        return refusal.code


# -- serve ---------------------------------------------------------------------------------------

def _serve(args: argparse.Namespace, on_ready: Callable[[Any], None] | None) -> int:
    if args.surface != "web":
        raise CliError(f"view serve: surface {args.surface} is planned and not implemented; nothing was started")
    runtime_dir = _runtime_dir(args)
    from .view_hooks import HookIngest
    from .view_serve import HOOK_PATH, ServeError, ViewServer, language_hint_from_environ

    bundle_dir = resolve_bundle_dir()
    bundle, import_map_sha256 = load_bundle(bundle_dir)
    store = _replayed_store(args)
    tail, discovered, notes = _watcher(args, store)
    hooks = HookIngest(store)
    created = _ensure_private_directory(runtime_dir)
    try:
        server = ViewServer(store, runtime_dir, port=args.port, bundle=bundle,
                            ingest_handlers={HOOK_PATH: hooks.handle}, names_inventory=hooks.dropped_names,
                            import_map_sha256=import_map_sha256, vendor_dir=vendor_dir_of(bundle_dir),
                            language_hint=language_hint_from_environ(os.environ),
                            rotate_token=args.rotate_token)
    except ServeError as exc:
        _remove_created(created)
        raise CliError(f"view serve: {exc}") from exc
    except OSError as exc:
        _remove_created(created)
        raise CliError(f"view serve: cannot bind port {args.port}: {exc.strerror}") from exc
    previous = _stop_on_sigterm()
    try:
        print("\n".join(_banner(server, tail, discovered, notes)), flush=True)
        if tail is not None:
            tail.start()
        try:
            if on_ready is not None:
                on_ready(server)
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    finally:
        if previous is not None:
            signal.signal(signal.SIGTERM, previous)
        if tail is not None:
            tail.stop()
        server.server_close()
    return 0


def _replayed_store(args: argparse.Namespace) -> Any:
    """A store holding the `--replay` stream, if one was given; a refused stream is exit code 1."""
    from .view_loom import LoomError
    from .view_serve import ServeError, load_replay, read_replay_file
    from .view_store import LoomStore

    store = LoomStore()
    try:
        if args.replay is not None:
            load_replay(store, read_replay_file(args.replay))
    except LoomError as exc:
        raise CliError(f"view serve: replay refused: {exc}", 1) from exc
    except ServeError as exc:
        raise CliError(f"view serve: {exc}") from exc
    return store


def _watcher(args: argparse.Namespace, store: Any) -> tuple[Any, list[Path], list[str]]:
    """The artifact watcher for `--watch` or the discovered roots: `(tail or None, discovered roots, notes)`."""
    from .view_tail import MAX_ROOTS, ArtifactTail, TailError

    discovered: list[Path] = []
    notes: list[str] = []
    if not args.watch and not args.no_discover:
        discovered, notes = discover_watch_roots()
    roots = list(args.watch) or discovered
    try:
        tail = ArtifactTail(store, roots) if roots else None
    except TailError as exc:
        if args.watch:
            raise CliError(f"view serve: watch: {exc.detail}") from exc
        tail, discovered = None, []
        notes.append(f"the discovered roots cannot be watched ({exc.detail})")
    if len(discovered) > MAX_ROOTS:
        notes.append(f"{len(discovered) - MAX_ROOTS} further result roots exceed the bound of {MAX_ROOTS} roots "
                     "and are not watched")
    return tail, discovered, notes


def _banner(server: Any, tail: Any, discovered: list[Path], notes: list[str]) -> list[str]:
    """The start text: the one-time URL, the token file and, when watching, the label to path mapping."""
    from .view_roots import root_label

    lines = ["Agent Braid activity viewer (read-only), surface web, loopback only.",
             f"Open once in a browser: {server.open_url}",
             f"Ingest token file (owner-only): {server.token_path}",
             "Ingest token: reused from the previous start; running hosts keep working." if server.token_reused
             else "Ingest token: new; restart Claude Code (or any host that read the old token) to pick it up."]
    if tail is not None:
        source = "discovered from the plugin registry" if discovered else "given with --watch"
        lines.append(f"Watching result roots {source} (read-only); the page shows only these labels:")
        lines.extend(f"  {root_label(index)}: {root}" for index, root in enumerate(tail.roots))
    lines.extend(f"Discovery note: {note}" for note in notes)
    return lines


def _stop_on_sigterm() -> Any:
    """Make SIGTERM end `serve` like Ctrl-C; return the previous handler (None off the main thread)."""
    def stop(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    try:
        return signal.signal(signal.SIGTERM, stop)
    except ValueError:  # not the main thread (tests): the caller stops the server itself
        return None


# -- validate ------------------------------------------------------------------------------------

def _validate(args: argparse.Namespace) -> int:
    from collections import Counter

    from .view_loom import SCHEMA_VERSIONS, LoomError, parse_stream
    from .view_serve import ServeError, read_replay_file
    try:
        data = read_replay_file(args.file)
    except ServeError as exc:
        raise CliError(f"view validate: {exc.detail}") from exc
    try:
        events = parse_stream(data)
    except LoomError as exc:
        raise CliError(f"view validate: invalid: {exc}", 1) from exc
    versions = Counter(event["schemaVersion"] for event in events)
    read = ", ".join(f"{version}: {versions[version]}" for version in SCHEMA_VERSIONS if versions[version])
    print(f"ok: {len(events)} events ({read or 'none'})")
    return 0


# -- env -----------------------------------------------------------------------------------------

def _env(args: argparse.Namespace) -> int:
    if args.host != "claude":
        raise CliError(f"view env: host {args.host} is not available yet; OTLP ingest arrives with VIS.1b")
    from .view_hooks import OBSERVATIONAL_EVENTS
    from .view_serve import HOOK_PATH, INGEST_TOKEN_NAME
    port = "<port>" if args.port is None else str(args.port)
    token_file = _runtime_dir(args) / INGEST_TOKEN_NAME
    hook = {"type": "http", "url": f"http://127.0.0.1:{port}{HOOK_PATH}",
            "headers": {"Authorization": f"Bearer ${TOKEN_ENV}"}, "allowedEnvVars": [TOKEN_ENV],
            "timeout": HOOK_TIMEOUT_SECONDS}
    settings = {"hooks": {event: [{"hooks": [hook]}] for event in OBSERVATIONAL_EVENTS}}
    print("\n".join((
        "# Agent Braid activity viewer: observational Claude Code hooks.",
        "# This command writes nothing. Merge the \"hooks\" object below into your user-level Claude Code",
        "# settings (~/.claude/settings.json) yourself; never into repository settings.",
        "# The viewer only observes: it answers every hook with an empty body and never takes part in a decision.",
        "# Use it only while the viewer is running: with it stopped, another process on that port would receive",
        "# the payloads. Start `agent-braid view serve` first and pass its port with --port.",
        "# Hooks send full payloads to the loopback port; the viewer then drops every field it does not need.",
        "# The token is read from its owner-only file when your shell starts Claude Code; it is never printed:",
        f"export {TOKEN_ENV}=\"$(cat {shlex.quote(str(token_file))})\"",
        json.dumps(settings, indent=2, sort_keys=True),
    )))
    return 0


__all__ = ["BUNDLE_DIR", "CliError", "SURFACES", "add_parser", "default_runtime_dir", "discover_watch_roots",
           "load_bundle", "resolve_bundle_dir", "run"]
