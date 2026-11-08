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
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import os
import platform
import pwd
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "specs/069-aim-request-authoring"
FAKE_HOSTS_DIR = ROOT / "tests/fixtures/spec069-fake-hosts"
BASELINE_COMMIT = "8f63c606"  # develop commit of PR #1099: alpha.7 runtime plus the interim guidance
DEFAULT_CODEX_BIN = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"
DEFAULT_OPENCODE_BIN = "~/.opencode/bin/opencode"
HOSTS = ("claude-code", "codex", "opencode")
ARMS = ("baseline", "final", "final-no-schema")
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
PLUGIN_NAME = "agent-braid"
# ToolSearch and Skill are host-side helpers: tool discovery, and the plugin's packaged guidance (the thing under measurement).
CLAUDE_ALLOWED = ["mcp__plugin_agent-braid_agent-braid__*", "ToolSearch", "Skill"]
# Built-in tools the host may offer: schema discovery and the plugin's packaged skills only. Anything else
# (for example ListAgents, SendMessage, TaskStop) is not available at all, rather than denied one by one.
CLAUDE_BUILTIN = ["ToolSearch", "Skill"]
CLAUDE_DENIED = ["Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Read", "Glob", "Grep", "Task", "Agent"]
OPENCODE_DENIED = ["bash", "edit", "write", "webfetch", "websearch", "read", "glob", "grep", "list", "task", "external_directory"]
# Host-side discovery helpers the host itself needs before it can see MCP tools (observed, see the runbook).
META_TOOLS = {"claude-code": {"ToolSearch", "Skill"}, "codex": set(), "opencode": {"execute", "skill"}}
EXIT_SAFETY, EXIT_TEARDOWN, EXIT_SECRET = 2, 3, 4


class SafetyStop(RuntimeError):
    """A safety invariant failed; nothing further may run."""


class SecretLeak(RuntimeError):
    """A secret was found in material about to be written."""


class DeclaredLimit(RuntimeError):
    """A host cannot run in this environment; reported, never replaced by a manual step."""


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def real_home() -> Path:
    return Path(pwd.getpwuid(os.getuid()).pw_dir)


# ----------------------------------------------------------------------------
# Secrets: redaction and scan
# ----------------------------------------------------------------------------
SECRET_PATTERNS = [re.compile(p) for p in (
    r"\bsk-ant-[A-Za-z0-9_\-]{8,}", r"\bsk-[A-Za-z0-9_\-]{16,}", r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}",
    r"\bAIza[0-9A-Za-z_\-]{20,}", r"\bxox[abprs]-[A-Za-z0-9\-]{10,}", r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"\bAKIA[0-9A-Z]{16}\b")]


class Secrets:
    """The literal secret values this process knows, plus generic credential patterns."""

    def __init__(self, values: list[str] | None = None) -> None:
        self.values: list[str] = []
        for value in values or []:
            self.add(value)

    def add(self, value: str | None) -> None:
        if value and len(value) >= 6 and value not in self.values:
            self.values.append(value)
            self.values.sort(key=len, reverse=True)

    def redact(self, text: str) -> str:
        for value in self.values:
            text = text.replace(value, "[REDACTED]")
        for pattern in SECRET_PATTERNS:
            text = pattern.sub("[REDACTED]", text)
        return text

    def redact_json(self, value: Any) -> Any:
        return json.loads(self.redact(json.dumps(value, ensure_ascii=False)))

    def scan(self, text: str) -> list[str]:
        found = [f"literal secret value ({len(v)} chars)" for v in self.values if v in text]
        found += [f"pattern {p.pattern[:24]}" for p in SECRET_PATTERNS if p.search(text)]
        return found

    def assert_clean(self, name: str, text: str) -> None:
        found = self.scan(text)
        if found:
            raise SecretLeak(f"secret scan failed for {name}: {', '.join(found)}")


# ----------------------------------------------------------------------------
# Isolation: real paths, leak guard, OS sandbox, canary and denied-access probe
# ----------------------------------------------------------------------------
def real_config_paths(home: Path) -> list[Path]:
    """Host configuration, data and credential stores that a driver run must never reach."""
    names = [".claude", ".claude.json", ".codex", ".config/opencode", ".local/share/opencode", ".local/state/opencode",
             ".cache/opencode", "Library/Keychains", ".ssh", ".aws", ".gnupg", ".netrc",
             "Library/Application Support/Claude", "Library/Application Support/Codex"]
    return [home / name for name in names]


def guard_leaks(label: str, env: dict[str, str], argv: list[str], protected: list[Path]) -> None:
    """Stop when an environment value or argument names a protected real path."""
    haystacks = [f"env {k}" for k in env if any(str(p) in env[k] for p in protected)]
    haystacks += [f"argument {i}" for i, a in enumerate(argv) if any(str(p) in a for p in protected)]
    if haystacks:
        raise SafetyStop(f"{label}: a real configuration path is named in " + ", ".join(haystacks))


def sandbox_profile(protected: list[Path]) -> str:
    rules = []
    for path in protected:
        for variant in {str(path), os.path.realpath(path)}:
            kind = "literal" if variant.endswith(".json") or variant.endswith(".netrc") else "subpath"
            rules.append(f'(deny file-read* file-write* ({kind} "{variant}"))')
    return "(version 1)\n(allow default)\n" + "\n".join(rules) + "\n"


class OsSandbox:
    """macOS ``sandbox-exec`` that denies the real configuration paths; elsewhere unavailable (declared)."""

    def __init__(self, protected: list[Path], enabled: bool = True) -> None:
        self.protected = protected
        self.tool = shutil.which("sandbox-exec") if enabled and sys.platform == "darwin" else None

    @property
    def name(self) -> str:
        return "sandbox-exec" if self.tool else "none"

    def wrap(self, argv: list[str]) -> list[str]:
        if not self.tool:
            return argv
        return [self.tool, "-p", sandbox_profile(self.protected), *argv]


CANARY_TOKEN = "spec069-canary-" + sha256_bytes(b"spec069-canary")[:16]


def probe_isolation(env: dict[str, str], home_dir: Path, sandbox: OsSandbox, protected: list[Path]) -> dict[str, Any]:
    """Canary read through the redirected home and denied read of every existing real path."""
    canary = home_dir / ".claude" / "CANARY"
    canary.parent.mkdir(parents=True, exist_ok=True)
    canary.write_text(CANARY_TOKEN)
    # The sandbox profile above is applied to the host; the probe reuses it so it proves the same boundary.
    got = subprocess.run(sandbox.wrap(["/bin/sh", "-c", 'cat "$HOME/.claude/CANARY"']), env=env, capture_output=True,
                         text=True, timeout=30)
    canary_ok = got.returncode == 0 and got.stdout.strip() == CANARY_TOKEN
    denied = []
    for path in protected:
        if not path.exists():
            continue
        read = subprocess.run(sandbox.wrap(["/bin/sh", "-c", 'ls "$1" >/dev/null 2>&1 || cat "$1" >/dev/null 2>&1', "sh", str(path)]),
                              env=env, capture_output=True, text=True, timeout=30)
        denied.append({"path": "~/" + str(path.relative_to(real_home())) if str(path).startswith(str(real_home())) else path.name,
                       "denied": read.returncode != 0})
    enforced = sandbox.name != "none"
    result = {"sandbox": sandbox.name, "canaryReadThroughRedirectedHome": canary_ok, "deniedPaths": denied,
              "enforced": enforced and all(item["denied"] for item in denied)}
    if not canary_ok:
        raise SafetyStop("isolation probe: the canary configuration was not read through the redirected home")
    if enforced and not result["enforced"]:
        raise SafetyStop("isolation probe: a real configuration path was readable under the sandbox")
    return result


# ----------------------------------------------------------------------------
# Disposable profile and teardown
# ----------------------------------------------------------------------------
def process_list() -> list[tuple[int, int, str]]:
    """``(pid, parent pid, command line)`` of every process."""
    out = subprocess.run(["ps", "-axo", "pid=,ppid=,command="], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) == 3 and parts[0].isdigit() and parts[1].isdigit():
            rows.append((int(parts[0]), int(parts[1]), parts[2]))
    return rows


def kill_tree(pids: list[int]) -> None:
    """SIGKILL the processes and all their descendants."""
    rows = process_list()
    doomed, queue = set(pids), list(pids)
    while queue:
        parent = queue.pop()
        for pid, ppid, _ in rows:
            if ppid == parent and pid not in doomed:
                doomed.add(pid)
                queue.append(pid)
    for pid in doomed:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.kill(pid, signal.SIGKILL)


class Profile:
    """A private temporary root that holds everything a run creates."""

    def __init__(self, parent: Path | None = None) -> None:
        # Canonical: the plugin refuses symlinked paths, and macOS temp dirs sit behind /var -> /private/var.
        self.root = Path(os.path.realpath(tempfile.mkdtemp(prefix="spec069-", dir=parent)))
        self.root.chmod(0o700)
        self.groups: list[int] = []

    def make(self, *parts: str) -> Path:
        path = self.root.joinpath(*parts)
        path.mkdir(parents=True, exist_ok=True)
        path.chmod(0o700)
        return path

    def track(self, pgid: int) -> None:
        self.groups.append(pgid)

    def _stragglers(self) -> list[int]:
        marker = str(self.root)
        return [pid for pid, _, cmd in process_list() if marker in cmd and pid != os.getpid()]

    def teardown(self) -> dict[str, Any]:
        for pgid in self.groups:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(pgid, signal.SIGTERM)
        time.sleep(0.2)
        for pgid in self.groups:
            with contextlib.suppress(ProcessLookupError, PermissionError):
                os.killpg(pgid, signal.SIGKILL)
        shutil.rmtree(self.root, ignore_errors=True)
        return self.verify()

    def verify(self) -> dict[str, Any]:
        """Nothing may be left. Anything found is reported, then removed as a last resort."""
        left_processes = self._stragglers()
        left_profile = self.root.exists()
        result = {"profileRemoved": not left_profile, "leftoverProcesses": len(left_processes),
                  "clean": not left_profile and not left_processes}
        kill_tree(left_processes)
        if left_profile:
            for path in [self.root, *self.root.rglob("*")]:
                with contextlib.suppress(OSError):
                    path.chmod(0o700)
            shutil.rmtree(self.root, ignore_errors=True)
        return result


# ----------------------------------------------------------------------------
# Hosts
# ----------------------------------------------------------------------------
@dataclass
class HostConfig:
    name: str
    binary: Path
    key_sources: tuple[str, ...]
    key_target: str
    model: str | None = None
    fake: bool = False


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


def build_host_env(profile: Profile, host: HostConfig, key: str, ab_home: Path, passthrough: dict[str, str]) -> dict[str, str]:
    """A minimal environment: private HOME/XDG, the one credential, no inherited variables."""
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
    env[host.key_target] = key
    env.update(passthrough)
    return env


@dataclass
class ToolCall:
    tool: str
    args: Any
    output: str | None
    is_error: bool


@dataclass
class Transcript:
    tool_calls: list[ToolCall] = field(default_factory=list)
    models: list[str] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    text: str = ""


def _jsonl(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("{"):
            with contextlib.suppress(json.JSONDecodeError):
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
    return rows


def _flatten(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(_flatten(part.get("text", "") if isinstance(part, dict) else part) for part in content)
    return json.dumps(content) if content is not None else ""


def parse_claude(stdout: str) -> Transcript:
    out, pending = Transcript(), {}
    for row in _jsonl(stdout):
        if row.get("type") == "system" and row.get("model"):
            out.models.append(row["model"])
        message = row.get("message") or {}
        if row.get("type") == "assistant":
            if message.get("model"):
                out.models.append(message["model"])
            for block in message.get("content") or []:
                if block.get("type") == "tool_use":
                    call = ToolCall(block.get("name", ""), block.get("input"), None, False)
                    pending[block.get("id")] = call
                    out.tool_calls.append(call)
                elif block.get("type") == "text":
                    out.text += block.get("text", "")
        elif row.get("type") == "user":
            for block in message.get("content") or [] if isinstance(message.get("content"), list) else []:
                call = pending.get(block.get("tool_use_id")) if block.get("type") == "tool_result" else None
                if call:
                    call.output, call.is_error = _flatten(block.get("content")), bool(block.get("is_error"))
        elif row.get("type") == "result":
            out.usage = {k: row[k] for k in ("total_cost_usd", "num_turns", "duration_ms", "usage") if k in row}
    out.models = sorted(set(out.models))
    return out


def parse_opencode(stdout: str) -> Transcript:
    out = Transcript()
    for row in _jsonl(stdout):
        part = row.get("part") or {}
        if part.get("type") == "tool":
            state = part.get("state") or {}
            failed = state.get("status") in ("error", "failed", "denied")
            output = state.get("error") if failed and state.get("error") else state.get("output")
            out.tool_calls.append(ToolCall(part.get("tool", ""), state.get("input"), _flatten(output), failed))
        elif part.get("type") == "text":
            out.text += part.get("text", "")
        elif part.get("type") == "step-finish":
            for key in ("cost", "tokens"):
                if key in part:
                    out.usage[key] = part[key]
    return out


def parse_codex(stdout: str) -> Transcript:
    """Unverified against a live model on this machine (no OpenAI key): shapes follow ``codex exec --json``."""
    out = Transcript()
    for row in _jsonl(stdout):
        item = row.get("item") or {}
        if row.get("type") == "item.completed":
            kind = item.get("type", "")
            if "mcp" in kind or kind == "tool_call":
                result = item.get("result") or {}
                text = _flatten(result.get("content")) if isinstance(result, dict) else _flatten(result)
                failed = item.get("status") in ("failed", "declined") or bool(item.get("error"))
                if failed and not text:
                    text = _flatten(item.get("error"))
                name = f"{item.get('server', '')}__{item.get('tool', '')}"
                out.tool_calls.append(ToolCall(name, item.get("arguments"), text, failed))
            elif kind in ("command_execution", "file_change", "web_search"):
                failed = item.get("status") in ("failed", "declined") or item.get("exit_code") not in (None, 0)
                out.tool_calls.append(ToolCall(kind, item.get("command") or item, _flatten(item.get("aggregated_output")), failed))
            elif kind == "agent_message":
                out.text += item.get("text", "")
        elif row.get("type") == "turn.completed":
            out.usage = row.get("usage") or {}
    return out


PARSERS: dict[str, Callable[[str], Transcript]] = {"claude-code": parse_claude, "opencode": parse_opencode, "codex": parse_codex}


def tool_class(host: str, call: ToolCall) -> str:
    """``agent-braid`` (allowed), ``meta`` (host discovery helper) or ``denied``."""
    name = call.tool
    if host == "claude-code" and name.startswith("mcp__plugin_agent-braid_agent-braid__"):
        return "agent-braid"
    if host == "opencode" and name.startswith("agent-braid_"):
        return "agent-braid"
    if host == "codex" and name.startswith("agent-braid__"):
        return "agent-braid"
    if name in META_TOOLS[host]:
        text = json.dumps(call.args)
        return "denied" if re.search(r"\bfetch\s*\(|XMLHttpRequest|require\(|import\(", text) else "meta"
    return "denied"


def short_name(call: ToolCall) -> str:
    for prefix in ("mcp__plugin_agent-braid_agent-braid__", "agent-braid__", "agent-braid_"):
        if call.tool.startswith(prefix):
            return call.tool[len(prefix):]
    return call.tool


def parse_envelope(call: ToolCall) -> dict[str, Any]:
    text = call.output or ""
    with contextlib.suppress(json.JSONDecodeError, TypeError):
        value = json.loads(text)
        if isinstance(value, dict) and isinstance(value.get("structuredContent"), dict):
            value = value["structuredContent"]
        if isinstance(value, dict) and "status" in value:
            return value
    return {"status": "error" if call.is_error else "unknown", "summary": text[:300]}


def attempts_from(transcript: Transcript, host: str) -> list[dict]:
    """The ordered analyze-work calls; plugin-status and workspaces calls are not attempts."""
    attempts = []
    for call in transcript.tool_calls:
        if tool_class(host, call) != "agent-braid" or short_name(call) != "analyze-work":
            continue
        args = call.args if isinstance(call.args, dict) else {}
        envelope = parse_envelope(call)
        accepted = envelope.get("status") == "ok" and not call.is_error
        result = envelope.get("result") if isinstance(envelope.get("result"), dict) else {}
        attempts.append({"kind": args.get("kind"), "request": args.get("request"), "accepted": accepted,
                         "refusalSummary": None if accepted else str(envelope.get("summary") or call.output or "")[:300],
                         "report": result.get("report") if accepted else None})
    return attempts


# ----------------------------------------------------------------------------
# Running processes
# ----------------------------------------------------------------------------
def run_process(argv: list[str], env: dict[str, str], cwd: Path, profile: Profile, protected: list[Path], sandbox: OsSandbox,
                timeout: int, label: str, wrap: bool = True) -> subprocess.CompletedProcess:
    guard_leaks(label, env, argv, protected)
    full = sandbox.wrap(argv) if wrap else argv
    proc = subprocess.Popen(full, env=env, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, start_new_session=True)
    profile.track(proc.pid)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(proc.pid, signal.SIGKILL)
        stdout, stderr = proc.communicate()
        timed_out = True
    result = subprocess.CompletedProcess(argv, proc.returncode, stdout or "", stderr or "")
    result.timed_out = timed_out  # type: ignore[attr-defined]
    return result


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
    """OpenCode permissions: deny every built-in tool. (Claude and Codex take their policy as flags.)"""
    if host.name != "opencode":
        return
    path = Path(env["XDG_CONFIG_HOME"]) / "opencode" / "opencode.json"
    config = json.loads(path.read_text()) if path.exists() else {}
    config["permission"] = {name: "deny" for name in OPENCODE_DENIED}
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
FAKE_VARIANTS = ("default", "retry", "denied-tool", "executed-tool", "leak-secret", "straggler")


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


def run_host(host: HostConfig, args: argparse.Namespace, prompt_set: dict, ctx: dict, profile: Profile, secrets: Secrets,
             out_dir: Path, scoring: Any, fixture: Any) -> dict[str, Any]:
    """One host end to end. Raises DeclaredLimit for a host that cannot run, SafetyStop for a safety failure."""
    key = next((os.environ[name] for name in KEY_SPECS[host.name][0] if os.environ.get(name)), None)
    if args.fake_hosts:
        key = key or "fake-key-not-a-secret"
    if not key:
        raise DeclaredLimit(f"no {' or '.join(KEY_SPECS[host.name][0])} in the driver environment (D13: the key is read from the environment only)")
    if host.name == "opencode" and not host.model and not args.fake_hosts:
        raise DeclaredLimit("OpenCode needs --model opencode=anthropic/<id>: without it the host uses a free hosted model")
    secrets.add(key)
    ab_home = profile.make("hosts", host.name, "agent-braid-home")
    passthrough = dict(ctx["passthrough"])
    env = build_host_env(profile, host, key, ab_home, passthrough)
    protected, sandbox = ctx["protected"], ctx["sandbox"]
    workspace = fixture.build(profile.make("hosts", host.name, "workspace") / "repo")
    guard_leaks(f"{host.name} setup", env, [str(host.binary)], protected)
    if not sandbox.tool and not args.no_os_sandbox and not args.fake_hosts:
        raise DeclaredLimit("no OS sandbox available on this platform; refusing an unsandboxed real run (use --no-os-sandbox only for an engineering probe)")
    probe = probe_isolation(env, Path(env["HOME"]), sandbox, protected)
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
            transcript = PARSERS[host.name](done.stdout)
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
                      "attempts": secrets.redact_json(attempts), "score": scoring.score_case(case, attempts)}
            runs.append(record)
            if any(item["outcome"] == "executed" for item in denied):
                violations.append(f"{case['id']} r{repetition}: a denied tool ran: {denied}")
                break
        if violations:
            break
    if violations:
        raise SafetyStop(f"{host.name}: " + "; ".join(violations))
    return {"status": "ran", "version": version, "auth": "env-key", "modelPinned": bool(host.model), "model": host.model,
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
    {"step": "Export the API keys in your own terminal before the run", "reason": "keys are read from the driver environment only and are never prompted for, written or logged (D13)"},
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
    p.add_argument("--fake-hosts", action="store_true", help="run the same pipeline against the fake hosts (pipeline-only evidence)")
    p.add_argument("--fake-variant", choices=FAKE_VARIANTS, default="default")
    p.add_argument("--extra-env", action="append", default=[], metavar="KEY=VALUE",
                   help="add a variable to the host environment; a value naming a real configuration path stops the run")
    p.add_argument("--real-home", type=Path, default=None, help="protected home (default: the account home)")
    p.add_argument("--no-os-sandbox", action="store_true", help="engineering probe only; never for measured evidence")
    args = p.parse_args(argv)
    args.plugin_root_for = {}
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    from scripts import spec069_fixture_workspace as fixture
    from scripts import spec069_scoring as scoring

    prompt_set, prompt_path = load_prompt_set(args.prompt_set)
    if args.limit_cases:
        prompt_set = {**prompt_set, "cases": prompt_set["cases"][: args.limit_cases]}
    models = dict(item.split("=", 1) for item in args.model)
    secrets = Secrets()
    passthrough = dict(item.split("=", 1) for item in args.extra_env)
    for name in ("ANTHROPIC_BASE_URL",):
        if os.environ.get(name) and not args.fake_hosts:
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
                                "repetitions": args.repetitions, "hosts": {}, "manualSteps": MANUAL_STEPS,
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
        ctx = {"plugin_dir": plugin_dir, "protected": protected, "sandbox": sandbox, "passthrough": passthrough}
        if args.fake_hosts:
            scenario = build_fake_scenario(prompt_set["cases"], args.fake_variant, scoring.reference_request)
            scenario_file = profile.make("fake") / "scenario.json"
            scenario_file.write_text(json.dumps(scenario))
            planted = "sk-ant-PLANTED-" + sha256_bytes(b"planted")[:24]
            secrets.add(planted)
            passthrough.update({"FAKE_SCENARIO": str(scenario_file), "FAKE_VARIANT": args.fake_variant, "FAKE_PLANTED_SECRET": planted,
                                "FAKE_PYTHON": sys.executable})
            os.environ.setdefault("ANTHROPIC_API_KEY", "fake-anthropic-key-0001")
        for name in [h for h in args.hosts.split(",") if h]:
            binary = host_binary(name, args)
            if binary is None:
                evidence["hosts"][name] = {"status": "declared-limit", "limit": f"{name} executable not found"}
                continue
            host = HostConfig(name, binary, *KEY_SPECS[name], model=models.get(name), fake=args.fake_hosts)
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
