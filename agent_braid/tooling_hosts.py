# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare and dispatch one-shot host sessions through the process supervisor.

This adapter has no authority to authenticate, grant tools, or approve a run.
It is usable only inside the existing admitted-session coordinator and relies
on injected caller attestations for route, opt-in, isolation, and native skill
loading. Parser observations remain untrusted until an outcome verifier checks
actual source evidence.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import math
import tomllib
from types import MappingProxyType
from typing import Any, Callable, Mapping, Protocol

from . import tooling_capture as capture
from . import tooling_evaluation as evaluation
from . import tooling_host_events
from . import tooling_sessions

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SUPPORTED_HOSTS = {"codex", "claude-code"}
_SUPPORTED_ARMS = {"mcp-only", "mcp-plus-skills"}
_SKILLS = (
    "agent-braid-analyze", "agent-braid-plan", "agent-braid-execute",
    "agent-braid-recover", "agent-braid-evidence",
)


class HostPreparationError(ValueError):
    """A host session cannot be safely prepared or dispatched."""


@dataclass(frozen=True)
class FilePin:
    path: Path
    sha256: str


@dataclass(frozen=True)
class LaunchEvidence:
    """Opaque references that an external trusted verifier must authenticate."""

    route_id: str
    route_attestation_sha256: str
    provider_opt_in_sha256: str
    isolation_attestation_sha256: str
    native_skills_attestation_sha256: str | None = None
    settings_support_attestation_sha256: str | None = None


@dataclass(frozen=True)
class HostLaunchConfig:
    """Caller-selected frozen inputs; no field grants permission to execute."""

    host: str
    arm: str
    executable: Path
    executable_sha256: str
    version: str
    model: str
    effort: str
    config_files: tuple[FilePin, ...]
    codex_config_overrides: tuple[str, ...] = field(repr=False)
    config_dir: Path
    cwd: Path
    mcp_result_root: Path
    output_root: Path
    source_roots: tuple[Path, ...]
    grant_root: Path
    prompt: bytes = field(repr=False)
    environment: Mapping[str, str] = field(repr=False)
    mcp_servers: tuple[str, ...]
    expected_tools: tuple[str, ...]
    runtime_enabled: bool
    expected_skill_bundle_sha256: str | None = None
    evidence: LaunchEvidence | None = None
    timeout_seconds: float = 57_600
    max_output_bytes: int = 8 * 1024 * 1024
    observation_max_age_seconds: float = 30
    poll_interval_seconds: float = 1
    term_grace_seconds: float = 5
    kill_grace_seconds: float = 5


@dataclass(frozen=True)
class HostLaunchPlan:
    """Immutable prepared request; prompt/environment are never serialized."""

    host: str
    arm: str
    attempt_id: str
    slot_id: str
    admission_receipt_sha256: str
    admission_subject_sha256: str
    executable: Path
    executable_sha256: str
    version: str
    model: str
    effort: str
    config_files: tuple[FilePin, ...]
    codex_config_overrides: tuple[str, ...] = field(repr=False)
    config_dir: Path
    cwd: Path
    mcp_result_root: Path
    output_root: Path
    source_roots: tuple[Path, ...]
    grant_root: Path
    argv: tuple[str, ...] = field(repr=False)
    codex_config_sha256: str | None
    prompt_sha256: str
    prompt: bytes = field(repr=False)
    environment: Mapping[str, str] = field(repr=False)
    mcp_servers: tuple[str, ...]
    expected_tools: tuple[str, ...]
    runtime_enabled: bool
    evidence: LaunchEvidence
    timeout_seconds: float
    max_output_bytes: int
    observation_max_age_seconds: float
    poll_interval_seconds: float
    term_grace_seconds: float
    kill_grace_seconds: float


class PreparationVerifier(Protocol):
    """Trusted caller check for admission, route, opt-in, and host evidence."""

    def verify_pre_dispatch(self, *, admission: capture.AttemptAdmission,
                            plan: HostLaunchPlan) -> None: ...


class HostSessionAdapter(tooling_sessions.SessionAdapter):
    """Single-dispatch adapter composed with `tooling_supervisor`.

    The `tooling_sessions.execute_admitted_attempt` coordinator must own the
    call. A started/ambiguous process is not retried. The supervisor is injected
    for tests and deployments; the default is the production bounded supervisor.
    """

    def __init__(self, plan: HostLaunchPlan, *, verifier: PreparationVerifier,
                 observer: Callable[..., Any], caps: Any,
                 supervisor: Callable[..., Any] | None = None,
                 outcome_reader: Callable[[Any], bytes] | None = None):
        if verifier is None or not callable(getattr(verifier, "verify_pre_dispatch", None)):
            raise HostPreparationError("trusted route and isolation verifier is required")
        if not callable(observer) or caps is None:
            raise HostPreparationError("fresh observation callback and explicit budget caps are required")
        self._plan = plan
        self._verifier = verifier
        self._observer = observer
        self._caps = caps
        self._supervisor = supervisor
        self._outcome_reader = outcome_reader
        self._used = False

    def execute(self, admission: capture.AttemptAdmission) -> Mapping[str, Any]:
        if self._used:
            raise HostPreparationError("host adapter is one-shot; do not retry")
        self._used = True
        plan = self._plan
        if not isinstance(admission, capture.AttemptAdmission):
            raise HostPreparationError("a capture admission is required")
        if admission.attempt_id != plan.attempt_id or admission.slot_id != plan.slot_id \
                or admission.receipt_sha256 != plan.admission_receipt_sha256 \
                or admission.subject_sha256 != plan.admission_subject_sha256:
            raise HostPreparationError("launch plan is not bound to this admission")
        self._verify_pins(plan)
        self._verifier.verify_pre_dispatch(admission=admission, plan=plan)
        if self._supervisor is None:
            from .tooling_supervisor import run_supervised
            runner = run_supervised
        else:
            runner = self._supervisor
        request = self._make_process_request(plan)
        outcome = runner(request, self._caps, self._observer)
        return self._public_outcome(plan, outcome)

    @staticmethod
    def _make_process_request(plan: HostLaunchPlan) -> Any:
        try:
            from .tooling_supervisor import FilePin as SupervisorFilePin, ProcessRequest
        except ImportError as exc:
            raise HostPreparationError("bounded process supervisor is unavailable") from exc
        return ProcessRequest(
            executable=plan.executable,
            executable_sha256=plan.executable_sha256,
            argv=plan.argv,
            cwd=plan.cwd,
            output_root=plan.output_root,
            source_roots=plan.source_roots,
            grant_root=plan.grant_root,
            file_pins=tuple(SupervisorFilePin(pin.path, pin.sha256) for pin in plan.config_files),
            env=dict(plan.environment),
            stdin=plan.prompt,
            max_output_bytes=plan.max_output_bytes,
            timeout_seconds=plan.timeout_seconds,
            observation_max_age_seconds=plan.observation_max_age_seconds,
            poll_interval_seconds=plan.poll_interval_seconds,
            term_grace_seconds=plan.term_grace_seconds,
            kill_grace_seconds=plan.kill_grace_seconds,
        )

    def _public_outcome(self, plan: HostLaunchPlan, outcome: Any) -> Mapping[str, Any]:
        """Return bounded metadata; never claim authenticity or invoice totals."""
        status = getattr(outcome, "status", None)
        if not isinstance(status, str):
            raise HostPreparationError("supervisor returned an untyped outcome")
        observation: Mapping[str, Any] | None = None
        returncode = getattr(outcome, "returncode", None)
        process_complete = (status == "completed" and type(returncode) is int
                            and returncode == 0 and getattr(outcome, "group_cleanup", None) == "clean"
                            and getattr(outcome, "launched", False))
        if process_complete:
            if self._outcome_reader is not None:
                raw = self._outcome_reader(outcome)
            else:
                try:
                    output_path = Path(outcome.stdout_path)
                    if output_path.stat().st_size > tooling_host_events.MAX_STREAM_BYTES:
                        raise HostPreparationError("host JSONL exceeds the parser byte bound")
                    with output_path.open("rb") as stream:
                        raw = stream.read(tooling_host_events.MAX_STREAM_BYTES + 1)
                except (AttributeError, OSError, TypeError) as exc:
                    raise HostPreparationError("supervisor stdout evidence is unavailable") from exc
            if not isinstance(raw, bytes):
                raise HostPreparationError("supervisor output reader must return bytes")
            if len(raw) > tooling_host_events.MAX_STREAM_BYTES:
                raise HostPreparationError("host JSONL exceeds the parser byte bound")
            parsed = tooling_host_events.parse_host_events(
                "codex" if plan.host == "codex" else "claude", raw,
                version=plan.version, expected_model=plan.model,
                expected_mcp_servers=plan.mcp_servers,
                exit_code=returncode,
            )
            observation = {
                "state": parsed.state,
                "initialized": parsed.initialized,
                "observedTools": list(parsed.observed_tools),
                "model": parsed.model,
                "inputTokens": parsed.input_tokens,
                "cachedInputTokens": parsed.cached_input_tokens,
                "outputTokens": parsed.output_tokens,
                "reasoningTokens": parsed.reasoning_tokens,
                "estimatedCostUsd": parsed.estimated_cost_usd,
                "costBasis": parsed.cost_basis,
                "error": parsed.error,
                "limits": list(parsed.limits),
            }
        else:
            observation = {
                "state": "unknown",
                "initialized": None,
                "limits": ["JSONL not parsed as a completed, clean supervisor outcome."],
            }
        return {
            "schemaVersion": "agent-braid-host-adapter-outcome-v1",
            "attemptId": plan.attempt_id,
            "slotId": plan.slot_id,
            "admissionReceiptSha256": plan.admission_receipt_sha256,
            "admissionSubjectSha256": plan.admission_subject_sha256,
            "host": plan.host,
            "arm": plan.arm,
            "routeId": plan.evidence.route_id,
            "executableSha256": plan.executable_sha256,
            "version": plan.version,
            "model": plan.model,
            "effort": plan.effort,
            "runtimeEnabled": plan.runtime_enabled,
            "mcpResultRoot": str(plan.mcp_result_root),
            "promptSha256": plan.prompt_sha256,
            "configFiles": [{"path": str(pin.path), "sha256": pin.sha256}
                            for pin in plan.config_files],
            "codexConfigOverridesSha256": plan.codex_config_sha256,
            "status": status,
            "launched": getattr(outcome, "launched", None),
            "returncode": getattr(outcome, "returncode", None),
            "signal": getattr(outcome, "signal", None),
            "startedAt": getattr(outcome, "started_at", None),
            "endedAt": getattr(outcome, "ended_at", None),
            "wallSeconds": getattr(outcome, "wall_elapsed_seconds", None),
            "stdoutBytes": getattr(outcome, "stdout_bytes", None),
            "stderrBytes": getattr(outcome, "stderr_bytes", None),
            "stdoutSha256": getattr(outcome, "stdout_sha256", None),
            "stderrSha256": getattr(outcome, "stderr_sha256", None),
            "stdoutPath": str(getattr(outcome, "stdout_path", "")) or None,
            "stderrPath": str(getattr(outcome, "stderr_path", "")) or None,
            "supervisorReceiptPath": str(getattr(outcome, "receipt_path", "")) or None,
            "supervisorReceiptSha256": getattr(outcome, "receipt_sha256", None),
            "groupCleanup": getattr(outcome, "group_cleanup", None),
            "reason": getattr(outcome, "reason", None),
            "telemetry": _telemetry_summary((getattr(outcome, "last_snapshot", None),)),
            "limits": list(getattr(outcome, "limits", ())),
            "observation": observation,
            "adapterLimits": [
                "Supervisor and parser results are observations; trusted outcome verification is still required.",
                "Reported host cost is an estimate when supplied, never an invoice.",
            ],
        }

    @staticmethod
    def _verify_pins(plan: HostLaunchPlan) -> None:
        _check_file_pin(FilePin(plan.executable, plan.executable_sha256), executable=True)
        for pin in plan.config_files:
            _check_file_pin(pin)


def prepare_host_launch(admission: capture.AttemptAdmission,
                        config: HostLaunchConfig) -> HostLaunchPlan:
    """Validate frozen inputs and prepare (but never dispatch) a host command."""
    if not isinstance(admission, capture.AttemptAdmission):
        raise HostPreparationError("a genuine capture admission is required")
    if not isinstance(config, HostLaunchConfig):
        raise HostPreparationError("typed host configuration is required")
    if config.host not in _SUPPORTED_HOSTS:
        raise HostPreparationError("unknown host route")
    if config.arm not in _SUPPORTED_ARMS:
        raise HostPreparationError("human CLI baseline is not launched by this adapter")
    if not isinstance(config.model, str) or not config.model.strip() \
            or not isinstance(config.effort, str) or not config.effort.strip():
        raise HostPreparationError("an explicit model and effort are required")
    if config.evidence is None or not config.evidence.route_id.strip():
        raise HostPreparationError("an authenticated explicit route is required")
    for digest in (config.executable_sha256, config.evidence.route_attestation_sha256,
                   config.evidence.provider_opt_in_sha256,
                   config.evidence.isolation_attestation_sha256):
        _require_digest(digest)
    if config.arm == "mcp-plus-skills":
        if not config.expected_skill_bundle_sha256 or not config.evidence.native_skills_attestation_sha256:
            raise HostPreparationError("native canonical skill-load evidence is required for arm C")
        _require_digest(config.expected_skill_bundle_sha256)
        _require_digest(config.evidence.native_skills_attestation_sha256)
    if config.evidence.settings_support_attestation_sha256 is not None:
        _require_digest(config.evidence.settings_support_attestation_sha256)
    else:
        raise HostPreparationError("effective host settings support must be verified before dispatch")
    if config.host == "claude-code" and _version_tuple(config.version, claude_stable=True) < (2, 1, 286):
        raise HostPreparationError("Claude Code before 2.1.286 is refused for isolated comparisons")
    if config.host == "codex" and _version_tuple(config.version) < (0, 162, 0):
        raise HostPreparationError("Codex CLI version predates the observed JSONL baseline")
    if config.host == "claude-code" and config.arm == "mcp-plus-skills" \
            and tuple(config.expected_tools) != tuple(f"Skill({name})" for name in _SKILLS):
        raise HostPreparationError("Claude arm C must request the exact five canonical native skills")
    if config.host == "claude-code" and config.arm == "mcp-only" and config.expected_tools:
        raise HostPreparationError("Claude arm B must remove built-in tools and skills")
    if config.host == "claude-code" and config.environment.get("CLAUDE_CONFIG_DIR") != str(config.config_dir):
        raise HostPreparationError("Claude requires an explicit isolated CLAUDE_CONFIG_DIR")
    if not isinstance(config.mcp_servers, tuple) or any(
            not isinstance(name, str) or not name for name in config.mcp_servers) \
            or len(set(config.mcp_servers)) != len(config.mcp_servers):
        raise HostPreparationError("MCP server set must contain unique non-empty names")
    if not isinstance(config.expected_tools, tuple) or any(
            not isinstance(name, str) or not name for name in config.expected_tools) \
            or len(set(config.expected_tools)) != len(config.expected_tools):
        raise HostPreparationError("expected tool set must contain unique non-empty names")
    _check_private_result_root(config.mcp_result_root)
    if config.host == "codex":
        if not config.codex_config_overrides:
            raise HostPreparationError("Codex requires explicit caller-supplied MCP and tool configuration")
        for override in config.codex_config_overrides:
            if not isinstance(override, str) or "=" not in override:
                raise HostPreparationError("Codex overrides must be explicit TOML assignments")
            try:
                parsed = tomllib.loads(override)
            except (tomllib.TOMLDecodeError, ValueError) as exc:
                raise HostPreparationError("Codex override is not valid TOML") from exc
            if set(parsed) - {"mcp_servers", "skills"}:
                raise HostPreparationError("Codex overrides may contain only MCP and native-skill configuration")
            _reject_credential_config(parsed)
        _validate_codex_configuration(config)
    if config.host == "claude-code":
        if not config.config_files:
            raise HostPreparationError("Claude requires an exact pinned MCP config file")
        _validate_claude_configuration(config)
    if not isinstance(config.prompt, bytes):
        raise HostPreparationError("prompt must be exact UTF-8 bytes")
    try:
        config.prompt.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HostPreparationError("prompt must be UTF-8") from exc
    if not isinstance(config.environment, Mapping):
        raise HostPreparationError("explicit child environment must be a mapping")
    if any(key in {"HOME", "CODEX_HOME"} for key in config.environment):
        raise HostPreparationError("HOME and CODEX_HOME cannot be reassigned")
    if any(not isinstance(k, str) or not isinstance(v, str) for k, v in config.environment.items()):
        raise HostPreparationError("explicit child environment must map strings to strings")
    for name, value in (("timeout_seconds", config.timeout_seconds),
                        ("max_output_bytes", config.max_output_bytes),
                        ("observation_max_age_seconds", config.observation_max_age_seconds),
                        ("poll_interval_seconds", config.poll_interval_seconds),
                        ("term_grace_seconds", config.term_grace_seconds),
                        ("kill_grace_seconds", config.kill_grace_seconds)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value <= 0:
            raise HostPreparationError(f"{name} must be a finite positive number")
    _check_file_pin(FilePin(config.executable, config.executable_sha256), executable=True)
    for pin in config.config_files:
        _check_file_pin(pin)
    argv = _build_argv(config)
    return HostLaunchPlan(
        host=config.host, arm=config.arm, attempt_id=admission.attempt_id,
        slot_id=admission.slot_id, admission_receipt_sha256=admission.receipt_sha256,
        admission_subject_sha256=admission.subject_sha256,
        executable=config.executable.resolve(strict=True),
        executable_sha256=config.executable_sha256, version=config.version,
        model=config.model, effort=config.effort,
        config_files=tuple(FilePin(pin.path.resolve(strict=True), pin.sha256) for pin in config.config_files),
        codex_config_overrides=config.codex_config_overrides,
        config_dir=config.config_dir, cwd=config.cwd, output_root=config.output_root,
        mcp_result_root=config.mcp_result_root,
        source_roots=config.source_roots, grant_root=config.grant_root,
        argv=argv,
        codex_config_sha256=(hashlib.sha256("\0".join(config.codex_config_overrides).encode("utf-8")).hexdigest()
                             if config.host == "codex" else None),
        prompt_sha256=hashlib.sha256(config.prompt).hexdigest(), prompt=config.prompt,
        environment=MappingProxyType(dict(config.environment)), mcp_servers=tuple(config.mcp_servers),
        expected_tools=config.expected_tools, evidence=config.evidence,
        runtime_enabled=config.runtime_enabled,
        timeout_seconds=config.timeout_seconds, max_output_bytes=config.max_output_bytes,
        observation_max_age_seconds=config.observation_max_age_seconds,
        poll_interval_seconds=config.poll_interval_seconds,
        term_grace_seconds=config.term_grace_seconds,
        kill_grace_seconds=config.kill_grace_seconds,
    )


def _build_argv(config: HostLaunchConfig) -> tuple[str, ...]:
    if config.host == "codex":
        argv = ["exec", "--json", "--ephemeral", "--ignore-user-config",
                "--sandbox", "read-only", "--model", config.model,
                "--cd", str(config.cwd)]
        argv.extend(("--config", "model_reasoning_effort='" + config.effort + "'"))
        for override in config.codex_config_overrides:
            argv.extend(("--config", override))
        # CLI settings remain unverified until a real host receipt establishes
        # acceptance and semantics. In particular, do not claim plugins=false
        # disables explicit MCP or that global skill loading is isolated.
        for key in ("features.shell_tool", "features.code_mode_host", "features.code_mode",
                    "features.multi_agent", "features.hooks", "features.apps", "features.plugins"):
            argv.extend(("--config", key + "=false"))
        argv.extend(("--config", "web_search=\"disabled\""))
        return tuple(argv)
    if config.host == "claude-code":
        argv = ["--bare", "--strict-mcp-config", "--no-session-persistence",
                "--print", "--verbose", "--output-format", "stream-json",
                "--model", config.model, "--effort", config.effort,
                "--mcp-config", str(config.config_files[0].path)]
        if config.arm == "mcp-only":
            argv.extend(("--tools", "", "--disable-slash-commands"))
        else:
            argv.extend(("--tools", ",".join(config.expected_tools)))
        argv.extend(("--permission-mode", "dontAsk"))
        return tuple(argv)
    raise HostPreparationError("unknown host route")


def _validate_codex_configuration(config: HostLaunchConfig) -> None:
    servers: dict[str, Any] = {}
    skills_config: Any = None
    for override in config.codex_config_overrides:
        try:
            parsed = tomllib.loads(override)
        except (tomllib.TOMLDecodeError, ValueError) as exc:
            raise HostPreparationError("Codex override is not valid TOML") from exc
        mcp = parsed.get("mcp_servers", {})
        if mcp and not isinstance(mcp, dict):
            raise HostPreparationError("Codex mcp_servers must be a table")
        servers.update(mcp)
        if "skills" in parsed and isinstance(parsed["skills"], dict) and "config" in parsed["skills"]:
            skills_config = parsed["skills"]["config"]
    if tuple(sorted(servers)) != tuple(sorted(config.mcp_servers)):
        raise HostPreparationError("Codex override server inventory differs from the registered MCP set")
    observed_tools: list[str] = []
    for name, server in servers.items():
        if not isinstance(server, dict) or set(server) - {"command", "args", "enabled_tools", "enabled"} \
                or not isinstance(server.get("command"), str):
            raise HostPreparationError(f"Codex MCP server {name} needs an explicit command")
        _validate_agent_braid_server(server.get("command"), server.get("args", []), config)
        tools = server.get("enabled_tools")
        if not isinstance(tools, list) or any(not isinstance(tool, str) for tool in tools):
            raise HostPreparationError(f"Codex MCP server {name} needs an explicit enabled_tools list")
        observed_tools.extend(tools)
    if tuple(sorted(observed_tools)) != tuple(sorted(config.expected_tools)):
        raise HostPreparationError("Codex enabled_tools differs from the exact expected MCP toolset")
    if config.arm == "mcp-only" and skills_config != []:
        raise HostPreparationError("Codex arm B requires explicit disabled native skills config")
    if config.arm == "mcp-plus-skills":
        if not isinstance(skills_config, list) or len(skills_config) != len(_SKILLS):
            raise HostPreparationError("Codex arm C requires exactly the five enabled native skills")
        by_name = {entry.get("name"): entry for entry in skills_config if isinstance(entry, dict)}
        if set(by_name) != set(_SKILLS):
            raise HostPreparationError("Codex arm C native skill names differ from the canonical bundle")
        for name, entry in by_name.items():
            path = entry.get("path")
            if entry.get("enabled") is not True or not isinstance(path, str):
                raise HostPreparationError("Codex arm C skills must be enabled with explicit pinned paths")
            skill_dir = Path(path)
            if not skill_dir.is_absolute():
                raise HostPreparationError("Codex arm C skill paths must be absolute")
            skill_file = skill_dir.resolve(strict=False) / "SKILL.md"
            if not any(pin.path.resolve(strict=False) == skill_file for pin in config.config_files):
                raise HostPreparationError(f"Codex skill file is not content-pinned: {name}")


def _reject_credential_config(value: Any) -> None:
    """Refuse inline credential channels before any command reaches argv."""
    sensitive = re.compile(r"(?i)(?:api[_-]?key|access[_-]?key|secret|password|token|credential|authorization|headers|^env$)")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or sensitive.search(key):
                raise HostPreparationError("Codex inline config cannot carry environment or credential fields")
            if key == "args":
                _reject_credential_arguments(child)
                continue
            _reject_credential_config(child)
    elif isinstance(value, list):
        for child in value:
            _reject_credential_config(child)
    elif isinstance(value, str) and re.search(
            r"(?i)(bearer\s+|sk-[A-Za-z0-9]{8,}|AKIA[0-9A-Z]{16}|secret[_ -]|token[_ -]|password[_ -])", value):
        raise HostPreparationError("Codex inline config appears to contain a credential value")


def _reject_credential_arguments(value: Any) -> None:
    if not isinstance(value, list) or any(not isinstance(arg, str) for arg in value):
        raise HostPreparationError("Codex MCP args must be an explicit list of strings")
    credential_flag = re.compile(r"(?i)^--?(?:api[-_]?key|access[-_]?key|secret|password|token|credential|authorization|header)(?:=|$)")
    if value:
        for index, arg in enumerate(value):
            if credential_flag.search(arg) or arg in {"-H", "--header"}:
                raise HostPreparationError("Codex MCP args cannot pass credentials or authorization headers")
        if index and credential_flag.fullmatch(value[index - 1]):
            raise HostPreparationError("Codex MCP args cannot pass credential values")
        if re.search(r"(?i)(?:api[-_]?key|access[-_]?key|secret|password|token|credential|authorization)=", arg):
            raise HostPreparationError("Codex MCP args cannot pass inline credential values")


def _validate_claude_configuration(config: HostLaunchConfig) -> None:
    pin = config.config_files[0]
    try:
        raw = pin.path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != pin.sha256:
            raise HostPreparationError("Claude MCP configuration changed after its pin was checked")
        data = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HostPreparationError("Claude MCP config is not readable strict JSON") from exc
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers"), dict):
        raise HostPreparationError("Claude MCP config must contain an mcpServers object")
    if tuple(sorted(data["mcpServers"])) != tuple(sorted(config.mcp_servers)):
        raise HostPreparationError("Claude MCP config inventory differs from the expected server set")
    for server in data["mcpServers"].values():
        if not isinstance(server, dict) or set(server) - {"command", "args", "env"}:
            raise HostPreparationError("Claude MCP servers must use the reviewed stdio command schema")
        if server.get("env"):
            raise HostPreparationError("Claude MCP server environment values are not accepted in this profile")
        _validate_agent_braid_server(server.get("command"), server.get("args", []), config)


def _validate_agent_braid_server(command: Any, args: Any, config: HostLaunchConfig) -> None:
    if not isinstance(command, str) or not Path(command).is_absolute():
        raise HostPreparationError("MCP command must be an absolute pinned Agent Braid console executable")
    canonical = Path(command).resolve(strict=True)
    if not canonical.is_file() or not os.access(canonical, os.X_OK):
        raise HostPreparationError("MCP command executable is unavailable")
    if not any(pin.path.resolve(strict=False) == canonical for pin in config.config_files):
        raise HostPreparationError("MCP command executable lacks a content pin")
    if not isinstance(args, list) or any(not isinstance(arg, str) for arg in args):
        raise HostPreparationError("MCP command arguments must be a string list")
    if len(args) < 7 or args[:4] != ["-m", "agent_braid", "tooling", "serve"]:
        raise HostPreparationError("MCP command must use the registered Agent Braid tooling serve entry point")
    source: str | None = None
    result: str | None = None
    grant: str | None = None
    worktrees: list[str] = []
    runtime = False
    index = 4
    while index < len(args):
        flag = args[index]
        if flag == "--enable-runtime":
            if runtime:
                raise HostPreparationError("duplicate runtime flag")
            runtime = True
            index += 1
            continue
        if flag not in {"--source-root", "--result-root", "--grant-store", "--worktree-root"} \
                or index + 1 >= len(args):
            raise HostPreparationError("MCP command contains an unsupported or incomplete argument")
        value = args[index + 1]
        if not Path(value).is_absolute():
            raise HostPreparationError("MCP root arguments must be absolute paths")
        if flag == "--source-root":
            if source is not None:
                raise HostPreparationError("duplicate source-root argument")
            source = value
        elif flag == "--result-root":
            if result is not None:
                raise HostPreparationError("duplicate result-root argument")
            result = value
        elif flag == "--grant-store":
            if grant is not None:
                raise HostPreparationError("duplicate grant-store argument")
            grant = value
        else:
            worktrees.append(value)
        index += 2
    source_path = Path(source).resolve(strict=True) if source else None
    result_path = Path(result).resolve(strict=True) if result else None
    grant_path = Path(grant).resolve(strict=False) if grant else None
    allowed_sources = {path.resolve(strict=True) for path in config.source_roots}
    expected_worktrees = {str(path.resolve(strict=True)) for path in config.source_roots}
    if source_path not in allowed_sources:
        raise HostPreparationError("MCP source root is outside the frozen source roots")
    if result_path is None or result_path != config.mcp_result_root.resolve(strict=True):
        raise HostPreparationError("MCP result root differs from the explicit isolated result root")
    if result_path in allowed_sources or result_path in {
            config.cwd.resolve(strict=True), config.output_root.resolve(strict=True),
            config.grant_root.resolve(strict=False)}:
        raise HostPreparationError("MCP result root overlaps a protected session root")
    if any(value not in expected_worktrees for value in worktrees) or len(set(worktrees)) != len(worktrees):
        raise HostPreparationError("MCP worktree roots differ from the frozen source roots")
    if runtime != config.runtime_enabled or (runtime and grant_path != config.grant_root.resolve(strict=False)):
        raise HostPreparationError("MCP runtime/grant arguments differ from the explicit admitted profile")
    if not runtime and grant is not None:
        raise HostPreparationError("grant-store cannot be configured while MCP runtime is disabled")
    if runtime and (grant_path is None or not grant_path.is_dir() or grant_path.is_symlink()):
        raise HostPreparationError("runtime grant store must be an existing explicit directory")


def _check_private_result_root(path: Path) -> None:
    try:
        resolved = path.resolve(strict=True)
        info = resolved.stat()
    except (OSError, TypeError) as exc:
        raise HostPreparationError("MCP result root must be an existing private directory") from exc
    if not resolved.is_dir() or info.st_uid != os.getuid() or info.st_mode & 0o077:
        raise HostPreparationError("MCP result root must be user-owned and private")


def _check_file_pin(pin: FilePin, *, executable: bool = False) -> None:
    if not isinstance(pin, FilePin) or not _SHA256.fullmatch(pin.sha256):
        raise HostPreparationError("invalid file identity pin")
    try:
        if not pin.path.is_absolute():
            raise HostPreparationError("pinned paths must be absolute")
        if pin.path.is_symlink():
            raise HostPreparationError("pinned files must not be symbolic links")
        path = pin.path.resolve(strict=True)
        if not path.is_file() or (executable and not os.access(path, os.X_OK)):
            raise HostPreparationError("pinned file is missing or not executable")
        sha = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                sha.update(chunk)
        digest = sha.hexdigest()
    except OSError as exc:
        raise HostPreparationError("pinned file cannot be inspected") from exc
    if digest != pin.sha256:
        raise HostPreparationError("pinned file content changed")


def _require_digest(value: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise HostPreparationError("a lowercase SHA-256 attestation is required")


def _version_tuple(version: str, *, claude_stable: bool = False) -> tuple[int, ...]:
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:([-+])[\w.-]+)?", version) if isinstance(version, str) else None
    if not match:
        raise HostPreparationError("exact semantic host version is required")
    if claude_stable and match.group(4):
        raise HostPreparationError("Claude Code prerelease builds are not accepted for isolated comparison")
    return tuple(int(match.group(index)) for index in (1, 2, 3))


def _telemetry_summary(snapshots: Any) -> list[dict[str, Any]]:
    """Keep only numeric measurements and opaque source digests."""
    result: list[dict[str, Any]] = []
    for snapshot in snapshots or ():
        costs = getattr(snapshot, "costs", None)
        if costs is None:
            continue
        values = getattr(costs, "values", {})
        result.append({
            "costs": {str(key): value for key, value in values.items()
                       if value is None or type(value) is int
                       or (type(value) is float and math.isfinite(value))},
            "sourceSha256": getattr(costs, "source_sha256", None),
            "observedAt": getattr(costs, "observed_at", None),
        })
    return result
