# SPDX-License-Identifier: AGPL-3.0-only
"""`agent-braid view`: the command line of the read-only activity viewer (SPEC-061 T028).

* `serve` wires the loopback `ViewServer` (T016/T017) to a `LoomStore`, the observational Claude Code
  hook ingest (T019, `/hook/claude` plus the dropped-names inventory), an optional `--replay` stream,
  optional `--watch` artifact directories (`ArtifactTail`, T020) and the first-party web bundle as the
  static root. `--surface web` is the only implemented surface; `mod`, `tui` and `mcp-app` report that
  they are planned and start nothing.
* `validate FILE` checks a recorded loom stream and writes nothing.
* `env --host claude` prints observational HTTP hook settings for the user to merge into user-level
  Claude Code settings. It writes nothing, contains no credential (the token is read from its file by
  the printed shell line) and names only observational hook events.

Exit codes: 0 success; 1 the stream was read but is invalid; 2 usage error, refusal or unavailable
resource. Nothing is created (no runtime directory, no token file) until every input was checked.
The viewer never writes host configuration. This module imports no network code; the server modules
are loaded only by the subcommands that need them.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Callable

SURFACES = ("web", "mod", "tui", "mcp-app")
HOSTS = ("claude", "codex")
RUNTIME_DIR_NAME = "agent-braid-view"
TOKEN_ENV = "AGENT_BRAID_VIEW_TOKEN"
HOOK_TIMEOUT_SECONDS = 5
BUNDLE_DIR = Path(__file__).resolve().parent.parent / "integrations" / "agent-braid-view" / "web"
MAX_BUNDLE_FILE_BYTES = 8 * 1024 * 1024
MAX_BUNDLE_FILES = 64
_IMPORT_MAP = re.compile(rb'<script\s+type="importmap"\s*>(.*?)</script>', re.DOTALL)


class CliError(Exception):
    """A refusal with a stable one-line message and an exit code."""

    def __init__(self, message: str, code: int = 2) -> None:
        super().__init__(message)
        self.message = message
        self.code = code


def _port(text: str) -> int:
    if not text.isascii() or not text.isdigit() or int(text) > 65535:
        raise argparse.ArgumentTypeError("--port is a number between 0 and 65535")
    return int(text)


def add_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser("view", help="read-only activity viewer: serve, validate, env")
    commands = parser.add_subparsers(dest="view_command", required=True)
    serve = commands.add_parser("serve", help="serve the viewer on loopback")
    serve.add_argument("--replay", type=Path, metavar="FILE", help="a recorded loom JSONL stream to load")
    serve.add_argument("--watch", type=Path, action="append", default=[], metavar="DIR",
                       help="a directory of known artifacts to poll (repeatable)")
    serve.add_argument("--port", type=_port, default=0, help="loopback port (default: OS-assigned)")
    serve.add_argument("--surface", choices=SURFACES, default="web",
                       help="web is implemented; the others report that they are planned")
    serve.add_argument("--runtime-dir", type=Path, metavar="DIR",
                       help="private directory for the ingest token (default: per-user location)")
    validate = commands.add_parser("validate", help="check a recorded loom stream")
    validate.add_argument("file", type=Path)
    env = commands.add_parser("env", help="print host configuration; writes nothing")
    env.add_argument("--host", choices=HOSTS, required=True)
    env.add_argument("--port", type=_port, help="the port printed by `view serve` (default: a placeholder)")
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


def _ensure_private_directory(path: Path) -> None:
    """Create the runtime directory (and missing parents) with mode 0700 before the server checks it."""
    try:
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
    except OSError as exc:
        raise CliError(f"view: runtime-dir: cannot create the runtime directory: {exc.strerror}") from exc


def load_bundle(directory: Path) -> tuple[dict[str, bytes], str | None]:
    """The flat first-party bundle files and the SHA-256 (base64) of the single inline import map."""
    files: dict[str, bytes] = {}
    try:
        with os.scandir(directory) as scan:
            entries = sorted(scan, key=lambda entry: entry.name)
        for entry in entries:
            if entry.name.startswith(".") or not entry.is_file(follow_symlinks=False):
                continue  # subdirectories (vendored code) and links are not served by the flat bundle
            if len(files) >= MAX_BUNDLE_FILES:
                raise CliError("view: bundle: the web bundle has too many files")
            descriptor = os.open(entry.path, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                with os.fdopen(descriptor, "rb", closefd=False) as stream:
                    content = stream.read(MAX_BUNDLE_FILE_BYTES + 1)
            finally:
                os.close(descriptor)
            if len(content) > MAX_BUNDLE_FILE_BYTES:
                raise CliError(f"view: bundle: {entry.name} is larger than the bundle file bound")
            files[entry.name] = content
    except OSError as exc:
        raise CliError(f"view: bundle: cannot read the web bundle: {exc.strerror}") from exc
    if "index.html" not in files:
        raise CliError("view: bundle: the web bundle has no index.html")
    maps = _IMPORT_MAP.findall(files["index.html"])
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
    from .view_loom import LoomError
    from .view_serve import HOOK_PATH, ServeError, ViewServer, load_replay, read_replay_file
    from .view_store import LoomStore
    from .view_tail import ArtifactTail, TailError

    bundle, import_map_sha256 = load_bundle(BUNDLE_DIR)
    store = LoomStore()
    try:
        if args.replay is not None:
            load_replay(store, read_replay_file(args.replay))
    except LoomError as exc:
        raise CliError(f"view serve: replay refused: {exc}", 1) from exc
    except ServeError as exc:
        raise CliError(f"view serve: {exc}") from exc
    try:
        tail = ArtifactTail(store, list(args.watch)) if args.watch else None
    except TailError as exc:
        raise CliError(f"view serve: watch: {exc.detail}") from exc
    hooks = HookIngest(store)
    _ensure_private_directory(runtime_dir)
    try:
        server = ViewServer(store, runtime_dir, port=args.port, bundle=bundle,
                            ingest_handlers={HOOK_PATH: hooks.handle}, names_inventory=hooks.dropped_names,
                            import_map_sha256=import_map_sha256)
    except ServeError as exc:
        raise CliError(f"view serve: {exc}") from exc
    except OSError as exc:
        raise CliError(f"view serve: cannot bind port {args.port}: {exc.strerror}") from exc
    try:
        print(f"Agent Braid activity viewer (read-only), surface web, loopback only.\n"
              f"Open once in a browser: {server.open_url}\n"
              f"Ingest token file (owner-only): {server.token_path}", flush=True)
        if tail is not None:
            tail.start()
        if on_ready is not None:
            on_ready(server)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    finally:
        if tail is not None:
            tail.stop()
        server.server_close()
    return 0


# -- validate ------------------------------------------------------------------------------------

def _validate(args: argparse.Namespace) -> int:
    from .view_loom import LoomError, parse_stream
    from .view_serve import ServeError, read_replay_file
    try:
        data = read_replay_file(args.file)
    except ServeError as exc:
        raise CliError(f"view validate: {exc.detail}") from exc
    try:
        events = parse_stream(data)
    except LoomError as exc:
        raise CliError(f"view validate: invalid: {exc}", 1) from exc
    print(f"ok: {len(events)} events")
    return 0


# -- env -----------------------------------------------------------------------------------------

def _env(args: argparse.Namespace) -> int:
    if args.host != "claude":
        raise CliError(f"view env: host {args.host} is not available yet; OTLP ingest arrives with VIS.1b")
    from .view_hooks import OBSERVATIONAL_EVENTS
    from .view_serve import HOOK_PATH
    port = "<port>" if args.port is None else str(args.port)
    token_file = _runtime_dir(args) / "view-ingest-token"
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


__all__ = ["BUNDLE_DIR", "CliError", "SURFACES", "add_parser", "default_runtime_dir", "load_bundle", "run"]
