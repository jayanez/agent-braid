# SPDX-License-Identifier: AGPL-3.0-only
"""Internal static verifier identity; neither dispatch nor execution authority.

The coordinator must pin the final extracted verifier source after the parallel
implementation join. Until then the production registry is unavailable. This
module has no registration API, plugin loader or caller-selected source path.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from hashlib import sha256
from pathlib import Path
import re

from .system_one import digest, freeze

_DOMAIN = "t024-eof-context-v1"
_IR_VERSION = "t024-literal-program-v1"
_OBSERVATION = "t024-path-blob-projection-v1"
_IMPLEMENTATION = "t024-eof-verifier-extracted-v1"
_IDENTITY_KEYS = frozenset({
    "domainId", "irVersion", "observationContract", "registryDigest", "verifierDigest",
})
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_MAX_SOURCE_BYTES = 1_048_576
_VERIFIER_SOURCE = Path(__file__).with_name("system_one_verified_ir.py")
# Serial coordinator integration replaces None with SHA-256 of final source bytes.
# Never fill this with a placeholder or a test fixture digest.
_PINNED_VERIFIER_SHA256: str | None = 'a0378c34b805387b0518cf6ebc3da05599976cb7f037d5f140c2571c8f362ea3'


def _entry(verifier_digest: str) -> Mapping[str, object]:
    return freeze({
        "domainId": _DOMAIN,
        "irVersion": _IR_VERSION,
        "observationContract": _OBSERVATION,
        "implementationId": _IMPLEMENTATION,
        "verifierDigest": verifier_digest,
    })


def _manifest(entry: Mapping[str, object]) -> Mapping[str, object]:
    return freeze({
        "format": "s1-static-verifier-registry-v1",
        "entries": [entry],
        "executionAuthorization": False,
    })


def _identity(identity: Mapping[str, object]) -> dict[str, str]:
    if not isinstance(identity, Mapping) or len(identity) != len(_IDENTITY_KEYS):
        raise ValueError("invalid-envelope")
    if set(identity) != _IDENTITY_KEYS:
        raise ValueError("invalid-envelope")
    result: dict[str, str] = {}
    for key in _IDENTITY_KEYS:
        value = identity[key]
        if type(value) is not str or not 1 <= len(value) <= 64:
            raise ValueError("invalid-envelope")
        if any(ord(char) < 32 or 127 <= ord(char) <= 159
               or 0xD800 <= ord(char) <= 0xDFFF for char in value):
            raise ValueError("invalid-envelope")
        if len(value.encode("utf-8")) > 64:
            raise ValueError("invalid-envelope")
        if key.endswith("Digest") and _HASH.fullmatch(value) is None:
            raise ValueError("invalid-envelope")
        result[key] = value
    return result


def resolve(identity: Mapping[str, object], *,
            checkpoint: Callable[[str, int], None]) -> Mapping[str, object]:
    """Resolve exactly the pinned local identity, returning an immutable entry.

    ``checkpoint`` is a trusted request-local dependency, never a wire field.
    Its exceptions propagate, including cancellation immediately before return.
    Unknown identities and unavailable/changed source pins are technical refusals,
    not semantic claims about a candidate plan.
    """
    checkpoint("verification", 0)
    admitted = _identity(identity)
    for key, expected, reason in (
        ("domainId", _DOMAIN, "unsupported-domain"),
        ("irVersion", _IR_VERSION, "unsupported-version"),
        ("observationContract", _OBSERVATION, "unsupported-observation"),
    ):
        if admitted[key] != expected:
            raise ValueError(reason)
    pin = _PINNED_VERIFIER_SHA256
    if type(pin) is not str or _HASH.fullmatch(pin) is None or pin == "0" * 64:
        raise ValueError("registry-mismatch")
    entry = _entry(pin)
    if admitted["registryDigest"] != digest(_manifest(entry)):
        raise ValueError("registry-mismatch")
    if admitted["verifierDigest"] != pin:
        raise ValueError("verifier-mismatch")
    checkpoint("verification", 0)
    try:
        with _VERIFIER_SOURCE.open("rb") as source:
            raw = source.read(_MAX_SOURCE_BYTES + 1)
    except OSError:
        raise ValueError("verifier-mismatch") from None
    if len(raw) > _MAX_SOURCE_BYTES or sha256(raw).hexdigest() != pin:
        raise ValueError("verifier-mismatch")
    checkpoint("verification", 0)
    return entry
