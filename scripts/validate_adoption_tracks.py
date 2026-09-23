#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate the radar-to-adoption registry without network access or approval."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TRACKS = ROOT / "research/adoption"
STAGES = (
    "observed", "triaged", "differentiation-hypothesis", "spike",
    "specified", "implemented", "verified", "decision", "operated",
)
DECISIONS = {"pending", "adopted", "watch", "rejected", "research-only"}
TERMINAL = {"adopted", "watch", "rejected", "research-only"}
SOURCES = {"paper", "standard", "official-documentation", "product", "market-signal"}
CLAIMS = {
    "official-documentation", "peer-reviewed-result", "unreproduced-result",
    "product-capability", "market-observation", "forecast",
}


def _nonempty(value: object, label: str, failures: list[str]) -> None:
    if not isinstance(value, str) or not value.strip():
        failures.append(f"missing {label}")


def _validate_track(
    path: Path,
    root: Path,
    seen: set[str],
    radar_ids: set[str],
) -> list[str]:
    failures: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path.name}: invalid JSON: {exc}"]
    if isinstance(data, list):
        failures: list[str] = []
        for index, record in enumerate(data):
            if not isinstance(record, dict):
                failures.append(f"{path.name}[{index}]: track must be an object")
                continue
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as temporary:
                json.dump(record, temporary)
                temporary.flush()
                failures.extend(_validate_track(Path(temporary.name), root, seen, radar_ids))
        return failures
    if not isinstance(data, dict):
        return [f"{path.name}: track must be an object"]
    required = (
        "trackVersion", "trackId", "title", "owner", "nextDecision",
        "sourceRadarIds", "sources",
        "capabilityDelta", "hypothesis", "evidencePlan", "affectedArtifacts",
        "risks", "stage", "decision", "stageHistory", "obtainedEvidence", "limits",
    )
    for field in required:
        if field not in data:
            failures.append(f"{path.name}: missing {field}")
    if data.get("trackVersion") != "0.1.0":
        failures.append(f"{path.name}: unsupported track version")
    track_id = data.get("trackId")
    if not isinstance(track_id, str) or not track_id.startswith("AT-2026-"):
        failures.append(f"{path.name}: invalid trackId")
    elif track_id in seen:
        failures.append(f"{path.name}: duplicate trackId {track_id}")
    else:
        seen.add(track_id)
    for field in ("title", "owner", "nextDecision"):
        value = data.get(field)
        if field == "title":
            _nonempty(value, field, failures)
        else:
            _nonempty(value, field, failures)
    for field in ("evidencePlan", "affectedArtifacts", "risks", "limits"):
        value = data.get(field)
        if not isinstance(value, list) or not value or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            failures.append(f"{path.name}: {field} must be a non-empty string list")
    source_ids = data.get("sourceRadarIds")
    if not isinstance(source_ids, list) or any(not isinstance(item, str) or not item for item in source_ids):
        failures.append(f"{path.name}: sourceRadarIds must be a string list")
    else:
        missing_ids = sorted(set(source_ids) - radar_ids)
        if radar_ids and missing_ids:
            failures.append(f"{path.name}: unknown sourceRadarIds: {', '.join(missing_ids)}")
        if not source_ids and not isinstance(data.get("sourceNote"), str):
            failures.append(f"{path.name}: sourceNote is required when sourceRadarIds is empty")
    for source in data.get("sources", []):
        if not isinstance(source, dict):
            failures.append(f"{path.name}: source must be an object")
            continue
        url = source.get("url", "")
        if not isinstance(url, str) or urlparse(url).scheme != "https":
            failures.append(f"{path.name}: source URL must use HTTPS")
        if source.get("sourceClass") not in SOURCES:
            failures.append(f"{path.name}: invalid source class")
        if source.get("claimLevel") not in CLAIMS:
            failures.append(f"{path.name}: invalid claim level")
        if source.get("provenance") not in {"primary", "secondary"}:
            failures.append(f"{path.name}: invalid provenance")
        if type(source.get("peerReviewed")) is not bool:
            failures.append(f"{path.name}: peerReviewed must be boolean")
    delta = data.get("capabilityDelta", {})
    if not isinstance(delta, dict):
        failures.append(f"{path.name}: capabilityDelta must be an object")
    else:
        for field in ("baseline", "candidate", "alternative", "observableMetric", "comparisonScenario"):
            _nonempty(delta.get(field), f"capabilityDelta.{field}", failures)
    hypothesis = data.get("hypothesis", {})
    if not isinstance(hypothesis, dict):
        failures.append(f"{path.name}: hypothesis must be an object")
    else:
        _nonempty(hypothesis.get("statement"), "hypothesis.statement", failures)
        _nonempty(hypothesis.get("invalidationResult"), "hypothesis.invalidationResult", failures)
    stage = data.get("stage")
    decision = data.get("decision")
    if stage not in STAGES:
        failures.append(f"{path.name}: invalid stage")
    if decision not in DECISIONS:
        failures.append(f"{path.name}: invalid decision")
    history = data.get("stageHistory")
    if not isinstance(history, list) or not history:
        failures.append(f"{path.name}: stageHistory must be non-empty")
        history = []
    history_stages: list[str] = []
    for item in history:
        if not isinstance(item, dict):
            failures.append(f"{path.name}: stage history item must be an object")
            continue
        item_stage = item.get("stage")
        if item_stage not in STAGES:
            failures.append(f"{path.name}: invalid historical stage")
        else:
            history_stages.append(item_stage)
        for field in ("date", "actor", "record"):
            _nonempty(item.get(field), f"stageHistory.{field}", failures)
    indexes = [STAGES.index(item) for item in history_stages]
    if indexes != sorted(indexes):
        failures.append(f"{path.name}: stage history moves backwards")
    if stage in STAGES and (not history_stages or history_stages[-1] != stage):
        failures.append(f"{path.name}: current stage does not match stage history")
    if stage != "decision" and decision in TERMINAL:
        failures.append(f"{path.name}: terminal decision requires decision stage")
    if stage == "decision" and decision == "pending":
        failures.append(f"{path.name}: decision stage cannot remain pending")
    if decision in TERMINAL:
        _nonempty(data.get("decisionRationale"), "decisionRationale", failures)
    if decision == "adopted":
        _nonempty(data.get("featureRef"), "featureRef", failures)
    for artifact in data.get("affectedArtifacts", []):
        if not isinstance(artifact, str) or not (root / artifact).is_file():
            failures.append(f"{path.name}: missing affected artifact {artifact}")
    if not isinstance(data.get("obtainedEvidence"), list):
        failures.append(f"{path.name}: obtainedEvidence must be a list")
    return [f"{path.name}: {failure}" for failure in failures]


def validate(root: Path = ROOT) -> list[str]:
    failures: list[str] = []
    radar_ids: set[str] = set()
    for radar_path in sorted((root / "research/radar").glob("*.json")):
        try:
            radar = json.loads(radar_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        radar_ids.update(
            entry.get("id") for entry in radar.get("entries", [])
            if isinstance(entry, dict) and isinstance(entry.get("id"), str)
        )
    paths = sorted(
        path for path in (root / "research/adoption").glob("*.json")
        if path.name != "adoption-track.schema.json"
    )
    if not paths:
        return ["no adoption tracks found"]
    seen: set[str] = set()
    for path in paths:
        failures.extend(_validate_track(path, root, seen, radar_ids))
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    failures = validate(args.root.resolve())
    if failures:
        print("Adoption-track validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Adoption-track structure and conservative pathline checks passed (no approval inferred).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
