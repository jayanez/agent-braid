# SPDX-License-Identifier: AGPL-3.0-only
"""Quarantined, scoped, revocable experience store; offline, deterministic, no authority.

Lessons are generated automatically from observed contrasts but start quarantined.
Automated validation can reach ``validated`` and never ``active``: activation needs an
explicit candidate-bound human decision record. A query for an online task returns only
active entries whose evidence, validation and activation all predate the task, whose
domain, source, host, tool set and policy match exactly, and whose evidence is neither
stale, expired, contradicted nor revoked. Lesson text is untrusted inert data; the
screen below is a conservative denylist and is not a semantic-safety guarantee.

The store is persistent: every operation returns a new store, so a prior store value is
a rollback point. Time is a caller-supplied integer tick; nothing here reads a clock,
file, host or model. ``executionAuthorization`` is always false.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from hashlib import sha256
import re
from types import MappingProxyType
from typing import Any
import unicodedata

from .system_one import InvalidDecision, canonical, digest, freeze, parse_json, thaw

ENTRY_FORMAT = "braid-harness-experience-entry/v0.1"
STORE_FORMAT = "braid-harness-experience-store/v0.1"
DECISION_FORMAT = "braid-harness-experience-decision/v0.1"
MAX_ENTRIES = 256
MAX_EVIDENCE = 16
MAX_HISTORY = 64
MAX_CUE = 160
MAX_LESSON = 512
MAX_TICK = 1 << 40
KINDS = ("positive", "negative", "inconclusive")
STATES = ("proposed", "quarantined", "validated", "active", "revoked", "expired")
TERMINAL = frozenset({"revoked", "expired"})
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}\Z")
# event -> (allowed previous states, resulting state); None previous means creation.
_TRANSITIONS = {
    "generated": ((None,), "proposed"),
    "screened": (("proposed",), "quarantined"),
    "validated": (("quarantined",), "validated"),
    "activated": (("validated",), "active"),
    "rolled-back": (("active",), "validated"),
    "revoked": (("proposed", "quarantined", "validated", "active"), "revoked"),
    "expired": (("quarantined", "validated", "active"), "expired"),
    "revalidated": (("validated", "active"), None),
    "evidence-added": (("quarantined", "validated", "active"), None),
}
_FORBIDDEN_CHARS = frozenset("`<>{}[]$\\|;")
_POISON = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\b(ignore|disregard|override|forget|bypass|skip)\b",
    r"\b(system|assistant|developer|user|human)\s*:",
    r"\b(you must|you should|always|never)\b",
    r"\b(approve[ds]?|activate[ds]?|grant(ed)?|authori[sz]e[ds]?|permission|sudo|exec(ute)?|eval|"
    r"chmod|curl|wget|rm\s+-rf|disable[ds]?)\b",
    r"\b(instructions?|prompt|policy|policies|tool call|credential)s?\b",
    r"(https?|file|ftp)://|www\.",
    r"\b(sk-|ghp_|akia|api[_ -]?key|password|secret|token)",
))


class ExperienceError(ValueError):
    """Sanitized refusal carrying a fixed reason code only."""

    def __init__(self, reason: str = "invalid-entry"):
        self.reason = reason
        super().__init__(reason)


def _require(condition: bool, reason: str = "invalid-entry") -> None:
    if not condition:
        raise ExperienceError(reason)


def _hash(value: Any) -> bool:
    return type(value) is str and _HASH.fullmatch(value) is not None


def _id(value: Any) -> bool:
    return type(value) is str and _ID.fullmatch(value) is not None


def _tick(value: Any) -> bool:
    return type(value) is int and 0 <= value < MAX_TICK


def _optional(value: Any, check) -> bool:
    return value is None or check(value)


def _exact(value: Any, keys: set[str], reason: str = "invalid-entry") -> None:
    _require(type(value) is dict and set(value) == keys, reason)


def screen_text(text: Any, limit: int) -> str:
    """Return ``text`` when it is plain bounded descriptive prose; refuse otherwise."""
    _require(type(text) is str and 0 < len(text.encode("utf-8", "surrogatepass")) <= limit,
             "invalid-text")
    _require(text == text.strip() and unicodedata.normalize("NFKC", text) == text
             and all(unicodedata.category(c)[0] not in "CZ" or c == " " for c in text)
             and not _FORBIDDEN_CHARS.intersection(text), "invalid-text")
    _require(not any(p.search(text) for p in _POISON), "poisoned-text")
    return text


def _content(d: Mapping) -> dict:
    return {k: d[k] for k in ("id", "kind", "cue", "lesson", "applicability", "provenance")}


def _check_decision(decision: Any, entry: Mapping, *, exact: bool) -> None:
    _exact(decision, {"format", "actor", "entryId", "contentSha256", "decision",
                      "evidenceSha256s", "decidedAt", "rollbackTarget", "executionAuthorization"},
           "invalid-decision")
    actor = decision["actor"]
    _exact(actor, {"kind", "id"}, "invalid-decision")
    _require(decision["format"] == DECISION_FORMAT and _id(actor["id"]) and _tick(decision["decidedAt"])
             and decision["executionAuthorization"] is False
             and decision["rollbackTarget"] == "validated", "invalid-decision")
    _require(actor["kind"] == "human", "not-human-decision")
    _require(decision["decision"] == "approved", "decision-not-approved")
    _require(decision["entryId"] == entry["id"] and decision["contentSha256"] == digest(_content(entry)),
             "decision-entry-mismatch")
    covered = decision["evidenceSha256s"]
    _require(type(covered) is list and covered == sorted(set(covered)) and all(map(_hash, covered)),
             "invalid-decision")
    current = {row["sha256"] for row in entry["evidence"]}
    _require(set(covered) == current if exact else set(covered) <= current, "decision-evidence-mismatch")


def _validate_entry(d: Any) -> None:
    _exact(d, {"format", "id", "kind", "cue", "lesson", "applicability", "provenance", "evidence",
               "expiresAt", "revalidateAfter", "state", "validatedAt", "activation", "history",
               "executionAuthorization"})
    _require(d["format"] == ENTRY_FORMAT and d["executionAuthorization"] is False
             and _id(d["id"]) and d["kind"] in KINDS and d["state"] in STATES)
    screen_text(d["cue"], MAX_CUE)
    screen_text(d["lesson"], MAX_LESSON)
    app = d["applicability"]
    _exact(app, {"domain", "sourceSha256", "host", "toolSetSha256", "policySha256"})
    _require(_id(app["domain"]) and _id(app["host"])
             and all(_hash(app[k]) for k in ("sourceSha256", "toolSetSha256", "policySha256")))
    prov = d["provenance"]
    _exact(prov, {"producer", "sourceRecordSha256", "generatedAt"})
    _require(_id(prov["producer"]) and _hash(prov["sourceRecordSha256"]) and _tick(prov["generatedAt"]))
    rows = d["evidence"]
    _require(type(rows) is list and 1 <= len(rows) <= MAX_EVIDENCE)
    for row in rows:
        _exact(row, {"sha256", "observedAt", "polarity"})
        _require(_hash(row["sha256"]) and _tick(row["observedAt"])
                 and row["polarity"] in ("supporting", "contrary"))
    _require(len({row["sha256"] for row in rows}) == len(rows))
    _require(_optional(d["expiresAt"], _tick) and _optional(d["validatedAt"], _tick)
             and _optional(d["revalidateAfter"], lambda v: type(v) is int and 1 <= v < MAX_TICK))
    history = d["history"]
    _require(type(history) is list and 2 <= len(history) <= MAX_HISTORY)
    state, last = None, 0
    for index, event in enumerate(history):
        _exact(event, {"seq", "event", "from", "to", "at", "reason"})
        previous, result = _TRANSITIONS.get(event["event"], ((), None))
        result = result or state
        _require(event["seq"] == index and state in previous and event["from"] == state
                 and event["to"] == result and _tick(event["at"]) and event["at"] >= last
                 and _optional(event["reason"], _id), "invalid-history")
        state, last = result, event["at"]
    _require(state == d["state"] and prov["generatedAt"] <= history[0]["at"]
             and all(row["observedAt"] <= last for row in rows), "invalid-history")
    validated = [e["at"] for e in history if e["event"] in ("validated", "revalidated")]
    _require((d["validatedAt"] is None) == (not validated)
             and (not validated or d["validatedAt"] == validated[-1]), "invalid-history")
    _require((d["activation"] is not None) == (state == "active"), "invalid-activation")
    if state == "active":
        _check_decision(d["activation"], d, exact=False)
        activated = [e for e in history if e["event"] == "activated"][-1]
        _require(d["activation"]["decidedAt"] == activated["at"], "invalid-activation")


@dataclass(frozen=True)
class Entry:
    """Immutable validated entry; ``sha256`` binds its canonical bytes including history."""

    data: Mapping[str, Any]

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def state(self) -> str:
        return self.data["state"]

    @property
    def sha256(self) -> str:
        return digest(self.data)

    @property
    def content_sha256(self) -> str:
        return digest(_content(self.data))

    @property
    def executionAuthorization(self) -> bool:
        return False

    def to_dict(self) -> dict:
        return thaw(self.data)


def _entry(d: dict) -> Entry:
    try:
        canonical(d)
    except (TypeError, ValueError, RecursionError):
        raise ExperienceError("invalid-entry") from None
    _validate_entry(d)
    return Entry(freeze(d))


@dataclass(frozen=True)
class QueryResult:
    """Lessons an online task may read as inert advisory data, plus audit exclusions."""

    served: tuple[Mapping[str, Any], ...]
    excluded: tuple[tuple[str, str], ...]

    @property
    def executionAuthorization(self) -> bool:
        return False


_PROPOSAL_KEYS = {"id", "kind", "cue", "lesson", "applicability", "provenance", "evidence",
                  "expiresAt", "revalidateAfter"}
_CONTEXT_KEYS = {"taskStartedAt", "domain", "sourceSha256", "host", "toolSetSha256", "policySha256"}
_MISMATCH = (("domain", "domain", "domain-mismatch"), ("sourceSha256", "sourceSha256", "source-mismatch"),
             ("host", "host", "host-mismatch"), ("toolSetSha256", "toolSetSha256", "tool-mismatch"),
             ("policySha256", "policySha256", "policy-mismatch"))


def _event(d: dict, name: str, at: int, reason: str | None = None) -> None:
    _require(_tick(at) and at >= d["history"][-1]["at"], "time-regression")
    state = d["state"]
    result = _TRANSITIONS[name][1] or state
    d["history"].append({"seq": len(d["history"]), "event": name, "from": state, "to": result,
                         "at": at, "reason": reason})
    d["state"] = result


def _contradicted(d: Mapping) -> bool:
    return any(row["polarity"] == "contrary" for row in d["evidence"])


def _stale(d: Mapping, now: int) -> bool:
    after = d["revalidateAfter"]
    return after is not None and d["validatedAt"] is not None and now > d["validatedAt"] + after


def _expired(d: Mapping, now: int) -> bool:
    return d["expiresAt"] is not None and now >= d["expiresAt"]


class ExperienceStore:
    """Immutable, id-sorted collection of entries; every operation returns a new store."""

    def __init__(self, entries: tuple[Entry, ...] = ()):
        _require(len(entries) <= MAX_ENTRIES and [e.id for e in entries] == sorted({e.id for e in entries}),
                 "invalid-store")
        self._entries = tuple(entries)

    @property
    def entries(self) -> tuple[Entry, ...]:
        return self._entries

    def get(self, entry_id: str) -> Entry:
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        raise ExperienceError("unknown-entry")

    def _with(self, *changed: Entry) -> "ExperienceStore":
        by_id = {e.id: e for e in self._entries}
        by_id.update({e.id: e for e in changed})
        return ExperienceStore(tuple(by_id[k] for k in sorted(by_id)))

    def _change(self, entry_id: str, at: int, event: str, reason: str | None = None,
                mutate=None) -> "ExperienceStore":
        d = self.get(entry_id).to_dict()
        _require(d["state"] not in TERMINAL, "terminal-entry")
        _require(d["state"] in _TRANSITIONS[event][0], "invalid-transition")
        if mutate is not None:
            mutate(d)
        _event(d, event, at, reason)
        return self._with(_entry(d))

    # --- automatic generation ------------------------------------------------------

    def add(self, proposal: Any, at: int) -> "ExperienceStore":
        """Quarantine a generated lesson; proposals cannot carry state, history or activation."""
        _exact(proposal, _PROPOSAL_KEYS)
        _require(len(self._entries) < MAX_ENTRIES and all(e.id != proposal["id"] for e in self._entries),
                 "duplicate-entry")
        d = thaw(proposal) | {"format": ENTRY_FORMAT, "state": "proposed", "validatedAt": None,
                              "activation": None, "history": [], "executionAuthorization": False}
        _require(type(proposal["evidence"]) is list, "invalid-entry")
        _require(_tick(at), "invalid-entry")
        d["history"] = [{"seq": 0, "event": "generated", "from": None, "to": "proposed", "at": at,
                         "reason": None}]
        _event(d, "screened", at)
        return self._with(_entry(d))

    # --- automated validation (never activates) ------------------------------------

    def validate(self, entry_id: str, validation: Any, at: int) -> "ExperienceStore":
        self._check_validation(entry_id, validation)
        return self._change(entry_id, at, "validated", mutate=lambda d: d.update(validatedAt=at))

    def revalidate(self, entry_id: str, validation: Any, at: int) -> "ExperienceStore":
        self._check_validation(entry_id, validation)
        return self._change(entry_id, at, "revalidated", mutate=lambda d: d.update(validatedAt=at))

    def _check_validation(self, entry_id: str, validation: Any) -> None:
        _exact(validation, {"validator", "evidenceSha256", "passed"}, "invalid-validation")
        _require(_id(validation["validator"]) and _hash(validation["evidenceSha256"])
                 and validation["passed"] is True, "invalid-validation")
        entry = self.get(entry_id)
        _require(validation["validator"] != entry.data["provenance"]["producer"], "validator-not-independent")
        _require(validation["evidenceSha256"] not in {r["sha256"] for r in entry.data["evidence"]},
                 "validation-not-independent")

    def add_evidence(self, entry_id: str, row: Any, at: int) -> "ExperienceStore":
        def mutate(d):
            d["evidence"].append(thaw(row))
        return self._change(entry_id, at, "evidence-added", mutate=mutate)

    # --- governed activation -------------------------------------------------------

    def activate(self, entry_id: str, decision: Any, at: int) -> "ExperienceStore":
        """Activate a validated entry only under an approved human decision bound to it."""
        entry = self.get(entry_id)
        _require(entry.state == "validated", "invalid-transition")
        d = entry.to_dict()
        _require(not _contradicted(d), "contradicted")
        _require(not _stale(d, at) and not _expired(d, at), "stale-revalidation")
        _check_decision(thaw(decision), d, exact=True)
        _require(thaw(decision)["decidedAt"] == at, "decision-time-mismatch")
        return self._change(entry_id, at, "activated", mutate=lambda e: e.update(activation=thaw(decision)))

    def rollback(self, entry_id: str, at: int, reason: str) -> "ExperienceStore":
        """Withdraw an active entry back to ``validated``; history keeps the activation."""
        return self._change(entry_id, at, "rolled-back", reason, lambda d: d.update(activation=None))

    def revoke(self, entry_id: str, at: int, reason: str) -> "ExperienceStore":
        return self._change(entry_id, at, "revoked", reason, lambda d: d.update(activation=None))

    def revoke_evidence(self, evidence_sha256: str, at: int, reason: str) -> "ExperienceStore":
        """Revoke every live entry that relies on this evidence as support."""
        _require(_hash(evidence_sha256), "invalid-evidence")
        store = self
        for entry in self._entries:
            cited = any(r["sha256"] == evidence_sha256 and r["polarity"] == "supporting"
                        for r in entry.data["evidence"])
            if cited and entry.state not in TERMINAL:
                store = store.revoke(entry.id, at, reason)
        return store

    def sweep(self, now: int) -> "ExperienceStore":
        """Move entries past ``expiresAt`` to the terminal expired state."""
        store = self
        for entry in self._entries:
            if entry.state not in TERMINAL and entry.state != "proposed" and _expired(entry.data, now):
                store = store._change(entry.id, now, "expired", "expired",
                                      lambda d: d.update(activation=None))
        return store

    # --- online read ---------------------------------------------------------------

    def query(self, context: Any) -> QueryResult:
        """Return active, earlier, in-scope, uncontested lessons for the task in ``context``."""
        _exact(context, _CONTEXT_KEYS, "invalid-context")
        start = context["taskStartedAt"]
        _require(_tick(start) and _id(context["domain"]) and _id(context["host"])
                 and all(_hash(context[k]) for k in ("sourceSha256", "toolSetSha256", "policySha256")),
                 "invalid-context")
        served, excluded = [], []
        for entry in self._entries:
            reason = self._exclusion(entry.data, context, start)
            if reason:
                excluded.append((entry.id, reason))
            else:
                served.append(MappingProxyType({
                    "id": entry.id, "contentSha256": entry.content_sha256, "kind": entry.data["kind"],
                    "cue": entry.data["cue"], "lesson": entry.data["lesson"], "role": "advisory-data"}))
        return QueryResult(tuple(served), tuple(excluded))

    @staticmethod
    def _exclusion(d: Mapping, context: Mapping, start: int) -> str | None:
        if d["state"] in TERMINAL:
            return d["state"]
        if d["state"] != "active":
            return "not-active"
        if max(r["observedAt"] for r in d["evidence"]) >= start or d["activation"]["decidedAt"] >= start \
                or d["validatedAt"] >= start:
            return "future-state"
        if _expired(d, start):
            return "expired"
        if _stale(d, start):
            return "stale-revalidation"
        for field, key, reason in _MISMATCH:
            expected = d["applicability"][field]
            if expected != context[key]:
                return reason
        return "contradicted" if _contradicted(d) else None

    # --- codec ---------------------------------------------------------------------

    def to_bytes(self) -> bytes:
        return canonical({"format": STORE_FORMAT, "entries": [e.to_dict() for e in self._entries]})

    @property
    def sha256(self) -> str:
        return sha256(self.to_bytes()).hexdigest()

    @classmethod
    def from_bytes(cls, raw: bytes) -> "ExperienceStore":
        """Accept only the exact canonical bytes ``to_bytes`` would produce."""
        try:
            value = parse_json(raw)
        except InvalidDecision:
            raise ExperienceError("invalid-json") from None
        _exact(value, {"format", "entries"}, "invalid-store")
        _require(value["format"] == STORE_FORMAT and type(value["entries"]) is list, "unknown-format")
        store = cls(tuple(_entry(e) for e in value["entries"]))
        _require(store.to_bytes() == raw, "non-canonical")
        return store
