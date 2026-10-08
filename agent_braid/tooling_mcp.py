# SPDX-License-Identifier: AGPL-3.0-only
"""Optional, bounded MCP tooling adapter over Agent Braid's existing APIs.

The MCP SDK is deliberately imported only by :func:`create_server` and
:func:`serve_stdio`; importing Agent Braid's core never requires the extra.
This module exposes no grant-issuance API or arbitrary command dispatch.
"""
from __future__ import annotations

import asyncio
import base64
from dataclasses import dataclass, field
import hashlib
import json
import math
import re
import sys
import threading
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit
import uuid

from . import __version__
from . import analysis, git_adapter, mcp_runtime
from . import git_replay, git_runtime, runtime_policy, runtime_scheduler
from .git_process import GitInfrastructureFailure

SCHEMA_VERSION = "agent-braid-tooling/v0.1"
MAX_FRAME_BYTES = 1024 * 1024
MAX_INPUT_DEPTH = 32
MAX_OPERATIONS = 32
MAX_IDENTIFIER_BYTES = 256
INLINE_RESULT_BYTES = 256 * 1024
MAX_SUMMARY_BYTES = 16 * 1024
MAX_ARTIFACT_BYTES = 8 * 1024 * 1024
MAX_INVENTORY_BYTES = 32 * 1024 * 1024
MAX_INVENTORY_ARTIFACTS = 128
CHUNK_BYTES = 128 * 1024
MAX_RESOURCE_RESPONSE_BYTES = 256 * 1024
MAX_ACTIVE_CALLS = 4
CALL_TIMEOUT_SECONDS = 360
_HASH = re.compile(r"^[0-9a-f]{64}$")
_UINT = re.compile(r"^(0|[1-9][0-9]*)$")


class ToolingError(ValueError):
    """A bounded, expected refusal at the adapter boundary."""


@dataclass(frozen=True)
class ToolingConfig:
    """Operator-selected roots and capabilities, fixed before server launch."""

    source_root: Path
    result_parent: Path
    grant_store: Path | None = None
    runtime_enabled: bool = False
    worktree_roots: tuple[Path, ...] = ()

    def __post_init__(self) -> None:
        source = Path(self.source_root).expanduser().resolve(strict=True)
        results = Path(self.result_parent).expanduser().resolve(strict=True)
        if not source.is_dir() or not results.is_dir():
            raise ToolingError("Configured source and result roots must be existing directories")
        if results == source or results.is_relative_to(source) or source.is_relative_to(results):
            raise ToolingError("Configured source and result roots must be disjoint")
        roots = {source}
        for candidate in self.worktree_roots:
            resolved = Path(candidate).expanduser().resolve(strict=True)
            if not resolved.is_dir():
                raise ToolingError("Configured worktree roots must be directories")
            roots.add(resolved)
        grant = None
        if self.grant_store is not None:
            requested_grant = Path(self.grant_store).expanduser().absolute()
            if requested_grant.is_symlink():
                raise ToolingError("Grant store cannot be a symbolic link")
            grant = requested_grant.resolve(strict=False)
            if (grant.is_relative_to(source) or source.is_relative_to(grant)
                    or grant.is_relative_to(results) or results.is_relative_to(grant)):
                raise ToolingError("Grant store must be outside source and result roots")
        if self.runtime_enabled and grant is None:
            raise ToolingError("Runtime mode requires an operator-configured grant store")
        object.__setattr__(self, "source_root", source)
        object.__setattr__(self, "result_parent", results)
        object.__setattr__(self, "grant_store", grant)
        object.__setattr__(self, "worktree_roots", tuple(sorted(roots, key=str)))


def _json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError, UnicodeError) as exc:
        raise ToolingError("Input is not bounded JSON data") from exc


def _check_depth(value: Any, depth: int = 0) -> None:
    if depth > MAX_INPUT_DEPTH:
        raise ToolingError("Input exceeds the maximum nesting depth")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise ToolingError("Object keys must be strings")
            _check_depth(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _check_depth(child, depth + 1)
    elif isinstance(value, float) and not math.isfinite(value):
        raise ToolingError("Non-finite numbers are not supported")


def _bounded_input(value: Any) -> bytes:
    _check_depth(value)
    raw = _json_bytes(value)
    if len(raw) > MAX_FRAME_BYTES:
        raise ToolingError("Input exceeds the 1 MiB adapter limit")
    return raw


def _operation_count(request: Any) -> int:
    if isinstance(request, list):
        return len(request)
    if isinstance(request, dict):
        for key in ("operations", "tasks"):
            value = request.get(key)
            if isinstance(value, list):
                return len(value)
    return 0


def _validate_operation_bounds(request: Any) -> None:
    count = _operation_count(request)
    if count > MAX_OPERATIONS:
        raise ToolingError("Request exceeds the 32-operation adapter limit")
    values = request if isinstance(request, list) else (
        request.get("operations", []) if isinstance(request, dict) else [])
    for item in values:
        if isinstance(item, dict):
            for key in ("instanceId", "attemptId"):
                value = item.get(key)
                if value is not None and len(str(value).encode("utf-8")) > MAX_IDENTIFIER_BYTES:
                    raise ToolingError("Operation identifier exceeds 256 bytes")


def _digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _core_failure_types() -> tuple[type[BaseException], ...]:
    return (ToolingError, mcp_runtime.InvalidMcpRuntime,
            analysis.InvalidAnalysis, git_adapter.InvalidGitAnalysis,
            git_runtime.InvalidGitRuntime, git_replay.InvalidGitReplay,
            runtime_policy.InvalidRuntimePolicy,
            runtime_scheduler.InvalidRuntimeSchedule,
            GitInfrastructureFailure, OSError, UnicodeError)


def _status_for_error(exc: BaseException) -> str:
    text = str(exc).lower()
    if "unavailable in the configured capability mode" in text:
        return "refused"
    if isinstance(exc, (FileNotFoundError, TimeoutError, GitInfrastructureFailure)) or any(
            phrase in text for phrase in ("unavailable observation", "git observation failed", "source changed during observation")):
        return "unknown"
    return "refused"


def _validate_call_shape(name: str, args: Any) -> None:
    if not isinstance(args, dict):
        raise ToolingError("Tool arguments must be an object")
    shapes = {
        "analyze-work": ({"kind", "request"}, {"kind", "request"}),
        "analyze": ({"request"}, {"request"}),
        "prepare": ({"request", "runDirectory"}, {"request", "runDirectory", "mode"}),
        "status": ({"plan"}, {"plan"}),
        "verify": ({"plan"}, {"plan"}),
        "execute": ({"plan", "grantId"}, {"plan", "grantId"}),
        "recover": ({"plan", "grantId", "action"}, {"plan", "grantId", "action"}),
    }
    required, allowed = shapes.get(name, (set(), set()))
    if not required or not required <= set(args) or not set(args) <= allowed:
        raise ToolingError("Tool arguments do not match the declared input schema")
    _bounded_input(args)


async def _settle_cancelled_worker(worker: asyncio.Task[Any], event: threading.Event) -> None:
    """Signal cancellation and wait for the worker so effects cannot be abandoned.

    Git subprocesses enforce command/end-to-end budgets and terminate on the event.
    This cannot bound a filesystem syscall stalled below Python; waiting for that
    worker to settle is intentional because returning early could misstate effects.
    """
    event.set()
    try:
        import anyio
    except ImportError:  # Core-only installations never require the optional SDK stack.
        try:
            await asyncio.shield(worker)
        except BaseException:
            pass
        return
    with anyio.CancelScope(shield=True):
        try:
            await asyncio.shield(worker)
        except BaseException:
            pass


def _summary(operation: str, status: str, result: Any = None, error: str | None = None) -> str:
    if error:
        value = f"{operation} {status}: {error}"
    elif isinstance(result, dict):
        domain = result.get("status") or result.get("classification")
        if domain is None and isinstance(result.get("report"), dict):
            domain = result["report"].get("status")
        value = f"{operation} completed; core outcome: {domain}" if domain else f"{operation} completed with a valid core result"
    else:
        value = f"{operation} completed with a valid core result"
    raw = value.encode("utf-8")
    if len(raw) > MAX_SUMMARY_BYTES:
        value = raw[:MAX_SUMMARY_BYTES].decode("utf-8", "ignore")
    return value


@dataclass(frozen=True)
class _Artifact:
    artifact_id: str
    run_id: str
    data: bytes
    media_type: str
    expected_digest: str
    expected_size: int


@dataclass
class ToolingService:
    config: ToolingConfig
    artifacts: dict[str, _Artifact] = field(default_factory=dict)
    plans: dict[str, dict[str, Any]] = field(default_factory=dict)
    lock: threading.RLock = field(default_factory=threading.RLock)
    runtime: mcp_runtime.RuntimeTools | None = None
    reserved_bytes: int = 0
    active_calls: int = 0

    def __post_init__(self) -> None:
        # RuntimeTools enforces the established path and request boundary. Its
        # grant path is inert unless explicit runtime capability is enabled.
        grant_path = self.config.grant_store or (self.config.result_parent / ".disabled-grants")
        self.runtime = mcp_runtime.RuntimeTools(
            self.config.source_root, self.config.result_parent, grant_path)

    @property
    def tools(self) -> tuple[str, ...]:
        if self.config.runtime_enabled:
            return ("analyze-work", "analyze", "prepare", "status", "execute", "recover", "verify")
        return ("analyze-work", "analyze", "prepare")

    def invoke(self, name: str, args: Any, cancelled: threading.Event) -> dict[str, Any]:
        if name not in self.tools:
            return self._envelope(name, "refused", None,
                                  "Tool is unavailable in the configured capability mode")
        try:
            _validate_call_shape(name, args)
            if name in {"analyze", "prepare"}:
                _validate_operation_bounds(args["request"])
        except ToolingError as exc:
            return self._envelope(name, "refused", None, self._safe_error(exc), input_value=args)
        with self.lock:
            stored_bytes = sum(len(item.data) for item in self.artifacts.values())
            if self.active_calls >= MAX_ACTIVE_CALLS:
                return self._envelope(name, "refused", None,
                                      "Adapter concurrency limit is full; retry after an active call completes")
            if (len(self.artifacts) >= MAX_INVENTORY_ARTIFACTS
                    or stored_bytes + self.reserved_bytes + MAX_ARTIFACT_BYTES > MAX_INVENTORY_BYTES):
                return self._envelope(name, "refused", None,
                    "Owned evidence inventory is full; inspect or restart this local server before another call")
            self.reserved_bytes += MAX_ARTIFACT_BYTES
            self.active_calls += 1
        try:
            _bounded_input(args)
            if cancelled.is_set():
                raise ToolingError("Call cancelled before dispatch")
            if name == "analyze-work":
                value = self._analyze_work(args)
            else:
                assert self.runtime is not None
                value = self.runtime.invoke(name, args, cancelled)
            if cancelled.is_set():
                raise ToolingError("Call cancelled; inspect the owned run before retrying")
            plan = args.get("plan") if isinstance(args, dict) else None
            if isinstance(plan, dict) and isinstance(plan.get("runtimeManifest"), dict):
                self._register_plan(plan)
            return self._envelope(name, "ok", value, input_value=args,
                                  plan_override=plan if isinstance(plan, dict) else None)
        except _core_failure_types() as exc:
            return self._envelope(name, _status_for_error(exc), None,
                                  self._safe_error(exc), input_value=args)
        except Exception as exc:
            # Do not return host paths, request data, or tracebacks through MCP.
            return self._envelope(name, "error", None,
                                  f"Internal adapter failure ({type(exc).__name__}); inspect owned state before retry",
                                  input_value=args)
        finally:
            with self.lock:
                self.reserved_bytes -= MAX_ARTIFACT_BYTES
                self.active_calls -= 1

    def _register_plan(self, plan: dict[str, Any]) -> str | None:
        manifest = plan.get("runtimeManifest")
        if not isinstance(manifest, dict):
            return None
        path = Path(manifest.get("runDirectory", ""))
        try:
            if path.parent.resolve() != self.config.result_parent:
                return None
        except (OSError, TypeError):
            return None
        run_id = "run-" + hashlib.sha256(str(path).encode()).hexdigest()[:20]
        with self.lock:
            self.plans[run_id] = plan
        return run_id

    def _safe_error(self, exc: BaseException) -> str:
        if isinstance(exc, ToolingError):
            return str(exc)[:1024]
        if isinstance(exc, OSError):
            return "The operation could not complete because an observation was unavailable"
        if isinstance(exc, UnicodeError):
            return "The operation encountered invalid text data"
        return "The bounded operation was refused"

    def _analyze_work(self, args: Any) -> dict[str, Any]:
        if not isinstance(args, dict) or set(args) != {"kind", "request"}:
            raise ToolingError("analyze-work requires exactly kind and request")
        kind, request = args["kind"], args["request"]
        _validate_operation_bounds(request)
        if kind == "aim":
            return {"report": analysis.analyze(request),
                    "provenance": {"source": "AIM input", "executionAuthorization": False}}
        if kind != "git":
            raise ToolingError("Unsupported analysis kind")
        if not isinstance(request, dict) or set(request) != {
                "gitAnalysisRequestVersion", "repository", "baseRevision", "operations"}:
            raise ToolingError("Git analysis request shape is invalid")
        repository = Path(request["repository"]).expanduser().resolve(strict=True)
        if repository != self.config.source_root:
            raise ToolingError("Git repository is outside the configured source root")
        roots = set(self.config.worktree_roots)
        for operation in request["operations"]:
            if not isinstance(operation, dict):
                raise ToolingError("Git operations must be objects")
            source = operation.get("source")
            if not isinstance(source, dict):
                raise ToolingError("Git operation source is invalid")
            if source.get("kind") == "worktree":
                candidate = Path(source.get("path", "")).expanduser().resolve(strict=True)
                if candidate not in roots:
                    raise ToolingError("Worktree is outside the operator-configured allowlist")
        report, provenance = git_adapter.analyze_git_with_provenance(request)
        return {"report": report, "provenance": provenance}

    def _envelope(self, operation: str, status: str, value: Any,
                  error: str | None = None, *, input_value: Any = None,
                  plan_override: dict[str, Any] | None = None) -> dict[str, Any]:
        run_id = uuid.uuid4().hex
        result_value = value
        evidence_refs: list[dict[str, Any]] = []
        plan = (value if isinstance(value, dict) and isinstance(value.get("runtimeManifest"), dict)
                else plan_override)
        if plan is not None:
            registered = self._register_plan(plan)
            if registered is not None:
                run_id = registered
        if status == "ok" and value is not None:
            _check_depth(value)
            raw = _json_bytes(value)
            if len(raw) > MAX_ARTIFACT_BYTES:
                if operation in {"execute", "recover"} and plan is not None:
                    # The core may already have crossed an effect boundary. Do
                    # not imply success or invite replay when its full outcome
                    # cannot be retained; point to the existing run for inspection.
                    status = "unknown"
                    error = ("Core outcome exceeds the 8 MiB evidence limit; inspect the existing run "
                             "with status and verify before deciding whether recovery is needed")
                    result_value = {"resultUnavailable": True, "runId": run_id,
                                    "reason": error, "retryGuidance": "Do not replay; inspect the existing run"}
                else:
                    status = "refused"
                    error = "Core result exceeds the 8 MiB evidence limit; no complete result is returned"
                    result_value = None
            else:
                artifact_id = "ev-" + uuid.uuid4().hex
                artifact = _Artifact(artifact_id, run_id, raw, "application/json",
                                     _digest_bytes(raw), len(raw))
                with self.lock:
                    self.artifacts[artifact_id] = artifact
                evidence_refs.append({"artifactId": artifact_id,
                                      "uri": self._base_uri(run_id, artifact_id),
                                      "sha256": artifact.expected_digest, "sizeBytes": artifact.expected_size})
                if len(raw) > INLINE_RESULT_BYTES:
                    result_value = self._artifact_reference(artifact)
        return {
            "schemaVersion": SCHEMA_VERSION,
            "operation": operation,
            "status": status,
            "summary": _summary(operation, status, value, error),
            "result": result_value,
            "evidenceRefs": evidence_refs,
            "limits": ["Bounded local stdio adapter; no new execution authority",
                       "Result is complete inline or must be reconstructed and hash-verified"],
            "provenance": {"candidateVersion": __version__,
                           "runtimePolicyVersion": runtime_policy.VERSION,
                           "schemaVersion": SCHEMA_VERSION,
                           "observationContract": "Existing Agent Braid core and bounded local roots",
                           "sourceIdentity": "sha256:" + hashlib.sha256(
                               str(self.config.source_root).encode("utf-8")).hexdigest(),
                           "inputDigest": _digest_bytes(_json_bytes({"operation": operation,
                                                                    "input": input_value})) if input_value is not None else None,
                           "executionAuthorization": False if operation in {"analyze-work", "analyze"} else None},
        }

    @staticmethod
    def _base_uri(run_id: str, artifact_id: str) -> str:
        return f"agent-braid://runs/{quote(run_id, safe='')}/evidence/{quote(artifact_id, safe='')}"

    def _artifact_reference(self, artifact: _Artifact) -> dict[str, Any]:
        return {"type": "evidence-artifact-reference", "artifactId": artifact.artifact_id,
                "uri": self._base_uri(artifact.run_id, artifact.artifact_id),
                "sha256": artifact.expected_digest, "sizeBytes": artifact.expected_size,
                "mediaType": artifact.media_type}

    def capabilities(self) -> dict[str, Any]:
        return {"schemaVersion": SCHEMA_VERSION, "tools": list(self.tools),
                "resources": ["agent-braid://capabilities", "agent-braid://runs/{id}/status",
                              "agent-braid://runs/{id}/evidence/{artifact}"],
                "prompts": ["agent-braid-analyze", "agent-braid-plan", "agent-braid-evidence"],
                "mode": "runtime-enabled" if self.config.runtime_enabled else "analysis-only",
                "limits": {"inputBytes": MAX_FRAME_BYTES, "depth": MAX_INPUT_DEPTH,
                           "inlineResultBytes": INLINE_RESULT_BYTES,
                           "artifactBytes": MAX_ARTIFACT_BYTES, "chunkBytes": CHUNK_BYTES}}

    def read_resource(self, uri: str, cancelled: threading.Event | None = None) -> tuple[str, str]:
        if not isinstance(uri, str):
            raise ToolingError("Resource selector must be a bounded URI")
        try:
            encoded_uri = uri.encode("utf-8", "strict")
        except UnicodeError as exc:
            raise ToolingError("Resource selector must be valid UTF-8") from exc
        if len(encoded_uri) > 1024:
            raise ToolingError("Resource selector exceeds the bounded URI limit")
        def response(mime: str, body: bytes) -> tuple[str, str]:
            if len(body) > MAX_RESOURCE_RESPONSE_BYTES:
                raise ToolingError("Resource response exceeds its 256 KiB limit")
            return mime, body.decode("utf-8")

        if uri == "agent-braid://capabilities":
            return response("application/json", _json_bytes(self.capabilities()))
        try:
            parsed = urlsplit(uri)
        except ValueError as exc:
            raise ToolingError("Malformed resource URI") from exc
        parts = parsed.path.strip("/").split("/")
        if parsed.scheme != "agent-braid" or parsed.netloc != "runs" or parsed.query or parsed.fragment:
            raise ToolingError("Unknown resource")
        if len(parts) == 2 and parts[1] == "status":
            run_id = unquote(parts[0])
            with self.lock:
                plan = self.plans.get(run_id)
            if plan is None:
                raise ToolingError("Owned run is unavailable")
            if self.config.runtime_enabled:
                assert self.runtime is not None
                status = self.runtime.invoke("status", {"plan": plan}, cancelled or threading.Event())
            else:
                status = {"status": "unknown", "planPrepared": True, "runObserved": False,
                          "planDigest": plan.get("planDigest"), "executionAuthorization": False,
                          "limits": ["Runtime inspection is not configured for this server"]}
            return response("application/json", _json_bytes({"runId": run_id, "status": status}))
        if len(parts) == 3 and parts[1] == "evidence":
            artifact = self._owned_artifact(unquote(parts[0]), unquote(parts[2]))
            manifest = {"artifactId": artifact.artifact_id, "sha256": artifact.expected_digest,
                        "sizeBytes": artifact.expected_size, "mediaType": artifact.media_type,
                        "chunkSizeBytes": CHUNK_BYTES,
                        "firstChunkUri": self._chunk_uri(artifact, 0) if artifact.data else None}
            body = _json_bytes(manifest)
            if len(body) > 16 * 1024:
                raise ToolingError("Evidence manifest exceeds its response limit")
            return response("application/json", body)
        if len(parts) == 7 and parts[1] == "evidence" and parts[3] == "chunks":
            run_id, artifact_id = unquote(parts[0]), unquote(parts[2])
            digest, offset_text, length_text = parts[4:7]
            if not _HASH.fullmatch(digest) or not _UINT.fullmatch(offset_text) or not _UINT.fullmatch(length_text):
                raise ToolingError("Invalid chunk selector")
            if len(offset_text) > 8 or len(length_text) > 6:
                raise ToolingError("Chunk selector exceeds the artifact bounds")
            offset, length = int(offset_text), int(length_text)
            artifact = self._owned_artifact(run_id, artifact_id)
            raw = artifact.data
            if digest != artifact.expected_digest or offset < 0 or offset >= len(raw) or not 1 <= length <= CHUNK_BYTES or offset + length > len(raw):
                raise ToolingError("Chunk selector is stale or out of range")
            chunk = raw[offset:offset + length]
            next_offset = offset + length
            payload = {"artifactId": artifact_id, "artifactSha256": artifact.expected_digest,
                       "chunkSha256": _digest_bytes(chunk), "offset": offset,
                       "length": len(chunk), "totalBytes": len(raw), "encoding": "base64",
                       "data": base64.b64encode(chunk).decode("ascii"),
                       "nextChunkUri": self._chunk_uri(artifact, next_offset) if next_offset < len(raw) else None}
            body = _json_bytes(payload)
            if len(body) > MAX_RESOURCE_RESPONSE_BYTES:
                raise ToolingError("Chunk response exceeds its 256 KiB limit")
            return response("application/json", body)
        raise ToolingError("Unknown resource")

    @staticmethod
    def _chunk_uri(artifact: _Artifact, offset: int) -> str:
        if offset >= len(artifact.data):
            raise ToolingError("Chunk offset is outside the artifact")
        length = min(CHUNK_BYTES, len(artifact.data) - offset)
        return (f"agent-braid://runs/{quote(artifact.run_id, safe='')}/evidence/"
                f"{quote(artifact.artifact_id, safe='')}/chunks/{artifact.expected_digest}/{offset}/{length}")

    def _owned_artifact(self, run_id: str, artifact_id: str) -> _Artifact:
        with self.lock:
            artifact = self.artifacts.get(artifact_id)
        if (artifact is None or artifact.run_id != run_id
                or len(artifact.data) != artifact.expected_size
                or artifact.expected_size > MAX_ARTIFACT_BYTES):
            raise ToolingError("Owned evidence artifact is missing or stale")
        if (not _HASH.fullmatch(artifact.expected_digest)
                or _digest_bytes(artifact.data) != artifact.expected_digest):
            raise ToolingError("Owned evidence artifact is corrupt or stale")
        return artifact


_PROMPT_TEXT = {
    "agent-braid-analyze": "Analyze the supplied bounded AIM or Git work request. Explain conflicts, conditions, unknown coverage, evidence and limits. Do not infer execution authority.",
    "agent-braid-plan": "Use Agent Braid analysis and preparation to inspect dependencies and the exact bounded plan. Explain what requires existing operator authorization. Never request or create a grant through a tool.",
    "agent-braid-evidence": "Retrieve only the referenced owned evidence. Reconstruct bytes from the manifest and chunk chain, verify every chunk and the complete SHA-256 and length before parsing or comparison.",
}


def _tool_definitions(service: ToolingService, types: Any) -> list[Any]:
    definitions = []
    for name in service.tools:
        if name == "analyze-work":
            request = {"oneOf": [{"type": "object"}, {"type": "array"}]}
            schema = {"type": "object", "additionalProperties": False,
                      "properties": {"kind": {"enum": ["aim", "git"]}, "request": request},
                      "required": ["kind", "request"]}
        elif name in {"analyze", "prepare"}:
            request = {"type": "object"}
            props = {"request": request}
            required = ["request"]
            if name == "prepare":
                props.update({"runDirectory": {"type": "string"},
                              "mode": {"enum": ["serial", "parallel"]}})
                required.append("runDirectory")
            schema = {"type": "object", "additionalProperties": False,
                      "properties": props, "required": required}
        else:
            props = {"plan": {"type": "object"}}
            required = ["plan"]
            if name in {"execute", "recover"}:
                props["grantId"] = {"type": "string"}
                required.append("grantId")
            if name == "recover":
                props["action"] = {"enum": ["resume", "abort"]}
                required.append("action")
            schema = {"type": "object", "additionalProperties": False,
                      "properties": props, "required": required}
        definitions.append(types.Tool(
            name=name, description=f"Bounded Agent Braid {name}; host permissions and annotations do not grant runtime authority.",
            inputSchema=schema, outputSchema={"type": "object", "properties": {
                "schemaVersion": {"const": SCHEMA_VERSION},
                "operation": {"type": "string"},
                "status": {"enum": ["ok", "refused", "unknown", "error"]},
                "summary": {"type": "string"}, "result": {},
                "evidenceRefs": {"type": "array"}, "limits": {"type": "array"},
                "provenance": {"type": "object"}},
                "required": ["schemaVersion", "operation", "status", "summary", "result", "evidenceRefs", "limits", "provenance"]},
            annotations=types.ToolAnnotations(readOnlyHint=name not in {"execute", "recover"},
                                               destructiveHint=name == "recover", openWorldHint=False)))
    return definitions


def create_server(config: ToolingConfig) -> Any:
    """Create the optional SDK server; importing the SDK remains lazy."""
    try:
        from importlib.metadata import PackageNotFoundError, version
        try:
            installed_version = version("mcp")
        except PackageNotFoundError as exc:
            raise RuntimeError(
                "Install Agent Braid with the optional 'tooling' extra (mcp==2.3.0) to serve MCP"
            ) from exc
        if installed_version != "2.3.0":
            raise RuntimeError(
                f"Unsupported MCP SDK version {installed_version!r}; install the pinned optional 'tooling' extra (mcp==2.3.0)"
            )
        from mcp.server import Server
        import mcp.types as types
    except RuntimeError:
        raise
    except ImportError as exc:
        raise RuntimeError("Install Agent Braid with the optional 'tooling' extra (mcp==2.3.0) to serve MCP") from exc
    service = ToolingService(config)

    async def list_tools(_ctx: Any, _params: Any) -> Any:
        return types.ListToolsResult(tools=_tool_definitions(service, types))

    async def call_tool(ctx: Any, params: Any) -> Any:
        name = params.name
        args = params.arguments or {}
        # Tool-name/shape failures are protocol errors. Bounded, well-shaped
        # requests that core rejects are returned as explicit refusal envelopes.
        if name not in service.tools:
            raise ToolingError("Tool is unavailable in the configured capability mode")
        _validate_call_shape(name, args)
        event = threading.Event()
        worker = asyncio.create_task(asyncio.to_thread(service.invoke, name, args, event))
        try:
            async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
                envelope = await asyncio.shield(worker)
        except BaseException:
            # Do not abandon a running effectful thread; runtime checkpoints
            # and exact grants remain in control until the worker settles.
            await _settle_cancelled_worker(worker, event)
            raise
        content = _json_bytes(envelope).decode("utf-8")
        return types.CallToolResult(content=[types.TextContent(text=content)],
                                    structuredContent=envelope,
                                    isError=envelope["status"] in {"refused", "error"})

    async def list_resources(_ctx: Any, _params: Any) -> Any:
        resources = [types.Resource(name="capabilities", uri="agent-braid://capabilities",
                                    mimeType="application/json", description="Configured bounded capabilities")]
        with service.lock:
            run_ids = sorted(service.plans)
            artifacts = list(service.artifacts.values())
        for run_id in run_ids:
            resources.append(types.Resource(name=f"run-{run_id}-status",
                uri=f"agent-braid://runs/{quote(run_id, safe='')}/status", mimeType="application/json"))
        for artifact in artifacts:
            resources.append(types.Resource(name=f"evidence-{artifact.artifact_id}",
                uri=service._base_uri(artifact.run_id, artifact.artifact_id), mimeType="application/json"))
        return types.ListResourcesResult(resources=resources)

    async def read_resource(_ctx: Any, params: Any) -> Any:
        mime, value = await _read_resource_bounded(service, str(params.uri))
        return types.ReadResourceResult(contents=[types.TextResourceContents(uri=str(params.uri),
                                                                               mimeType=mime, text=value)])

    async def list_prompts(_ctx: Any, _params: Any) -> Any:
        prompts = [types.Prompt(name=name, description=text) for name, text in _PROMPT_TEXT.items()]
        return types.ListPromptsResult(prompts=prompts)

    async def get_prompt(_ctx: Any, params: Any) -> Any:
        text = _PROMPT_TEXT.get(params.name)
        if text is None:
            raise ToolingError("Unknown prompt")
        arguments = params.arguments or {}
        if len(_json_bytes(arguments)) > 16 * 1024:
            raise ToolingError("Prompt arguments exceed the bounded limit")
        return types.GetPromptResult(description="Read-only bounded workflow guidance",
            messages=[types.PromptMessage(role="user", content=types.TextContent(text=text))])

    return Server("agent-braid-tooling", version=__version__,
                  instructions="Bounded local analysis and explicitly configured private runtime.",
                  on_list_tools=list_tools, on_call_tool=call_tool,
                  on_list_resources=list_resources, on_read_resource=read_resource,
                  on_list_prompts=list_prompts, on_get_prompt=get_prompt)


async def _read_resource_bounded(service: ToolingService, uri: str) -> tuple[str, str]:
    """Read resources off-loop and do not abandon a cancellable status inspection."""
    event = threading.Event()
    worker = asyncio.create_task(asyncio.to_thread(service.read_resource, uri, event))
    try:
        async with asyncio.timeout(CALL_TIMEOUT_SECONDS):
            return await asyncio.shield(worker)
    except BaseException:
        await _settle_cancelled_worker(worker, event)
        raise


async def serve_stdio(config: ToolingConfig, stdin: Any = None, stdout: Any = None) -> None:
    """Serve MCP over stdio with bounded input.

    An injected ``stdin`` must be a synchronous binary or text stream exposing
    ``readline(size)``. It is wrapped in the async iterator expected by the SDK;
    arbitrary AnyIO async file objects are not accepted by this entry point.
    """
    try:
        import anyio
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise RuntimeError("Install Agent Braid with the optional 'tooling' extra (mcp==2.3.0) to serve MCP") from exc
    server = create_server(config)
    default_stdin = getattr(sys.stdin, "buffer", sys.stdin)
    bounded_stdin = _BoundedInput(stdin if stdin is not None else default_stdin)
    async with stdio_server(stdin=bounded_stdin, stdout=stdout) as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


class _BoundedInput:
    """Async text iterator that caps each raw JSON-RPC line before SDK parsing."""

    def __init__(self, stream: Any):
        self.stream = stream
        self.closed = False

    def __aiter__(self) -> "_BoundedInput":
        return self

    async def __anext__(self) -> str:
        line = await asyncio.to_thread(self._read_line)
        if line is None:
            raise StopAsyncIteration
        if line == "__MCP_TOOLING_OVERSIZE__":
            return "{\n"
        try:
            raw = line.encode("utf-8")
            _scan_depth(raw)
            _validate_wire_json(raw)
        except ToolingError:
            # Feed a bounded malformed frame to the SDK, which owns parse-error
            # and JSON-RPC response semantics. No tool handler sees this line.
            return "{\n"
        return line

    def _read_line(self) -> str | None:
        if self.closed:
            return None
        pieces: list[bytes] = []
        total = 0
        while True:
            size = min(8192, MAX_FRAME_BYTES + 1 - total)
            part = self.stream.readline(size)
            if not part:
                if not pieces:
                    return None
                break
            if isinstance(part, str):
                try:
                    part = part.encode("utf-8")
                except UnicodeEncodeError:
                    return "{\n"
            total += len(part)
            if total > MAX_FRAME_BYTES:
                # The frame cannot be resynchronized safely without draining an
                # unbounded peer stream; close after the SDK receives one bounded
                # malformed frame. No request handler sees the oversized input.
                self.closed = True
                return "__MCP_TOOLING_OVERSIZE__"
            pieces.append(part)
            if part.endswith(b"\n"):
                break
        try:
            return b"".join(pieces).decode("utf-8")
        except UnicodeDecodeError:
            return "{\n"


def _scan_depth(raw: bytes) -> None:
    depth = 0
    in_string = False
    escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
        elif byte == 0x22:
            in_string = True
        elif byte in (0x7B, 0x5B):
            depth += 1
            if depth > MAX_INPUT_DEPTH + 8:  # allow the MCP envelope around args
                raise ToolingError("Input exceeds maximum JSON nesting depth")
        elif byte in (0x7D, 0x5D):
            depth -= 1


def _validate_wire_json(raw: bytes) -> None:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in items:
            if key in result:
                raise ToolingError("Duplicate JSON member")
            result[key] = value
        return result
    def constant(_value: str) -> None:
        raise ToolingError("Non-finite JSON number")
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ToolingError("Malformed JSON-RPC frame") from exc
    # Allow the bounded JSON-RPC envelope around a 32-level tool argument.
    _check_depth(value, depth=-4)


def main(argv: list[str] | None = None) -> int:
    """Standalone entry point; CLI integration may call :func:`serve_stdio`."""
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--result-parent", type=Path, required=True)
    parser.add_argument("--grant-store", type=Path)
    parser.add_argument("--enable-runtime", action="store_true")
    parser.add_argument("--worktree-root", action="append", default=[], type=Path)
    args = parser.parse_args(argv)
    try:
        config = ToolingConfig(args.source_root, args.result_parent, args.grant_store,
                               args.enable_runtime, tuple(args.worktree_root))
        asyncio.run(serve_stdio(config))
        return 0
    except (RuntimeError, ToolingError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


__all__ = ["ToolingConfig", "ToolingService", "ToolingError", "create_server", "serve_stdio", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
