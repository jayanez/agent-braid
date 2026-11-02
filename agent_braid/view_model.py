# SPDX-License-Identifier: AGPL-3.0-only
"""The pure viewer model: Loom events in, render-ready lanes, elements and counters out.

One model feeds the web bundle (`/snapshot`), the frames and the export. Nothing here
reads a file, a clock or the network, and nothing can grant, run or schedule anything:
the model repeats `executionAuthorization: false`. Every element has exactly one source
event and carries that event's `evidenceRef` and `verification`. Lane order is a layout
choice (classified pairs are kept adjacent where possible); no braid relation is applied.
Only an `independent-candidate` pair adjacent in the layout is drawn as a swap; a pair
that is not adjacent is drawn as hops that visibly do not cross the lanes between them.
Absence (unknown pairs, incomplete coverage, hazards not observed, gaps, capped
elements) is reported as such and is never counted as independent or clean. Counters
carry no ratio against serial execution: planned wave width is shown alone.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from agent_braid.view_loom import (
    EXECUTION_AUTHORIZATION, GAP_REASONS, MAX_EVENTS, LoomError, validate_event,
)

MODEL_VERSION = "agent-braid-loom-model/v0.1"
DEFAULT_GAP_THRESHOLD_MS = 5_000
DEFAULT_GAP_NOMINAL_MS = 500
DEFAULT_LIMITS = {"strands": 256, "crossings": 4096, "waves": 64, "grants": 1024}
WAVE_LABEL = "advisory plan, not a runtime measurement"

_GLYPHS = {
    "independent-candidate": "swap",
    "ordered": "ordered-link",
    "conflicting": "conflict-knot",
    "unknown": "unknown-link",
}
_ABSENCE_HAZARDS = ("not-observed", "partial-coverage", "unattributed-writer")


def _positive_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _lanes_of(lanes: dict[str, int], ids: list[str]) -> tuple[list[int], list[str]]:
    """Lane indexes for the strands that have a lane (sorted) and the ids that have none."""
    found = sorted({lanes[i] for i in ids if i in lanes})
    return found, [i for i in ids if i not in lanes]


def _layout(order: list[str], pairs: list[tuple[str, str]]) -> list[str]:
    """Lane order keeping classified pairs adjacent where possible (greedy path cover).

    Pairs are taken in event order; a pair is linked while both strands have at most one
    neighbour and are not already on one path, so the result is a set of paths laid out in
    first-appearance order. A pair that closes a cycle or branches stays non-adjacent.
    """
    adjacent: dict[str, list[str]] = {i: [] for i in order}
    component = {i: i for i in order}

    def root(i: str) -> str:
        while component[i] != i:
            component[i] = component[component[i]]
            i = component[i]
        return i

    for left, right in pairs:
        if left == right or left not in adjacent or right not in adjacent:
            continue
        if len(adjacent[left]) < 2 and len(adjacent[right]) < 2 and root(left) != root(right):
            adjacent[left].append(right)
            adjacent[right].append(left)
            component[root(left)] = root(right)

    def walk(start: str, came_from: str) -> list[str]:
        out, previous, current = [], came_from, start
        while current is not None:
            out.append(current)
            onward = [n for n in adjacent[current] if n != previous]
            previous, current = current, (onward[0] if onward else None)
        return out

    placed: list[str] = []
    seen: set[str] = set()
    for strand_id in order:
        if strand_id in seen:
            continue
        neighbours = adjacent[strand_id]
        path = list(reversed(walk(neighbours[1], strand_id))) if len(neighbours) > 1 else []
        path.append(strand_id)
        if neighbours:
            path += walk(neighbours[0], strand_id)
        seen.update(path)
        placed += path
    return placed


def _time_axis(events: list[dict[str, Any]], threshold: int, nominal: int) -> tuple[dict[int, dict], dict]:
    """Effective time, compressed position and tie-break order per event, plus the axis."""
    timed = [e["at"]["relMs"] for e in events if e["at"]["basis"] != "sequence-only"]
    effective: dict[int, int] = {}
    # A sequence-only event states no time; it takes its predecessor's position, and a leading
    # one the first stated time, so no time is invented.
    previous = timed[0] if timed else 0
    for event in events:
        if event["at"]["basis"] != "sequence-only":
            previous = event["at"]["relMs"]
        effective[event["seq"]] = previous
    x_of: dict[int, int] = {}
    after_gap: set[int] = set()
    compressions: list[dict[str, int]] = []
    position = 0
    last: int | None = None
    for moment in sorted(set(effective.values())):
        if last is not None:
            span = moment - last
            if span > threshold:
                position += nominal
                after_gap.add(moment)
                compressions.append({"fromMs": last, "toMs": moment, "spanMs": span, "shownMs": nominal})
            else:
                position += span
        x_of[moment] = position
        last = moment
    ranked = sorted(effective, key=lambda seq: (effective[seq], seq))
    order = {seq: index for index, seq in enumerate(ranked)}
    bases = {event["at"]["basis"] for event in events}
    times = [effective[e["seq"]] for e in events if e["at"]["basis"] != "sequence-only"]
    axis = {
        "basis": next(iter(bases)) if len(bases) == 1 else ("mixed" if bases else "sequence-only"),
        "gapThresholdMs": threshold,
        "gapNominalMs": nominal,
        "minMs": min(times) if times else None,
        "maxMs": max(times) if times else None,
        "spanMs": (max(times) - min(times)) if times else 0,
        "shownSpan": position,
        "compressions": compressions,
    }
    placement = {
        event["seq"]: {
            "relMs": event["at"]["relMs"], "basis": event["at"]["basis"],
            "timeKnown": event["at"]["basis"] != "sequence-only",
            "x": x_of[effective[event["seq"]]], "order": order[event["seq"]],
            "afterCompressedGap": effective[event["seq"]] in after_gap,
        }
        for event in events
    }
    return placement, axis


def _complete(coverage: list[str]) -> bool:
    return bool(coverage) and all(item == "complete" for item in coverage)


def _crossing(data: dict[str, Any], lanes: dict[str, int], reports: dict[str, dict]) -> dict[str, Any]:
    classification = data["classification"]
    complete = _complete(data["evidence"]["coverage"])
    left, right = lanes.get(data["left"]), lanes.get(data["right"])
    segments: list[dict[str, Any]] = []
    passes: list[int] = []
    if left is None or right is None or left == right:
        draw_as = "unplaced"
    else:
        low, high = sorted((left, right))
        passes = list(range(low + 1, high))
        if passes:
            draw_as = "bridge"
            segments = [{"fromLane": k, "toLane": k + 1, "kind": "bridge", "crossesStrand": False}
                        for k in range(low, high)]
        else:
            draw_as = _GLYPHS[classification]
            segments = [{"fromLane": low, "toLane": high, "kind": draw_as,
                         "crossesStrand": draw_as == "swap"}]
    return {
        "element": "crossing",
        "subject": f"{data['left']} / {data['right']}",
        "status": classification,
        "lanes": sorted({i for i in (left, right) if i is not None}),
        "left": data["left"],
        "right": data["right"],
        "classification": classification,
        "drawAs": draw_as,
        "isSwap": draw_as == "swap",
        "segments": segments,
        "passesOverLanes": passes,
        "sharedResources": list(data["sharedResources"]),
        "reasons": list(data["reasons"]),
        "constraints": list(data["constraints"]),
        "evidence": deepcopy(data["evidence"]),
        "incompleteCoverage": not complete,
        "uncertain": classification == "unknown" or not complete,
        "report": reports.get(data["reportId"]),
    }


def _effort(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
    known = [data[name] for name in ("inputTokens", "outputTokens") if data[name] is not None]
    return {
        "element": "effort",
        "subject": data["strandId"],
        "status": data["basis"],
        "lanes": _lanes_of(lanes, [data["strandId"]])[0],
        "effortBasis": data["basis"],
        "knownTokens": sum(known) if known else None,  # input + output only; cache counts stay separate
        "effort": {name: value for name, value in data.items() if name not in ("strandId", "basis")},
    }


def _wave_plane(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
    waves = [{"strands": list(ids), "width": len(ids), "lanes": _lanes_of(lanes, list(ids))[0]}
             for ids in data["waves"]]
    return {
        "element": "wave-plane", "subject": data["planId"], "status": data["mode"],
        "lanes": sorted({i for wave in waves for i in wave["lanes"]}),
        "planId": data["planId"], "mode": data["mode"], "serialSlots": data["serialSlots"],
        "waves": waves, "label": WAVE_LABEL,
    }


def _wave_marker(phase: str):
    def build(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
        return {
            "element": "wave-marker", "subject": f"{data['scheduleId']}#{data['wave']}", "status": phase,
            "lanes": _lanes_of(lanes, data["strands"])[0], "phase": phase,
            "scheduleId": data["scheduleId"], "wave": data["wave"], "strands": list(data["strands"]),
        }
    return build


def _grant(state: str):
    def build(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
        return {
            "element": "gate-ring", "ringKind": "grant", "subject": data["grantId"], "status": state,
            "lanes": [], "grantId": data["grantId"], "action": data["action"],
            "derived": data["derived"], "state": state,
        }
    return build


def _hazard(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
    anchored, unanchored = _lanes_of(lanes, data["units"])
    return {
        "element": "hazard-cone", "subject": data["hazardKind"], "status": data["stage"],
        "lanes": anchored, "unanchoredUnits": unanchored, "units": list(data["units"]),
        "hazardKind": data["hazardKind"], "stage": data["stage"],
        "absence": data["hazardKind"] in _ABSENCE_HAZARDS,
    }


def _gap(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
    ids = [data["strandId"]] if data["strandId"] is not None else []
    return {
        "element": "gap", "subject": data["strandId"] or "", "status": data["reason"],
        "lanes": _lanes_of(lanes, ids)[0], "reason": data["reason"], "strandId": data["strandId"],
        "fromSeq": data["fromSeq"], "toSeq": data["toSeq"],
    }


def _strand(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
    return {
        "element": "strand", "subject": data["label"], "status": None,
        "lanes": _lanes_of(lanes, [data["strandId"]])[0], "strandId": data["strandId"],
        "role": data["role"], "parentStrandId": data["parentStrandId"],
    }


def _lane_event(element: str, status_field: str):
    def build(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
        built = {
            "element": element, "subject": data["strandId"], "status": data[status_field],
            "lanes": _lanes_of(lanes, [data["strandId"]])[0], "strandId": data["strandId"],
        }
        built[status_field] = data[status_field]
        if "toolName" in data:
            built["toolName"] = data["toolName"]
        return built
    return build


def _plain(element: str, subject: str, status: str | None, **fields: str):
    def build(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
        built = {"element": element, "subject": data[subject], "status": data[status] if status else None,
                 "lanes": []}
        built.update({name: data[source] for name, source in fields.items()})
        return built
    return build


_BUILDERS = {
    "strand.open": _strand,
    "effort.sample": _effort,
    "wave.planned": _wave_plane,
    "wave.started": _wave_marker("started"),
    "wave.finished": _wave_marker("finished"),
    "grant.issued": _grant("issued"),
    "grant.consumed": _grant("consumed"),
    "grant.expired": _grant("expired"),
    "grant.refused": _grant("refused"),
    "hazard.noticed": _hazard,
    "observation.gap": _gap,
    "strand.update": _lane_event("strand-state", "state"),
    "strand.close": _lane_event("strand-end", "outcome"),
}


def _gate(kind: str):
    def build(data: dict[str, Any], lanes: dict[str, int]) -> dict[str, Any]:
        built = {"element": "gate-ring", "ringKind": kind, "subject": data["gateId"],
                 "status": data["status"], "lanes": [], "gateId": data["gateId"], "gateStatus": data["status"]}
        if kind == "workflow-phase":
            built["phase"] = data["phase"]
        else:
            built["operationCount"] = data["operationCount"]
        return built
    return build


_BUILDERS["gate.phase"] = _gate("workflow-phase")
_BUILDERS["gate.result"] = _gate("workflow-result")
_BUILDERS["runtime.phase"] = _plain("runtime-phase", "manifestDigest", "phase",
                                    manifestDigest="manifestDigest", phase="phase")
_BUILDERS["session.origin"] = _plain("session", "mode", "mode", mode="mode", hosts="hosts", limits="limits")
_BUILDERS["analysis.report"] = _plain(
    "report", "reportId", None, reportId="reportId", operationCount="operationCount",
    pairCount="pairCount", summary="summary", uncertainty="uncertainty", limits="limits")


def _element(event: dict[str, Any], built: dict[str, Any], timing: dict[str, Any]) -> dict[str, Any]:
    source = event["source"]
    return {
        "id": f"e{event['seq']}",
        "seq": event["seq"],
        "kind": event["kind"],
        **timing,
        "host": source["host"],
        "evidenceRef": deepcopy(source["evidenceRef"]),
        "verification": source["verification"],
        "unverified": source["verification"] == "unverified",
        "compatibilityClass": event["assurance"]["compatibilityClass"],
        "notAGuarantee": True,
        **deepcopy(built),
    }


def _gaps_by_reason(elements: list[dict[str, Any]]) -> dict[str, int]:
    counts = dict.fromkeys(GAP_REASONS, 0)
    for element in elements:
        if element["element"] == "gap":
            counts[element["reason"]] += 1
    return counts


def _counters(elements: list[dict[str, Any]]) -> dict[str, Any]:
    def count(name: str, **match: Any) -> int:
        return sum(1 for e in elements if e["element"] == name
                   and all(e.get(key) == value for key, value in match.items()))

    crossings = [e for e in elements if e["element"] == "crossing"]
    independent = [e for e in crossings if e["classification"] == "independent-candidate"]
    hazards = [e for e in elements if e["element"] == "hazard-cone"]
    widths = [wave["width"] for e in elements if e["element"] == "wave-plane" for wave in e["waves"]]
    gap_reasons = _gaps_by_reason(elements)
    gap_total = sum(gap_reasons.values())
    unknown = sum(1 for e in crossings if e["classification"] == "unknown")
    grants = {state: sum(1 for e in elements if e["element"] == "gate-ring"
                         and e["ringKind"] == "grant" and e["state"] == state)
              for state in ("issued", "consumed", "expired", "refused")}
    return {
        "conflictsFlagged": sum(1 for e in crossings if e["classification"] == "conflicting"),
        "orderedPairs": sum(1 for e in crossings if e["classification"] == "ordered"),
        "independentCandidates": sum(1 for e in independent if not e["incompleteCoverage"]),
        "unknownPairs": unknown,
        "swaps": sum(1 for e in crossings if e["drawAs"] == "swap" and not e["incompleteCoverage"]),
        "bridges": sum(1 for e in crossings if e["drawAs"] == "bridge"),
        "plannedWaveWidth": {"maxWidth": max(widths) if widths else None,
                             "plans": count("wave-plane"), "label": WAVE_LABEL},
        "hazards": {"total": len(hazards),
                    "byKind": {k: sum(1 for e in hazards if e["hazardKind"] == k)
                               for k in sorted({e["hazardKind"] for e in hazards})}},
        "gaps": {"total": gap_total, "byReason": gap_reasons},
        "gates": {"phases": count("gate-ring", ringKind="workflow-phase"),
                  "results": count("gate-ring", ringKind="workflow-result")},
        "grants": {"total": sum(grants.values()), **grants},
        "unverifiedElements": sum(1 for e in elements if e["unverified"]),
        "absence": {
            "unknownPairs": unknown,
            "independentWithIncompleteCoverage": sum(1 for e in independent if e["incompleteCoverage"]),
            "hazardsNotObserved": sum(1 for e in hazards if e["absence"]),
            "gaps": gap_total,
            "truncated": 0,  # set by build_model once the caps are applied
        },
    }


def _table(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [{
        "seq": e["seq"], "kind": e["kind"], "element": e["element"], "relMs": e["relMs"], "x": e["x"],
        "subject": e["subject"], "status": e["status"], "compatibilityClass": e["compatibilityClass"],
        "verification": e["verification"], "unverified": e["unverified"],
        "evidencePath": (e["evidenceRef"] or {}).get("path"),
        "uncertain": e.get("uncertain", False),
    } for e in elements]


def _limit_group(kind: str) -> str | None:
    if kind == "crossing.classified":
        return "crossings"
    if kind.startswith("wave."):
        return "waves"
    if kind.startswith("grant."):
        return "grants"
    return None


def build_model(
    events: list[dict[str, Any]], *, gap_threshold_ms: int = DEFAULT_GAP_THRESHOLD_MS,
    gap_nominal_ms: int = DEFAULT_GAP_NOMINAL_MS, limits: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build the render-ready model of a validated, `seq`-ordered event sequence.

    Raises LoomError when an event or the sequence breaks the contract (no partial model),
    and ValueError for invalid axis or limit parameters. Spans longer than `gap_threshold_ms`
    between consecutive moments are drawn `gap_nominal_ms` wide and listed in
    `axis.compressions`. `limits` overrides DEFAULT_LIMITS per name; elements beyond a limit
    are dropped from `elements` and `lanes` (listed in `truncated`) but never from counters.
    """
    threshold = _positive_int(gap_threshold_ms, "gap_threshold_ms")
    nominal = _positive_int(gap_nominal_ms, "gap_nominal_ms")
    if nominal > threshold:
        raise ValueError("gap_nominal_ms must not exceed gap_threshold_ms")
    caps = dict(DEFAULT_LIMITS)
    for name, value in (limits or {}).items():
        if name not in caps:
            raise ValueError(f"unknown limit {name!r}")
        caps[name] = _positive_int(value, name)
    if len(events) > MAX_EVENTS:
        raise LoomError("too-many-events", f"a model holds at most {MAX_EVENTS} events")
    last_seq = 0
    for event in events:
        validate_event(event)
        if event["seq"] <= last_seq:
            raise LoomError("seq-order", f"seq {event['seq']} does not exceed {last_seq}")
        last_seq = event["seq"]

    # Lanes: one per strand in first-appearance order; a crossing may name an undeclared strand.
    first: dict[str, dict[str, Any]] = {}
    for event in events:
        data = event["data"]
        if event["kind"] == "strand.open":
            if not first.get(data["strandId"], {"declared": False})["declared"]:
                first[data["strandId"]] = {"event": event, "declared": True}
        elif event["kind"] == "crossing.classified":
            for name in (data["left"], data["right"]):
                first.setdefault(name, {"event": event, "declared": False})
    pairs = [(e["data"]["left"], e["data"]["right"]) for e in events if e["kind"] == "crossing.classified"]
    kept = list(first)[:caps["strands"]]
    dropped_by = {"strands": len(first) - len(kept), "crossings": 0, "waves": 0, "grants": 0}
    lane_ids = _layout(kept, pairs)
    lane_of = {strand_id: index for index, strand_id in enumerate(lane_ids)}
    lanes = []
    for strand_id in lane_ids:
        origin, declared = first[strand_id]["event"], first[strand_id]["declared"]
        data = origin["data"]
        lanes.append({
            "laneIndex": lane_of[strand_id], "strandId": strand_id, "declared": declared,
            "host": data["host"] if declared else None, "role": data["role"] if declared else None,
            "label": data["label"] if declared else strand_id,
            "parentStrandId": data["parentStrandId"] if declared else None,
            "seq": origin["seq"], "evidenceRef": deepcopy(origin["source"]["evidenceRef"]),
            "verification": origin["source"]["verification"],
            "unverified": origin["source"]["verification"] == "unverified",
        })

    timing, axis = _time_axis(events, threshold, nominal)
    reports: dict[str, dict] = {}
    for event in events:
        if event["kind"] == "analysis.report":
            reports.setdefault(event["data"]["reportId"], {
                "seq": event["seq"], "uncertainty": list(event["data"]["uncertainty"]),
                "limits": list(event["data"]["limits"])})

    built_elements = []
    for event in events:
        kind, data = event["kind"], event["data"]
        if kind == "crossing.classified":
            built = _crossing(data, lane_of, reports)
        else:
            built = _BUILDERS[kind](data, lane_of)
        built_elements.append((event, _element(event, built, timing[event["seq"]])))

    counters = _counters([element for _, element in built_elements])
    elements = []
    kept_by = dict.fromkeys(("crossings", "waves", "grants"), 0)
    for event, element in built_elements:
        group = _limit_group(event["kind"])
        if group is not None and kept_by[group] >= caps[group]:
            dropped_by[group] += 1
            continue
        if event["kind"] == "strand.open" and event["data"]["strandId"] not in lane_of:
            continue  # its lane was dropped by the strand cap
        if group is not None:
            kept_by[group] += 1
        elements.append(element)
    counters["absence"]["truncated"] = sum(dropped_by.values())
    return {
        "modelVersion": MODEL_VERSION,
        "executionAuthorization": EXECUTION_AUTHORIZATION,
        "notAGuarantee": True,
        "eventCount": len(events),
        "lastSeq": last_seq,
        "axis": axis,
        "lanes": lanes,
        "elements": elements,
        "table": _table(elements),
        "counters": counters,
        "truncated": [{"what": name, "limit": caps[name], "dropped": dropped_by[name]}
                      for name in ("strands", "crossings", "waves", "grants") if dropped_by[name]],
    }
