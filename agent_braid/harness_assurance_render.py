# SPDX-License-Identifier: AGPL-3.0-only
"""Assurance profiles, generators: the track-brief section and the PR "Pre-PR review" skeleton; offline, advisory.

Both generators are pure functions of a compiled artifact (``harness_assurance.compile_artifact``, T005) and
return Markdown text, so equal input yields byte-identical output. ``track_brief_section`` states the ownership,
isolation, model and effort given by the caller together with the artifact's depth, required reviews and modes;
``pre_pr_review_block`` lists exactly the reviews the effective depth requires, each with placeholders for the
findings applied and rejected, destined for the existing Evidence section of the PR body (the PR template itself
is unchanged). An artifact whose ``executionAuthorization`` is not false, whose digest does not match its content,
whose shape is not exactly that of ``compile_artifact`` or whose review table disagrees with the ladder is refused
with a fixed reason, so no value the text interpolates can carry Markdown. The generators cannot recompute the
compilation: callers confirm the artifact against its inputs with ``harness_assurance.verify_artifact``. The text
grants nothing: no tool, merge, release or approval.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .harness_assurance import (
    CHECKPOINTS, COMPILED_FORMAT, DEPTH_CHECKPOINT, DEPTHS, INDEPENDENT_REVIEW, MIN_INDEPENDENT_REVIEWERS, MODES,
    REASONS, SCOPES, AssuranceError, _hash, _id, _int, digest, required_reviews,
)

PLACEHOLDER = "_pending_"
MAX_FIELD = 200
_UNSAFE = frozenset("|`[]<>*#_\\")  # Markdown syntax the caller's free text may not carry
_ARTIFACT_KEYS = frozenset({"schema", "profile", "scopeSources", "checkpoints", "noAttribution", "refusedLowerings",
                            "executionAuthorization", "risk", "inputs", "reviews", "digest"})
_REVIEW_KEYS = frozenset({"checkpoint", "depth", "docsOnly", "required", "minIndependentReviewers"})
_REFUSAL_KEYS = frozenset({"checkpoint", "dimension", "requested", "scope", "floor", "reason"})
_RISK_CLASSES = ("docs-only", "ordinary", "elevated")


def _invalid() -> AssuranceError:
    return AssuranceError("invalid-artifact")


def _well_formed(artifact: dict[str, Any]) -> bool:
    """Whether every value the generators read has the exact shape ``compile_artifact`` produces."""
    profile, risk, reviews = artifact["profile"], artifact["risk"], artifact["reviews"]
    rows, refusals = artifact["checkpoints"], artifact["refusedLowerings"]
    if not (type(profile) is dict and _id(profile.get("name")) and _int(profile.get("version"), 1, (1 << 31) - 1)
            and type(risk) is dict and risk.get("riskClass") in _RISK_CLASSES
            and type(rows) is list and [r.get("checkpoint") for r in rows if type(r) is dict] == list(CHECKPOINTS)
            and type(refusals) is list and _hash(artifact["digest"])):
        return False
    if not all(r.get("mode") in MODES and _id(r.get("modeSource")) for r in rows):
        return False
    if not all(type(f) is dict and set(f) == _REFUSAL_KEYS and f["checkpoint"] in (None, *CHECKPOINTS)
               and f["dimension"] in ("mode", "depth", "noAttribution") and f["scope"] in SCOPES
               and f["reason"] in REASONS for f in refusals):
        return False
    row = next(r for r in rows if r["checkpoint"] == DEPTH_CHECKPOINT)
    required = reviews.get("required") if type(reviews) is dict else None
    return (set(reviews) == _REVIEW_KEYS and reviews["checkpoint"] == DEPTH_CHECKPOINT and reviews["depth"] in DEPTHS
            and type(reviews["docsOnly"]) is bool and type(required) is list
            and required == list(required_reviews(reviews["depth"], reviews["docsOnly"]))
            and reviews["minIndependentReviewers"] == (MIN_INDEPENDENT_REVIEWERS if INDEPENDENT_REVIEW in required else 0)
            and row.get("depth") == reviews["depth"] and _id(row.get("depthSource")))


def _checked(artifact: Any) -> dict[str, Any]:
    """The artifact when it is a well-formed, unaltered advisory artifact; otherwise ``AssuranceError``."""
    if type(artifact) is not dict or set(artifact) != _ARTIFACT_KEYS or artifact["schema"] != COMPILED_FORMAT:
        raise _invalid()
    if artifact["executionAuthorization"] is not False:
        raise AssuranceError("execution-authorization")
    try:
        intact = artifact["digest"] == digest({k: v for k, v in artifact.items() if k != "digest"})
        well_formed = intact and _well_formed(artifact)
    except (KeyError, TypeError, ValueError, AttributeError, StopIteration):
        raise _invalid() from None
    if not intact:
        raise AssuranceError("digest-mismatch")
    if not well_formed:
        raise _invalid()
    return artifact


def _single_line(value: Any) -> str:
    """A caller-supplied one-line text that cannot carry Markdown structure."""
    if (type(value) is not str or not value.strip() or len(value) > MAX_FIELD or not value.isprintable()
            or _UNSAFE & set(value)):
        raise _invalid()
    return value.strip()


def _change_kind(reviews: Mapping[str, Any]) -> str:
    return "documentation-only change" if reviews["docsOnly"] else "code change"


def _reviewers_rule(reviews: Mapping[str, Any]) -> str:
    return f"at least {reviews['minIndependentReviewers']}, distinct from the author and from each other"


def track_brief_section(artifact: Any, *, ownership: str, isolation: str, model: str, effort: str) -> str:
    """The "Assurance profile" section of a track brief; deterministic Markdown ending in a newline."""
    artifact = _checked(artifact)
    ownership, isolation, model, effort = map(_single_line, (ownership, isolation, model, effort))
    reviews = artifact["reviews"]
    required = reviews["required"]
    depth_source = next(r["depthSource"] for r in artifact["checkpoints"] if r["checkpoint"] == DEPTH_CHECKPOINT)
    lines = [
        "## Assurance profile",
        "",
        f"- Profile: {artifact['profile']['name']} v{artifact['profile']['version']}",
        f"- Compiled artifact digest: `{artifact['digest']}`",
        f"- Ownership: {ownership}",
        f"- Isolation: {isolation}",
        f"- Model and effort: {model}, {effort}",
        f"- Pre-PR review depth: {reviews['depth']} ({_change_kind(reviews)})",
        f"- Depth source: {depth_source}; risk class: {artifact['risk']['riskClass']}",
        f"- Required reviews: {', '.join(required) if required else 'none'}",
    ]
    if INDEPENDENT_REVIEW in required:
        lines.append(f"- Independent reviewers: {_reviewers_rule(reviews)}")
    lines += ["", "| Checkpoint | Mode | Source |", "|---|---|---|"]
    lines += [f"| {row['checkpoint']} | {row['mode']} | {row['modeSource']} |" for row in artifact["checkpoints"]]
    if artifact["refusedLowerings"]:
        lines.append("")
    for refusal in artifact["refusedLowerings"]:
        lines.append(f"- Refused lowering: {refusal['checkpoint'] or 'all'} {refusal['dimension']} "
                     f"requested by {refusal['scope']} ({refusal['reason']})")
    lines += ["", "Advisory only: this profile grants no tool, merge, release or approval.", ""]
    return "\n".join(lines)


def pre_pr_review_block(artifact: Any) -> str:
    """The "Pre-PR review" skeleton of a PR body; lists only the reviews the depth requires."""
    artifact = _checked(artifact)
    reviews = artifact["reviews"]
    lines = [
        "## Pre-PR review",
        "",
        f"Depth {reviews['depth']}, {_change_kind(reviews)}; compiled artifact `{artifact['digest']}`.",
    ]
    if not reviews["required"]:
        lines += ["", "No review is required at this depth."]
    for kind in reviews["required"]:
        lines += ["", f"### {kind}", ""]
        if kind == INDEPENDENT_REVIEW:
            lines.append(f"- Reviewers ({_reviewers_rule(reviews)}): {PLACEHOLDER}")
        lines += [f"- Findings applied: {PLACEHOLDER}", f"- Findings rejected, with reason: {PLACEHOLDER}"]
    lines.append("")
    return "\n".join(lines)
