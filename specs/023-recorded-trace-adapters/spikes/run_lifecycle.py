# SPDX-License-Identifier: AGPL-3.0-only
"""Offline finite lifecycle projection experiment; no SDK/provider dispatch."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from agent_braid.analysis import analyze
from agent_braid.trace_adapter import (
    InvalidTrace, MAPPER, VERSION, canonical_bytes, digest_bytes, import_trace,
)

FEATURE = Path(__file__).resolve().parents[1]
EXPECTED_VERSIONS = {"openai": "v0.23.1", "mcp": "2025-11-25"}
MCP_STATUS = {"working": "started", "input_required": "deferred", "completed": "completed"}


def run_case(case: dict) -> dict:
    """Retain the synthetic timeline and measure a deliberately partial projection."""
    # Cases are checked-in synthetic experiment fixtures, never a real-source
    # admission API. Selected source versions cannot be changed by fixtures.
    if case["admission"] != "synthetic" or case["sourceVersion"] != EXPECTED_VERSIONS[case["provider"]]:
        raise ValueError("unadmitted-or-unpinned-spike-case")
    timeline = case["timeline"]
    result = {"caseId": case["caseId"], "provider": case["provider"],
              "sourceVersion": case["sourceVersion"], "timeline": timeline,
              "sourceCaseDigest": digest_bytes(canonical_bytes(case)),
              "executionAuthorization": False,
              "retainedInPacket": ["instanceId", "attemptId", "definition", "inputDigest", "timeline"],
              "notRepresentedInAim": ["lifecycleTimeline", "sourceProtocolVersion"],
              "providerCalls": 0,
              "analyzerRecomputeLimits": "Same-engine consistency only; not an independent mapping baseline or provider conformance control."}
    if any("requestState" in event for event in timeline):
        # requestState belongs to the later multi-round-trip dialect, not the
        # selected 2025 task contract; its inclusion never silently upgrades it.
        return {**result, "outcome": "unsupported", "reason": "unselected-request-state-dialect",
                "classification": None, "falseSafe": False, "analyzerRecomputeConsistency": None}
    if any("taskId" in event for event in timeline):
        result["retainedInPacket"].append("taskId")
        result["notRepresentedInAim"].append("taskId")
        result["stateHandles"] = [
            {"kind": "taskId", "digest": digest_bytes(event["taskId"].encode()),
             "digestMethod": "local-sha256-synthetic-task-handle", "decoded": False}
            for event in timeline if "taskId" in event]
    events = []
    for event in timeline:
        status = event["status"]
        if case["provider"] == "mcp":
            status = MCP_STATUS.get(status, "unknown")
        events.append({key: event[key] for key in ("eventId", "instanceId", "attemptId", "timestamp")}
                      | {"status": status})
    records = {"operations": case["operations"], "events": events}
    request = {"traceImportVersion": VERSION, "mapper": MAPPER,
               "admission": {"kind": "synthetic"},
               "source": {"kind": "generic-metadata", "schemaVersion": VERSION,
                          "contentDigest": digest_bytes(canonical_bytes(records))}, **records}
    try:
        artifacts = import_trace(canonical_bytes(request), mapper=MAPPER)
    except InvalidTrace as exc:
        return {**result, "outcome": "unsupported", "reason": str(exc), "classification": None,
                "falseSafe": False, "analyzerRecomputeConsistency": None}
    classification = artifacts.report["interactions"][0]["classification"]
    false_safe = classification == "independent-candidate" and case["expected"]["classification"] != classification
    return {**result, "outcome": "mapped", "classification": classification, "falseSafe": false_safe,
            "analyzerRecomputeConsistency": artifacts.report == analyze(artifacts.projection),
            "reportDigest": artifacts.provenance["reportDigest"],
            "projectionDigest": artifacts.provenance["projectionDigest"],
            "mappings": artifacts.provenance["mappings"],
            "mappedEvents": artifacts.provenance["events"]}


def run() -> dict:
    """Regenerate bounded results from predeclared corpus and immutable source pins."""
    corpus_bytes = (FEATURE / "spikes/corpus.json").read_bytes()
    pins_bytes = (FEATURE / "source-pins.json").read_bytes()
    corpus, pins = json.loads(corpus_bytes), json.loads(pins_bytes)
    for provider, version in EXPECTED_VERSIONS.items():
        pin = next(source for source in pins["sources"] if source["id"] == provider)
        if pin["selectedVersion"] != version or not any(
                doc["status"] == "retrieved" for doc in pin["documents"]):
            raise ValueError("source-pin-unavailable")
    results = [run_case(case) for case in corpus["cases"]]
    providers = []
    for provider in EXPECTED_VERSIONS:
        selected = [r for r in results if r["provider"] == provider]
        mapped = [r for r in selected if r["outcome"] == "mapped"]
        providers.append({"provider": provider, "version": EXPECTED_VERSIONS[provider],
                          "caseCount": len(selected), "mappedCount": len(mapped),
                          "unsupportedCount": len(selected) - len(mapped),
                          "unknownCount": sum(r["classification"] == "unknown" for r in mapped),
                          "falseSafeCount": sum(r["falseSafe"] for r in selected),
                          "analyzerRecomputeConsistencyCount": sum(r["analyzerRecomputeConsistency"] is True for r in mapped),
                          "outcome": "negative-for-complete-provider-projection",
                          "nextDecision": "research-only",
                          "limits": "Timeline retained in private spike packet; AIM has no lifecycle/task handle or multiple-attempt representation. Synthetic fixtures do not validate actual provider behavior."})
    return {"spikeResultVersion": VERSION, "corpusDigest": digest_bytes(corpus_bytes),
            "sourcePinsDigest": digest_bytes(pins_bytes), "results": results, "providers": providers,
            "casesExcluded": 0, "providerCalls": 0, "modelCalls": 0,
            "executionAuthorization": False, "providerAdoption": "pending",
            "realSourceAdmission": "pending", "scientificReview": "pending"}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, indent=2))
