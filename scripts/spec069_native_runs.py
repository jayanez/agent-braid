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
    short_name, tool_class, utc_now)

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
KEYCHAIN_SERVICES = {"anthropic": "agent-braid-anthropic", "openai": "agent-braid-openai", "openrouter": "agent-braid-openrouter"}
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


def acquire_credential(host: HostConfig, args: argparse.Namespace) -> tuple[str | None, str, str]:
    """``(key or None, auth, key source)``. Raises DeclaredLimit when the host's credential is not available."""
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


def build_host_env(profile: Profile, host: HostConfig, key: str | None, ab_home: Path, passthrough: dict[str, str],
                   auth_home: Path | None = None) -> dict[str, str]:
    """A minimal environment: private HOME/XDG, the one credential, no inherited variables.

    With ``auth_home`` (subscription mode) the host's configuration directory is the dedicated sign-in directory and no key is set.
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


def fake_plugin(work: Path) -> Path:
    """A stand-in plugin tree for ``--fake-hosts``: its launcher answers ``plugin setup`` like the real one."""
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
    market = plugin.parent.parent / ".agents/plugins"
    market.mkdir(parents=True)
    (market / "marketplace.json").write_text(json.dumps({"name": PLUGIN_NAME}))
    return plugin


# ----------------------------------------------------------------------------
# Fake-host scenarios (--fake-hosts)
# ----------------------------------------------------------------------------
FAKE_VARIANTS = ("default", "retry", "denied-tool", "executed-tool", "leak-secret", "straggler", "echo-credentials")


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
    route = route_of(host.name, host.model)
    if host.name == "opencode" and not host.model and not args.fake_hosts:
        raise DeclaredLimit("OpenCode needs --model opencode=anthropic/<id> or openrouter/<id>: without it the host uses a free hosted model")
    secrets.add(key)
    auth_home = ctx["auth_home"] if auth == "interactive-once" else None
    ab_home = profile.make("hosts", host.name, "agent-braid-home")
    passthrough = dict(ctx["passthrough"])
    env = build_host_env(profile, host, key, ab_home, passthrough, auth_home)
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
    plugin_root = install_plugin(host, ctx["plugin_dir"], env, profile, workspace, protected, sandbox, args)
    args.plugin_root_for[host.name] = plugin_root
    write_host_policy(host, env)
    workspace_id = register_workspace(plugin_root, workspace, env, profile, protected, sandbox, ab_home)
    runs, violations = [], []
    for repetition in range(1, args.repetitions + 1):
        for case in prompt_set["cases"]:
            argv = prompt_argv(host, case["prompt"], args)
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
                      "attempts": secrets.redact_json(attempts), "score": scoring.score_case(case, attempts)}
            runs.append(record)
            if any(item["outcome"] == "executed" for item in denied):
                violations.append(f"{case['id']} r{repetition}: a denied tool ran: {denied}")
                break
        if violations:
            break
    if violations:
        raise SafetyStop(f"{host.name}: " + "; ".join(violations))
    reported = sorted({r["keySourceReported"] for r in runs if r.get("keySourceReported")})
    notes = ([OPENROUTER_NOTE, OPENCODE_MODEL_NOTE] if route == "openrouter" else []) + ([SUBSCRIPTION_NOTE] if auth == "interactive-once" else [])
    return {"status": "ran", "version": version, "auth": auth, "keySource": key_source, "route": route, "notes": notes,
            "hostReportedKeySource": reported, "modelPinned": bool(host.model), "model": host.model,
            "modelsObserved": sorted({m for run in runs for m in run["models"]}), "osSandbox": probe["sandbox"],
            "probe": probe, "workspaceRegistered": bool(workspace_id), "runs": runs,
            "allowlist": {"claude-code": CLAUDE_ALLOWED, "codex": ["agent-braid MCP server; read-only sandbox; approval never"],
                          "opencode": [f"deny {', '.join(OPENCODE_DENIED)}; execute screened for network and import use"]}[host.name]}


def write_evidence(path: Path, evidence: dict, secrets: Secrets) -> None:
    text = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    secrets.assert_clean(path.name, text)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


MANUAL_STEPS = [
    {"step": "Store the API keys once (macOS keychain generic passwords, or export them in your own terminal before the run)", "reason": "keys are read from the driver environment or the keychain only and are never prompted for, written or logged (D13)"},
    {"step": "Subscription mode only: sign in once per host in your own Terminal.app (--login HOST prints the command)", "reason": "the driver never reads a terminal or a credential file (D13: interactive-once)"},
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
    p.add_argument("--auth", choices=("key", "subscription"), default="key",
                   help="key = API key (default); subscription = one-time sign-in in --auth-profile-dir (claude-code, codex; D13 fallback)")
    p.add_argument("--auth-profile-dir", type=Path, help="dedicated reusable sign-in directory (outside the repo and every real host configuration); kept across runs")
    p.add_argument("--login", choices=("claude-code", "codex"), metavar="HOST", help="print the command to sign in HOST in your own terminal, then exit")
    p.add_argument("--check-login", choices=("claude-code", "codex"), metavar="HOST",
                   help="confirm the sign-in (credential file existence and size, never its contents, plus one trivial headless prompt), then exit")
    p.add_argument("--fake-hosts", action="store_true", help="run the same pipeline against the fake hosts (pipeline-only evidence)")
    p.add_argument("--fake-variant", choices=FAKE_VARIANTS, default="default")
    p.add_argument("--extra-env", action="append", default=[], metavar="KEY=VALUE",
                   help="add a variable to the host environment; a value naming a real configuration path stops the run")
    p.add_argument("--real-home", type=Path, default=None, help="protected home (default: the account home)")
    p.add_argument("--no-os-sandbox", action="store_true", help="engineering probe only; never for measured evidence")
    args = p.parse_args(argv)
    args.plugin_root_for = {}
    if args.fake_hosts and args.security_bin == "/usr/bin/security":
        args.security_bin = str(FAKE_HOSTS_DIR / "security")
    if (args.auth == "subscription" or args.login or args.check_login) and not args.auth_profile_dir:
        p.error("--auth subscription, --login and --check-login need --auth-profile-dir")
    return args


def login_command(host: str, auth_home: Path) -> str:
    target = shlex.quote(str(auth_home / AUTH_SUBDIR[host]))
    return f"mkdir -p -m 700 {target} && " + LOGIN_COMMAND[host].format(dir=target)


def print_login(args: argparse.Namespace) -> int:
    """Print the sign-in command only. Nothing is started, read or created."""
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
    try:
        auth_home = prepare_auth_profile(args.auth_profile_dir, protected)
        binary = host_binary(host_name, args)
        result["credential"] = credential_file_info(auth_home, host_name)
        if binary is None:
            result["error"] = f"{host_name} executable not found"
            return 1
        host = HostConfig(host_name, binary, (), "", fake=args.fake_hosts)
        env = build_host_env(profile, host, None, profile.make("hosts", host_name, "agent-braid-home"), {"FAKE_PYTHON": sys.executable,
                             **({k: os.environ[k] for k in ("FAKE_LOG", "FAKE_VARIANT") if k in os.environ} | {"FAKE_REQUIRE_LOGIN": "1"} if args.fake_hosts else {})}, auth_home)
        cwd = profile.make("hosts", host_name, "workspace")
        probe = probe_isolation(env, Path(env["HOME"]), sandbox, protected)
        result["sandbox"] = probe["sandbox"]
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
        elif not result["credential"]["exists"]:
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
    out_file = args.output or SPEC_DIR / "evidence" / f"native-runs-{args.arm}{'-fake' if args.fake_hosts else ''}.json"
    out_dir = out_file.with_suffix(".transcripts")
    profile = Profile()
    evidence: dict[str, Any] = {"evidenceVersion": 1, "task": "SPEC-069 T013", "label": evidence_label(args.fake_hosts),
                                "generatedAt": utc_now(), "arm": args.arm, "platform": platform.platform(),
                                "promptSet": {"setId": prompt_set["setId"], "file": str(prompt_path.name),
                                              "sha256": sha256_file(prompt_path), "cases": len(prompt_set["cases"])},
                                "repetitions": args.repetitions, "hosts": {}, "manualSteps": MANUAL_STEPS, "authMode": args.auth,
                                "keysFromKeychain": args.keys_from_keychain,
                                "driverSha256": sha256_file(Path(__file__)), "scoringSha256": sha256_file(Path(scoring.__file__))}
    if args.fake_hosts:
        evidence["note"] = "PIPELINE ONLY: fake host executables prove the driver pipeline, not any host or model."
    exit_code = 0
    try:
        work = profile.make("work")
        if args.plugin_dir:
            plugin_dir, evidence["candidate"] = args.plugin_dir, {"arm": args.arm, "prebuilt": True}
        elif args.fake_hosts:
            plugin_dir, evidence["candidate"] = fake_plugin(work), {"arm": args.arm, "fake": True}
        else:
            plugin_dir, evidence["candidate"] = build_candidate(args.arm, work, args.build_cache, args.allow_dirty)
        auth_home = prepare_auth_profile(args.auth_profile_dir, protected) if args.auth == "subscription" else None
        ctx = {"plugin_dir": plugin_dir, "protected": protected, "sandbox": sandbox, "passthrough": passthrough, "auth_home": auth_home}
        if args.fake_hosts:
            scenario = build_fake_scenario(prompt_set["cases"], args.fake_variant, scoring.reference_request)
            scenario_file = profile.make("fake") / "scenario.json"
            scenario_file.write_text(json.dumps(scenario))
            planted = "sk-ant-PLANTED-" + sha256_bytes(b"planted")[:24]
            secrets.add(planted)
            passthrough.update({"FAKE_SCENARIO": str(scenario_file), "FAKE_VARIANT": args.fake_variant, "FAKE_PLANTED_SECRET": planted,
                                "FAKE_PYTHON": sys.executable})
            if args.auth == "subscription":
                passthrough["FAKE_REQUIRE_LOGIN"] = "1"
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
        results = {n: [dict(r["score"], caseId=r["caseId"],repetition=r["repetition"]) for r in h["runs"]]
                   for n, h in evidence["hosts"].items() if h.get("status") == "ran"}
        evidence["summary"] = scoring.summarize(results, repetitions=args.repetitions) if results else {"overall": "inconclusive"}
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
