# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T013 (REQ-013 / SC-013): one command that measures whether host models author valid analyze-work requests.

For each host (Claude Code, Codex, OpenCode) the driver builds or takes a candidate plugin, creates a
disposable profile under a private temporary root, installs the plugin, registers a fixed sandbox
workspace, runs every prompt of a prompt set through the host's headless mode, parses the ordered
``analyze-work`` attempts, scores them with ``scripts/spec069_scoring.py``, redacts and secret-scans
everything, writes evidence with hashes and tears everything down.

    python -m scripts.spec069_native_runs --prompt-set development --arm final \\
        --model claude-code=<id> --model opencode=anthropic/<id> --model codex=<id>
    python -m scripts.spec069_native_runs --fake-hosts --prompt-set development   # pipeline self-test

Safety (A10): only Agent Braid MCP tools are allowed (a denied tool that runs stops the host); the
host runs under an OS sandbox that denies the real configuration directories and credential stores;
a probe and a canary configuration prove it before the first prompt; any real path in an argument or
environment value stops the run; credentials come only from this process's environment, are injected
into the child environment and are never written; transcripts are redacted and scanned before any
byte reaches the evidence directory. ``--fake-hosts`` evidence is labelled ``pipeline-only``.

Credential routes (D13), all injected into the child environment only and never written:
the default reads keys from this process's environment; ``--keys-from-keychain`` reads them from the macOS keychain
(generic passwords ``agent-braid-anthropic`` / ``-openai`` / ``-openrouter``) through the ``security`` CLI;
``--auth token`` (claude-code only) injects a long-lived OAuth token from ``claude setup-token`` as
``CLAUDE_CODE_OAUTH_TOKEN`` into the Claude Code child only (keychain service ``agent-braid-claude-oauth`` with
``--keys-from-keychain``, else this process's ``CLAUDE_CODE_OAUTH_TOKEN``; recorded as ``auth: oauth-token-env``; no
``ANTHROPIC_API_KEY`` is set for that child and no profile credential file is used);
``--auth subscription`` (claude-code and codex) uses a one-time owner sign-in kept in a dedicated reusable profile
(``--auth-profile-dir``, recorded as ``auth: interactive-once``; ``--login HOST`` prints the sign-in command and
``--check-login HOST`` verifies it). OpenCode may run through OpenRouter: ``--model opencode=openrouter/<id>``.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from agent_braid.lightning_hosts import (  # noqa: F401  (re-exported: the driver's public surface is unchanged)
    CANARY_TOKEN, CLAUDE_ALLOWED, CLAUDE_BUILTIN, CLAUDE_DENIED, META_TOOLS, OPENCODE_DENIED, PARSERS, SECRET_PATTERNS,
    SYSTEM_PATH, DeclaredLimit, HostConfig, OsSandbox, Profile, SafetyStop, SecretLeak, Secrets, ToolCall, Transcript,
    _flatten, _jsonl, attempts_from, guard_leaks, kill_tree, parse_claude, parse_codex, parse_envelope, parse_opencode,
    probe_isolation, process_list, real_config_paths, real_home, run_process, sandbox_profile, sha256_bytes, sha256_file,
    short_name, tool_class as _host_tool_class, utc_now)

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "specs/069-aim-request-authoring"
FAKE_HOSTS_DIR = ROOT / "tests/fixtures/spec069-fake-hosts"
BASELINE_COMMIT = "8f63c606"  # develop commit of PR #1099: alpha.7 runtime plus the interim guidance
DEFAULT_CODEX_BIN = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"
DEFAULT_OPENCODE_BIN = "~/.opencode/bin/opencode"
HOSTS = ("claude-code", "codex", "opencode")
ARMS = ("baseline", "final", "final-no-schema")
PLUGIN_NAME = "agent-braid"
EXIT_SAFETY, EXIT_TEARDOWN, EXIT_SECRET = 2, 3, 4




# ----------------------------------------------------------------------------
# Hosts
# ----------------------------------------------------------------------------


def host_binary(name: str, args: argparse.Namespace) -> Path | None:
    if args.fake_hosts:
        return FAKE_HOSTS_DIR / {"claude-code": "claude", "codex": "codex", "opencode": "opencode"}[name]
    configured = {"claude-code": args.claude_bin, "codex": args.codex_bin, "opencode": args.opencode_bin}[name]
    candidate = configured or {"claude-code": shutil.which("claude"), "codex": DEFAULT_CODEX_BIN,
                               "opencode": shutil.which("opencode") or str(Path(DEFAULT_OPENCODE_BIN).expanduser())}[name]
    path = Path(candidate).expanduser() if candidate else None
    return path if path and path.exists() else None


KEY_SPECS = {"claude-code": (("ANTHROPIC_API_KEY",), "ANTHROPIC_API_KEY"),
             # codex exec honours CODEX_API_KEY, not OPENAI_API_KEY (observed on codex-cli 0.167.0-alpha.3.2).
             "codex": (("CODEX_API_KEY", "OPENAI_API_KEY"), "CODEX_API_KEY"),
             "opencode": (("ANTHROPIC_API_KEY",), "ANTHROPIC_API_KEY")}


OPENROUTER_PREFIX = "openrouter/"
OPENROUTER_SPEC = (("OPENROUTER_API_KEY",), "OPENROUTER_API_KEY")
KEYCHAIN_SERVICES = {"anthropic": "agent-braid-anthropic", "openai": "agent-braid-openai", "openrouter": "agent-braid-openrouter",
                     "claude-oauth": "agent-braid-claude-oauth"}
# Long-lived Claude Code OAuth token (``claude setup-token``): the one credential injected into the claude-code child in token mode.
OAUTH_AUTH, OAUTH_ENV = "oauth-token-env", "CLAUDE_CODE_OAUTH_TOKEN"
TOKEN_NOTE = ("Token mode (auth: oauth-token-env): Claude Code authenticated with a long-lived subscription OAuth token, not an API key; "
              "subscription and API runs may differ in default model, system prompt and limits, so keep one arm pair on one access path")
KEY_ACCOUNT = {"claude-code": "anthropic", "codex": "openai", "opencode": "anthropic"}
OPENROUTER_NOTE = ("OpenCode ran through OpenRouter (route: openrouter), not the direct Anthropic API: routing, provider "
                   "selection, caching and latency differ, so these results are not strictly comparable with the direct-API baseline")
OPENCODE_MODEL_NOTE = "the OpenCode JSON stream names no model (OpenCode 2.1.4): the pinned id is the model identity, modelsObserved stays empty"
# Subscription sign-in (D13 fallback): one dedicated subdirectory per host, the credential file the host writes there.
AUTH_SUBDIR = {"claude-code": "claude", "codex": "codex"}
AUTH_FILE = {"claude-code": ".credentials.json", "codex": "auth.json"}
AUTH_ENV = {"claude-code": "CLAUDE_CONFIG_DIR", "codex": "CODEX_HOME"}
LOGIN_COMMAND = {"claude-code": "CLAUDE_CONFIG_DIR={dir} claude", "codex": "CODEX_HOME={dir} codex login"}
LOGIN_HINT = {"claude-code": "then type /login inside Claude Code, complete the browser sign-in, and exit",
              "codex": "complete the browser sign-in it opens"}
TRIVIAL_PROMPT = "Reply with the single word OK."
SUBSCRIPTION_NOTE = ("Subscription mode (auth: interactive-once): runs bill to the owner's subscription limits, not an API "
                     "account; usage may be rate limited and automated use is subject to the provider's terms")


def _add_counts(total: dict[str, Any], step: dict[str, Any]) -> None:
    for key, value in step.items():
        if isinstance(value, dict):
            _add_counts(total.setdefault(key, {}), value)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            total[key] = total.get(key, 0) + value


def parse_opencode_run(stdout: str) -> Transcript:
    """``parse_opencode`` with usage summed over every step (cost, tokens) and a model when a row names one.

    OpenCode 2.1.4 names no model in its JSON stream; the shared parser keeps only the last step's usage.
    """
    out = parse_opencode(stdout)
    out.usage, models = {}, set(out.models)
    for row in _jsonl(stdout):
        part = row.get("part") or {}
        models.update(m for named in (row, part) for m in [named.get("modelID") or named.get("model")] if isinstance(m, str) and m)
        if part.get("type") == "step-finish":
            _add_counts(out.usage, {key: part[key] for key in ("cost", "tokens") if key in part})
    out.models = sorted(models)
    return out


HOST_PARSERS = {**PARSERS, "opencode": parse_opencode_run}


def route_of(host: str, model: str | None) -> str:
    return "openrouter" if host == "opencode" and bool(model) and model.startswith(OPENROUTER_PREFIX) else "direct"


def key_spec(host: str, model: str | None) -> tuple[tuple[str, ...], str]:
    return OPENROUTER_SPEC if route_of(host, model) == "openrouter" else KEY_SPECS[host]


def keychain_secret(service: str, security_bin: str) -> str | None:
    """One generic password from the macOS keychain through the ``security`` CLI; ``None`` when absent or unreadable.

    The value goes to the caller only: no output of the command is logged, and a failure reports the service name alone.
    """
    try:
        done = subprocess.run([security_bin, "find-generic-password", "-s", service, "-w"], capture_output=True, text=True,
                              stdin=subprocess.DEVNULL, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = done.stdout.rstrip("\n") if done.returncode == 0 else ""
    return value or None


def acquire_oauth_token(args: argparse.Namespace) -> tuple[str, str]:
    """``(token, source)`` for token mode: the keychain with ``--keys-from-keychain`` (the environment is then not used), else the environment."""
    if args.keys_from_keychain:
        service = KEYCHAIN_SERVICES["claude-oauth"]
        token = keychain_secret(service, args.security_bin)
        if not token:
            raise DeclaredLimit(f"keychain item {service} is missing or unreadable (generic password created with `claude setup-token`; the driver never prompts)")
        return token, "keychain"
    token = os.environ.get(OAUTH_ENV)
    if not token:
        raise DeclaredLimit(f"no {OAUTH_ENV} in the driver environment and --keys-from-keychain not set (create the token once with `claude setup-token`)")
    return token, "environment"


def acquire_credential(host: HostConfig, args: argparse.Namespace) -> tuple[str | None, str, str]:
    """``(key or token or None, auth, key source)``. Raises DeclaredLimit when the host's credential is not available."""
    if args.auth == "token" and host.name == "claude-code":
        token, source = acquire_oauth_token(args)
        return token, OAUTH_AUTH, source
    if args.auth == "subscription" and host.name in AUTH_SUBDIR:
        return None, "interactive-once", "profile"
    if args.keys_from_keychain:
        route = route_of(host.name, host.model)
        service = KEYCHAIN_SERVICES["openrouter" if route == "openrouter" else KEY_ACCOUNT[host.name]]
        key = keychain_secret(service, args.security_bin)
        if not key:
            raise DeclaredLimit(f"keychain item {service} is missing or unreadable (generic password; the driver never prompts)")
        return key, "env-key", "keychain"
    key = next((os.environ[name] for name in host.key_sources if os.environ.get(name)), None)
    if args.fake_hosts:
        key = key or "fake-key-not-a-secret"
    if not key:
        raise DeclaredLimit(f"no {' or '.join(host.key_sources)} in the driver environment (D13: the key is read from the environment only)")
    return key, "env-key", "environment"


def check_auth_profile(path: Path, protected: list[Path]) -> Path:
    """The resolved dedicated sign-in directory; SafetyStop when it is, contains or lies under a real configuration path."""
    resolved = Path(os.path.realpath(path.expanduser()))
    for real in protected:
        for variant in {real, Path(os.path.realpath(real))}:
            if resolved == variant or variant in resolved.parents or resolved in variant.parents:
                raise SafetyStop(f"auth profile directory overlaps a real configuration path: {variant.name}")
    if resolved == ROOT or ROOT in resolved.parents or resolved in ROOT.parents:
        raise SafetyStop("auth profile directory must be outside the repository")
    return resolved


def prepare_auth_profile(path: Path, protected: list[Path]) -> Path:
    resolved = check_auth_profile(path, protected)
    resolved.mkdir(parents=True, exist_ok=True)
    if resolved.stat().st_uid != os.getuid():
        raise SafetyStop("auth profile directory is not owned by this user")
    resolved.chmod(0o700)
    return resolved


def credential_file_info(auth_dir: Path, host: str) -> dict[str, Any]:
    """Existence and size only: the file is never opened."""
    try:
        return {"file": AUTH_FILE[host], "exists": True, "bytes": (auth_dir / AUTH_SUBDIR[host] / AUTH_FILE[host]).stat().st_size}
    except OSError:
        return {"file": AUTH_FILE[host], "exists": False, "bytes": 0}


# Codex's read-only MCP resource listing is a discovery helper (observed in T010), like ToolSearch for Claude Code.
CODEX_HELPERS = frozenset({"codex__list_mcp_resources", "codex__list_mcp_resource_templates"})


def tool_class(host: str, call: ToolCall) -> str:
    """``agent-braid``, ``meta`` or ``denied``: the shared classification plus Codex's resource-listing helpers."""
    if host == "codex" and call.tool in CODEX_HELPERS:
        return "meta"
    return _host_tool_class(host, call)


def agent_braid_home(profile: Profile, host: HostConfig) -> Path:
    """Where the plugin registry lives for a host.

    Codex starts the plugin server without ``AGENT_BRAID_HOME``, so the server falls back to the default state root under
    ``HOME`` (observed 2026-11-11: registry empty and ``analyze-work`` unreachable). Register there; the other hosts forward
    the variable.
    """
    if host.name == "codex":
        return profile.make("hosts", host.name, "home", "Library", "Application Support", "AgentBraid")
    return profile.make("hosts", host.name, "agent-braid-home")


def build_host_env(profile: Profile, host: HostConfig, key: str | None, ab_home: Path, passthrough: dict[str, str],
                   auth_home: Path | None = None, oauth_token: str | None = None) -> dict[str, str]:
    """A minimal environment: private HOME/XDG, the one credential, no inherited variables.

    With ``auth_home`` (subscription mode) the host's configuration directory is the dedicated sign-in directory and no key is set.
    With ``oauth_token`` (token mode, claude-code only) the token is the one credential and ``ANTHROPIC_API_KEY`` is never set.
    """
    home = profile.make("hosts", host.name, "home")
    xdg = profile.make("hosts", host.name, "xdg")
    tmp = profile.make("hosts", host.name, "tmp")
    env = {"PATH": f"{host.binary.parent}:{SYSTEM_PATH}:/opt/homebrew/bin", "HOME": str(home), "TMPDIR": str(tmp),
           "XDG_CONFIG_HOME": str(xdg / "config"), "XDG_DATA_HOME": str(xdg / "data"), "XDG_CACHE_HOME": str(xdg / "cache"),
           "XDG_STATE_HOME": str(xdg / "state"), "AGENT_BRAID_HOME": str(ab_home), "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_SYSTEM": os.devnull, "NO_COLOR": "1", "CI": "1", "LANG": "C.UTF-8"}
    for sub in ("config", "data", "cache", "state"):
        (xdg / sub).mkdir(parents=True, exist_ok=True)
    if host.name == "claude-code":
        env["CLAUDE_CONFIG_DIR"] = str(profile.make("hosts", host.name, "claude-config"))
        env["DISABLE_AUTOUPDATER"] = "1"
    if host.name == "codex":
        env["CODEX_HOME"] = str(profile.make("hosts", host.name, "codex-home"))
    if auth_home is not None:
        sign_in = auth_home / AUTH_SUBDIR[host.name]
        sign_in.mkdir(mode=0o700, exist_ok=True)
        sign_in.chmod(0o700)
        env[AUTH_ENV[host.name]] = str(sign_in)
    if key is not None:  # an empty key is still set: the Lightning runner relies on it
        env[host.key_target] = key
    env.update(passthrough)
    if oauth_token is not None:
        env.pop("ANTHROPIC_API_KEY", None)  # an API key would take precedence over the token: the token path must be the one used
        env[OAUTH_ENV] = oauth_token
    return env






def version_of(host: HostConfig, env: dict[str, str], cwd: Path, profile: Profile, protected: list[Path], sandbox: OsSandbox) -> str:
    done = run_process([str(host.binary), "--version"], env, cwd, profile, protected, sandbox, 60, f"{host.name} version")
    return (done.stdout or done.stderr).strip().splitlines()[0] if (done.stdout or done.stderr).strip() else "unknown"


def prompt_argv(host: HostConfig, prompt: str, args: argparse.Namespace) -> list[str]:
    binary = str(host.binary)
    if host.name == "claude-code":
        argv = [binary, "-p", prompt, "--output-format", "stream-json", "--verbose", "--max-turns", str(args.max_turns),
                "--no-session-persistence", "--plugin-dir", str(args.plugin_root_for["claude-code"]),
                "--tools", ",".join(CLAUDE_BUILTIN), "--allowedTools", *CLAUDE_ALLOWED, "--disallowedTools", *CLAUDE_DENIED]
        return argv + (["--model", host.model] if host.model else [])
    if host.name == "codex":
        argv = [binary, "exec", "--json", "--skip-git-repo-check", "-s", "read-only", "-c", 'approval_policy="never"']
        return argv + (["-m", host.model] if host.model else []) + [prompt]
    argv = [binary, "run", "--standalone", "--format", "json"]  # never the background service: it may be the owner's
    return argv + (["-m", host.model] if host.model else []) + [prompt]


def install_plugin(host: HostConfig, plugin_dir: Path, env: dict[str, str], profile: Profile, cwd: Path, protected: list[Path],
                   sandbox: OsSandbox, args: argparse.Namespace) -> Path:
    """Install the candidate into the host profile; return the plugin root the host will run."""
    binary = str(host.binary)

    def run(argv: list[str], label: str) -> str:
        done = run_process(argv, env, cwd, profile, protected, sandbox, 300, f"{host.name} {label}")
        if done.returncode != 0:
            raise DeclaredLimit(f"{host.name} {label} failed: {(done.stderr or done.stdout).strip()[:200]}")
        return done.stdout

    if host.name == "claude-code":
        return plugin_dir
    if host.name == "codex":
        market = plugin_dir.parent.parent
        if not (market / ".agents/plugins/marketplace.json").exists() and not host.fake:
            raise DeclaredLimit("codex needs a marketplace root (.agents/plugins/marketplace.json) above the plugin directory")
        run([binary, "plugin", "marketplace", "add", str(market)], "marketplace add")
        added = run([binary, "plugin", "add", f"{PLUGIN_NAME}@{PLUGIN_NAME}"], "plugin add")
        match = re.search(r"Installed plugin root:\s*(\S+)", added)
        if not match:
            raise DeclaredLimit("codex plugin add did not report the installed plugin root")
        return Path(match.group(1))
    source = profile.make("hosts", host.name, "plugin-source")
    shutil.copytree(plugin_dir.parent, source / "plugins", symlinks=True, dirs_exist_ok=True)
    git = {"cwd": source, "check": True, "capture_output": True, "env": {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull,
           "GIT_CONFIG_SYSTEM": os.devnull, "GIT_AUTHOR_NAME": "d", "GIT_AUTHOR_EMAIL": "d@example.invalid",
           "GIT_COMMITTER_NAME": "d", "GIT_COMMITTER_EMAIL": "d@example.invalid"}}
    subprocess.run(["git", "init", "-q", "-b", "candidate"], **git)
    subprocess.run(["git", "add", "-A"], **git)
    subprocess.run(["git", "commit", "-q", "-m", "candidate"], **git)
    run([binary, "plugin", "add", f"git+file://{source}#candidate::path:plugins/agent-braid"], "plugin add")
    found = sorted(Path(env["XDG_CACHE_HOME"]).glob("opencode/npm/*/*/node_modules/agent-braid")) or \
        sorted(Path(env["XDG_CACHE_HOME"]).glob("opencode/npm/*/node_modules/agent-braid"))
    return found[-1] if found else source / "plugins/agent-braid"


def install_stdio_proxy(plugin_root: Path, receipt_dir: Path, profile_root: Path) -> None:
    """Wrap only a disposable candidate launcher; receipts contain allowlisted hashes, never traffic."""
    profile_root = Path(os.path.realpath(profile_root))
    plugin_root = Path(os.path.realpath(plugin_root))
    receipt_dir = Path(os.path.realpath(receipt_dir))
    for path in (plugin_root, receipt_dir):
        if path == profile_root or profile_root not in path.parents:
            raise SafetyStop("stdio proxy paths must remain below the disposable profile")
    launch = plugin_root / "launch"
    real_launch = plugin_root / "launch.t005-real"
    proxy = plugin_root / ".spec069_stdio_proxy.py"
    runtimes = sorted((plugin_root / "runtime").glob("*/bin/python3.12"))
    if (not launch.is_file() or launch.is_symlink() or real_launch.exists() or proxy.exists()
            or len(runtimes) != 1 or not os.access(runtimes[0], os.X_OK)):
        raise SafetyStop("candidate launcher is not eligible for isolated stdio recording")
    source_proxy = Path(__file__).with_name("spec069_stdio_proxy.py")
    if not source_proxy.is_file():
        raise SafetyStop("stdio proxy source is unavailable")
    receipt_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    receipt_dir.chmod(0o700)
    shutil.copyfile(source_proxy, proxy)
    proxy.chmod(0o600)
    launch.replace(real_launch)
    python = shlex.quote(str(runtimes[0]))
    proxy_arg = shlex.quote(str(proxy))
    real_arg = shlex.quote(str(real_launch))
    receipt_arg = shlex.quote(str(receipt_dir / "connection.")) + '"$$".json'
    launcher = ("#!/bin/sh\nset -eu\n"
                f"exec {python} -I {proxy_arg} --receipt {receipt_arg} -- {real_arg} \"$@\"\n")
    launch.write_text(launcher)
    launch.chmod(0o700)


def summarize_proxy_receipt(path: Path) -> dict[str, Any]:
    """Validate and reduce one private relay receipt to path-free, non-content metadata."""
    try:
        if not hasattr(os, "O_NOFOLLOW"):
            raise ValueError
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            metadata = os.fstat(stream.fileno())
            if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.getuid()
                    or metadata.st_mode & 0o077 or metadata.st_size > 1024 * 1024):
                raise ValueError
            raw = stream.read(1024 * 1024 + 1)
            if len(raw) > 1024 * 1024:
                raise ValueError
        receipt = json.loads(raw)
        if (not isinstance(receipt, dict)
                or not {"version", "complete", "protocolVersion", "listings", "calls", "errors"} <= set(receipt)
                or not set(receipt) <= {"version", "complete", "protocolVersion", "listings", "calls", "errors", "discover"}
                or receipt.get("version") != 1
                or type(receipt.get("complete")) is not bool
                or not isinstance(receipt.get("errors"), list)
                or len(receipt["errors"]) > 4096
                or any(not isinstance(item, str) or not re.fullmatch(r"[a-z_]{1,64}", item) for item in receipt["errors"])):
            raise ValueError
        protocol = receipt.get("protocolVersion")
        if protocol is not None and (not isinstance(protocol, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", protocol)):
            raise ValueError
        listings = receipt.get("listings")
        calls = receipt.get("calls")
        if not isinstance(listings, list) or len(listings) > 4096 or not isinstance(calls, list) or len(calls) > 4096:
            raise ValueError
        safe_listings = []
        for item in listings:
            if (not isinstance(item, dict)
                    or set(item) != {"lineSha256", "lineBytes", "resultCanonicalSha256", "analyzeWorkCanonicalSha256", "toolCount"}):
                raise ValueError
            hashes = [item.get(name) for name in ("lineSha256", "resultCanonicalSha256", "analyzeWorkCanonicalSha256")]
            if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in hashes):
                raise ValueError
            if (type(item.get("lineBytes")) is not int or not 1 <= item["lineBytes"] <= 1024 * 1024 + 1
                    or type(item.get("toolCount")) is not int or not 1 <= item["toolCount"] <= 4096):
                raise ValueError
            safe_listings.append({"lineSha256": hashes[0], "lineBytes": item["lineBytes"],
                                  "resultCanonicalSha256": hashes[1],
                                  "analyzeWorkCanonicalSha256": hashes[2], "toolCount": item["toolCount"]})
        request_types = []
        for item in calls:
            if (not isinstance(item, dict) or not {"requestType"} <= set(item) <= {"requestType", "kind"}
                    or item.get("requestType") not in {"object", "array", "other"}
                    or item.get("kind") not in {None, "aim", "git", "units"}):
                raise ValueError
            request_types.append(item["requestType"])
        if receipt["complete"] and (protocol is None or not safe_listings or receipt["errors"]):
            raise ValueError
        return {"receiptSha256": sha256_bytes(raw), "complete": receipt["complete"],
                "protocolVersion": protocol, "listings": safe_listings,
                "requestTypes": request_types, "errors": receipt["errors"]}
    except (OSError, ValueError, TypeError, UnicodeError, RecursionError, json.JSONDecodeError):
        raise SafetyStop("stdio proxy receipt failed validation") from None


def proxy_receipt_paths(receipt_dir: Path) -> list[Path]:
    current = []
    for path in receipt_dir.glob("connection.*.json"):
        current.append(path)
        if len(current) > 4096:
            raise SafetyStop("stdio proxy connection count exceeded the evidence bound")
    return sorted(current)


def new_proxy_receipts(receipt_dir: Path, previous: set[str]) -> list[dict[str, Any]]:
    current = proxy_receipt_paths(receipt_dir)
    return [summarize_proxy_receipt(path) for path in current if path.name not in previous]


def summarize_stdio_proxy(hosts: dict[str, Any]) -> dict[str, Any]:
    """Cross-host listing identity and request-shape summary; loading mode remains unobserved."""
    connections = []
    call_counts = {}
    for host_name, host in sorted(hosts.items()):
        transcript_calls = 0
        proxy_calls = 0
        for run in host.get("runs", []):
            transcript_calls += len(run.get("attempts", []))
            for receipt in run.get("stdioProxy", []):
                proxy_calls += len(receipt["requestTypes"])
                connections.append({"host": host_name, "protocolVersion": receipt["protocolVersion"],
                                    "complete": receipt["complete"], "listings": receipt["listings"],
                                    "requestTypes": receipt["requestTypes"], "errors": receipt["errors"]})
        if host.get("runs"):
            call_counts[host_name] = {"hostTranscriptAnalyzeWorkCalls": transcript_calls,
                                      "proxyObservedAnalyzeWorkCalls": proxy_calls,
                                      "countsMatch": transcript_calls == proxy_calls}
    by_protocol: dict[str, set[str]] = {}
    request_types = {name: 0 for name in ("object", "array", "other")}
    for connection in connections:
        protocol = connection["protocolVersion"] or "unnegotiated"
        for listing in connection["listings"]:
            by_protocol.setdefault(protocol, set()).add(listing["analyzeWorkCanonicalSha256"])
        for request_type in connection["requestTypes"]:
            request_types[request_type] += 1
    definitions = {protocol: sorted(values) for protocol, values in sorted(by_protocol.items())}
    return {"connectionCount": len(connections), "completeConnections": sum(c["complete"] for c in connections),
            "protocolVersions": sorted({c["protocolVersion"] for c in connections if c["protocolVersion"]}),
            "analyzeWorkDefinitionHashesByProtocol": definitions,
            "definitionIdenticalWithinProtocol": bool(definitions) and all(len(values) == 1 for values in definitions.values()),
            "analyzeWorkRequestTypes": request_types,
            "callCountsByHost": call_counts,
            "hostCallCountsMatch": bool(call_counts) and all(row["countsMatch"] for row in call_counts.values()),
            "modelLoadingMode": "unobserved: stdio recording does not capture model API requests"}


def write_host_policy(host: HostConfig, env: dict[str, str]) -> None:
    """OpenCode permissions: deny every built-in tool; the OpenRouter provider reads its key from the child environment.

    (Claude and Codex take their policy as flags.)
    """
    if host.name != "opencode":
        return
    path = Path(env["XDG_CONFIG_HOME"]) / "opencode" / "opencode.json"
    config = json.loads(path.read_text()) if path.exists() else {}
    config["permission"] = {name: "deny" for name in OPENCODE_DENIED}
    if route_of(host.name, host.model) == "openrouter":
        # The pinned id is declared as a custom model: OpenCode's catalogue lists other spellings (claude-sonnet-5.5) and
        # answers "Model unavailable" for an id it does not know, although OpenRouter serves it.
        model_id = host.model[len(OPENROUTER_PREFIX):]
        config.setdefault("provider", {})["openrouter"] = {"options": {"apiKey": "{env:OPENROUTER_API_KEY}"},
                                                           "models": {model_id: {"name": model_id}}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config))


def register_workspace(plugin_root: Path, workspace: Path, env: dict[str, str], profile: Profile, protected: list[Path],
                       sandbox: OsSandbox, ab_home: Path) -> str:
    base = [str(plugin_root / "launch"), "plugin", "setup", "--home", str(ab_home), "--plugin-root", str(plugin_root),
            "--source-root", str(workspace), "--telemetry", "local"]
    ab_home.chmod(0o700)
    preview = run_process(base, env, workspace, profile, protected, sandbox, 120, "plugin setup preview")
    try:
        previewed = json.loads(preview.stdout)
        digest, workspace_id = previewed["previewDigest"], previewed["registry"]["workspaces"][0]["workspaceId"]
    except (json.JSONDecodeError, KeyError, IndexError) as exc:
        raise DeclaredLimit(f"plugin setup preview failed: {(preview.stderr or preview.stdout).strip()[:200]}") from exc
    applied = run_process([*base, "--apply", "--preview-digest", digest], env, workspace, profile, protected, sandbox, 120,
                          "plugin setup apply")
    if applied.returncode != 0:
        raise DeclaredLimit(f"plugin setup apply failed: {(applied.stderr or applied.stdout).strip()[:200]}")
    return workspace_id


# ----------------------------------------------------------------------------
# Candidate plugin
# ----------------------------------------------------------------------------
def build_candidate(arm: str, work: Path, build_cache: Path, allow_dirty: bool) -> tuple[Path, dict[str, Any]]:
    """Build the plugin for an arm.

    ``baseline`` = develop commit 8f63c606 (alpha.7 runtime plus #1099); ``final`` = this checkout (per-kind request
    schemas in the ``analyze-work`` inputSchema); ``final-no-schema`` = the committed HEAD of this checkout with only the
    request schema reverted to the interim description (D9 ablation, ``spec069_tool_schemas --delivery description-only``).
    """
    source = ROOT
    cleanup: Callable[[], None] = lambda: None  # noqa: E731
    if arm in ("baseline", "final-no-schema"):
        source = work / f"{arm}-source"
        subprocess.run(["git", "-C", str(ROOT), "worktree", "add", "--detach", str(source), BASELINE_COMMIT if arm == "baseline" else "HEAD"],
                       check=True, capture_output=True)
        cleanup = lambda: subprocess.run(["git", "-C", str(ROOT), "worktree", "remove", "--force", str(source)],  # noqa: E731
                                         capture_output=True)
    try:
        venv = work / "venv312"
        subprocess.run(["uv", "venv", "--python", "3.12", str(venv)], check=True, capture_output=True)
        py = venv / "bin/python"
        subprocess.run([str(py), "-m", "ensurepip"], check=True, capture_output=True)
        subprocess.run([str(py), "-m", "pip", "install", "-q", "build", "-r", str(source / "requirements-dev.txt")], check=True,
                       capture_output=True)
        if arm == "final-no-schema":
            subprocess.run([str(py), "-m", "scripts.spec069_tool_schemas", "--delivery", "description-only"], cwd=source, check=True,
                           capture_output=True)
            allow_dirty = True  # dirty by construction: the generated schema module differs from the committed one
        out = work / "candidate"
        platform_id = "macos-arm64" if sys.platform == "darwin" else "linux-x86_64"
        command = [str(py), str(source / "scripts/build_native_plugin.py"), "--output", str(out), "--cache", str(build_cache),
                   "--platform", platform_id] + (["--allow-dirty"] if allow_dirty else [])
        built = subprocess.run(command, cwd=source, check=True, capture_output=True, text=True)
        info = json.loads(built.stdout[built.stdout.index("{"):]) if "{" in built.stdout else {}
        commit = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        record = {"arm": arm, "sourceCommit": commit, "allowDirty": allow_dirty, "sourceDirty": info.get("sourceDirty")}
        schema_module = source / "agent_braid/analyze_work_schema.py"
        if arm != "baseline" and schema_module.exists():
            text = schema_module.read_text(encoding="utf-8")
            found = re.search(r"^DELIVERY = '([^']+)'", text, re.M)
            record["delivery"] = found.group(1) if found else None
            record["analyzeWorkSchemaSha256"] = sha256_bytes(text.encode("utf-8"))
        return out / "plugins" / PLUGIN_NAME, record
    finally:
        cleanup()


def fake_plugin(work: Path, definition: str | None = None) -> Path:
    """A stand-in plugin tree for ``--fake-hosts``: its launcher answers ``plugin setup`` like the real one.

    With ``definition`` (``--probe-schema``) ``plugin serve`` is a minimal MCP server that lists that ``analyze-work`` definition.
    """
    plugin = work / "fake-candidate/plugins/agent-braid"
    plugin.mkdir(parents=True)
    (plugin / "launch").write_text('#!/bin/sh\nexec "${FAKE_PYTHON:-python3}" "$(dirname "$0")/launch.py" "$@"\n')
    (plugin / "launch").chmod(0o755)
    (plugin / "launch.py").write_text(
        "import json, sys\n"
        "args = sys.argv[1:]\n"
        "if args[:2] == ['plugin', 'setup']:\n"
        "    out = {'previewDigest': 'f' * 64, 'registry': {'workspaces': [{'workspaceId': 'fake-workspace-0001'}]}}\n"
        "    print(json.dumps(out))\n"
        "else:\n"
        "    print('{}')\n")
    (plugin / "plugin.json").write_text(json.dumps({"name": PLUGIN_NAME, "version": "0.0.0-fake"}))
    if definition is not None:
        (plugin / "definition.json").write_text(definition)
        (plugin / "launch.py").write_text((FAKE_HOSTS_DIR / "_fake_server.py").read_text())
    market = plugin.parent.parent / ".agents/plugins"
    market.mkdir(parents=True)
    (market / "marketplace.json").write_text(json.dumps({"name": PLUGIN_NAME}))
    return plugin


# ----------------------------------------------------------------------------
# Fake-host scenarios (--fake-hosts)
# ----------------------------------------------------------------------------
FAKE_VARIANTS = ("default", "retry", "denied-tool", "executed-tool", "leak-secret", "straggler", "echo-credentials", "stringify")


def envelope_ok(case: dict, request: dict) -> dict:
    ids = {u["key"]: u["key"] for u in case["expect"]["units"]}
    interactions = [{"left": ids[p["left"]], "right": ids[p["right"]], "classification": p["classification"],
                     "constraints": list(p["constraints"])} for p in case["expect"]["pairs"]]
    return {"operation": "analyze-work", "status": "ok", "summary": "ok", "result": {"report": {"interactions": interactions}}}


def build_fake_scenario(cases: list[dict], variant: str, reference: Callable[[dict], dict]) -> dict:
    scenario = {}
    for index, case in enumerate(cases):
        request = reference(case)
        call = {"tool": "analyze-work", "args": {"kind": case["expect"]["kind"], "request": request},
                "result": envelope_ok(case, request)}
        steps: list[dict] = [{"tool": "workspaces", "args": {}, "result": {"operation": "workspaces", "status": "ok", "summary": "ok"}}]
        if variant == "retry" and index % 3 == 0:
            bad = {"kind": case["expect"]["kind"], "request": {"operations": []}}
            steps.append({"tool": "analyze-work", "args": bad, "result": {
                "operation": "analyze-work", "status": "refused", "summary": "analyze-work refused: missing operations at /operations; expected a list"}})
        if variant == "denied-tool" and index == 0:
            steps.append({"tool": "Bash", "args": {"command": "ls /"}, "executed": False})
        if variant == "executed-tool" and index == 0:
            steps.append({"tool": "Bash", "args": {"command": "ls /"}, "executed": True})
        steps.append(call)
        scenario[case["prompt"]] = {"steps": steps, "text": "done" + (" ${LEAK}" if variant == "leak-secret" else "")}
    return scenario


# ----------------------------------------------------------------------------
# Schema probe (--probe-schema, SPEC-069 T005 / procedure_005)
# ----------------------------------------------------------------------------
PROBE_RELAY = ROOT / "scripts/spec069_stdio_proxy.py"
PROBE_AIM_FIXTURE = ROOT / "examples/analysis/file-edits.json"
PROBE_UNITS_FIXTURE = ROOT / "tests/fixtures/analysis-requests/units/golden/t010-readme-conflict.request.json"
PROBE_DELIVERY = {"final": "per-kind", "final-no-schema": "description-only"}  # the D9 arm baked into each build
PROBE_CASE_ID = "probe-schema"
WORKSPACE_PLACEHOLDER = "{workspaceId}"
PROBE_WRAPPER = """#!/bin/sh
# SPEC-069 T005 probe: recording stdio relay in front of the real launcher (disposable installed copy only).
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
if [ "${{1:-}}" = plugin ] && [ "${{2:-}}" = serve ]; then
  exec {python} -I -B "$here/probe-relay.py" --keep-listing --receipt "{receipts}/connection-$(date +%s)-$$.json" -- "$here/launch.real" "$@"
fi
exec "$here/launch.real" "$@"
"""


def probe_prompt_set() -> dict:
    """One prompt asking for two ``analyze-work`` calls: the ``aim`` example file and one ``units`` request."""
    aim = json.dumps(json.loads(PROBE_AIM_FIXTURE.read_text()), separators=(",", ":"))
    units = json.dumps(json.loads(PROBE_UNITS_FIXTURE.read_text()), separators=(",", ":"))
    prompt = (f"Use the agent-braid analyze-work tool twice, with workspaceId \"{WORKSPACE_PLACEHOLDER}\", then stop. "
              f"First call: kind \"aim\" and request equal to this JSON value: {aim} "
              f"Second call: kind \"units\" and request equal to this JSON value: {units}")
    return {"setId": "t005-probe-schema", "cases": [{"id": PROBE_CASE_ID, "prompt": prompt}]}


def expected_fingerprints() -> dict[str, dict[str, Any]]:
    """Model-facing fingerprint of ``analyze-work`` per D9 arm, computed from this checkout (never hard-coded)."""
    from scripts.spec069_capture_t005_evidence import listed_sizes

    sizes, texts = listed_sizes()
    return {delivery: {"sha256": arm["analyze-work"]["sha256"], "bytes": arm["analyze-work"]["bytes"], "text": texts[delivery],
                       "canonicalSha256": sha256_bytes(canonical_json(json.loads(texts[delivery])))}
            for delivery, arm in sizes.items()}


def canonical_json(value: Any) -> bytes:
    """Sorted keys, compact, UTF-8: the comparison form (key order differs between protocol versions, content does not)."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def wrap_launcher(plugin_root: Path, receipts: Path) -> Callable[[], None]:
    """Put the recording relay in front of ``launch`` in the installed copy; return the function that restores it."""
    launch, real = plugin_root / "launch", plugin_root / "launch.real"
    if real.exists():
        raise SafetyStop("probe: launch.real already exists in the installed copy (a previous probe was not restored)")
    os.replace(launch, real)
    shutil.copyfile(PROBE_RELAY, plugin_root / "probe-relay.py")
    launch.write_text(PROBE_WRAPPER.format(python=shlex.quote(sys.executable), receipts=receipts))
    launch.chmod(0o755)

    def restore() -> None:
        if real.exists():
            os.replace(real, launch)
        (plugin_root / "probe-relay.py").unlink(missing_ok=True)
    return restore


def read_receipts(receipts: Path, seen: set[str], wait_seconds: float = 15.0) -> list[dict[str, Any]]:
    """New receipts of this prompt; an empty or unreadable one (relay killed) is kept as incomplete, never dropped."""
    deadline = time.time() + wait_seconds
    while True:
        files = sorted(f for f in receipts.glob("connection-*.json") if f.name not in seen)
        if all(f.stat().st_size for f in files) or time.time() > deadline:
            break
        time.sleep(0.5)
    out = []
    for file in files:
        seen.add(file.name)
        try:
            receipt = json.loads(file.read_text())
        except (OSError, json.JSONDecodeError):
            receipt = {"complete": False, "errors": ["empty_or_unreadable_receipt"], "listings": [], "calls": [], "protocolVersion": None}
        out.append(dict(receipt, file=file.name))
    return out


def init_tool_names(stdout: str) -> list[str]:
    """Tool names in Claude Code's ``system/init`` row (names only: the schemas are not in the stream)."""
    for row in _jsonl(stdout):
        if row.get("type") == "system" and row.get("subtype") == "init":
            return [t for t in row.get("tools") or [] if isinstance(t, str)]
    return []


def loading_mode(host: str, transcript: Transcript) -> str:
    """From the transcript: ``deferred`` when a tool-search step precedes the first analyze-work call (Claude Code's ToolSearch);
    ``eager`` when the call came with no discovery step; ``helper-before-call`` for another helper first; ``not-observed`` without a call."""
    for call in transcript.tool_calls:
        if short_name(call) == "analyze-work":
            return "eager"
        if call.tool == "ToolSearch":
            return "deferred"
        if tool_class(host, call) == "meta" and call.tool != "Skill":
            return "helper-before-call"
    return "not-observed"


def probe_connections(receipts: list[dict], expected: dict[str, Any], out_dir: Path, host: str, secrets: Secrets) -> list[dict]:
    """Per connection: protocol version, raw listing line (saved) with its hashes, model-facing fingerprint check, calls."""
    from scripts.spec069_tool_schemas import model_facing_bytes

    connections = []
    for index, receipt in enumerate(receipts):
        listings = []
        for number, listing in enumerate(receipt.get("listings") or []):
            raw = listing.pop("rawLine", None)
            entry = dict(listing)
            if raw is not None:
                tools = json.loads(raw)["result"]["tools"]
                definition = next(t for t in tools if t.get("name") == "analyze-work")
                facing = model_facing_bytes(definition)
                facing_canonical = sha256_bytes(canonical_json(json.loads(facing)))
                file = out_dir / host / f"tools-list-c{index}-{number}.json"
                file.parent.mkdir(parents=True, exist_ok=True)
                secrets.assert_clean(file.name, raw)
                file.write_text(raw)
                entry.update({"rawLineFile": str(file.relative_to(out_dir.parent)), "modelFacingSha256": sha256_bytes(facing),
                              "modelFacingCanonicalSha256": facing_canonical, "modelFacingBytes": len(facing),
                              "matchesFingerprint": facing_canonical == expected["canonicalSha256"],
                              "servedKeyOrderEqualsFingerprint": sha256_bytes(facing) == expected["sha256"],
                              "toolNames": sorted(t.get("name") for t in tools if isinstance(t, dict))})
            listings.append(entry)
        connections.append({"receipt": receipt.get("file"), "complete": receipt.get("complete"), "errors": receipt.get("errors"),
                            "protocolVersion": receipt.get("protocolVersion"), "listings": listings, "calls": receipt.get("calls") or [],
                            "trace": receipt.get("trace"), "discover": receipt.get("discover")})
    return connections


def probe_verdict(host: str, connections: list[dict], stdout: str, stderr: str, transcript: Transcript) -> dict[str, Any]:
    """Host acceptance, object-versus-string requests at the server, byte identity and loading for one host and arm."""
    calls = [call for conn in connections for call in conn["calls"]]
    listings = [listing for conn in connections for listing in conn["listings"]]
    claude_names = init_tool_names(stdout) if host == "claude-code" else []
    convert_error = "Failed to convert" in stdout or "Failed to convert" in stderr
    listed = bool(listings) and (any(n.endswith("__analyze-work") for n in claude_names) if host == "claude-code" else not convert_error)
    kinds = sorted({c["kind"] for c in calls if c.get("kind")})
    types = sorted({c["requestType"] for c in calls})
    always_object = bool(calls) and types == ["object"]
    identical = bool(listings) and all(listing.get("matchesFingerprint") for listing in listings)
    loading = loading_mode(host, transcript)
    if not listings:
        verdict = "not-observed: no tools/list reached the recording relay"
    elif not listed:
        verdict = "declared-limit: the host did not expose analyze-work to the model (description-only fallback)"
    elif not calls:
        verdict = "not-observed: the model made no analyze-work call"
    elif not always_object:
        verdict = "declared-limit: the request reached the server as " + "/".join(types) + ", not always an object (description-only fallback)"
    elif not {"aim", "units"} <= set(kinds):
        verdict = "partial: request objects observed, but not for both the aim and units branches"
    elif not identical:
        verdict = "fail: the served analyze-work definition differs from the build fingerprint"
    else:
        verdict = "pass"
    return {"exposedToModel": listed, "claudeInitListsAnalyzeWork": any(n.endswith("__analyze-work") for n in claude_names) if host == "claude-code" else None,
            "codexConvertError": convert_error if host == "codex" else None, "callsAtServer": calls, "kindsAtServer": kinds,
            "requestAlwaysObject": always_object if calls else None, "servedBytesMatchFingerprint": identical,
            "protocolVersions": sorted({c["protocolVersion"] for c in connections if c["protocolVersion"]}),
            "receiptsComplete": f"{sum(1 for c in connections if c['complete'])}/{len(connections)}", "loading": loading, "verdict": verdict}


def cross_host_identity(hosts: dict[str, Any]) -> dict[str, Any]:
    """Byte identity of analyze-work across every host connection of this build, compared within each protocol version."""
    groups: dict[str, dict[str, set[str]]] = {}
    for name, host in hosts.items():
        for conn in (host.get("schemaProbe") or {}).get("connections", []):
            for listing in conn["listings"]:
                group = groups.setdefault(conn["protocolVersion"] or "unknown", {"canonical": set(), "facing": set(), "hosts": set()})
                group["canonical"].add(listing["analyzeWorkCanonicalSha256"])
                group["facing"].add(listing.get("modelFacingCanonicalSha256") or "")
                group["hosts"].add(name)
    by_version = {v: {"hosts": sorted(g["hosts"]), "analyzeWorkCanonicalSha256": sorted(g["canonical"]),
                      "modelFacingCanonicalSha256": sorted(g["facing"]), "identical": len(g["canonical"]) == 1}
                  for v, g in sorted(groups.items())}
    facing = {f for g in groups.values() for f in g["facing"]}
    return {"byProtocolVersion": by_version, "modelFacingIdenticalAcrossVersions": len(facing) == 1,
            "note": ("analyzeWorkCanonicalSha256 compares the full served definition within one protocol version; "
                     "modelFacingCanonicalSha256 (name, description, inputSchema, sorted keys) compares across versions and with the build fingerprint")}



def build_probe_scenario(prompt: str) -> dict:
    """Fake-host scenario for ``--probe-schema``: the two calls the probe prompt asks for, sent through the plugin server."""
    calls = []
    for kind, fixture in (("aim", PROBE_AIM_FIXTURE), ("units", PROBE_UNITS_FIXTURE)):
        args = {"workspaceId": "fake-workspace-0001", "kind": kind, "request": json.loads(fixture.read_text())}
        calls.append({"tool": "analyze-work", "args": args, "result": {"operation": "analyze-work", "status": "ok", "summary": "ok"}})
    return {prompt: {"steps": calls, "text": "done"}}


# ----------------------------------------------------------------------------
# The run
# ----------------------------------------------------------------------------
def load_prompt_set(spec: str) -> tuple[dict, Path]:
    path = Path(spec)
    if not path.exists():
        path = SPEC_DIR / "prompts" / f"{spec}.json"
    return json.loads(path.read_text()), path


def evidence_label(fake: bool) -> str:
    return "pipeline-only" if fake else "host-run"


def auth_dir_usable(env: dict[str, str], auth_home: Path, host: str, sandbox: OsSandbox) -> bool:
    """The dedicated sign-in directory can be listed and written under the same OS sandbox the host runs in."""
    target = str(auth_home / AUTH_SUBDIR[host])
    script = 'ls "$1" >/dev/null && t="$1/.sandbox-write-probe" && : > "$t" && rm -f "$t"'
    return subprocess.run(sandbox.wrap(["/bin/sh", "-c", script, "sh", target]), env=env, capture_output=True, timeout=30).returncode == 0


def run_host(host: HostConfig, args: argparse.Namespace, prompt_set: dict, ctx: dict, profile: Profile, secrets: Secrets,
             out_dir: Path, scoring: Any, fixture: Any) -> dict[str, Any]:
    """One host end to end. Raises DeclaredLimit for a host that cannot run, SafetyStop for a safety failure."""
    key, auth, key_source = acquire_credential(host, args)
    token, key = (key, None) if auth == OAUTH_AUTH else (None, key)
    route = route_of(host.name, host.model)
    if host.name == "opencode" and not host.model and not args.fake_hosts:
        raise DeclaredLimit("OpenCode needs --model opencode=anthropic/<id> or openrouter/<id>: without it the host uses a free hosted model")
    secrets.add(token or key)
    auth_home = ctx["auth_home"] if auth == "interactive-once" else None
    ab_home = agent_braid_home(profile, host)
    passthrough = dict(ctx["passthrough"])
    env = build_host_env(profile, host, key, ab_home, passthrough, auth_home, token)
    protected, sandbox = ctx["protected"], ctx["sandbox"]
    workspace = fixture.build(profile.make("hosts", host.name, "workspace") / "repo")
    guard_leaks(f"{host.name} setup", env, [str(host.binary)], protected)
    if not sandbox.tool and not args.no_os_sandbox and not args.fake_hosts:
        raise DeclaredLimit("no OS sandbox available on this platform; refusing an unsandboxed real run (use --no-os-sandbox only for an engineering probe)")
    probe = probe_isolation(env, Path(env["HOME"]), sandbox, protected)
    if auth_home is not None:
        probe["authProfile"] = {**credential_file_info(auth_home, host.name), "usableUnderSandbox": auth_dir_usable(env, auth_home, host.name, sandbox)}
        if sandbox.name != "none" and not probe["authProfile"]["usableUnderSandbox"]:
            raise SafetyStop("isolation probe: the dedicated sign-in directory is not usable under the sandbox")
    version = version_of(host, env, workspace, profile, protected, sandbox)
    candidate_dir = ctx["plugin_dir"]
    if args.record_mcp:
        marketplace = candidate_dir.parent.parent
        source_marketplace = profile.root / "recording-source" / host.name / "marketplace"
        source_marketplace.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copytree(marketplace, source_marketplace, symlinks=True)
        candidate_dir = source_marketplace / "plugins" / PLUGIN_NAME
    plugin_root = install_plugin(host, candidate_dir, env, profile, workspace, protected, sandbox, args)
    receipt_dir = None
    if args.record_mcp:
        receipt_dir = profile.make("mcp-observations", host.name)
        install_stdio_proxy(plugin_root, receipt_dir, profile.root)
    restore: Callable[[], None] = lambda: None  # noqa: E731
    receipts, seen, probe_runs = None, set(), []
    if args.probe_schema:
        if host.name == "claude-code":  # --plugin-dir points at the build output: probe a disposable copy, never the build
            copy = profile.make("hosts", host.name, "plugin-copy") / PLUGIN_NAME
            shutil.copytree(plugin_root, copy, symlinks=True)
            plugin_root = copy
        receipts = profile.make("hosts", host.name, "probe-receipts")
        restore = wrap_launcher(plugin_root, receipts)
    try:
        args.plugin_root_for[host.name] = plugin_root
        write_host_policy(host, env)
        workspace_id = register_workspace(plugin_root, workspace, env, profile, protected, sandbox, ab_home)
        runs, violations = _run_prompts(host, args, prompt_set, env, workspace, workspace_id, profile, protected, sandbox, secrets,
                                        out_dir, scoring, receipts, seen, probe_runs, ctx, receipt_dir)
    finally:
        restore()  # Codex keeps its install in the reusable sign-in directory: never leave the relay there
    if violations:
        raise SafetyStop(f"{host.name}: " + "; ".join(violations))
    reported = sorted({r["keySourceReported"] for r in runs if r.get("keySourceReported")})
    notes = ([OPENROUTER_NOTE, OPENCODE_MODEL_NOTE] if route == "openrouter" else []) + ([SUBSCRIPTION_NOTE] if auth == "interactive-once" else []) + ([TOKEN_NOTE] if auth == OAUTH_AUTH else [])
    result = {"status": "ran", "version": version, "auth": auth, "keySource": key_source, "route": route, "notes": notes,
              "hostReportedKeySource": reported, "modelPinned": bool(host.model), "model": host.model,
              "modelsObserved": sorted({m for run in runs for m in run["models"]}), "osSandbox": probe["sandbox"],
              "probe": probe, "workspaceRegistered": bool(workspace_id), "runs": runs,
              "allowlist": {"claude-code": CLAUDE_ALLOWED, "codex": ["agent-braid MCP server; read-only sandbox; approval never"],
                            "opencode": [f"deny {', '.join(OPENCODE_DENIED)}; execute screened for network and import use"]}[host.name]}
    if receipt_dir:
        result["stdioProxy"] = {"enabled": True, "receiptCount": sum(len(run.get("stdioProxy", [])) for run in runs)}
    if args.probe_schema:
        result["schemaProbe"] = probe_runs[-1] if probe_runs else {"connections": [], "verdict": {"verdict": "not-observed: no prompt ran"}}
    return result


def _run_prompts(host: HostConfig, args: argparse.Namespace, prompt_set: dict, env: dict[str, str], workspace: Path, workspace_id: str,
                 profile: Profile, protected: list[Path], sandbox: OsSandbox, secrets: Secrets, out_dir: Path, scoring: Any,
                 receipts: Path | None, seen: set[str], probe_runs: list[dict], ctx: dict,
                 receipt_dir: Path | None = None) -> tuple[list[dict], list[str]]:
    runs, violations = [], []
    for repetition in range(1, args.repetitions + 1):
        for case in prompt_set["cases"]:
            prior_receipts = {path.name for path in proxy_receipt_paths(receipt_dir)} if receipt_dir else set()
            argv = prompt_argv(host, case["prompt"].replace(WORKSPACE_PLACEHOLDER, workspace_id), args)
            started = time.time()
            done = run_process(argv, env, workspace, profile, protected, sandbox, args.timeout, f"{host.name} {case['id']}")
            stdout = secrets.redact(done.stdout)
            stderr = secrets.redact(done.stderr)
            transcript = HOST_PARSERS[host.name](done.stdout)
            if done.returncode != 0 and not transcript.tool_calls and not transcript.text:
                # The host failed before the model answered (authentication, quota, network): not a measurement.
                tail = (stdout.strip().splitlines() or stderr.strip().splitlines() or ["no output"])[-1][:240]
                raise DeclaredLimit(f"{host.name} failed before the model answered (exit {done.returncode}): {tail}")
            classes = [(call, tool_class(host.name, call)) for call in transcript.tool_calls]
            denied = [{"tool": call.tool, "outcome": "refused" if call.is_error else "executed"} for call, cls in classes if cls == "denied"]
            attempts = attempts_from(transcript, host.name)
            file = out_dir / host.name / f"{case['id']}-r{repetition}.jsonl"
            file.parent.mkdir(parents=True, exist_ok=True)
            body = (stdout if stdout.endswith("\n") or not stdout else stdout + "\n") + "\n".join(f"#stderr {line}" for line in stderr.splitlines()[-40:]) + "\n"
            secrets.assert_clean(str(file.name), body)
            file.write_text(body)
            record = {"caseId": case["id"], "repetition": repetition, "exitCode": done.returncode, "timedOut": done.timed_out,
                      "durationSeconds": round(time.time() - started, 1),
                      "transcript": {"file": str(file.relative_to(out_dir.parent)), "sha256": sha256_bytes(body.encode()), "bytes": len(body.encode())},
                      "toolCalls": [{"tool": call.tool, "class": cls, "isError": call.is_error} for call, cls in classes],
                      "deniedToolRequests": denied, "models": transcript.models, "usage": secrets.redact_json(transcript.usage),
                      "keySourceReported": secrets.redact(transcript.key_source) if transcript.key_source else None,
                      "attempts": secrets.redact_json(attempts)}
            if receipts is not None:
                connections = probe_connections(read_receipts(receipts, seen), ctx["expected"], out_dir, host.name, secrets)
                verdict = probe_verdict(host.name, connections, done.stdout, done.stderr, transcript)
                probe_runs.append({"connections": connections, "verdict": verdict})
                record["probe"] = {"verdict": verdict["verdict"], "loading": verdict["loading"]}
            else:
                record["score"] = scoring.score_case(case, attempts)
            if receipt_dir:
                record["stdioProxy"] = new_proxy_receipts(receipt_dir, prior_receipts)
            runs.append(record)
            if any(item["outcome"] == "executed" for item in denied):
                violations.append(f"{case['id']} r{repetition}: a denied tool ran: {denied}")
                break
        if violations:
            break
    return runs, violations


def write_evidence(path: Path, evidence: dict, secrets: Secrets) -> None:
    text = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    secrets.assert_clean(path.name, text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


MANUAL_STEPS = [
    {"step": "Store the API keys once (macOS keychain generic passwords, or export them in your own terminal before the run)", "reason": "keys are read from the driver environment or the keychain only and are never prompted for, written or logged (D13)"},
    {"step": "Subscription mode only: sign in once per host in your own Terminal.app (--login HOST prints the command)", "reason": "the driver never reads a terminal or a credential file (D13: interactive-once)"},
    {"step": "Token mode only: run `claude setup-token` in your own Terminal.app and store the token silently (security add-generic-password -a \"$USER\" -s agent-braid-claude-oauth -w)", "reason": "the driver never reads a terminal and never prompts for or logs a token (D13)"},
    {"step": "Install Codex when the ChatGPT desktop bundle is absent (--codex-bin)", "reason": "the driver does not install host applications (D11)"},
    {"step": "Decide on the release (REQ-012) and on the result of a run", "reason": "owner decisions are not automated (D5)"},
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--prompt-set", default="development", help="a set id under specs/069-aim-request-authoring/prompts/ or a path")
    p.add_argument("--arm", choices=ARMS, default="final",
                   help="baseline = alpha.7 + #1099; final = candidate with per-kind schemas; final-no-schema = candidate with the interim description only (D9)")
    p.add_argument("--hosts", default=",".join(HOSTS))
    p.add_argument("--repetitions", type=int, default=1, help="D9 asks for 3 per prompt in a measured run")
    p.add_argument("--limit-cases", type=int, default=0, help="run only the first N prompts (probes)")
    p.add_argument("--plugin-dir", type=Path, help="a prebuilt plugins/agent-braid directory; skips the build")
    p.add_argument("--build-cache", type=Path, default=Path(tempfile.gettempdir()) / "agent-braid-spec069-build-cache")
    p.add_argument("--allow-dirty", action="store_true", help="build from a dirty checkout (engineering artifact, recorded)")
    p.add_argument("--model", action="append", default=[], metavar="HOST=ID", help="pin the model per host (D9)")
    p.add_argument("--claude-bin")
    p.add_argument("--codex-bin")
    p.add_argument("--opencode-bin")
    p.add_argument("--timeout", type=int, default=300)
    p.add_argument("--max-turns", type=int, default=12)
    p.add_argument("--output", type=Path, help="evidence file (default: evidence/native-runs-<arm>.json)")
    p.add_argument("--keys-from-keychain", action="store_true",
                   help="read each host's key from the macOS keychain (services agent-braid-anthropic/-openai/-openrouter); the environment is not used")
    p.add_argument("--security-bin", default="/usr/bin/security", help=argparse.SUPPRESS)
    p.add_argument("--auth", choices=("key", "subscription", "token"), default="key",
                   help="key = API key (default); subscription = one-time sign-in in --auth-profile-dir (claude-code, codex; D13 fallback); "
                        "token = long-lived Claude Code OAuth token from `claude setup-token` (claude-code only; keychain agent-braid-claude-oauth or CLAUDE_CODE_OAUTH_TOKEN)")
    p.add_argument("--auth-profile-dir", type=Path, help="dedicated reusable sign-in directory (outside the repo and every real host configuration); kept across runs")
    p.add_argument("--login", choices=("claude-code", "codex"), metavar="HOST", help="print the command to sign in HOST in your own terminal, then exit")
    p.add_argument("--check-login", choices=("claude-code", "codex"), metavar="HOST",
                   help="confirm the sign-in (credential file existence and size, never its contents, plus one trivial headless prompt), then exit")
    p.add_argument("--fake-hosts", action="store_true", help="run the same pipeline against the fake hosts (pipeline-only evidence)")
    p.add_argument("--record-mcp", action="store_true",
                   help="opt-in: wrap the disposable installed candidate and persist private hash-only MCP connection receipts (does not cap provider spend)")
    p.add_argument("--fake-variant", choices=FAKE_VARIANTS, default="default")
    p.add_argument("--probe-schema", action="store_true",
                   help="T005 host probe: one prompt with an aim and a units analyze-work call per host through a recording stdio relay in "
                        "the disposable installed copy; records protocol version, raw tools/list line and hashes, byte identity against the "
                        "build fingerprint, object or string requests at the server and eager or deferred loading (--arm final = per-kind, "
                        "final-no-schema = description-only)")
    p.add_argument("--extra-env", action="append", default=[], metavar="KEY=VALUE",
                   help="add a variable to the host environment; a value naming a real configuration path stops the run")
    p.add_argument("--real-home", type=Path, default=None, help="protected home (default: the account home)")
    p.add_argument("--no-os-sandbox", action="store_true", help="engineering probe only; never for measured evidence")
    args = p.parse_args(argv)
    args.plugin_root_for = {}
    if args.probe_schema:
        if args.arm not in PROBE_DELIVERY:
            p.error("--probe-schema needs --arm final (per-kind) or final-no-schema (description-only)")
        if args.repetitions != 1 or args.limit_cases:
            p.error("--probe-schema runs one prompt once per host")
    if args.fake_hosts and args.security_bin == "/usr/bin/security":
        args.security_bin = str(FAKE_HOSTS_DIR / "security")
    if args.probe_schema and args.record_mcp:
        p.error("--probe-schema installs its own recording relay; do not combine it with --record-mcp")
    if args.fake_hosts and args.record_mcp:
        p.error("--record-mcp requires the real installed candidate; fake-host runs cannot produce product-boundary evidence")
    token_mode = args.auth == "token"
    if token_mode and ((args.login or args.check_login) not in (None, "claude-code")):
        p.error("--auth token applies to claude-code only")
    if (args.auth == "subscription" or ((args.login or args.check_login) and not token_mode)) and not args.auth_profile_dir:
        p.error("--auth subscription, --login and --check-login need --auth-profile-dir (except with --auth token)")
    return args


def login_command(host: str, auth_home: Path) -> str:
    target = shlex.quote(str(auth_home / AUTH_SUBDIR[host]))
    return f"mkdir -p -m 700 {target} && " + LOGIN_COMMAND[host].format(dir=target)


def print_login(args: argparse.Namespace) -> int:
    """Print the sign-in command only. Nothing is started, read or created."""
    if args.auth == "token":
        print("Create the token once in your own Terminal.app (the driver never reads the terminal; never paste the token in chat):\n\n"
              "    claude setup-token\n"
              f"    security add-generic-password -a \"$USER\" -s {KEYCHAIN_SERVICES['claude-oauth']} -w    # type the token silently\n\n"
              "Then confirm with: python -m scripts.spec069_native_runs --check-login claude-code --auth token --keys-from-keychain")
        return 0
    protected = real_config_paths(args.real_home or real_home())
    try:
        auth_home = check_auth_profile(args.auth_profile_dir, protected)
    except SafetyStop as stop:
        print(f"refused: {stop}", file=sys.stderr)
        return EXIT_SAFETY
    print(f"Run this in your own Terminal.app ({LOGIN_HINT[args.login]}); the driver never reads the terminal or the credential file:\n\n"
          f"    {login_command(args.login, auth_home)}\n\nThen confirm with: python -m scripts.spec069_native_runs --check-login {args.login} "
          f"--auth-profile-dir {shlex.quote(str(auth_home))}")
    return 0


def check_login(args: argparse.Namespace) -> int:
    """Credential file existence and size (never contents) plus one trivial headless prompt under the run's sandbox."""
    host_name = args.check_login
    protected = real_config_paths(args.real_home or real_home())
    sandbox = OsSandbox(protected, enabled=not args.no_os_sandbox)
    secrets = Secrets()
    profile = Profile()
    result: dict[str, Any] = {"host": host_name, "ok": False}
    token = None
    try:
        if args.auth == "token":
            auth_home = None
            try:
                token, source = acquire_oauth_token(args)
            except DeclaredLimit as limit:
                result["error"] = f"declared limit: {limit}"
                return 1
            secrets.add(token)
            result["credential"] = {"auth": OAUTH_AUTH, "source": source, "present": True, "length": len(token)}  # presence and length only
        else:
            auth_home = prepare_auth_profile(args.auth_profile_dir, protected)
            result["credential"] = credential_file_info(auth_home, host_name)
        binary = host_binary(host_name, args)
        if binary is None:
            result["error"] = f"{host_name} executable not found"
            return 1
        host = HostConfig(host_name, binary, (), "", fake=args.fake_hosts)
        env = build_host_env(profile, host, None, profile.make("hosts", host_name, "agent-braid-home"), {"FAKE_PYTHON": sys.executable,
                             **({k: os.environ[k] for k in ("FAKE_LOG", "FAKE_VARIANT") if k in os.environ} | {"FAKE_REQUIRE_LOGIN": "1"} if args.fake_hosts else {})}, auth_home, token)
        cwd = profile.make("hosts", host_name, "workspace")
        probe = probe_isolation(env, Path(env["HOME"]), sandbox, protected)
        result["sandbox"] = probe["sandbox"]
        if auth_home is not None:
            result["usableUnderSandbox"] = auth_dir_usable(env, auth_home, host_name, sandbox)
        binary_s = str(binary)
        argv = ([binary_s, "-p", TRIVIAL_PROMPT, "--output-format", "stream-json", "--verbose", "--max-turns", "1", "--no-session-persistence",
                 "--tools", ""] if host_name == "claude-code" else
                [binary_s, "exec", "--json", "--skip-git-repo-check", "-s", "read-only", "-c", 'approval_policy="never"', TRIVIAL_PROMPT])
        done = run_process(argv, env, cwd, profile, protected, sandbox, args.timeout, f"{host_name} check-login")
        transcript = PARSERS[host_name](done.stdout)
        result["ok"] = done.returncode == 0 and bool(transcript.text.strip())
        if not result["ok"]:
            tail = (done.stdout.strip().splitlines() or done.stderr.strip().splitlines() or ["no output"])[-1][:200]
            result["error"] = secrets.redact(f"headless prompt failed (exit {done.returncode}): {tail}")
            if token is not None:
                result["error"] += "; declared limit: the token may be rejected or expired (run `claude setup-token` again and store it)"
        elif auth_home is not None and not result["credential"]["exists"]:
            result["note"] = "no credential file in the dedicated profile; the session works, so it is held elsewhere (for example the keychain)"
    except SafetyStop as stop:
        result["error"] = f"safety stop: {stop}"
        return EXIT_SAFETY
    finally:
        result["teardown"] = profile.teardown()
        print(json.dumps(result))
    return 0 if result["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.login:
        return print_login(args)
    if args.check_login:
        return check_login(args)
    from scripts import spec069_fixture_workspace as fixture
    from scripts import spec069_scoring as scoring

    if args.probe_schema:
        prompt_set, prompt_path = probe_prompt_set(), PROBE_AIM_FIXTURE
    else:
        prompt_set, prompt_path = load_prompt_set(args.prompt_set)
    if args.limit_cases:
        prompt_set = {**prompt_set, "cases": prompt_set["cases"][: args.limit_cases]}
    models = dict(item.split("=", 1) for item in args.model)
    secrets = Secrets()
    passthrough = dict(item.split("=", 1) for item in args.extra_env)
    for name in ("ANTHROPIC_BASE_URL",):
        # the base URL belongs to the environment key: it never follows a keychain key or a subscription sign-in
        if os.environ.get(name) and not args.fake_hosts and not args.keys_from_keychain and args.auth == "key":
            passthrough.setdefault(name, os.environ[name])
            secrets.add(os.environ[name])
    home = args.real_home or real_home()
    protected = real_config_paths(home)
    sandbox = OsSandbox(protected, enabled=not args.no_os_sandbox)
    stem = "native-probe-schema" if args.probe_schema else "native-runs"
    out_file = args.output or SPEC_DIR / "evidence" / f"{stem}-{args.arm}{'-fake' if args.fake_hosts else ''}.json"
    out_dir = out_file.with_suffix(".transcripts")
    profile = Profile()
    evidence: dict[str, Any] = {"evidenceVersion": 1, "task": "SPEC-069 T013", "label": evidence_label(args.fake_hosts),
                                "generatedAt": utc_now(), "arm": args.arm, "platform": platform.platform(),
                                "promptSet": {"setId": prompt_set["setId"], "file": str(prompt_path.name),
                                              "sha256": sha256_file(prompt_path), "cases": len(prompt_set["cases"])},
                                "repetitions": args.repetitions, "hosts": {}, "manualSteps": MANUAL_STEPS, "authMode": args.auth,
                                "keysFromKeychain": args.keys_from_keychain,
                                "driverSha256": sha256_file(Path(__file__)), "scoringSha256": sha256_file(Path(scoring.__file__))}
    expected: dict[str, Any] | None = None
    if args.probe_schema:
        delivery = PROBE_DELIVERY[args.arm]
        expected = expected_fingerprints()[delivery]
        evidence["task"] = "SPEC-069 T005 host probe of the analyze-work schema (procedure_005)"
        evidence["promptSet"] = {"setId": prompt_set["setId"], "promptSha256": sha256_bytes(prompt_set["cases"][0]["prompt"].encode()),
                                 "fixtures": {str(f.relative_to(ROOT)): sha256_file(f) for f in (PROBE_AIM_FIXTURE, PROBE_UNITS_FIXTURE)},
                                 "cases": 1, "prompt": prompt_set["cases"][0]["prompt"]}
        evidence["schemaProbe"] = {"delivery": delivery, "relaySha256": sha256_file(PROBE_RELAY),
                                   "expectedFingerprint": {"sha256": expected["sha256"], "bytes": expected["bytes"],
                                                           "canonicalSha256": expected["canonicalSha256"],
                                                           "source": "scripts.spec069_capture_t005_evidence.listed_sizes() on this checkout"}}
    if args.fake_hosts:
        evidence["note"] = "PIPELINE ONLY: fake host executables prove the driver pipeline, not any host or model."
    exit_code = 0
    try:
        work = profile.make("work")
        if args.plugin_dir:
            plugin_dir, evidence["candidate"] = args.plugin_dir, {"arm": args.arm, "prebuilt": True}
        elif args.fake_hosts:
            plugin_dir = fake_plugin(work, expected["text"] if args.probe_schema else None)
            evidence["candidate"] = {"arm": args.arm, "fake": True}
        else:
            plugin_dir, evidence["candidate"] = build_candidate(args.arm, work, args.build_cache, args.allow_dirty)
        auth_home = prepare_auth_profile(args.auth_profile_dir, protected) if args.auth == "subscription" else None
        ctx = {"plugin_dir": plugin_dir, "protected": protected, "sandbox": sandbox, "passthrough": passthrough, "auth_home": auth_home,
               "expected": expected if args.probe_schema else None}
        if args.fake_hosts:
            scenario = (build_probe_scenario(prompt_set["cases"][0]["prompt"].replace(WORKSPACE_PLACEHOLDER, "fake-workspace-0001"))
                        if args.probe_schema else build_fake_scenario(prompt_set["cases"], args.fake_variant, scoring.reference_request))
            scenario_file = profile.make("fake") / "scenario.json"
            scenario_file.write_text(json.dumps(scenario))
            planted = "sk-ant-PLANTED-" + sha256_bytes(b"planted")[:24]
            secrets.add(planted)
            passthrough.update({"FAKE_SCENARIO": str(scenario_file), "FAKE_VARIANT": args.fake_variant, "FAKE_PLANTED_SECRET": planted,
                                "FAKE_PYTHON": sys.executable})
            if args.auth == "subscription":
                passthrough["FAKE_REQUIRE_LOGIN"] = "1"
            if args.probe_schema:
                passthrough["FAKE_PROBE"] = "1"
            os.environ.setdefault("ANTHROPIC_API_KEY", "fake-anthropic-key-0001")
        for name in [h for h in args.hosts.split(",") if h]:
            binary = host_binary(name, args)
            if binary is None:
                evidence["hosts"][name] = {"status": "declared-limit", "limit": f"{name} executable not found"}
                continue
            host = HostConfig(name, binary, *key_spec(name, models.get(name)), model=models.get(name), fake=args.fake_hosts)
            try:
                evidence["hosts"][name] = run_host(host, args, prompt_set, ctx, profile, secrets, out_dir, scoring, fixture)
            except DeclaredLimit as limit:
                evidence["hosts"][name] = {"status": "declared-limit", "limit": secrets.redact(str(limit))}
        if args.probe_schema:
            evidence["schemaProbe"]["crossHost"] = cross_host_identity(evidence["hosts"])
            evidence["summary"] = {n: (h["schemaProbe"]["verdict"] if h.get("status") == "ran" else {"verdict": "declared-limit: " + h.get("limit", "")})
                                   for n, h in evidence["hosts"].items()}
        else:
            results = {n: [dict(r["score"], caseId=r["caseId"],repetition=r["repetition"]) for r in h["runs"]]
                       for n, h in evidence["hosts"].items() if h.get("status") == "ran"}
            evidence["summary"] = scoring.summarize(results, repetitions=args.repetitions) if results else {"overall": "inconclusive"}
        if args.record_mcp:
            evidence["stdioProxy"] = summarize_stdio_proxy(evidence["hosts"])
    except SafetyStop as stop:
        evidence["stopped"] = secrets.redact(str(stop))
        exit_code = EXIT_SAFETY
    except SecretLeak as leak:
        evidence["stopped"] = str(leak)
        exit_code = EXIT_SECRET
    finally:
        evidence["teardown"] = profile.teardown()
    if not evidence["teardown"]["clean"]:
        exit_code = exit_code or EXIT_TEARDOWN
    try:
        write_evidence(out_file, evidence, secrets)
    except SecretLeak as leak:
        print(f"refusing to write evidence: {leak}", file=sys.stderr)
        return EXIT_SECRET
    print(json.dumps({"evidence": str(out_file), "label": evidence["label"], "exit": exit_code, "stopped": evidence.get("stopped"),
                      "teardown": evidence["teardown"], "hosts": {n: h.get("status") for n, h in evidence["hosts"].items()}}))
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
