# SPDX-License-Identifier: AGPL-3.0-only
"""Exact caller-declared synthetic metadata routing; advice only."""
from __future__ import annotations

from collections.abc import Mapping
from time import monotonic_ns as _monotonic_ns
from typing import Any

from agent_braid.system_one import CancellationToken, HASH, InvalidDecision, MAX_BYTES, canonical, digest, freeze, parse_json, thaw

VERSION = "s1-metadata-router-v1"
_TASKS = ("boolean-fixture", "choice-fixture", "score-fixture", "schema-compile-fixture")
_LANGUAGES = ("en", "es")
try:
    from agent_braid.system_one_product_metadata import COMPILER_MANIFEST, CORE_ROUTE_MANIFEST, ROUTER_REGISTRY
except ModuleNotFoundError as exc:
    if exc.name != "agent_braid.system_one_product_metadata":
        raise
    # During coordinated development, absent package metadata grants no support.
    COMPILER_MANIFEST = CORE_ROUTE_MANIFEST = freeze({})
    ROUTER_REGISTRY = freeze({"version": VERSION, "routes": [], "digest": digest({"version": VERSION, "routes": []})})


def _identifier(value: Any) -> bool:
    return (type(value) is str and 1 <= len(value.encode("utf-8")) <= 64
            and not any(ord(c) < 32 or 127 <= ord(c) <= 159 for c in value))


def _hash(value: Any) -> bool:
    return type(value) is str and HASH.fullmatch(value) is not None


def _validated_registry() -> dict:
    """Validate package metadata even when tests replace its private binding."""
    registry = thaw(ROUTER_REGISTRY)
    if type(registry) is not dict or set(registry) != {"version", "routes", "digest"} or registry["version"] != VERSION:
        raise InvalidDecision()
    routes = registry["routes"]
    if type(routes) is not list or len(routes) > 8 or not _hash(registry["digest"]):
        raise InvalidDecision()
    if registry["digest"] != digest({"version": VERSION, "routes": routes}):
        raise InvalidDecision()
    seen = set()
    expected_order = [(language, task) for language in _LANGUAGES for task in _TASKS]
    positions = []
    for route in routes:
        if type(route) is not dict or set(route) != {"languageTag", "taskId", "capabilityId", "backendId", "policyId", "installedManifestDigest", "supported"}:
            raise InvalidDecision()
        language, task = route["languageTag"], route["taskId"]
        if type(language) is not str or type(task) is not str or (language, task) not in expected_order or (language, task) in seen:
            raise InvalidDecision()
        seen.add((language, task))
        positions.append(expected_order.index((language, task)))
        compiler = task == "schema-compile-fixture"
        identities = ("s1-schema-synthetic-v1", None, None) if compiler else ("synthetic-reference-v1", "stdlib-rule-fixture-v1", "strict-uncalibrated-v1")
        if tuple(route[k] for k in ("capabilityId", "backendId", "policyId")) != identities or type(route["supported"]) is not bool:
            raise InvalidDecision()
        manifest = COMPILER_MANIFEST if compiler else CORE_ROUTE_MANIFEST
        if not _hash(route["installedManifestDigest"]) or route["installedManifestDigest"] != digest(manifest):
            raise InvalidDecision()
        if route["supported"] and not manifest:
            raise InvalidDecision()
    if positions != sorted(positions):
        raise InvalidDecision()
    return registry


def router_registry_manifest() -> Mapping:
    """Return the immutable static installed registry; no dynamic discovery."""
    return freeze(_validated_registry())


def router_capabilities() -> Mapping:
    """Describe only package-declared supported routes, without dispatch."""
    registry = _validated_registry()
    return freeze(dict(contractVersion=VERSION, registryDigest=registry["digest"],
                       routes=[r for r in registry["routes"] if r["supported"]],
                       evidenceClass="heuristic", executionAuthorization=False))


def _packet(request: dict | None, registry_digest: str | None, status: str, reason: str | None, route: dict | None = None) -> Mapping:
    fields = dict(contractVersion=VERSION, requestId=request["requestId"] if request is not None else None,
                  requestDigest=digest(request) if request is not None else None, registryDigest=registry_digest,
                  status=status, route=route, reasonCodes=[] if reason is None else [reason],
                  evidenceClass="heuristic", executionAuthorization=False)
    fields["packetDigest"] = digest(fields)
    return freeze(fields)


def route_metadata(request_bytes: bytes, *, expected_registry_digest: str,
                   cancellation: CancellationToken | None = None) -> Mapping:
    """Match a validated envelope against closed installed metadata only."""
    start = _monotonic_ns()
    if cancellation is not None and not isinstance(cancellation, CancellationToken):
        raise TypeError("invalid cancellation token")
    if cancellation is not None:
        cancellation.claim()
    request = None
    registry_digest = None
    deadline = start + 5000000000
    try:
        if cancellation is not None and cancellation.cancelled:
            return _packet(None, None, "defer", "cancelled")
        try:
            raw = parse_json(request_bytes)
            if len(canonical(raw)) > MAX_BYTES:
                raise InvalidDecision()
            if set(raw) != {"contractVersion", "requestId", "sourceKind", "languageTag", "taskId", "registryDigest", "deadlineMs"}:
                raise InvalidDecision()
            if (raw["contractVersion"] != VERSION or not _identifier(raw["requestId"])
                    or type(raw["sourceKind"]) is not str
                    or (raw["languageTag"] is not None and type(raw["languageTag"]) is not str)
                    or (raw["taskId"] is not None and not _identifier(raw["taskId"]))
                    or not _hash(raw["registryDigest"]) or type(raw["deadlineMs"]) is not int
                    or not 1 <= raw["deadlineMs"] <= 5000):
                raise InvalidDecision()
        except InvalidDecision:
            return _packet(None, None, "refused", "invalid-router-request")
        request = raw
        deadline = start + raw["deadlineMs"] * 1000000
        if cancellation is not None and cancellation.cancelled:
            return _packet(request, None, "defer", "cancelled")
        if _monotonic_ns() >= deadline:
            return _packet(request, None, "defer", "deadline-exceeded")
        if raw["sourceKind"] != "synthetic":
            return _packet(request, None, "refused", "unsupported-source")
        try:
            registry = _validated_registry()
        except InvalidDecision:
            return _packet(request, None, "refused", "registry-pin-mismatch")
        registry_digest = registry["digest"]
        if not _hash(expected_registry_digest) or raw["registryDigest"] != registry_digest or expected_registry_digest != registry_digest:
            return _packet(request, registry_digest, "refused", "registry-pin-mismatch")
        status, reason, selected = "matched", None, None
        if raw["languageTag"] not in _LANGUAGES:
            status, reason = "unavailable", "unsupported-language-tag"
        elif raw["taskId"] not in _TASKS:
            status, reason = "unavailable", "unsupported-task-id"
        else:
            selected = next((route for route in registry["routes"] if route["languageTag"] == raw["languageTag"] and route["taskId"] == raw["taskId"] and route["supported"]), None)
            if selected is None:
                status, reason = "unavailable", "capability-not-installed"
        result = _packet(request, registry_digest, status, reason, selected)
        def publish(cancelled: bool) -> Mapping:
            if cancelled:
                return _packet(request, registry_digest, "defer", "cancelled")
            if _monotonic_ns() >= deadline:
                return _packet(request, registry_digest, "defer", "deadline-exceeded")
            return result
        return cancellation.publish(publish) if cancellation is not None else publish(False)
    finally:
        if cancellation is not None:
            cancellation.release()
