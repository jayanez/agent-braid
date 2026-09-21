#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Validate and render the transparent Agent Braid opportunity scenarios."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "research/market/2026-opportunity-model.json"
ORDER = ("low", "base", "high")


def load_and_calculate(path: Path = MODEL) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["baseYear"] != 2026 or data["horizonYear"] != 2029:
        raise ValueError("market model must retain the approved 2026–2029 horizon")
    observation_ids = [item.get("id") for item in data["observations"]]
    if any(not identifier for identifier in observation_ids):
        raise ValueError("every observation requires an id")
    if len(observation_ids) != len(set(observation_ids)):
        raise ValueError("observation ids must be unique")
    observations = {item["id"]: item for item in data["observations"]}
    anchor = observations[data["calculation"]["anchorObservation"]]
    if anchor["unit"] != "OpenAI business customers":
        raise ValueError("anchor unit changed without a model revision")
    for item in data["observations"]:
        if not item.get("source", "").startswith("https://") or not item.get("unit") or not item.get("use"):
            raise ValueError(f"observation {item.get('id')} lacks source, unit, or use")
    results = {}
    for name in ORDER:
        scenario = data["scenarios"][name]
        shares = [scenario[key] for key in (
            "agentDevelopingShare", "sharedStateRelevanceShare",
            "engineeringIntensiveEuUsShare")]
        if any(not 0 <= value <= 1 for value in shares):
            raise ValueError(f"{name} contains a share outside [0, 1]")
        tam = anchor["value"] * shares[0] * shares[1]
        sam = tam * shares[2]
        economic = sam * scenario["illustrativeAnnualAssuranceSpendUsd"]
        if sam > tam or tam > anchor["value"]:
            raise ValueError(f"{name} violates nested TAM/SAM bounds")
        results[name] = {
            "tamOrganizationProxy": round(tam),
            "samOrganizationProxy": round(sam),
            "illustrativeEconomicReferenceUsd": round(economic),
            "somCommunityTargets18Months": data["somCommunityTargets18Months"][name],
        }
    for metric in ("tamOrganizationProxy", "samOrganizationProxy", "illustrativeEconomicReferenceUsd"):
        values = [results[name][metric] for name in ORDER]
        if values != sorted(values):
            raise ValueError(f"scenarios are not monotonic for {metric}")
    for metric in data["somCommunityTargets18Months"]["low"]:
        values = [data["somCommunityTargets18Months"][name][metric] for name in ORDER]
        if values != sorted(values):
            raise ValueError(f"SOM scenarios are not monotonic for {metric}")
    if "never summed" not in data["calculation"]["doubleCountingRule"]:
        raise ValueError("double-counting rule must prohibit summing incompatible units")
    return {"modelVersion": data["modelVersion"], "results": results, "limits": data["limits"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate without printing the table")
    args = parser.parse_args()
    output = load_and_calculate()
    if not args.check:
        print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
