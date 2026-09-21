#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate committed radar structure and provenance without network access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RADAR = ROOT / "research/radar"
SOURCE_CLASSES = {"paper", "standard", "official-documentation", "product", "market-signal"}
CLAIM_LEVELS = {"official-documentation", "peer-reviewed-result", "unreproduced-result", "product-capability", "market-observation", "forecast"}
STATUSES = {"candidate", "adopted", "rejected", "watch"}
PROVENANCE = {"primary", "secondary"}


def validate(
    milestone: str | None = None,
    root: Path = ROOT,
    require_approved: bool = False,
) -> list[str]:
    failures: list[str] = []
    reviews = []
    for path in sorted((root / "research/radar").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        review = data.get("review", {})
        reviews.append(review)
        if not review.get("date") or not review.get("kind") or not review.get("decisionRecord"):
            failures.append(f"{path.name}: incomplete review record")
        elif not (root / review["decisionRecord"]).is_file():
            failures.append(f"{path.name}: missing decision record {review['decisionRecord']}")
        ids = set()
        for entry in data.get("entries", []):
            identifier = entry.get("id")
            if not identifier or identifier in ids:
                failures.append(f"{path.name}: missing or duplicate entry id {identifier}")
            ids.add(identifier)
            required = ("title", "url", "sourceDate", "sourceClass", "provenance", "peerReviewed", "claimLevel", "relationship", "affectedArtifacts", "status", "decision")
            for field in required:
                if field not in entry or entry[field] in ("", []):
                    failures.append(f"{identifier}: missing {field}")
            if not entry.get("url", "").startswith("https://"):
                failures.append(f"{identifier}: source URL must use HTTPS")
            if entry.get("sourceClass") not in SOURCE_CLASSES:
                failures.append(f"{identifier}: invalid source class")
            if entry.get("claimLevel") not in CLAIM_LEVELS:
                failures.append(f"{identifier}: invalid claim level")
            if entry.get("status") not in STATUSES:
                failures.append(f"{identifier}: invalid status")
            if entry.get("provenance") not in PROVENANCE:
                failures.append(f"{identifier}: invalid provenance")
            if type(entry.get("peerReviewed")) is not bool:
                failures.append(f"{identifier}: peerReviewed must be boolean")
            if entry.get("claimLevel") == "peer-reviewed-result" and entry.get("peerReviewed") is not True:
                failures.append(f"{identifier}: peer-reviewed claim lacks peer-reviewed provenance")
            for artifact in entry.get("affectedArtifacts", []):
                if not (root / artifact).exists():
                    failures.append(f"{identifier}: missing affected artifact {artifact}")
    if not reviews:
        failures.append("no radar reviews found")
    matching = [review for review in reviews
                if review.get("kind") == "milestone"
                and milestone in review.get("milestones", [])] if milestone else []
    if milestone and not matching:
        failures.append(f"no milestone radar review found for {milestone}")
    elif milestone and require_approved \
            and not any(review.get("decision") == "approved" for review in matching):
        failures.append(f"no approved milestone radar review found for {milestone}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--milestone")
    parser.add_argument("--require-approved", action="store_true")
    args = parser.parse_args()
    failures = validate(args.milestone, require_approved=args.require_approved)
    if failures:
        print("Research radar validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Research radar structure and provenance passed (offline check only).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
