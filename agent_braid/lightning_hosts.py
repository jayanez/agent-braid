# SPDX-License-Identifier: AGPL-3.0-only
"""Host plumbing shared by the SPEC-069 native-run driver and the Braid Lightning runner (SPEC-071 REQ-002).

Extracted unchanged from ``scripts/spec069_native_runs.py``: secrets redaction and scan, the real-path leak
guard, the macOS OS sandbox and isolation probe, disposable profiles with teardown, process-tree kill, the
headless transcript parsers and the analyze-work attempt extraction. The only additions are a configurable
profile prefix and the host-reported credential source (``Transcript.key_source``), which the driver ignores.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
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

SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
# ToolSearch and Skill are host-side helpers: tool discovery, and the plugin's packaged guidance (the thing under measurement).
CLAUDE_ALLOWED = ["mcp__plugin_agent-braid_agent-braid__*", "ToolSearch", "Skill"]
# Built-in tools the host may offer: schema discovery and the plugin's packaged skills only. Anything else
# (for example ListAgents, SendMessage, TaskStop) is not available at all, rather than denied one by one.
CLAUDE_BUILTIN = ["ToolSearch", "Skill"]
CLAUDE_DENIED = ["Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Read", "Glob", "Grep", "Task", "Agent"]
OPENCODE_DENIED = ["bash", "edit", "write", "webfetch", "websearch", "read", "glob", "grep", "list", "task", "external_directory"]
# Host-side discovery helpers the host itself needs before it can see MCP tools (observed, see the runbook).
META_TOOLS = {"claude-code": {"ToolSearch", "Skill"}, "codex": set(), "opencode": {"execute", "skill"}}


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

    def __init__(self, parent: Path | None = None, prefix: str = "spec069-") -> None:
        # Canonical: the plugin refuses symlinked paths, and macOS temp dirs sit behind /var -> /private/var.
        self.root = Path(os.path.realpath(tempfile.mkdtemp(prefix=prefix, dir=parent)))
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


@dataclass
class HostConfig:
    name: str
    binary: Path
    key_sources: tuple[str, ...]
    key_target: str
    model: str | None = None
    fake: bool = False


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
    key_source: str | None = None  # host-reported credential source (Claude Code ``apiKeySource``); None when absent


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
        if row.get("type") == "system" and isinstance(row.get("apiKeySource"), str):
            out.key_source = row["apiKeySource"]
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
