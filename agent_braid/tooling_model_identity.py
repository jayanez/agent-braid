# SPDX-License-Identifier: AGPL-3.0-only
"""Declared and freshly observed model identity for M4.5 host registrations.

These records make a requested remote route distinguishable from an immutable
backend build. They validate caller data only; the configured trusted verifier
must authenticate the provider route and catalog evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import re
from typing import Any, Mapping
from urllib.parse import urlsplit

IDENTITY_KINDS = frozenset({"immutable-provider-build", "observable-requested-route"})
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SECRET_HINT = re.compile(r"token|secret|password|api[-_]?key|authorization|credential", re.IGNORECASE)


class ModelIdentityError(ValueError):
    """Declared or observed model identity is malformed, stale, or drifted."""


@dataclass(frozen=True)
class ModelIdentityObservation:
    selector_kind: str
    configured_selector: str
    reported_selector: str | None
    effort: str
    config_sha256: str
    catalog_sha256: str
    entry_sha256: str
    provider_route: Mapping[str, str]
    backend_available: bool
    immutable_id: str | None
    backend_sha256: str | None
    observed_at_utc: datetime
    source_ref: str
    source_sha256: str

    def as_dict(self) -> dict[str, Any]:
        if not isinstance(self.observed_at_utc, datetime) or self.observed_at_utc.tzinfo is None:
            raise ModelIdentityError("model identity observation timestamp must be timezone-aware")
        return {
            "selectorKind": self.selector_kind,
            "configuredSelector": self.configured_selector,
            "reportedSelector": self.reported_selector,
            "effort": self.effort,
            "configSha256": self.config_sha256,
            "catalogSha256": self.catalog_sha256,
            "entrySha256": self.entry_sha256,
            "providerRoute": dict(self.provider_route) if isinstance(self.provider_route, Mapping) else self.provider_route,
            "backendAvailable": self.backend_available,
            "immutableId": self.immutable_id,
            "backendSha256": self.backend_sha256,
            "observedAtUtc": _iso(self.observed_at_utc),
            "sourceRef": self.source_ref,
            "sourceSha256": self.source_sha256,
        }


def validate_identity(value: Any, *, host: str, model: Any) -> None:
    """Validate model identity; ``backendAvailable`` means immutable ID exposed.

    It says nothing about whether the remote model service is reachable. Config
    and entry hashes use canonical JSON; native catalog hashes cover the exact
    retained artifact bytes. Hashes alone do not authenticate either source.
    """
    if not isinstance(value, Mapping):
        raise ModelIdentityError("modelIdentity must be an object")
    common = {"kind", "selectorKind", "selector", "effort", "effectiveConfig", "configSha256", "cliBuild", "nativeCatalogEntry",
              "providerRoute", "backendAvailable", "immutableId", "backendDigestAvailable", "backendSha256"}
    if set(value) != common:
        raise ModelIdentityError("modelIdentity fields are incomplete or unknown")
    kind = value.get("kind")
    if not isinstance(kind, str) or kind not in IDENTITY_KINDS:
        raise ModelIdentityError("modelIdentity.kind is unsupported")
    selector_kind = value.get("selectorKind")
    selector_kinds = ({"provider-alias"} if kind == "observable-requested-route"
                      else {"immutable-id", "provider-alias"})
    if not isinstance(selector_kind, str) or selector_kind not in selector_kinds:
        raise ModelIdentityError("modelIdentity.selectorKind is unsupported for its identity kind")
    _text(value.get("selector"), "modelIdentity.selector")
    _text(value.get("effort"), "modelIdentity.effort")
    config = value.get("effectiveConfig")
    expected_config_keys = {"selector", "effort", "providerEndpoint", "authMethod", "hostSelection"}
    _validate_route(value.get("providerRoute"))
    expected_provider = {"codex": "openai", "claude-code": "anthropic"}.get(host)
    expected_auth = {"codex": "chatgpt", "claude-code": "claude.ai"}.get(host)
    route = value["providerRoute"]
    if route["provider"] != expected_provider or route["authMethod"] != expected_auth:
        raise ModelIdentityError("provider and subscription authentication route must match the registered host")
    if not isinstance(config, Mapping) or set(config) != expected_config_keys:
        raise ModelIdentityError("modelIdentity.effectiveConfig fields are incomplete or unknown")
    if config.get("selector") != value["selector"] or config.get("effort") != value["effort"]:
        raise ModelIdentityError("effective model/effort selection differs from registered selector and effort")
    _text(config.get("providerEndpoint"), "modelIdentity.effectiveConfig.providerEndpoint")
    endpoint_text = config["providerEndpoint"]
    if endpoint_text != "native-first-party-default":
        try:
            endpoint = urlsplit(endpoint_text)
            domain = endpoint.hostname or ""
        except ValueError as exc:
            raise ModelIdentityError("effective provider endpoint is malformed") from exc
        approved_domains = {"codex": ("openai.com", "chatgpt.com"),
                            "claude-code": ("anthropic.com", "claude.ai")}.get(host)
        if (endpoint.scheme != "https" or not domain or endpoint.username is not None or endpoint.password is not None
                or endpoint.query or endpoint.fragment or not approved_domains
                or not any(domain == root or domain.endswith("." + root) for root in approved_domains)):
            raise ModelIdentityError("effective provider endpoint must be official HTTPS without credentials")
        if _SECRET_HINT.search(endpoint.path):
            raise ModelIdentityError("effective provider endpoint path appears to contain credential material")
    if config.get("authMethod") != value.get("providerRoute", {}).get("authMethod"):
        raise ModelIdentityError("effective configuration auth method differs from provider route")
    selection = config.get("hostSelection")
    if (not isinstance(selection, Mapping) or set(selection) != {"source", "configRef", "flags", "argv"}
            or not isinstance(selection.get("source"), str)
            or selection.get("source") not in {"config", "argv", "both"}):
        raise ModelIdentityError("effective configuration hostSelection is incomplete or unsupported")
    config_ref = selection.get("configRef")
    if config_ref is not None and (not isinstance(config_ref, str)
                                   or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,255}", config_ref)
                                   or _SECRET_HINT.search(config_ref)):
        raise ModelIdentityError("host selection configRef must be a sanitized artifact identifier")
    if selection.get("flags") != ["model-selector", "reasoning-effort"]:
        raise ModelIdentityError("host selection flags must use the bounded selector/effort descriptors")
    if selection.get("argv") != ["selector", "effort"]:
        raise ModelIdentityError("host selection argv may contain only abstract selector/effort descriptors")
    if len(_canonical_json_bytes(config)) > 8192:
        raise ModelIdentityError("effective configuration is too large")
    _hash(value.get("configSha256"), "modelIdentity.configSha256")
    if value["configSha256"] != canonical_json_sha256(config):
        raise ModelIdentityError("modelIdentity.configSha256 does not match canonical effectiveConfig JSON")
    cli = value.get("cliBuild")
    if not isinstance(cli, Mapping) or set(cli) != {"version", "sha256"}:
        raise ModelIdentityError("modelIdentity.cliBuild must bind version and SHA-256")
    _text(cli.get("version"), "modelIdentity.cliBuild.version")
    _hash(cli.get("sha256"), "modelIdentity.cliBuild.sha256")
    catalog = value.get("nativeCatalogEntry")
    if not isinstance(catalog, Mapping) or set(catalog) != {"observedAtUtc", "sourceRef", "catalogSha256", "entrySha256"}:
        raise ModelIdentityError("modelIdentity.nativeCatalogEntry must bind a dated native catalog entry")
    _timestamp(catalog.get("observedAtUtc"), "modelIdentity.nativeCatalogEntry.observedAtUtc")
    _text(catalog.get("sourceRef"), "modelIdentity.nativeCatalogEntry.sourceRef")
    _hash(catalog.get("catalogSha256"), "modelIdentity.nativeCatalogEntry.catalogSha256")
    _hash(catalog.get("entrySha256"), "modelIdentity.nativeCatalogEntry.entrySha256")
    available = value.get("backendAvailable")
    immutable_id = value.get("immutableId")
    if type(available) is not bool:
        raise ModelIdentityError("modelIdentity.backendAvailable must be explicit boolean")
    digest_available = value.get("backendDigestAvailable")
    backend_sha256 = value.get("backendSha256")
    if type(digest_available) is not bool:
        raise ModelIdentityError("modelIdentity.backendDigestAvailable must be explicit boolean")
    if digest_available:
        _hash(backend_sha256, "modelIdentity.backendSha256")
    elif backend_sha256 is not None:
        raise ModelIdentityError("unavailable backend artifact digest must be explicitly null")
    if available:
        _text(immutable_id, "modelIdentity.immutableId")
        if kind != "immutable-provider-build":
            raise ModelIdentityError("an available immutable backend requires immutable-provider-build identity")
    elif immutable_id is not None:
        raise ModelIdentityError("unavailable backend identity must be explicitly null")
    if kind == "immutable-provider-build" and (not available or not isinstance(immutable_id, str)):
        raise ModelIdentityError("immutable-provider-build requires an available authoritative immutable ID")
    if kind == "immutable-provider-build" and selector_kind == "immutable-id" and value["selector"] != immutable_id:
        raise ModelIdentityError("immutable-id selector must equal the authoritative provider ID")
    if kind == "observable-requested-route" and available:
        raise ModelIdentityError("observable-requested-route requires backendAvailable false")
    if not isinstance(model, Mapping):
        raise ModelIdentityError("host model must be an object")
    if set(model) != {"name", "version", "sha256"}:
        raise ModelIdentityError("v2 host model must explicitly provide name, version, and sha256 fields")
    if model.get("name") != value["selector"]:
        raise ModelIdentityError("legacy model.name must equal the exact configured selector")
    if kind == "observable-requested-route":
        if model.get("version") is not None or model.get("sha256") is not None:
            raise ModelIdentityError("requested-route identity must leave backend model version and SHA-256 null")
        if digest_available or backend_sha256 is not None:
            raise ModelIdentityError("requested-route backend artifact digest must remain unavailable and null")
    else:
        if model.get("version") != immutable_id:
            raise ModelIdentityError("host model.version must equal the authoritative immutable provider ID")
        if digest_available:
            if model.get("sha256") != backend_sha256:
                raise ModelIdentityError("host model.sha256 must equal the declared authoritative backend digest")
        elif model.get("sha256") is not None:
            raise ModelIdentityError("unavailable backend artifact digest must remain null")


def check_observation(observation: ModelIdentityObservation, identity: Mapping[str, Any], *,
                      now: datetime | None = None, max_age_seconds: float = 60) -> bool:
    if not isinstance(observation, ModelIdentityObservation):
        raise ModelIdentityError("fresh typed model identity observation is required")
    _validate_identity_only(identity)
    if isinstance(max_age_seconds, bool) or not isinstance(max_age_seconds, (int, float)):
        raise ModelIdentityError("max_age_seconds must be finite and nonnegative")
    try:
        if not math.isfinite(max_age_seconds) or max_age_seconds < 0:
            raise ModelIdentityError("max_age_seconds must be finite and nonnegative")
    except (TypeError, OverflowError) as exc:
        raise ModelIdentityError("max_age_seconds must be finite and nonnegative") from exc
    if not isinstance(observation.provider_route, Mapping):
        raise ModelIdentityError("observed provider route must be an object")
    _validate_route(observation.provider_route)
    if observation.configured_selector != identity["selector"]:
        raise ModelIdentityError("configured selector drifted from the frozen registration")
    if observation.reported_selector is not None and observation.reported_selector != identity["selector"]:
        raise ModelIdentityError("reported selector drifted from the frozen registration")
    if observation.effort != identity["effort"] or observation.config_sha256 != identity["configSha256"]:
        raise ModelIdentityError("model selection effort or configuration hash drifted")
    catalog = identity["nativeCatalogEntry"]
    if (observation.catalog_sha256 != catalog["catalogSha256"]
            or observation.entry_sha256 != catalog["entrySha256"]):
        raise ModelIdentityError("native model catalog or selected entry drifted")
    if dict(observation.provider_route) != dict(identity["providerRoute"]):
        raise ModelIdentityError("authenticated provider/account route drifted")
    if type(observation.backend_available) is not bool:
        raise ModelIdentityError("backend availability must be explicitly observed")
    if observation.backend_available != identity["backendAvailable"]:
        raise ModelIdentityError("backend availability differs from registered identity")
    if observation.backend_available:
        if not isinstance(observation.immutable_id, str) or observation.immutable_id != identity["immutableId"]:
            raise ModelIdentityError("observed immutable backend ID differs from the frozen registration")
        if identity["backendDigestAvailable"]:
            if observation.backend_sha256 != identity["backendSha256"]:
                raise ModelIdentityError("observed backend digest differs from its authoritative registered digest")
        elif observation.backend_sha256 is not None:
            raise ModelIdentityError("unregistered backend digest must remain null")
    elif observation.immutable_id is not None:
        raise ModelIdentityError("unavailable backend must retain an explicit null immutable ID")
    elif observation.backend_sha256 is not None:
        raise ModelIdentityError("unavailable backend digest must remain null")
    if observation.selector_kind != identity["selectorKind"]:
        raise ModelIdentityError("observed selector kind differs from the frozen registration")
    if (not isinstance(observation.configured_selector, str)
            or not isinstance(observation.effort, str)
            or (observation.reported_selector is not None and not isinstance(observation.reported_selector, str))):
        raise ModelIdentityError("observed model selectors and effort must be text or explicit null")
    _hash(observation.config_sha256, "observed config SHA-256")
    _hash(observation.catalog_sha256, "observed catalog SHA-256")
    _hash(observation.entry_sha256, "observed catalog-entry SHA-256")
    _hash(observation.source_sha256, "model identity source SHA-256")
    _text(observation.source_ref, "model identity source reference")
    current = datetime.now(timezone.utc) if now is None else now
    if (not isinstance(current, datetime) or not isinstance(observation.observed_at_utc, datetime)
            or current.tzinfo is None or observation.observed_at_utc.tzinfo is None
            or observation.observed_at_utc.utcoffset() != timezone.utc.utcoffset(observation.observed_at_utc)):
        raise ModelIdentityError("model identity observation timestamp must be UTC")
    age = (current - observation.observed_at_utc).total_seconds()
    if age < 0 or age > max_age_seconds:
        raise ModelIdentityError("model identity observation is from the future or stale")
    return True


def observation_from_dict(value: Any) -> ModelIdentityObservation:
    expected = {"selectorKind", "configuredSelector", "reportedSelector", "effort", "configSha256", "catalogSha256",
                "entrySha256", "providerRoute", "backendAvailable", "immutableId", "observedAtUtc",
                "backendSha256", "sourceRef", "sourceSha256"}
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ModelIdentityError("serialized model identity observation fields are invalid")
    try:
        observed = value["observedAtUtc"]
        if not isinstance(observed, str):
            raise ValueError("timestamp must be text")
        timestamp = datetime.fromisoformat(observed.replace("Z", "+00:00"))
        if timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(timestamp):
            raise ValueError("timestamp must be UTC")
        result = ModelIdentityObservation(
            selector_kind=value["selectorKind"],
            configured_selector=value["configuredSelector"], reported_selector=value["reportedSelector"],
            effort=value["effort"], config_sha256=value["configSha256"], catalog_sha256=value["catalogSha256"],
            entry_sha256=value["entrySha256"], provider_route=value["providerRoute"],
            backend_available=value["backendAvailable"], immutable_id=value["immutableId"],
            backend_sha256=value["backendSha256"],
            observed_at_utc=timestamp, source_ref=value["sourceRef"], source_sha256=value["sourceSha256"])
    except (TypeError, ValueError, KeyError) as exc:
        raise ModelIdentityError("serialized model identity observation is malformed") from exc
    _text(result.configured_selector, "configured selector")
    if not isinstance(result.selector_kind, str) or result.selector_kind not in {"immutable-id", "provider-alias"}:
        raise ModelIdentityError("serialized selectorKind is unsupported")
    if result.reported_selector is not None:
        _text(result.reported_selector, "reported selector")
    _text(result.effort, "observed effort")
    for name, digest in (("config", result.config_sha256), ("catalog", result.catalog_sha256),
                         ("entry", result.entry_sha256), ("source", result.source_sha256)):
        _hash(digest, f"observed {name} SHA-256")
    _validate_route(result.provider_route)
    if type(result.backend_available) is not bool:
        raise ModelIdentityError("serialized backendAvailable must be boolean")
    if result.backend_available:
        _text(result.immutable_id, "observed immutable backend ID")
    elif result.immutable_id is not None:
        raise ModelIdentityError("unavailable backend identity must be null")
    if result.backend_sha256 is not None:
        _hash(result.backend_sha256, "observed backend SHA-256")
    _text(result.source_ref, "model identity source reference")
    return result


def _validate_identity_only(identity: Any) -> None:
    if not isinstance(identity, Mapping):
        raise ModelIdentityError("registered modelIdentity must be an object")
    # Use a harmless legacy model representation to apply the same discriminated contract.
    if identity.get("kind") == "observable-requested-route":
        model = {"name": identity.get("selector"), "version": None, "sha256": None}
    else:
        model = {"name": identity.get("selector"), "version": identity.get("immutableId"),
                 "sha256": identity.get("backendSha256")}
    route = identity.get("providerRoute")
    auth_method = route.get("authMethod") if isinstance(route, Mapping) else None
    host = {"chatgpt": "codex", "claude.ai": "claude-code"}.get(auth_method, "")
    validate_identity(identity, host=host, model=model)


def _validate_route(route: Any) -> None:
    if not isinstance(route, Mapping) or set(route) != {"provider", "accountSha256", "authMethod"}:
        raise ModelIdentityError("providerRoute must bind provider, account hash, and authentication method")
    _text(route.get("provider"), "providerRoute.provider")
    _hash(route.get("accountSha256"), "providerRoute.accountSha256")
    _text(route.get("authMethod"), "providerRoute.authMethod")


def _text(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value.encode("utf-8")) > 2048:
        raise ModelIdentityError(f"{label} must be nonempty bounded text")


def _hash(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ModelIdentityError(f"{label} must be lowercase SHA-256")


def canonical_json_sha256(value: Any) -> str:
    """Hash canonical UTF-8 JSON using sorted keys and compact separators."""
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def entry_sha256(value: Any) -> str:
    """Hash a complete retained native catalog entry as canonical JSON."""
    return canonical_json_sha256(value)


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, OverflowError, UnicodeError) as exc:
        raise ModelIdentityError("identity JSON must contain only finite UTF-8 values") from exc


def artifact_sha256(value: bytes) -> str:
    """Hash exact retained native catalog artifact bytes, without parsing them."""
    if not isinstance(value, bytes):
        raise ModelIdentityError("retained native catalog artifact must be bytes")
    return hashlib.sha256(value).hexdigest()


def _timestamp(value: Any, label: str) -> None:
    if not isinstance(value, str):
        raise ModelIdentityError(f"{label} must be a timezone-aware timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ModelIdentityError(f"{label} must be a timezone-aware timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ModelIdentityError(f"{label} must be a UTC timestamp")


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


__all__ = ["IDENTITY_KINDS", "ModelIdentityError", "ModelIdentityObservation", "check_observation",
           "artifact_sha256", "canonical_json_sha256", "entry_sha256", "observation_from_dict",
           "validate_identity"]
