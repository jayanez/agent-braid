# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic T005 control evidence over the frozen manifest; no timings."""

import argparse
from collections import Counter
import json
import platform
import sys

from .__main__ import Rejected, load_file, write_exclusive
from .analysis import additive_candidate, classify, control_result, validate_manifest
from .evidence import explore, source_bindings
from .model import InvalidWorkload, digest

CLASSIFIERS = ("conservative-all-orders", "declared-effects")


def control_evidence(manifest, registration, command=None):
    """Explore every frozen fixture once and record controls and H2 eligibility.

    Measures no cost and assesses no feasibility: the registered T006/T008
    experiment stays separate and is not run here.
    """
    validate_manifest(manifest, registration)
    bound = source_bindings()
    fixtures = []
    for fixture in manifest["fixtures"]:
        report = explore(fixture["request"])
        classifications = {method: classify(fixture["request"], method) for method in CLASSIFIERS}
        fixtures.append({
            "id": fixture["id"], "h2": fixture["h2"], "requestHash": fixture["requestHash"],
            "reportHash": digest(report), "coverage": report["coverage"],
            "verdict": report["comparison"]["verdict"], "traceSafety": report["traceSafety"],
            "classifications": {method: {"pairs": result["pairs"],
                                         "unknownOperations": result["unknownOperations"]}
                                for method, result in classifications.items()},
            "control": control_result(fixture, report),
            "h2Eligibility": additive_candidate(fixture["request"], report) if fixture["h2"] else None,
            "executionAuthorization": False})
    if source_bindings() != bound:
        raise InvalidWorkload("simulation source changed during capture")
    h2 = [entry["h2Eligibility"] for entry in fixtures if entry["h2"]]
    return {
        "format": "effectful-workload-controls-evidence-v1", "registration": registration,
        "sourceBindings": bound, "fixtures": fixtures,
        "accounting": {
            "registeredFixtures": len(fixtures),
            "controlFixtures": sum(not entry["h2"] for entry in fixtures),
            "h2Fixtures": len(h2),
            "completeCoverage": sum(entry["coverage"]["complete"] for entry in fixtures),
            "controlStatus": dict(sorted(Counter(entry["control"]["status"] for entry in fixtures).items())),
            "h2EligibleTerminalCandidates": sum(result["terminalCandidate"] for result in h2),
            "h2Exclusions": dict(sorted(Counter(result["exclusion"] for result in h2
                                                if not result["terminalCandidate"]).items()))},
        "environment": {"python": platform.python_version(),
                        "implementation": platform.python_implementation(),
                        "platform": sys.platform, "machine": platform.machine(), "command": command},
        "timing": "none; deterministic controls only, the registered experiment was not run",
        "contextualEquivalence": "unknown", "runtimeSafety": "unknown",
        "scientificReview": "pending", "executionAuthorization": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--registration", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        evidence = control_evidence(load_file(args.manifest), load_file(args.registration),
                                    command=["python3", "-m", "research.workload_lab.controls",
                                             *(sys.argv[1:] if argv is None else argv)])
        data = json.dumps(evidence, sort_keys=True, indent=2, ensure_ascii=True,
                          allow_nan=False).encode("ascii") + b"\n"
        write_exclusive(args.output, data, args.manifest)
    except Rejected as exc:
        reason = exc.reason
    except (InvalidWorkload, ValueError, TypeError, KeyError, OSError):
        reason = "invalid-control-capture"
    else:
        print(json.dumps({"status": "written", "accounting": evidence["accounting"],
                          "executionAuthorization": False}, sort_keys=True))
        return 0
    print(json.dumps({"status": "rejected", "reason": reason, "executionAuthorization": False},
                     sort_keys=True))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
