# SPDX-License-Identifier: AGPL-3.0-only
"""Versioned, offline synthetic adoption evidence intake (SPEC-026).

No record dispatches replay commands, contacts people or updates release status.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

VERSION = "synthetic-adoption-evidence-v1"
ID = re.compile(r"[a-z][a-z0-9-]{0,63}\Z")
HASH = re.compile(r"[0-9a-f]{64}\Z")
PHASES = ("setup", "run", "review", "debug")
MAX_BYTES = 1024 * 1024


class InvalidEvidence(ValueError):
    """The input violates the bounded synthetic interface."""


def canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def _object(value: Any, fields: set[str], required: set[str]) -> dict:
    if not isinstance(value, dict) or set(value) - fields or required - set(value):
        raise InvalidEvidence("invalid object fields")
    return value


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise InvalidEvidence("invalid identifier")
    return value


def _text(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise InvalidEvidence("invalid bounded text")
    return value


def _hash(value: Any) -> str:
    if not isinstance(value, str) or not HASH.fullmatch(value):
        raise InvalidEvidence("invalid digest")
    return value


def _choice(value: Any, values: set) -> None:
    if type(value) not in (str, type(None)) or value not in values:
        raise InvalidEvidence("invalid enumerated value")


def _rows(value: Any) -> list:
    if not isinstance(value, list) or len(value) > 1000:
        raise InvalidEvidence("invalid bounded collection")
    return value


def _unique(rows: list) -> dict:
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise InvalidEvidence("invalid record")
        key = _identifier(row.get("id"))
        if key in result:
            raise InvalidEvidence("duplicate record identity")
        result[key] = row
    return result


def _binding(value: Any) -> None:
    keys = {"candidate", "input", "protocol", "environment", "report"}
    _object(value, keys, keys)
    for item in value.values():
        _hash(item)


def _bounded_tree(value: Any, depth: int = 0) -> None:
    if depth > 16:
        raise InvalidEvidence("depth bound exceeded")
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > 128:
                raise InvalidEvidence("invalid key")
            _bounded_tree(item, depth + 1)
    elif isinstance(value, list):
        _rows(value)
        for item in value:
            _bounded_tree(item, depth + 1)
    elif isinstance(value, str):
        if len(value) > 512:
            raise InvalidEvidence("text bound exceeded")
    elif value is not None and type(value) not in (int, float, bool):
        raise InvalidEvidence("invalid JSON value")
    elif type(value) is int:
        # Check Python integers before any implicit conversion to float.
        if abs(value) > 2**53:
            raise InvalidEvidence("numeric bound exceeded")
    elif type(value) is float:
        if not math.isfinite(value) or abs(value) > 2**53:
            raise InvalidEvidence("numeric bound exceeded")


def load(path: Path) -> dict:
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise InvalidEvidence("input byte bound exceeded")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise InvalidEvidence("duplicate JSON member")
            result[key] = value
        return result

    try:
        value = json.loads(data, object_pairs_hook=pairs,
                           parse_constant=lambda _: (_ for _ in ()).throw(
                               InvalidEvidence("non-finite JSON number")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise InvalidEvidence("invalid JSON") from error
    _bounded_tree(value)
    return value


def freeze(register: dict) -> dict:
    """Bind exact inputs before observation; caller stores this returned packet."""
    validate(register)
    return {"version": VERSION, "inputHash": digest(register),
            "windowHash": digest(register["window"]),
            "manifestHash": digest(register["metrics"]),
            "recordHashes": {name: {row["id"]: digest(row) for row in register[name]}
                             for name in ("sources", "organizations", "workloads",
                                          "episodes", "contributions", "reproductions")}}


def validate(register: Any) -> None:
    keys = {"version", "population", "window", "sources", "organizations",
            "workloads", "episodes", "contributions", "reproductions", "metrics"}
    _bounded_tree(register)
    _object(register, keys, keys)
    if register["version"] != VERSION or register["population"] != "synthetic":
        raise InvalidEvidence("only versioned synthetic intake is supported")
    window = _object(register["window"], {"id", "start", "end", "prospective"},
                     {"id", "start", "end", "prospective"})
    _identifier(window["id"])
    for key in ("start", "end"):
        if not isinstance(window[key], str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", window[key]):
            raise InvalidEvidence("invalid collection window")
    try:
        for key in ("start", "end"):
            datetime.date.fromisoformat(window[key])
    except ValueError as error:
        raise InvalidEvidence("invalid calendar window") from error
    if window["start"] > window["end"] or window["prospective"] is not True:
        raise InvalidEvidence("invalid prospective window")
    sources = _unique(_rows(register["sources"]))
    for source in sources.values():
        _object(source, {"id", "kind", "permission", "boundary"},
                {"id", "kind", "permission", "boundary"})
        _choice(source["permission"], {"generated", "withdrawn", "pending"})
        if source["kind"] != "synthetic":
            raise InvalidEvidence("real or unsupported source admission")
        _text(source["boundary"])
    organizations = _unique(_rows(register["organizations"]))
    aliases = {}
    for org in organizations.values():
        _object(org, {"id", "aliases", "segments", "source", "eligible", "reason"},
                {"id", "aliases", "segments", "source", "eligible", "reason"})
        _identifier(org["source"])
        if org["source"] not in sources or type(org["eligible"]) is not bool:
            raise InvalidEvidence("unresolved organization source")
        _text(org["reason"])
        for alias in [org["id"], *_rows(org["aliases"])]:
            _identifier(alias)
            if alias in aliases and aliases[alias] != org["id"]:
                raise InvalidEvidence("unresolved organization alias")
            aliases[alias] = org["id"]
        for segment in _rows(org["segments"]):
            _identifier(segment)
    workloads = _unique(_rows(register["workloads"]))
    if not 1 <= len(workloads) <= 3:
        raise InvalidEvidence("require one to three workload families")
    for workload in workloads.values():
        _object(workload, {"id", "boundary"}, {"id", "boundary"})
        _text(workload["boundary"])
    episodes = _unique(_rows(register["episodes"]))
    episode_identities = set()
    for episode in episodes.values():
        fields = {"id", "organization", "workload", "integration", "source", "window",
                  "condition", "rubric", "outcome", "errors", "times", "judgment", "binding"}
        _object(episode, fields, fields)
        for key in ("organization", "workload", "source"):
            _identifier(episode[key])
        if (episode["organization"] not in aliases or episode["workload"] not in workloads
                or episode["source"] not in sources):
            raise InvalidEvidence("unresolved episode units")
        for key in ("integration", "window", "rubric"):
            _identifier(episode[key])
        if episode["window"] != window["id"]:
            raise InvalidEvidence("episode outside frozen window")
        _choice(episode["condition"], {"baseline", "report"})
        _choice(episode["outcome"], {"completed", "failed", "abandoned", "unknown", None})
        if episode["errors"] is not None and (type(episode["errors"]) is not int or episode["errors"] < 0):
            raise InvalidEvidence("invalid error observation")
        _choice(episode["judgment"], {"useful", "unhelpful", "abstain", None})
        _object(episode["times"], set(PHASES), set(PHASES))
        for value in episode["times"].values():
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise InvalidEvidence("invalid duration seconds")
        _binding(episode["binding"])
        # An arbitrary row ID or organization alias cannot create another use.
        identity = digest({
            "organization": aliases[episode["organization"]],
            **{key: episode[key] for key in ("workload", "integration", "source",
                                            "window", "condition", "rubric", "binding")},
        })
        if identity in episode_identities:
            raise InvalidEvidence("duplicate bound episode observation")
        episode_identities.add(identity)
    for name in ("contributions", "reproductions"):
        for row in _unique(_rows(register[name])).values():
            required = {"id", "source", "rights", "binding", "outcome", "commands", "limits"}
            extra = ({"author", "conflicts", "workload", "expected", "observed", "minimization", "review", "replay"}
                     if name == "contributions" else {"reviewer", "environment", "review"})
            _object(row, required | extra, required | extra)
            _identifier(row["source"])
            _choice(row["rights"], {"generated", "missing", "withdrawn"})
            if row["source"] not in sources:
                raise InvalidEvidence("invalid dossier source or rights")
            _binding(row["binding"])
            _choice(row["outcome"], {"positive", "negative", "inconclusive"})
            for command in _rows(row["commands"]):
                _text(command)  # metadata only; never executed
            _text(row["limits"])
            _choice(row["review"], {"pending", "changes-requested", "approved"})
            if name == "contributions":
                for key in ("author", "conflicts", "expected", "observed"):
                    if row[key] is not None:
                        _text(row[key])
                _identifier(row["workload"])
                if row["replay"] is not None:
                    replay_counterexample(row["replay"])
                _choice(row["minimization"], {"minimized", "not-minimized", "unknown"})
            else:
                reviewer = _object(row["reviewer"], {"identity", "affiliation", "role", "external", "conflicts"},
                                   {"identity", "affiliation", "role", "external", "conflicts"})
                for key in ("identity", "affiliation", "conflicts"):
                    if reviewer[key] is not None:
                        _text(reviewer[key])
                _choice(reviewer["role"], {"founder", "maintainer", "external"})
                if type(reviewer["external"]) is not bool:
                    raise InvalidEvidence("invalid reviewer classification")
                if row["environment"] is not None:
                    _text(row["environment"])
    expected = {
        "organizations": ("organization", "unique-eligible-organizations", "observed"),
        "workloads": ("workload", "unique-eligible-workloads", "observed"),
        "completion": ("episode", "completed/known-eligible-episodes", "observed"),
        "cost": ("seconds", "sum(setup+run+review+debug)", "observed"),
        "judgment": ("episode", "useful/known-eligible-judgments", "proxy"),
    }
    metrics = _unique(_rows(register["metrics"]))
    if set(metrics) != set(expected):
        raise InvalidEvidence("unsupported metric or popularity substitution")
    for key, row in metrics.items():
        fields = {"id", "unit", "formula", "evidenceClass", "baseline", "limit"}
        _object(row, fields, fields)
        if (row["unit"], row["formula"], row["evidenceClass"]) != expected[key]:
            raise InvalidEvidence("metric unit/formula/class mismatch")
        _text(row["baseline"])
        _text(row["limit"])


def replay_counterexample(replay: Any) -> dict:
    """Replay only a closed literal-write fixture, without evaluating command text."""
    _object(replay, {"initial", "left", "right"}, {"initial", "left", "right"})
    if type(replay["initial"]) is not int or abs(replay["initial"]) > 2**31 - 1:
        raise InvalidEvidence("invalid synthetic replay initial state")
    results = {}
    for key in ("left", "right"):
        steps = _rows(replay[key])
        if not 1 <= len(steps) <= 6 or any(type(v) is not int or abs(v) > 2**31 - 1 for v in steps):
            raise InvalidEvidence("invalid closed synthetic literal writes")
        results[key] = steps[-1]
    if sorted(replay["left"]) != sorted(replay["right"]):
        raise InvalidEvidence("replay must compare orders of the same writes")
    return {"left": results["left"], "right": results["right"],
            "diverges": results["left"] != results["right"], "inputHash": digest(replay)}


def report(register: dict, frozen: dict, candidate: str) -> dict:
    """Audit against externally retained frozen inputs; redact raw identities/content."""
    validate(register)
    _hash(candidate)
    _object(frozen, {"version", "inputHash", "windowHash", "manifestHash", "recordHashes"},
            {"version", "inputHash", "windowHash", "manifestHash", "recordHashes"})
    if frozen["version"] != VERSION:
        raise InvalidEvidence("unsupported frozen interface")
    for key in ("inputHash", "windowHash", "manifestHash"):
        _hash(frozen[key])
    current = freeze(register)
    reasons = []
    for key in ("inputHash", "windowHash", "manifestHash", "recordHashes"):
        if frozen[key] != current[key]:
            reasons.append("drift:" + key)
    sources = {row["id"]: row for row in register["sources"]}
    orgs = {row["id"]: row for row in register["organizations"]}
    aliases = {alias: row["id"] for row in orgs.values() for alias in [row["id"], *row["aliases"]]}
    eligible_orgs = {key for key, row in orgs.items()
                     if row["eligible"] and sources[row["source"]]["permission"] == "generated"}
    episodes, excluded = [], 0
    for row in register["episodes"]:
        if row["binding"]["candidate"] != candidate:
            reasons.append("stale-episode:" + row["id"])
        eligible = aliases[row["organization"]] in eligible_orgs and sources[row["source"]]["permission"] == "generated"
        total = sum(row["times"].values()) if all(v is not None for v in row["times"].values()) else None
        episodes.append({"id": row["id"], "eligible": eligible,
                         "reason": "admitted-synthetic" if eligible else "excluded-permission-or-frame",
                         "condition": row["condition"], "outcome": row["outcome"],
                         "errors": row["errors"], "seconds": dict(row["times"]), "totalSeconds": total,
                         "judgmentClass": "proxy", "judgment": row["judgment"], "evidenceHash": digest(row)})
        excluded += not eligible
    admitted = [row for row in episodes if row["eligible"]]
    known = [row for row in admitted if row["outcome"] not in (None, "unknown")]
    timed = [row for row in admitted if row["totalSeconds"] is not None]
    judged = [row for row in admitted if row["judgment"] in ("useful", "unhelpful")]
    metric_values = {
        "organizations": (len(eligible_orgs), len(orgs), 0, len(orgs) - len(eligible_orgs)),
        "workloads": (len({row["workload"] for row in register["episodes"]
                           if aliases[row["organization"]] in eligible_orgs and sources[row["source"]]["permission"] == "generated"}),
                      len(register["workloads"]), 0, 0),
        "completion": (sum(row["outcome"] == "completed" for row in known) / len(known) if known else None,
                       len(known), len(admitted) - len(known), excluded),
        "cost": (sum(row["totalSeconds"] for row in timed) if timed else None,
                 len(timed), len(admitted) - len(timed), excluded),
        "judgment": (sum(row["judgment"] == "useful" for row in judged) / len(judged) if judged else None,
                     len(judged), len(admitted) - len(judged), excluded),
    }
    metrics = []
    for manifest in register["metrics"]:
        value, denominator, missing, exclusion = metric_values[manifest["id"]]
        metrics.append({**{key: manifest[key] for key in ("id", "unit", "formula", "evidenceClass")},
                        "baselineHash": digest(manifest["baseline"]),
                        "limit": "Synthetic fixture only; missingness and selection bound interpretation.",
                        "value": None if reasons else value,
                        "denominator": denominator,
                        "denominatorUnit": "episode" if manifest["id"] in ("completion", "cost", "judgment") else manifest["unit"],
                        "missing": missing, "excluded": exclusion,
                        "eligiblePopulation": len(eligible_orgs) if manifest["id"] == "organizations" else
                            len(register["workloads"]) if manifest["id"] == "workloads" else len(admitted),
                        "windowHash": current["windowHash"], "inputHash": current["inputHash"],
                        "manifestHash": current["manifestHash"], "valid": not reasons,
                        "reasons": list(reasons)})
    contributions = []
    seen = set()
    for row in register["contributions"]:
        identity = digest({key: row[key] for key in ("binding", "workload", "expected", "observed")})
        disposition, why = "admitted", "synthetic-replay-metadata"
        if row["rights"] != "generated" or sources[row["source"]]["permission"] != "generated":
            disposition, why = "rejected", "missing-or-withdrawn-rights"
        elif row["workload"] not in {w["id"] for w in register["workloads"]}:
            disposition, why = "rejected", "unsupported-workload"
        elif row["binding"]["candidate"] != candidate:
            disposition, why = "changes-requested", "stale-candidate"
        elif not row["commands"] or row["replay"] is None or any(row[k] is None for k in ("author", "conflicts", "expected", "observed")):
            disposition, why = "pending", "incomplete-replay-or-author-metadata"
        elif (str(replay_counterexample(row["replay"])["left"]) != row["expected"]
              or str(replay_counterexample(row["replay"])["right"]) != row["observed"]):
            disposition, why = "changes-requested", "contradictory-replay-outcome"
        elif identity in seen:
            disposition, why = "duplicate", "duplicate-divergence"
        if reasons and disposition == "admitted":
            disposition, why = "changes-requested", "frozen-evidence-drift"
        if disposition == "admitted":
            seen.add(identity)
        contributions.append({"id": row["id"], "disposition": disposition, "reason": why,
                              "outcome": row["outcome"], "review": row["review"],
                              "minimization": row["minimization"], "evidenceHash": digest(row),
                              "replayExecuted": disposition == "admitted",
                              "replay": replay_counterexample(row["replay"]) if disposition == "admitted" else None})
    reproductions = []
    for row in register["reproductions"]:
        reviewer = row["reviewer"]
        status, why = "pending", "incomplete-external-evidence"
        if row["binding"]["candidate"] != candidate:
            status, why = "changes-requested", "stale-candidate"
        elif row["rights"] != "generated" or sources[row["source"]]["permission"] != "generated":
            status, why = "pending", "missing-or-withdrawn-rights"
        elif reviewer["role"] in ("founder", "maintainer"):
            status, why = "internal", "project-affiliated-reviewer"
        elif row["binding"]["candidate"] != candidate:
            status, why = "changes-requested", "stale-candidate"
        elif (row["rights"] == "generated" and sources[row["source"]]["permission"] == "generated"
              and reviewer["external"] and all(reviewer[k] is not None for k in ("identity", "affiliation", "conflicts"))
              and row["environment"] is not None and row["commands"]):
            status, why = "synthetic-external-proposal", "separate-real-evidence-and-release-review-required"
        if reasons and status == "synthetic-external-proposal":
            status, why = "changes-requested", "frozen-evidence-drift"
        reproductions.append({"id": row["id"], "status": status, "reason": why,
                              "outcome": row["outcome"], "review": row["review"],
                              "evidenceHash": digest(row), "releaseUpdateApplied": False})
    return {"version": VERSION, "population": "synthetic", "inputHash": current["inputHash"],
            "frozenInputHash": frozen["inputHash"], "candidate": candidate,
            "auditReasons": reasons, "metrics": sorted(metrics, key=lambda row: row["id"]),
            "episodes": episodes, "contributions": contributions, "reproductions": reproductions,
            "independentValidation": "pending", "realYield": 0,
            "limits": "Synthetic plumbing only; no adoption, benefit, scientific or independence claim.",
            "publicationAuthorized": False, "executionAuthorized": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("register", type=Path)
    parser.add_argument("frozen", type=Path)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args(argv)
    try:
        result = report(load(args.register), load(args.frozen), args.candidate)
    except (InvalidEvidence, OSError, ValueError, TypeError):
        print("adoption-evidence: input refused", file=sys.stderr)
        return 2
    sys.stdout.buffer.write(canonical(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
