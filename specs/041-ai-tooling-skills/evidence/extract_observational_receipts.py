#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only extractor of derived observational native receipts.

Scans local Claude Code transcripts (``~/.claude/projects``) and Codex sessions
(``~/.codex/sessions``) and emits only derived, minimal metadata: skill and MCP
tool names, timestamps, counts, plugin versions, outcomes, content digests and
truncated session hashes. It never copies prompts, tool inputs, assistant text,
working directories or project names. Nothing is written unless ``--out`` is
given; transcripts are only opened for reading.

Usage: extract_observational_receipts.py [--claude DIR] [--codex DIR] [--out FILE]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path

SCHEMA = "agent-braid-observational-native-receipts/v1"
SKILLS = ("analyze", "plan", "execute", "recover", "evidence", "setup")
MCP_RE = re.compile(r"^mcp__(?:plugin_)?agent[-_]braid_agent[-_]braid__(.+)$|^mcp__agent[-_]braid__(.+)$")
SKILL_RE = re.compile(r"^agent-braid(?::|-)(?:agent-braid-)?(" + "|".join(SKILLS) + r")$")
LISTING_RE = re.compile(r"^- agent-braid:(?:agent-braid-)?(" + "|".join(SKILLS) + r")\b", re.M)
VERSION_RE = re.compile(r"/agent-braid/agent-braid/([0-9][^/\s]*)/skills/")
CODEX_LISTING_RE = re.compile(r"agent-braid:(?:agent-braid-)?(" + "|".join(SKILLS) + r")\b")
ENUM_RE = re.compile(r"^[A-Za-z0-9_.:/-]{1,64}$")
BASE_DIR = "Base directory for this skill:"


def short_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:12]


def lines(path: Path):
    try:
        with path.open(errors="replace") as handle:
            for raw in handle:
                try:
                    yield json.loads(raw)
                except ValueError:
                    continue
    except OSError:
        return


def text_of(content) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(b.get("text", "") for b in content if isinstance(b, dict))
    return ""


class Tally:
    """Counts, first/last seen, sessions, versions and outcomes for one item."""

    def __init__(self):
        self.count = 0
        self.first = None
        self.last = None
        self.sessions = set()
        self.versions = defaultdict(int)
        self.outcomes = defaultdict(int)
        self.digests = defaultdict(int)

    def add(self, ts, session, version=None, outcome=None, digest=None):
        self.count += 1
        if ts:
            self.first = min(filter(None, (self.first, ts)))
            self.last = max(filter(None, (self.last, ts)))
        self.sessions.add(short_hash(session))
        if version:
            self.versions[version] += 1
        if outcome:
            self.outcomes[outcome] += 1
        if digest:
            self.digests[digest] += 1

    def render(self) -> dict:
        if not self.count:
            return {"state": "not-observed", "count": 0}
        out = {
            "state": "observed",
            "count": self.count,
            "sessions": len(self.sessions),
            "firstSeen": self.first,
            "lastSeen": self.last,
            "versions": dict(sorted(self.versions.items())) or "unavailable",
            "outcomes": dict(sorted(self.outcomes.items())),
        }
        if self.digests:
            out["loadedContentSha256"] = dict(sorted(self.digests.items()))
        return out


def classify_result(block) -> tuple[str, str | None]:
    """Return (outcome, candidateVersion) from an MCP tool_result envelope."""
    try:
        envelope = json.loads(text_of(block.get("content")))
    except ValueError:
        return ("error" if block.get("is_error") else "ok-unparsed"), None
    if not isinstance(envelope, dict):
        return ("error" if block.get("is_error") else "ok-unparsed"), None
    status = envelope.get("status")
    outcome = status if isinstance(status, str) and ENUM_RE.match(status) else (
        "error" if block.get("is_error") else "ok-unparsed"
    )
    provenance = envelope.get("provenance")
    version = provenance.get("candidateVersion") if isinstance(provenance, dict) else None
    if version is None and isinstance(envelope.get("result"), dict):
        version = envelope["result"].get("version")
    return outcome, version if isinstance(version, str) and ENUM_RE.match(version) else None


def scan_claude(root: Path) -> dict:
    listed, loaded, used = (defaultdict(Tally) for _ in range(3))
    mcp = defaultdict(Tally)
    journeys: dict[str, list] = defaultdict(list)
    seen_use: set[str] = set()
    seen_listed: set[tuple[str, str]] = set()
    seen_meta: set[str] = set()
    files = sessions_with_hits = 0
    discovery_mcp = set()
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else []:
        files += 1
        pending: dict[str, tuple[str, str, str]] = {}
        skill_uses: list[tuple[str, str, str, str, str]] = []
        meta_version: dict[str, str] = {}
        first_ts = None
        hit = False
        for rec in lines(path):
            ts = rec.get("timestamp")
            session = rec.get("sessionId") or path.stem
            first_ts = first_ts or ts
            kind = rec.get("type")
            if kind == "attachment":
                att = rec.get("attachment") or {}
                if att.get("type") == "skill_listing":
                    for name in set(LISTING_RE.findall(att.get("content", ""))):
                        if (session, name) not in seen_listed:
                            seen_listed.add((session, name))
                            listed[name].add(ts, session)
                        hit = True
                elif att.get("type") == "mcp_instructions_delta":
                    if "plugin:agent-braid:agent-braid" in att.get("addedNames", []):
                        discovery_mcp.add((short_hash(session), ts))
                        hit = True
                continue
            content = (rec.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                btype = block.get("type")
                if btype == "tool_use":
                    name, uid = block.get("name", ""), block.get("id")
                    if not uid or uid in seen_use:
                        continue
                    skill = None
                    if name == "Skill":
                        match = SKILL_RE.match(str((block.get("input") or {}).get("skill", "")))
                        skill = match.group(1) if match else None
                    mcp_match = MCP_RE.match(name)
                    if skill:
                        pending[uid] = ("skill", skill, ts)
                    elif mcp_match:
                        pending[uid] = ("mcp", mcp_match.group(1) or mcp_match.group(2), ts)
                    else:
                        continue
                    seen_use.add(uid)
                    hit = True
                elif btype == "tool_result" and block.get("tool_use_id") in pending:
                    ckind, cname, cts = pending.pop(block["tool_use_id"])
                    if ckind == "skill":
                        outcome = "error" if block.get("is_error") else "invoked"
                        skill_uses.append((block["tool_use_id"], cname, cts, session, outcome))
                    else:
                        outcome, version = classify_result(block)
                        mcp[cname].add(cts, session, version, outcome)
                    journeys[short_hash(session)].append((cts, f"{ckind}:{cname}", outcome))
            if kind == "user" and rec.get("isMeta") and rec.get("sourceToolUseID") not in seen_meta | {None}:
                body = text_of(content)
                if body.startswith(BASE_DIR):
                    first_line, _, rest = body.partition("\n")
                    version = VERSION_RE.search(first_line)
                    skill = re.search(r"/skills/([a-z-]+)\s*$", first_line)
                    name = skill.group(1) if skill else None
                    name = name[len("agent-braid-"):] if name and name.startswith("agent-braid-") else name
                    if name in SKILLS:
                        seen_meta.add(rec["sourceToolUseID"])
                        digest = hashlib.sha256(rest.encode()).hexdigest()
                        loaded[name].add(ts, session, version.group(1) if version else None,
                                         "loaded", digest)
                        meta_version[rec["sourceToolUseID"]] = version.group(1) if version else None
        for uid, cname, cts, session, outcome in skill_uses:
            used[cname].add(cts, session, meta_version.get(uid), outcome)
        sessions_with_hits += hit
    return {
        "host": "claude-code",
        "transcriptFilesScanned": files,
        "transcriptFilesWithAgentBraidEvents": sessions_with_hits,
        "c1Discovery": {
            "skillsListedInContext": {s: listed[s].render() for s in SKILLS},
            "mcpServerInstructionsDelivered": {
                "state": "observed" if discovery_mcp else "not-observed",
                "sessions": len({h for h, _ in discovery_mcp}),
                "firstSeen": min((t for _, t in discovery_mcp if t), default=None),
                "lastSeen": max((t for _, t in discovery_mcp if t), default=None),
            },
        },
        "c2InstructionsLoaded": {s: loaded[s].render() for s in SKILLS},
        "c3ObservedUse": {
            "skills": {s: used[s].render() for s in SKILLS},
            "mcpTools": {n: mcp[n].render() for n in sorted(mcp)},
        },
        "_journeys": journeys,
    }


def scan_codex(root: Path) -> dict:
    listed = defaultdict(Tally)
    files = hits = 0
    for path in sorted(root.rglob("*.jsonl")) if root.is_dir() else []:
        files += 1
        session = path.stem
        names: set[str] = set()
        pending_listing: list[tuple[str, str]] = []
        version = None
        for rec in lines(path):
            payload = rec.get("payload")
            blob = json.dumps(payload) if isinstance(payload, dict) else ""
            found = VERSION_RE.search(blob)
            version = found.group(1) if found else version
            if "agent-braid:" not in blob or payload.get("role") not in ("developer", "system"):
                continue
            ts = rec.get("timestamp")
            for name in set(CODEX_LISTING_RE.findall(blob)):
                if name not in names:
                    names.add(name)
                    pending_listing.append((name, ts))
        for name, ts in pending_listing:
            listed[name].add(ts, session, version, "listed")
        hits += bool(names)
    return {
        "host": "codex",
        "sessionFilesScanned": files,
        "sessionFilesListingAgentBraidSkills": hits,
        "c1Discovery": {"skillsListedInContext": {s: listed[s].render() for s in SKILLS}},
        "c2InstructionsLoaded": "not-observed",
        "c3ObservedUse": {"state": "not-observed"},
    }


def _tree_counts(path: Path) -> dict:
    if not path.exists():
        return {"state": "absent"}
    stamps, unreadable = [], 0
    for item in path.rglob("*"):
        try:
            if item.is_file():
                stamps.append(item.stat().st_mtime)
        except OSError:
            unreadable += 1
    iso = lambda t: datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
    return {"state": "present", "files": len(stamps), "unreadable": unreadable, "modifiedFirst": iso(min(stamps)) if stamps else None,
            "modifiedLast": iso(max(stamps)) if stamps else None}


def scan_local_stores(home: Path) -> dict:
    """Numeric summaries of the other real-use sources; paths, names and contents are never kept."""
    share, state = home / ".local/share/agent-braid", home / ".local/state/agent-braid"
    support = home / "Library/Application Support/AgentBraid"
    out: dict = {"telemetry": {"state": "unavailable"}}
    try:
        report = json.loads(subprocess.run(
            [sys.executable, "-m", "agent_braid", "telemetry", "report", "--format", "json"],
            capture_output=True, text=True, timeout=60, check=True).stdout)
        calls: dict[str, dict] = {}
        for row in report.get("rows", []):
            if row.get("metric") == "calls":
                cell = calls.setdefault(f'{row["surface"]}:{row["operation"]}:{row["outcome"]}',
                                        {"count": 0, "firstDay": row["day"], "lastDay": row["day"]})
                cell["count"] += row["count"]
                cell["firstDay"], cell["lastDay"] = min(cell["firstDay"], row["day"]), max(cell["lastDay"], row["day"])
        out["telemetry"] = {"state": "observed" if calls else "no-observations", "retentionDays": report.get("retentionDays"),
                            "calls": dict(sorted(calls.items())),
                            "coverage": "daily aggregates; portable MCP tools and CLI analyze/analyze-git only; no skill-level data"}
    except (OSError, ValueError, subprocess.SubprocessError):
        pass
    for name, path in (("evidenceStore", share / "evidence"), ("coordinationStore", share / "coordination"),
                       ("identityStore", share / "identity"), ("runtimeState", state),
                       ("pluginResults", support / "results")):
        out[name] = _tree_counts(path)
    try:
        registry = json.loads((support / "registry.json").read_text())
        out["pluginWorkspaceRegistry"] = {"state": "present", "configuredWorkspaces": len(registry.get("workspaces", []))}
    except (OSError, ValueError, AttributeError):
        out["pluginWorkspaceRegistry"] = {"state": "absent"}
    return out


def build(claude_root: Path, codex_root: Path, home: Path | None = None) -> tuple[dict, dict]:
    claude = scan_claude(claude_root)
    journeys = claude.pop("_journeys")
    ordered = []
    for sid, events in sorted(journeys.items()):
        events.sort(key=lambda e: e[0] or "")
        ordered.append({"session": sid, "events": [
            {"at": at, "item": item, "outcome": out} for at, item, out in events]})
    base = {
        "schema": SCHEMA,
        "evidenceClass": "observational-native-receipt",
        "privacy": "derived names, timestamps, counts, versions, outcomes, content digests and "
                   "12-hex session hashes only; no prompts, inputs, assistant text, paths or project names",
        "extractorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "scan": {"claudeCodeRoot": "~/.claude/projects", "codexRoot": "~/.codex/sessions",
                 "policy": "docs/development/REAL_USE_EVIDENCE.md"},
    }
    receipts = {**base, "hosts": [claude, scan_codex(codex_root)], "localStores": scan_local_stores(home or Path.home())}
    journey = {**base, "host": "claude-code", "journeys": ordered}
    return receipts, journey


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude", type=Path, default=Path("~/.claude/projects").expanduser())
    parser.add_argument("--codex", type=Path, default=Path("~/.codex/sessions").expanduser())
    parser.add_argument("--out", type=Path, help="write receipts JSON here")
    parser.add_argument("--journey-out", type=Path, help="write per-session ordered journeys here")
    args = parser.parse_args(argv)
    receipts, journey = build(args.claude, args.codex)
    for target, data in ((args.out, receipts), (args.journey_out, journey)):
        if target:
            target.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    if not args.out:
        json.dump(receipts, sys.stdout, indent=2, sort_keys=True)
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
