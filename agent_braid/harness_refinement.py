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
# Adapted the propose/probe/compose stage structure with fallback from
# harness2/core/recursion.py (Stage, _run_stage, run_sequential) and the candidate
# comparison that includes the unchanged base from
# harness2/core/selection.py (assign_ids, selection_pool) at
# 1cfe254e8d25b15f37048c3730134686abe60335. Changes: one fixed round, injected
# proposer/prober callbacks instead of model sessions or thread pools, a frozen
# hash-bound selection policy, explicit keep-base/inconclusive/refused outcomes,
# strict untrusted-output validation, protected-surface checks reused from
# harness_surface, and no reflection/adoption-by-output-presence step.
"""One-round general/task-specific propose-probe-compose with keep-base selection.

Pure and offline. The module dispatches nothing: a trusted caller supplies a
proposer (untrusted text/bytes in) and a prober (an independent verifier's score
out). Every proposal is validated against the protected guidance surface before
it is probed, every probe is spent from the frozen budget, and the unchanged base
always competes. The selection policy is parsed from raw bytes and bound to the
manifest's policy hash; no proposal, rationale or score can carry or alter it.
The decision is advisory evidence with ``executionAuthorization`` false.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from types import MappingProxyType
from typing import Any
import re

from .harness_manifest import HarnessManifest
# _text is private to harness_surface; coupled deliberately so proposal text uses the
# exact same encoding/executable checks as candidate import.
from .harness_surface import SurfaceError, SurfaceSpec, _text
from .system_one import InvalidDecision, canonical, digest, freeze, parse_json, thaw

POLICY_FORMAT = "braid-harness-selection-policy/v0.1"
DECISION_FORMAT = "braid-harness-refinement-decision/v0.1"
UPSTREAM_REVISION = "1cfe254e8d25b15f37048c3730134686abe60335"
SCOPES = ("general", "task")
MAX_POLICY_BYTES = 4096
MAX_RATIONALE_BYTES = 2048
MAX_SCORE = 1_000_000
MAX_PROBES = 4  # base, one general probe, one task probe, one composed probe
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_TERMINALS = ("completed", "failed", "interrupted", "refused")
_PROPOSAL_KEYS = {"parentManifestSha256", "scope", "changes", "rationale"}
_OUTPUT_KEYS = {"terminal", "score", "observationSha256"}
_UNOBSERVED = {"unscored", "missing", "invalid", "failed", "interrupted", "refused",
               "not-probed"}
_PROVENANCE = {
    "upstreamRevision": UPSTREAM_REVISION,
    "adapted": [
        "core/recursion.py: Stage/_run_stage propose-probe-compose with fallback",
        "core/selection.py: assign_ids/selection_pool candidate comparison including base (labels are not blinding)",
    ],
    "changes": "one fixed round; injected callbacks; frozen hash-bound policy; "
               "keep-base/inconclusive/refused; strict output validation; no reflection",
}


class RefinementError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-request"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-request") -> None:
    if not condition:
        raise RefinementError(reason)


def _int(value: Any, low: int, high: int) -> bool:
    return type(value) is int and low <= value <= high


# --- protected selection policy ---------------------------------------------------------


@dataclass(frozen=True)
class SelectionPolicy:
    """Frozen selection rules; construction is not verification (see ``parse_policy``)."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def margin_micros(self) -> int:
        return self.data["marginMicros"]

    @property
    def max_probes(self) -> int:
        return self.data["maxProbes"]


def parse_policy(raw: bytes, *, manifest: HarnessManifest) -> SelectionPolicy:
    """Strictly parse a policy and bind it to the manifest's policy identity."""
    _require(isinstance(manifest, HarnessManifest))
    _require(type(raw) is bytes and len(raw) <= MAX_POLICY_BYTES, "invalid-policy")
    try:
        value = parse_json(raw)
    except InvalidDecision:
        raise RefinementError("invalid-policy") from None
    ok = (type(value) is dict and set(value) == {"format", "version", "marginMicros", "maxProbes"}
          and value["format"] == POLICY_FORMAT
          and type(value["version"]) is str and _ID.fullmatch(value["version"]) is not None
          and _int(value["marginMicros"], 1, MAX_SCORE) and _int(value["maxProbes"], 1, MAX_PROBES))
    _require(ok, "invalid-policy")
    policy = SelectionPolicy(freeze(value), canonical(value))
    bound = manifest.data["policy"]
    _require(policy.sha256 == bound["sha256"] and value["version"] == bound["version"],
             "policy-drift")
    return policy


# --- proposals and candidates ----------------------------------------------------------


@dataclass(frozen=True)
class ProbeRequest:
    """What a prober may see: identity and exact changes, never policy or rationale."""

    scope: str
    candidate_sha256: str
    changes: Mapping[str, bytes]


def _surface(manifest: HarnessManifest) -> SurfaceSpec:
    limits = manifest.data["limits"]
    return SurfaceSpec(tuple(manifest.data["allowedComponentPaths"]), limits["maxFiles"],
                       limits["maxFileBytes"], limits["maxCandidateBytes"],
                       limits["maxPathDepth"])


def _candidate_hash(manifest: HarnessManifest, changes: Mapping[str, bytes]) -> tuple[str | None, str]:
    """Hash of the base inventory overlaid with ``changes``; or (None, reason)."""
    rows = {row["path"]: dict(row) for row in manifest.data["base"]["files"]}
    for path, content in changes.items():
        rows[path] = {"path": path, "sha256": sha256(content).hexdigest(), "sizeBytes": len(content)}
    limits = manifest.data["limits"]
    if len(rows) > limits["maxFiles"] or sum(r["sizeBytes"] for r in rows.values()) \
            > limits["maxCandidateBytes"]:
        return None, "candidate-too-large"
    return digest([rows[p] for p in sorted(rows)]), ""


def _copy(value: Any) -> dict | None:
    """Copy an untrusted mapping into a plain dict; hostile behaviour yields None.

    The only broad catch: it runs untrusted code (``keys``/``__getitem__``/``__iter__``).
    Everything after it operates on plain builtins, so our own bugs still propagate.
    """
    if not isinstance(value, Mapping):
        return None
    try:
        return dict(value)
    except Exception:
        return None


def _validate_proposal(value: Any, scope: str, manifest: HarnessManifest) -> tuple[dict | None, str]:
    """Return (changes, "") for a valid proposal or (None, fixed reason)."""
    wire = _copy(value)
    if wire is None:
        return None, "invalid-proposal"
    if set(wire) != _PROPOSAL_KEYS:
        return None, "unexpected-field" if set(wire) > _PROPOSAL_KEYS else "invalid-proposal"
    if wire["parentManifestSha256"] != manifest.sha256:
        return None, "wrong-parent"
    if wire["scope"] != scope:
        return None, "wrong-scope"
    rationale = wire["rationale"]
    try:
        bounded = type(rationale) is str and len(rationale) <= MAX_RATIONALE_BYTES \
            and len(rationale.encode("utf-8")) <= MAX_RATIONALE_BYTES
    except UnicodeEncodeError:  # lone surrogate
        bounded = False
    if not bounded:
        return None, "invalid-rationale"  # untrusted text is bounded, then discarded
    changes = _copy(wire["changes"])
    if changes is None:
        return None, "invalid-changes"
    limits = manifest.data["limits"]
    if not changes:
        return None, "empty-changes"
    if len(changes) > limits["maxFiles"] or not all(
            type(k) is str and type(v) is bytes for k, v in changes.items()):
        return None, "invalid-changes"
    spec = _surface(manifest)
    try:
        for path, content in changes.items():
            spec.validate_path(path)
            if len(content) > limits["maxFileBytes"]:
                return None, "file-too-large"
            _text(content)
    except SurfaceError as exc:
        return None, exc.reason
    candidate, reason = _candidate_hash(manifest, changes)
    if candidate is None:
        return None, reason
    if candidate == manifest.data["base"]["sha256"]:
        return None, "no-op"
    return changes, ""


def _compose(manifest: HarnessManifest, first: Mapping[str, bytes],
             second: Mapping[str, bytes]) -> tuple[dict | None, str]:
    for path in first.keys() & second.keys():
        if first[path] != second[path]:
            return None, "composition-conflict"
    merged = {**first, **second}
    candidate, reason = _candidate_hash(manifest, merged)
    return (merged, "") if candidate is not None else (None, "composition-too-large")



def _outcome(output: Any) -> dict:
    """Normalize an untrusted prober result into a fixed-shape attempt outcome."""
    if output is None:
        return {"status": "missing", "reason": "no-output"}
    wire = _copy(output) or {}
    ok = (set(wire) == _OUTPUT_KEYS and wire["terminal"] in _TERMINALS
          and (wire["score"] is None or (_int(wire["score"], 0, MAX_SCORE)
                                         and wire["terminal"] == "completed"))
          and type(wire["observationSha256"]) is str
          and _HASH.fullmatch(wire["observationSha256"]) is not None)
    if not ok:
        return {"status": "invalid", "reason": "invalid-output"}
    score = wire["score"]
    status = "scored" if score is not None else \
        "unscored" if wire["terminal"] == "completed" else wire["terminal"]
    return {"status": status, "reason": None, "score": score,
            "observationSha256": wire["observationSha256"]}


# --- decision record ---------------------------------------------------------------------


@dataclass(frozen=True)
class RefinementDecision:
    """Immutable advisory decision; ``sha256`` binds its canonical bytes."""

    data: Mapping[str, Any]
    canonical_bytes: bytes

    @property
    def sha256(self) -> str:
        return sha256(self.canonical_bytes).hexdigest()

    @property
    def executionAuthorization(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return thaw(self.data)


class _Round:
    """Mutable bookkeeping for one round; never exposed to callbacks."""

    def __init__(self, manifest: HarnessManifest, policy: SelectionPolicy, probe: Callable):
        self.manifest, self.policy, self.callback = manifest, policy, probe
        self.attempts: list[dict] = []
        self.losses: set[str] = set()
        self.probes = 0

    def record(self, scope: str, candidate: str | None, status: str,
               reason: str | None = None, **extra: Any) -> dict:
        attempt = {"scope": scope, "candidateSha256": candidate, "status": status,
                   "reason": reason, "score": None, "deltaMicros": None, "regressed": None,
                   "observationSha256": None, **extra}
        self.attempts.append(attempt)
        return attempt

    def probe(self, scope: str, candidate: str, changes: Mapping[str, bytes]) -> dict:
        """Spend one probe, or record that the frozen budget cannot admit it."""
        if self.probes >= self.policy.max_probes:
            self.losses.add("budget-exhausted")
            return self.record(scope, candidate, "not-probed", "budget-exhausted")
        self.probes += 1
        request = ProbeRequest(scope, candidate, MappingProxyType(dict(changes)))
        try:
            outcome = _outcome(self.callback(request))
        except Exception:  # untrusted prober: surface a fixed reason only
            outcome = {"status": "missing", "reason": "probe-failed"}
        return self.record(scope, candidate, outcome["status"], outcome["reason"],
                           score=outcome.get("score"),
                           observationSha256=outcome.get("observationSha256"))



def _scored(attempt: dict | None) -> bool:
    return attempt is not None and attempt["status"] == "scored"


def _collect_proposals(state: _Round, propose: Callable[[str], Any], seen: set[str]
                       ) -> tuple[list[tuple[str, str, dict]], int, int]:
    """Ask the proposer per scope; record abstentions/rejections; return valid ones."""
    manifest = state.manifest
    valid: list[tuple[str, str, dict]] = []
    abstentions = rejections = 0
    for scope in SCOPES:
        try:
            proposed = propose(scope)
        except Exception:  # untrusted proposer: surface a fixed reason only
            state.record(scope, None, "missing", "proposer-failed")
            continue
        if proposed is None:
            abstentions += 1
            state.record(scope, None, "abstained")
            continue
        changes, reason = _validate_proposal(proposed, scope, manifest)
        candidate = _candidate_hash(manifest, changes)[0] if changes else None
        if changes is not None and candidate in seen:
            changes, reason = None, "duplicate-candidate"
        if changes is None:
            rejections += 1
            state.record(scope, None, "rejected", reason)
            continue
        seen.add(candidate)
        valid.append((scope, candidate, changes))
    return valid, abstentions, rejections


def _decide(attempts: list[dict], base: dict, margin: int, abstentions: int
            ) -> tuple[str, list[str], str | None]:
    """Select from the probed attempts against the base; also fills delta/regressed."""
    candidates = [a for a in attempts if a["scope"] != "base" and a["candidateSha256"]]
    for attempt in candidates:
        if attempt["score"] is not None:
            attempt["deltaMicros"] = attempt["score"] - base["score"]
            attempt["regressed"] = attempt["deltaMicros"] < 0
    scored = [a for a in candidates if a["status"] == "scored"]
    if scored:
        best = max(a["score"] for a in scored)
        top = [a for a in scored if a["score"] == best]
        if best - base["score"] < margin:
            return "keep-base", ["no-candidate-beats-base"], None
        if len(top) > 1:
            return "inconclusive", ["top-tied"], None
        return "candidate", ["improved-over-base"], top[0]["candidateSha256"]
    if any(a["status"] in _UNOBSERVED for a in attempts if a["scope"] != "base"):
        return "inconclusive", ["no-scored-candidate"], None
    if abstentions == len(SCOPES):
        return "keep-base", ["all-abstained"], None
    return "keep-base", ["no-valid-candidate"], None


def run_round(manifest: HarnessManifest, policy: SelectionPolicy, *,
              propose: Callable[[str], Any], probe: Callable[[ProbeRequest], Any]
              ) -> RefinementDecision:
    """Run one propose-probe-compose round and select candidate, keep-base, inconclusive
    or refused under the frozen policy. Invalid arguments raise ``RefinementError``."""
    _require(isinstance(manifest, HarnessManifest) and isinstance(policy, SelectionPolicy)
             and callable(propose) and callable(probe))
    policy = parse_policy(policy.canonical_bytes, manifest=manifest)  # re-verify, never trust
    state = _Round(manifest, policy, probe)
    base_hash = manifest.data["base"]["sha256"]
    margin = policy.margin_micros

    base = state.probe("base", base_hash, {})
    abstentions = rejections = 0
    if base["status"] == "refused":
        decision, reasons, chosen = "refused", ["base-refused"], None
    elif not _scored(base):
        decision, reasons, chosen = "inconclusive", ["base-unscored"], None
    else:
        seen = {base_hash}
        valid, abstentions, rejections = _collect_proposals(state, propose, seen)
        results = {scope: (state.probe(scope, candidate, changes), changes)
                   for scope, candidate, changes in valid}
        if len(results) == len(SCOPES) and all(
                _scored(a) and a["score"] - base["score"] >= margin for a, _ in results.values()):
            merged, reason = _compose(manifest, results["general"][1], results["task"][1])
            candidate = _candidate_hash(manifest, merged)[0] if merged else None
            if merged is None:
                state.losses.add(reason)
            elif candidate in seen:
                state.losses.add("composition-duplicate")
            else:
                state.probe("composed", candidate, merged)
        decision, reasons, chosen = _decide(state.attempts, base, margin, abstentions)

    # Deterministic labels over every attempt, base included. These are stable
    # identifiers, not blinding: each attempt keeps its scope and candidate hash.
    keyed = sorted(state.attempts, key=lambda a: sha256(
        f"{policy.sha256}:{a['candidateSha256'] or a['scope']}".encode()).hexdigest())
    for number, attempt in enumerate(keyed, 1):
        attempt["id"] = f"c{number}"
    record = {
        "format": DECISION_FORMAT, "manifestSha256": manifest.sha256,
        "policySha256": policy.sha256, "baseSha256": base_hash, "marginMicros": margin,
        "decision": decision, "reasons": reasons, "chosenCandidateSha256": chosen,
        "attempts": keyed,
        "counts": {"probes": state.probes, "maxProbes": policy.max_probes,
                   "abstentions": abstentions, "rejections": rejections},
        "losses": sorted(state.losses), "provenance": _PROVENANCE,
        "executionAuthorization": False}
    return RefinementDecision(freeze(record), canonical(record))
