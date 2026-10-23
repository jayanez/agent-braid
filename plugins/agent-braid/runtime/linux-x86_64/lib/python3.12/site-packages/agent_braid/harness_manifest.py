# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Agent Braid modifications Copyright 2026 Juan Antonio Yáñez García.
# Adapted typed-view/identity scaffolding from harness2/core/spec.py:RunView
# and harness2/core/runmark.py:fingerprint at
# 1cfe254e8d25b15f37048c3730134686abe60335. Changes: original strict HAR schema,
# immutable complete SHA-256 bindings, independent consumer checks and a finite
# offline-only envelope; no upstream launcher, shortened hash or base sentinel.
"""Pure immutable offline harness manifests; no filesystem or execution authority.

Inventory digests bind declared metadata. The importer must independently check
the actual file bytes. Consumers reparse raw bytes with trusted expected hashes;
a caller-constructed view, producer digest or unknown host identity is no grant.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import re
import unicodedata
from typing import Any

from .system_one import InvalidDecision, canonical, digest, freeze, parse_json, thaw

FORMAT = "braid-harness-manifest/v0.1"
PROFILE = "offline-foundations"
MAX_BYTES = 1_048_576
DEFAULT_LIMITS = freeze({
    "maxManifestBytes": MAX_BYTES, "maxFiles": 32, "maxFileBytes": 32_768,
    "maxCandidateBytes": 262_144, "maxPathDepth": 4, "maxContextEntries": 16,
    "maxContextBytes": 131_072, "maxStageOutputBytes": 65_536,
    "maxJournalBytes": 8_388_608, "maxAdmissionSeconds": 300,
    "maxNativeSessions": 0, "maxModelSessions": 0, "maxChildProcesses": 0,
    "maxNetworkConnections": 0, "maxAdditionalCashMicros": 0,
    "maxAutomaticRetries": 0, "cashCurrency": "EUR",
})
_TOP = {"format", "profile", "source", "base", "candidate", "task", "context",
        "host", "tools", "policy", "verifier", "normalizer", "environment",
        "envelopeSha256", "allowedComponentPaths", "effects", "limits",
        "executionAuthorization"}
_SUBRECORDS = ("source", "base", "candidate", "task", "context", "host", "tools",
               "policy", "verifier", "normalizer", "environment")
BINDING_NAMES = frozenset((*_SUBRECORDS, "fixture", "envelope"))
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_COMMIT = re.compile(r"[0-9a-f]{40}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")


class ManifestError(ValueError):
    """A sanitized manifest or trusted consumer-binding failure."""

    def __init__(self, reason: str = "invalid-manifest"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-manifest") -> None:
    if not condition:
        raise ManifestError(reason)


def _keys(value: Any, fields: set[str]) -> None:
    _require(type(value) is dict and set(value) == fields)


def _hash(value: Any) -> None:
    _require(type(value) is str and _HASH.fullmatch(value) is not None)


def _identifier(value: Any) -> None:
    _require(type(value) is str and _ID.fullmatch(value) is not None)


def _integer(value: Any, maximum: int, *, minimum: int = 0) -> None:
    _require(type(value) is int and minimum <= value <= maximum, "invalid-budget")


def _path(value: Any, depth: int) -> None:
    _require(type(value) is str and 0 < len(value.encode("utf-8")) <= 512,
             "invalid-path")
    _require(unicodedata.normalize("NFC", value) == value and
             not any(unicodedata.category(c) in {"Cc", "Cf", "Cs"} for c in value) and
             not any(c in value for c in "\\:*?[]{}~"), "invalid-path")
    parts = value.split("/")
    _require(len(parts) <= depth and all(p not in {"", ".", ".."} for p in parts),
             "invalid-path")


def _ordered_unique(values: list[str], *, paths: bool = False) -> None:
    _require(values == sorted(values) and len(set(values)) == len(values),
             "duplicate-or-unordered-inventory")
    if paths:
        _require(len({v.casefold() for v in values}) == len(values), "path-alias")


def _inventory(value: Any, limits: dict, *, source: bool = False) -> list[str]:
    _require(type(value) is list and int(source) <= len(value) <= limits["maxFiles"],
             "inventory-budget-exceeded")
    paths, total = [], 0
    for row in value:
        _keys(row, {"path", "sha256", "sizeBytes", "origin"} if source else
              {"path", "sha256", "sizeBytes"})
        _path(row["path"], limits["maxPathDepth"])
        _hash(row["sha256"])
        _integer(row["sizeBytes"], limits["maxFileBytes"])
        if source:
            _require(type(row["origin"]) is str and row["origin"] in {"committed", "uncommitted"})
        paths.append(row["path"])
        total += row["sizeBytes"]
    _ordered_unique(paths, paths=True)
    _require(total <= limits["maxCandidateBytes"], "inventory-budget-exceeded")
    return paths


def _limits(value: Any, raw_size: int) -> None:
    _keys(value, set(DEFAULT_LIMITS))
    _require(value["cashCurrency"] == "EUR", "unsupported-profile")
    for key, maximum in DEFAULT_LIMITS.items():
        if key != "cashCurrency":
            _integer(value[key], maximum, minimum=0 if maximum == 0 else 1)
    _require(raw_size <= value["maxManifestBytes"], "input-budget-exceeded")
    _require(value["maxFileBytes"] <= value["maxCandidateBytes"], "invalid-budget")


def _validate(value: dict, raw_size: int) -> None:
    _keys(value, _TOP)
    _require(value["format"] == FORMAT, "unsupported-version")
    _require(value["profile"] == PROFILE and value["executionAuthorization"] is False,
             "unsupported-profile")
    limits = value["limits"]
    _limits(limits, raw_size)
    source = value["source"]
    _keys(source, {"commit", "selectedInputs"})
    _require(type(source["commit"]) is str and _COMMIT.fullmatch(source["commit"]) is not None)
    source_paths = _inventory(source["selectedInputs"], limits, source=True)
    inventory_paths = {"source": source_paths}
    allowed = value["allowedComponentPaths"]
    _require(type(allowed) is list and 1 <= len(allowed) <= limits["maxFiles"])
    for path in allowed:
        _path(path, limits["maxPathDepth"])
    _ordered_unique(allowed, paths=True)
    for name in ("base", "candidate"):
        record = value[name]
        _keys(record, {"sha256", "files"})
        _hash(record["sha256"])
        paths = _inventory(record["files"], limits)
        inventory_paths[name] = paths
        _require(set(paths) <= set(allowed), "path-outside-surface")
        _require(record["sha256"] == digest(record["files"]), "inventory-digest-mismatch")
    task = value["task"]
    _keys(task, {"id", "inputSha256", "fixtureSha256"})
    _identifier(task["id"])
    _hash(task["inputSha256"])
    _hash(task["fixtureSha256"])
    context = value["context"]
    _require(type(context) is list and len(context) <= limits["maxContextEntries"])
    context_ids, context_paths, context_bytes = [], [], 0
    for row in context:
        _keys(row, {"id", "path", "sha256", "sizeBytes", "trust", "selected"})
        _identifier(row["id"])
        _path(row["path"], limits["maxPathDepth"])
        _hash(row["sha256"])
        _integer(row["sizeBytes"], limits["maxContextBytes"])
        _require(type(row["trust"]) is str and row["trust"] in {"trusted-task", "untrusted-evidence"} and
                 type(row["selected"]) is bool)
        context_ids.append(row["id"])
        context_paths.append(row["path"])
        context_bytes += row["sizeBytes"]
    _require(len(set(context_ids)) == len(context_ids) and
             len({p.casefold() for p in context_paths}) == len(context_paths),
             "duplicate-context")
    _require(context_bytes <= limits["maxContextBytes"], "context-budget-exceeded")
    host = value["host"]
    _keys(host, {"kind", "executableSha256", "build", "requested", "observed"})
    _require(host["kind"] == "offline" and host["executableSha256"] is None and
             host["build"] is None, "unsupported-profile")
    _keys(host["requested"], {"model", "effort", "route"})
    _require(host["requested"] == {"model": None, "effort": None, "route": "offline"},
             "unsupported-profile")
    _keys(host["observed"], {"provider", "model", "build", "route"})
    _require(all(v is None for v in host["observed"].values()), "unsupported-profile")
    tools = value["tools"]
    _require(type(tools) is list and len(tools) <= limits["maxFiles"])
    tool_ids = []
    for row in tools:
        _keys(row, {"id", "sha256"})
        _identifier(row["id"])
        _hash(row["sha256"])
        tool_ids.append(row["id"])
    _ordered_unique(tool_ids)
    for name in ("policy", "verifier", "normalizer"):
        _keys(value[name], {"version", "sha256"})
        _identifier(value[name]["version"])
        _hash(value[name]["sha256"])
    environment = value["environment"]
    _keys(environment, {"os", "architecture", "sha256", "outputDestinationSha256"})
    _identifier(environment["os"])
    _identifier(environment["architecture"])
    _hash(environment["sha256"])
    _hash(environment["outputDestinationSha256"])
    _hash(value["envelopeSha256"])
    effects = value["effects"]
    _keys(effects, {"read", "write", "delete"})
    inventory_paths["context"] = context_paths
    readable = {namespace + "/" + path for namespace, paths in inventory_paths.items()
                for path in paths}
    for kind, resources in effects.items():
        maximum = len(readable) if kind == "read" else 2 * limits["maxFiles"]
        _require(type(resources) is list and len(resources) <= maximum)
        for resource in resources:
            _require(type(resource) is str and "/" in resource, "invalid-resource")
            namespace, path = resource.split("/", 1)
            _path(path, limits["maxPathDepth"])
            _require(resource in readable if kind == "read" else
                     namespace == "lab" and path in value["allowedComponentPaths"],
                     "effect-outside-inventory")
        _ordered_unique(resources, paths=True)


@dataclass(frozen=True)
class HarnessManifest:
    """Immutable parsed view; construction is not independent verification."""

    data: Mapping[str, Any]
    canonical_bytes: bytes
    bindings: Mapping[str, str]

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    def to_dict(self) -> dict:
        """Return an independent mutable copy of the validated wire record."""
        return thaw(self.data)


def parse_manifest(raw: bytes) -> HarnessManifest:
    """Parse strict bounded UTF-8 JSON and validate the finite offline profile."""
    try:
        value = parse_json(raw)
    except InvalidDecision as exc:
        raise ManifestError("input-budget-exceeded" if exc.reason == "input-budget-exceeded"
                            else "invalid-json") from None
    _validate(value, len(raw))
    bindings = {name: digest(value[name]) for name in _SUBRECORDS}
    bindings.update(fixture=value["task"]["fixtureSha256"], envelope=value["envelopeSha256"])
    return HarnessManifest(freeze(value), canonical(value), freeze(bindings))


def verify_manifest(raw: bytes, *, expected_sha256: str,
                    expected_bindings: Mapping[str, str]) -> HarnessManifest:
    """Independently reparse and compare trusted complete/named identities.

    Expected hashes must come from the consumer's trusted observations. Matching
    hashes establish byte identity, never source rights, containment or authority.
    """
    _hash(expected_sha256)
    _require(isinstance(expected_bindings, Mapping), "invalid-expected-bindings")
    expected = dict(expected_bindings)
    _require(set(expected) <= BINDING_NAMES, "invalid-expected-bindings")
    for value in expected.values():
        _hash(value)
    manifest = parse_manifest(raw)
    _require(manifest.sha256 == expected_sha256, "manifest-drift")
    _require(all(manifest.bindings[name] == value for name, value in expected.items()),
             "binding-drift")
    return manifest
