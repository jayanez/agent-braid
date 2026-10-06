# SPDX-License-Identifier: AGPL-3.0-only
"""Report SPEC-019 candidate prerequisites from explicit metadata, without admission.

Run as ``python -m scripts.check_predictor_readiness manifest.json``. This reads
one supplied manifest only; it never follows source paths or verifies rights.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
from typing import Any

FORMAT = "m35-readiness-metadata-v1"
MAX_BYTES = 1024 * 1024
MAX_FAMILIES = 1000
MAX_IDS = 4096
MAX_COUNT = 1000000
MAX_DEPTH = 32
HASH = re.compile(r"[0-9a-f]{64}\Z")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


def _keys(value: Any, keys: set[str], name: str) -> None:
    if type(value) is not dict or set(value) != keys:
        raise ValueError(f"{name} must contain exactly {sorted(keys)}")


def check_readiness(manifest: Any) -> dict:
    """Check claimed metadata consistency, never authorize data use or training."""
    _keys(manifest, {"format", "sourceKind", "protocol", "rubric", "families"}, "manifest")
    if manifest["format"] != FORMAT or manifest["sourceKind"] not in ("synthetic", "metadata-only"):
        raise ValueError("explicit synthetic or metadata-only readiness manifest required")
    reasons: list[str] = []
    for name in ("protocol", "rubric"):
        record = manifest[name]
        _keys(record, {"recordedHash", "currentHash", "approved"}, name)
        if (any(type(record[key]) is not str or HASH.fullmatch(record[key]) is None
                for key in ("recordedHash", "currentHash")) or type(record["approved"]) is not bool):
            raise ValueError(f"invalid {name} commitment")
        if not record["approved"]:
            reasons.append(f"{name}-unapproved")
        if record["recordedHash"] != record["currentHash"]:
            reasons.append(f"{name}-hash-drift")
    families = manifest["families"]
    if type(families) is not list or len(families) > MAX_FAMILIES:
        raise ValueError("families must be a list")
    seen: set[str] = set()
    partitions: Counter = Counter()
    classes: dict[str, Counter] = {key: Counter() for key in ("train", "calibration", "holdout")}
    identities: dict[tuple[str, str], str] = {}
    total = known = 0
    for family in families:
        _keys(family, {"familyId", "partition", "rights", "eligible", "windowFrozen",
                       "completenessReviewed", "admittedPairs", "positive", "negative",
                       "unknown", "annotationAttempts", "policyBlind", "holdoutSealed",
                       "sessionIds", "duplicateGroupIds"}, "family")
        family_id, partition = family["familyId"], family["partition"]
        if type(family_id) is not str or ID.fullmatch(family_id) is None or family_id in seen:
            raise ValueError("invalid or duplicate familyId")
        if type(partition) is not str or partition not in classes:
            raise ValueError("invalid family partition")
        seen.add(family_id)
        _keys(family["rights"], {"owner", "participants", "data", "privacy"}, "rights")
        if any(type(value) is not bool for value in family["rights"].values()):
            raise ValueError("rights claims must be booleans")
        for flag in ("eligible", "windowFrozen", "completenessReviewed", "policyBlind", "holdoutSealed"):
            if type(family[flag]) is not bool:
                raise ValueError(f"{flag} must be a boolean")
        for field in ("admittedPairs", "positive", "negative", "unknown", "annotationAttempts"):
            if type(family[field]) is not int or not 0 <= family[field] <= MAX_COUNT:
                raise ValueError(f"{field} must be a nonnegative integer")
        admitted = family["admittedPairs"]
        if (family["positive"] + family["negative"] + family["unknown"] != admitted
                or family["positive"] + family["negative"] > family["annotationAttempts"]
                or family["annotationAttempts"] > admitted):
            raise ValueError("inconsistent pair and annotation counts")
        for field in ("sessionIds", "duplicateGroupIds"):
            values = family[field]
            if (type(values) is not list or len(values) > MAX_IDS or any(type(value) is not str or ID.fullmatch(value) is None
                                               for value in values) or len(set(values)) != len(values)):
                raise ValueError(f"invalid {field}")
            for value in values:
                key = (field, value)
                if key in identities and identities[key] != partition:
                    reasons.append(f"{field}-partition-leakage")
                identities[key] = partition
        if not all(family["rights"].values()):
            reasons.append(f"{family_id}:missing-rights")
        for flag in ("eligible", "windowFrozen", "completenessReviewed"):
            if not family[flag]:
                reasons.append(f"{family_id}:{flag}-missing")
        if admitted == 0:
            reasons.append(f"{family_id}:zero-yield")
        if admitted and not family["sessionIds"]:
            reasons.append(f"{family_id}:session-inventory-missing")
        if family["annotationAttempts"] != admitted or not family["policyBlind"]:
            reasons.append(f"{family_id}:annotation-incomplete-or-unblinded")
        if partition == "holdout" and not family["holdoutSealed"]:
            reasons.append(f"{family_id}:holdout-unsealed")
        if family["eligible"] and all(family["rights"].values()) and admitted:
            partitions[partition] += 1
        classes[partition].update({"positive": family["positive"], "negative": family["negative"]})
        total += admitted
        known += family["positive"] + family["negative"]
    if total == 0:
        reasons.append("zero-yield")
    if sum(partitions.values()) < 5:
        reasons.append("insufficient-eligible-families")
    for partition, minimum in (("train", 1), ("calibration", 1), ("holdout", 3)):
        if partitions[partition] < minimum:
            reasons.append(f"{partition}-families-insufficient")
        required_class = 20 if partition == "holdout" else 1
        if any(classes[partition][label] < required_class for label in ("positive", "negative")):
            reasons.append(f"{partition}-class-coverage-insufficient")
    if known < 100:
        reasons.append("known-label-count-insufficient")
    return {"format": "m35-readiness-report-v1", "sourceKind": manifest["sourceKind"],
            "metadataPrerequisitesMet": not reasons, "reasons": sorted(set(reasons)),
            "claimedPairs": total, "claimedKnownLabels": known,
            "realPairsAdmitted": 0, "trainingAuthorization": False,
            "executionAuthorization": False, "humanApprovalVerified": False,
            "limits": "Unverified metadata claims and proposed thresholds only; no source admission, rights verification or scientific approval."}


def load_manifest(path: Path) -> Any:
    """Read at most 1 MiB of explicit metadata; reject ambiguous JSON."""
    def members(pairs: list[tuple[str, Any]]) -> dict:
        result: dict = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON member")
            result[key] = value
        return result

    def nonfinite(_value: str) -> None:
        raise ValueError("nonfinite JSON value")

    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("metadata exceeds size limit")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=members,
                           parse_constant=nonfinite)
    except RecursionError as exc:
        raise ValueError("metadata exceeds depth limit") from exc
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise ValueError("metadata exceeds depth limit")
        if type(item) is dict:
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) is list:
            stack.extend((child, depth + 1) for child in item)
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args(argv)
    try:
        report = check_readiness(load_manifest(args.manifest))
    except (OSError, UnicodeError, ValueError, RecursionError):
        # Do not echo private paths, JSON fragments or untrusted exception text.
        parser.error("invalid readiness metadata; check format, counts and limits")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["metadataPrerequisitesMet"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
