# SPDX-License-Identifier: AGPL-3.0-only
"""Bounded, offline presentation helpers for tooling result envelopes.

The helpers in this module format already-owned values. They do not read source
files, resolve evidence URIs, dispatch runtime tools, or grant authority.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any
from urllib.parse import quote


FORMAT_VERSION = "agent-braid-presentation/0.1"
MAX_ENVELOPE_BYTES = 8 * 1024 * 1024
MAX_SUMMARY_BYTES = 16 * 1024
MAX_NODES = 128
MAX_EDGES = 1024
MAX_IDENTIFIER_CHARS = 256

_SENSITIVE_KEY = re.compile(
    r"(?:password|passwd|secret|token|credential|api[_-]?key|private[_-]?key|"
    r"grant[_-]?id|grant[_-]?store|authorization[_-]?header|cookie)", re.IGNORECASE
)
_ABSOLUTE_PATH = re.compile(
    r"(?<![\w:/])(?:/[^\s\"'<>|;]+|[A-Za-z]:\\[^\s\"'<>|;]+)"
)
_RELATIVE_PATH = re.compile(r"(?<![\w.-])(?:[A-Za-z0-9_.-]+/){1,}[A-Za-z0-9_.-]+")
_REMOTE_URI = re.compile(r"\b(?:https?|file|ftp)://[^\s\"'<>]+", re.IGNORECASE)
_SECRET_ASSIGNMENT = re.compile(
    r"\b(password|passwd|secret|token|credential|api[_-]?key)\b\s*[:=]\s*[^\s,;]+",
    re.IGNORECASE,
)
_BEARER = re.compile(r"\bBearer\s+[^\s,;]+", re.IGNORECASE)
_DIGEST = re.compile(r"^(?:sha256:)?[0-9a-f]{64}$")
_DOMAIN_STATES = {
    "verified", "failed", "cancelled", "refused", "unknown", "complete",
    "incomplete", "no-private-run", "not-verified", "not-dispatched",
    "not-repeated", "performed", "fallback", "ready", "in-progress",
    "manual-review", "serial-fallback", "candidate-preparation-waves",
}
_OPERATIONS = {"analyze-work", "analyze", "prepare", "status", "execute", "recover", "verify"}
_SAFE_KINDS = {
    "dependency", "conflict", "conflicting", "conditional", "unknown",
    "ordered", "independent-candidate",
}
_KIND_STYLE = {
    "dependency": ("dependency", ""),
    "conflict": ("conflict", "8 3"),
    "conflicting": ("conflict", "8 3"),
    "conditional": ("conditional", "5 3"),
    "unknown": ("unknown", "2 3"),
    "ordered": ("ordered", ""),
    "independent-candidate": ("independent-candidate", "1 3"),
}


class PresentationError(ValueError):
    """Invalid, incomplete, unsafe, or over-budget presentation input."""


def _json_tree(value: Any, *, max_depth: int = 64) -> None:
    """Validate JSON-compatible values iteratively, including finite numbers."""
    stack = [(value, 0)]
    seen_containers: set[int] = set()
    while stack:
        item, depth = stack.pop()
        if depth > max_depth:
            raise PresentationError("presentation input exceeds nesting limit")
        if item is None or type(item) in (str, bool, int):
            continue
        if type(item) is float:
            if not math.isfinite(item):
                raise PresentationError("presentation input contains a non-finite number")
            continue
        if type(item) is list:
            identity = id(item)
            if identity in seen_containers:
                raise PresentationError("presentation input contains a cycle")
            seen_containers.add(identity)
            stack.extend((child, depth + 1) for child in item)
            continue
        if type(item) is dict:
            identity = id(item)
            if identity in seen_containers:
                raise PresentationError("presentation input contains a cycle")
            seen_containers.add(identity)
            for key, child in item.items():
                if not isinstance(key, str):
                    raise PresentationError("presentation object keys must be strings")
                stack.append((child, depth + 1))
            continue
        raise PresentationError("presentation input must contain JSON values only")


def canonical_json(value: Any, *, max_bytes: int = MAX_ENVELOPE_BYTES) -> bytes:
    """Return deterministic JSON bytes without changing the represented value."""
    _json_tree(value)
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")
    except (TypeError, ValueError, RecursionError) as exc:
        raise PresentationError("presentation input is not serializable JSON") from exc
    if len(encoded) > max_bytes:
        raise PresentationError("presentation input exceeds size limit")
    return encoded


def _as_mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(k, str) for k in value):
        raise PresentationError(f"{label} must be an object")
    return value


def _core_result(envelope: Mapping[str, Any]) -> Mapping[str, Any]:
    """Unwrap an inline result; never treat a reference as the complete result."""
    result = envelope.get("result")
    if "schemaVersion" in envelope and "operation" in envelope:
        if not isinstance(result, Mapping):
            if result is None and envelope.get("status") in {"refused", "unknown", "error"}:
                return {}
            raise PresentationError("complete inline result is unavailable")
        reference_tags = {"artifactRef", "artifact-reference", "evidence-artifact-reference"}
        if ((isinstance(result.get("type"), str) and result.get("type") in reference_tags)
                or result.get("kind") in reference_tags or result.get("$type") in reference_tags
                or "artifactRef" in result or "$ref" in result):
            raise PresentationError("resolve the owned artifact before presenting its result")
        return result
    return envelope


def _envelope(value: Any) -> tuple[Mapping[str, Any], Mapping[str, Any]]:
    _as_mapping(value, "presentation input")
    canonical_json(value)
    envelope = value
    core = _core_result(envelope)
    return envelope, core


def _domain_result(envelope: Mapping[str, Any], core: Mapping[str, Any]) -> Mapping[str, Any]:
    """Select the analysis report for display while retaining its full wrapper."""
    if envelope.get("operation") == "analyze-work":
        report = core.get("report")
        if isinstance(report, Mapping):
            return report
    return core


def _ascii(value: Any, *, limit: int = 240) -> str:
    text = value if isinstance(value, str) else str(value)
    text = _REMOTE_URI.sub("<external-uri>", text)
    text = _ABSOLUTE_PATH.sub("<local-path>", text)
    text = _RELATIVE_PATH.sub("<local-path>", text)
    text = _SECRET_ASSIGNMENT.sub(lambda match: match.group(1) + "=<redacted>", text)
    text = _BEARER.sub("Bearer <redacted>", text)
    cleaned = []
    for char in text:
        code = ord(char)
        if code < 32 or code == 127:
            cleaned.append(f"\\x{code:02x}")
        elif code > 126:
            cleaned.append(char.encode("ascii", "backslashreplace").decode("ascii"))
        else:
            cleaned.append(char)
    rendered = "".join(cleaned)
    if len(rendered) > limit:
        rendered = rendered[: limit - 3] + "..."
    return rendered


def _identifier_text(value: str) -> str:
    """Encode delimiters inside IDs so labels cannot impersonate graph syntax."""
    return quote(_ascii(value, limit=MAX_IDENTIFIER_CHARS), safe="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._:-")


def _markdown_literal(value: str) -> str:
    """Keep untrusted text inert in Markdown, including link and code syntax."""
    escaped = html.escape(value, quote=True)
    for char, entity in (("[", "&#91;"), ("]", "&#93;"), ("(", "&#40;"),
                         (")", "&#41;"), ("`", "&#96;"), ("!", "&#33;"),
                         ("*", "&#42;"), ("_", "&#95;"), ("~", "&#126;")):
        escaped = escaped.replace(char, entity)
    return escaped


def _walk_named(value: Any, names: set[str], *, max_visits: int = 10000):
    """Yield selected named values without traversing unbounded structures."""
    stack = [(value, 0)]
    visited = 0
    while stack:
        current, depth = stack.pop()
        visited += 1
        if visited > max_visits or depth > 64:
            raise PresentationError("presentation traversal exceeds limit")
        if isinstance(current, Mapping):
            for key, child in current.items():
                if key in names:
                    yield key, child
                if isinstance(child, (Mapping, list)):
                    stack.append((child, depth + 1))
        elif isinstance(current, list):
            stack.extend((child, depth + 1) for child in current)


def _first_named(value: Any, names: tuple[str, ...]) -> tuple[str, Any] | None:
    wanted = set(names)
    for name, found in _walk_named(value, wanted):
        if name in wanted:
            return name, found
    return None


def _bounded_strings(values: Iterable[str], *, limit: int, label: str) -> tuple[str, ...]:
    try:
        iterator = iter(values)
    except TypeError as exc:
        raise PresentationError(f"{label} must be an iterable") from exc
    result = []
    for value in iterator:
        if len(result) >= limit:
            raise PresentationError(f"{label} exceeds item limit")
        if not isinstance(value, str):
            raise PresentationError(f"{label} entries must be strings")
        result.append(value)
    return tuple(result)


def _digest_for(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value)).hexdigest()


def _identity(core: Mapping[str, Any]) -> list[str]:
    lines = []
    for key in ("analysisId", "planDigest", "evidenceDigest", "manifestDigest", "inputDigest"):
        value = core.get(key)
        if isinstance(value, str) and _DIGEST.fullmatch(value):
            lines.append(f"{key}: {_ascii(value, limit=80)}")
    return lines


def _safe_provenance(envelope: Mapping[str, Any]) -> dict[str, str]:
    """Keep only bounded version tokens and hashes from provenance metadata."""
    provenance = envelope.get("provenance")
    if not isinstance(provenance, Mapping):
        return {}
    result: dict[str, str] = {}
    token_fields = ("candidateVersion", "runtimePolicyVersion", "schemaVersion", "runtimeVersion",
                    "bundleVersion", "sdkVersion", "protocolVersion", "hostVersion")
    for key in token_fields:
        value = provenance.get(key)
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:/+-]{0,127}", value):
            result[key] = value
    for key in ("candidate", "candidateId", "candidateCommit", "sourceRevision", "inputDigest", "sourceIdentity"):
        value = provenance.get(key)
        if isinstance(value, str) and re.fullmatch(r"(?:sha256:)?[0-9a-fA-F]{7,64}", value):
            result[key] = value
    for key in ("observationContract", "runtimeSemantics"):
        value = provenance.get(key)
        if isinstance(value, str) and value.strip():
            result[key] = _ascii(value, limit=160)
    authorization = provenance.get("executionAuthorization")
    if type(authorization) is bool:
        result["executionAuthorization"] = str(authorization).lower()
    input_ids = provenance.get("inputIdentifiers")
    if isinstance(input_ids, list) and len(input_ids) <= 16 and all(
            isinstance(item, str) and re.fullmatch(r"(?:sha256:)?[0-9a-fA-F]{7,64}", item)
            for item in input_ids):
        result["inputIdentifiers"] = ",".join(input_ids)
    return dict(sorted(result.items()))


def _classifications(core: Mapping[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    interactions = core.get("interactions")
    if interactions is not None:
        if not isinstance(interactions, list) or len(interactions) > MAX_EDGES:
            raise PresentationError("interaction list is malformed or too large")
        for item in interactions:
            if not isinstance(item, Mapping):
                raise PresentationError("interaction entry must be an object")
            classification = item.get("classification")
            if not isinstance(classification, str) or classification not in _SAFE_KINDS:
                raise PresentationError("interaction has an unsupported classification")
            counts[classification] = counts.get(classification, 0) + 1
        return dict(sorted(counts.items()))
    summary = core.get("summary")
    if isinstance(summary, Mapping) and isinstance(summary.get("classifications"), Mapping):
        for key, count in summary["classifications"].items():
            if key not in _SAFE_KINDS or type(count) is not int or count < 0:
                raise PresentationError("classification summary is malformed")
            counts[key] = count
    return dict(sorted(counts.items()))


def _domain_status(core: Mapping[str, Any]) -> list[str]:
    found = []
    for key in ("dispatch", "status", "verificationStatus"):
        value = core.get(key)
        if isinstance(value, str) and value in _DOMAIN_STATES:
            label = {"status": "domain status", "verificationStatus": "verification status"}.get(key, key)
            found.append(f"{label}: {_ascii(value)}")
    for name, value in _walk_named(core, {"dispatch", "status", "verificationStatus"}):
        if name == "status" and isinstance(value, str) and value in _DOMAIN_STATES:
            line = f"domain {name}: {_ascii(value)}"
            if line not in found:
                found.append(line)
    return found[:8]


def render_summary(value: Any, *, selected_evidence_refs: Iterable[str] = ()) -> str:
    """Render a compact, sanitized explanation without source payloads."""
    envelope, core = _envelope(value)
    domain = _domain_result(envelope, core)
    selected = _bounded_strings(selected_evidence_refs, limit=512, label="selected evidence references")
    if any(len(item) > MAX_IDENTIFIER_CHARS for item in selected):
        raise PresentationError("selected evidence references must be bounded identifiers")
    lines = ["Agent Braid evidence summary"]
    operation = envelope.get("operation", "result")
    if not isinstance(operation, str) or ("schemaVersion" in envelope and operation not in _OPERATIONS):
        operation = "unknown operation"
    lines.append(f"Operation: {_ascii(operation, limit=96)}")
    provenance = _safe_provenance(envelope)
    if provenance:
        lines.append("Provenance: " + ", ".join(f"{key}={_ascii(item, limit=128)}" for key, item in provenance.items()))
    else:
        lines.append("Provenance: limited; consult the complete evidence value.")
    adapter_status = envelope.get("status")
    if isinstance(adapter_status, str) and adapter_status in {"ok", "refused", "unknown", "error"}:
        lines.append(f"Adapter status: {adapter_status} (not a domain-success verdict)")
    else:
        lines.append("Adapter status: unspecified")
    if "schemaVersion" in envelope and envelope.get("result") is None:
        lines.append("Core result: unavailable; no domain-success claim is made.")
        detail = envelope.get("summary")
        if isinstance(detail, str) and detail:
            lines.append("Adapter detail: " + _ascii(detail, limit=320))
    lines.extend(_identity(domain))
    lines.extend(_domain_status(domain))
    for name, value in _walk_named(domain, {"reasonCode", "refusalCode", "recoveryStatus", "action"}):
        if isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}", value):
            line = f"{name}: {value}"
            if line not in lines:
                lines.append(line)
                if len(lines) >= 36:
                    break
    counts = _classifications(domain)
    if counts:
        lines.append("Interaction classifications: " + ", ".join(
            f"{key}={count}" for key, count in counts.items()
        ))
    auth = _first_named(domain, ("executionAuthorization",))
    raw_provenance = envelope.get("provenance")
    if auth is None and isinstance(raw_provenance, Mapping):
        authorization = raw_provenance.get("executionAuthorization")
        if type(authorization) is bool:
            auth = ("executionAuthorization", authorization)
    if auth is None:
        lines.append("Execution authorization: not established by this result")
    elif auth[1] is True:
        lines.append("Core reports execution authorization: true for this recorded operation only")
    elif auth[1] is False:
        lines.append("Execution authorization: false")
    else:
        lines.append("Execution authorization: unknown")
    if operation in {"execute", "recover"}:
        statuses = [value for name, value in _walk_named(domain, {"status"}) if isinstance(value, str)]
        if adapter_status == "refused" or "refused" in statuses:
            lines.append("Authority: the exact existing operator grant is required; this interface never issues one.")
        elif _first_named(domain, ("dispatch",)) is not None:
            lines.append("Authority: report the checked grant scope for this operation; it is not general authorization.")
    order = domain.get("orderedReadyIds")
    if not isinstance(order, list):
        order = domain.get("order")
    if isinstance(order, list) and all(isinstance(item, str) for item in order[:128]):
        lines.append("Advisory order: " + (" -> ".join(_identifier_text(item) for item in order[:128]) or "none"))
        lines.append("The order is advisory; it does not issue authority or dispatch work.")
    if selected:
        lines.append("Selected evidence references: " + ", ".join(_identifier_text(item) for item in selected))
    for label, limits in (("Envelope limits", envelope.get("limits")), ("Core report limits", domain.get("limits"))):
        if isinstance(limits, list):
            safe_limits = [_ascii(item, limit=320) for item in limits[:8] if isinstance(item, str)]
            if safe_limits:
                lines.append(f"{label}:")
                lines.extend("- " + item for item in safe_limits)
    lines.append("Evidence supports only its recorded observation boundary; it does not establish code correctness or a theorem.")
    lines.append("Presentation is sanitized. A private export, when requested, keeps the complete evidence value in evidence.json.")
    rendered = "\n".join(lines) + "\n"
    if len(rendered.encode("ascii")) > MAX_SUMMARY_BYTES:
        raise PresentationError("rendered summary exceeds size limit")
    return rendered


def build_graph(value: Any) -> dict[str, Any]:
    """Build a deterministic graph from explicit operation/interaction fields."""
    envelope_value, core = _envelope(value)
    if "schemaVersion" in envelope_value and envelope_value.get("result") is None:
        raise PresentationError("graph requires a complete inline core result")
    core = _domain_result(envelope_value, core)
    operations = core.get("operations", [])
    if not isinstance(operations, list) or len(operations) > MAX_NODES:
        raise PresentationError("operation list is malformed or too large")
    nodes: dict[str, dict[str, str]] = {}
    dependencies: list[dict[str, str]] = []
    for operation in operations:
        if not isinstance(operation, Mapping):
            raise PresentationError("operation entry must be an object")
        identifier = operation.get("instanceId", operation.get("operationId", operation.get("id")))
        if not isinstance(identifier, str) or not identifier or len(identifier) > MAX_IDENTIFIER_CHARS:
            raise PresentationError("operation has an invalid identifier")
        if identifier in nodes:
            raise PresentationError("operation identifiers must be unique")
        nodes[identifier] = {"id": identifier, "label": identifier}
        depends_on = operation.get("dependencies", [])
        if not isinstance(depends_on, list) or len(depends_on) > MAX_EDGES:
            raise PresentationError("operation dependencies must be an array")
        for parent in depends_on:
            if not isinstance(parent, str) or len(parent) > MAX_IDENTIFIER_CHARS:
                raise PresentationError("dependency identifier is invalid")
            dependencies.append({"source": parent, "target": identifier, "kind": "dependency"})
            if len(dependencies) > MAX_EDGES:
                raise PresentationError("graph has too many dependency edges")
    edges = list(dependencies)
    interactions = core.get("interactions", [])
    if not isinstance(interactions, list) or len(interactions) > MAX_EDGES:
        raise PresentationError("interaction list is malformed or too large")
    for interaction in interactions:
        if not isinstance(interaction, Mapping):
            raise PresentationError("interaction entry must be an object")
        left, right = interaction.get("left"), interaction.get("right")
        kind = interaction.get("classification")
        if not isinstance(left, str) or not isinstance(right, str) or not isinstance(kind, str) or kind not in _SAFE_KINDS:
            raise PresentationError("interaction edge is malformed")
        if left not in nodes or right not in nodes:
            raise PresentationError("interaction references an unknown operation")
        edges.append({"source": left, "target": right, "kind": kind})
    if len(edges) > MAX_EDGES:
        raise PresentationError("graph has too many edges")
    known = set(nodes)
    if any(edge["source"] not in known or edge["target"] not in known for edge in edges):
        raise PresentationError("dependency references an unknown operation")
    return {
        "nodes": [nodes[key] for key in sorted(nodes)],
        "edges": sorted(edges, key=lambda edge: (edge["source"], edge["target"], edge["kind"])),
        "legend": ["dependency", "conflict", "conditional", "unknown", "ordered", "independent-candidate"],
    }


def render_graph_ascii(graph: Mapping[str, Any]) -> str:
    """Render a color-independent, terminal-safe graph listing."""
    _as_mapping(graph, "graph")
    nodes, edges = graph.get("nodes"), graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list) or len(nodes) > MAX_NODES or len(edges) > MAX_EDGES:
        raise PresentationError("graph is malformed or too large")
    lines = ["Interaction graph", "Nodes:"]
    for node in nodes:
        if not isinstance(node, Mapping) or not isinstance(node.get("id"), str):
            raise PresentationError("graph node is malformed")
        lines.append("- " + _identifier_text(node["id"]))
    lines.append("Edges:")
    for edge in edges:
        if not isinstance(edge, Mapping):
            raise PresentationError("graph edge is malformed")
        source, target, kind = edge.get("source"), edge.get("target"), edge.get("kind")
        if not isinstance(source, str) or not isinstance(target, str) or not isinstance(kind, str) or kind not in _SAFE_KINDS:
            raise PresentationError("graph edge is malformed")
        lines.append(f"{_identifier_text(source)} --[{kind}]--> {_identifier_text(target)}")
    if not edges:
        lines.append("(no explicit edges; no independence is inferred)")
    lines.append("Legend: dependency, conflict, conditional, unknown, ordered, independent-candidate are separate evidence labels.")
    return "\n".join(lines) + "\n"


def _svg_graph(graph: Mapping[str, Any]) -> str:
    nodes, edges = graph["nodes"], graph["edges"]
    width = 960
    row_height = 54
    height = max(150, 80 + row_height * max(len(nodes), len(edges), 1))
    if height > 20000:
        raise PresentationError("graph rendering exceeds size limit")
    node_labels = {node["id"] for node in nodes}
    body = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Agent Braid interaction graph</title>',
        '<desc id="desc">Edges retain their explicit dependency, conflict, conditional, unknown, order, or candidate label.</desc>',
        '<style>text{font:14px sans-serif;fill:#111} .node{fill:#fff;stroke:#111;stroke-width:2} .edge{stroke:#111;stroke-width:2;fill:none} .unknown{stroke-dasharray:2 3} .conditional{stroke-dasharray:5 3} .conflict{stroke-dasharray:8 3}</style>',
    ]
    for index, edge in enumerate(edges):
        sy = ty = 70 + index * row_height
        sx, tx = 150, width - 150
        label, dash = _KIND_STYLE[edge["kind"]]
        style = f' class="edge {label}"'
        if dash:
            style += f' stroke-dasharray="{dash}"'
        body.append(f'<path{style} d="M {sx} {sy} L {tx} {ty}"/>')
        body.append(f'<text x="{width // 2}" y="{sy - 4}" text-anchor="middle">{html.escape(edge["kind"])}</text>')
        for x, identifier in ((sx, edge["source"]), (tx, edge["target"])):
            label = html.escape(_ascii(identifier, limit=48))
            body.append(f'<rect class="node" x="{x - 110}" y="{sy - 17}" width="220" height="34" rx="5"/>')
            body.append(f'<text x="{x}" y="{sy + 5}" text-anchor="middle">{label}</text>')
    isolated = sorted(node_labels - {edge[key] for edge in edges for key in ("source", "target")})
    for index, identifier in enumerate(isolated):
        y = 70 + (len(edges) + index) * row_height
        label = html.escape(_ascii(identifier, limit=48))
        body.append(f'<rect class="node" x="{width // 2 - 110}" y="{y - 17}" width="220" height="34" rx="5"/>')
        body.append(f'<text x="{width // 2}" y="{y + 5}" text-anchor="middle">{label}</text>')
    body.append(f'<text x="20" y="{height - 26}">Legend: dependency | conflict | conditional | unknown | ordered | independent-candidate</text>')
    body.append("</svg>")
    result = "\n".join(body)
    if len(result.encode("utf-8")) > 1024 * 1024:
        raise PresentationError("SVG output exceeds size limit")
    return result


def canonical_result_json(value: Any) -> bytes:
    """Serialize the complete inline core result for full-value CLI parity."""
    envelope, core = _envelope(value)
    if "schemaVersion" in envelope and envelope.get("result") is None:
        raise PresentationError("complete inline result is unavailable")
    if core is envelope and "result" not in envelope:
        return canonical_json(core)
    return canonical_json(core)


def _selected_refs(envelope: Mapping[str, Any], selected: Iterable[str] | None) -> tuple[str, ...]:
    if selected is None:
        raise PresentationError("export requires an explicit evidence selection (an empty selection is allowed)")
    known_raw = envelope.get("evidenceRefs", [])
    if not isinstance(known_raw, list) or len(known_raw) > 512:
        raise PresentationError("evidence reference list is malformed or too large")
    known = set()
    for reference in known_raw:
        if isinstance(reference, str):
            known.add(reference)
        elif isinstance(reference, Mapping) and isinstance(reference.get("artifactId"), str):
            known.add(reference["artifactId"])
        else:
            raise PresentationError("evidence reference is malformed")
    chosen = _bounded_strings(selected, limit=512, label="evidence selection")
    if any(len(item) > MAX_IDENTIFIER_CHARS for item in chosen):
        raise PresentationError("evidence selection is malformed or too large")
    if len(set(chosen)) != len(chosen) or not set(chosen) <= known:
        raise PresentationError("evidence selection contains duplicates or unowned references")
    return tuple(sorted(chosen))


def build_exports(value: Any, *, selected_evidence_refs: Iterable[str] | None) -> dict[str, bytes]:
    """Build deterministic safe views plus complete JSON for a private destination.

    This function performs no file reads or writes. The evidence JSON is complete
    and intentionally sensitive; callers should persist it only with
    :func:`write_exports` in a private operator-selected directory.
    """
    envelope_value, core = _envelope(value)
    if "schemaVersion" in envelope_value and envelope_value.get("result") is None:
        raise PresentationError("export requires a complete inline core result")
    selected = _selected_refs(envelope_value, selected_evidence_refs)
    evidence = canonical_json(envelope_value)
    source_digest = "sha256:" + hashlib.sha256(evidence).hexdigest()
    graph = build_graph(envelope_value)
    summary = render_summary(envelope_value, selected_evidence_refs=selected)
    graph_text = render_graph_ascii(graph)
    graph_svg = _svg_graph(graph)
    markdown = (
        "# Agent Braid evidence summary\n\n"
        "> " + "\n> ".join(_markdown_literal(line) for line in summary.rstrip("\n").splitlines()) + "\n\n"
        "## Interaction graph\n\n> " + "\n> ".join(_markdown_literal(line) for line in graph_text.rstrip("\n").splitlines()) + "\n\n"
        f"Sanitized view. Complete evidence is in `evidence.json` (SHA-256 `{source_digest}`).\n"
    )
    html_summary = html.escape(summary)
    html_graph = graph_svg
    page = (
        "<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Agent Braid evidence summary</title>"
        "<style>body{font:16px system-ui,sans-serif;max-width:72rem;margin:2rem auto;padding:0 1rem;color:#111}"
        "pre{white-space:pre-wrap;overflow-wrap:anywhere}svg{width:100%;height:auto;border:1px solid #888}"
        "</style></head><body><h1>Agent Braid evidence summary</h1>"
        f"<pre>{html_summary}</pre><h2>Interaction graph</h2>{html_graph}"
        f"<p>Sanitized view. Complete evidence is in <code>evidence.json</code> (SHA-256 <code>{source_digest}</code>).</p>"
        "</body></html>\n"
    )
    if "<script" in page.lower() or "http://" in page.lower() or "https://" in page.lower():
        # The only allowed URI is the static SVG namespace.
        if page.lower().replace('xmlns="http://www.w3.org/2000/svg"', "").find("http://") >= 0:
            raise PresentationError("export unexpectedly contains a remote reference")
        if "<script" in page.lower() or "https://" in page.lower():
            raise PresentationError("export contains active or remote content")
    safe_views = {
        "summary.md": markdown.encode("utf-8"),
        "graph.svg": graph_svg.encode("utf-8"),
        "index.html": page.encode("utf-8"),
        "evidence.json": evidence,
    }
    for name, contents in safe_views.items():
        if len(contents) > MAX_ENVELOPE_BYTES:
            raise PresentationError(f"{name} exceeds export size limit")
    receipt = {
        "format": FORMAT_VERSION,
        "completeEvidence": True,
        "rawEvidenceFile": "evidence.json",
        "rawEvidenceSha256": source_digest,
        "selectedEvidenceRefs": list(selected),
        "provenance": _safe_provenance(envelope_value),
        "presentation": "sanitized-summary-only; source payload is not rendered",
        "limits": ["No source files or evidence URIs were read.", "No scripts, remote resources, telemetry, or execution were used."],
        "outputs": {
            name: "sha256:" + hashlib.sha256(contents).hexdigest()
            for name, contents in sorted(safe_views.items())
        },
    }
    safe_views["receipt.json"] = canonical_json(receipt, max_bytes=64 * 1024)
    return safe_views


def write_exports(value: Any, destination: str | os.PathLike[str], *,
                  selected_evidence_refs: Iterable[str] | None) -> dict[str, Any]:
    """Write an export bundle to a new, private, explicitly selected directory."""
    files = build_exports(value, selected_evidence_refs=selected_evidence_refs)
    target = Path(destination)
    if not target.is_absolute() or not target.name:
        raise PresentationError("export destination must be an explicit absolute path")
    parent = target.parent.resolve(strict=True)
    parent_info = parent.stat()
    if not stat.S_ISDIR(parent_info.st_mode) or parent_info.st_uid != os.getuid() or stat.S_IMODE(parent_info.st_mode) & 0o077:
        raise PresentationError("export parent must be a user-owned private directory")
    target = parent / target.name
    if os.path.lexists(target):
        raise PresentationError("export destination already exists")
    try:
        target.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise PresentationError("export destination already exists") from exc
    created: list[Path] = []
    try:
        for name, content in sorted(files.items()):
            path = target / name
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            fd = os.open(path, flags, 0o600)
            created.append(path)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
        dir_fd = os.open(target, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        for path in reversed(created):
            try:
                path.unlink()
            except OSError:
                pass
        try:
            target.rmdir()
        except OSError:
            pass
        raise
    return {"directory": str(target), "files": sorted(files), "completeEvidence": True}


__all__ = [
    "FORMAT_VERSION", "PresentationError", "build_exports", "build_graph",
    "canonical_json", "canonical_result_json", "render_graph_ascii",
    "render_summary", "write_exports",
]
